"""
Targeted fix for remaining unfixable items using exact EDB indicator paths.
"""
import sys, json, time, sqlite3
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_wind_mappings import call_edb

DB_PATH = 'data/monthly_brief.sqlite'

# Known-successful EDB path pattern from verified fx_fwd:D:
# "银行代客结售汇:以美元计价:差额:银行自身" → perfect match

# For each remaining unfixable, try the EXACT EDB path
EXACT_ATTEMPTS = [
    # --- 银行自身 系列 ---
    # Pattern from fx_fwd:D (verified): 银行代客结售汇:以美元计价:差额:银行自身
    ("fx_fwd:B", [
        "银行代客结售汇:以美元计价:结汇:银行自身",
        "银行结售汇:以美元计价:银行自身结汇:当月值",
    ]),
    ("fx_fwd:C", [
        "银行代客结售汇:以美元计价:售汇:银行自身",
        "银行结售汇:以美元计价:银行自身售汇:当月值",
    ]),

    # --- 远期净结汇 系列 ---
    # fx_fwd:E (verified): 远期结售汇签约额:以美元计价:结汇 → perfect
    # fx_fwd:F (fixed): 远期结售汇签约额:以美元计价:售汇 → perfect
    # So net = 结汇 - 售汇 (but DB stores it separately)
    ("fx_fwd:G", [
        "远期结售汇签约额:以美元计价:差额",
        "银行代客远期结售汇签约净额:当月值",
    ]),
    ("trade_goods:J", [
        "远期结售汇签约额:以美元计价:差额",
        "银行代客远期结售汇签约净额:当月值",
    ]),

    # --- 涉外支出:证券投资 ---
    ("fx_crossborder:S", [
        "银行代客涉外收付款:以美元计价:支出:资本和金融项目:证券投资",
        "银行代客涉外收付款:以人民币计价:支出:资本和金融项目:证券投资",
    ]),

    # --- 债券托管 系列 ---
    ("sec_fi:E", [  # 中国农业发展银行债:境外机构
        "债券持有量:中国农业发展银行债:银行间债券市场:境外机构",
        "中债:债券托管量:中国农业发展银行债:境外机构",
    ]),
    ("sec_fi:G", [  # 商业银行次级债:境外机构
        "债券持有量:商业银行次级债:银行间债券市场:境外机构",
    ]),
    ("sec_fi:I", [  # 二级资本工具:境外机构
        "债券持有量:二级资本工具:银行间债券市场:境外机构",
    ]),
    ("sec_fi:Q", [  # 区域集优中小企业集合票据
        "上清所:债券托管量:公司信用类债券:集合票据:人民银行批准的境外机构",
    ]),
    ("sec_fi:T", [  # 资产管理公司金融债
        "上清所:债券托管量:金融债:资产管理公司:人民银行批准的境外机构",
        "上清所:债券托管量:公司信用类债券:金融债:资产管理公司",
    ]),
    ("sec_fi:U", [  # 政府支持机构债券
        "上清所:债券托管量:政府支持机构债券:人民银行批准的境外机构",
        "债券持有量:政府支持机构债券:银行间债券市场:境外机构",
    ]),
    ("sec_fi:V", [  # 绿色债务融资工具
        "上清所:债券托管量:公司信用类债券:绿色债务融资工具:人民银行批准的境外机构",
    ]),

    # --- 港股通 系列 ---
    ("sec_eq:H", [  # 港股通:当日买入成交净额
        "港股通:当日成交净买入",
        "港股通:成交净买入",
        "港股通:净买入额",
    ]),
]

