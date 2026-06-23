# Martin Monthly Brief：生产化修正执行 Loop

> 审阅基准：2026-06-23，commit `4b96770`  
> 适用范围：结售汇与 Flow 看板下一阶段  
> 执行目标：从“可演示原型”推进到“可安全更新、可审计、可长期使用的 v1”

## 1. 执行任务

继续现有项目，不推翻以下架构：

```text
Excel 历史种子
  → SQLite
  → Python 衍生指标
  → Wind MCP 增量更新
  → chart catalog
  → 单文件 Chart.js HTML
```

本 Loop 只处理：

1. 生产更新链；
2. 正式图表的数据可信度；
3. 季节性图、单位、摘要和移动端；
4. 端到端测试；
5. 文档口径收口。

不得扩大到 `待处理数据.xlsx` 中的其他模块。

## 2. 必读文件

开始前按顺序读取：

1. `NEXT_PHASE_EXECUTION_LOOP.md`
2. `docs/NEXT_PHASE_PLAN_20260623.md`
3. `docs/CHART_MIGRATION_PLAN.md`
4. `MASTER_EXECUTION_LOOP.md`
5. `docs/REVIEW_HANDOFF.md`
6. `config/wind_mapping.json`
7. `config/chart_catalog.json`
8. `scripts/build_update_plan.py`
9. `scripts/fetch_wind.py`
10. `scripts/validate_update.py`
11. `scripts/generate_dashboard.py`
12. 当前 Git 状态、数据库和测试结果

若旧文档与代码或本 Loop 冲突，以以下顺序为准：

1. 用户明确要求；
2. 本 Loop；
3. `docs/NEXT_PHASE_PLAN_20260623.md`；
4. 代码、数据库和真实测试结果；
5. 旧进度文档。

`README.md`、`docs/PROGRESS_REPORT.md` 和旧版
`docs/REVIEW_HANDOFF.md` 当前存在冲突，不得直接作为完成证据。

## 3. 当前基线

执行 agent 必须重新验证，但应预期看到：

- Git 基准 commit：`4b96770`；
- SQLite：383 条 series、137,622 条 observations；
- metric definitions：224 条；
- 正式图表：29 张，20 primary + 9 drill-down；
- 图表唯一引用序列：79 条；
- 图表引用 derived：62 条；
- 其中 6 条仍是 `excel_cached`，1 条是 `excel_vlookup`；
- Wind 正式验证：`wind_verified=true` 为 0；
- 当前 `update_plan.json`：103 条，但不能由现有代码重新生成；
- `test_all.py`：显示 84 passed，但存在错误测试合同；
- `validate_all.py`：7/8，通过失败项为 trailing zeros；
- 桌面看板可以渲染；
- 390px 窄屏存在横向溢出；
- 季节性图没有真正实现历史区间 band。

如果重新检查结果不同，在 `docs/REVIEW_HANDOFF.md` 记录差异，并以实时结果继续。

## 4. 不可协商的规则

- 原 Excel 只读。
- 不覆盖用户或其他 agent 的未提交改动。
- 不使用 Web、iFind、相似指标或猜测值冒充 Wind。
- iFind 结果只能作为 `external_candidate`。
- 只有 `wind_verified=true` 的 mapping 可以进入生产更新计划。
- 少于两个真实重叠点时禁止自动写入。
- 历史修订不得静默覆盖。
- 正式图表不得依赖 `excel_cached` 或 `excel_vlookup`。
- 未发布月份不得显示为占位零。
- 不新增模块，不新增与本计划无关的功能。
- 每个 Loop 完成后必须验证实际产物，而不只验证代码。
- 任一阶段 Gate 未通过，不得进入下一阶段。

## 5. 通用循环协议

每个 Loop 按以下顺序执行：

### 5.1 Observe

- 读取当前 Git 状态；
- 读取 `docs/REVIEW_HANDOFF.md`；
- 运行本轮基线测试；
- 查询数据库或检查 HTML 真实产物；
- 区分本轮前已有改动和本轮新增改动。

### 5.2 Define

在开始修改前明确：

- 本轮问题；
- 修改文件；
- 预期失败测试；
- 完成门禁；
- 不在本轮处理的事项。

### 5.3 Implement

- 先写能证明问题存在的测试；
- 确认测试失败；
- 做最小修改；
- 不顺便重构无关代码。

### 5.4 Verify

- 运行针对性测试；
- 运行全量测试；
- 检查数据库、JSON、HTML 或浏览器实际结果；
- 与本轮开始前基线比较。

### 5.5 Record

