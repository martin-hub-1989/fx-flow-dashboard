# PROGRESS — FX Flow 看板

> 实时进度追踪。每完成一个子任务后立即更新。
> 遵循「Agent 工作规范」`【跨平台工作指南】agent.md` 状态管理约定。

## 最后更新：2026-06-25

## 当前状态
项目整理完成：核心文件已归入 `flow dashboard/`，开发过程文档归入 `相关开发文档/`，全量测试通过；4 个状态管理文件已按指引创建。

## 已完成
- [x] POST_EXECUTION_CORRECTION_LOOP Loop 1-5（VLOOKUP 门禁/unit 污染/staging 元数据/数据字典口径/最终复审）→ 详见 `相关开发文档/POST_EXECUTION_CORRECTION_LOOP.md` + `docs/REVIEW_HANDOFF.md`
- [x] PR #1 合并到 main（commit 1808a92）→ https://github.com/martin-hub-1989/fx-flow-dashboard/pull/1
- [x] 目录结构重构 → `flow dashboard/` + `相关开发文档/`（commit a92a470）
- [x] 4 处硬编码路径改相对路径 → `scripts/import_excel_seed.py` `build_chart_catalog.py` `build_chart_disposition.py` `tests/test_loop13_disposition.py`
- [x] 按「Agent 工作规范」创建状态文件 → `CONTEXT.md` `PLAN.md` `PROGRESS.md` `DECISIONS.md`

## 当前真实数据快照（权威源：SQLite + config，由 gen_status_docs.py 复核）

| 维度 | 值 |
|------|-----|
| series | 383 (raw 158 / derived 223 / manual 2) |
| observations | 137,626（其中非空 133,535）|
| 时间跨度 | 1994-01-31 → 2026-05-31 |
| metric_definitions | 224 |
| Python 复算观测 | 6,792 |
| Wind MCP 写入观测 | 4 (2026-05-31, source=wind_mcp) |
| Wind verified 序列 | 5/148（fx_fwd:B/C/F, fx_cspot:H/O）|
| 生产 update_plan | 5 条（仅 wind_verified，unit=亿美元）|
| 正式图表 | 29（20 primary + 9 drilldown）|
| 散点图 | 2（含 OLS 回归 + R²）|
| 季节性图 | 4（1-12 月 band）|
| chart-critical Excel 缓存 | 0（应为 0）|
| chart-critical unknown unit | 0（应为 0）|
| 66 图处置 | 66/66（retained 28/merged 30/rebuilt 1/deleted 7）|
| update_runs | 28 completed + 2 cancelled（0 running）|
| revision 审计 | 0 |

## 测试状态
- `python3 -m pytest tests/` → 68 passed（在 `flow dashboard/` 下运行）
- `python3 scripts/test_all.py` → 84 passed
- `python3 scripts/validate_all.py` → 8/8 checks passed
- `node tests/browser_check.js` → 桌面+移动无溢出，0 console 错误
- `node tests/test_loop14_export_check.js` → PNG+CSV 导出正常

## 下一步
- [ ] 修正 README.md 过时数字：序列数 385→383、3.证券FI 56→54、合计 385→383（输入：`flow dashboard/README.md`）
- [ ] （可选）扩大 Wind 验证：80 条 mapping_pending 逐条用精确指标名查 Wind（输入：`config/wind_mapping.json`）
- [ ] （可选）fx_fwd:F 限流补 fetch（Wind 间歇限流导致该序列 fetch 不全）
- [ ] （可选）fx_fwd:AN 映射 Wind USDCNY 月度汇率序列，替换 Excel seed

## 阻塞项
无。

## 已知限制（非阻塞）
1. **Wind verified 仅 5 条**：其余 143 条映射来自 iFind 历史验证，历史可用但未达生产门禁。
2. **fx_fwd:F 限流**：Wind MCP 间歇限流，下次重试可补全。
3. **DB series.unit='monthly_amount'**：5 条 verified 序列的 DB unit 是频率式泛标签，已被 build_plan 绕过（用 mapping 字段）；DB unit 本身的数据质量待后续统一。
4. **validate_update.py --dry-run 孤立 run**：start_update_run 会 commit 一行 running，rollback 不删除（已手动标记 cancelled，非代码改动）；建议后续让 dry-run 不持久化 run 行。
