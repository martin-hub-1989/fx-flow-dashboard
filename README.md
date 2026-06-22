# FX Flow Dashboard — 结售汇与跨境资金流看板

从 `FX Chartbook - Flow 0515.xlsx` 重构的交互式数据看板。
采用 SQLite → Python 复算 → Chart.js HTML 架构。

## 快速开始

```bash
# 1. 导入 Excel 历史种子（幂等）
python3 scripts/import_excel_seed.py --all

# 2. 复算衍生指标
python3 scripts/recompute_derived.py --module "3.即远期"

# 3. 生成 HTML 看板
python3 scripts/generate_dashboard.py

# 4. 验证
python3 scripts/validate_all.py

# 打开 reports/fx_flow_dashboard.html
```

## 架构

```
Excel 历史种子 (只读)
      ↓
SQLite (data/monthly_brief.sqlite)
  ├── series        — 序列元数据
  ├── observations  — 观测值 (series_id, date, value)
  ├── metric_definitions — 衍生指标公式
  ├── update_runs   — 更新运行日志
  └── validation_events — 校验事件
      ↓
Python 复算层 (scripts/recompute_derived.py)
      ↓
HTML 生成器 (scripts/generate_dashboard.py)
      ↓
单文件交互式看板 (reports/fx_flow_dashboard.html)
```

## 覆盖模块

| 模块 | 工作表 | 序列数 | 频率 |
|------|--------|--------|------|
| 即远期供求 | 3.即远期 | 44 | 月度 |
| 代客即期结构 | 3.代客即期 | 47 | 月度 |
| 涉外收付 | 3.涉外收付 | 55 | 月度 |
| 货物贸易 | 3.货物贸易 | 46 | 月度 |
| 贸易商意愿 | 3.贸易商 | 46 | 月度 |
| 服务贸易 | 3.服务贸易 | 6 | 月度 |
| FDI | 3.FDI | 55 | 月度 |
| 证券资金流：EQ | 3.证券EQ | 30 | 日度 |
| 证券资金流：FI | 3.证券FI | 56 | 月度 |
| **合计** | | **385** | |

## 目录结构

```
.
├── README.md
├── AGENT_LOOP.md              ← 执行规范
├── config/
│   └── series_catalog.json    ← 407 序列编目
├── data/
│   └── monthly_brief.sqlite   ← 运行时数据库
├── docs/
│   ├── DATA_DICTIONARY.md     ← 数据字典
│   ├── EXCEL_LINEAGE.md       ← 数据血缘
│   └── REVIEW_HANDOFF.md      ← 交接文档
├── scripts/
│   ├── lib.py                 ← 共享库
│   ├── import_excel_seed.py   ← Excel → SQLite
│   ├── recompute_derived.py   ← 衍生指标复算
│   ├── generate_dashboard.py  ← HTML 看板生成
│   └── validate_all.py       ← 全面验证
├── templates/
│   ├── chart.min.js           ← Chart.js (内联用)
│   └── datalabels.min.js      ← Datalabels 插件
└── reports/
    └── fx_flow_dashboard.html ← 最终产物
```

## 数据特征

- **总观测值：** 131,603
- **日期范围：** 1994-01 至 2026-05
- **序列分类：** 159 raw / 224 derived / 2 manual
- **所有 raw 序列来源：** Excel EDB 缓存快照
- **所有 derived 序列：** 由 raw 序列通过可审计 Python 代码复算

## 看板特性

- ✅ Chart.js + chartjs-plugin-datalabels（内联，离线可用）
- ✅ 9 个模块，顶部导航切换
- ✅ 时间范围控制（全部/5年/3年/1年/年初至今）
- ✅ 图表图片导出（PNG）
- ✅ 数据下载（CSV）
- ✅ 最新数据摘要表（含环比变化）
- ✅ 单文件自包含（~4 MB）

## 待完成

- [ ] Wind MCP 增量更新映射（Step 5）
- [ ] 安全增量更新流水线（Step 6）
- [ ] 剩余 8 个模块的衍生指标复算（Step 4）
- [ ] 更多图表配置优化
- [ ] 单元测试

## 约束

- 原始 Excel 只读，禁止修改
- 不得扩展到 `待处理数据.xlsx` 中的模块
- 所有 derived 序列必须有公式说明和测试
- 历史修订不可静默覆盖
