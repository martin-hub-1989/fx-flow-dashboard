# Review Handoff — 当前状态 (自动生成)

> 自动生成：2026-06-24 22:07 · 由 gen_status_docs.py 从数据库与配置生成
> 历史执行记录与限制说明见 docs/REVIEW_HANDOFF.md（手维护；本文件仅承载当前快照，不覆盖历史）

## 真实数据快照

| 维度 | 值 |
|------|-----|
| series | 383 (raw 158 / derived 223 / manual 2) |
| observations (非空) | 133,535 |
| metric_definitions | 224 |
| 时间跨度 | 1994-01-31 → 2026-05-31 |
| Python 复算观测 | 6,792 |
| Wind MCP 写入观测 | 4 |
| Wind verified 序列 | 5/148（3.4%）|
| 生产 update_plan | 5 条（仅 wind_verified）|
| 正式图表 | 29（20 primary + 9 drill-down）|
| 散点图 | 2 |
| 季节性图 | 4 |
| 图表引用序列 | 79 |
| chart-critical Excel 缓存 | 0（应为 0）|
| chart-critical unknown unit | 0（应为 0）|
| 66 图处置 | 66 (deleted_with_reason 7, merged_into 30, rebuilt_as 1, retained 28) |
| update_runs | {'completed': 28, 'cancelled': 2} |
| revision 审计 | 0 |

## 文档边界 (v1 范围)

- **正式图表引用范围**：79 条序列全部有真实单位（unknown unit 0 条，应为 0）— 满足图表展示合同。
- **DB-only 中间列**：仍有 `Column_*` / unknown unit 的序列为 Excel 历史中间计算列，保留在 DB 但不属于 v1 展示范围（不进入 chart_catalog，不进入 series_catalog 主表）。
- **fx_fwd:AN (USDCNY)**：当前作为 raw 外部 seed 汇率序列（`series_type=raw`, `unit=CNY/USD`, `source=excel_seed`），历史值来自 Excel VLOOKUP 汇率查找表；后续建议完成 Wind USDCNY 月度汇率序列映射。

> 不出现"全库完全清理"等超出事实的表述：正式图表口径已清理，全库中间列仍保留待处理。
