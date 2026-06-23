# Martin Monthly Brief 下一阶段工作计划

> 审阅日期：2026-06-23  
> 审阅基准：commit `4b96770`  
> 目标：从“可演示看板原型”推进到“可安全更新、可审计、可长期使用的生产版本”

## 一、当前判断

项目方向正确，不建议推翻 SQLite → Python → Chart.js 架构。

当前真实状态应拆开评价：

| 工作面 | 当前评价 |
|---|---|
| Excel 历史迁移 | 基本完成，可继续使用 |
| SQLite 数据底座 | 可用，但元数据和尾部零值仍需清理 |
| 衍生指标 | 核心部分已复算，但正式图表仍引用 Excel 缓存指标 |
| Wind 映射 | 尚未形成正式 Wind 验证覆盖 |
| 增量更新 | 有代码框架，但不满足安全写入条件 |
| 桌面看板 | 可演示，29 张图可渲染 |
| 图表语义 | 部分完成，季节性和单位轴尚未落实 |
| 移动端 | 未通过 |
| 测试与文档 | 测试存在假通过，文档口径明显冲突 |

因此，不应将阶段 A 和阶段 B 标记为全部完成。项目目前是“历史数据库 + 桌面看板原型完成，生产更新链和正式 QA 未完成”。

## 二、审阅发现

### P0：生产更新链未通过

1. `scripts/build_update_plan.py`
   - 不能读取 `wind_mapping.json` 的 `_metadata` 行；
   - 只识别旧状态 `verified` / `verified_with_transform`；
   - 当前映射改为 `verified_exact` / `verified_unit_transform` 后，过滤 metadata 再重建计划得到 0 条；
   - 现有 103 条 `update_plan.json` 不可由当前代码复现。

2. `scripts/validate_update.py`
   - 零重叠点仍返回通过；
   - 只要求至少一个重叠点，而不是两个；
   - 写入仍通过 `INSERT OR REPLACE` 覆盖旧值；
   - 新增与修订数量在写入后判断，统计会失真；
   - 没有独立 revision audit；
   - 写入后没有触发受影响 derived 指标复算。

3. `scripts/fetch_wind.py`
   - mapping 中的受控 transform 没有在校验前应用；
   - 查询统一尝试“亿美元/人民币亿元”，没有严格使用每条 mapping 的单位合同；
   - 当前 staging 文件仍是 2026-06-22 的空模拟结果；
   - 尚无一条生产映射标记为 `wind_verified=true`。

4. 当前 45 条 `verified_exact` / `verified_unit_transform` 全部来自 iFind 历史验证，`wind_verified=false`，不应进入 Wind 生产计划。

### P0：测试门禁存在假通过

- `python3 scripts/test_all.py` 报告 84/84，但测试仍明确断言“零重叠应通过”。
- update-plan gate 只检查现有 JSON 有两个不同日期，没有检查：
  - 是否能从当前 mapping 重建；
  - 日期是否确实是数据库最后两个实际观测点；
  - mapping 是否已由 Wind 验证。
- metric-definition gate 只检查有记录，没有拒绝 `excel_cached`。
- chart-catalog gate 只检查普通 datasets，没有完整检查 scatter、单位、derived 实现和数据质量。
- `python3 scripts/validate_all.py` 当前失败：30 条序列存在 trailing zeros。

### P1：数据与元数据尚未收口

- `series_catalog.json` 有 412 条，SQLite 有 383 条，catalog 多出 29 条。
- SQLite 仍有 86 个 `Column_*` 展示名。
- SQLite 有 144 条空或 unknown 单位。
- 正式图表使用的 79 条唯一序列中，5 条单位不明确。
- 正式图表使用的 62 条 derived 中仍有：
  - 6 条 `excel_cached`；
  - 1 条 `excel_vlookup`。
- 30 条尾部零值集中在 FDI、证券 EQ/FI 和服务贸易等模块，可能把未发布月份误当成真实数据。

### P1：看板功能与方案仍有差距

已经完成：

- 9 个模块；
- 29 张图；
- catalog 驱动；
- 普通趋势、柱线组合、双轴和两张散点回归图；
- 时间范围、CSV 和 PNG 入口；
- 桌面浏览器无控制台错误。

尚未完成：

