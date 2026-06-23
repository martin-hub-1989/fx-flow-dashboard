# 项目方向修正执行 Loop（历史文件）

> 本文件已与 `CHART_IMPLEMENTATION_LOOP.md` 合并为
> `MASTER_EXECUTION_LOOP.md`。执行 agent 应以统一 Loop 为准；
> 本文件只保留用于追溯原审阅结论。

## 目标

在不推翻 SQLite 优先架构的前提下，修复当前项目的数据源偏移、错误映射、更新安全、指标血缘和 HTML 失效问题，使项目重新满足原 `AGENT_LOOP.md` 的约束。

## 执行原则

- 不覆盖原 Excel。
- 不回退或删除用户及其他 agent 的未提交改动。
- 修复期间冻结新增图表和新增映射。
- 每轮只解决一个可验证问题集。
- 每轮结束更新 `docs/REVIEW_HANDOFF.md`。
- 任何无法证明正确的数据，不得进入生产状态。

## Loop 0：建立审阅基线

1. 读取：
   - `docs/CURRENT_PROJECT_REVIEW_20260622.md`
   - `AGENT_LOOP.md`
   - 当前 Git 状态
   - `docs/REVIEW_HANDOFF.md`
2. 保存当前数据库、配置和 HTML 的校验摘要。
3. 标记并保留当前未结束的 update run，不要静默删除。
4. 建立本轮修正清单和完成门禁。

## Loop 1：恢复数据源契约

1. 将“目标数据源”明确为 Wind MCP。
2. 盘点当前 iFind 代码、配置和结果。
3. 将所有 iFind 验证结果降级为：
   - `external_candidate`
   - `needs_wind_verification`
4. 禁止在文档中把 iFind 写成 Wind。
5. 按本机 Wind 技能和工具合约实现一个 1 条序列的小样本调用。
6. 若 Wind MCP 不支持某类序列，标记为 unsupported，并记录真实限制。

完成门禁：

- 数据来源名称真实；
- Wind 调用不是 stub；
- 至少一个原始序列通过 Wind MCP 小样本查询；
- 失败路径有明确状态，不做 iFind 静默替代。

## Loop 2：重建元数据主表

1. 选择 `config/series_catalog.json` 为版本管理主表，SQLite series 为运行时镜像。
2. 修复：
   - `Column_*`
   - unknown unit
   - 日期列被当作序列
   - 频率错误
   - raw/derived/manual 分类错误
3. 每个序列补齐：
   - 名称
   - 单位
   - 频率
   - 原始/衍生属性
   - Excel 来源范围
   - 更新方式
4. 从 catalog 自动生成 SQLite 元数据和 Data Dictionary。

完成门禁：

- catalog、SQLite、Data Dictionary 数量一致；
- 目标展示序列没有 `Column_*`；
- 目标展示序列单位不得为空；
- 日期轴不作为业务序列。

## Loop 3：修复衍生指标和血缘

1. 将 224 条 derived 分成：
   - 已 Python 复算；
   - 待迁移；
   - 仅供 Excel 辅助、不进入看板；
2. 填充 `metric_definitions`。
3. 优先修复所有进入图表方案的指标。
4. 修复 TTM：
   - TTM 流量使用 rolling sum；
   - MMA 使用 moving average；
   - 两者不得混用。
5. 迁移必要的 VLOOKUP、PERCENTRANK 和 CORREL。
6. 每个指标按最近 24 个有效点和完整公共区间分别校验。
7. 报告必须按“指标通过率”和“数据点通过率”分别呈现。

完成门禁：

- 所有进入正式图表的 derived 指标均为 Python 复算；
- `metric_definitions` 不为空且覆盖正式图表指标；
- TTM/MMA 语义正确；
- 不再用 Excel 缓存 derived 值驱动正式图表。

## Loop 4：重做 Wind 映射验证

允许的单位转换必须来自受控列表：

- identity
- divide_1e4
- divide_1e8
- multiply_100 / divide_100
- sign_flip
- currency_conversion_by_date
- cumulative_to_period

