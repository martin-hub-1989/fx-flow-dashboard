# Martin Monthly Brief：结售汇与 Flow 看板执行 Loop

## 1. 任务目标

将 `FX Chartbook - Flow 0515.xlsx` 中的结售汇与 Flow 模块重构为：

1. 以 Excel 现有数据作为历史种子；
2. 以本地 SQLite 数据库作为唯一数据源；
3. 以后通过 Wind MCP 增量更新原始序列；
4. 在数据库之外用可审计代码复算自定义指标；
5. 生成单文件、自包含、可离线打开的交互式 HTML 看板；
6. 保留完整的数据血缘、校验记录和更新日志。

不要机械翻译 Excel，也不要以 Excel 作为 HTML 的运行时数据源。

## 2. 首版范围

只覆盖以下 9 个工作表：

- `3.即远期`
- `3.代客即期`
- `3.涉外收付`
- `3.货物贸易`
- `3.贸易商`
- `3.服务贸易`
- `3.FDI`
- `3.证券EQ`
- `3.证券FI`

以下模块不进入首版，已另存于 `待处理数据.xlsx`：

- `SAFE`
- `4.Valuation`
- `4.实际汇率`
- `Other`
- `Shadow Reserve`
- `CNY Key Driver`
- `Real Rate`

不得在首版中顺手扩展这些模块。

## 3. 权威输入

- 主工作簿：`FX Chartbook - Flow 0515.xlsx`
- 前期经验：`Martin Morning Brief 项目总结 - Agent 参考.md`
- 暂缓模块：`待处理数据.xlsx`

原始工作簿只读，禁止覆盖、改名或清理其公式和外部链接。

## 4. 不可协商的设计约束

### 4.1 数据架构

采用：

```text
Excel 历史种子
      ↓
SQLite 原始序列层
      ↓
Python 指标复算层
      ↓
SQLite 衍生序列层
      ↓
HTML 生成器
      ↓
单文件交互式看板
```

SQLite 是完成迁移后的唯一数据源。HTML 不直接读取 Excel。

### 4.2 原始数据与衍生指标必须分离

每个序列必须标记为：

- `raw`：Wind 或 Excel 直接提供；
- `derived`：由原始序列计算；
- `manual`：人工维护的政策事件、权重或特殊假设；
- `legacy_external`：依赖旧外部工作簿且暂时无法还原。

不得把 Excel 公式结果伪装成 Wind 原始数据。

### 4.3 可审计性

每个 derived 序列必须有：

- 稳定的 `series_id`；
- 中文展示名；
- 所属模块；
- 频率与单位；
- 公式或算法说明；
- 输入序列列表；
- 对应 Excel 工作表及代表性单元格；
- 首个有效日期；
- 缺失值和除零处理规则；
- 代码实现位置；
- 校验状态。

### 4.4 Wind MCP 边界

- 先读取本机 Wind 技能及工具合约，再选择实际可调用工具。
- EDB 指标优先尝试 `economic_data.get_economic_data`。
- 日期参数使用 `yyyyMMdd`。
- 不得因为 Excel 中存在 `[1]!edb()` 就假设指标可以自动映射。
- 当前 Wind 技能不承诺直接汇率行情接口。逐序列做能力测试。
- 禁止用 Web、猜测值、相似指标或其他无授权数据源填补 Wind 缺口。
- 无法更新的序列保留 Excel 历史种子，并标为 `unsupported`、`no_result` 或 `mapping_pending`。

### 4.5 增量更新校验

每次更新必须回取数据库最后两个已有日期：

```text
fetch_start_date = 数据库倒数第二个日期
validation_dates = 数据库最后两个日期
```

只有两个重叠点通过校验后，才允许写入新数据。

校验至少包括：

- 日期是否对应；
- 单位是否一致；
- 数值是否在容差内；
- 返回频率是否正确；
- 最新值是否异常跳变；
- 是否出现历史修订。

历史修订不能静默覆盖。记录旧值、新值、差异、来源和更新时间。

## 5. 建议目录

```text
.
├── AGENT_LOOP.md
├── README.md
├── config/
│   ├── series_catalog.json
│   ├── wind_mapping.json
│   ├── dashboard_modules.json
│   └── validation_rules.json
├── data/
│   ├── monthly_brief.sqlite
│   ├── update_plan.json
│   └── update_report.json
├── docs/
│   ├── DATA_DICTIONARY.md
│   ├── EXCEL_LINEAGE.md
│   ├── WIND_COVERAGE.md
│   └── REVIEW_HANDOFF.md
├── scripts/
│   ├── lib.py
│   ├── inspect_excel.py
│   ├── import_excel_seed.py
│   ├── recompute_derived.py
│   ├── build_update_plan.py
│   ├── fetch_wind.py
│   ├── validate_update.py
│   ├── generate_dashboard.py
│   └── run_update.py
├── templates/
│   └── dashboard.html
├── reports/
│   └── fx_flow_dashboard.html
└── tests/
```

