"""
Loop 1 tests: mapping & update-plan contract.
Per NEXT_PHASE_EXECUTION_LOOP.md Loop 1.

Covers:
1. mapping with _metadata row does not error
2. wind_verified=false does NOT enter plan
3. old status names do NOT enter plan
4. only verified_exact / verified_unit_transform may enter
5. validation dates MUST equal DB's last two actual observation dates
6. reject plan when only one date or duplicate dates
7. identical input reproduces identical plan
"""
import sys, json, sqlite3, tempfile, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_update_plan as bup


def make_db(rows):
    """rows: {series_id: [(date, value), ...]}. Returns conn with series+observations."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE series (
        series_id TEXT PRIMARY KEY, display_name TEXT, module TEXT,
        series_type TEXT, frequency TEXT, unit TEXT, source TEXT,
        source_query TEXT, excel_sheet TEXT, excel_range TEXT,
        update_status TEXT, first_date TEXT, last_date TEXT, notes TEXT)""")
    conn.execute("""CREATE TABLE observations (
        series_id TEXT, date TEXT, value REAL, source TEXT,
        source_vintage TEXT, imported_at TEXT, run_id TEXT,
        PRIMARY KEY(series_id, date))""")
    for sid, pts in rows.items():
        dates = [d for d, _ in pts]
        conn.execute("INSERT INTO series (series_id, frequency, last_date, first_date) VALUES (?,?,?,?)",
                     (sid, "monthly", max(dates) if dates else None, min(dates) if dates else None))
        for d, v in pts:
            conn.execute("INSERT INTO observations (series_id, date, value) VALUES (?,?,?)", (sid, d, v))
    conn.commit()
    return conn


def write_mapping(entries):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(entries, f, ensure_ascii=False)
    f.close()
    return f.name


def test_metadata_row_does_not_error():
    conn = make_db({"x:A": [("2026-03-31", 1.0), ("2026-04-30", 2.0)]})
    mp = write_mapping([
        {"_metadata": {"note": "header"}},
        {"series_id": "x:A", "status": "verified_exact", "wind_verified": True, "frequency": "monthly"},
    ])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert isinstance(plan, list)


def test_wind_verified_false_excluded():
    conn = make_db({"x:A": [("2026-03-31", 1.0), ("2026-04-30", 2.0)]})
    mp = write_mapping([
        {"series_id": "x:A", "status": "verified_exact", "wind_verified": False, "frequency": "monthly"},
    ])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert len(plan) == 0, "wind_verified=false must not enter plan"


def test_old_status_names_excluded():
    conn = make_db({"x:A": [("2026-03-31", 1.0), ("2026-04-30", 2.0)]})
    mp = write_mapping([
        {"series_id": "x:A", "status": "verified", "wind_verified": True, "frequency": "monthly"},
        {"series_id": "x:A", "status": "verified_with_transform", "wind_verified": True, "frequency": "monthly"},
    ])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert len(plan) == 0, "old status names must not enter plan"


def test_only_verified_states_enter():
    conn = make_db({
        "x:A": [("2026-03-31", 1.0), ("2026-04-30", 2.0)],
        "x:B": [("2026-03-31", 1.0), ("2026-04-30", 2.0)],
        "x:C": [("2026-03-31", 1.0), ("2026-04-30", 2.0)],
    })
    mp = write_mapping([
        {"series_id": "x:A", "status": "verified_exact", "wind_verified": True, "frequency": "monthly"},
        {"series_id": "x:B", "status": "verified_unit_transform", "wind_verified": True, "frequency": "monthly"},
        {"series_id": "x:C", "status": "mapping_pending", "wind_verified": True, "frequency": "monthly"},
    ])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    sids = {e["series_id"] for e in plan}
    assert sids == {"x:A", "x:B"}, f"only verified_exact/unit_transform expected, got {sids}"


def test_validation_dates_are_last_two_db_dates():
    conn = make_db({"x:A": [("2026-01-31", 1.0), ("2026-02-28", 2.0),
                            ("2026-03-31", 3.0), ("2026-04-30", 4.0)]})
    mp = write_mapping([
        {"series_id": "x:A", "status": "verified_exact", "wind_verified": True, "frequency": "monthly"},
    ])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert len(plan) == 1
    vd = plan[0]["validation_dates"]
    assert vd == ["2026-03-31", "2026-04-30"], f"must be last two actual DB dates, got {vd}"


def test_reject_single_date():
    conn = make_db({"x:A": [("2026-04-30", 4.0)]})  # only ONE observation
    mp = write_mapping([
        {"series_id": "x:A", "status": "verified_exact", "wind_verified": True, "frequency": "monthly"},
    ])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert len(plan) == 0, "series with <2 observations must not enter plan"


def test_reproducible():
    conn = make_db({"x:A": [("2026-03-31", 1.0), ("2026-04-30", 2.0)]})
    mp = write_mapping([
        {"series_id": "x:A", "status": "verified_exact", "wind_verified": True, "frequency": "monthly"},
    ])
    p1 = bup.build_plan(conn, mapping_path=mp)
    p2 = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True), "plan must be reproducible"


def test_production_plan_currently_zero():
    """With real wind_mapping.json (0 wind_verified=true), production plan must be 0."""
    conn = bup.get_db()
    plan = bup.build_plan(conn, mapping_path="config/wind_mapping.json")
    conn.close()
    assert len(plan) == 0, f"no wind_verified mappings yet, expected 0, got {len(plan)}"
