# Martin Monthly Brief：数据修正与图表实施统一 Loop

## 1. 最终目标

在不推翻现有 SQLite 优先架构的前提下，将 `FX Chartbook - Flow 0515.xlsx` 中 9 个结售汇与 Flow 模块建设为可持续维护的本地看板：

```text
Excel 历史种子
  → SQLite 原始序列
  → Python 衍生指标复算
  → Wind MCP 增量更新与修订审计
  → chart catalog
  → 单文件、离线可用的交互式 HTML
```

本 Loop 同时负责：

1. 修正当前项目的数据、映射、更新和 HTML 基线问题；
2. 落实原 Excel 66 张图的保留、合并、重做和删除方案；
3. 完成端到端测试、视觉检查和文档交接。

## 2. 首版范围

只处理：

- `3.即远期`
- `3.代客即期`
- `3.涉外收付`
- `3.货物贸易`
- `3.贸易商`
- `3.服务贸易`
- `3.FDI`
- `3.证券EQ`
- `3.证券FI`

`待处理数据.xlsx` 中的其他模块不进入本轮。

## 3. 权威输入与执行优先级

必须读取：

1. `EXECUTION_AGENT_TASK.md`
2. 本文件
3. `docs/CURRENT_PROJECT_REVIEW_20260622.md`
4. `docs/CHART_MIGRATION_PLAN.md`
5. `AGENT_LOOP.md`
6. `docs/REVIEW_HANDOFF.md`
7. `.inspection/chart_inventory.json`
8. 当前 Git 状态、SQLite、配置、代码和测试

冲突时按以下顺序处理：

1. 用户明确要求；
2. 本统一 Loop；
3. 当前审阅报告和图表迁移方案；
4. 原 `AGENT_LOOP.md`；
5. 当前实现。

## 4. 不可协商的规则

- 原 Excel 只读，禁止覆盖、改名或清理公式与外部链接。
- SQLite 是迁移完成后的唯一运行时数据源，HTML 不直接读取 Excel。
- 目标外部更新源是 Wind MCP；不得把 iFind 或其他来源写成 Wind。
- 未经用户明确许可，不得使用 Web、猜测值或相似指标替代 Wind。
- 无两个真实重叠点时，禁止自动写入更新。
- 禁止用数据拟合出的任意比例因子证明序列映射正确。
- 历史修订不得通过 `INSERT OR REPLACE` 静默覆盖。
- 正式图表使用的 derived 指标必须由 Python 复算并有指标定义。
- 图表必须来自 `config/chart_catalog.json`，禁止自动选取前几个序列。
- 不删除或覆盖用户及其他 agent 的未提交改动。
- 每轮只处理一个可验证的问题集；完成测试后再进入下一轮。
- 每轮更新 `docs/REVIEW_HANDOFF.md`，记录改动、验证、遗留问题和下一步。

## 5. 统一循环协议

每个 Loop 均执行：

1. **读取状态**：检查 Git、交接文档、数据库和最近测试。
2. **定义本轮门禁**：写明本轮要通过的自动测试和人工检查。
3. **最小实现**：只修改本轮所需范围。
4. **验证**：运行针对性测试和全量回归。
5. **复核产物**：检查数据库、配置、HTML 或截图等实际输出。
6. **记录**：更新 `docs/REVIEW_HANDOFF.md`。
7. **决策**：
   - 门禁通过：进入下一 Loop；
   - 门禁失败：留在当前 Loop 修正；
   - 外部能力确实缺失：记录证据与安全降级，不伪造完成。

---

# 阶段 A：恢复可信的数据与运行基线

阶段 A 未全部通过前，禁止批量实施图表。

## Loop A0：建立可复现基线

1. 保存当前 Git 状态、数据库统计、mapping 状态、update plan、测试结果和 HTML 检查结果。
2. 标记当前未结束的 update run，不静默删除。
3. 区分本轮前已存在的未提交改动与本轮新增改动。
4. 将审阅报告中的 P0/P1 问题转为可勾选清单。

完成门禁：

- 任一后续改动均可与基线比较；
- 用户已有改动未被覆盖；
- 数据库、配置和报告的当前统计已记录。