运行时数据库和报告是否进入 Git，根据仓库实际情况决定；配置、代码、测试和文档必须可版本管理。

## 6. SQLite 最低数据模型

至少实现以下表。

### `series`

```text
series_id             PRIMARY KEY
display_name
module
series_type           raw / derived / manual / legacy_external
frequency
unit
source
source_query
excel_sheet
excel_range
update_status
first_date
last_date
notes
```

### `observations`

```text
series_id
date
value
source
source_vintage
imported_at
run_id
PRIMARY KEY(series_id, date)
```

### `metric_definitions`

```text
series_id             PRIMARY KEY
formula_description
input_series_json
calculation_version
implementation
missing_value_rule
sign_convention
```

### `update_runs`

```text
run_id                PRIMARY KEY
started_at
finished_at
status
requested_series
successful_series
failed_series
new_observations
revised_observations
error_summary
```

### `validation_events`

```text
run_id
series_id
date
database_value
fetched_value
difference
tolerance
status
message
```

可增加表，但不要删除这些审计能力。

## 7. 执行 Loop

持续重复以下循环，直到所有完成条件满足。

### Step 0：读取与状态恢复

每次开始先读取：

- 本文件；
- `docs/REVIEW_HANDOFF.md`；
- 当前 Git 状态；
- 最近测试结果；
- 当前 blocker；
- 上一轮遗留任务。

若项目尚无 `docs/REVIEW_HANDOFF.md`，立即创建。

### Step 1：只做结构盘点

输出工作簿清单，不写正式业务代码：

- 每张目标表的原始数据块；
- 计算块；
- 图表；
- 数据频率；
- 单位；
- 时间方向；
- 跨表引用；
- 外部链接；
- 手工假设；
- 最新与最早日期。

形成：

- `config/series_catalog.json`
- `docs/DATA_DICTIONARY.md`
- `docs/EXCEL_LINEAGE.md`

每个原始列和每个首版展示指标都必须进入 catalog。

### Step 2：建立最小数据库

先选一个端到端切片：

- 推荐模块：`3.即远期`
- 推荐原始序列：银行自身结售汇、代客即期、远期签约；
- 推荐衍生指标：外汇市场供求、即期结售汇发生额、衍生品当月签约。

完成：

1. Excel 种子导入；
2. 数据库存储；
3. 指标复算；
4. 与 Excel 缓存结果比较；
5. 生成一个最小 HTML 页面。

该切片未通过前，不得批量铺开其他模块。

### Step 3：导入全部首版历史种子

导入时：

- 使用 Excel 已缓存的数值作为历史基准；
- 同时读取公式文本用于血缘文档；
- 日期统一为 ISO `YYYY-MM-DD`；
- 保留原单位，不在导入层随意缩放；
- 对 Excel 中的 `0`、空值、`#N/A` 分别处理；
- 不把尚未发布月份的占位零当作真实观测；
- 记录每个序列的最早、最晚日期和观测数。

导入必须幂等：重复运行不得产生重复记录。

### Step 4：迁移自定义指标

按模块逐个迁移：

1. 即远期；
2. 代客即期；
3. 涉外收付；
4. 货物贸易；
5. 贸易商；
6. 服务贸易；
7. FDI；
8. 证券 EQ；
9. 证券 FI。

优先迁移有图表或明确分析意义的指标，不需要复刻 Excel 中所有辅助单元格。

复杂 Excel 公式拆成有名称的中间序列，不写不可审计的超长表达式。

每迁移一个指标：

1. 写公式说明；
2. 写代码；
3. 写单元测试；
4. 和 Excel 至少比较最近 24 个有效点；
5. 记录最大绝对误差与相对误差；
6. 通过后再进入下一个指标。

### Step 5：建立 Wind 映射

对每个 raw 序列执行：

1. 从 Excel 指标名称提取候选查询；
2. 只查询最近 3 至 5 个点；
3. 比较 Excel 最近两个可用点；
4. 确认频率、单位、方向和日期标签；
5. 通过后写入 `config/wind_mapping.json`；
6. 失败则记录在 `docs/WIND_COVERAGE.md`。

映射状态只能是：

- `verified`
- `verified_with_transform`
- `mapping_pending`
- `unsupported`
- `no_result`
- `manual`

`verified_with_transform` 必须明确写出变换，例如单位缩放、符号反转、月末日期归一化。

### Step 6：实现安全增量更新

`build_update_plan.py` 为每个可更新序列生成：

- `last_date`
- `next_start_date`
- `fetch_start_date`
- `validation_dates`
- `wind_method`
- `query`
- `frequency`
- `unit`
- `tolerance`

`fetch_wind.py` 只负责取数并保存暂存结果，不直接修改正式 observations。

`validate_update.py` 先验证重叠点。通过后使用事务写入：

