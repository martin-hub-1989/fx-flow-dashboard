import json

with open('.inspection/deep_inventory.json', 'r') as f:
    data = json.load(f)

for sheet_name, r in data.items():
    if 'error' in r:
        continue
    sep = "=" * 80
    print(f"\n{sep}")
    print(f"Sheet: {sheet_name}  (rows={r['max_row']}, cols={r['max_column']}, formulas={r['cell_stats']['formula']})")
    print(f"Date columns: {r['date_columns']}")
    print(f"Data regions: {r['data_regions']}")
    print(f"Charts: {len(r['charts'])}")
    print(f"\nColumn headers (first 35 cols):")
    headers = r.get('column_headers', {})
    sorted_headers = sorted(headers.items(), key=lambda x: (len(x[0]), x[0]))
    for col_letter, info in sorted_headers[:35]:
        formula_mark = ' [F]' if info.get('has_formulas') else ''
        header_text = info['header'][:100] if info.get('header') else '(empty)'
        print(f"  {col_letter} (row {info['row']}): {header_text}{formula_mark} (n={info['nonempty_count']})")

    # External refs
    refs = r.get('external_refs_sample', [])
    if refs:
        print(f"\nExternal refs (first 5):")
        for ref in refs[:5]:
            print(f"  {ref[:150]}")
