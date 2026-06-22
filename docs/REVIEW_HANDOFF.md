# Review Handoff

> 最后更新：2026-06-22 11:33 CST

## 当前完成度

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 0: 状态恢复 | ✅ 完成 | Git 仓库初始化，目录结构就绪 |
| Step 1: 结构盘点 | ✅ 完成 | 407 序列编目，DATA_DICTIONARY + EXCEL_LINEAGE |
| Step 2: 最小数据库 | ✅ 完成 | 3.即远期 端到端验证：导入→复算→HTML，100% 匹配 Excel |
| Step 3: 全部历史导入 | ✅ 完成 | 9 模块 385 序列 131,603 观测值，幂等导入 |
| Step 4: 迁移自定义指标 | 🔄 部分 | 3.即远期 5 个衍生序列完成；其他 8 模块待迁移 |
| Step 5: Wind 映射 | ⬜ 待开始 | |
| Step 6: 增量更新 | ⬜ 待开始 | |
| Step 7: HTML 看板 | ✅ 完成 | 9 模块 Chart.js 单文件 HTML（4 MB），含导出、时间范围 |
| Step 8: 验证 | ✅ 完成 | 7/8 核心检查通过；1 个已知问题（trailing zeros） |
| Step 9: 交接文件 | ✅ 本轮更新 | |

## 本轮变更

- ✅ Step 3: 全部 9 个模块导入 SQLite（385 序列，131,603 obs）
- ✅ Step 7: 完整 9 模块 HTML 看板生成（Chart.js + datalabels，内联离线）
- ✅ Step 8: 全面验证脚本 `validate_all.py`（8 项检查）
- ✅ 修复 `last_date` 计算 bug（从 observations 表反推）
- ✅ 生成 README.md
- ✅ 更新本文件

## 已验证内容

### 数据库完整性
- ✅ 唯一键约束（无重复 observation）
- ✅ 无 NULL series_id/date
- ✅ 无非有限值（Infinity/NaN）
- ✅ 所有非 manual 序列均有观测值
- ✅ 幂等性（重复运行不产生重复记录）
- ✅ 9 模块全覆盖
- ⚠️ 30 序列有 trailing zeros（Excel 占位零，待增量更新处理）
- ⚠️ 9 个日期列（:A）无观测值（符合预期）

### 衍生指标验证
- ✅ `fx_fwd:supply_demand` = AB + AD + AJ：231 点，100% 匹配 Excel（max_diff=0.0）
- ✅ `fx_fwd:deriv_flow` = AD + AJ：231 点，100% 匹配 Excel（max_diff=0.0）
- ✅ `fx_fwd:supply_demand_3mma`：229 点，逻辑正确
- ✅ `fx_fwd:supply_demand_12mma`：220 点，逻辑正确

### HTML 看板
- ✅ 9 模块导航 + 时间范围控制（全部/5年/3年/1年/年初至今）
- ✅ 3.即远期 4 张图表（供求总览、即期vs衍生品、银行自身、远期签约）
- ✅ 其余 8 模块自动发现并渲染图表
- ✅ 图表图片导出（PNG 2x）+ 数据下载（CSV）
- ✅ 最新数据摘要表（含环比变化）
- ✅ 单文件自包含（Chart.js + datalabels 内联）

## 未覆盖内容

- ❌ 8 个模块的复杂衍生指标（Step 4 仅完成 3.即远期）
- ❌ Wind MCP 系列映射（Step 5）
- ❌ 增量更新 + 两点校验（Step 6）
- ❌ 单元测试（未在首轮实施）
- ❌ 跨表引用验证（3.货物贸易、3.证券FI 的 VLOOKUP to 3.即远期）

## Wind 覆盖率

- 0/147 raw 序列已建立 Wind 映射
- 所有 raw 序列当前标记为 `excel_seed`

## 已知数据差异

| 问题 | 严重性 | 说明 |
|------|--------|------|
| Trailing zeros | 低 | 30 序列末尾有连续零值（未发布月份的占位） |
| 日期列无观测 | 信息 | 9 个 :A 列为日期标识，不属于数据观测 |
| last_date 历史bug | 已修复 | 导入时的 last_date 偏移已通过 observations 反推修正 |

## 当前 blocker

- 无硬阻塞。建议下一步：Step 4（补充剩余 8 模块衍生指标）或 Step 5（Wind 映射）。

## 运行命令

```bash
# 导入（幂等）
python3 scripts/import_excel_seed.py --all

# 复算衍生指标
python3 scripts/recompute_derived.py --module "3.即远期"

# 生成看板
python3 scripts/generate_dashboard.py

# 验证
python3 scripts/validate_all.py

# 打开看板
open reports/fx_flow_dashboard.html
```

## 关键文件

| 文件 | 用途 | 行数/大小 |
|------|------|-----------|
| `AGENT_LOOP.md` | 执行规范 | 545 行 |
| `README.md` | 项目说明 | ~120 行 |
| `config/series_catalog.json` | 407 序列编目 | ~200 KB |
| `data/monthly_brief.sqlite` | 运行时数据库 | ~15 MB |
| `docs/DATA_DICTIONARY.md` | 数据字典 | ~200 行 |
| `docs/EXCEL_LINEAGE.md` | 数据血缘 | ~180 行 |
| `scripts/lib.py` | 共享库（DB+验证） | ~200 行 |
| `scripts/import_excel_seed.py` | Excel→SQLite | ~180 行 |
| `scripts/recompute_derived.py` | 衍生指标复算 | ~200 行 |
| `scripts/generate_dashboard.py` | HTML 看板生成 | ~590 行 |
| `scripts/validate_all.py` | 全面验证 | ~180 行 |
| `reports/fx_flow_dashboard.html` | 最终产物 | ~4 MB |

## 建议审阅顺序

1. `README.md` — 快速了解项目
2. `reports/fx_flow_dashboard.html` — 打开看板，体验交互
3. `docs/DATA_DICTIONARY.md` — 了解数据结构
4. `docs/EXCEL_LINEAGE.md` — 了解数据血缘
5. `scripts/generate_dashboard.py` — 看板生成逻辑
6. `scripts/validate_all.py` — 运行验证确认质量