```text
BEGIN
写入新原始数据
记录修订
复算受影响的 derived 序列
写入验证日志
COMMIT
```

任何失败执行 `ROLLBACK`，其他序列可以继续。

### Step 7：生成交互式 HTML

首版采用单文件自包含 HTML：

- 数据从 SQLite 读取后内嵌；
- 无服务器即可打开；
- 尽量无外部运行时依赖；
- 图表建议使用内联的轻量图表库或经过验证的 SVG 组件；
- 所有模块共享同一套渲染器和视觉规范。

建议的信息结构：

```text
总览
├── 即远期供求
├── 代客即期结构
├── 涉外收付
├── 货物贸易与贸易商意愿
├── 服务贸易
├── FDI
├── 证券资金流：EQ
└── 证券资金流：FI
```

至少提供：

- 时间范围切换；
- 指标显示与隐藏；
- tooltip；
- 单位和来源；
- 最新值与环比/同比；
- 数据下载；
- 图表图片导出；
- 数据截至日期；
- 更新状态与缺失提示。

不要逐张复刻 81 张 Excel 图表。先围绕分析问题整合图表。

### Step 8：验证

每轮必须运行：

- 数据库唯一键和空值检查；
- 原始序列观测数与日期范围检查；
- derived 指标与 Excel 对比；
- 全量公式错误/非有限值检查；
- 重复执行幂等检查；
- 更新事务回滚测试；
- HTML 数据 payload 校验；
- JavaScript 语法检查；
- 页面初始化检查；
- 关键模块截图或浏览器目测；
- 更新前后最新值检查。

不得只报告“脚本运行成功”。

### Step 9：更新交接文件

每轮结束更新 `docs/REVIEW_HANDOFF.md`：

```markdown
# Review Handoff

## 当前完成度
## 本轮变更
## 已验证内容
## 未覆盖内容
## Wind 覆盖率
## 已知数据差异
## 当前 blocker
## 运行命令
## 关键文件
## 建议审阅顺序
```

然后判断：

- 若仍有安全可执行任务：回到 Step 0；
- 若需要用户业务判断：停止并提出一个具体问题；
- 若满足完成条件：停止并提交审阅。

## 8. 禁止事项

- 禁止修改原始 Excel。
- 禁止把公式缓存值当作 Wind 来源。
- 禁止为了通过校验而放宽容差。
- 禁止静默覆盖历史修订。
- 禁止把零值一律视为真实数据。
- 禁止一次性迁移全部 9 万多个公式。
- 禁止在映射未验证时执行大范围 Wind 拉取。
- 禁止用相似指标替代缺失指标。
- 禁止只做漂亮页面而不做数据血缘和测试。
- 禁止因单个序列失败而终止全部更新。
- 禁止扩展到 `待处理数据.xlsx` 中的模块。

## 9. 完成条件

只有同时满足以下条件才可声称完成：

- 9 个目标工作表均已完成数据盘点；
- 首版所需 raw/derived/manual 序列均有 catalog；
- Excel 历史种子已幂等导入 SQLite；
- 所有展示用 derived 指标均有代码、定义和测试；
- 代表性指标最近 24 个有效点与 Excel 一致；
- 每个 raw 序列都有 Wind 映射状态；
- 所有 `verified` 序列可完成两点重叠校验后增量写入；
- 更新失败可回滚并形成报告；
- HTML 可离线打开并覆盖 9 个模块；
- 核心交互和导出功能通过验证；
- README、数据字典、Wind 覆盖表和交接文档完整；
- 没有未解释的高优先级数据差异。

## 10. 最终交付

最终至少提供：

- `data/monthly_brief.sqlite`
- `reports/fx_flow_dashboard.html`
- `config/series_catalog.json`
- `config/wind_mapping.json`
- 全套更新与生成脚本
- 测试
- `README.md`
- `docs/DATA_DICTIONARY.md`
- `docs/EXCEL_LINEAGE.md`
- `docs/WIND_COVERAGE.md`
- `docs/REVIEW_HANDOFF.md`

完成后不要自行宣布业务验收通过。通知用户返回本线程，由 Codex 根据第 11 节进行独立审阅。

## 11. Codex 后续独立审阅清单

审阅时重点检查：

1. 数据库是否真正成为唯一数据源；
2. raw、derived、manual 是否正确分类；
3. Excel 到数据库的历史值是否完整；
4. 自定义指标是否与 Excel 对齐；
5. Wind 映射是否逐序列验证；
6. 两点重叠校验是否在正式写入前发生；
7. 历史修订是否可追踪；
8. 更新失败是否事务回滚；
9. HTML 是否直接来自数据库；
10. 页面是否围绕分析问题组织，而非机械复制工作表；
11. 数据截至日期、单位、来源和缺失状态是否清楚；
12. 是否存在硬编码、静默 fallback 或未经验证的替代数据。

