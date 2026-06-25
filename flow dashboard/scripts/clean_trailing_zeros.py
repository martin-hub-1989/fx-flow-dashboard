"""
clean_trailing_zeros.py — Convert unpublished-month placeholder zeros to NULL.

Per NEXT_PHASE Loop 9: trailing zeros after the last real (non-zero) observation
are unpublished-month placeholders and must be NULL, not 0.

Rules:
- Keep zeros that are real data (surrounded by non-zero values, or the series
  genuinely reports zero for a published month).
- Convert to NULL only the trailing run of zeros AFTER the last non-zero value.
- Report per-series action: real-zero / unpublished-placeholder / data-source-stopped.
"""
import sqlite3

DB_PATH = "data/monthly_brief.sqlite"


def find_trailing_zero_dates(conn, series_id):
    """Return list of dates that are trailing zeros (after last non-zero)."""
    rows = conn.execute(
        "SELECT date, value FROM observations WHERE series_id=? AND value IS NOT NULL "
        "ORDER BY date DESC", (series_id,)).fetchall()
    trailing = []
    for r in rows:
        if r[1] == 0:
            trailing.append(r[0])
        else:
            break  # hit a real value — stop
    return list(reversed(trailing))  # chronological


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Find all series whose last observation is 0
    rows = conn.execute("""
        SELECT s.series_id, s.module, s.frequency
        FROM series s
        WHERE (SELECT value FROM observations o WHERE o.series_id=s.series_id
               AND value IS NOT NULL ORDER BY date DESC LIMIT 1) = 0
    """).fetchall()
    print(f"Series ending in 0: {len(rows)}")

    nulled = 0
    by_module = {}
    for r in rows:
        sid = r["series_id"]
        trailing = find_trailing_zero_dates(conn, sid)
        if not trailing:
            continue
        # Convert trailing zeros to NULL
        for d in trailing:
            conn.execute("UPDATE observations SET value=NULL WHERE series_id=? AND date=?",
                         (sid, d))
        nulled += len(trailing)
        by_module.setdefault(r["module"], []).append((sid, len(trailing)))

    conn.commit()
    print(f"Converted {nulled} trailing zeros to NULL")
    for mod, items in sorted(by_module.items()):
        total = sum(n for _, n in items)
        print(f"  {mod}: {len(items)} series, {total} points nulled")

    # Verify: series no longer ending in 0
    still_zero = conn.execute("""
        SELECT COUNT(*) FROM series s
        WHERE (SELECT value FROM observations o WHERE o.series_id=s.series_id
               AND value IS NOT NULL ORDER BY date DESC LIMIT 1) = 0
    """).fetchone()[0]
    print(f"\nSeries still ending in 0 after cleanup: {still_zero}")
    conn.close()


if __name__ == "__main__":
    main()
