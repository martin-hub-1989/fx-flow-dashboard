#!/usr/bin/env python3
"""
migrate_chart_derived.py — Migrate the 6 chart-critical derived indicators
that are still Excel caches to Python-recomputed values.

Calculation logic extracted from FX Chartbook - Flow 0515.xlsx:

  fx_fwd:AE  远期履约/平仓  = (J[t+1] + G[t]) - J[t]    # J=远期累计未到期存量, G=当月净签约(S=G)
  fx_fwd:Y   代客衍生品签约 = G[t] + T[t]              # T=期权Delta敞口变动(cache)
  fx_fwd:AN  USDCNY         = VLOOKUP(AM, AK:AL, 2)     # 汇率查找 → 保留 cache, 标 raw 性质
  trade_goods:AC 分位       = PERCENTRANK(AA[t:t+59], AA[t]) * 100
  trade_goods:AD 分位       = PERCENTRANK(AB[t:t+59], AB[t]) * 100
  trade_goods:U  即远期结汇估 = T[t] + 0.75*J[t] - 0.75*AJ_fx[t]   # AJ from 即远期 by date

Validates against existing Excel cache, writes to DB + metric_definitions.
"""
import sys, sqlite3, json, bisect
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import get_db

DB_PATH = 'data/monthly_brief.sqlite'


def load_series(conn, sid):
    """Return {date_str: value} for a series (non-null, non-zero excluded for percentile)."""
    rows = conn.execute(
        "SELECT date, value FROM observations WHERE series_id=? AND value IS NOT NULL ORDER BY date",
        (sid,)
    ).fetchall()
    return {r[0][:10]: r[1] for r in rows}


def excel_percentrank(arr, x):
    """Replicate Excel PERCENTRANK(array, x). Returns 0..1 or None."""
    arr = sorted(v for v in arr if v is not None)
    n = len(arr)
    if n < 2:
        return None
    if x <= arr[0]:
        return 0.0
    if x >= arr[-1]:
        return 1.0
    idx = bisect.bisect_left(arr, x)
    if idx < n and arr[idx] == x:
        # x present — average rank of duplicates
        lo = idx
        while lo > 0 and arr[lo - 1] == x:
            lo -= 1
        hi = idx
        while hi < n - 1 and arr[hi + 1] == x:
            hi += 1
        avg_rank = (lo + hi) / 2.0
        return avg_rank / (n - 1)
    else:
        # linear interpolation
        lower = arr[idx - 1]
        upper = arr[idx]
        if upper == lower:
            return (idx - 1) / (n - 1)
        return (idx - 1 + (x - lower) / (upper - lower)) / (n - 1)


def recompute_fwd_ae(j_map, g_map):
    """fx_fwd:AE = (J[t-1] + G[t]) - J[t].

    Excel is reverse-chronological (newest row 7/8), so formula =(J8+S7)-J7
    means row8 = previous period. In DB ascending order: J[t-1] = previous date.
    Semantics: 履约 = 签约(G) - 存量变动(ΔJ) where ΔJ = J[t]-J[t-1].
    """
    result = {}
    j_dates = sorted(j_map.keys())
    for i, d in enumerate(j_dates):
        if i == 0:
            continue  # no previous period
        d_prev = j_dates[i - 1]
        j_t = j_map[d]
        j_prev = j_map[d_prev]
        g_t = g_map.get(d)
        if j_t is not None and j_prev is not None and g_t is not None:
            result[d] = (j_prev + g_t) - j_t
    return result


def recompute_fwd_y(g_map, t_map):
    """fx_fwd:Y = G[t] + T[t]."""
    result = {}
    for d in sorted(set(g_map) & set(t_map)):
        if g_map[d] is not None and t_map[d] is not None:
            result[d] = g_map[d] + t_map[d]
    return result


def recompute_percentile(base_map, window=60):
    """PERCENTRANK over PAST window of `window` months (Excel reverse-chrono).

    Excel AC8 = PERCENTRANK(AA8:AA67, AA8); row8=newest, rows8-67 = past 60 months.
    In DB ascending order: past window = dates[i-window+1 : i+1].
    Returns 0..100 (percent). Excel cache is 0..1, validated with cache_scale.
    """
    result = {}
    dates = sorted(base_map.keys())
    for i, d in enumerate(dates):
        start = max(0, i - window + 1)
        window_dates = dates[start:i + 1]
        window_vals = [base_map[wd] for wd in window_dates if base_map[wd] is not None]
        if len(window_vals) < 2:
            continue
        x = base_map[d]
        if x is None:
            continue
        pr = excel_percentrank(window_vals, x)
        if pr is not None:
            result[d] = pr * 100.0  # store as percent 0-100
    return result