禁止：

- 从两条序列的中位数比值生成任意缩放因子；
- 通过放宽容差把相似指标标为已验证；
- 用一个重叠点标记 verified；
- 用不同经济概念替代原指标。

建议门禁：

- 月度：至少 12 个重叠点，最近 2 点必须一致；
- 日度：至少 40 个重叠点，最近 5 个交易日必须一致；
- 季度：至少 4 个重叠季度，最近 2 季必须一致；
- 单位转换后平均相对误差通常不超过 0.1%；
- 历史修订单独标记，不计入单位转换误差。

状态限定为：

- `verified_exact`
- `verified_unit_transform`
- `revision_review`
- `mapping_pending`
- `unsupported`
- `no_result`
- `manual`
- `not_applicable`

## Loop 5：修复更新计划

1. 直接查询数据库最后两个实际观测点。
2. `validation_dates` 必须是这两个真实日期。
3. 日度使用交易日数据，不做自然日推算。
4. 月度和季度保留正确的 period end。
5. 两个重叠日期不得重复。
6. update plan 必须从最新 mapping 自动生成，禁止保存陈旧的 2 条样例冒充正式计划。

完成门禁：

- 每条计划有两个不同、真实存在的 validation dates；
- update plan 条数与生产可更新映射数一致；
- 频率和日期标签正确。

## Loop 6：实现真实 Wind 拉取和安全写入

1. `fetch_via_wind_mcp()` 实现真实调用。
2. 拉取结果先写 staging，不直接改数据库。
3. staging 保存：
   - 原始响应来源；
   - 查询参数；
   - 数据单位；
   - 拉取时间；
   - 变换前后值；
4. 无两个有效重叠点时拒绝自动写入。
5. 新值和历史修订分开处理。
6. 禁止 `INSERT OR REPLACE` 静默覆盖历史数据。
7. 建立 revision audit 表或等价结构。
8. 写入成功后只复算受影响的下游 derived 指标。
9. 新增/修订计数必须在写入前判定。
10. 所有失败 run 必须结束并记录状态。

## Loop 7：恢复 HTML 基线

1. 修复生成器的 JavaScript 引号错误。
2. 每次生成后强制执行：
   - HTML 结构检查；
   - 内联 JavaScript `node --check`；
   - 页面初始化测试；
3. 移除“自动取前 6 个 raw 序列”逻辑。
4. 图表配置改为 `config/chart_catalog.json`。
5. 在执行 `CHART_IMPLEMENTATION_LOOP.md` 前，只保留一个最小可运行的即远期页面。

完成门禁：

- HTML JavaScript 语法通过；
- 页面可初始化；
- 所有图表必须来自明确配置，不允许自动猜测。

## Loop 8：补生产级测试

必须新增测试：

- 任意比例因子不得通过映射验证；
- 语义不一致的指标不得通过；
- 只有一个重叠点不得通过；
- 无重叠点不得通过；
- validation dates 必须来自数据库最后两个点；
- 季度日期不能重复；
- 新增和修订计数正确；
- 历史修订不会静默覆盖；
- raw 更新后触发下游复算；
- TTM 使用 rolling sum；
- 生成 HTML 通过 JavaScript 语法检查；
- chart catalog 引用的所有 series 均存在。

## Loop 9：重新生成文档

文档不得手工维护冲突数字。由代码生成：

- series 数量；
- raw/derived/manual 数量；
- Wind 覆盖率；
- 更新计划条数；
- 图表数量；
- 测试结果；
- 数据截至日期。

更新：

- README
- DATA_DICTIONARY
- WIND_COVERAGE
- PROGRESS_REPORT
- REVIEW_HANDOFF

## 停止条件

同时满足以下条件才进入图表实施：

- Wind MCP 有真实成功调用；
- 不存在任意数据拟合缩放因子；
- 两点重叠校验严格执行；
- 生产更新不再是 stub；
- 正式图表指标全部 Python 复算；
- metric_definitions 完整；
- HTML 可运行；
- 所有 P0 测试通过。
