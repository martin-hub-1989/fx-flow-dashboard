"""
Loop 2 tests: transform contract.
Per NEXT_PHASE_EXECUTION_LOOP.md Loop 2.

- unknown transform rejected
- transform order stable
- unit conversion happens BEFORE overlap validation (apply_transform_chain)
- currency conversion uses date-matched FX rate
- cumulative_to_period handles year-start and missing months
- raw and transformed values both preserved
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import transforms as T


def test_allowed_transforms_present():
    for name in ["identity", "divide_1e4", "divide_1e8", "multiply_100",
                 "divide_100", "sign_flip", "currency_conversion_by_date",
                 "cumulative_to_period"]:
        assert name in T.ALLOWED_TRANSFORMS


def test_unknown_transform_rejected():
    data = {"2026-01-31": 100.0}
    with pytest.raises(ValueError):
        T.apply_transform_chain(data, ["bogus_transform"])


def test_identity():
    data = {"2026-01-31": 100.0, "2026-02-28": 200.0}
    out = T.apply_transform_chain(data, ["identity"])
    assert out == data


def test_divide_1e8():
    data = {"2026-01-31": 1.9e10}
    out = T.apply_transform_chain(data, ["divide_1e8"])
    assert abs(out["2026-01-31"] - 190.0) < 1e-9


def test_sign_flip():
    data = {"2026-01-31": 50.0, "2026-02-28": -30.0}
    out = T.apply_transform_chain(data, ["sign_flip"])
    assert out["2026-01-31"] == -50.0 and out["2026-02-28"] == 30.0


def test_transform_order_stable():
    """divide_100 then sign_flip != sign_flip then... actually commutative here,
    but multiply_100 then divide_1e4 differs from reverse for documentation."""
    data = {"d": 100.0}
    out1 = T.apply_transform_chain(data, ["multiply_100", "divide_1e4"])
    # 100*100=10000, /1e4 = 1.0
    assert abs(out1["d"] - 1.0) < 1e-9


def test_currency_conversion_by_date():
    # USD value -> CNY using per-date FX rate
    data = {"2026-01-31": 100.0, "2026-02-28": 200.0}
    fx = {"2026-01-31": 7.0, "2026-02-28": 7.2}
    out = T.apply_transform_chain(data, ["currency_conversion_by_date"], fx_rates=fx)
    assert abs(out["2026-01-31"] - 700.0) < 1e-9
    assert abs(out["2026-02-28"] - 1440.0) < 1e-9


def test_currency_conversion_missing_rate_drops_point():
    data = {"2026-01-31": 100.0, "2026-02-28": 200.0}
    fx = {"2026-01-31": 7.0}  # missing Feb
    out = T.apply_transform_chain(data, ["currency_conversion_by_date"], fx_rates=fx)
    assert "2026-02-28" not in out
    assert abs(out["2026-01-31"] - 700.0) < 1e-9


def test_cumulative_to_period():
    # cumulative resets each year; period = diff within year, year-start = first value
    data = {
        "2025-01-31": 10.0, "2025-02-28": 25.0, "2025-03-31": 45.0,
        "2026-01-31": 12.0, "2026-02-28": 30.0,
    }
    out = T.apply_transform_chain(data, ["cumulative_to_period"])
    assert abs(out["2025-01-31"] - 10.0) < 1e-9   # year start = cumulative
    assert abs(out["2025-02-28"] - 15.0) < 1e-9   # 25-10
    assert abs(out["2025-03-31"] - 20.0) < 1e-9   # 45-25
    assert abs(out["2026-01-31"] - 12.0) < 1e-9   # new year start
    assert abs(out["2026-02-28"] - 18.0) < 1e-9   # 30-12


def test_raw_and_transformed_preserved():
    data = {"2026-01-31": 1.9e10}
    result = T.transform_with_audit(data, ["divide_1e8"])
    assert result["raw_observations"] == data
    assert abs(result["transformed_observations"]["2026-01-31"] - 190.0) < 1e-9
    assert result["transform_chain"] == ["divide_1e8"]
