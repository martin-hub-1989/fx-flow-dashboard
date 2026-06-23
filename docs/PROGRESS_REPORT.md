# FX Flow 看板 — 进度报告

> 自动生成：2026-06-23 20:38 · 由 gen_status_docs.py 从数据库与配置生成

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

## 更新运行

{'completed': 28, 'cancelled': 1}
