# Martin Morning Brief — 项目总结 (Agent 参考)

> 写给后续开发类似项目的 Claude agents。记录架构决策、踩过的坑、复用模式。

---

## 项目概览

一个**单文件自包含**的多资产金融市场交互看板。每天从多个数据源拉取 ~150 个时间序列，生成一个 HTML 文件即可分享给任何人使用——无服务器、无数据库依赖、无前端框架。

**规模指标：**

| 指标 | 数值 |
|------|------|
| 时间序列 | 152 个 |
| 数据源 | 5 层（同花顺 EDB / Wind MCP / Python 复算 / 华泰智研 MCP / 种子 Excel） |
| 看板模块 | 12 个（封面 + 看世界 + 10 个数据模块） |
| Python 脚本 | 9 个（流水线编排 + 数据拉取 + 复算 + 看板生成） |
| HTML 模板 | 1 个（~2900 行，手绘 SVG 图表，零外部 JS 依赖） |
| 项目周期 | ~2 周 |

---

## 一、核心架构决策

### 1.1 单文件 HTML 看板（最重要的决策）

**选型：** 所有数据嵌入一个 HTML 文件，通过 `<script id="dashboard-data" type="application/json">` 承载全部时序数据。

```html
<script id="dashboard-data" type="application/json">{"generated_at": "...", "observations": {...}}</script>
<script>
const DATA = JSON.parse(document.getElementById("dashboard-data").textContent);
// 所有图表从 DATA 渲染
</script>
```

**为什么：**
- 零依赖共享——别人收到文件直接打开就能用
- 不需要 Web 服务器、不需要 npm install
- GitHub Pages 天然兼容（`docs/index.html`）
- 离线可用

**代价：**
- 文件体积大（~25MB 含全部历史数据）
- JSON 序列化/反序列化开销
- 不能做增量更新（每次都重建整个文件）

**适用场景：** 数据量在百万级以下、需要离线/共享、用户不懂技术的场景。不适用：实时数据、超大体积、多用户协同。

---

### 1.2 SQLite 作为单一数据源

**选型：** 所有数据存储在 SQLite 文件中，脚本读写同一个 DB。

```
data/morning_brief.sqlite
├── series (series_id, display_name, unit, update_method, ...)
└── observations (series_id, date, value, UNIQUE(series_id, date))
```

**为什么优于文件/CSV：**
- 单文件、不需安装数据库服务
- 事务保证（不会出现半拉子更新）
- SQL 查询比 pandas 操作 CSV 快得多
- `.gitignore` 一下就行

**关键教训：**
- `series_id` 用命名空间前缀（`trend:`, `fx:`, `valuation:`, `super_cycle:`）——方便分类查询
- `update_method` 字段记录数据来源（`edb_mcp` / `wind_mcp` / `wind_mcp_fallback`）——方便追踪数据链路
- UNIQUE 约束防止重复插入（`INSERT OR REPLACE` / `UPSERT`）

---

### 1.3 多数据源自动降级链

**架构：**

```
拉取序列 X 的最新数据
  ├─ 1. 同花顺 EDB API → 成功 → 验证通过 → ✓
  ├─ 2. EDB 失败/超时 → 自动查 wind_mapping.json → 有映射 → Wind MCP → ✓
  ├─ 3. EDB 验证失败 → 自动 Wind fallback → 二次验证 → ✓/✗
  └─ 4. 全部失败 → 记录错误，跳过，继续下一个序列
```

**设计原则：**
- **永不阻塞流水线** —— 单个序列失败不中止全局
- **自动切换，无需人工干预** —— fallback 逻辑在循环内，透明执行
- **记录来源** —— `update_method = 'wind_mcp_fallback'` 让下游知道数据走了降级
- **跨引用配置文件** —— `edb_mapping.json`（59 项）和 `wind_mapping.json`（36 项）取交集找到 27 个共享序列

**代码模式（可复用）：**

```python
def _try_wind_fallback(series_id, wind_mappings):
    """通用 fallback 模式：查映射 → 分发方法 → 转换格式"""
    wind_cfg = wind_mappings.get(series_id)
    if not wind_cfg:
        return None
    
    if wind_cfg["method"] == "kline":
        raw = _fetch_wind_kline(wind_cfg)
    else:
        raw = _fetch_wind_economic(wind_cfg)
    
    # 关键：转换 Wind 格式为 EDB 兼容格式
    return {"points": convert(raw), "source": "wind_fallback"}
```

