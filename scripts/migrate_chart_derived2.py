"""
migrate_chart_derived2.py — Migrate the remaining 7 chart-critical derived
that are still Excel cached/vlookup (NEXT_PHASE Loop 7).

Excel formulas extracted from FX Chartbook - Flow 0515.xlsx:

  fx_fwd:AB  即期代客结售汇差额(Headline) = R + AE
  fx_fwd:AD  代客衍生品净结汇           = S + T - AE
  fx_fwd:AJ  期权Delta净变动            = T  (copy of 期权Delta敞口变动)
  fx_fwd:AN  USDCNY                    = VLOOKUP(AM,AK:AL,2)  → reclassify raw
  sec_eq:AF  Net Equity Flow 3MMA      = AE(北上3M) + AD(南下3M)
  sec_eq:AH  CNYX 3M变动%             = AC/AC[t-12m] - 1
  sec_eq:AJ  USDCNY 3M变动%           = 1/(AB/AB[t-12m]) - 1

Validates against Excel cache (0% expected), writes to DB + metric_definitions.
For fx_fwd:AN (a VLOOKUP exchange-rate lookup, essentially raw), reclassify
series_type to raw and record metric_def instead of pretending it's derived.
"""
import sys, sqlite3, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import get_db

DB_PATH = 'data/monthly_brief.sqlite'


def load(conn, sid):
    rows = conn.execute(
        "SELECT date, value FROM observations WHERE series_id=? AND value IS NOT NULL ORDER BY date",
        (sid,)).fetchall()
    return {r[0][:10]: r[1] for r in rows}


def validate(conn, sid, computed, sample=6):
    cache = load(conn, sid)
    ov = sorted(set(computed) & set(cache))
    if not ov:
        return 0, None, None, []
    errs, smp = [], []
    for d in ov[-sample:]:
        cv, ev = cache[d], computed[d]
        denom = abs(cv) if abs(cv) > 1e-9 else 1.0
        e = abs(ev - cv) / denom * 100
        errs.append(e); smp.append((d, round(cv, 4), round(ev, 4), round(e, 3)))
    return len(ov), (sum(errs)/len(errs) if errs else None), (max(errs) if errs else None), smp


def recompute_sum(a, b):
    """a + b on shared dates."""
    return {d: a[d] + b[d] for d in (set(a) & set(b)) if a[d] is not None and b[d] is not None}


def recompute_a_minus_b(a, b):
    return {d: a[d] - b[d] for d in (set(a) & set(b)) if a[d] is not None and b[d] is not None}


def recompute_copy(a):
    return {d: v for d, v in a.items() if v is not None}


def recompute_three_m_change(curr_map, window_points=60):
    """(curr[t] / curr[t-window_points]) - 1.

    sec_eq is daily; Excel uses AC[t]/AC[t-60rows] (≈3 months trading days).
    window_points=60 = number of observations to look back, matching Excel rows.
    """
    dates = sorted(curr_map.keys())
    result = {}
    for i, d in enumerate(dates):
        if i - window_points < 0:
            continue
        base = dates[i - window_points]
        cur = curr_map[d]; bas = curr_map[base]
        if bas is not None and bas != 0 and cur is not None:
            result[d] = (cur / bas) - 1
    return result


def recompute_usdcny_three_m_change(usdcny_map, window_points=60):
    """1/(USDCNY[t]/USDCNY[t-window]) - 1 = USDCNY[t-window]/USDCNY[t] - 1."""
    dates = sorted(usdcny_map.keys())
    result = {}
    for i, d in enumerate(dates):
        if i - window_points < 0:
            continue
        base = dates[i - window_points]
        cur = usdcny_map[d]; bas = usdcny_map[base]
        if cur is not None and cur != 0 and bas is not None:
            result[d] = (bas / cur) - 1
    return result


