# CONTEXT — FX Flow 看板

> 项目背景、术语定义、核心假设。仅当理解发生根本变化时更新。
> 遵循「Agent 工作规范」`【跨平台工作指南】agent.md` 状态管理约定。

## 项目定位

将 `FX Chartbook - Flow 0515.xlsx`（手工维护的外汇结售汇与跨境资金流月报）重构为**可维护的本地交互式看板**。不是重写：保留原有业务口径，只把数据合同、更新链、图表语义工程化。

## 核心数据流

```
Excel 历史种子 (只读，永远不改)
      ↓ import_excel_seed.py (幂等)
SQLite (data/monthly_brief.sqlite)
      ↓ build_update_plan.py → fetch_wind.py → validate_update.py
Wind MCP 生产更新 (两点重叠验证 + revision 审计)
      ↓ recompute_derived.py (derived 拓扑复算)
chart_catalog.json (图表单一事实源, 29 张)
      ↓ generate_dashboard.py
单文件 Chart.js HTML (reports/fx_flow_dashboard.html, 离线可用)
```

## 术语定义

| 术语 | 含义 |
|------|------|
| series | 一条数据序列 (series_id = `{module_prefix}:{excel_col}`，如 `fx_fwd:B`) |
| raw / derived / manual | 序列三种类型：原始种子 / 公式衍生 / 手工录入 |
| chart-critical | 被 chart_catalog.json 引用的序列，是看板的展示合同，必须真实可复算 |
| wind_verified | 经真实 Wind MCP 闭环验证 (含精确 EDB code + 两点重叠通过)，可进入生产更新链 |
| mapping_pending | iFind 历史已验证但未用 Wind 重新确认，历史可用但未达生产门禁 |
| excel_cached / excel_vlookup | derived 仍依赖 Excel 缓存/VLOOKUP 的实现标签 —— **chart-critical 序列不得以此形式存在** |
| external_lookup_seed | fx_fwd:AN 的实现标签：raw 外部汇率 seed (USDCNY)，历史来自 Excel 查找表，待 Wind 汇率映射 |

## 核心假设

1. **原 Excel 严格只读** —— 永不覆写、改名、清洗公式，仅作为历史种子与业务口径参照。
2. **Wind 是目标权威源** —— 生产更新用 Wind MCP；iFind 仅作历史验证，结果必须标 `external_source=ifind_edb`、`wind_verified=False`，不得冒充 Wind。
3. **两点重叠验证** —— 写入前必须 ≥2 个真实重叠日期通过容差，防止数据拟合/错位。
4. **不静默覆盖修订** —— 生产 raw 用 `INSERT`（非 `INSERT OR REPLACE`），修订走 `observation_revisions` 审计表。
5. **生成型文档不手改** —— DATA_DICTIONARY/PROGRESS_REPORT/WIND_COVERAGE/REVIEW_HANDOFF_STATUS 均由脚本生成；REVIEW_HANDOFF.md 例外（手维护历史 + 脚本只加一行指针）。
6. **chart_catalog.json 是图表单一事实源** —— 不再自动选前 N 条序列画图。

## 数据库 schema (5+1 表)

- `series` — 序列元数据 (series_id, display_name, module, series_type, unit, source...)
- `observations` — 观测值 (series_id, date, value, source) · PK(series_id,date)
- `metric_definitions` — 衍生公式 (implementation, formula_description, input_series_json...)
- `update_runs` — 更新运行日志
- `validation_events` — 校验事件
- `observation_revisions` — 修订审计 (Loop 4 新增)

## 覆盖模块 (9 个)

`3.即远期`(44) · `3.代客即期`(47) · `3.涉外收付`(55) · `3.货物贸易`(46) · `3.贸易商`(46) · `3.服务贸易`(6) · `3.FDI`(55) · `3.证券EQ`(30,日度) · `3.证券FI`(54) — 合计 383 序列。

## 目录结构 (2026-06-25 重构后)

```
Martin Monthly Brief/
├── flow dashboard/          # ★ 项目核心
│   ├── config/ data/ docs/ reports/ scripts/ templates/ tests/
│   ├── FX Chartbook - Flow 0515.xlsx   # 原始 Excel (只读)
│   └── README.md / pytest.ini / package.json
└── 相关开发文档/             # 开发过程文档 (不跟踪入 git)
    ├── *LOOP*.md            # 已执行完毕的执行计划
    └── docs/ .inspection/ .superpowers/
```

脚本内路径均为相对路径（`Path(__file__).resolve().parent...`），迁移目录后仍可运行。

---

## 项目补充信息

> 2026-06-25 by Martin
> - 本项目核心关注外汇结售汇与跨境资金流，报告风格偏买方内部备忘录
> - 数据口径：Wind 为权威源，iFind 作历史验证备选
> - 看板 HTML 需离线可用（单文件，Chart.js + datalabels 内联）

<!-- 新增内容请在条目前标注写入者和日期 -->
