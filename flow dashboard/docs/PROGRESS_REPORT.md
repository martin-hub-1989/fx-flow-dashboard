# FX Flow 看板 — 进度报告

> 自动生成：2026-06-25 11:40 · 由 gen_status_docs.py 从数据库与配置生成

## 数据规模

| 指标 | 数值 |
|------|------|
| 总序列 | 383 (raw 158 / derived 223 / manual 2) |
| 观测值 | 133,535 |
| 时间跨度 | 1994-01-31 → 2026-05-31 |
| 模块数 | 9 |
| metric_definitions | 224 |
| Python 复算观测 | 6792 |
| Wind MCP 写入观测 | 4 |
| revision 审计 | 0 |

## Wind 映射

| 状态 | 数量 |
|------|------|
| mapping_pending | 80 |
| no_data_in_db | 8 |
| no_result | 8 |
| not_applicable | 7 |
| verified_exact | 1 |
| verified_unit_transform | 44 |

- wind_verified=true：**5** / 148（3.4%）
- 生产更新计划：5 条（仅 wind_verified）

## 图表

| 指标 | 数值 |
|------|------|
| 正式图表 | 29（20 primary + 9 drill-down）|
| 散点图 | 2 |
| 季节性图 | 4 |
| 图表引用序列 | 79 |
| chart-critical Excel 缓存 | 0（应为 0）|

## 66 张原图处置

| 状态 | 数量 |
|------|------|
| retained | 28 |
| merged_into | 30 |
| deleted_with_reason | 7 |
| rebuilt_as | 1 |

## 文档边界 (v1 范围)

- **正式图表引用范围**：79 条序列全部有真实单位（unknown unit 0 条，应为 0）— 满足图表展示合同。
- **DB-only 中间列**：仍有 `Column_*` / unknown unit 的序列为 Excel 历史中间计算列，保留在 DB 但不属于 v1 展示范围（不进入 chart_catalog，不进入 series_catalog 主表）。
- **fx_fwd:AN (USDCNY)**：当前作为 raw 外部 seed 汇率序列（`series_type=raw`, `unit=CNY/USD`, `source=excel_seed`），历史值来自 Excel VLOOKUP 汇率查找表；后续建议完成 Wind USDCNY 月度汇率序列映射。

## 更新运行

{'completed': 28, 'cancelled': 2}
