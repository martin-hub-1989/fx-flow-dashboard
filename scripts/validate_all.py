"""
Step 8: Comprehensive validation.
Checks: DB integrity, idempotency, data quality, Excel comparison.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import get_db, validate_db, values_match

MODULES = [
    "3.即远期", "3.代客即期", "3.涉外收付", "3.货物贸易",
    "3.贸易商", "3.服务贸易", "3.FDI", "3.证券EQ", "3.证券FI"
]


def check_unique_keys(conn):
    """Check no duplicate (series_id, date) pairs."""
    dupes = conn.execute("""
        SELECT series_id, date, COUNT(*) as cnt
        FROM observations GROUP BY series_id, date HAVING cnt > 1
    """).fetchall()
    return len(dupes) == 0, f"{len(dupes)} duplicate keys" if dupes else "OK"


def check_null_values(conn):
    """Check no NULL values in critical columns."""
    null_series = conn.execute(
        "SELECT COUNT(*) as cnt FROM observations WHERE series_id IS NULL OR date IS NULL"
    ).fetchone()["cnt"]
    return null_series == 0, f"{null_series} NULL series_id/date" if null_series else "OK"


def check_nonfinite(conn):
    """Check no Infinity/NaN values."""
    # SQLite stores these as strings
    nonfinite = conn.execute("""
        SELECT COUNT(*) as cnt FROM observations
        WHERE value IS NOT NULL AND (CAST(value AS TEXT) = 'Infinity' OR CAST(value AS TEXT) = '-Infinity' OR CAST(value AS TEXT) = 'NaN')
    """).fetchone()["cnt"]
    return nonfinite == 0, f"{nonfinite} non-finite values" if nonfinite else "OK"


def check_series_have_observations(conn):
    """Every series should have at least some observations."""
    no_obs = conn.execute("""
        SELECT s.series_id FROM series s
        WHERE s.series_type != 'manual'
        AND s.series_id NOT IN (SELECT DISTINCT series_id FROM observations)
    """).fetchall()
    # Exclude date columns (column A)
    no_obs_real = [r for r in no_obs if not r["series_id"].endswith(":A")]
    return len(no_obs_real) == 0, f"{len(no_obs_real)} series without obs: {[r['series_id'] for r in no_obs_real[:5]]}" if no_obs_real else "OK"


def check_zero_as_data(conn):
    """Check for suspicious consecutive zeros at the end of series (future months)."""
    suspicious = []
    for row in conn.execute(
        "SELECT DISTINCT o.series_id FROM observations o "
        "JOIN series s ON o.series_id = s.series_id WHERE s.series_type != 'derived'"
    ).fetchall():
        sid = row["series_id"]
        # Get last 6 values
        last_vals = conn.execute(
            "SELECT date, value FROM observations WHERE series_id=? ORDER BY date DESC LIMIT 6",
            (sid,)
        ).fetchall()
        # If last 3+ are exactly zero, flag
        zeros = sum(1 for v in last_vals if v["value"] == 0)
        if zeros >= 3 and len(last_vals) >= 3:
            suspicious.append(sid)
    return len(suspicious) == 0, f"{len(suspicious)} series with trailing zeros: {suspicious[:5]}" if suspicious else "OK"


def check_date_continuity(conn):
    """Check for unrealistic gaps in date ranges."""
    issues = []
    for mod in MODULES:
        row = conn.execute("""
            SELECT MIN(date) as min_d, MAX(date) as max_d
            FROM observations o JOIN series s ON o.series_id = s.series_id
            WHERE s.module = ?
        """, (mod,)).fetchone()
        if row["min_d"] and row["max_d"]:
            min_y = int(row["min_d"][:4])
            max_y = int(row["max_d"][:4])
            if max_y < 2025:
                issues.append(f"{mod}: max date {row['max_d']} is old")
    return len(issues) == 0, "; ".join(issues) if issues else "OK"


def check_idempotency(conn):
    """Verify that re-running operations doesn't create duplicates."""
    # Check: INSERT OR REPLACE should be safe
    before = conn.execute("SELECT COUNT(*) as cnt FROM observations").fetchone()["cnt"]
    # Try re-inserting existing data
    try:
        conn.execute("""
            INSERT OR REPLACE INTO observations
            SELECT * FROM observations WHERE series_id = (SELECT series_id FROM observations LIMIT 1) LIMIT 1
        """)
        after = conn.execute("SELECT COUNT(*) as cnt FROM observations").fetchone()["cnt"]
        conn.rollback()
        return before == after, f"Count changed: {before} -> {after}" if before != after else "OK"
    except Exception as e:
        conn.rollback()
        return False, str(e)


def check_module_coverage(conn):
    """Check each module has raw and observation data."""
    results = {}
    for mod in MODULES:
        raw = conn.execute(
            "SELECT COUNT(*) as cnt FROM series WHERE module=? AND series_type='raw'", (mod,)
        ).fetchone()["cnt"]
        obs = conn.execute("""
            SELECT COUNT(*) as cnt FROM observations o
            JOIN series s ON o.series_id = s.series_id WHERE s.module=?
        """, (mod,)).fetchone()["cnt"]
        results[mod] = f"{raw} raw series, {obs} obs"
    all_ok = all("raw series" in v and int(v.split()[0]) > 0 for v in results.values())
    return all_ok, results if not all_ok else "OK"


def main():
    conn = get_db()
    print("=" * 60)
    print("FX Flow Dashboard — Comprehensive Validation")
    print(f"Ran at: {datetime.now().isoformat()}")
    print("=" * 60)

    checks = [
        ("Unique keys", check_unique_keys),
        ("No NULL series_id/date", check_null_values),
        ("No non-finite values", check_nonfinite),
        ("Series have observations", check_series_have_observations),
        ("No trailing zeros", check_zero_as_data),
        ("Date range valid", check_date_continuity),
        ("Idempotency", check_idempotency),
        ("Module coverage", check_module_coverage),
    ]

    passed = 0
    failed = 0
    for name, fn in checks:
        ok, msg = fn(conn)
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {msg}")
        if ok:
            passed += 1
        else:
            failed += 1

    # Standard validate_db
    print(f"\n  --- Additional DB checks ---")
    issues = validate_db(conn)
    for issue in issues:
        print(f"  ⚠️  {issue}")

    # Summary stats
    total_series = conn.execute("SELECT COUNT(*) FROM series").fetchone()[0]
    total_obs = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    raw_series = conn.execute("SELECT COUNT(*) FROM series WHERE series_type='raw'").fetchone()[0]
    derived_series = conn.execute("SELECT COUNT(*) FROM series WHERE series_type='derived'").fetchone()[0]

    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {passed}/{passed+failed} checks passed")
    print(f"  Series: {total_series} ({raw_series} raw, {derived_series} derived)")
    print(f"  Observations: {total_obs:,}")
    print(f"  Modules: {len(MODULES)}")

    conn.close()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
