"""
Step 6a: Build incremental update plan from wind_mapping.json.

PRODUCTION CONTRACT (NEXT_PHASE Loop 1):
- Skips metadata rows (no series_id).
- Only mappings with wind_verified=True AND status in
  (verified_exact, verified_unit_transform) enter the plan.
- validation_dates are the LAST TWO ACTUAL observation dates from the DB
  (queried directly, never guessed by date subtraction).
- Series with fewer than 2 real observations are excluded.
- Deterministic: identical inputs produce an identical plan.
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import get_db

# Only these statuses are production-eligible, and only when wind_verified=True.
PRODUCTION_STATUSES = ("verified_exact", "verified_unit_transform")


def get_last_two_dates(conn, series_id):
    """Return the last two actual observation dates (ascending) or None.

    Direct DB query — never guessed by arithmetic.
    """
    rows = conn.execute(
        "SELECT date FROM observations WHERE series_id=? AND value IS NOT NULL "
        "ORDER BY date DESC LIMIT 2",
        (series_id,)
    ).fetchall()
    if len(rows) < 2:
        return None
    d1 = rows[0][0] if not hasattr(rows[0], "keys") else rows[0]["date"]
    d2 = rows[1][0] if not hasattr(rows[1], "keys") else rows[1]["date"]
    dates = sorted([d1[:10], d2[:10]])
    if dates[0] == dates[1]:
        return None  # duplicate dates — refuse
    return dates


def build_plan(conn, mapping_path="config/wind_mapping.json"):
    """Generate a reproducible incremental update plan from wind_mapping.json."""
    with open(mapping_path, "r", encoding="utf-8") as f:
        mappings = json.load(f)

    plan = []
    for m in mappings:
        # Skip metadata / malformed rows safely.
        if not isinstance(m, dict) or "series_id" not in m or "_metadata" in m:
            continue

        sid = m["series_id"]
        status = m.get("status", "mapping_pending")

        # Production gate: must be wind-verified AND a production status.
        if m.get("wind_verified") is not True:
            continue
        if status not in PRODUCTION_STATUSES:
            continue

        # Validation dates = last two ACTUAL DB observation dates.
        val_dates = get_last_two_dates(conn, sid)
        if not val_dates:
            continue

        row = conn.execute(
            "SELECT frequency FROM series WHERE series_id=?", (sid,)
        ).fetchone()
        db_freq = (row["frequency"] if row and hasattr(row, "keys") else
                   (row[0] if row else None))
        frequency = m.get("frequency") or db_freq or "monthly"

        entry = {
            "series_id": sid,
            "display_name": m.get("display_name", ""),
            "wind_indicator": m.get("wind_indicator", ""),
            "module": m.get("module", ""),
            "last_date": val_dates[-1],
            "fetch_start_date": val_dates[0],
            "validation_dates": val_dates,
            "wind_method": m.get("wind_method", "economic_data.get_economic_data"),
            "query": m.get("wind_indicator", ""),
            "frequency": frequency,
            "unit": m.get("unit", ""),
            "transform": m.get("transform") or [],
            "tolerance": m.get("tolerance", 1e-6),
            # Exact Wind closure fields (Loop 6) for precise fetch.
            "wind_query_exact": m.get("wind_query_exact", ""),
            "wind_code": m.get("wind_code", ""),
            "wind_name": m.get("wind_name", ""),
        }
        plan.append(entry)

    # Deterministic ordering.
    plan.sort(key=lambda e: e["series_id"])
    return plan


def main():
    conn = get_db()
    print("Building incremental update plan (production contract)...")
    plan = build_plan(conn)

    plan_path = Path("config/update_plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    by_module = {}
    for e in plan:
        by_module[e["module"]] = by_module.get(e["module"], 0) + 1

    print(f"Update plan: {len(plan)} production-eligible series")
    for mod, cnt in sorted(by_module.items()):
        print(f"  {mod}: {cnt}")

    if not plan:
        print("\n0 production-eligible series — no mapping has wind_verified=true.")
        print("This is correct until real Wind MCP verification closes the loop (Loop 6).")

    conn.close()


if __name__ == "__main__":
    main()