## Loop A1：恢复 Wind MCP 数据源契约

1. 读取本机 Wind 技能和可调用工具合约。
2. 盘点当前 iFind 代码、配置和结果。
3. 将所有 iFind 验证结果标为 `external_candidate` 或 `needs_wind_verification`。
4. 文档和字段使用真实来源名。
5. 通过 Wind MCP 完成至少一个原始序列的小样本查询。
6. 若 Wind MCP 不支持某类序列，记录为 `unsupported`、`no_result` 或 `mapping_pending`，不得静默改用 iFind。

完成门禁：

- Wind 调用不是 stub；
- 至少一条序列有真实 Wind MCP 成功响应；
- 来源名称真实；
- Wind 失败路径有明确状态。

## Loop A2：重建元数据唯一主表

以 `config/series_catalog.json` 为版本管理主表，SQLite `series` 表为运行时镜像。

修复：

- `Column_*`；
- 空或 unknown 单位；
- 日期列误识别；
- 频率错误；
- raw / derived / manual / legacy_external 分类错误；
- catalog、SQLite 和 Data Dictionary 数量不一致。

每个正式序列至少包含：

- 稳定 `series_id`；
- 名称、模块、频率和单位；
- 序列类型；
- Excel 来源；
- 更新方式和来源；
- 首末有效日期；
- 状态与备注。

完成门禁：

- catalog、SQLite、Data Dictionary 数量与分类一致；
- 正式展示序列无 `Column_*`；
- 正式展示序列单位完整；
- 日期轴不作为业务序列。

## Loop A3：修复衍生指标与血缘

1. 将所有 derived 分为：已复算、待迁移、不进入正式看板。
2. 填充 `metric_definitions`。
3. 优先迁移 `docs/CHART_MIGRATION_PLAN.md` 所需指标。
4. 修复：
   - TTM 流量使用 rolling sum；
   - MMA 使用 moving average；
   - 必要的 VLOOKUP、PERCENTRANK、CORREL；
   - 缺失值、除零和符号规则。
5. 对最近 24 个有效点及完整公共区间分别校验。
6. 同时报告指标通过率和数据点通过率。

完成门禁：

- 正式图表所需 derived 全部由 Python 复算；
- 对应 `metric_definitions` 完整；
- TTM 与 MMA 语义正确；
- 正式图表不读取 Excel 缓存 derived 值。

## Loop A4：严格重做 Wind 映射

允许的转换必须来自受控列表：

- `identity`
- `divide_1e4`
- `divide_1e8`
- `multiply_100`
- `divide_100`
- `sign_flip`
- `currency_conversion_by_date`
- `cumulative_to_period`

禁止：

- 用中位数比值生成任意缩放因子；
- 放宽容差制造 verified；
- 用一个重叠点通过验证；
- 用不同经济概念替代；
- 用静态比例进行跨币种转换。

建议最低验证门槛：

- 月度：至少 12 个重叠点，最近 2 点一致；
- 日度：至少 40 个重叠点，最近 5 个交易日一致；
- 季度：至少 4 个重叠季度，最近 2 季一致；
- 受控转换后平均相对误差通常不超过 0.1%；
- 历史修订单独进入 review。

状态限定为：

- `verified_exact`
- `verified_unit_transform`
- `revision_review`
- `mapping_pending`
- `unsupported`
- `no_result`
- `manual`
- `not_applicable`

## Loop A5：修复更新计划

1. 从数据库读取每个序列最后两个实际观测日期。
2. 两个 `validation_dates` 必须真实、不同且存在。
3. 日度使用真实交易日期；月度、季度保留正确 period end。
4. update plan 每次从最新生产 mapping 自动生成。
5. 禁止陈旧样例计划冒充正式计划。

完成门禁：

- 每条生产计划均有两个有效重叠日期；
- 计划条数与生产可更新 mapping 一致；
- 日期和频率正确。

## Loop A6：实现安全的 Wind 更新

