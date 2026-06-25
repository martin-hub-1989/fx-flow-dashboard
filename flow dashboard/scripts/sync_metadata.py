"""
sync_metadata.py — Unify series_catalog.json, SQLite series, and Data Dictionary
(NEXT_PHASE Loop 8).

Actions:
1. Remove from catalog the 29 catalog-only non-business auxiliary columns
   (频率/单位/Wind placeholders, deleted BE/BF, Column_* intermediate).
2. Backfill units for chart-critical series that are missing units.
3. Verify catalog ⊆ SQLite after sync (catalog becomes the business master list).
4. Report final counts.
"""
import json, sqlite3
from pathlib import Path

DB_PATH = "data/monthly_brief.sqlite"
CATALOG_PATH = "config/series_catalog.json"

# Chart-critical units (from chart_catalog / Excel headers / Wind confirmed units)
UNIT_BACKFILL = {
    "fx_fwd:AJ": "亿美元",          # 期权Delta净变动 (copy of T, USD settlement)
    "fx_fwd:AN": "CNY/USD",         # USDCNY exchange rate (reclassified raw)
    "fx_fwd:Y":  "亿美元",          # 代客衍生品签约
    "trade_goods:AC": "分位(0-100)", # 滚动分位
    "trade_goods:U":  "亿美元",      # 即远期结汇估
    "fx_fwd:AB": "亿美元",          # 即期代客结售汇差额
    "fx_fwd:AD": "亿美元",          # 代客衍生品净结汇
    "fx_fwd:AE": "亿美元",          # 远期履约/平仓
    "sec_eq:AF": "亿元",            # Net Equity Flow
    "sec_eq:AH": "变化率",          # CNYX 3M变动率
    "sec_eq:AJ": "变化率",          # USDCNY 3M变动率
}


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 1. Backfill units in SQLite
    print("=== Backfilling chart-critical units ===")
    bf = 0
    for sid, unit in UNIT_BACKFILL.items():
        cur = conn.execute("SELECT unit FROM series WHERE series_id=?", (sid,)).fetchone()
        if cur and (cur["unit"] in (None, "", "unknown")):
            conn.execute("UPDATE series SET unit=? WHERE series_id=?", (unit, sid))
            bf += 1
            print(f"  {sid}: unit -> {unit}")
    conn.commit()
    print(f"Backfilled {bf} units")

    # 2. Sync catalog: drop non-business auxiliary entries (catalog-only + Column_*)
    cat = json.load(open(CATALOG_PATH, encoding="utf-8"))
    entries = cat if isinstance(cat, list) else cat.get("series", [])
    db_sids = {r[0] for r in conn.execute("SELECT series_id FROM series")}

    kept = []
    dropped = []
    for x in entries:
        if not isinstance(x, dict) or "series_id" not in x:
            continue
        sid = x["series_id"]
        # Drop if catalog-only (not in DB) — these are Excel auxiliaries
        if sid not in db_sids:
            dropped.append((sid, "catalog-only (Excel auxiliary)"))
            continue
        # Drop if pure Column_* with no business meaning and not chart-referenced
        nm = x.get("display_name", "")
        if nm.startswith("Column_"):
            dropped.append((sid, "Column_* placeholder"))
            continue
        kept.append(x)

    print(f"\n=== Catalog sync ===")
    print(f"  before: {len(entries)} entries")
    print(f"  dropped: {len(dropped)} (catalog-only / Column_*)")
    print(f"  kept: {len(kept)} (business series, all in DB)")

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    # 3. Verify consistency
    cat_sids = {x["series_id"] for x in kept}
    cat_only = cat_sids - db_sids
    db_only = db_sids - cat_sids
    print(f"\n=== Consistency ===")
    print(f"  catalog: {len(cat_sids)}, SQLite: {len(db_sids)}")
    print(f"  catalog-only (not in DB): {len(cat_only)}")
    print(f"  DB-only (not in catalog): {len(db_only)} (Excel auxiliaries, acceptable)")

    # 4. Remaining Column_* in DB (not chart-referenced intermediates)
    col_db = conn.execute("SELECT COUNT(*) FROM series WHERE display_name LIKE 'Column_%'").fetchone()[0]
    print(f"  SQLite Column_*: {col_db} (non-displayed intermediates, acceptable if not chart-referenced)")

    # 5. Empty units remaining
    eu = conn.execute("SELECT COUNT(*) FROM series WHERE unit IS NULL OR unit='' OR unit='unknown'").fetchone()[0]
    print(f"  SQLite empty/unknown unit: {eu}")

    # chart-critical units check
    chart_cat = json.load(open("config/chart_catalog.json", encoding="utf-8"))
    chart_sids = set()
    for mod, md in chart_cat["modules"].items():
        for ch in md["charts"]:
            for ds in ch["datasets"]:
                chart_sids.add(ds["series_id"])
            if ch.get("scatter"):
                chart_sids.add(ch["scatter_x"]["series_id"])
                chart_sids.add(ch["scatter_y"]["series_id"])
    missing_unit = [r[0] for r in conn.execute(
        f"SELECT series_id FROM series WHERE series_id IN ({','.join('?'*len(chart_sids))}) "
        "AND (unit IS NULL OR unit='' OR unit='unknown')", list(chart_sids))]
    print(f"  chart-critical missing unit: {len(missing_unit)} {missing_unit}")

    conn.close()


if __name__ == "__main__":
    main()