- `seasonality_band` 只是普通多序列时间图，没有 1–12 月横轴、历史 min-max band、均值和当年轨迹；
- 所有普通图左轴标题在生成器中硬编码为“亿美元”；
- 双轴右轴标题硬编码为“右轴”；
- 摘要表仍自动取前 10 个 raw 序列，并使用普通百分比变化及红绿方向；
- 390px 窄屏实测页面宽度为 484px，图表和图例横向裁切；
- CSS 输出为无效的 `@@media`；
- catalog 只直接引用 46 张原 Excel 图，剩余删除/吸收关系主要存在于迁移文档，没有机器可验证的 66 图覆盖表。

### P1：文档不可作为状态来源

`README.md`、`PROGRESS_REPORT.md` 和 `REVIEW_HANDOFF.md` 同时存在以下冲突：

- 88、224、62 等不同复算口径；
- 124 条 iFind 验证与 45 条严格状态混用；
- 一处称散点图已完成，另一处称未实现；
- 一处称 62/62 图表指标已复算，数据库实际仍有 7 条 Excel 缓存/查找指标；
- 一处称阶段 A/B 全部完成，但生产更新门禁实际未通过。

## 三、下一阶段执行顺序

## Phase 1：重建可信的生产更新门禁

### Task 1.1：统一 mapping 和 update-plan 合同

**修改：**

- `config/wind_mapping.json`
- `scripts/build_update_plan.py`
- `scripts/test_all.py`

**要求：**

1. 安全跳过 `_metadata`。
2. 只允许 `wind_verified=true` 且状态为：
   - `verified_exact`
   - `verified_unit_transform`
3. validation dates 直接查询数据库最后两个实际观测日期。
4. 季度、月度、日度均不得用日期减法猜测重叠日期。
5. update plan 必须可重复生成，生成结果与当前 mapping 一致。

**验收：**

- 当前没有 Wind 正式验证时，生产计划应明确为 0，而不是沿用 103 条旧计划；
- 对测试 fixture 加入 3 条已验证序列后，计划应稳定生成 3 条；
- 每条计划包含两个不同且真实存在的数据库日期。

### Task 1.2：重写安全校验与修订写入

**修改：**

- `scripts/validate_update.py`
- `scripts/lib.py`
- SQLite migration
- `scripts/test_all.py`

**要求：**

1. 少于两个有效重叠点直接拒绝。
2. transform 在重叠校验前应用。
3. 写入前区分：
   - new observation；
   - unchanged overlap；
   - historical revision。
4. 新建 `observation_revisions` 或等价审计表。
5. 未审核修订不得覆盖 observations。
6. 禁止生产 raw 更新使用通用 `INSERT OR REPLACE`。
7. 写入成功后按依赖关系复算下游 derived。
8. run 无论成功或异常均结束状态。

**验收：**

- 零重叠、一个重叠、一个通过一个失败均拒绝；
- 两个通过才允许新增；
- 修订保留旧值、新值、来源、run 和审核状态；
- 新增/修订计数准确；
- raw 更新后目标 derived 数值同步变化。

### Task 1.3：完成小范围真实 Wind 闭环

**修改：**

- `scripts/wind_mcp_adapter.py`
- `scripts/fetch_wind.py`
- `config/wind_mapping.json`
- `docs/WIND_COVERAGE.md`

**执行：**

1. 只选择 3–5 条概念、频率、单位最清楚的月度序列。
2. 保存 Wind 返回的代码、名称、单位和原始值。
3. 做最近两个实际日期重叠验证。
4. 通过后标记 `wind_verified=true`。
5. 执行一次 dry run 和一次受控写入。

**验收：**

- 至少 3 条序列完成真实 fetch → staging → transform → overlap → write → audit → downstream recompute；
- 失败序列有明确原因，不能回退到 iFind。

## Phase 2：收口正式图表数据

### Task 2.1：清理图表关键 derived

**优先序列：**

- `fx_fwd:AB`
- `fx_fwd:AD`
- `fx_fwd:AJ`
- `fx_fwd:AN`
- `sec_eq:AF`
- `sec_eq:AH`
- `sec_eq:AJ`

**修改：**

- `scripts/recompute_derived.py`
- `scripts/migrate_chart_derived.py`
- `metric_definitions`
- 对应测试

**验收：**

- 正式图表不再引用 `excel_cached` 或 `excel_vlookup`；
- 最近 24 点和完整公共区间分别校验；
- 指标通过率和数据点通过率分别报告。