1. 实现真实 `fetch_via_wind_mcp()`。
2. 原始响应先写 staging。
3. staging 保存来源、参数、单位、时间、变换前后值。
4. 两点重叠验证失败时拒绝自动写入。
5. 新值与历史修订分开处理。
6. 增加 revision audit，保存旧值、新值、差异和审核状态。
7. 禁止静默覆盖。
8. 写入后只复算受影响的下游 derived。
9. 写入前判定新增和修订数量。
10. 所有 update run 必须结束为成功或失败状态。

## Loop A7：恢复最小 HTML 基线

1. 修复生成器 JavaScript 引号和其他语法错误。
2. 生成后强制执行：
   - HTML 结构检查；
   - 内联 JavaScript `node --check`；
   - 页面初始化测试。
3. 移除自动取前 6 个 raw 序列的逻辑。
4. 建立最小 `config/chart_catalog.json`。
5. 仅保留一个可运行的即远期基线图，用于验证完整数据链。

完成门禁：

- HTML JavaScript 语法通过；
- 页面可初始化；
- 图表只能由 catalog 显式配置；
- 最小图表从 SQLite 读取正确数据。

## Loop A8：补齐生产门禁测试

必须覆盖：

- 任意比例因子不得通过；
- 语义不一致不得通过；
- 一个或零个重叠点不得通过；
- validation dates 来自数据库最后两个点；
- 季度日期不重复；
- 新增与修订计数正确；
- 历史修订不静默覆盖；
- raw 更新触发下游复算；
- TTM 使用 rolling sum；
- HTML 通过 JavaScript 和初始化检查；
- chart catalog 引用的 series 全部存在。

## 阶段 A 关卡

以下条件必须同时满足：

- Wind MCP 有真实成功调用；
- 映射不存在任意数据拟合比例；
- 两点重叠校验严格执行；
- 生产更新不是 stub；
- 正式图表指标均由 Python 复算；
- `metric_definitions` 覆盖正式图表指标；
- 最小 HTML 可运行；
- 阶段 A 全部测试通过。

不满足时不得进入阶段 B。

---

# 阶段 B：实施原 Excel 图表迁移方案

## Loop B0：建立完整 chart catalog

根据 `docs/CHART_MIGRATION_PLAN.md` 和 `.inspection/chart_inventory.json` 创建完整 `config/chart_catalog.json`。

每个图表合同必须包含：

- `chart_id`
- module
- primary / drilldown
- 分析问题和默认 takeaway
- 原 Excel 图表编号
- family 与 chart type
- required series
- 单位与频率
- 默认时间范围
- 轴配置
- 颜色策略
- tooltip 字段
- 数据质量门禁
- 空数据 fallback

实现 validator：

- `chart_id` 唯一；
- series 存在；
- derived 有 metric definition；
- 不同单位明确双轴或转换；
- scatter 的 x/y 同粒度；
- seasonality 有月份和历史样本。

## Loop B1：实现共享图表组件

依次实现：

1. signed bar + moving-average line；
2. stacked bar + total line；
3. multi-line trend；
4. dual-axis trend；
5. seasonality band；
6. percentile line；
7. scatter + regression；
8. floating range + current marker；
9. latest-value summary table。

技术约束：

- 使用 Chart.js + chartjs-plugin-datalabels；
- 依赖内联，保持单文件离线使用；
- 特殊 band、回归线和浮动区间可用小型自定义插件；
- 不以手绘 SVG 作为默认实现；
- 线图默认不填充面积；
- signed flow 必须有清晰零轴。

每个组件要有最小 fixture 和结构或截图验证。

## Loop B2：先完成即远期模块

根据迁移方案实现即远期保留图表。

验证：

- 分解关系与 Excel 一致；
- 月度值与 12MMA/6MMA 不混淆；
- 远期、履约和期权方向正确；
- USDCNY 双轴单位与方向明确；
- CSV 与 PNG 导出正确。

即远期未通过，禁止复制到其他模块。

## Loop B3：逐模块扩展

按顺序实施：

1. 代客即期；
2. 涉外收付；
3. 货物贸易；
4. 贸易商；
5. 服务贸易；
6. FDI；
7. 证券 EQ；
8. 证券 FI。

每个模块都要：

1. 实现主图；
2. 实现 drill-down；
3. 对照原 Excel 图表覆盖关系；
4. 运行 catalog validator；
5. 运行数据、JS 和页面初始化测试；
6. 更新 Review Handoff。