更新 `docs/REVIEW_HANDOFF.md`：

- 本轮改动；
- 测试命令和结果；
- 数据统计变化；
- 实际产物检查；
- 遗留问题；
- 下一 Loop。

### 5.6 Decide

- 全部门禁通过：进入下一 Loop；
- 任一门禁失败：留在当前 Loop；
- 真实外部能力缺失：记录证据，停止相关路径，但继续不依赖该路径的安全工作；
- 不得把“代码存在”或“测试数量增加”当作完成。

---

# Phase 0：恢复可信基线

## Loop 0：重新建立状态快照

### 操作

1. 记录：
   - `git status --short`
   - `git log --oneline -5`
   - 数据库表数量和主要统计；
   - mapping 状态数量；
   - `wind_verified` 数量；
   - update plan 条数；
   - chart catalog 图表数量；
   - 图表引用的 cached derived 数量。
2. 运行：

```bash
python3 scripts/test_all.py
python3 scripts/validate_all.py
python3 -m compileall -q scripts
python3 scripts/generate_dashboard.py
```

3. 对生成 HTML 的每个内联脚本执行 `node --check`。
4. 浏览器检查：
   - 1280×720；
   - 390×844；
   - 9 个模块；
   - 两张散点图；
   - 控制台错误；
   - 页面横向溢出。
5. 将快照写入 `docs/REVIEW_HANDOFF.md`。

### 完成门禁

- 基线可复现；
- 已有改动未被覆盖；
- 所有后续结果均可与该快照比较。

---

# Phase 1：重建生产更新门禁

Phase 1 完成前，禁止新增或精修图表。

## Loop 1：修复 mapping 与 update plan 合同

### 修改范围

- `scripts/build_update_plan.py`
- `config/wind_mapping.json`
- `config/update_plan.json`
- `scripts/test_all.py` 或新增 pytest 测试

### 必须先写的失败测试

1. mapping 含 `_metadata` 时不会报错。
2. `wind_verified=false` 不进入计划。
3. 旧状态名不进入生产计划。
4. 只有以下状态可进入计划：
   - `verified_exact`
   - `verified_unit_transform`
5. validation dates 必须等于数据库最后两个实际观测日期。
6. 一个日期或重复日期时拒绝生成计划。
7. 相同输入重复生成完全相同的计划。

### 实现要求

- 安全过滤没有 `series_id` 的 metadata 行。
- 不通过日期减法猜测 overlap。
- 直接执行：

```sql
SELECT date
FROM observations
WHERE series_id = ?
ORDER BY date DESC
LIMIT 2
```

- 按时间正序保存两个 validation dates。
- 当前 `wind_verified=true` 为 0 时，生产计划应明确生成 0 条。
- 旧的 103 条计划不得继续冒充生产计划。

### 完成门禁

- `build_update_plan.py` 可直接运行；
- 当前生产计划为真实可复现结果；
- fixture 中 3 条 Wind verified mapping 稳定生成 3 条计划；
- 所有 validation dates 是数据库真实日期。

## Loop 2：实现 transform 合同

### 修改范围

- `scripts/fetch_wind.py`
- `scripts/wind_mcp_adapter.py`
- 新建或修改 transform 公共模块
- 对应测试

### 允许的 transform

- `identity`
- `divide_1e4`
- `divide_1e8`
- `multiply_100`
- `divide_100`
- `sign_flip`
- `currency_conversion_by_date`
- `cumulative_to_period`

### 必须先写的失败测试

- 未知 transform 被拒绝；
- transform 顺序稳定；
- 单位转换发生在 overlap 校验前；
- currency conversion 使用对应日期汇率；
- cumulative-to-period 正确处理年初和缺失月份；
- 原始值与转换后值均保留。

### 实现要求

staging 至少保存：

```text
series_id
query
wind_code
wind_name
wind_unit
requested_frequency
requested_currency
fetched_at
raw_observations
transform_chain
transformed_observations
```

不得对所有序列统一猜测“亿美元”或“人民币亿元”。

### 完成门禁

- 所有生产 mapping 的单位和 transform 可由代码执行；
- staging 可审计；
- 未知 transform 明确失败。

## Loop 3：重写两点重叠验证

### 修改范围

- `scripts/validate_update.py`
- `scripts/test_all.py` 或新增 pytest 测试

### 必须先删除或反转的错误测试

当前“零重叠应通过”的测试必须改为“零重叠拒绝”。

### 必须覆盖