### Task 2.2：统一元数据和尾部缺失处理

**修改：**

- `config/series_catalog.json`
- SQLite `series`
- `docs/DATA_DICTIONARY.md`
- 导入与验证脚本

**要求：**

- 明确 29 条 catalog-only 序列是补录、删除还是不入库；
- 清理正式展示范围的 `Column_*`；
- 补齐正式图表单位；
- 将未发布月份零值转为空值或明确标记真实零；
- FDI 季度序列恢复正确 period end。

**验收：**

- catalog、SQLite 和 Data Dictionary 数量一致；
- 正式图表序列无 unknown 单位；
- `validate_all.py` 全部通过。

## Phase 3：完成图表语义和响应式质量

### Task 3.1：实现真正的季节性组件

**修改：**

- `scripts/generate_dashboard.py`
- `config/chart_catalog.json`
- 图表测试 fixture

**要求：**

- x 轴固定 1–12 月；
- 历史 min-max band；
- 历史均值或中位数；
- 当年轨迹；
- 未发布月份为 null；
- 指标选择器真正可交互。

### Task 3.2：修复单位、摘要与响应式布局

**修改：**

- `scripts/generate_dashboard.py`
- `config/chart_catalog.json`

**要求：**

- y 轴标题由 catalog 的单位生成；
- 双轴标题和颜色绑定对应序列；
- 修复 `@@media`；
- 390px viewport 不产生页面级横向溢出；
- 长图例可换行或折叠；
- signed flow 摘要改为最新值、前值、变化额、3MMA、历史分位；
- 不用红绿表达好坏。

**验收：**

- 桌面 1280×720 和移动 390×844 均通过；
- `scrollWidth <= clientWidth`；
- 9 个模块导航、时间筛选、PNG、CSV 均实际测试。

### Task 3.3：机器化验证 66 张原图处置

为每张原 Excel 图建立状态记录：

- retained；
- merged_into；
- rebuilt_as；
- deleted_with_reason。

validator 必须确认 66/66 均有唯一处置结果，并且所有保留目标 chart_id 存在。

## Phase 4：测试与文档收口

### Task 4.1：建立端到端测试

测试至少覆盖：

- 当前 mapping → update plan 可重复生成；
- Wind staging 合同；
- transform 后两点重叠；
- revision audit；
- derived 依赖复算；
- chart catalog 全字段；
- seasonality 输出；
- HTML JS/CSS；
- 浏览器加载和 9 模块切换；
- 桌面与移动端无溢出；
- PNG 与 CSV 导出。

建议将当前自建 assertion runner 逐步迁移到 `pytest`，使测试数等于测试用例数，而不是 assertion 次数。

### Task 4.2：重新生成状态文档

由单一脚本从数据库和配置生成：

- `README.md`
- `docs/PROGRESS_REPORT.md`
- `docs/WIND_COVERAGE.md`
- `docs/DATA_DICTIONARY.md`
- `docs/REVIEW_HANDOFF.md`

禁止手工维护完成百分比和相互冲突的统计。

## 四、阶段门禁

### Gate 1：允许批量 Wind 更新

- 至少 3 条真实 Wind 闭环成功；
- 两点重叠强制执行；
- transform 已应用；
- revision audit 生效；
- update plan 可重复生成。

### Gate 2：允许认定正式图表数据可信

- 所有正式图表 derived 均为 Python 复算；
- 正式图表单位完整；
- trailing zeros 清理；
- catalog、SQLite 和字典一致。

### Gate 3：允许交付 v1

- 29 张图均能渲染；
- 66/66 原图处置可机器验证；
- 季节性组件符合合同；
- 桌面和移动端通过；
- 更新、导出和导航端到端测试通过；
- 文档统计一致。

## 五、建议排期

| 工作包 | 建议投入 | 结果 |
|---|---:|---|
| Phase 1：生产更新门禁 | 2–3 个工作日 | 3–5 条真实 Wind 闭环 |
| Phase 2：图表数据收口 | 1–2 个工作日 | 正式图表不依赖 Excel 缓存 |
| Phase 3：图表精修 | 2 个工作日 | 季节性、单位和移动端完成 |
| Phase 4：测试与文档 | 1 个工作日 | 可审计 v1 交付 |

执行优先级必须是 Phase 1 → Phase 2 → Phase 3 → Phase 4。Phase 1 未通过前，不新增图表或扩大模块范围。