---

### 1.4 幂等复算层

**问题：** 外汇衍生序列（汇率拆解、套保成本、年化）由原始序列计算得出。如果公式变了，需要重算全部历史。

**方案：** `recompute_fx_derived.py` 从原始数据重新计算全部衍生序列，输出与 DB 比对后只 INSERT 新行。

```
原始数据 (Wind)
  ├── fx:usdcny-spot
  ├── fx:usdcny-fixing  
  ├── fx:cnh-usd-1y-df
  └── fx:usdcny-swap-1y
       │
       ▼ recompute_fx_derived.py (幂等)
衍生产出
  ├── fx:usdcny-decomp-overnight   (夜盘调整)
  ├── fx:usdcny-decomp-day         (日盘变动)
  ├── fx:cnh-hedge-1y              (套保成本)
  └── fx:cnh-hedge-1y-annualized   (年化)
```

**关键设计：** 重复运行 0 new observations——通过 UNIQUE 约束天然保证幂等。

---

## 二、HTML 看板自包含技术

### 2.1 内联数据嵌入

看板生成器 (`generate_interactive_dashboard.py`) 读取 SQLite → 构建 JSON payload → 替换模板中的 `__DATA__` 占位符：

```python
payload = build_payload(db_path)
html = HTML_TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
```

**注意：** `ensure_ascii=False` 保留中文；`separators=(",", ":")` 减小体积但非必须。

### 2.2 Blob URL 嵌入外部 HTML（关键创新）

**问题：** 看世界模块原本用 `<iframe src="global-news-report.html">` 加载外部文件，分享看板时对方没有这个文件。

**方案：** 生成时将新闻报告 HTML 内联为 `<script type="text/html">`，运行时转为 Blob URL 赋给 iframe。

```html
<!-- 1. 生成时注入（Python 侧） -->
<script type="text/html" id="world-html-content"><!-- 完整的新闻报告 HTML --></script>
<iframe id="world-iframe"></iframe>

<script>
// 2. 运行时创建 Blob URL（JS 侧）
var content = document.getElementById("world-html-content").textContent;
var blob = new Blob([content], { type: "text/html;charset=utf-8" });
document.getElementById("world-iframe").src = URL.createObjectURL(blob);
</script>
```

**为什么用 `<script type="text/html">` 而不是直接放 JSON 里：**
- JSON 需要转义所有 `<` `>` `&` `"` —— HTML 内容巨大时容易出错
- `<script type="text/html">` 浏览器不会执行也不会渲染，天然适合存 HTML 字符串
- Blob URL 创建的 iframe 有完整的 CSS 隔离——新闻报告的样式不会污染看板

**Blob URL vs Data URI：**
- Blob URL (`blob:...`)——浏览器原生支持，无长度限制，推荐
- Data URI (`data:text/html;base64,...`)——URL 长度有限制（部分浏览器 ~2MB），且 iframe 导航可能受限

---

### 2.3 手绘 SVG 图表（零依赖）

看板的走势、柱状、分类、期限结构等图表全部用裸 SVG 手绘——不依赖 Chart.js / ECharts。

**为什么：**
- 真正的零外部依赖
- 精确控制渲染（标签位置、颜色、格式）
- 导出图片时质量完美（SVG 原生矢量）

**代价：**
- 代码量大（renderSvgLine / renderBarChart / renderTermStructure 各 ~80-200 行）
- 交互弱（没有 tooltip 悬浮，只能用 CSS :hover 模拟）
- 可访问性差

**推荐阈值：** 如果需要 >3 种图表类型或有复杂交互需求，选 Chart.js + chartjs-plugin-datalabels。如果追求极致独立性和导出质量，用手绘 SVG。

### 2.4 图表导出按钮

两个按钮，hover 显示：

```
📷 导出图片  ← SVG → Canvas → PNG 下载 + 剪贴板
📥 下载数据  ← 存储在图容器上的 _chartData → XML Spreadsheet → .xls 下载
```

