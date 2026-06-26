# PLAN — FX Flow 看板

> 当前阶段的目标、计划、约束。阶段切换或方向调整时更新。
> 遵循「Agent 工作规范」`【跨平台工作指南】agent.md` 状态管理约定。

## 当前阶段：v1 维护基线已建立

POST_EXECUTION_CORRECTION_LOOP 已全部完成并合并。项目处于**可信的后续生产更新基线**状态：数据合同、测试门禁、状态文档生成链均已修正。下一步是按需扩大 Wind 闭环 + 周期性月度更新。

## 阶段目标

1. **保持基线可信**：任何后续改动不得破坏既有数据合同（两点重叠、不静默覆盖、不冒充 Wind、chart-critical 不退回 Excel 缓存）。
2. **周期性月度更新**：每月初用 Wind MCP 拉取上月数据，经两点重叠验证后写入。
3. **逐步扩大 Wind 闭环**：将 80 条 mapping_pending 中的高频/重要序列用精确 Wind 指标名重新验证。

## 标准月度更新流程

```bash
cd "flow dashboard"
python3 scripts/build_update_plan.py     # 生成计划（仅 wind_verified）
python3 scripts/fetch_wind.py             # 真实 Wind 拉取 + transform + staging
python3 scripts/validate_update.py        # 两点重叠验证 + 安全写入 + revision 审计
python3 scripts/generate_dashboard.py     # 重生成 HTML 看板
python3 -m pytest tests/ -q               # 全量验证
python3 scripts/gen_status_docs.py        # 重生成状态文档
```

> 注意：脚本需在 `flow dashboard/` 目录下运行（路径均为相对该目录）。

## 约束（不可违反）

- **不改原 Excel** —— `FX Chartbook - Flow 0515.xlsx` 只读。
- **不冒充 Wind** —— iFind 结果标 `external_source=ifind_edb`、`wind_verified=False`。
- **不手改生成型文档** —— 修生成脚本再重新生成（REVIEW_HANDOFF.md 例外：仅脚本加一行指针）。
- **不用 INSERT OR REPLACE 写生产 raw** —— 用 INSERT + observation_revisions 审计。
- **两点重叠强制** —— 写入前 ≥2 个真实重叠日期通过容差。
- **chart-critical 不退回 Excel 缓存** —— implementation 不得 `excel_cached`/`excel_vlookup*` 前缀。
- **不推翻 DECISIONS.md** —— 需改先向用户确认。

## 关键脚本索引

| 用途 | 脚本 |
|------|------|
| 导入 Excel 种子（幂等）| `scripts/import_excel_seed.py` |
| 复算衍生指标 | `scripts/recompute_derived.py` |
| 生成更新计划 | `scripts/build_update_plan.py` |
| Wind MCP 拉取 | `scripts/fetch_wind.py`（→ `wind_mcp_adapter.py`）|
| 两点重叠验证+安全写入 | `scripts/validate_update.py`（→ `safe_write.py`）|
| derived 依赖图复算 | `scripts/dependency_graph.py` |
| 新序列 Wind 验证闭环 | `scripts/wind_closure.py` |
| 构建图表目录 | `scripts/build_chart_catalog.py` / `build_chart_disposition.py` |
| 生成 HTML 看板 | `scripts/generate_dashboard.py` |
| 生成数据字典 | `scripts/gen_data_dictionary.py` |
| 生成状态文档 | `scripts/gen_status_docs.py` |
| 全量验证 | `scripts/validate_all.py` / `scripts/test_all.py` |

## 状态文件职责（本工作规范）

| 文件 | 用途 | 更新频率 |
|------|------|---------|
| `CONTEXT.md` | 项目背景、术语、核心假设 | 仅根本理解变化时 |
| `PLAN.md` | 阶段目标、计划、约束 | 阶段切换/方向调整时 |
| `PROGRESS.md` | 实时进度追踪 | 每完成子任务后立即 |
| `DECISIONS.md` | 关键决策及理由 | 每次影响后续的决策时追加 |
