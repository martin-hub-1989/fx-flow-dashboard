"""
transforms.py — Controlled transform contract for Wind/iFind data.

Per NEXT_PHASE_EXECUTION_LOOP.md Loop 2, only a fixed whitelist of transforms
is allowed. Transforms are applied as an ordered chain BEFORE overlap validation.
Unknown transforms raise ValueError (no silent passthrough).
"""

ALLOWED_TRANSFORMS = (
    "identity",
    "divide_1e4",
    "divide_1e8",
    "multiply_100",
    "divide_100",
    "sign_flip",
    "currency_conversion_by_date",
    "cumulative_to_period",
)


def _scalar(data, factor):
    return {d: v * factor for d, v in data.items() if v is not None}


def _identity(data, **kw):
    return dict(data)


def _divide_1e4(data, **kw):
    return _scalar(data, 1.0 / 1e4)


def _divide_1e8(data, **kw):
    return _scalar(data, 1.0 / 1e8)


def _multiply_100(data, **kw):
    return _scalar(data, 100.0)


def _divide_100(data, **kw):
    return _scalar(data, 1.0 / 100.0)


def _sign_flip(data, **kw):
    return _scalar(data, -1.0)


def _currency_conversion_by_date(data, fx_rates=None, **kw):
    """Multiply each value by the FX rate for that date. Points with no
    matching rate are dropped (never guessed)."""
    if not fx_rates:
        raise ValueError("currency_conversion_by_date requires fx_rates")
    out = {}
    for d, v in data.items():
        if v is None:
            continue
        rate = fx_rates.get(d)
        if rate is None:
            continue  # no rate for this date — drop, don't guess
        out[d] = v * rate
    return out


def _cumulative_to_period(data, **kw):
    """Convert year-to-date cumulative values to per-period values.

    Within a calendar year, period[t] = cumulative[t] - cumulative[t-1];
    the first month of each year keeps its cumulative value (= period value).
    Missing months are handled by using the previous available month within
    the same year as the baseline.
    """
    out = {}
    dates = sorted(data.keys())
    prev_year = None
    prev_val = None
    for d in dates:
        v = data[d]
        if v is None:
            continue
        year = d[:4]
        if year != prev_year:
            # new year — cumulative value IS the period value
            out[d] = v
        else:
            out[d] = v - prev_val
        prev_year = year
        prev_val = v
    return out


_DISPATCH = {
    "identity": _identity,
    "divide_1e4": _divide_1e4,
    "divide_1e8": _divide_1e8,
    "multiply_100": _multiply_100,
    "divide_100": _divide_100,
    "sign_flip": _sign_flip,
    "currency_conversion_by_date": _currency_conversion_by_date,
    "cumulative_to_period": _cumulative_to_period,
}


def apply_transform_chain(data, chain, fx_rates=None):
    """Apply an ordered list of transforms to {date: value}.

    Raises ValueError on any unknown transform name.
    Returns a new {date: value} dict.
    """
    if chain is None:
        chain = []
    for name in chain:
        if name not in ALLOWED_TRANSFORMS:
            raise ValueError(f"Unknown transform: {name!r}. "
                             f"Allowed: {ALLOWED_TRANSFORMS}")
    out = dict(data)
    for name in chain:
        out = _DISPATCH[name](out, fx_rates=fx_rates)
    return out


def transform_with_audit(data, chain, fx_rates=None):
    """Apply transforms and return an auditable record preserving raw values."""
    transformed = apply_transform_chain(data, chain, fx_rates=fx_rates)
    return {
        "raw_observations": dict(data),
        "transform_chain": list(chain or []),
        "transformed_observations": transformed,
    }