## Loop B4：统一季节性组件

- x 轴为 1–12 月；
- 历史 min-max band；
- 历史均值；
- 当年轨迹；
- 指标选择器；
- 未发布月份为空，不显示 0；
- 去年同期或历史中位数可作为可选基准。

用一个组件替代 Excel 中重复复制的季节性图。

## Loop B5：双轴与散点关系图

双轴：

- 只用于不同单位且分析关系明确的序列；
- 轴颜色匹配序列；
- 汇率轴标明升贬值方向；
- 不截断轴制造相关性。

散点：

- 至少 20 个有效样本；
- x/y 同频率、同窗口；
- 显示样本数、相关系数和 OLS 回归线；
- 全历史与近期使用筛选器，不复制图；
- 历史阶段用颜色或点形区分。

## Loop B6：摘要、交互与导出

实现：

- 全部、5Y、3Y、1Y、YTD；
- 模块内指标选择；
- 图表说明与来源；
- 最新有效日期与更新状态；
- 缺失或停更提示；
- CSV 下载；
- PNG 导出；
- tooltip；
- 移动端堆叠布局。

signed flow 摘要默认显示：

- 最新值；
- 前值；
- 变化额；
- 3MMA；
- 历史分位。

不默认使用普通百分比环比。

---

# 阶段 C：端到端验收与交付

## Loop C0：数据与计算 QA

- 图表数据与 SQLite 查询一致；
- 所有 derived 指标可由定义复算；
- 不存在未来占位零；
- 单位、频率、符号和日期标签正确；
- 更新测试使用真实重叠日期；
- 修订审计可追踪。

## Loop C1：功能与视觉 QA

自动检查：

- HTML 结构；
- JavaScript 语法；
- 页面初始化；
- catalog 完整性；
- 空图、非有限值；
- 时间筛选、导航和导出。

视觉检查：

- 零轴和负值；
- 双轴可读性；
- 标题、图例和标签；
- 季节性 band；
- 极值和长标签；
- 常规屏幕与窄屏；
- 摘要值与图表一致。

## Loop C2：重新生成文档

由代码生成并更新：

- README；
- DATA_DICTIONARY；
- EXCEL_LINEAGE；
- WIND_COVERAGE；
- PROGRESS_REPORT；
- REVIEW_HANDOFF。

文档统计不得手工维护冲突数字，至少包含：

- series 总数及分类；
- Wind 覆盖率；
- update plan 条数；
- 指标复算覆盖率；
- 原 66 图处理覆盖率；
- 最终主图与 drill-down 数量；
- 测试结果；
- 数据截至日期；
- 已知 unsupported / manual 项。

## 6. 最终完成条件

只有以下全部满足才可宣告完成：

- 9 个目标模块均已交付；
- SQLite 为 HTML 唯一运行时数据源；
- Wind MCP 更新链至少对已验证序列可真实运行；
- 两点重叠与修订审计生效；
- 正式图表指标全部可审计复算；
- 原 66 张图全部映射为保留、合并、重做或删除；
- 默认页面约 24 张核心图，其余通过 drill-down 或选择器访问；
- 不存在自动选择前几个序列的逻辑；
- HTML 单文件离线可打开；
- PC 与窄屏通过视觉检查；
- CSV 与 PNG 导出通过；
- 自动测试全部通过；
- `docs/REVIEW_HANDOFF.md` 完整记录最终状态与遗留限制。

## 7. 停止与升级条件

出现以下情况时停止相关路径并明确报告，不得伪造完成：

- Wind MCP 工具不可用或不支持目标序列；
- 指标定义无法从 Excel、代码或可靠来源还原；
- 需要用不同经济概念替代原指标；
- 需要覆盖用户已有未提交改动；
- 必须扩大到 9 个模块之外；
- 数据无法通过重叠验证；
- 视觉验收环境不可用且没有可替代的结构检查。

停止时仍应继续完成不依赖该阻塞项的安全工作，并在 Review Handoff 中列出：

- 阻塞项；
- 已尝试方法；
- 证据；
- 影响范围；
- 需要用户决定的最小问题。
