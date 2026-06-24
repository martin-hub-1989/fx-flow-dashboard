"""
gen_status_docs.py — Generate status documents from DB + config (Loop 15 / Loop 4).

Single source of truth: queries DB and config files, writes:
  - docs/PROGRESS_REPORT.md
  - docs/WIND_COVERAGE.md
  - docs/REVIEW_HANDOFF_STATUS.md  (Loop 4: generated current-status snapshot)

REVIEW_HANDOFF.md itself is NOT regenerated (it carries hand-maintained
historical execution records). This script only prepends a one-line pointer
to its top, directing readers to REVIEW_HANDOFF_STATUS.md for the live
snapshot — the documented exception to the 'no hand-edits to generated docs'
rule. (Earlier docstring wrongly claimed main() wrote REVIEW_HANDOFF.md's
status section; that was the latent trap Loop 1 reviewer flagged.)

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
        # prefix check (not exact match) so variants like excel_vlookup_lookup
        # cannot slip past the chart-critical gate (matches test_loop14_gates).
        if r and r[0] and r[0].startswith(("excel_cached","excel_vlookup")): cached.append(sid)
    s["chart_cached"] = len(cached)
    # chart-critical unknown-unit count (Loop 4 boundary: must be 0 for v1).
    sids_list = list(chart_sids)
    if sids_list:
        s["chart_critical_unknown_unit"] = c.execute(
            "SELECT COUNT(*) FROM series WHERE series_id IN ({}) "
            "AND (unit IS NULL OR unit='' OR unit='unknown')".format(
                ",".join("?" * len(sids_list))),
            sids_list,
        ).fetchone()[0]
    else:
        s["chart_critical_unknown_unit"] = 0
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

## 文档边界 (v1 范围)

- **正式图表引用范围**：{s['chart_sids']} 条序列全部有真实单位（unknown unit {s['chart_critical_unknown_unit']} 条，应为 0）— 满足图表展示合同。
- **DB-only 中间列**：仍有 `Column_*` / unknown unit 的序列为 Excel 历史中间计算列，保留在 DB 但不属于 v1 展示范围（不进入 chart_catalog，不进入 series_catalog 主表）。
- **fx_fwd:AN (USDCNY)**：当前作为 raw 外部 seed 汇率序列（`series_type=raw`, `unit=CNY/USD`, `source=excel_seed`），历史值来自 Excel VLOOKUP 汇率查找表；后续建议完成 Wind USDCNY 月度汇率序列映射。

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


REVIEW_HANDOFF_POINTER = "> 当前状态见 docs/REVIEW_HANDOFF_STATUS.md (自动生成)\n"


def gen_review_handoff_status(s):
    """Loop 4: generated current-status snapshot, written to
    docs/REVIEW_HANDOFF_STATUS.md. Replaces the hand-maintained top status
    section of REVIEW_HANDOFF.md (which is no longer edited by this script)."""
    wv_pct = (s["wind_verified"]/s["mapping_total"]*100) if s["mapping_total"] else 0
    disp = ", ".join(f"{k} {v}" for k, v in sorted(s["disposition"].items()))
    return f"""# Review Handoff — 当前状态 (自动生成)

> 自动生成：{datetime.now().strftime('%Y-%m-%d %H:%M')} · 由 gen_status_docs.py 从数据库与配置生成
> 历史执行记录与限制说明见 docs/REVIEW_HANDOFF.md（手维护；本文件仅承载当前快照，不覆盖历史）

## 真实数据快照

| 维度 | 值 |
|------|-----|
| series | {s['series_total']} (raw {s['by_type'].get('raw',0)} / derived {s['by_type'].get('derived',0)} / manual {s['by_type'].get('manual',0)}) |
| observations (非空) | {s['observations']:,} |
| metric_definitions | {s['metric_definitions']} |
| 时间跨度 | {s['date_range'][0]} → {s['date_range'][1]} |
| Python 复算观测 | {s['python_recompute']:,} |
| Wind MCP 写入观测 | {s['wind_mcp_obs']} |
| Wind verified 序列 | {s['wind_verified']}/{s['mapping_total']}（{wv_pct:.1f}%）|
| 生产 update_plan | {s['update_plan']} 条（仅 wind_verified）|
| 正式图表 | {s['charts_total']}（{s['charts_primary']} primary + {s['charts_drilldown']} drill-down）|
| 散点图 | {s['scatter']} |
| 季节性图 | {s['seasonality']} |
| 图表引用序列 | {s['chart_sids']} |
| chart-critical Excel 缓存 | {s['chart_cached']}（应为 0）|
| chart-critical unknown unit | {s['chart_critical_unknown_unit']}（应为 0）|
| 66 图处置 | {sum(s['disposition'].values())} ({disp}) |
| update_runs | {dict(s['runs'])} |
| revision 审计 | {s['revision_audits']} |

## 文档边界 (v1 范围)

- **正式图表引用范围**：{s['chart_sids']} 条序列全部有真实单位（unknown unit {s['chart_critical_unknown_unit']} 条，应为 0）— 满足图表展示合同。
- **DB-only 中间列**：仍有 `Column_*` / unknown unit 的序列为 Excel 历史中间计算列，保留在 DB 但不属于 v1 展示范围（不进入 chart_catalog，不进入 series_catalog 主表）。
- **fx_fwd:AN (USDCNY)**：当前作为 raw 外部 seed 汇率序列（`series_type=raw`, `unit=CNY/USD`, `source=excel_seed`），历史值来自 Excel VLOOKUP 汇率查找表；后续建议完成 Wind USDCNY 月度汇率序列映射。

> 不出现"全库完全清理"等超出事实的表述：正式图表口径已清理，全库中间列仍保留待处理。
"""


def write_review_handoff_pointer():
    """Idempotently prepend a one-line pointer to the top of REVIEW_HANDOFF.md
    directing readers to the generated REVIEW_HANDOFF_STATUS.md. Does NOT
    rewrite the hand-maintained historical content below — the documented
    exception to the 'no hand-edits to generated docs' rule. Returns True if
    the pointer was added, False if it was already present."""
    p = ROOT / "docs" / "REVIEW_HANDOFF.md"
    if not p.exists():
        return False
    text = p.read_text(encoding="utf-8")
    needle = "REVIEW_HANDOFF_STATUS.md (自动生成)"
    head = "\n".join(text.splitlines()[:3])
    if needle in head:
        return False  # already pointed
    p.write_text(REVIEW_HANDOFF_POINTER + text, encoding="utf-8")
    return True


def main():
    s = stats()
    (ROOT/"docs"/"PROGRESS_REPORT.md").write_text(gen_progress(s), encoding="utf-8")
    (ROOT/"docs"/"WIND_COVERAGE.md").write_text(gen_wind_coverage(s), encoding="utf-8")
    (ROOT/"docs"/"REVIEW_HANDOFF_STATUS.md").write_text(gen_review_handoff_status(s), encoding="utf-8")
    added = write_review_handoff_pointer()
    actions = "Generated docs/PROGRESS_REPORT.md + docs/WIND_COVERAGE.md + docs/REVIEW_HANDOFF_STATUS.md"
    if added:
        actions += " (+ pointer prepended to docs/REVIEW_HANDOFF.md)"
    print(actions)
    print(json.dumps(s, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