def get_db_values(conn, series_id):
    rows = conn.execute(
        "SELECT date, value FROM observations WHERE series_id=? AND value != 0 ORDER BY date",
        (series_id,)
    ).fetchall()
    return {r['date']: r['value'] for r in rows}

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    with open('config/wind_mapping.json', 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    mapping_by_id = {m['series_id']: m for m in mappings}

    fixed = []

    for sid, queries in EXACT_ATTEMPTS:
        m = mapping_by_id.get(sid)
        if not m:
            continue
        if m['status'] in ('verified', 'verified_with_transform'):
            continue

        print(f"\n{'='*60}")
        print(f"{sid} ({m['status']}): {m.get('display_name', m.get('wind_indicator', ''))[:80]}")
        db_map = get_db_values(conn, sid)
        if not db_map:
            print(f"  DB: NO non-zero data")
            continue
        dates = sorted(db_map.keys())
        print(f"  DB: {len(db_map)} values, {dates[0]} → {dates[-1]}")
        start, end = dates[0][:7], dates[-1][:7]

        found = False
        for qi, query_str in enumerate(queries):
            full_q = f"{query_str}（{start}-{end}）"
            print(f"  [{qi+1}] Trying: {query_str[:70]}...")

            result = call_edb(full_q)
            if not result or result.get('code') != 1:
                print(f"      ❌ {result.get('msg', 'no data') if result else 'None'}")
                continue

            edb_datas = result.get('data', {}).get('datas', [])
            if not edb_datas:
                print(f"      ❌ empty")
                continue

            edb_data = edb_datas[0].get('data', {})
            rows = edb_data.get('data', [])
            columns = edb_data.get('columns', [])
            edb_indicator = columns[1] if len(columns) > 1 else "unknown"
            index_id = edb_datas[0].get('extra', {}).get('index_id', '')

            edb_map = {}
            for row in rows:
                if len(row) >= 2:
                    d = str(row[0]).strip()[:10]
                    try:
                        edb_map[d] = float(row[1])
                    except:
                        pass

            if not edb_map:
                print(f"      ❌ no values")
                continue

            print(f"      ✓ EDB: {edb_indicator} ({len(edb_map)} pts, idx={index_id})")

            # Check overlap and compute ratios
            overlap = sorted(set(edb_map.keys()) & set(db_map.keys()))
            if len(overlap) < 3:
                # Try cumulative→monthly
                cum_dates = sorted(edb_map.keys())
                monthly_from_cum = {}
                prev = None
                for d in cum_dates:
                    if prev is not None:
                        monthly_from_cum[d] = edb_map[d] - edb_map[prev]
                    prev = d
                overlap2 = sorted(set(monthly_from_cum.keys()) & set(db_map.keys()))
                if len(overlap2) >= 3:
                    # Compare monthly from cumulative
                    ratios = []
                    for d in overlap2:
                        if abs(db_map[d]) > 1e-9:
                            ratios.append(monthly_from_cum[d] / db_map[d])
                    if ratios:
                        from statistics import median
                        factor = median(ratios)
                        errors = [abs(monthly_from_cum[d]/factor - db_map[d]) / abs(db_map[d]) * 100
                                  for d in overlap2 if abs(db_map[d]) > 1e-9]
                        avg_err = sum(errors) / len(errors) if errors else 999
                        print(f"      Cum→Monthly: {len(overlap2)} overlap, factor={factor:.0f}, avg_err={avg_err:.2f}%")
                        if avg_err <= 5:
                            print(f"      ✅ FIXED (cumulative→monthly)!")
                            _update_mapping(m, 'verified_with_transform', sid, overlap2, edb_indicator, index_id,
                                          monthly_from_cum, db_map, factor, cum_to_monthly=True)
                            fixed.append(sid)
                            found = True
                            break
                continue

            # Direct comparison with unit detection
            ratios = []
            for d in overlap:
                if abs(db_map[d]) > 1e-9:
                    ratios.append(edb_map[d] / db_map[d])

            if not ratios:
                print(f"      ❌ all DB values zero")
                continue

            from statistics import median
            factor = median(ratios)
            errors = [abs(edb_map[d]/factor - db_map[d]) / abs(db_map[d]) * 100
                      for d in overlap if abs(db_map[d]) > 1e-9]
            avg_err = sum(errors) / len(errors) if errors else 999
            max_err = max(errors) if errors else 999

            print(f"      Direct: {len(overlap)} overlap, factor={factor:.0f}, avg_err={avg_err:.2f}%, max_err={max_err:.2f}%")

            # Show samples
            for d in overlap[-3:]:
                ev = edb_map[d] / factor
                dv = db_map[d]
                pct = abs(ev - dv) / abs(dv) * 100 if abs(dv) > 1e-9 else 0
                print(f"        {d}: DB={dv:.4f} vs EDB={ev:.4f} ({pct:.2f}%)")

            if avg_err <= 5:
                print(f"      ✅ FIXED!")
                _update_mapping(m, 'verified_with_transform', sid, overlap, edb_indicator, index_id,
                              edb_map, db_map, factor)
                fixed.append(sid)
                found = True
                break
            elif avg_err <= 15:
                print(f"      ⚠️ Close ({avg_err:.1f}%) — possible data revision")

            time.sleep(0.2)

        if not found:
            print(f"  ❌ No fix found for {sid}")

    # Save
    with open('config/wind_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"FIXED: {len(fixed)} items")
    for sid in fixed:
        m = mapping_by_id[sid]
        print(f"  ✅ {sid}: {m.get('display_name', '')[:80]}")
    print(f"Saved: config/wind_mapping.json")
    conn.close()

def _update_mapping(m, status, sid, overlap, edb_indicator, index_id, edb_map, db_map, factor, cum_to_monthly=False):
    m['status'] = status
    transform = ['cumulative_to_monthly'] if cum_to_monthly else []
    if abs(factor - 1) > 0.01:
        transform.append(f'unit_div_{factor:.0f}')
    m['transform'] = transform

    errors = []
    samples = []
    for d in overlap[-5:]:
        ev = edb_map[d] / factor
        dv = db_map[d]
        pct = abs(ev - dv) / abs(dv) * 100 if abs(dv) > 1e-9 else 0
        errors.append(pct)
        samples.append((d, dv, ev, pct))

    avg_err = sum(errors) / len(errors) if errors else 0
    m['verify_details'] = {
        'overlap_points': len(overlap),
        'avg_diff_pct': round(avg_err, 2),
        'max_diff_pct': round(max(errors), 2) if errors else 0,
        'unit_factor': factor,
        'transform': transform,
        'samples': [(f"{d}", f"{dv:.4f}", f"{ev:.4f}") for d, dv, ev, pct in samples[-3:]],
        'edb_indicator': edb_indicator,
        'index_id': index_id,
        'note': 'Exact EDB path lookup' + (' + cumulative→monthly' if cum_to_monthly else ''),
    }
    m['verified_at'] = datetime.now().isoformat()
    m['verify_note'] = f'Exact path: {edb_indicator}'

if __name__ == '__main__':
    main()
