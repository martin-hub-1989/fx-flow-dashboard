# 执行 Agent 任务说明：Martin Monthly Brief 结售汇与 Flow 看板

## 任务

请在当前项目中完整执行 `MASTER_EXECUTION_LOOP.md`，修正现有数据与更新链路，并基于原 Excel 图表完成结售汇与 Flow 交互式 HTML 看板。

这不是从零重写项目。现有顶层架构继续保留：

```text
Excel 历史种子 → SQLite → Python 指标复算 → Wind MCP 增量更新
→ chart catalog → 单文件交互式 HTML
```

当前实现是一个历史数据迁移和看板生成原型，但生产更新、映射验证、指标血缘和图表实现尚未达到可交付标准。先修正可信数据链，再实施图表，不能倒序。

## 必读文件

开始前按顺序读取：

1. `MASTER_EXECUTION_LOOP.md`：唯一执行流程和验收标准；
2. `docs/CURRENT_PROJECT_REVIEW_20260622.md`：当前问题与审阅证据；
3. `docs/CHART_MIGRATION_PLAN.md`：原 Excel 66 张图的逐张处理决定；
4. `.inspection/chart_inventory.json`：原图、系列和引用范围清单；
5. `AGENT_LOOP.md`：项目原始设计约束；
6. `docs/REVIEW_HANDOFF.md`：当前执行状态；
7. `FX Chartbook - Flow 0515.xlsx`：只读权威原始文件；
8. `Martin Morning Brief 项目总结 - Agent 参考.md`：前期项目经验。

`CORRECTION_LOOP.md` 和 `CHART_IMPLEMENTATION_LOOP.md` 已由 `MASTER_EXECUTION_LOOP.md` 合并取代，只作为历史参考，不应再被当作两个独立流程执行。

## 范围

只完成 9 个模块：

- `3.即远期`
- `3.代客即期`
- `3.涉外收付`
- `3.货物贸易`
- `3.贸易商`
- `3.服务贸易`
- `3.FDI`
- `3.证券EQ`
- `3.证券FI`

不要处理 `待处理数据.xlsx` 中的其他模块。

## 当前已知问题

不要把当前通过的基础测试等同于项目正确。审阅已确认：

- 当前代码实际使用过 iFind EDB，但文档将其写成 Wind；
- 部分映射使用任意数据比例拟合、低重叠或语义不一致；
- `fetch_via_wind_mcp()` 尚未形成真实生产调用；
- update plan 没有严格读取数据库最后两个实际日期；
- 无重叠数据可能被错误放行；
- 历史修订可能被静默覆盖；
- 正式 raw 更新后没有完整触发下游 derived 复算；
- `metric_definitions` 尚未覆盖正式图表指标；
- 部分 TTM 被错误实现为移动平均；
- 当前 HTML 存在 JavaScript 语法错误；
- 多数模块的图表只是自动取前几个序列，并未复现 Excel 的分析问题。

必须用代码、数据库查询和测试重新验证这些问题，不能只照文档机械修改。

## 执行要求

1. 先执行 `MASTER_EXECUTION_LOOP.md` 阶段 A。
2. 阶段 A 关卡未全部通过前，不得批量开发图表。
3. 阶段 B 严格按照 `docs/CHART_MIGRATION_PLAN.md`：
   - 66 张原图全部有处置结果；
   - 默认看板约 24 张核心图；
   - 重复季节性图合并为选择器；
   - 其余保留内容进入 drill-down。
4. 使用 Chart.js + chartjs-plugin-datalabels；保持单文件离线交付。
5. 图表必须通过 `config/chart_catalog.json` 驱动。
6. 每完成一个 Loop：
   - 运行针对性测试；
   - 运行相关回归测试；
   - 检查真实产物；
   - 更新 `docs/REVIEW_HANDOFF.md`。
7. 遇到失败应留在当前 Loop 修正，不得跳过门禁继续堆功能。

## 文件和 Git 安全

- 原 Excel 只读，绝对不能覆盖。
- 当前工作区可能已有用户或其他 agent 的未提交改动。
- 开始前保存 `git status`，识别并保留既有改动。
- 不得使用破坏性 Git 命令。
- 不得回退、删除或格式化与本任务无关的改动。
- 提交时只包含自己确认过的相关文件；若仓库约定不允许提交，则保持清晰的变更清单。

## 数据源边界

- 目标更新源是 Wind MCP。
- 先检查当前环境真实可调用的 Wind 工具与技能。
- iFind 结果只能作为外部候选或历史研究记录，不能标记为 Wind 验证。
- 不得用 Web、相似指标、猜测值或任意比例替代 Wind。
- Wind 无法提供的数据应保留 Excel 历史种子并准确标记状态。
- 没有两个有效重叠点时拒绝自动写入。

## 图表实现原则

- 保留分析问题，不要求机械复刻 Excel 外观。
- signed flow 使用清晰零轴，不用红绿表达好坏。
- 线图默认不填充面积。
- datalabels 只显示最新点、极值或选中点。
- 双轴仅用于单位不同且比较关系明确的序列。
- 散点图显示样本数、相关系数和回归线。
- 未发布月份显示为空，不显示未来占位 0。
- 每张图显示单位、频率、来源和数据截至日期。
- 支持 CSV 下载、PNG 导出、时间筛选和窄屏布局。

## 需要交付的主要产物

- 修正后的 SQLite 数据与数据模型；
- 完整且可信的 `config/series_catalog.json`；
- 严格验证后的 `config/wind_mapping.json`；
- 动态生成的正式 update plan；
- 真实 Wind 拉取、staging、重叠校验和 revision audit；
- 可审计的 derived 指标代码与 `metric_definitions`；
- 完整 `config/chart_catalog.json` 及 validator；
- 共享 Chart.js 图表组件；
- `reports/fx_flow_dashboard.html`；
- 生产级自动测试和视觉检查结果；
- 自动生成或同步更新的项目文档；
- 最终 `docs/REVIEW_HANDOFF.md`。

## 完成定义

不要用“代码已写”作为完成标准。只有 `MASTER_EXECUTION_LOOP.md` 的最终完成条件全部满足，任务才算完成。

最终汇报必须包含：

1. 完成了哪些 Loop；
2. 数据库和数据源的最终状态；
3. Wind 可更新、不可更新和待人工处理的序列数量；
4. derived 指标复算覆盖率；
5. 原 66 张图的覆盖结果；
6. 最终主图、drill-down 和选择器数量；
7. 测试命令与结果；
8. HTML 验证与视觉检查结果；
9. 未解决问题、真实限制和需要用户决定的事项；
10. 本轮修改文件清单。

## 开始方式

现在开始执行，不要先重写计划。第一步：

1. 读取上述必读文件；
2. 检查当前 Git 状态；
3. 执行 `MASTER_EXECUTION_LOOP.md` 的 Loop A0；
4. 在 `docs/REVIEW_HANDOFF.md` 写入基线和本轮门禁；
5. 继续循环，直至完成或遇到明确的外部阻塞。
