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


def _looks_numeric(s):
    """True if s is a pure numeric string (e.g. '444.8627' — a polluted last value,
    NOT a real unit). Empty strings and None are NOT numeric."""
    if s is None:
        return False
    try:
        float(str(s))
        return True
    except (ValueError, TypeError):
        return False


def _make_verified_mapping(sid="x:A", **overrides):
    """A verified_unit_transform mapping with sensible defaults for unit tests."""
    m = {
        "series_id": sid,
        "status": "verified_unit_transform",
        "wind_verified": True,
        "frequency": "monthly",
        "wind_code": "M5201660",
        "wind_query_exact": "中国:test:当月值",
    }
    m.update(overrides)
    return m


# --- Loop 2: unit field must carry a UNIT, never a last observation value ---

def test_numeric_mapping_unit_not_propagated():
    """A numeric `unit` in the mapping (polluted with a last value) must NOT
    pass through into plan.unit."""
    conn = make_db({"x:A": [("2026-03-31", 1.0), ("2026-04-30", 2.0)]})
    mp = write_mapping([_make_verified_mapping(
        unit="444.8627",                 # polluted last value, must NOT propagate
        target_unit="亿美元",            # the clean, correct unit source
    )])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert len(plan) == 1
    entry = plan[0]
    assert not _looks_numeric(entry["unit"]), \
        f"numeric mapping unit leaked into plan: entry['unit']={entry['unit']!r}"


def test_target_unit_propagates_when_db_unit_absent():
    """When DB series.unit is NULL (the real production case — DB unit is
    'monthly_amount', a frequency-style label bypassed by build_plan), the
    mapping's clean `target_unit` must propagate to plan.unit."""
    conn = make_db({"x:A": [("2026-03-31", 1.0), ("2026-04-30", 2.0)]})
    # make_db does NOT populate series.unit -> DB unit is NULL here.
    mp = write_mapping([_make_verified_mapping(
        target_unit="亿美元",
        unit="",                          # no polluted value, but also no unit
    )])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert len(plan) == 1
    assert plan[0]["unit"] == "亿美元", \
        f"target_unit should propagate; got {plan[0]['unit']!r}"


def test_wind_unit_confirmed_echoed():
    """The plan entry must echo the mapping's wind_unit_confirmed field."""
    conn = make_db({"x:A": [("2026-03-31", 1.0), ("2026-04-30", 2.0)]})
    mp = write_mapping([_make_verified_mapping(
        target_unit="亿美元",
        wind_unit_confirmed="亿美元",
    )])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert len(plan) == 1
    assert plan[0].get("wind_unit_confirmed") == "亿美元", \
        f"wind_unit_confirmed not echoed; got {plan[0].get('wind_unit_confirmed')!r}"


def test_numeric_unit_rejected_when_no_clean_source():
    """If mapping.unit is numeric AND no target_unit/wind_unit_confirmed is
    available, plan.unit must be empty (never the numeric value)."""
    conn = make_db({"x:A": [("2026-03-31", 1.0), ("2026-04-30", 2.0)]})
    mp = write_mapping([_make_verified_mapping(
        unit="72.3267",                  # polluted, no clean alternative provided
        target_unit=None,
        wind_unit_confirmed="",
    )])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert len(plan) == 1
    assert plan[0]["unit"] == "", \
        f"numeric unit with no clean source must be empty; got {plan[0]['unit']!r}"
    assert not _looks_numeric(plan[0]["unit"])


def test_target_unit_preferred_over_wind_unit_confirmed_sentence():
    """Priority: target_unit first. Even if wind_unit_confirmed is a verbose
    sentence (legacy form), the clean target_unit must win."""
    conn = make_db({"x:A": [("2026-03-31", 1.0), ("2026-04-30", 2.0)]})
    mp = write_mapping([_make_verified_mapping(
        target_unit="亿美元",
        wind_unit_confirmed="亿美元 (Wind matches DB unit, no transform needed)",
        unit="414.0625",
    )])
    plan = bup.build_plan(conn, mapping_path=mp)
    os.unlink(mp)
    assert len(plan) == 1
    assert plan[0]["unit"] == "亿美元", \
        f"target_unit must take priority; got {plan[0]['unit']!r}"


def test_production_plan_units_not_numeric():
    """Integration: every entry in the REAL production plan (built from the real
    config/wind_mapping.json + real DB) must carry a non-numeric unit and a
    clean wind_unit_confirmed of '亿美元'."""
    conn = bup.get_db()
    plan = bup.build_plan(conn, mapping_path="config/wind_mapping.json")
    conn.close()
    assert len(plan) > 0, "expected wind_verified entries in production config"
    for e in plan:
        assert not _looks_numeric(e["unit"]), \
            f"{e['series_id']}: numeric unit leaked into production plan: {e['unit']!r}"
        assert e.get("wind_unit_confirmed") == "亿美元", \
            f"{e['series_id']}: wind_unit_confirmed must be clean '亿美元'; " \
            f"got {e.get('wind_unit_confirmed')!r}"


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


def test_production_plan_matches_wind_verified():
    """Production plan count must equal the number of wind_verified=true mappings
    in the real config/wind_mapping.json (deterministic, code-reproducible)."""
    conn = bup.get_db()
    plan = bup.build_plan(conn, mapping_path="config/wind_mapping.json")
    conn.close()
    import json as _j
    mappings = _j.load(open("config/wind_mapping.json", encoding="utf-8"))
    expected = sum(1 for x in mappings
                   if isinstance(x, dict) and x.get("wind_verified") is True
                   and x.get("status") in ("verified_exact", "verified_unit_transform"))
    assert len(plan) == expected, f"plan {len(plan)} != wind_verified {expected}"
    # every plan entry must carry the wind closure fields
    for e in plan:
        assert e.get("wind_code"), f"{e['series_id']} missing wind_code"
        assert e.get("wind_query_exact"), f"{e['series_id']} missing wind_query_exact"
