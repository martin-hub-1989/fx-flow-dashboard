"""
Step 6a: Build incremental update plan from wind_mapping.json.
For each verifiable series, generate fetch parameters and validation dates.
"""
import sys, json
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import get_db


def get_next_start_date(last_date, frequency):
    """Compute the next fetch start date given a last_date and frequency."""
    if not last_date:
        return None
    try:
        d = datetime.strptime(last_date[:10], '%Y-%m-%d')
    except ValueError:
        return None

    if frequency == 'monthly' or frequency == '月':
        next_d = d + relativedelta(months=1)
    elif frequency == 'daily' or frequency == '日':
        next_d = d + timedelta(days=1)
    elif frequency == 'quarterly' or frequency == '季':
        next_d = d + relativedelta(months=3)
    else:
        next_d = d + relativedelta(months=1)

    return next_d.strftime('%Y-%m-%d')


def build_plan(conn, mapping_path='config/wind_mapping.json'):
    """Generate an incremental update plan from the wind mapping."""
    with open(mapping_path, 'r', encoding='utf-8') as f:
        mappings = json.load(f)

    plan = []

    for m in mappings:
        sid = m['series_id']
        status = m.get('status', 'mapping_pending')

        # Only plan updates for verifiable series
        if status not in ('verified', 'verified_with_transform'):
            continue

        # Get last date from DB
        row = conn.execute(
            "SELECT last_date, frequency FROM series WHERE series_id=?", (sid,)
        ).fetchone()

        if not row:
            continue

        last_date = row['last_date']
        frequency = m.get('frequency') or row['frequency']

        if not last_date:
            continue

        next_start = get_next_start_date(last_date, frequency)

        # For validation: fetch slightly before last_date for overlap check
        if frequency in ('monthly', '月'):
            overlap_start = (datetime.strptime(last_date[:10], '%Y-%m-%d') -
                            relativedelta(months=2)).strftime('%Y-%m-%d')
        elif frequency in ('daily', '日'):
            overlap_start = (datetime.strptime(last_date[:10], '%Y-%m-%d') -
                            timedelta(days=5)).strftime('%Y-%m-%d')
        else:
            overlap_start = last_date

        entry = {
            "series_id": sid,
            "display_name": m.get('display_name', ''),
            "wind_indicator": m.get('wind_indicator', ''),
            "module": m.get('module', ''),
            "last_date": last_date,
            "next_start_date": next_start,
            "fetch_start_date": overlap_start,
            "validation_dates": [overlap_start, last_date],
            "wind_method": m.get('wind_method', 'wsd'),  # wsd = Wind EDB time series
            "query": m.get('wind_indicator', ''),
            "frequency": frequency,
            "unit": m.get('unit', ''),
            "transform": m.get('transform'),
            "tolerance": m.get('tolerance', 1e-6),
        }
        plan.append(entry)

    return plan


def main():
    conn = get_db()

    print("Building incremental update plan...")
    plan = build_plan(conn)

    # Save plan
    plan_path = Path('config/update_plan.json')
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    # Summary
    by_module = {}
    for entry in plan:
        mod = entry['module']
        by_module[mod] = by_module.get(mod, 0) + 1

    print(f"Update plan: {len(plan)} series ready for incremental update")
    for mod, count in sorted(by_module.items()):
        print(f"  {mod}: {count} series")

    if len(plan) == 0:
        print("\nNo verified series yet. Run Wind MCP verification first (Step 5).")
        print("All 141 mapped series are in 'mapping_pending' status.")
        print("Once Wind MCP is available, query and verify each series to move to 'verified'.")

    conn.close()


if __name__ == "__main__":
    main()
