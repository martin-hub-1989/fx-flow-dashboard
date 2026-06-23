# 图表方案执行 Loop（历史文件）

> 本文件已与 `CORRECTION_LOOP.md` 合并为
> `MASTER_EXECUTION_LOOP.md`。执行 agent 应以统一 Loop 为准；
> 本文件只保留用于追溯原图表实施计划。

## 前置门禁

只有 `CORRECTION_LOOP.md` 的停止条件全部满足后，才开始本 loop。

若以下任一条件不满足，立即停止图表实现并返回修正 loop：

- HTML JavaScript 语法通过；
- chart catalog 引用的指标全部存在；
- 正式图表 derived 指标均由 Python 复算；
- 单位、频率和日期标签明确；
- 不存在未来占位零；
- 生产数据来源状态可信。

## Loop 0：读取图表方案

读取：

- `docs/CHART_MIGRATION_PLAN.md`
- `.inspection/chart_inventory.json`
- `docs/CURRENT_PROJECT_REVIEW_20260622.md`
- 当前 `config/series_catalog.json`
- 当前 SQLite 元数据

不得只阅读现有 `generate_dashboard.py` 后自行决定图表。

## Loop 1：建立 chart catalog

创建 `config/chart_catalog.json`。

每个新图必须包含：

- chart_id
- module
- primary / drilldown
- 分析问题
- 默认 takeaway
- 原 Excel 图表编号
- 图表 family 和具体类型
- required_series
- 单位
- 频率
- 默认时间范围
- 轴配置
- 颜色策略
- tooltip 字段
- 数据质量门禁
- 空数据 fallback

完成后写 catalog validator：

- series 必须存在；
- derived 必须有 metric definition；
- 单位不同的多序列必须声明双轴或转换；
- scatter 必须有 x/y 同粒度数据；
- seasonality 必须有月份和历史样本；
- chart_id 唯一。

## Loop 2：实现共用图表组件

按顺序实现：

1. 月度 signed bar + moving-average line；
2. 堆叠柱 + total line；
3. 普通多线趋势；
4. 双轴趋势；
5. seasonality band；
6. percentile line；
7. scatter + regression；
8. floating range + current marker；
9. 最新值摘要表。

每个组件必须有最小 fixture 和截图/结构验证。

## Loop 3：先完成即远期模块

按方案实现即远期 6 张保留图。

验证：

- 原 Excel 分解关系一致；
- signed flow 零轴清晰；
- 12MMA 与月度值不混淆；
- 远期、履约和期权方向正确；
- USDCNY 双轴方向和单位明确；
- 图片和 CSV 可导出。

即远期未通过，不得批量复制到其他模块。

## Loop 4：按分析链扩展模块

按以下顺序：

1. 代客即期；
2. 涉外收付；
3. 货物贸易；
4. 贸易商；
5. 服务贸易；
6. FDI；
7. 证券 EQ；
8. 证券 FI。

每完成一个模块：

1. 实现主图；
2. 实现 drill-down；
3. 检查与原 Excel 图表清单的覆盖关系；
4. 运行 catalog validator；
5. 运行 JS 语法和页面初始化测试；
6. 更新 `docs/REVIEW_HANDOFF.md`。

## Loop 5：季节性图合并

建立一个统一 seasonality 组件：

- x 轴固定 1–12 月；
- 历史 min-max 区间；
- 历史均值；
- 当年轨迹；
- 可选择指标；
- 未发布月份显示为空，不显示 0；
- 支持去年同期或历史中位数可选基准。

替代原 Excel 中多张复制的季节性图。

## Loop 6：关系图和散点图

### 双轴趋势

- 仅用于不同单位；
- 左右轴颜色与对应序列一致；
- 汇率轴明确升值/贬值方向；
- 不通过截断轴制造相关性。

### 散点图

- 至少 20 个有效样本；
- x/y 同频率和同窗口；
- 显示样本数；
- 显示相关系数；
- 添加 OLS 回归线；
- 全历史和近期使用时间筛选，不复制两张图；
- 历史阶段差异用颜色或点形区分。

## Loop 7：摘要与交互

实现：

- 时间范围：全部、5Y、3Y、1Y、YTD；
- 模块内指标选择；
- 图表说明；
- 最新有效日期；
- 更新状态；
- 缺失/停更提示；
- CSV 下载；
- PNG 导出；
- tooltip；
- 移动端堆叠布局。

signed flow 摘要默认显示：

- 最新值；
- 前值；
- 变化额；
- 3MMA；
- 历史分位；

不默认显示普通百分比环比。

## Loop 8：最终 QA

自动检查：

- HTML 结构；
- JavaScript 语法；
- chart catalog 完整性；
- 数据引用；
- 空图；
- 非有限值；
- 导出函数；
- 时间筛选；
- 模块导航。

人工/视觉检查：

- 零轴；
- 负值标签；
- 双轴可读性；
- 图例和标题；
- 季节性 band；
- 极值和长标签；
- 笔记本宽度；
- 移动端宽度；
- 图表与摘要数值一致。

## 完成条件

- 66 张原图全部映射到保留、合并、重做或删除。
- 默认页面图表不超过约 24 张。
- 所有其他保留内容可在 drill-down 或选择器中访问。
- 不存在自动选择前 6 个 raw 序列的逻辑。
- 所有模块使用共享组件。
- HTML 可离线打开。
- JavaScript 语法与初始化测试通过。
- 图表数据来自 SQLite。
- 每张图均显示单位、频率、截至日期和来源。
- Review Handoff 列明原图覆盖率、最终图表数和已删除图表。
