# DECISIONS — FX Flow 看板

> 关键决策及其理由。每次做出影响后续的决策时追加，不删除已有记录。
> 遵循「Agent 工作规范」：读到此处记录后不自行推翻，需修改先向用户确认。

## 2026-06-23 — Wind 与 iFind 数据源口径

**决定**：生产更新以 Wind MCP 为权威源；iFind EDB 仅作历史验证备选，其结果必须标 `external_source=ifind_edb`、`wind_verified=False`，不得冒充 Wind。
**理由**：原 Excel 用 Wind 数据，只要提取数据能和历史匹配，Wind/iFind 都可接受；但来源必须如实标注，避免 iFind 被误当 Wind 用于生产。
**影响**：wind_mapping.json 中 148 条映射，仅 5 条标 `wind_verified=true` 可进生产计划；80 条 `mapping_pending`（iFind 已验证但未 Wind 确认）仅历史可用，不进 update_plan。

## 2026-06-23 — chart-critical derived 本地复算

**决定**：把画图用得上的 derived 指标搞清楚计算逻辑，在本地 Python 重算，不再依赖 Excel 缓存。
**理由**：看板需可信可复算，Excel 公式无法纳入版本化数据合同。
**影响**：6 个图表关键 derived 迁移到 Python 复算（fx_fwd:AE/Y、trade_goods:AC/AD/U、fx_fwd:AN），0% 误差；chart-critical 序列的 `implementation` 不得为 `excel_cached`/`excel_vlookup*`（Loop 1 前缀门禁）。

## 2026-06-23 — fx_fwd:AN 作为 raw 外部汇率 seed

**决定**：fx_fwd:AN（USDCNY 汇率）重标为 `external_lookup_seed`（raw 类型），保留 Excel seed 历史值，不当作 derived 复算。
**理由**：本质是外部汇率查找，非 Excel 公式衍生；当时未找到并验证 USDCNY 月度 Wind 指标（Plan B 不可行）。
**影响**：fx_fwd:AN 不进 chart-critical derived 检查；历史值仍为 `excel_seed`，后续应映射 Wind USDCNY 月度汇率序列替换。

## 2026-06-23 — sec_fi:BE/BF 删除

**决定**：删除 sec_fi:BE/BF 两列数据，以后不再处理。
**理由**：经测试证明它们是中债登/上清所独立公布的官方合计，无法由现有债券分项 SUM 汇总得到（误差 160-258%），不能作为 derived 重算。
**影响**：DB 与 wind_mapping 中移除这两列；不进任何图表或更新链。

## 2026-06-23 — 季节性辅助列标 not_applicable

**决定**：3 条季节性辅助列标为 `not_applicable`，不进 Wind 验证。
**理由**：Excel 占位列，无业务序列含义。
**影响**：wind_mapping 中 7 条 `not_applicable`（含此 3 条）。

## 2026-06-23 — 仓库公开 + 不上传 Excel/SQLite/HTML

**决定**：GitHub 仓库 `fx-flow-dashboard` 设为 Public；不上传原 Excel、SQLite、生成的 HTML（gitignore）；保留 config 中的样本金融值推送。
**理由**：用户知情并接受样本值公开风险；代码/配置/文档为可复现资产，数据文件本地保留。
**影响**：`.gitignore` 排除 `FX Chartbook - Flow 0515.xlsx`、`data/monthly_brief.sqlite`、`reports/fx_flow_dashboard.html`、`data/staging_fetched.json`、`待处理数据.xlsx`、`node_modules/`。

## 2026-06-24 — Loop 2 DB unit 绕过

**决定**：build_update_plan 的生产 `unit` 不读 DB `series.unit`（值为 `monthly_amount`，是频率式泛标签），改用 `target_unit → wind_unit_confirmed → ""` 优先级 + 数值守卫。
**理由**：DB unit 语义非货币量纲，放进生产计划会产生无意义 `monthly_amount`；真实单位在 Wind 验证字段。
**影响**：unit 解析逻辑改变，已记录于 REVIEW_HANDOFF 真实限制 #6；DB unit 本身的数据质量问题留待后续。

## 2026-06-25 — 目录结构重构

**决定**：项目分两个文件夹 —— `flow dashboard/`（核心文件）+ `相关开发文档/`（开发过程文档，不跟踪入 git）。
**理由**：分离项目产物与历史开发文档，降低认知负担；4 处硬编码路径改相对路径。
**影响**：所有脚本路径改为 `Path(__file__).resolve().parent...`；根 `.gitignore` 排除 `相关开发文档/`。
