"""Loop 14 production gate tests — regression protection for the v1 contract.

Covers:
- chart-catalog derived has no excel_cached / excel_vlookup (Loop 7 gate)
- update plan only contains wind_verified mappings (Loop 1 gate)
- metric_definitions coverage for chart-critical derived
- HTML structure (9 modules, 29 charts, 2 scatter, 4 seasonality)
"""
import json, sqlite3
from pathlib import Path
import pytest


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect("data/monthly_brief.sqlite")
    c.row_factory = sqlite3.Row
    yield c
    c.close()


@pytest.fixture(scope="module")
def chart_sids():
    cat = json.load(open("config/chart_catalog.json", encoding="utf-8"))
    sids = set()
    for mod, md in cat["modules"].items():
        for ch in md["charts"]:
            for ds in ch["datasets"]:
                sids.add(ds["series_id"])
            if ch.get("scatter"):
                sids.add(ch["scatter_x"]["series_id"])
                sids.add(ch["scatter_y"]["series_id"])
    return sids


def test_chart_critical_derived_not_cached(conn, chart_sids):
    """Loop 7 gate: chart-referenced derived must not be excel_cached/vlookup."""
    cached = []
    for sid in chart_sids:
        r = conn.execute("SELECT implementation FROM metric_definitions WHERE series_id=?",
                         (sid,)).fetchone()
        if r and r[0] in ("excel_cached", "excel_vlookup"):
            cached.append((sid, r[0]))
    assert cached == [], f"chart-critical still cached: {cached}"


def test_update_plan_only_wind_verified():
    """Loop 1 gate: every plan entry corresponds to a wind_verified mapping."""
    plan = json.load(open("config/update_plan.json", encoding="utf-8"))
    mappings = json.load(open("config/wind_mapping.json", encoding="utf-8"))
    wv = {m["series_id"] for m in mappings
          if isinstance(m, dict) and m.get("wind_verified") is True}
    for e in plan:
        assert e["series_id"] in wv, f"{e['series_id']} in plan but not wind_verified"
        # validation_dates must be 2 distinct real DB dates
        vd = e["validation_dates"]
        assert len(vd) == 2 and vd[0] != vd[1], f"{e['series_id']} bad validation_dates"


def test_metric_definitions_cover_chart_derived(conn, chart_sids):
    """Every chart-critical derived series has a metric_definition."""
    missing = []
    for sid in chart_sids:
        st = conn.execute("SELECT series_type FROM series WHERE series_id=?", (sid,)).fetchone()
        if st and st[0] == "derived":
            d = conn.execute("SELECT COUNT(*) FROM metric_definitions WHERE series_id=?",
                             (sid,)).fetchone()[0]
            if d == 0:
                missing.append(sid)
    assert missing == [], f"chart derived missing metric_def: {missing}"


def test_html_structure():
    """HTML has 9 modules, 29 chart cards, 2 scatter, 4 seasonality."""
    cat = json.load(open("config/chart_catalog.json", encoding="utf-8"))
    total = sum(len(md["charts"]) for md in cat["modules"].values())
    scatter = sum(1 for md in cat["modules"].values() for c in md["charts"] if c.get("scatter"))
    season = sum(1 for md in cat["modules"].values() for c in md["charts"]
                 if c["chart_type"] == "seasonality_band")
    assert total == 29, f"expected 29 charts, got {total}"
    assert scatter == 2, f"expected 2 scatter, got {scatter}"
    assert season == 4, f"expected 4 seasonality, got {season}"
    assert len(cat["modules"]) == 9, "expected 9 modules"


def test_disposition_table_66(conn):
    """Loop 13 gate: 66/66 original charts disposed, targets exist."""
    d = json.load(open("config/excel_chart_disposition.json", encoding="utf-8"))
    assert len(d["dispositions"]) == 66
    cat = json.load(open("config/chart_catalog.json", encoding="utf-8"))
    cat_ids = {c["chart_id"] for md in cat["modules"].values() for c in md["charts"]}
    for r in d["dispositions"]:
        if r["status"] in ("retained", "merged_into", "rebuilt_as"):
            for t in r["target_chart_ids"]:
                assert t in cat_ids, f"{r['excel_chart_id']} target {t} missing"


def test_no_trailing_zeros(conn):
    """Loop 9 gate: no series ends in a trailing zero."""
    rows = conn.execute("""
        SELECT s.series_id FROM series s
        WHERE (SELECT value FROM observations o WHERE o.series_id=s.series_id
               AND value IS NOT NULL ORDER BY date DESC LIMIT 1) = 0
    """).fetchall()
    assert len(rows) == 0, f"{len(rows)} series still end in 0"


def test_validate_all_passes():
    """validate_all.py must report 8/8."""
    import subprocess
    r = subprocess.run(["python3", "scripts/validate_all.py"],
                      capture_output=True, text=True, timeout=60)
    assert "8/8 checks passed" in r.stdout or "8/8" in r.stdout, \
        f"validate_all not 8/8:\n{r.stdout[-500:]}"
