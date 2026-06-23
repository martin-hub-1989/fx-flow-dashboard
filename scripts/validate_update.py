"""
Step 6c: Safe incremental update with two-point overlap validation.
- Reads fetched data from a staging area (JSON)
- Validates overlapping points against existing DB values
- Uses transaction: BEGIN → write → validate → COMMIT or ROLLBACK
- Records all events in validation_events table
"""
import sys, json, math, sqlite3
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (
    get_db, init_db, start_update_run, finish_update_run,
    insert_observations_batch, upsert_series
)
from safe_write import safe_write, ensure_revision_table


def load_fetched_data(staging_path):
    """Load data fetched by fetch_wind.py from staging file."""
    with open(staging_path, 'r', encoding='utf-8') as f:
        return json.load(f)


MIN_OVERLAP_POINTS = 2


def validate_overlap(conn, series_id, new_data, tolerance=1e-6):
    """
    Compare new data with existing DB values on overlapping dates.

    CONTRACT (NEXT_PHASE Loop 3):
    - Requires at least MIN_OVERLAP_POINTS (2) overlapping dates.
    - Every overlapping point must pass tolerance.
    - Non-finite fetched values (NaN/Inf) cause rejection.
    - Fewer than 2 valid overlaps → REJECT (never pass-through).

    Returns: (passed: bool, issues: list[dict])
    """
    issues = []

    if not new_data:
        return False, [{"date": None, "status": "fail",
                        "message": "empty fetched data — nothing to validate"}]

    # Reject non-finite values up front.
    for d, v in new_data.items():
        if v is None or (isinstance(v, float) and not math.isfinite(v)):
            return False, [{"date": d, "status": "fail",
                            "database_value": None, "fetched_value": v,
                            "difference": None, "relative_difference": None,
                            "tolerance": tolerance,
                            "message": f"non-finite or null fetched value at {d}"}]

    overlap_dates = list(new_data.keys())
    placeholders = ','.join('?' for _ in overlap_dates)
    existing = conn.execute(
        f"SELECT date, value FROM observations WHERE series_id=? AND date IN ({placeholders})",
        [series_id] + overlap_dates
    ).fetchall()
    existing_map = {}
    for r in existing:
        d = r['date'] if hasattr(r, 'keys') else r[0]
        v = r['value'] if hasattr(r, 'keys') else r[1]
        existing_map[d] = v

    overlap_count = 0
    for d, new_val in sorted(new_data.items()):
        old_val = existing_map.get(d)
        if old_val is None:
            continue  # new date, not an overlap point
        overlap_count += 1
        diff = abs(new_val - old_val)
        rel_diff = diff / abs(old_val) if abs(old_val) > 1e-9 else diff
        passed = diff <= tolerance or rel_diff <= tolerance
        issue = {
            "date": d,
            "database_value": old_val,
            "fetched_value": new_val,
            "difference": diff,
            "relative_difference": rel_diff,
            "tolerance": tolerance,
            "status": "pass" if passed else "fail",
        }
        if not passed:
            issue["message"] = (
                f"Overlap FAILED at {d}: db={old_val}, fetched={new_val}, "
                f"diff={diff:.6g}, rel={rel_diff:.6g}, tol={tolerance:.6g}"
            )
        issues.append(issue)

    # Hard gate: need at least 2 overlapping points.
    if overlap_count < MIN_OVERLAP_POINTS:
        issues.append({
            "date": None, "status": "fail",
            "message": f"insufficient overlap: {overlap_count} point(s), "
                       f"need >= {MIN_OVERLAP_POINTS}",
        })
        return False, issues

    # Every overlap must pass.
    failing = sum(1 for i in issues if i["status"] == "fail")
    if failing > 0:
        return False, issues

    return True, issues


