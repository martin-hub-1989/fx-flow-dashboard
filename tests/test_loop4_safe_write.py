"""
Loop 4 tests: safe write + revision audit.
Per NEXT_PHASE_EXECUTION_LOOP.md Loop 4.

- classify new / unchanged / revision before write
- new observations INSERT (not overwrite)
- unchanged overlap not rewritten
- historical revision goes to audit, NOT auto-overwrite
- new/revised counts computed BEFORE write
- observation_revisions table preserves old + new value
"""
import sys, sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import lib
import safe_write as SW


def make_conn(existing):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    lib.init_db(conn)
    SW.ensure_revision_table(conn)
    for sid, pts in existing.items():
        conn.execute("INSERT INTO series (series_id, display_name, module, series_type) VALUES (?,?,?,'raw')",
                     (sid, sid, "test"))
        for d, v in pts.items():
            conn.execute("INSERT INTO observations (series_id, date, value) VALUES (?,?,?)", (sid, d, v))
    conn.commit()
    return conn


def test_classify_new_unchanged_revision():
    conn = make_conn({"x:A": {"2026-01-31": 100.0, "2026-02-28": 200.0}})
    fetched = {
        "2026-01-31": 100.0,   # unchanged
        "2026-02-28": 250.0,   # revision (changed)
        "2026-03-31": 300.0,   # new
    }
    cls = SW.classify(conn, "x:A", fetched)
    assert set(cls["new"].keys()) == {"2026-03-31"}
    assert set(cls["unchanged"].keys()) == {"2026-01-31"}
    assert set(cls["revision"].keys()) == {"2026-02-28"}


def test_counts_before_write():
    conn = make_conn({"x:A": {"2026-01-31": 100.0, "2026-02-28": 200.0}})
    fetched = {"2026-02-28": 200.0, "2026-03-31": 300.0, "2026-04-30": 400.0}
    cls = SW.classify(conn, "x:A", fetched)
    assert len(cls["new"]) == 2      # Mar, Apr
    assert len(cls["unchanged"]) == 1  # Feb
    assert len(cls["revision"]) == 0


def test_new_observations_inserted():
    conn = make_conn({"x:A": {"2026-01-31": 100.0, "2026-02-28": 200.0}})
    SW.safe_write(conn, "x:A", {"2026-03-31": 300.0}, run_id="r1", source="wind_mcp")
    v = conn.execute("SELECT value FROM observations WHERE series_id='x:A' AND date='2026-03-31'").fetchone()[0]
    assert v == 300.0


def test_unchanged_not_rewritten():
    conn = make_conn({"x:A": {"2026-01-31": 100.0}})
    # capture imported_at after first insert (None here), write same value
    SW.safe_write(conn, "x:A", {"2026-01-31": 100.0}, run_id="r1", source="wind_mcp")
    # value still 100, no revision recorded
    revs = conn.execute("SELECT COUNT(*) FROM observation_revisions WHERE series_id='x:A'").fetchone()[0]
    assert revs == 0, "unchanged overlap must not create a revision"


def test_revision_not_auto_overwritten():
    conn = make_conn({"x:A": {"2026-01-31": 100.0}})
    SW.safe_write(conn, "x:A", {"2026-01-31": 175.0}, run_id="r1", source="wind_mcp")
    # original value preserved in observations (not silently overwritten)
    v = conn.execute("SELECT value FROM observations WHERE series_id='x:A' AND date='2026-01-31'").fetchone()[0]
    assert v == 100.0, "historical value must NOT be auto-overwritten"
    # revision recorded with old + new
    rev = conn.execute("SELECT old_value, new_value, review_status FROM observation_revisions "
                       "WHERE series_id='x:A' AND date='2026-01-31'").fetchone()
    assert rev is not None
    assert rev[0] == 100.0 and rev[1] == 175.0
    assert rev[2] == "pending"


def test_revision_table_schema():
    conn = make_conn({})
    cols = {r[1] for r in conn.execute("PRAGMA table_info(observation_revisions)")}
    for c in ["revision_id", "run_id", "series_id", "date", "old_value",
              "new_value", "difference", "relative_difference", "source",
              "source_vintage", "detected_at", "review_status",
              "reviewed_at", "review_note"]:
        assert c in cols, f"missing column {c}"