- 0 个重叠点：拒绝；
- 1 个重叠点：拒绝；
- 2 个都通过：允许；
- 1 个通过、1 个失败：拒绝；
- 2 个都失败：拒绝；
- fetched 数据只有新日期：拒绝；
- tolerance 边界；
- null、NaN、Infinity；
- 返回频率不一致；
- 重复日期。

### 完成门禁

- 少于两个有效重叠点不可能返回通过；
- 校验事件完整保存；
- 错误原因可定位到日期、旧值、新值和容差。

## Loop 4：建立安全写入与 revision audit

### 修改范围

- `scripts/lib.py`
- `scripts/validate_update.py`
- SQLite migration
- 对应测试

### 数据模型

新增 `observation_revisions` 或等价表，至少包含：

```text
revision_id
run_id
series_id
date
old_value
new_value
difference
relative_difference
source
source_vintage
detected_at
review_status
reviewed_at
review_note
```

### 实现要求

- 写入前区分：
  - unchanged overlap；
  - new observation；
  - historical revision。
- new observations 使用 INSERT，不覆盖。
- unchanged overlap 不重写。
- historical revision 写入 audit，不自动覆盖。
- production raw 路径禁止调用通用 `INSERT OR REPLACE`。
- 新增和修订计数必须在写入前计算。
- 任一异常必须正确结束 update run。

### 完成门禁

- 修订记录保留旧值和新值；
- observations 中旧值未被静默覆盖；
- new/revised 计数正确；
- update run 没有残留 `running` 状态。

## Loop 5：实现受影响 derived 自动复算

### 修改范围

- `scripts/recompute_derived.py`
- `scripts/validate_update.py`
- metric dependency 相关代码
- 对应测试

### 实现要求

- 从 `metric_definitions.input_series_json` 建立依赖关系。
- raw 更新成功后只复算受影响的下游 derived。
- 支持至少两层依赖。
- 复算记录 calculation version 和 run id。
- 复算失败时不得把整个 update run 标记为完全成功。

### 完成门禁

- 修改 fixture raw 值后，下游 derived 自动改变；
- 无关 derived 不被重算；
- 复算失败可审计。

## Loop 6：完成 3–5 条真实 Wind 闭环

### 选择原则

只选择：

- 月度；
- 指标概念清楚；
- 单位清楚；
- Excel 最近两个点非零；
- 不需要复杂币种转换的序列。

### 执行步骤

每条序列依次完成：

1. Wind MCP 查询；
2. 保存原始返回；
3. 核对 Wind code、name、unit 和 frequency；
4. transform；
5. 最近两个数据库实际日期 overlap；
6. 标记 `wind_verified=true`；
7. 重建 update plan；
8. dry run；
9. 受控写入；
10. revision audit；
11. derived 复算；
12. 更新覆盖文档。

### 禁止

- 使用 iFind 替代；
- 使用相似指标；
- 放宽容差制造通过；
- 使用任意比例；
- 一个点通过就标记 verified。

### Phase 1 Gate

必须同时满足：

- 至少 3 条真实 Wind 闭环成功；
- update plan 可由当前代码重复生成；
- transform 在校验前执行；
- 两点重叠强制执行；
- revision audit 生效；
- downstream derived 自动复算；
- 所有 Phase 1 测试通过。

未通过时不得进入 Phase 2。

---

# Phase 2：收口正式图表数据

## Loop 7：迁移剩余图表关键 derived

### 必须优先处理

- `fx_fwd:AB`
- `fx_fwd:AD`
- `fx_fwd:AJ`
- `fx_fwd:AN`
- `sec_eq:AF`
- `sec_eq:AH`
- `sec_eq:AJ`

### 修改范围

- `scripts/recompute_derived.py`
- `scripts/migrate_chart_derived.py`
- `metric_definitions`
- 对应测试

### 执行要求

每条指标必须记录：

- 业务定义；
- 公式；
- 输入序列；
- 频率；
- 单位；
- 符号；
- 缺失值规则；
- Excel 公式或来源范围；
- Python 实现；
- 最近 24 点校验；
- 完整公共区间校验。

如果 `fx_fwd:AN` 等指标本质是外部原始数据，不得为了清零
`excel_vlookup` 而伪装成 derived；应重新分类为 raw 或
legacy_external，并明确更新来源。

### 完成门禁

- chart catalog 引用的 derived 中：
  - `excel_cached` = 0；
  - `excel_vlookup` = 0。
- 每条指标有可执行实现和测试；
- 指标通过率与数据点通过率分开报告。

## Loop 8：统一 catalog、SQLite 和 Data Dictionary

### 修改范围

- `config/series_catalog.json`
- SQLite `series`
- `docs/DATA_DICTIONARY.md`
- 导入、同步和验证脚本

