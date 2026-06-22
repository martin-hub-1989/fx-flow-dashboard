"""
Recompute derived indicators from raw observations.
Step 2c: For the 3.即远期 pilot module.
Each derived series has a documented formula, inputs, and implementation.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (
    get_db, init_db, start_update_run, finish_update_run,
    insert_observations_batch, upsert_series, get_observations
)

# --- Derived indicator definitions for 3.即远期 ---

DERIVED_DEFS = [
    {
        "series_id": "fx_fwd:supply_demand",
        "display_name": "外汇市场即远期总供求",
        "description": "即期代客结售汇差额 + 远期签约净结汇 + 期权Delta变动。反映外汇市场总体供需。",
        "inputs": ["fx_fwd:AB", "fx_fwd:AD", "fx_fwd:AJ"],  # 即期代客差额 + 衍生品净结汇 + 期权Delta
        "module": "3.即远期",
        "frequency": "monthly",
        "unit": "net_flow",
    },
    {
        "series_id": "fx_fwd:spot_flow",
        "display_name": "即期结售汇发生额（银行自身+代客）",
        "description": "银行自身结售汇差额 + 代客即期结售汇差额。",
        "inputs": ["fx_fwd:D", "fx_fwd:AB"],  # 银行自身差额 + 代客即期差额
        "module": "3.即远期",
        "frequency": "monthly",
        "unit": "net_flow",
    },
    {
        "series_id": "fx_fwd:deriv_flow",
        "display_name": "衍生品当月净签约（远期+期权）",
        "description": "远期签约净结汇 + 期权Delta净变动。",
        "inputs": ["fx_fwd:AD", "fx_fwd:AJ"],  # 衍生品净结汇 + 期权Delta
        "module": "3.即远期",
        "frequency": "monthly",
        "unit": "net_flow",
    },
    {
        "series_id": "fx_fwd:supply_demand_3mma",
        "display_name": "外汇市场即远期总供求（3MMA）",
        "description": "3-month moving average of fx_fwd:supply_demand.",
        "inputs": ["fx_fwd:supply_demand"],
        "module": "3.即远期",
        "frequency": "monthly",
        "unit": "moving_average",
    },
    {
        "series_id": "fx_fwd:supply_demand_12mma",
        "display_name": "外汇市场即远期总供求（12MMA）",
        "description": "12-month moving average of fx_fwd:supply_demand.",
        "inputs": ["fx_fwd:supply_demand"],
        "module": "3.即远期",
        "frequency": "monthly",
        "unit": "moving_average",
    },
]


def compute_moving_average(values, window):
    """Compute simple moving average."""
    result = {}
    sorted_dates = sorted(values.keys())
    for i, d in enumerate(sorted_dates):
        if i >= window - 1:
            window_vals = [values[sorted_dates[j]] for j in range(i - window + 1, i + 1)]
            valid = [v for v in window_vals if v is not None]
            if len(valid) >= max(1, window // 2):  # Require at least half the window
                result[d] = sum(valid) / len(valid)
    return result


def recompute_derived(conn, run_id, module_filter=None):
    """Recompute all derived indicators for specified module(s)."""
    # Get existing raw data
    raw_cache = {}

    def load_series(sid):
        if sid not in raw_cache:
            rows = get_observations(conn, sid)
            raw_cache[sid] = {r["date"]: r["value"] for r in rows}
        return raw_cache[sid]

    new_obs = []
    computed_series = []

    for defn in DERIVED_DEFS:
        if module_filter and defn["module"] != module_filter:
            continue

        print(f"  Computing: {defn['series_id']} — {defn['display_name']}")

        # Load all input series
        input_data = {}
        for inp_sid in defn["inputs"]:
            input_data[inp_sid] = load_series(inp_sid)

        # Find common date range
        all_dates = set()
        for data in input_data.values():
            all_dates.update(data.keys())
        all_dates = sorted(all_dates)

        if not all_dates:
            print(f"    WARNING: No dates found for inputs")
            continue

        # Compute values based on the formula
        result = {}
        formula_desc = ""

        if defn["series_id"] == "fx_fwd:supply_demand":
            # 即期代客差额 + 远期签约净结汇 + 期权Delta变动
            a = input_data.get("fx_fwd:AB", {})
            b = input_data.get("fx_fwd:AD", {})
            c = input_data.get("fx_fwd:AJ", {})
            for d in all_dates:
                vals = [a.get(d), b.get(d), c.get(d)]
                if all(v is not None for v in vals):
                    result[d] = sum(vals)
            formula_desc = "即期代客结售汇差额 + 衍生品净结汇 + 期权Delta净变动"

        elif defn["series_id"] == "fx_fwd:spot_flow":
            # 银行自身差额 + 代客即期差额
            a = input_data.get("fx_fwd:D", {})
            b = input_data.get("fx_fwd:AB", {})
            for d in all_dates:
                vals = [a.get(d), b.get(d)]
                if all(v is not None for v in vals):
                    result[d] = sum(vals)
            formula_desc = "银行自身结售汇差额 + 代客即期结售汇差额"

        elif defn["series_id"] == "fx_fwd:deriv_flow":
            # 远期签约净结汇 + 期权Delta净变动
            a = input_data.get("fx_fwd:AD", {})
            b = input_data.get("fx_fwd:AJ", {})
            for d in all_dates:
                vals = [a.get(d), b.get(d)]
                if all(v is not None for v in vals):
                    result[d] = sum(vals)
            formula_desc = "衍生品净结汇 + 期权Delta净变动"

        elif defn["series_id"] in ("fx_fwd:supply_demand_3mma", "fx_fwd:supply_demand_12mma"):
            window = 3 if "3mma" in defn["series_id"] else 12
            sd_data = input_data.get("fx_fwd:supply_demand", {})
            if not sd_data:
                print(f"    WARNING: supply_demand not yet computed, skipping")
                continue
            result = compute_moving_average(sd_data, window)
            formula_desc = f"{window}-month moving average of 外汇市场即远期总供求"

        else:
            print(f"    WARNING: Unknown derived series {defn['series_id']}")
            continue

        if not result:
            print(f"    WARNING: No values computed")
            continue

        # Determine first/last dates
        sorted_result = sorted(result.keys())
        first_date = sorted_result[0]
        last_date = sorted_result[-1]

        # Upsert series metadata
        upsert_series(conn, {
            "series_id": defn["series_id"],
            "display_name": defn["display_name"],
            "module": defn["module"],
            "series_type": "derived",
            "frequency": defn["frequency"],
            "unit": defn["unit"],
            "source": "recomputed",
            "source_query": formula_desc,
            "excel_sheet": defn["module"],
            "update_status": "computed",
            "first_date": first_date,
            "last_date": last_date,
            "notes": f"Inputs: {', '.join(defn['inputs'])}. {formula_desc}",
        })

        # Collect observations
        for d, v in result.items():
            new_obs.append((defn["series_id"], d, v, "recomputed"))

        computed_series.append(defn["series_id"])
        print(f"    Computed {len(result)} values, range {first_date} to {last_date}")

    # Batch insert
    if new_obs:
        insert_observations_batch(conn, new_obs, run_id)
        conn.commit()
        print(f"  Inserted {len(new_obs)} derived observations")

    return computed_series, len(new_obs)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Recompute derived indicators")
    parser.add_argument("--module", default="3.即远期", help="Module to recompute")
    args = parser.parse_args()

    conn = get_db()
    init_db(conn)
    run_id = start_update_run(conn, 0)

    print(f"Recomputing derived indicators for: {args.module}")
    computed, n_obs = recompute_derived(conn, run_id, args.module)

    finish_update_run(conn, run_id, "completed", successful=len(computed), new_obs=n_obs)

    # Verify against Excel cached values
    print(f"\n--- Comparison with Excel cached values ---")
    for sid in computed:
        ours = dict(get_observations(conn, sid))
        # Find corresponding Excel column
        excel_rows = conn.execute(
            "SELECT series_id, excel_range FROM series WHERE module=? AND series_type='derived' LIMIT 5",
            (args.module,)
        ).fetchall()
        ours_last = sorted(ours.keys())[-5:] if ours else []
        if ours_last:
            vals = [f"{d}={ours[d]:.2f}" for d in ours_last]
            print(f"  {sid} last 5: {', '.join(vals)}")

    conn.close()
    print(f"\nDone: {len(computed)} derived series, {n_obs} new observations")


if __name__ == "__main__":
    main()
