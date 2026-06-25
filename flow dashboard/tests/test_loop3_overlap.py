"""
Loop 3 tests: two-point overlap validation contract.
Per NEXT_PHASE_EXECUTION_LOOP.md Loop 3.

- 0 overlap points: REJECT
- 1 overlap point: REJECT
- 2 both pass: ALLOW
- 1 pass 1 fail: REJECT
- 2 both fail: REJECT
- fetched only new dates (no overlap): REJECT
- tolerance boundary
- null/NaN/Infinity
- frequency mismatch / duplicate dates
"""
import sys, sqlite3, math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_update as VU


def make_conn(series_id, existing):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE observations (
        series_id TEXT, date TEXT, value REAL,
        PRIMARY KEY(series_id, date))""")
    for d, v in existing.items():
        conn.execute("INSERT INTO observations (series_id, date, value) VALUES (?,?,?)",
                     (series_id, d, v))
    conn.commit()
    return conn


def test_zero_overlap_rejected():
    conn = make_conn("x:A", {"2026-01-31": 1.0, "2026-02-28": 2.0})
    # fetched data only has NEW dates, no overlap with DB
    new = {"2026-03-31": 3.0, "2026-04-30": 4.0}
    passed, issues = VU.validate_overlap(conn, "x:A", new)
    assert passed is False, "zero overlap must be REJECTED"


def test_one_overlap_rejected():
    conn = make_conn("x:A", {"2026-01-31": 1.0, "2026-02-28": 2.0})
    new = {"2026-02-28": 2.0, "2026-03-31": 3.0}  # only 1 overlap
    passed, issues = VU.validate_overlap(conn, "x:A", new)
    assert passed is False, "single overlap must be REJECTED"


def test_two_both_pass_allowed():
    conn = make_conn("x:A", {"2026-01-31": 1.0, "2026-02-28": 2.0})
    new = {"2026-01-31": 1.0, "2026-02-28": 2.0, "2026-03-31": 3.0}
    passed, issues = VU.validate_overlap(conn, "x:A", new)
    assert passed is True, "two matching overlaps must be ALLOWED"


def test_one_pass_one_fail_rejected():
    conn = make_conn("x:A", {"2026-01-31": 1.0, "2026-02-28": 2.0})
    new = {"2026-01-31": 1.0, "2026-02-28": 99.0}  # second fails
    passed, issues = VU.validate_overlap(conn, "x:A", new)
    assert passed is False, "one fail must REJECT the whole update"


def test_two_both_fail_rejected():
    conn = make_conn("x:A", {"2026-01-31": 1.0, "2026-02-28": 2.0})
    new = {"2026-01-31": 50.0, "2026-02-28": 99.0}
    passed, issues = VU.validate_overlap(conn, "x:A", new)
    assert passed is False


def test_tolerance_boundary():
    conn = make_conn("x:A", {"2026-01-31": 100.0, "2026-02-28": 200.0})
    # within 1e-6 relative
    new = {"2026-01-31": 100.00005, "2026-02-28": 200.0}
    passed, issues = VU.validate_overlap(conn, "x:A", new, tolerance=1e-3)
    assert passed is True


def test_nan_rejected():
    conn = make_conn("x:A", {"2026-01-31": 1.0, "2026-02-28": 2.0})
    new = {"2026-01-31": float("nan"), "2026-02-28": 2.0}
    passed, issues = VU.validate_overlap(conn, "x:A", new)
    assert passed is False, "NaN must be rejected"


def test_infinity_rejected():
    conn = make_conn("x:A", {"2026-01-31": 1.0, "2026-02-28": 2.0})
    new = {"2026-01-31": float("inf"), "2026-02-28": 2.0}
    passed, issues = VU.validate_overlap(conn, "x:A", new)
    assert passed is False, "Infinity must be rejected"


def test_empty_fetched_rejected():
    conn = make_conn("x:A", {"2026-01-31": 1.0, "2026-02-28": 2.0})
    passed, issues = VU.validate_overlap(conn, "x:A", {})
    assert passed is False, "empty fetched data must be rejected"