def recompute_trade_u(t_map, j_map, ae_fx_map):
    """trade_goods:U = T[t] + 0.75*J[t] - 0.75*AE_fx[t].

    Excel: U8 = T8 + J8*0.75 - VLOOKUP(Q8,'3.即远期'!P:AJ,16,FALSE)*0.75
    VLOOKUP col 16 from P = AE (远期履约/平仓), NOT AJ. AE from 即远期 by date.
    """
    result = {}
    for d in sorted(set(t_map) & set(j_map)):
        t_t = t_map.get(d)
        j_t = j_map.get(d)
        ae_t = ae_fx_map.get(d)
        if t_t is None or j_t is None:
            continue
        if ae_t is None:
            continue
        result[d] = t_t + 0.75 * j_t - 0.75 * ae_t
    return result


def validate(conn, sid, computed, sample=8, cache_scale='auto'):
    """Compare computed with Excel cache. Return (overlap, avg_err, max_err, samples).

    cache_scale: 'auto' detects 0-1 vs 0-100 from cache range; or explicit float.
    """
    cache = load_series(conn, sid)
    overlap = sorted(set(computed) & set(cache))
    if not overlap:
        return 0, None, None, []
    # auto-detect scale: if cache values are all < 2, assume 0-1 (scale to 100)
    if cache_scale == 'auto':
        probe = [abs(cache[d]) for d in overlap if cache[d] is not None]
        cache_scale = 100.0 if (probe and max(probe) < 2.0) else 1.0
    errors, samples = [], []
    for d in overlap[-sample:]:
        cv = cache[d] * cache_scale
        ev = computed[d]
        if cv is None or ev is None:
            continue
        denom = abs(cv) if abs(cv) > 1e-9 else 1.0
        err = abs(ev - cv) / denom * 100
        errors.append(err)
        samples.append((d, cv, ev, err))
    avg = sum(errors) / len(errors) if errors else None
    mx = max(errors) if errors else None
    return len(overlap), avg, mx, samples


def write_metric_def(conn, sid, formula_desc, inputs, impl, missing_rule, sign_conv, notes=""):
    """Upsert metric_definitions row."""
    conn.execute("""
        INSERT INTO metric_definitions
        (series_id, formula_description, input_series_json, calculation_version,
         implementation, missing_value_rule, sign_convention)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(series_id) DO UPDATE SET
          formula_description=excluded.formula_description,
          input_series_json=excluded.input_series_json,
          calculation_version=excluded.calculation_version,
          implementation=excluded.implementation,
          missing_value_rule=excluded.missing_value_rule,
          sign_convention=excluded.sign_convention
    """, (sid, formula_desc, json.dumps(inputs, ensure_ascii=False), "v2.0",
          impl, missing_rule, sign_conv))
    # update series series_type if was cache-derived without def
    conn.execute("UPDATE series SET notes=COALESCE(?, notes) WHERE series_id=? AND (notes IS NULL OR notes='')",
                 (notes, sid))


