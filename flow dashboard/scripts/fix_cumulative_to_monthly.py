"""
Fix: Fetch cumulative (累计值) data from EDB and compute monthly (当月值)
via month-over-month differencing: 当月值 = 累计值(t) - 累计值(t-1)
"""
import sys, json, time, sqlite3
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_wind_mappings import call_edb, detect_unit_factor

DB_PATH = 'data/monthly_brief.sqlite'

# Known cumulative→monthly fix targets
# (series_id, cumulative_edb_query, cumulative_edb_index_id)
FIX_TARGETS = [
    # From re-test: EDB returned 累计值 but DB stores 当月值
    ("fx_fwd:B", "银行代客结售汇:以美元计价:结汇:银行自身:累计值", "M012255813"),
    ("fx_fwd:C", "银行代客结售汇:以人民币计价:售汇:银行自身:累计值", "M012255854"),
    ("fx_fwd:G", "银行代客远期结售汇展期差额:累计值", "M012255841"),
    ("trade_goods:J", "银行代客远期结售汇平仓差额:累计值", "M012255840"),
]

def get_db_values(conn, series_id):
    rows = conn.execute(
        "SELECT date, value FROM observations WHERE series_id=? AND value != 0 ORDER BY date",
        (series_id,)
    ).fetchall()
    return {r['date']: r['value'] for r in rows}

def compute_monthly_from_cumulative(edb_map):
    """Convert cumulative values to monthly via MoM differencing."""
    dates = sorted(edb_map.keys())
    monthly = {}
    prev_val = None
    for d in dates:
        val = edb_map[d]
        if prev_val is not None:
            monthly[d] = val - prev_val
        prev_val = val
    return monthly

def compare_monthly(edb_monthly, db_map):
    """Compare computed monthly values with DB."""
    overlap = sorted(set(edb_monthly.keys()) & set(db_map.keys()))
    if len(overlap) < 3:
        return None, len(overlap)

    errors = []
    samples = []
    for d in overlap:
        ev = edb_monthly[d]
        dv = db_map[d]
        diff = abs(ev - dv)
        pct = diff / abs(dv) * 100 if abs(dv) > 1e-9 else diff * 100
        errors.append(pct)
        samples.append((d, dv, ev, pct))

    avg_err = sum(errors) / len(errors)
    max_err = max(errors)
    return {
        'overlap': len(overlap),
        'avg_error': round(avg_err, 2),
        'max_error': round(max_err, 2),
        'samples': samples[-5:],
    }, len(overlap)

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    with open('config/wind_mapping.json', 'r', encoding='utf-8') as f:
        mappings = json.load(f)

    mapping_by_id = {m['series_id']: m for m in mappings}

    print(f"Testing cumulative→monthly conversion for {len(FIX_TARGETS)} targets...")
    print(f"{'='*80}")

    fixed = []
    still_broken = []

    for sid, cum_query, index_id in FIX_TARGETS:
        m = mapping_by_id.get(sid)
        if not m:
            continue

        print(f"\n{sid}: {m.get('display_name', m.get('wind_indicator', ''))[:80]}")
        print(f"  Wind query: {m.get('wind_indicator', '')[:80]}")
        db_map = get_db_values(conn, sid)
        if not db_map:
            print(f"  ⚠️ DB has no non-zero data")
            continue
        dates = sorted(db_map.keys())
        print(f"  DB: {len(db_map)} values, {dates[0]} → {dates[-1]}")

        # Fetch cumulative EDB data
        start = dates[0][:7]
        end = dates[-1][:7]
        query = f"{cum_query}（{start}-{end}）"
        print(f"  EDB query: {cum_query[:60]}...")

        result = call_edb(query)
        if not result or result.get('code') != 1:
            print(f"  ❌ EDB query failed: {result.get('msg', 'no result') if result else 'None'}")
            continue

        edb_datas = result.get('data', {}).get('datas', [])
        if not edb_datas:
            print(f"  ❌ No EDB data")
            continue

        edb_data = edb_datas[0].get('data', {})
        rows = edb_data.get('data', [])
        columns = edb_data.get('columns', [])
        edb_indicator = columns[1] if len(columns) > 1 else "unknown"

        # Build cumulative map
        cum_map = {}
        for row in rows:
            if len(row) >= 2:
                d = str(row[0]).strip()[:10]
                try:
                    cum_map[d] = float(row[1])
                except (ValueError, TypeError):
                    pass

        print(f"  EDB cumulative: {len(cum_map)} points, indicator={edb_indicator}")

        # Compute monthly from cumulative
        monthly_edb = compute_monthly_from_cumulative(cum_map)
        print(f"  Computed monthly: {len(monthly_edb)} points")

        # Compare with DB
        result_info, n_overlap = compare_monthly(monthly_edb, db_map)

        if result_info is None:
            print(f"  ❌ Only {n_overlap} overlap points — insufficient")
            continue

        print(f"  Overlap: {result_info['overlap']}, avg_error: {result_info['avg_error']}%, max_error: {result_info['max_error']}%")
        for d, dv, ev, pct in result_info['samples'][-3:]:
            print(f"    {d}: DB={dv:.4f} vs EDB(monthly)={ev:.4f} ({pct:.2f}%)")

        if result_info['avg_error'] <= 5:
            print(f"  ✅ FIXED via cumulative→monthly conversion!")
            # Update mapping
            m['status'] = 'verified_with_transform'
            m['transform'] = ['cumulative_to_monthly', f'unit_div_100000000']
            m['verify_details'] = {
                'overlap_points': result_info['overlap'],
                'avg_diff_pct': result_info['avg_error'],
                'max_diff_pct': result_info['max_error'],
                'unit_factor': 100000000.0,
                'transform': ['cumulative_to_monthly'],
                'samples': [(d, f"{dv:.4f}", f"{ev:.4f}") for d, dv, ev, pct in result_info['samples'][-3:]],
                'edb_indicator': edb_indicator,
                'edb_unit': '美元' if '美元' in cum_query else '元',
                'index_id': index_id,
                'note': f'Fixed by cumulative→monthly: {cum_query}',
                'cumulative_query': cum_query,
                'cumulative_to_monthly': True,
            }
            m['verified_at'] = datetime.now().isoformat()
            m['verify_note'] = f'Cumulative→monthly conversion. {result_info["overlap"]} pts, avg {result_info["avg_error"]}%'
            fixed.append((sid, result_info))
        else:
            print(f"  ❌ Still poor match after cumulative→monthly conversion")
            still_broken.append((sid, result_info))

        time.sleep(0.3)

    # Save
    with open('config/wind_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"CUMULATIVE→MONTHLY FIX RESULTS")
    print(f"  ✅ Fixed: {len(fixed)}")
    print(f"  ❌ Still broken: {len(still_broken)}")
    for sid, r in fixed:
        m = mapping_by_id[sid]
        print(f"  ✅ {sid} ({m['status']}): {m['wind_indicator'][:70]}")
    for sid, r in still_broken:
        print(f"  ❌ {sid}: avg_error={r['avg_error']}%")

    print(f"\nSaved: config/wind_mapping.json")
    conn.close()

if __name__ == '__main__':
    main()