def write_obs(conn, sid, computed, run_id, source='python_recompute'):
    n = 0
    for d, v in computed.items():
        if v is None: continue
        conn.execute(
            "INSERT OR REPLACE INTO observations (series_id, date, value, source, "
            "source_vintage, imported_at, run_id) VALUES (?,?,?,?,?,?,?)",
            (sid, d, float(v), source, 'v2.0', datetime.now().isoformat(), run_id))
        n += 1
    if computed:
        ds = sorted(computed.keys())
        conn.execute("UPDATE series SET first_date=?, last_date=?, update_status='recomputed' WHERE series_id=?",
                     (ds[0], ds[-1], sid))
    return n


def write_def(conn, sid, desc, inputs, impl, missing_rule, sign_conv, notes=''):
    conn.execute("""
        INSERT INTO metric_definitions
        (series_id, formula_description, input_series_json, calculation_version,
         implementation, missing_value_rule, sign_convention)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(series_id) DO UPDATE SET
          formula_description=excluded.formula_description,
          input_series_json=excluded.input_series_json,
          implementation=excluded.implementation,
          missing_value_rule=excluded.missing_value_rule,
          sign_convention=excluded.sign_convention
    """, (sid, desc, json.dumps(inputs, ensure_ascii=False), 'v2.1', impl, missing_rule, sign_conv))
    conn.execute("UPDATE series SET notes=COALESCE(?,notes) WHERE series_id=? AND (notes IS NULL OR notes='')",
                 (notes, sid))


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    run_id = 'run_loop7_' + datetime.now().strftime('%Y%m%d_%H%M%S')
    conn.execute("INSERT INTO update_runs (run_id, started_at, status, requested_series) VALUES (?,?,?,?)",
                 (run_id, datetime.now().isoformat(), 'running', 'loop7_derived'))

    print("=" * 70)
    print("Loop 7: migrating remaining chart-critical derived")
    print("=" * 70)

    # Load fx_fwd inputs
    r_fwd = load(conn, 'fx_fwd:R')
    s_fwd = load(conn, 'fx_fwd:S')
    t_fwd = load(conn, 'fx_fwd:T')
    ae_fwd = load(conn, 'fx_fwd:AE')

    # Load sec_eq inputs (daily — but DB stores them)
    ae_eq = load(conn, 'sec_eq:AE')   # 北上3M
    ad_eq = load(conn, 'sec_eq:AD')   # 南下3M
    ac_eq = load(conn, 'sec_eq:AC')   # CNYX
    ab_eq = load(conn, 'sec_eq:AB')   # USDCNY

    results = []
    # 1. fx_fwd:AB = R + AE
    ab = recompute_sum(r_fwd, ae_fwd)
    ov, avg, mx, smp = validate(conn, 'fx_fwd:AB', ab)
    results.append(('fx_fwd:AB', ab, ov, avg, mx, smp,
                    "R[t] + AE[t] (即期代客结售汇 + 远期履约/平仓)",
                    ['fx_fwd:R', 'fx_fwd:AE'], 'recompute_sum', 'skip if null', 'signed flow'))

    # 2. fx_fwd:AD = S + T - AE
    st = recompute_sum(s_fwd, t_fwd)
    ad_fwd = recompute_a_minus_b(st, ae_fwd)
    ov, avg, mx, smp = validate(conn, 'fx_fwd:AD', ad_fwd)
    results.append(('fx_fwd:AD', ad_fwd, ov, avg, mx, smp,
                    "S[t] + T[t] - AE[t] (远期净签约 + 期权Delta - 履约)",
                    ['fx_fwd:S', 'fx_fwd:T', 'fx_fwd:AE'], 'recompute_sum+recompute_a_minus_b',
                    'skip if null', 'signed flow'))

    # 3. fx_fwd:AJ = T (copy)
    aj = recompute_copy(t_fwd)
    ov, avg, mx, smp = validate(conn, 'fx_fwd:AJ', aj)
    results.append(('fx_fwd:AJ', aj, ov, avg, mx, smp,
                    "T[t] (期权Delta净变动 = 期权Delta敞口变动 copy)",
                    ['fx_fwd:T'], 'recompute_copy', 'skip if null', 'signed'))

    # 4. sec_eq:AF = AE + AD (北上3M + 南下3M)
    af = recompute_sum(ae_eq, ad_eq)
    ov, avg, mx, smp = validate(conn, 'sec_eq:AF', af)
    results.append(('sec_eq:AF', af, ov, avg, mx, smp,
                    "AE[t] + AD[t] (北上资金3M + 南下资金3M = 陆港通净流入3MMA)",
                    ['sec_eq:AE', 'sec_eq:AD'], 'recompute_sum', 'skip if null', 'signed flow'))

    # 5. sec_eq:AH = AC/AC[t-3m] - 1
    ah = recompute_three_m_change(ac_eq, 60)
    ov, avg, mx, smp = validate(conn, 'sec_eq:AH', ah)
    results.append(('sec_eq:AH', ah, ov, avg, mx, smp,
                    "AC[t]/AC[t-3m] - 1 (CNYX 3个月变动率)",
                    ['sec_eq:AC'], 'recompute_three_m_change', 'skip if base missing',
                    'positive=升值'))

    # 6. sec_eq:AJ = 1/(AB/AB[t-3m]) - 1 = AB[t-3m]/AB[t] - 1
    aj_eq = recompute_usdcny_three_m_change(ab_eq, 60)
    ov, avg, mx, smp = validate(conn, 'sec_eq:AJ', aj_eq)
    results.append(('sec_eq:AJ', aj_eq, ov, avg, mx, smp,
                    "AB[t-3m]/AB[t] - 1 (USDCNY 3个月变动率, 升值为正)",
                    ['sec_eq:AB'], 'recompute_usdcny_three_m_change', 'skip if base missing',
                    'positive=人民币升值'))

    # Report
    print(f"\n{'series':14s} {'overlap':>8s} {'avg_err':>10s} {'max_err':>10s}  samples")
    print("-" * 90)
    passed = []
    for sid, comp, ov, avg, mx, smp, desc, inputs, impl, mr, sc in results:
        a = f"{avg:.4f}%" if avg is not None else "N/A"
        m = f"{mx:.4f}%" if mx is not None else "N/A"
        s3 = "; ".join(f"{d}:{c}/{e}" for d, c, e, _ in smp[-3:])
        ok = (avg is not None and avg <= 1.0)
        print(f"{sid:14s} {ov:>8d} {a:>10s} {m:>10s}  [{'PASS' if ok else 'FAIL'}] {s3}")
        if ok:
            passed.append((sid, comp, desc, inputs, impl, mr, sc))

    # fx_fwd:AN: reclassify as raw (VLOOKUP exchange-rate lookup, not derived)
    conn.execute("UPDATE series SET series_type='raw', "
                 "notes=COALESCE('VLOOKUP汇率查找表(AM->AK:AL);本质raw外部数据',notes) "
                 "WHERE series_id='fx_fwd:AN' AND series_type='derived'")
    write_def(conn, 'fx_fwd:AN',
              "VLOOKUP(AM[t],AK:AL,2,FALSE) — 按日期查USDCNY汇率查找表",
              ['excel:AK:AL'], 'excel_vlookup_lookup',
              'skip if date not in lookup table', 'CNY per USD',
              '重分类为raw: 汇率查找非计算衍生')
    print(f"\nfx_fwd:AN           reclassified raw (VLOOKUP rate lookup, not derived)")

    # Write passed
    print("\n" + "=" * 70)
    for sid, comp, desc, inputs, impl, mr, sc in passed:
        n = write_obs(conn, sid, comp, run_id)
        write_def(conn, sid, desc, inputs, impl, mr, sc,
                  notes=f"Loop7 migrated from Excel cache; {len(comp)} pts")
        print(f"  ✅ {sid}: wrote {n} obs + metric_definition")

    conn.execute("UPDATE update_runs SET status='completed', finished_at=?, successful_series=? WHERE run_id=?",
                 (datetime.now().isoformat(), json.dumps([r[0] for r in passed]), run_id))
    conn.commit()
    conn.close()
    print(f"\nrun_id={run_id}. Passed: {len(passed)}/6 (AN reclassified)")


if __name__ == '__main__':
    main()
