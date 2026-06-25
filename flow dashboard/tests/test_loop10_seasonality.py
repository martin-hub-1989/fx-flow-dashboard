"""
Loop 10 tests: seasonality band contract.
Per NEXT_PHASE_EXECUTION_LOOP.md Loop 10.

The generator must produce a seasonality chart spec with:
- x axis fixed 1-12 months
- history min/max band
- history mean (or median)
- current-year trajectory
- unpublished months null
- selector that switches indicator
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def test_seasonality_compute():
    """compute_seasonality returns {month: {min,max,mean,current}} with 1-12."""
    import generate_dashboard as gd
    pts = [
        ("2024-01-31", 100.0), ("2024-02-28", 110.0), ("2024-03-31", 120.0),
        ("2024-04-30", 90.0), ("2024-05-31", 95.0), ("2024-06-30", 105.0),
        ("2024-07-31", 130.0), ("2024-08-31", 140.0), ("2024-09-30", 125.0),
        ("2024-10-31", 115.0), ("2024-11-30", 100.0), ("2024-12-31", 110.0),
        ("2025-01-31", 105.0), ("2025-02-28", 115.0),
        # current year 2026 partial
        ("2026-01-31", 108.0), ("2026-02-28", 112.0),
    ]
    result = gd.compute_seasonality(pts, history_start_year=2024, history_end_year=2025,
                                    current_year=2026)
    assert len(result) == 12, f"must have 12 months, got {len(result)}"
    # Jan: history [100, 105], min=100 max=105 mean=102.5, current=108
    jan = result[0]
    assert jan["month"] == 1
    assert jan["min"] == 100.0
    assert jan["max"] == 105.0
    assert abs(jan["mean"] - 102.5) < 1e-6
    assert jan["current"] == 108.0
    # unpublished month (Dec 2026) must be null
    dec = result[11]
    assert dec["current"] is None


def test_seasonality_no_history_for_current_year():
    """History excludes current year."""
    import generate_dashboard as gd
    pts = [("2026-01-31", 100.0), ("2026-02-28", 200.0)]
    result = gd.compute_seasonality(pts, history_start_year=2020, history_end_year=2025,
                                    current_year=2026)
    assert result[0]["min"] is None  # no history
    assert result[0]["current"] == 100.0


def test_chart_catalog_has_seasonality_charts():
    cat = json.load(open("config/chart_catalog.json", encoding="utf-8"))
    seas = []
    for mod, md in cat["modules"].items():
        for ch in md["charts"]:
            if ch.get("chart_type") == "seasonality_band":
                seas.append(ch["chart_id"])
    assert len(seas) >= 4, f"need >=4 seasonality charts, got {seas}"