### 必须处理

- catalog-only 29 条序列；
- `Column_*`；
- unknown 或空单位；
- raw / derived / manual 分类；
- 日期轴误识别；
- 正式图表 5 条缺单位序列。

### 处理规则

每条 catalog-only 序列必须明确属于：

- import_to_db；
- metadata_only；
- delete_from_catalog；
- out_of_scope。

不得仅为追求数字一致而删除业务序列。

### 完成门禁

- catalog、SQLite、Data Dictionary 统计一致；
- 正式图表序列无 `Column_*`；
- 正式图表序列单位完整；
- 分类和频率可审计。

## Loop 9：修复 trailing zeros 与日期频率

### 修改范围

- 数据清理或导入脚本；
- `scripts/validate_all.py`
- SQLite；
- 对应测试

### 执行要求

逐条判断尾部零是：

- 真实零；
- 未发布月份占位；
- Excel 公式填充；
- 数据源停更；
- 频率错位。

只有后四类可转换为 null、删除或标记停更。

重点检查：

- FDI；
- 服务贸易；
- 证券 EQ；
- 证券 FI；
- FDI 季度日期。

### Phase 2 Gate

- 正式图表不依赖 Excel 缓存公式；
- 正式图表单位完整；
- 未发布月份不显示为零；
- catalog、SQLite 和字典一致；
- `python3 scripts/validate_all.py` 全部通过。

---

# Phase 3：完成图表语义与响应式质量

## Loop 10：实现真正的 seasonality band

### 修改范围

- `scripts/generate_dashboard.py`
- `config/chart_catalog.json`
- 图表 fixture 和测试

### 必须实现

- x 轴固定为 1–12 月；
- 历史 min-max band；
- 历史均值或中位数；
- 当年轨迹；
- 可选去年同期；
- 未发布月份为 null；
- 指标选择器真正切换数据。

### 适用图表

- `fx_cspot_seasonality`
- `fx_cross_seasonality`
- `trade_goods_seasonality`
- `fdi_seasonality`

### 完成门禁

- 季节性图不再使用普通年月时间轴；
- 1–12 月标签完整；
- 当年未发布月份为空；
- selector 实际改变图表。

## Loop 11：修复轴、单位和摘要合同

### 修改范围

- `scripts/generate_dashboard.py`
- `config/chart_catalog.json`

### 必须修复

- 左轴标题不得硬编码“亿美元”；
- 右轴标题不得硬编码“右轴”；
- 轴标题、颜色与数据集绑定；
- signed flow 显示零轴；
- 汇率轴标明升值/贬值方向；
- summary 不再自动取前 10 个 raw 序列；
- summary 由 catalog 明确配置；
- signed flow 默认显示：
  - 最新值；
  - 前值；
  - 变化额；
  - 3MMA；
  - 历史分位。
- 不用红绿表达好坏。

### 完成门禁

- 每张图的单位与 catalog 一致；
- 摘要指标是业务选择，不是列顺序选择；
- 图表与摘要数值一致。

## Loop 12：修复窄屏和 CSS

### 必须修复

- `@@media` 改为有效 `@media`；
- 390×844 下：
  - `scrollWidth <= clientWidth`；
  - 图表不被裁切；
  - 图例可换行或折叠；
  - 顶部导航可用；
  - 时间范围按钮可用；
  - 导出按钮不溢出。
- 桌面 1280×720 不得退化。

### 完成门禁

浏览器实际检查：

- 1280×720；
- 390×844；
- 即远期；
- 季节性图；
- 证券 EQ 散点；
- 证券 FI 散点；
- 最长图例模块。

## Loop 13：建立 66 张原图机器化处置表

### 新增配置

创建例如：

```text
config/excel_chart_disposition.json
```

每张原图必须包含：

```json
{
  "excel_chart_id": "3.即远期#01",
  "status": "retained",
  "target_chart_ids": ["fx_fwd_total_supply"],
  "reason": ""
}
```

允许状态：

- `retained`
- `merged_into`
- `rebuilt_as`
- `deleted_with_reason`

### Validator

必须确认：

- 原图恰好 66 张；
- 66/66 均有唯一记录；
- retained / merged / rebuilt 的 target chart 存在；
- deleted 必须有原因；
- 不存在重复或未知原图 ID。

### Phase 3 Gate

- 29 张正式图均可渲染；
- 季节性合同完成；
- 单位与摘要合同完成；
- 桌面和移动端通过；
- 66/66 原图处置可机器验证。

---

# Phase 4：端到端测试和文档收口

