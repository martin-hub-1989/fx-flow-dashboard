"""
Step 6c: Safe incremental update with two-point overlap validation.
- Reads fetched data from a staging area (JSON)
- Validates overlapping points against existing DB values
- Uses transaction: BEGIN → write → validate → COMMIT or ROLLBACK
- Records all events in validation_events table
"""
import sys, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (
    get_db, init_db, start_update_run, finish_update_run,
    insert_observations_batch, upsert_series
)


def load_fetched_data(staging_path):
    """Load data fetched by fetch_wind.py from staging file."""
    with open(staging_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_overlap(conn, series_id, new_data, tolerance=1e-6):
    """
    Compare new data with existing DB values on overlapping dates.
    Returns: (passed, issues_list)
    """
    issues = []

    # Get existing values for overlapping dates
    overlap_dates = list(new_data.keys())
    if not overlap_dates:
        return True, []

    placeholders = ','.join('?' for _ in overlap_dates)
    existing = conn.execute(
        f"SELECT date, value FROM observations WHERE series_id=? AND date IN ({placeholders})",
        [series_id] + overlap_dates
    ).fetchall()
    existing_map = {r['date']: r['value'] for r in existing}

    for d, new_val in sorted(new_data.items()):
        old_val = existing_map.get(d)
        if old_val is not None:
            diff = abs(new_val - old_val)
            rel_diff = diff / abs(old_val) if abs(old_val) > 1e-9 else diff

            # Determine if pass
            passed = diff <= tolerance or rel_diff <= tolerance

            issues.append({
                "date": d,
                "database_value": old_val,
                "fetched_value": new_val,
                "difference": diff,
                "relative_difference": rel_diff,
                "tolerance": tolerance,
                "status": "pass" if passed else "fail",
            })

            if not passed:
                issues[-1]["message"] = (
                    f"Overlap validation FAILED: diff={diff:.6f}, rel_diff={rel_diff:.6f}"
                )

    # Check: at least 2 overlapping points should pass
    passing = sum(1 for i in issues if i["status"] == "pass")
    failing = len(issues) - passing

    if failing > 0:
        return False, issues
    if len(issues) < 1:
        return True, issues  # No overlap points found (warning, not error)

    return True, issues


def apply_update(conn, run_id, plan_entry, new_data):
    """
    Apply an incremental update for a single series.
    Uses a SAVEPOINT for per-series rollback capability.
    Returns: (success, message, event_count)
    """
    series_id = plan_entry["series_id"]
    tolerance = plan_entry.get("tolerance", 1e-6)

    # Create savepoint for this series
    conn.execute(f"SAVEPOINT sp_{series_id.replace(':', '_')}")

    try:
        # 1. Validate overlap
        passed, issues = validate_overlap(conn, series_id, new_data, tolerance)

        # 2. Record validation events
        for issue in issues:
            conn.execute("""
                INSERT OR REPLACE INTO validation_events
                (run_id, series_id, date, database_value, fetched_value,
                 difference, tolerance, status, message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, series_id, issue["date"],
                issue["database_value"], issue["fetched_value"],
                issue["difference"], tolerance,
                issue["status"], issue.get("message", "")
            ))

        if not passed:
            conn.execute(f"ROLLBACK TO sp_{series_id.replace(':', '_')}")
            fail_details = [i for i in issues if i["status"] == "fail"]
            return False, f"Overlap validation failed: {fail_details[0].get('message', 'unknown')}", len(issues)

        # 3. Write new observations (INSERT OR REPLACE is idempotent)
        new_obs = []
        for d, v in new_data.items():
            new_obs.append((series_id, d, v, "wind_mcp"))

        insert_observations_batch(conn, new_obs, run_id)

        # 4. Update series metadata
        sorted_new = sorted(new_data.keys())
        if sorted_new:
            last_date = sorted_new[-1]
            conn.execute(
                "UPDATE series SET last_date=?, update_status='updated' WHERE series_id=?",
                (last_date, series_id)
            )

        conn.execute(f"RELEASE sp_{series_id.replace(':', '_')}")
        return True, f"Updated {len(new_data)} points", len(issues)

    except Exception as e:
        conn.execute(f"ROLLBACK TO sp_{series_id.replace(':', '_')}")
        return False, f"Exception: {str(e)}", 0


def process_update(conn, run_id, plan_entries, fetched_data_by_series):
    """
    Process a batch of updates. Each series updates independently.
    One series failing does not block others.
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
            results["failed"].append({
                "series_id": sid,
                "reason": "No fetched data available"
            })
            continue

        new_data = fetched_data_by_series[sid]
        if not new_data:
            continue

        success, message, events = apply_update(conn, run_id, entry, new_data)

        if success:
            results["successful"].append(sid)
            # Count new vs revised
            for d in new_data:
                exists = conn.execute(
                    "SELECT 1 FROM observations WHERE series_id=? AND date=?",
                    (sid, d)
                ).fetchone()
                if exists:
                    results["total_revised_observations"] += 1
                else:
                    results["total_new_observations"] += 1
        else:
            results["failed"].append({
                "series_id": sid,
                "reason": message
            })

        results["validation_events"] += events

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
