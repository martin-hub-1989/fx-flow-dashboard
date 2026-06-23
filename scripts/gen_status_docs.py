"""
gen_status_docs.py — Generate status documents from DB + config (Loop 15).

Single source of truth: queries DB and config files, writes:
  - docs/PROGRESS_REPORT.md
  - docs/WIND_COVERAGE.md
  - docs/REVIEW_HANDOFF.md (status section)

No hand-maintained percentages; every number is computed.
"""
import json, sqlite3
from datetime import datetime
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "monthly_brief.sqlite"


def stats():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    s = {}
    s["series_total"] = c.execute("SELECT COUNT(*) FROM series").fetchone()[0]
    s["by_type"] = dict(Counter(r[0] for r in c.execute("SELECT series_type FROM series")))
    s["observations"] = c.execute("SELECT COUNT(*) FROM observations WHERE value IS NOT NULL").fetchone()[0]
    s["date_range"] = (c.execute("SELECT MIN(date),MAX(date) FROM observations WHERE value IS NOT NULL").fetchone())
    s["metric_definitions"] = c.execute("SELECT COUNT(*) FROM metric_definitions").fetchone()[0]
    s["modules"] = [r[0] for r in c.execute("SELECT DISTINCT module FROM series ORDER BY module")]
    # Wind mapping
    m = json.load(open(ROOT/"config/wind_mapping.json"))
    s["mapping_status"] = dict(Counter(x.get("status") for x in m if isinstance(x,dict) and x.get("series_id")))
    s["wind_verified"] = sum(1 for x in m if isinstance(x,dict) and x.get("wind_verified") is True)
    s["mapping_total"] = sum(1 for x in m if isinstance(x,dict) and x.get("series_id"))
    # update plan
    s["update_plan"] = len(json.load(open(ROOT/"config/update_plan.json")))
    # chart catalog
    cat = json.load(open(ROOT/"config/chart_catalog.json"))
    s["charts_total"] = sum(len(md["charts"]) for md in cat["modules"].values())
    s["charts_primary"] = sum(1 for md in cat["modules"].values() for ch in md["charts"] if ch["priority"]=="primary")
    s["charts_drilldown"] = s["charts_total"] - s["charts_primary"]
    s["scatter"] = sum(1 for md in cat["modules"].values() for ch in md["charts"] if ch.get("scatter"))
    s["seasonality"] = sum(1 for md in cat["modules"].values() for ch in md["charts"] if ch["chart_type"]=="seasonality_band")
    # chart-critical derived
    chart_sids=set()
    for md in cat["modules"].values():
        for ch in md["charts"]:
            for ds in ch["datasets"]: chart_sids.add(ds["series_id"])
            if ch.get("scatter"):
                chart_sids.add(ch["scatter_x"]["series_id"]); chart_sids.add(ch["scatter_y"]["series_id"])
    s["chart_sids"] = len(chart_sids)
    cached=[]
    for sid in chart_sids:
        r=c.execute("SELECT implementation FROM metric_definitions WHERE series_id=?",(sid,)).fetchone()
        if r and r[0] in ("excel_cached","excel_vlookup"): cached.append(sid)
    s["chart_cached"] = len(cached)
    # disposition
    disp = json.load(open(ROOT/"config/excel_chart_disposition.json"))
    s["disposition"] = dict(Counter(r["status"] for r in disp["dispositions"]))
    # recompute count
    s["python_recompute"] = c.execute("SELECT COUNT(*) FROM observations WHERE source='python_recompute'").fetchone()[0]
    # wind-written obs
    s["wind_mcp_obs"] = c.execute("SELECT COUNT(*) FROM observations WHERE source='wind_mcp'").fetchone()[0]
    # update runs
    s["runs"] = dict(Counter(r[0] for r in c.execute("SELECT status FROM update_runs")))
    s["revision_audits"] = c.execute("SELECT COUNT(*) FROM observation_revisions").fetchone()[0]
    c.close()
    return s


def gen_progress(s):
    wv_pct = (s["wind_verified"]/s["mapping_total"]*100) if s["mapping_total"] else 0
    return f"""# FX Flow 看板 — 进度报告

> 自动生成：{datetime.now().strftime('%Y-%m-%d %H:%M')} · 由 gen_status_docs.py 从数据库与配置生成

## 数据规模

| 指标 | 数值 |
|------|------|
| 总序列 | {s['series_total']} (raw {s['by_type'].get('raw',0)} / derived {s['by_type'].get('derived',0)} / manual {s['by_type'].get('manual',0)}) |
| 观测值 | {s['observations']:,} |
| 时间跨度 | {s['date_range'][0]} → {s['date_range'][1]} |
| 模块数 | {len(s['modules'])} |
| metric_definitions | {s['metric_definitions']} |
| Python 复算观测 | {s['python_recompute']} |
| Wind MCP 写入观测 | {s['wind_mcp_obs']} |
| revision 审计 | {s['revision_audits']} |

## Wind 映射

| 状态 | 数量 |
|------|------|
""" + "\n".join(f"| {k} | {v} |" for k,v in sorted(s["mapping_status"].items())) + f"""

- wind_verified=true：**{s['wind_verified']}** / {s['mapping_total']}（{wv_pct:.1f}%）
- 生产更新计划：{s['update_plan']} 条（仅 wind_verified）

## 图表

| 指标 | 数值 |
|------|------|
| 正式图表 | {s['charts_total']}（{s['charts_primary']} primary + {s['charts_drilldown']} drill-down）|
| 散点图 | {s['scatter']} |
| 季节性图 | {s['seasonality']} |
| 图表引用序列 | {s['chart_sids']} |
| chart-critical Excel 缓存 | {s['chart_cached']}（应为 0）|

## 66 张原图处置

| 状态 | 数量 |
|------|------|
""" + "\n".join(f"| {k} | {v} |" for k,v in s["disposition"].items()) + f"""

## 更新运行

{dict(s['runs'])}
"""


def gen_wind_coverage(s):
    return f"""# Wind 覆盖率

> 自动生成：{datetime.now().strftime('%Y-%m-%d %H:%M')}

## 映射状态

{json.dumps(s['mapping_status'], ensure_ascii=False, indent=2)}

## Wind verified 序列（{s['wind_verified']} 条）

真实 Wind MCP 闭环完成的序列，含精确 EDB code，可进入生产更新。
"""


def main():
    s = stats()
    (ROOT/"docs"/"PROGRESS_REPORT.md").write_text(gen_progress(s), encoding="utf-8")
    (ROOT/"docs"/"WIND_COVERAGE.md").write_text(gen_wind_coverage(s), encoding="utf-8")
    print("Generated docs/PROGRESS_REPORT.md + docs/WIND_COVERAGE.md")
    print(json.dumps(s, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