def apply_update(conn, run_id, plan_entry, new_data):
    """
    Apply an incremental update for a single series.
    Uses a SAVEPOINT for per-series rollback capability.
    Safe write: new=INSERT, unchanged=skip, revision=audit (no overwrite).
    Returns: (success, message, stats_dict)
    """
    series_id = plan_entry["series_id"]
    tolerance = plan_entry.get("tolerance", 1e-6)
    sp = _sp_name(series_id)

    conn.execute(f"SAVEPOINT {sp}")
    try:
        # 1. Validate overlap (>=2 points enforced inside).
        passed, issues = validate_overlap(conn, series_id, new_data, tolerance)

        # 2. Record validation events.
        for issue in issues:
            conn.execute("""
                INSERT INTO validation_events
                (run_id, series_id, date, database_value, fetched_value,
                 difference, tolerance, status, message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, series_id, issue.get("date"),
                issue.get("database_value"), issue.get("fetched_value"),
                issue.get("difference"), tolerance,
                issue.get("status"), issue.get("message", "")
            ))

        if not passed:
            _safe_rollback(conn, sp)
            fail = [i for i in issues if i.get("status") == "fail"]
            msg = fail[0].get("message", "overlap validation failed") if fail else "overlap validation failed"
            return False, msg, {"new": 0, "unchanged": 0, "revision": 0}

        # 3. Safe write (counts computed before write inside safe_write).
        stats = safe_write(conn, series_id, new_data, run_id=run_id, source="wind_mcp")

        _safe_release(conn, sp)
        return True, f"new={stats['new']} unchanged={stats['unchanged']} revision={stats['revision']}", stats

    except Exception as e:
        _safe_rollback(conn, sp)
        return False, f"Exception: {str(e)}", {"new": 0, "unchanged": 0, "revision": 0}


def _sp_name(series_id):
    """Safe SAVEPOINT identifier (alnum + underscore only)."""
    import re
    return "sp_" + re.sub(r"[^A-Za-z0-9]", "_", series_id)


def _safe_rollback(conn, sp):
    """ROLLBACK TO a savepoint if it exists; never raise."""
    try:
        conn.execute(f"ROLLBACK TO {sp}")
        conn.execute(f"RELEASE {sp}")
    except sqlite3.OperationalError:
        pass


def _safe_release(conn, sp):
    """RELEASE a savepoint if it exists; never raise."""
    try:
        conn.execute(f"RELEASE {sp}")
    except sqlite3.OperationalError:
        pass


def process_update(conn, run_id, plan_entries, fetched_data_by_series):
    """
    Process a batch of updates. Each series updates independently.
    One series failing does not block others.
    new/revised counts come from safe_write (computed before write).
    """
    results = {
        "successful": [],
        "failed": [],
        "total_new_observations": 0,
        "total_revised_observations": 0,
        "validation_events": 0,
    }

    for entry in plan_entries:
        sid = entry["series_id"]
        if sid not in fetched_data_by_series:
            results["failed"].append({"series_id": sid, "reason": "No fetched data available"})
            continue
        new_data = fetched_data_by_series[sid]
        if not new_data:
            continue

        success, message, stats = apply_update(conn, run_id, entry, new_data)
        if success:
            results["successful"].append(sid)
            results["total_new_observations"] += stats.get("new", 0)
            results["total_revised_observations"] += stats.get("revision", 0)
        else:
            results["failed"].append({"series_id": sid, "reason": message})

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate and apply incremental updates")
    parser.add_argument("--staging", default="data/staging_fetched.json",
                       help="Path to staging file with fetched data")
    parser.add_argument("--dry-run", action="store_true",
                       help="Validate only, don't write to DB")
    args = parser.parse_args()

    staging_path = Path(args.staging)
    if not staging_path.exists():
        print(f"Staging file not found: {staging_path}")
        print("Run fetch_wind.py first to create the staging file.")
        print("For now, you can create a test staging file to validate the pipeline.")
        return 1

    conn = get_db()
    init_db(conn)
    ensure_revision_table(conn)

    # Load data
    fetched = load_fetched_data(staging_path)
    fetched_by_series = fetched.get("series_data", {})

    # Load plan
    plan_path = Path('config/update_plan.json')
    if plan_path.exists():
        with open(plan_path, 'r', encoding='utf-8') as f:
            plan = json.load(f)
    else:
        print("No update plan found. Run build_update_plan.py first.")
        return 1

    run_id = start_update_run(conn, len(plan))

    print(f"Processing {len(plan)} series from update plan...")
    print(f"Fetched data available for {len(fetched_by_series)} series")

    if args.dry_run:
        print("DRY RUN — no changes will be committed")
        for entry in plan[:5]:
            sid = entry['series_id']
            new_data = fetched_by_series.get(sid, {})
            passed, issues = validate_overlap(conn, sid, new_data)
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status} {sid}: {len(issues)} overlap points checked")
        conn.rollback()
    else:
        results = process_update(conn, run_id, plan, fetched_by_series)
        conn.commit()

        finish_update_run(
            conn, run_id, "completed",
            successful=len(results["successful"]),
            failed=len(results["failed"]),
            new_obs=results["total_new_observations"],
            revised_obs=results["total_revised_observations"],
            error_summary=str(results["failed"][:3]) if results["failed"] else ""
        )

        print(f"\nUpdate complete:")
        print(f"  Successful: {len(results['successful'])} series")
        print(f"  Failed: {len(results['failed'])} series")
        print(f"  New observations: {results['total_new_observations']}")
        print(f"  Revised observations: {results['total_revised_observations']}")
        print(f"  Validation events: {results['validation_events']}")

    conn.close()


if __name__ == "__main__":
    main()