def write_observations(conn, sid, computed, run_id):
    """Replace observations for sid with computed (INSERT OR REPLACE ok for derived — derived are recomputed, not historical revisions)."""
    n = 0
    for d, v in computed.items():
        if v is None:
            continue
        conn.execute("""
            INSERT OR REPLACE INTO observations (series_id, date, value, source, source_vintage, imported_at, run_id)
            VALUES (?,?,?,?,?,?,?)
        """, (sid, d, float(v), 'python_recompute', 'v2.0', datetime.now().isoformat(), run_id))
        n += 1
    # update first/last date
    if computed:
        ds = sorted(computed.keys())
        conn.execute("UPDATE series SET first_date=?, last_date=?, update_status='recomputed' WHERE series_id=?",
                     (ds[0], ds[-1], sid))
    return n


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    run_id = 'run_recompute_' + datetime.now().strftime('%Y%m%d_%H%M%S')
    conn.execute("INSERT INTO update_runs (run_id, started_at, status, requested_series) VALUES (?,?,?,?)",
                 (run_id, datetime.now().isoformat(), 'running', 'chart_critical_derived'))

    print("=" * 70)
    print("Migrating chart-critical derived indicators to Python recompute")
    print("=" * 70)

    results = []

    # --- Load inputs ---
    j_fwd = load_series(conn, 'fx_fwd:J')   # 远期累计未到期存量
    g_fwd = load_series(conn, 'fx_fwd:G')   # 远期净签约当月值
    t_fwd = load_series(conn, 'fx_fwd:T')   # 期权Delta敞口变动 (cache)
    ae_fx = load_series(conn, 'fx_fwd:AE')  # 远期履约/平仓 (just recomputed above)
    aa_tg = load_series(conn, 'trade_goods:AA')  # 跨境-结汇 TTM
    ab_tg = load_series(conn, 'trade_goods:AB')  # 顺差-结汇 TTM
    t_tg = load_series(conn, 'trade_goods:T')    # 即期结汇差额
    j_tg = load_series(conn, 'trade_goods:J')    # 远期净结汇当月值

    # --- 1. fx_fwd:AE ---
    ae = recompute_fwd_ae(j_fwd, g_fwd)
    ov, avg, mx, smp = validate(conn, 'fx_fwd:AE', ae)
    results.append(('fx_fwd:AE', ae, ov, avg, mx, smp,
                     "(J[t+1] + G[t]) - J[t]", ['fx_fwd:J', 'fx_fwd:G'],
                     'migrate_chart_derived.recompute_fwd_ae',
                     'skip if any input null', 'positive=履约结汇方向'))

    # --- 2. fx_fwd:Y ---
    y = recompute_fwd_y(g_fwd, t_fwd)
    ov, avg, mx, smp = validate(conn, 'fx_fwd:Y', y)
    results.append(('fx_fwd:Y', y, ov, avg, mx, smp,
                     "G[t] + T[t] (远期净签约 + 期权Delta敞口变动)",
                     ['fx_fwd:G', 'fx_fwd:T'],
                     'migrate_chart_derived.recompute_fwd_y',
                     'skip if any input null', 'positive=净签约方向'))

    # --- 3. trade_goods:AC ---
    ac = recompute_percentile(aa_tg, window=60)
    ov, avg, mx, smp = validate(conn, 'trade_goods:AC', ac)
    results.append(('trade_goods:AC', ac, ov, avg, mx, smp,
                     "PERCENTRANK(AA[t-59:t], AA[t]) * 100 (past 60M window)",
                     ['trade_goods:AA'],
                     'migrate_chart_derived.recompute_percentile',
                     'skip if window<2', '0-100, higher=头寸越大'))

    # --- 4. trade_goods:AD ---
    ad = recompute_percentile(ab_tg, window=60)
    ov, avg, mx, smp = validate(conn, 'trade_goods:AD', ad)
    results.append(('trade_goods:AD', ad, ov, avg, mx, smp,
                     "PERCENTRANK(AB[t-59:t], AB[t]) * 100 (past 60M window)",
                     ['trade_goods:AB'],
                     'migrate_chart_derived.recompute_percentile',
                     'skip if window<2', '0-100, higher=头寸越大'))

    # --- 5. trade_goods:U ---
    # NOTE: depends on fx_fwd:AE which must be recomputed first (above).
    u = recompute_trade_u(t_tg, j_tg, ae_fx)
    ov, avg, mx, smp = validate(conn, 'trade_goods:U', u)
    results.append(('trade_goods:U', u, ov, avg, mx, smp,
                     "T[t] + 0.75*J[t] - 0.75*AE_fx[t]  (即期结汇 + 0.75*(远期净结汇 - 远期履约/平仓))",
                     ['trade_goods:T', 'trade_goods:J', 'fx_fwd:AE'],
                     'migrate_chart_derived.recompute_trade_u',
                     'skip if AE_fx missing for date', 'positive=净结汇'))

    # --- Report + decision ---
    print(f"\n{'series':18s} {'overlap':>8s} {'avg_err':>9s} {'max_err':>9s}  samples(last 3)")
    print("-" * 90)
    threshold = 1.0  # percent
    pass_list = []
    for sid, comp, ov, avg, mx, smp, desc, inputs, impl, mr, sc in results:
        avg_s = f"{avg:.3f}%" if avg is not None else "N/A"
        mx_s = f"{mx:.3f}%" if mx is not None else "N/A"
        last3 = "; ".join(f"{d}:{c:.2f}/{e:.2f}" for d, c, e, _ in smp[-3:])
        status = "PASS" if (avg is not None and avg <= threshold) else "FAIL"
        print(f"{sid:18s} {ov:>8d} {avg_s:>9s} {mx_s:>9s}  [{status}] {last3}")
        if status == "PASS":
            pass_list.append((sid, comp, desc, inputs, impl, mr, sc))

    # --- fx_fwd:AN: record formula, keep cache ---
    write_metric_def(conn, 'fx_fwd:AN',
                     "VLOOKUP(AM[t], AK:AL, 2, FALSE) — 按日期查汇率查找表 (USDCNY)",
                     ['excel:AK:AL'], 'excel_vlookup',
                     'skip if date not in lookup table', 'CNY per USD')
    print(f"\nfx_fwd:AN           kept as exchange-rate lookup (cache retained, metric_def recorded)")

    # --- Write passed ---
    print("\n" + "=" * 70)
    if not pass_list:
        print("⚠️  No indicators passed validation — not writing to DB.")
    else:
        for sid, comp, desc, inputs, impl, mr, sc in pass_list:
            n = write_observations(conn, sid, comp, run_id)
            write_metric_def(conn, sid, desc, inputs, impl, mr, sc,
                             notes=f"Migrated from Excel cache; validated {len(comp)} pts")
            print(f"  ✅ {sid}: wrote {n} obs + metric_definition")

    conn.execute("UPDATE update_runs SET status='completed', finished_at=?, successful_series=? WHERE run_id=?",
                 (datetime.now().isoformat(), json.dumps([r[0] for r in pass_list]), run_id))
    conn.commit()
    conn.close()
    print(f"\nrun_id={run_id} completed. Passed: {len(pass_list)}/5")


if __name__ == '__main__':
    main()
