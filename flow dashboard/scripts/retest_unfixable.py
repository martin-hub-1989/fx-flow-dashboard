"""
Re-test all unfixable Wind EDB mappings with alternative query strategies.
The original data ALL comes from Wind, so these should be findable with
the right query string.
"""
import sys, json, time, sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_wind_mappings import call_edb, detect_unit_factor

DB_PATH = 'data/monthly_brief.sqlite'

def load_mappings():
    with open('config/wind_mapping.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_db_values(conn, series_id):
    """Get all non-zero observations for a series."""
    rows = conn.execute(
        "SELECT date, value FROM observations WHERE series_id=? AND value != 0 ORDER BY date",
        (series_id,)
    ).fetchall()
    return {r['date']: r['value'] for r in rows}

def generate_alternative_queries(mapping):
    """Generate alternative EDB query strings to try."""
    wind = mapping.get('wind_indicator', '')
    module = mapping.get('module', '')
    sid = mapping['series_id']

    queries = []

    # Strategy 1: Original query (as-is)
    queries.append(('original', wind))

    # Strategy 2: Strip "中国:" prefix
    if wind.startswith('中国:'):
        queries.append(('strip_中国', wind[3:]))

    # Strategy 3: Remove "以人民币计价" and add "以美元计价"
    if '以人民币计价' in wind:
        usd = wind.replace('以人民币计价', '以美元计价')
        queries.append(('to_usd', usd))
    elif '以美元计价' in wind:
        cny = wind.replace('以美元计价', '以人民币计价')
        queries.append(('to_cny', cny))

    # Strategy 4: For 结汇/售汇 items - try with full EDB naming pattern
    if '结汇' in wind and '以美元计价' not in wind and '以人民币计价' not in wind:
        if '银行代客结汇:' in wind or wind.startswith('银行代客结汇'):
            # Try USD denomination
            simple = wind.replace('银行代客结汇:', '').replace('银行代客结汇', '')
            if simple:
                queries.append(('fx_usd_jiehui', f'银行代客结售汇:以美元计价:结汇:{simple}'))
                queries.append(('fx_cny_jiehui', f'银行代客结售汇:以人民币计价:结汇:{simple}'))

    if '售汇' in wind and '以美元计价' not in wind and '以人民币计价' not in wind:
        if '银行代客售汇:' in wind or wind.startswith('银行代客售汇'):
            simple = wind.replace('银行代客售汇:', '').replace('银行代客售汇', '')
            if simple:
                queries.append(('fx_usd_shouhui', f'银行代客结售汇:以美元计价:售汇:{simple}'))
                queries.append(('fx_cny_shouhui', f'银行代客结售汇:以人民币计价:售汇:{simple}'))

    # Strategy 5: Try "当月值" instead of "累计值" and vice versa
    if '当月值' in wind:
        queries.append(('to_cumulative', wind.replace('当月值', '累计值')))
    if '累计值' in wind:
        queries.append(('to_monthly', wind.replace('累计值', '当月值')))

    # Strategy 6: For 涉外收付 items - try EDB naming
    if '境内银行代客' in wind:
        alt = wind.replace('境内银行代客', '银行代客')
        queries.append(('remove_境内', alt))
        # Try with 以美元计价
        alt2 = wind.replace('境内银行代客', '银行代客').replace('涉外收付款:', '涉外收付款:以美元计价:')
        queries.append(('add_usd', alt2))

    # Strategy 7: For 涉外收入/支出 items
    if '涉外收入' in wind:
        for prefix in ['银行代客涉外收付款:以美元计价:收入:', '银行代客涉外收付款:以人民币计价:收入:']:
            simple = wind.split('涉外收入:')[-1] if '涉外收入:' in wind else wind
            queries.append(('fx_income', f'{prefix}{simple}'))
    if '涉外支出' in wind:
        for prefix in ['银行代客涉外收付款:以美元计价:支出:', '银行代客涉外收付款:以人民币计价:支出:']:
            simple = wind.split('涉外支出:')[-1] if '涉外支出:' in wind else wind
            queries.append(('fx_expense', f'{prefix}{simple}'))

    # Strategy 8: For 债券托管量 items - try different bond category names
    if '债券托管量' in wind:
        # Strip 人民银行批准的境外机构 → 境外机构
        if '人民银行批准的境外机构' in wind:
            queries.append(('strip_pboc', wind.replace('人民银行批准的境外机构', '境外机构')))
        # Try adding 中债/上清 prefix omitting
        if '中债:债券托管量:' in wind:
            simpler = wind.replace('中债:债券托管量:', '债券托管量:')
            queries.append(('strip_中债', simpler))
        if '上清所:债券托管量:' in wind:
            simpler = wind.replace('上清所:债券托管量:', '债券托管量:')
            queries.append(('strip_上清', simpler))

    # Strategy 9: For 证券EQ / 巨潮指数
    if '巨潮' in wind:
        queries.append(('juchao_alt', wind.replace('巨潮人民币名义有效汇率指数', '人民币名义有效汇率指数')))

    # Strategy 10: For 港股通/陆股通
    if '港股通' in wind or '陆股通' in wind:
        if '当日' in wind:
            queries.append(('to_netbuy', wind.replace('当日买入成交净额(人民币)', '当日成交净买入').replace('港股通:', '').replace('陆股通:', '')))

    # Strategy 11: For PMI and other macro indicators
    if wind == 'PMI':
        queries.append(('pmi_mfg', '制造业采购经理指数(PMI)'))
        queries.append(('pmi_caixin', '中国:财新PMI'))

    # Strategy 12: For 服务贸易 items - try 服务进出口 naming
    if '服务出口' in wind:
        queries.append(('svc_export', wind.replace('中国:服务出口金额:人民币:', '服务进出口金额(人民币计价):出口:')))
    if '服务进口' in wind:
        queries.append(('svc_import', wind.replace('中国:服务进口金额:人民币:', '服务进出口金额(人民币计价):进口:')))

    # Strategy 13: For 银行自身 items
    if '银行自身结汇' in wind:
        queries.append(('bank_self_jh', '银行结售汇:以美元计价:银行自身结汇:当月值'))
    if '银行自身售汇' in wind:
        queries.append(('bank_self_sh', '银行结售汇:以美元计价:银行自身售汇:当月值'))

    # Strategy 14: For 远期售汇 签约
    if '远期售汇' in wind:
        queries.append(('fwd_sell', '远期结售汇签约额:以美元计价:售汇'))

    # Strategy 15: For FDI service sector
    if '服务业' in wind and 'FDI' in module:
        queries.append(('svc_fdi', wind.replace('服务业:实际使用外商直接投资:', '实际使用外资(人民币):服务业:')))

    # Strategy 16: Try shorter names - last part only
    parts = wind.split(':')
    if len(parts) > 3:
        short = ':'.join(parts[-3:])
        queries.append(('short_last3', short))
    if len(parts) > 2:
        short = ':'.join(parts[-2:])
        queries.append(('short_last2', short))

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for tag, q in queries:
        if q and q not in seen:
            seen.add(q)
            unique.append((tag, q))

    return unique

def try_queries(mapping, db_map, conn):
    """Try all alternative queries for a mapping, return best result."""
    queries = generate_alternative_queries(mapping)
    best_result = None

    for tag, query_str in queries:
        # Build EDB query with date range
        if db_map:
            dates = sorted(db_map.keys())
            start = dates[0][:7] if dates else '2023-01'
            end = dates[-1][:7] if dates else '2026-05'
        else:
            start, end = '2024-01', '2026-05'

        full_query = f"{query_str}（{start}-{end}）"

        try:
            result = call_edb(full_query)
        except Exception as e:
            continue

        if not result or 'error' in (result or {}):
            continue

        if result.get('code') != 1:
            continue

        edb_datas = result.get('data', {}).get('datas', [])
        if not edb_datas:
            continue

        edb_data = edb_datas[0].get('data', {})
        rows = edb_data.get('data', [])
        columns = edb_data.get('columns', [])
        attrs = edb_data.get('attrs', {})
        index_id = edb_datas[0].get('extra', {}).get('index_id', '')
        edb_indicator = columns[1] if len(columns) > 1 else "unknown"
        edb_unit = ''
        if attrs:
            edb_unit = list(attrs.values())[0].get('unit', '') if isinstance(attrs, dict) else ''

        if not rows:
            continue

        # Build EDB map
        edb_map = {}
        for row in rows:
            if len(row) >= 2:
                d = str(row[0]).strip()[:10]
                try:
                    edb_map[d] = float(row[1])
                except (ValueError, TypeError):
                    pass

        if not edb_map:
            continue

        best_result = {
            'tag': tag,
            'query': query_str,
            'edb_map': edb_map,
            'edb_indicator': edb_indicator,
            'edb_unit': edb_unit,
            'index_id': index_id,
            'n_points': len(rows),
        }

        # If we have DB values, check match quality
        if db_map:
            factor, error = detect_unit_factor(edb_map, db_map)
            best_result['factor'] = factor
            best_result['detection_error'] = error

            # Check overlap
            overlap = set(edb_map.keys()) & set(db_map.keys())
            if overlap:
                # Apply factor
                samples = []
                errors = []
                for d in sorted(overlap)[-5:]:
                    ev = edb_map[d] / factor
                    dv = db_map[d]
                    diff = abs(ev - dv)
                    pct = diff / abs(dv) * 100 if abs(dv) > 1e-9 else diff * 100
                    samples.append((d, round(dv, 4), round(ev, 4), round(pct, 2)))
                    errors.append(pct)
                avg_err = sum(errors) / len(errors) if errors else 999
                best_result['overlap'] = len(overlap)
                best_result['avg_error'] = round(avg_err, 2)
                best_result['max_error'] = round(max(errors), 2) if errors else 999
                best_result['samples'] = samples

        # If this is a very close match, stop searching
        if db_map and best_result.get('avg_error', 999) < 5:
            break

        time.sleep(0.15)

    return best_result

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    mappings = load_mappings()
    unfixable_statuses = ['no_result', 'no_data_in_db', 'edb_no_exact_match']
    targets = [m for m in mappings if m.get('status') in unfixable_statuses]

    print(f"Re-testing {len(targets)} unfixable mappings...")
    print(f"  no_result: {sum(1 for m in targets if m['status']=='no_result')}")
    print(f"  no_data_in_db: {sum(1 for m in targets if m['status']=='no_data_in_db')}")
    print(f"  edb_no_exact_match: {sum(1 for m in targets if m['status']=='edb_no_exact_match')}")
    print(f"{'='*80}")

    newly_fixed = []
    still_broken = []
    results_by_status = defaultdict(list)

    for i, m in enumerate(targets):
        sid = m['series_id']
        old_status = m['status']
        print(f"\n[{i+1}/{len(targets)}] {sid} ({old_status})")
        print(f"  Wind: {m.get('wind_indicator', '(none)')[:100]}")

        # Get DB values
        db_map = get_db_values(conn, sid)
        if db_map:
            dates = sorted(db_map.keys())
            print(f"  DB: {len(db_map)} non-zero values, {dates[0]} → {dates[-1]}")
        else:
            print(f"  DB: ALL ZERO — no data to verify against")

        # Try queries
        result = try_queries(m, db_map, conn)

        if result is None:
            print(f"  ❌ Still no EDB data found (tried all strategies)")
            still_broken.append((m, None))
            results_by_status['still_no_result'].append(m)
            continue

        print(f"  ✓ EDB found via strategy '{result['tag']}': {result['edb_indicator']}")
        print(f"  EDB unit: {result.get('edb_unit', '?')}, index: {result.get('index_id', '?')}")
        print(f"  Data points: {result['n_points']}")

        if db_map and 'avg_error' in result:
            print(f"  Overlap: {result['overlap']}, avg_error: {result['avg_error']}%, factor: {result.get('factor', 1):.2f}")
            if result['samples']:
                for d, dv, ev, pct in result['samples'][-3:]:
                    print(f"    {d}: DB={dv} vs EDB={ev} ({pct}%)")

            if result['avg_error'] <= 5:
                print(f"  ✅ NEWLY FIXED! (was {old_status})")
                newly_fixed.append((m, result))
                # Update mapping
                m['status'] = 'verified_with_transform'
                m['transform'] = [f"unit_div_{result['factor']:.0f}"] if abs(result['factor'] - 1) > 0.01 else []
                m['verify_details'] = {
                    'overlap_points': result['overlap'],
                    'avg_diff_pct': result['avg_error'],
                    'unit_factor': result['factor'],
                    'transform': m['transform'],
                    'samples': [(d, f"{dv:.4f}", f"{ev:.4f}") for d, dv, ev, pct in result['samples'][-3:]],
                    'edb_indicator': result['edb_indicator'],
                    'edb_unit': result.get('edb_unit', ''),
                    'index_id': result.get('index_id', ''),
                    'note': f'Fixed by re-test with strategy: {result["tag"]} — query="{result["query"]}"',
                    'retest_fix': True,
                }
                m['verified_at'] = datetime.now().isoformat()
                m['verify_note'] = f'Re-test fix: {result["tag"]} → {result["edb_indicator"]}'
            elif result['avg_error'] <= 15:
                print(f"  ⚠️ Close but not exact (avg_error={result['avg_error']}%)")
                still_broken.append((m, result))
                results_by_status['close_match'].append(m)
            else:
                print(f"  ❌ Poor match (avg_error={result['avg_error']}%)")
                still_broken.append((m, result))
                results_by_status['poor_match'].append(m)
        else:
            if db_map:
                print(f"  ❌ EDB data found but no overlap with DB")
                still_broken.append((m, result))
                results_by_status['no_overlap'].append(m)
            else:
                print(f"  ⚠️ EDB data found but DB has no data to verify")
                still_broken.append((m, result))
                results_by_status['db_no_data'].append(m)

        time.sleep(0.2)

    # Save updated mappings
    with open('config/wind_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"RE-TEST RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"  ✅ Newly fixed:          {len(newly_fixed)}")
    print(f"  ⚠️ Close match (<15%):   {len(results_by_status['close_match'])}")
    print(f"  ❌ Poor match:           {len(results_by_status['poor_match'])}")
    print(f"  ❌ Still no EDB data:    {len(results_by_status['still_no_result'])}")
    print(f"  🔍 No overlap:           {len(results_by_status['no_overlap'])}")
    print(f"  ⚪ DB has no data:        {len(results_by_status['db_no_data'])}")

    if newly_fixed:
        print(f"\n✅ NEWLY FIXED:")
        for m, r in newly_fixed:
            print(f"  {m['series_id']} ({m['status']}): {m['wind_indicator'][:80]}")
            print(f"    → {r['edb_indicator']} (strategy: {r['tag']})")

    print(f"\nSaved: config/wind_mapping.json")
    conn.close()

if __name__ == '__main__':
    main()