**PNG 导出关键步骤：**
1. 克隆 SVG → 内联 CSS（`getComputedStyle` → `style` 属性）
2. `XMLSerializer` 序列化为字符串
3. 创建 `new Blob([svgString], {type: "image/svg+xml"})`
4. 画到 `new Image()` → `<canvas>`（2x 分辨率）
5. `canvas.toBlob()` 下载

**数据导出关键步骤：**
1. 图表渲染时将数据存在容器上：`container._chartData = {...}`
2. 构建 Excel XML Spreadsheet 2003 格式（单 XML 文件，`.xls` 扩展名）
3. Excel / WPS / Numbers 都能直接打开

---

### 2.5 返回主页按钮

每个模块页 `.panel-head` 右上角自动注入 `← 主页` 按钮。

**用 JS 注入而非每个 HTML 块手写**——因为模块有 11 个，JS 一行搞定：

```javascript
document.querySelectorAll(".view:not(#view-cover)").forEach(view => {
  const panelHead = view.querySelector(".panel-head");
  if (panelHead) {
    const btn = document.createElement("button");
    btn.className = "back-home-btn";
    btn.textContent = "← 主页";
    btn.addEventListener("click", goHome);
    panelHead.appendChild(btn);  // panel-head 有 position: relative
  }
});
```

---

## 三、踩过的坑

### 3.1 Wind MCP CLI 软链接路径陷阱

**症状：** `node ~/.claude/skills/wind-mcp-skill/scripts/cli.mjs call ...` 返回 exit 0 但 stdout 为空。

**原因：** `~/.claude/skills/wind-mcp-skill/` 是 `~/.agents/skills/wind-mcp-skill/` 的软链接。CLI 内部用 `IS_MAIN` guard 检查 `import.meta.url === pathToFileURL(process.argv[1]).href`，但 Node.js 的 `import.meta.url` 解析到真实路径，`process.argv[1]` 用的是用户传入的软链接路径——两者不相等，`IS_MAIN` 判断失败，代码不执行。

**修复：** 始终用真实路径 `~/.agents/skills/wind-mcp-skill/scripts/cli.mjs`。

**教训：** 当 CLI 工具在软链接下行为异常时，先怀疑路径解析问题。`import.meta.url` 和 `process.argv[1]` 在软链接场景下可能不对齐。

### 3.2 Python 3.11- f-string 反斜杠限制

**症状：** `SyntaxError: f-string expression part cannot include a backslash`

```python
# ❌ Python <3.12 不行
f"Count: {len(x.split('\n'))}"

# ✅ 先赋值
lines = x.split('\n')
f"Count: {len(lines)}"
```

**教训：** 写 Python 脚本时假设目标环境是 Python 3.11（macOS 默认），避免 f-string 中有 `\`。

### 3.3 macOS 没有 `timeout` 命令

Linux 的 `timeout 30 command` 在 macOS 上不存在。替代方案：
- `gtimeout`（需 `brew install coreutils`）
- Python 的 `subprocess.run(cmd, timeout=30)`
- Node.js 的 `setTimeout` + `child_process.kill()`

本项目用 Python 做超时控制（`subprocess.run(timeout=...)`），天然跨平台。

### 3.4 EDB API 间歇超时

同花顺 EDB API 部分序列（`cny-bond-1y`, `usd-bond-1y`）间歇性超时，重试无用。

**不重试，直接降级**——EDB 超时 → 立即走 Wind fallback，总体更快且成功率更高。

### 3.5 单文件体积膨胀

25MB 的 HTML 文件在邮件/微信中传输困难。

**缓解措施：**
- GitHub Pages 作为主要分发渠道（链接分享）
- 可考虑压缩历史数据精度（浮点 → 4 位小数）或按年份拆分为分卷

---

## 四、可复用的代码模式

### 4.1 Python 流水线编排模式

```python
# 动态步骤列表 + 失败不中止
steps = [
    ("生成更新计划", ["scripts/update_data.py"]),
    ("拉取 EDB", ["scripts/fetch_data.py"]),
    ("拉取 Wind", ["scripts/fetch_wind.py"]),
    # ...
]

for label, cmd in steps:
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"WARNING: {label} 失败，继续...")
        failures += 1