## Loop 14：重构生产测试门禁

### 测试方向

优先使用 pytest，测试数量应表示测试用例，不是 assertion 数量。

至少覆盖：

- mapping metadata；
- Wind verified 过滤；
- update plan 可重复生成；
- 最后两个真实日期；
- transform chain；
- staging 合同；
- 0/1/2 overlap；
- revision audit；
- new/revised 计数；
- downstream recompute；
- chart catalog 完整性；
- 图表 derived 实现；
- seasonality 1–12 月；
- 66 图处置表；
- HTML JS 语法；
- CSS media query；
- 浏览器 9 模块；
- 桌面与移动端无溢出；
- PNG 与 CSV 导出。

### 完成门禁

- 不再存在“错误合同测试通过”；
- 针对性测试和全量测试均通过；
- `validate_all.py` 通过；
- HTML 浏览器无错误。

## Loop 15：重新生成状态文档

### 修改

建立一个状态生成脚本，由数据库和配置生成：

- `README.md`
- `docs/PROGRESS_REPORT.md`
- `docs/WIND_COVERAGE.md`
- `docs/DATA_DICTIONARY.md`
- `docs/REVIEW_HANDOFF.md`

### 文档必须区分

- raw / derived / manual；
- Python 复算数；
- Excel 缓存数；
- iFind historical candidate；
- Wind verified；
- mapping pending；
- update-plan production eligible；
- primary / drill-down；
- 66 图处置覆盖；
- 数据截至日期；
- 测试结果；
- 已知限制。

禁止使用模糊的总体“完成百分比”替代分项状态。

## Loop 16：最终独立审阅

由未参与实现的 reviewer 审查：

1. 生产更新安全；
2. 数据和指标语义；
3. 测试是否真正覆盖门禁；
4. HTML 功能；
5. 桌面和移动端；
6. 文档与真实状态一致性。

发现 P0/P1 问题时返回对应 Loop，不得直接结束。

---

# 6. 最终完成条件

只有以下全部满足才能宣告 v1 完成：

- 至少 3 条真实 Wind 序列完成端到端更新闭环；
- 生产计划只包含 `wind_verified=true`；
- validation dates 是数据库最后两个真实日期；
- 少于两个 overlap 时强制拒绝；
- transform 在校验前执行；
- 历史修订不静默覆盖；
- revision audit 可查询；
- raw 更新触发下游 derived 复算；
- 正式图表 derived 不含 `excel_cached` / `excel_vlookup`；
- 正式图表单位完整；
- trailing zeros 已逐条处置；
- `validate_all.py` 全通过；
- 29 张图均可渲染；
- 4 个 seasonality 图符合 1–12 月 band 合同；
- 66/66 原图处置可机器验证；
- 桌面和 390px 窄屏无横向溢出；
- 9 模块、时间筛选、PNG、CSV 通过真实浏览器测试；
- 全量自动测试通过；
- 状态文档由真实数据生成且相互一致；
- 独立 reviewer 无 P0/P1 阻塞意见。

# 7. 停止和升级条件

出现以下情况时，停止对应路径并明确报告：

- Wind MCP 不可调用；
- Wind 返回的指标概念、单位或频率不能证明与 Excel 一致；
- 需要使用未经授权的数据源；
- 指标公式无法从 Excel 或可靠定义还原；
- 必须覆盖用户未提交改动；
- 必须扩大首版范围；
- 视觉测试环境不可用；
- 需要用户决定是否接受口径变化。

报告必须包含：

- 阻塞项；
- 已尝试方法；
- 证据；
- 影响范围；
- 可继续完成的工作；
- 需要用户回答的最小问题。

# 8. 最终交接格式

最终回复和 `docs/REVIEW_HANDOFF.md` 必须列明：

1. 完成的 Loop；
2. 未完成的 Loop；
3. Wind verified、pending、unsupported 数量；
4. 本次真实更新的序列和日期；
5. revision audit 结果；
6. derived 复算覆盖；
7. 数据质量检查；
8. 图表和 66 图覆盖；
9. 桌面与移动端结果；
10. 测试命令及输出摘要；
11. 修改文件；
12. 真实限制和待用户决定事项。

# 9. 开始指令

现在开始执行，不要重新写计划。

第一轮操作：

1. 读取必读文件；
2. 执行 Loop 0；
3. 将实时基线写入 `docs/REVIEW_HANDOFF.md`；
4. 执行 Loop 1；
5. 未通过当前门禁时持续修正，不跳到后续阶段；
6. 持续执行，直到满足最终完成条件或遇到明确外部阻塞。
