"""Loop 13 tests: 66-chart disposition table machine-verifiable."""
import json
from pathlib import Path


def test_exactly_66_charts():
    d = json.load(open("config/excel_chart_disposition.json", encoding="utf-8"))
    assert d["_meta"]["total_original_charts"] == 66
    assert len(d["dispositions"]) == 66


def test_all_statuses_valid():
    d = json.load(open("config/excel_chart_disposition.json", encoding="utf-8"))
    valid = {"retained", "merged_into", "rebuilt_as", "deleted_with_reason"}
    for r in d["dispositions"]:
        assert r["status"] in valid, f"{r['excel_chart_id']}: {r['status']}"


def test_unique_excel_ids():
    d = json.load(open("config/excel_chart_disposition.json", encoding="utf-8"))
    ids = [r["excel_chart_id"] for r in d["dispositions"]]
    assert len(set(ids)) == 66, "duplicate excel_chart_id"


def test_retained_merged_targets_exist():
    d = json.load(open("config/excel_chart_disposition.json", encoding="utf-8"))
    cat = json.load(open("config/chart_catalog.json", encoding="utf-8"))
    cat_ids = set()
    for mod, md in cat["modules"].items():
        for ch in md["charts"]:
            cat_ids.add(ch["chart_id"])
    for r in d["dispositions"]:
        if r["status"] in ("retained", "merged_into", "rebuilt_as"):
            for t in r["target_chart_ids"]:
                assert t in cat_ids, f"{r['excel_chart_id']} target {t} not in catalog"


def test_deleted_has_reason():
    d = json.load(open("config/excel_chart_disposition.json", encoding="utf-8"))
    for r in d["dispositions"]:
        if r["status"] == "deleted_with_reason":
            assert r["reason"], f"{r['excel_chart_id']} deleted without reason"
            assert r["target_chart_ids"] == [], f"{r['excel_chart_id']} deleted but has targets"


def test_matches_inventory():
    inv = json.load(open(".inspection/chart_inventory.json", encoding="utf-8"))
    inv_ids = {c["chart_id"] for c in inv}
    d = json.load(open("config/excel_chart_disposition.json", encoding="utf-8"))
    disp_ids = {r["excel_chart_id"] for r in d["dispositions"]}
    assert inv_ids == disp_ids, f"diff: {inv_ids ^ disp_ids}"