# 最后汇总
print(f"步骤失败: {failures} 个 (已自动跳过)")
```

### 4.2 双源验证 + 降级模式

```python
# 主源拉取
data = fetch_from_primary(series_id)

# 验证
if data and not validate(data, db_reference):
    # 主源验证失败 → 自动降级
    data = fetch_from_fallback(series_id)
    if data:
        data["source"] = "fallback"

# 全部失败 → 记录但不中止
if not data:
    errors.append(series_id)
```

### 4.3 HTML 占位符替换模式

```python
# Python 生成器
template = Path("templates/template.html").read_text()
html = template.replace("__DATA__", json.dumps(payload))
html = html.replace("__WORLD_HTML__", world_html_content)
output_path.write_text(html)
```

### 4.4 JS View 切换模式

```css
.view { display: none; }
.view.active { display: block; }
```

```javascript
function switchToView(viewName) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById(`view-${viewName}`).classList.add("active");
}
```

比 SPA 路由轻量，适合 10-20 个视图的场景。

---

## 五、项目文件组织建议

```
project/
├── SKILL.md              ← Claude Code skill 定义（告诉 agent 怎么做）
├── CLAUDE.md             ← 本地项目指令（.gitignore，不入库）
├── README.md             ← 人类可读的说明
├── .gitignore
├── requirements.txt      ← 最小化（pandas + openpyxl 就够）
├── config/               ← 数据源映射（JSON）
├── templates/            ← HTML 模板（含 __DATA__ 等占位符）
├── scripts/              ← 所有 Python 脚本
│   ├── lib.py            ← 公共工具（DB 连接、验证、路径）
│   └── run_daily.py      ← 一键入口
├── data/                 ← 运行时产物（.gitignore）
├── output/               ← 最终产物
├── docs/                 ← GitHub Pages（index.html = output 的副本）
└── tests/
```

**关键原则：**
- `config/` 和 `templates/` 是人写的数据，入 git
- `data/` 和 `output/` 是机器产物，不 git
- `SKILL.md` 是 agent 的操作手册，入 git
- `CLAUDE.md` 是本地的 agent 参考，不入 git

---

## 六、如果重新做，哪些会不同

1. **图表库**：手绘 SVG 适合 2-3 种简单图表，但本项目有 5 种图表类型。如果重来会选 Chart.js + chartjs-plugin-datalabels（2 号风格已经验证可行），大幅减少渲染代码量。

2. **数据压缩**：25MB 的 HTML 应该做 payload 压缩——浮点数截断到 4 位小数，或用二进制格式（base64 编码的 protobuf/msgpack）替代 JSON。当前没有做是因为"够用了"，但对重复分享的场景是个痛点。

3. **增量看板**：每次都重建整个 HTML 是个浪费。更好的方案是数据文件（JSON）+ 静态 HTML 模板分离，数据文件可以独立缓存。但这就牺牲了"单文件自包含"的优势——本质上是 trade-off。

4. **测试覆盖**：当前测试只覆盖了 `values_match` 和 `recompute_fx_derived`。fetch_data 的 fallback 逻辑、看板生成的 JSON 结构、HTML 的有效性都应加测试。

5. **类型规范**：`series_id` 用裸字符串而没有枚举/类型定义。当 152 个序列散布在 5 个配置文件里时很容易拼错。应该用 Python `Enum` 或至少一个 `constants.py` 集中管理所有 series_id。

---

## 七、写给 Agent 的操作建议

如果你被要求构建类似的项目（多数据源 → 本地数据库 → 交互式 HTML 看板），按以下顺序做：

1. **先设计数据模型**：`series_id` 命名规范、`observations` 表结构、验证规则
2. **搭最小流水线**：一个硬编码序列 → 拉取 → 写入 DB → 生成最简单的 HTML → 确认能看
3. **加自动降级**：在主拉取循环里加 fallback，不要后加（后面改循环结构成本高）
4. **做 HTML 模板**：先用占位符，确认 JS 渲染管线 OK，再填 CSS 细节
5. **文档化 SKILL.md**：让下一个 agent（或你自己下次）能直接上手
6. **每次执行报告指标**：耗时、API 调用次数、降级次数——这是运维的眼睛

**最重要的原则：自包含优于优雅。** 用户能双击打开一个文件就比需要 `npm install && npm run dev` 好十倍。
