"""
Loop 3 (a.k.a. staging-metadata loop) tests.

Staging records in data/staging_fetched.json must carry Wind-RETURNED metadata
(wind_code / wind_name / wind_unit), not values synthesized from plan fields.
Wind metadata is authoritative; plan fields are fallback only. A numeric-looking
wind_unit (a polluted last-observation value) must NEVER be stored.

TDD: this file is written FIRST and must FAIL against the current code (which
sets wind_name/wind_unit from plan entry.get('wind_indicator') / entry.get('unit')),
then pass once fetch_via_wind_mcp returns the structured shape and main() uses it.
"""
import sys, json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_wind


# --- constants & helpers ---------------------------------------------------

WIND_NAME = "中国:银行自身结汇金额:当月值"
WIND_CODE = "M5207846"
WIND_UNIT = "亿美元"


def _is_numeric_unit_local(s):
    """Local mirror of build_update_plan._is_numeric_unit for assertions."""
    if s is None or s == "":
        return False
    try:
        float(str(s))
        return True
    except (ValueError, TypeError):
        return False


def _plan_entry():
    """A plan entry whose plan-sourced fields DELIBERATELY DIFFER from Wind-returned
    metadata, so a staging record synthesized from plan (the bug) is distinguishable
    from one that uses Wind-returned metadata (the fix).

    Note `unit` is a polluted numeric last-value (the Loop 2 bug shape) and
    `wind_indicator` is a plan display name — neither should ever reach staging
    when Wind returns clean metadata.
    """
    return {
        "series_id": "fx_fwd:B",
        "query": "中国:银行自身结汇金额:当月值",
        "wind_indicator": "PLAN_DISPLAY_NAME",   # plan display name (NOT Wind)
        "wind_name": "",                           # plan wind_name empty -> Wind wins
        "wind_code": WIND_CODE,                    # matches Wind (no conflict here)
        "wind_unit_confirmed": WIND_UNIT,          # clean plan fallback
        "unit": "444.8627",                        # POLLUTED numeric (old bug)
        "frequency": "monthly",
        "currency": "USD",
        "transform": [],
        "validation_dates": ["2026-03-31", "2026-04-30"],
    }


def _wind_result(*, with_metadata):
    """The NEW structured shape returned by fetch_via_wind_mcp after Loop 3."""
    base = {
        "data": {"2026-04-30": 444.8627},
        "raw_response_summary": {"n_points": 1, "code": WIND_CODE, "name": WIND_NAME},
    }
    if with_metadata:
        base.update({"wind_code": WIND_CODE, "wind_name": WIND_NAME, "wind_unit": WIND_UNIT})
    else:
        base.update({"wind_code": None, "wind_name": None, "wind_unit": None})
    return base


def _run_fetch(monkeypatch, tmp_path, wind_fn):
    """Monkeypatch fetch_via_wind_mcp -> wind_fn, run main(), return staging_records.

    Drives main() via sys.argv (no signature change to main needed)."""
    monkeypatch.setattr(fetch_wind, "fetch_via_wind_mcp", wind_fn)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps([_plan_entry()], ensure_ascii=False), encoding="utf-8")
    staging_path = tmp_path / "staging.json"
    monkeypatch.setattr("sys.argv", [
        "fetch_wind.py", "--plan", str(plan_path), "--output", str(staging_path),
    ])
    rc = fetch_wind.main()
    assert rc == 0, f"main() returned {rc}"
    staging = json.loads(staging_path.read_text(encoding="utf-8"))
    return staging["staging_records"]


# --- tests ------------------------------------------------------------------

def test_staging_uses_wind_returned_metadata(monkeypatch, tmp_path):
    """wind_unit / wind_name / wind_code come from the Wind return, not the plan."""
    recs = _run_fetch(monkeypatch, tmp_path, lambda entry: _wind_result(with_metadata=True))
    rec = recs["fx_fwd:B"]

    # (a) wind_unit == Wind-returned unit, NOT plan's polluted "444.8627"
    assert rec["wind_unit"] == WIND_UNIT, rec["wind_unit"]
    # (b) wind_name == Wind-returned name, NOT plan's wind_indicator
    assert rec["wind_name"] == WIND_NAME, rec["wind_name"]
    # wind_code from Wind return
    assert rec["wind_code"] == WIND_CODE, rec["wind_code"]
    # (c) wind_unit is never numeric-looking
    assert not _is_numeric_unit_local(rec["wind_unit"]), rec["wind_unit"]
    # (d) raw + transformed observations preserved and date-shaped
    assert rec["raw_observations"], rec["raw_observations"]
    assert "2026-04-30" in rec["raw_observations"], rec["raw_observations"]
    assert rec["transformed_observations"], rec["transformed_observations"]
    assert "2026-04-30" in rec["transformed_observations"]
    # remaining staging fields present
    for k in ("query", "requested_frequency", "requested_currency",
              "fetched_at", "transform_chain", "series_id"):
        assert k in rec, k


def test_staging_falls_back_to_plan_when_wind_metadata_missing(monkeypatch, tmp_path):
    """When the Wind return lacks metadata, staging falls back to CLEAN plan fields,
    and NEVER stores a numeric unit."""
    recs = _run_fetch(monkeypatch, tmp_path, lambda entry: _wind_result(with_metadata=False))
    rec = recs["fx_fwd:B"]

    # wind_unit falls back to wind_unit_confirmed (clean), NOT polluted unit "444.8627"
    assert rec["wind_unit"] == WIND_UNIT, rec["wind_unit"]
    # wind_name falls back to wind_indicator (plan display name) since wind_name empty
    assert rec["wind_name"] == "PLAN_DISPLAY_NAME", rec["wind_name"]
    # numeric guard holds even on the fallback path
    assert not _is_numeric_unit_local(rec["wind_unit"]), rec["wind_unit"]
    # observations still preserved
    assert "2026-04-30" in rec["raw_observations"], rec["raw_observations"]
    assert "2026-04-30" in rec["transformed_observations"]
