"""
safe_write.py — Safe observation writes with revision audit.

Per NEXT_PHASE_EXECUTION_LOOP.md Loop 4:
- Classify fetched data into new / unchanged / revision BEFORE writing.
- New observations are INSERTed.
- Unchanged overlaps are left alone (not rewritten).
- Historical revisions are recorded in observation_revisions and NOT
  auto-overwritten (review_status='pending'). The production raw path never
  calls a blanket INSERT OR REPLACE.
"""
from datetime import datetime

REVISION_DDL = """
CREATE TABLE IF NOT EXISTS observation_revisions (
    revision_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id               TEXT,
    series_id            TEXT,
    date                 TEXT,
    old_value            REAL,
    new_value            REAL,
    difference           REAL,
    relative_difference  REAL,
    source               TEXT,
    source_vintage       TEXT,
    detected_at          TEXT,
    review_status        TEXT DEFAULT 'pending',
    reviewed_at          TEXT,
    review_note          TEXT
);
CREATE INDEX IF NOT EXISTS idx_rev_series_date
    ON observation_revisions(series_id, date);
"""

UNCHANGED_TOL = 1e-9


def ensure_revision_table(conn):
    conn.executescript(REVISION_DDL)
    conn.commit()


def classify(conn, series_id, fetched, tol=UNCHANGED_TOL):
    """Split fetched {date: value} into new / unchanged / revision vs DB.

    Computed BEFORE any write so counts are accurate.
    """
    dates = list(fetched.keys())
    existing = {}
    if dates:
        ph = ",".join("?" for _ in dates)
        rows = conn.execute(
            f"SELECT date, value FROM observations WHERE series_id=? AND date IN ({ph})",
            [series_id] + dates
        ).fetchall()
        for r in rows:
            d = r["date"] if hasattr(r, "keys") else r[0]
            v = r["value"] if hasattr(r, "keys") else r[1]
            existing[d] = v

    new, unchanged, revision = {}, {}, {}
    for d, v in fetched.items():
        if d not in existing:
            new[d] = v
        else:
            old = existing[d]
            if old is None or abs(v - old) > tol:
                revision[d] = (old, v)
            else:
                unchanged[d] = v
    return {"new": new, "unchanged": unchanged, "revision": revision}


def safe_write(conn, series_id, fetched, run_id, source="wind_mcp",
               source_vintage=None):
    """Write fetched data safely.

    Returns dict with counts: new, unchanged, revision.
    - new: INSERT
    - unchanged: skip
    - revision: record in observation_revisions (pending), do NOT overwrite
    """
    ensure_revision_table(conn)
    cls = classify(conn, series_id, fetched)
    now = datetime.now().isoformat()

    # New observations: plain INSERT (no overwrite path).
    for d, v in cls["new"].items():
        conn.execute(
            "INSERT INTO observations (series_id, date, value, source, imported_at, run_id) "
            "VALUES (?,?,?,?,?,?)",
            (series_id, d, v, source, now, run_id)
        )

    # Revisions: audit only, do not touch observations.
    for d, (old, new_v) in cls["revision"].items():
        diff = new_v - old if old is not None else None
        rel = (abs(diff) / abs(old)) if (old not in (None, 0)) else None
        conn.execute(
            "INSERT INTO observation_revisions "
            "(run_id, series_id, date, old_value, new_value, difference, "
            " relative_difference, source, source_vintage, detected_at, review_status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,'pending')",
            (run_id, series_id, d, old, new_v, diff, rel, source, source_vintage, now)
        )

    # Update series last_date if new observations extended the series.
    if cls["new"]:
        new_last = max(cls["new"].keys())
        row = conn.execute("SELECT last_date FROM series WHERE series_id=?", (series_id,)).fetchone()
        cur_last = (row["last_date"] if row and hasattr(row, "keys") else (row[0] if row else None))
        if cur_last is None or new_last > cur_last:
            conn.execute("UPDATE series SET last_date=?, update_status='updated' WHERE series_id=?",
                         (new_last, series_id))

    return {
        "new": len(cls["new"]),
        "unchanged": len(cls["unchanged"]),
        "revision": len(cls["revision"]),
    }
