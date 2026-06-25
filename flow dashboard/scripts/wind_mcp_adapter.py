"""
Wind MCP CLI adapter — production fetch module.
Replaces the fetch_via_wind_mcp() stub with real Wind MCP calls.

Usage:
    from wind_mcp_adapter import wind_mcp_query, wind_mcp_fetch_series
"""

import subprocess, json, os
from pathlib import Path

SKILL_DIR = os.path.expanduser("~/.claude/skills/wind-mcp-skill")
if os.path.islink(SKILL_DIR):
    SKILL_DIR = os.path.realpath(SKILL_DIR)

WIND_CLI = os.path.join(SKILL_DIR, "scripts", "cli.mjs")

if not os.path.exists(WIND_CLI):
    WIND_CLI = os.path.expanduser("~/.agents/skills/wind-mcp-skill/scripts/cli.mjs")


def wind_mcp_query(indicator_name, begin_date="20260101", end_date="20260622",
                   freq="月", magnitude="亿", currency="USD", timeout=90):
    """
    Query Wind MCP economic_data.get_economic_data.

    Args:
        indicator_name: Natural language indicator query (e.g. "中国:银行代客结售汇差额:经常项目:当月值")
        begin_date/end_date: yyyyMMdd format
        freq: 日/工作日/周/月/季/半年/年/年度
        magnitude: 个/千/万/百万/千万/亿/十亿/百亿/千亿/万亿
        currency: USD/CNY/EUR/JPY/...
        timeout: seconds

    Returns:
        dict with 'data' (date->value map), 'name', 'unit', 'code'
        or None on failure
    """
    params = json.dumps({
        "metricIdsStr": indicator_name,
        "beginDate": begin_date,
        "endDate": end_date,
        "freq": freq,
        "magnitude": magnitude,
        "currency": currency
    })

    try:
        result = subprocess.run(
            ["node", WIND_CLI, "call", "economic_data", "get_economic_data", params],
            capture_output=True, text=True, timeout=timeout, cwd=SKILL_DIR
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return None

    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    content = data.get('content', [])
    if not content:
        return None

    text = content[0].get('text', '')
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    indicators = parsed.get('data', {}).get('indicatorInfo', [])
    dates = parsed.get('data', {}).get('date', [])

    if not indicators:
        return None

    # Return the first matching indicator
    ind = indicators[0]
    wind_map = {}
    for d, v in zip(dates, ind.get('data', [])):
        if v is not None:
            d_str = str(d)[:4] + '-' + str(d)[4:6] + '-' + str(d)[6:8]
            wind_map[d_str] = float(v)

    return {
        'data': wind_map,
        'name': ind.get('name', ''),
        'unit': ind.get('unit', ''),
        'code': ind.get('code', ''),
        'n_points': len(wind_map),
        'all_names': [i.get('name', '') for i in indicators[:5]],
    }


def wind_mcp_fetch_series(wind_indicator, last_db_date, second_last_date=None):
    """
    Fetch new data for a series from Wind MCP.

    Args:
        wind_indicator: Wind indicator name query
        last_db_date: Last date in DB (YYYY-MM-DD)
        second_last_date: Second-to-last date for overlap validation

    Returns:
        {date: value} dict of NEW data (after last_db_date), or None
    """
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta

    last_dt = datetime.strptime(last_db_date[:10], '%Y-%m-%d')
    # Fetch from second-last date for overlap
    start_dt = datetime.strptime(second_last_date[:10], '%Y-%m-%d') if second_last_date else (
        last_dt - relativedelta(months=6)
    )
    end_dt = datetime.now()

    begin = start_dt.strftime('%Y%m%d')
    end = end_dt.strftime('%Y%m%d')

    result = wind_mcp_query(
        wind_indicator,
        begin_date=begin,
        end_date=end,
        freq="月",
        magnitude="亿",
        currency="USD"
    )

    if not result:
        # Try CNY
        result = wind_mcp_query(
            wind_indicator,
            begin_date=begin,
            end_date=end,
            freq="月",
            magnitude="亿",
            currency="CNY"
        )

    if not result:
        return None

    # Filter to only new data (after last_db_date)
    new_data = {d: v for d, v in result['data'].items() if d > last_db_date}
    return new_data if new_data else None
