"""
Generate single-file, self-contained HTML dashboard for all 9 modules.
Data embedded as JSON, Chart.js + datalabels plugin inlined.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import get_db, REPORTS_DIR, TEMPLATES_DIR

# Module definitions with chart configurations
MODULES = [
    {
        "id": "fx-fwd", "name": "即远期供求", "sheet": "3.即远期", "prefix": "fx_fwd",
        "charts": [
            {"id": "supply-demand", "title": "外汇市场即远期总供求", "type": "line",
             "series": [
                 {"id": "fx_fwd:supply_demand", "label": "即远期总供求", "color": "blue"},
                 {"id": "fx_fwd:supply_demand_3mma", "label": "3MMA", "color": "orange"},
                 {"id": "fx_fwd:supply_demand_12mma", "label": "12MMA", "color": "green"},
             ]},
            {"id": "spot-deriv-breakdown", "title": "即期 vs 衍生品净结汇（堆叠柱状）", "type": "bar",
             "series": [
                 {"id": "fx_fwd:spot_flow", "label": "即期结售汇差额", "color": "blue"},
                 {"id": "fx_fwd:deriv_flow", "label": "衍生品净签约", "color": "red"},
             ]},
            {"id": "bank-own-fx", "title": "银行自身结售汇", "type": "line",
             "series": [
                 {"id": "fx_fwd:B", "label": "自身结汇", "color": "green"},
                 {"id": "fx_fwd:C", "label": "自身售汇", "color": "red"},
                 {"id": "fx_fwd:D", "label": "差额", "color": "blue"},
             ]},
            {"id": "fwd-signing", "title": "银行代客远期签约", "type": "line",
             "series": [
                 {"id": "fx_fwd:E", "label": "远期结汇签约", "color": "green"},
                 {"id": "fx_fwd:F", "label": "远期售汇签约", "color": "red"},
                 {"id": "fx_fwd:G", "label": "净结汇", "color": "blue"},
             ]},
        ]
    },
    {
        "id": "fx-cspot", "name": "代客即期结构", "sheet": "3.代客即期", "prefix": "fx_cspot",
        "charts": []  # Will auto-discover key series
    },
    {
        "id": "fx-crossborder", "name": "涉外收付", "sheet": "3.涉外收付", "prefix": "fx_crossborder",
        "charts": []
    },
    {
        "id": "trade-goods", "name": "货物贸易", "sheet": "3.货物贸易", "prefix": "trade_goods",
        "charts": []
    },
    {
        "id": "trade-merchant", "name": "贸易商意愿", "sheet": "3.贸易商", "prefix": "trade_merchant",
        "charts": []
    },
    {
        "id": "trade-services", "name": "服务贸易", "sheet": "3.服务贸易", "prefix": "trade_services",
        "charts": []
    },
    {
        "id": "fdi", "name": "FDI", "sheet": "3.FDI", "prefix": "fdi",
        "charts": []
    },
    {
        "id": "sec-eq", "name": "证券资金流：EQ", "sheet": "3.证券EQ", "prefix": "sec_eq",
        "charts": []
    },
    {
        "id": "sec-fi", "name": "证券资金流：FI", "sheet": "3.证券FI", "prefix": "sec_fi",
        "charts": []
    },
]

COLORS_JS = {
    "blue": "rgba(54, 162, 235, 1)",
    "blue_bg": "rgba(54, 162, 235, 0.2)",
    "red": "rgba(255, 99, 132, 1)",
    "red_bg": "rgba(255, 99, 132, 0.2)",
    "green": "rgba(75, 192, 192, 1)",
    "green_bg": "rgba(75, 192, 192, 0.2)",
    "orange": "rgba(255, 159, 64, 1)",
    "orange_bg": "rgba(255, 159, 64, 0.2)",
    "purple": "rgba(153, 102, 255, 1)",
    "purple_bg": "rgba(153, 102, 255, 0.2)",
    "gray": "rgba(100, 100, 100, 1)",
}


def build_payload(conn):
    """Build data payload from SQLite."""
    payload = {"generated_at": datetime.now().isoformat(), "data_through": {}, "modules": {}}

    for mod in MODULES:
        series_rows = conn.execute(
            "SELECT series_id, display_name, series_type, frequency, unit, first_date, last_date "
            "FROM series WHERE module=? ORDER BY series_id", (mod["sheet"],)
        ).fetchall()

        if not series_rows:
            payload["modules"][mod["id"]] = {"series": [], "observations": {}}
            continue

        series_ids = [r["series_id"] for r in series_rows]
        placeholders = ",".join("?" for _ in series_ids)
        obs_rows = conn.execute(
            f"SELECT series_id, date, value FROM observations WHERE series_id IN ({placeholders}) ORDER BY series_id, date ASC",
            series_ids
        ).fetchall()

        obs_dict = {}
        for row in obs_rows:
            sid = row["series_id"]
            if sid not in obs_dict:
                obs_dict[sid] = []
            obs_dict[sid].append([row["date"], row["value"]])

        latest = None
        for s in series_rows:
            if s["last_date"] and (latest is None or s["last_date"] > latest):
                latest = s["last_date"]

        payload["data_through"][mod["id"]] = latest
        payload["modules"][mod["id"]] = {
            "series": [
                {"id": r["series_id"], "name": r["display_name"][:120], "type": r["series_type"],
                 "freq": r["frequency"], "unit": r["unit"], "first": r["first_date"], "last": r["last_date"]}
                for r in series_rows
            ],
            "observations": obs_dict,
        }

    return payload


def generate_html(payload, output_path):
    """Generate complete HTML with inlined Chart.js + data."""
    chart_js = (TEMPLATES_DIR / "chart.min.js").read_text()
    datalabels_js = (TEMPLATES_DIR / "datalabels.min.js").read_text()

    # Build chart configs as JS
    charts_js_parts = []
    for mod in MODULES:
        mid = mod["id"]
        mod_data = payload["modules"].get(mid, {})
        obs = mod_data.get("observations", {})
        series_list = mod_data.get("series", [])

        if mod.get("charts"):
            # Use predefined charts
            chart_configs = []
            for ch in mod["charts"]:
                # Check data availability
                available = []
                for s in ch["series"]:
                    if s["id"] in obs and len(obs[s["id"]]) > 0:
                        available.append(s)
                if available:
                    chart_configs.append({"id": ch["id"], "title": ch["title"], "type": ch["type"], "series": available})
            charts_js_parts.append(f'  "{mid}": {json.dumps(chart_configs, ensure_ascii=False)}')
        else:
            # Auto-discover: pick first 4-6 raw series
            raw_sids = [s["id"] for s in series_list if s["type"] == "raw" and s["id"] in obs and len(obs.get(s["id"], [])) > 10]
            auto_charts = []
            color_keys = ["blue", "red", "green", "orange", "purple"]
            for i, sid in enumerate(raw_sids[:6]):
                s_info = next((s for s in series_list if s["id"] == sid), None)
                auto_charts.append({
                    "id": f"auto-{i}",
                    "title": s_info["name"][:60] if s_info else sid,
                    "type": "line",
                    "series": [{"id": sid, "label": s_info["name"][:40] if s_info else sid, "color": color_keys[i % len(color_keys)]}]
                })
            charts_js_parts.append(f'  "{mid}": {json.dumps(auto_charts, ensure_ascii=False)}')

    chart_configs_js = "{\n" + ",\n".join(charts_js_parts) + "\n}"

    # Pre-serialize JS data to avoid f-string brace escaping issues
    modules_js = json.dumps([{"id": m["id"], "name": m["name"], "sheet": m["sheet"], "prefix": m["prefix"]} for m in MODULES], ensure_ascii=False)
    payload_js = json.dumps(payload, ensure_ascii=False)
    colors_js = json.dumps(COLORS_JS)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FX Flow Dashboard — 结售汇与跨境资金流</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f0f2f5; color: #333; }}

/* Header */
.header {{ background: linear-gradient(135deg, #0d1b3e 0%, #1a3365 50%, #264785 100%); color: white; padding: 20px 32px; position: sticky; top: 0; z-index: 100; }}
.header h1 {{ font-size: 22px; font-weight: 600; letter-spacing: 0.5px; }}
.header .meta {{ font-size: 12px; opacity: 0.75; margin-top: 4px; display: flex; gap: 20px; flex-wrap: wrap; }}
.header .meta span {{ white-space: nowrap; }}

/* Controls bar */
.controls-bar {{ background: white; padding: 12px 24px; border-bottom: 1px solid #e0e0e0; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }}
.controls-bar label {{ font-size: 13px; color: #666; font-weight: 500; }}
.controls-bar select {{ padding: 6px 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 13px; background: white; }}
.range-preset {{ padding: 5px 12px; border: 1px solid #ddd; border-radius: 16px; background: white; cursor: pointer; font-size: 12px; transition: all 0.15s; }}
.range-preset:hover {{ background: #e8eaf6; border-color: #3949ab; }}
.range-preset.active {{ background: #3949ab; color: white; border-color: #3949ab; }}

/* Navigation */
.nav {{ display: flex; gap: 2px; padding: 8px 24px; background: white; border-bottom: 2px solid #e0e0e0; overflow-x: auto; }}
.nav-btn {{ padding: 8px 14px; border: none; border-bottom: 2px solid transparent; background: transparent; cursor: pointer; font-size: 13px; white-space: nowrap; color: #666; transition: all 0.2s; margin-bottom: -2px; }}
.nav-btn:hover {{ color: #3949ab; }}
.nav-btn.active {{ color: #3949ab; border-bottom-color: #3949ab; font-weight: 600; }}

/* Module panels */
.module {{ display: none; padding: 24px; }}
.module.active {{ display: block; }}
.module-title {{ font-size: 20px; font-weight: 700; margin-bottom: 8px; color: #0d1b3e; }}
.module-subtitle {{ font-size: 13px; color: #999; margin-bottom: 20px; }}

/* Charts grid */
.charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(460px, 1fr)); gap: 16px; }}
.chart-card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); transition: box-shadow 0.2s; }}
.chart-card:hover {{ box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
.chart-card h3 {{ font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #555; }}
.chart-card .chart-wrap {{ position: relative; height: 300px; }}
.chart-card .chart-wrap canvas {{ width: 100% !important; height: 100% !important; }}
.chart-card .chart-actions {{ display: flex; gap: 8px; margin-top: 8px; justify-content: flex-end; }}
.chart-card .chart-actions button {{ padding: 4px 10px; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; font-size: 11px; color: #888; }}
.chart-card .chart-actions button:hover {{ background: #f5f5f5; color: #333; }}

/* Summary table */
.summary-section {{ margin-top: 24px; }}
.summary-section h3 {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #0d1b3e; }}
.data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
.data-table th, .data-table td {{ padding: 8px 14px; text-align: right; border-bottom: 1px solid #f0f0f0; }}
.data-table th {{ background: #f8f9fa; color: #555; font-weight: 600; font-size: 12px; text-transform: uppercase; }}
.data-table td:first-child, .data-table th:first-child {{ text-align: left; }}
.data-table tr:hover {{ background: #fafbfc; }}

/* Placeholder */
.placeholder {{ padding: 60px 20px; text-align: center; color: #aaa; font-size: 16px; background: white; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
.placeholder .icon {{ font-size: 40px; margin-bottom: 12px; }}

/* Footer */
.footer {{ padding: 16px 32px; text-align: center; color: #999; font-size: 11px; border-top: 1px solid #e0e0e0; margin-top: 40px; }}
</style>
</head>
<body>

<div class="header">
  <h1>结售汇与跨境资金流看板</h1>
  <div class="meta">
    <span>📅 数据截至：<b id="data-through">—</b></span>
    <span>🕐 生成：{payload["generated_at"][:19]}</span>
    <span>📊 数据源：SQLite (Excel 种子)</span>
  </div>
</div>

<div class="controls-bar">
  <label>时间范围：</label>
  <button class="range-preset active" data-range="all">全部</button>
  <button class="range-preset" data-range="5y">5年</button>
  <button class="range-preset" data-range="3y">3年</button>
  <button class="range-preset" data-range="1y">1年</button>
  <button class="range-preset" data-range="ytd">年初至今</button>
  <span style="margin-left:auto;font-size:12px;color:#999">💡 点击图表下方按钮导出图片/数据</span>
</div>

<div class="nav" id="nav"></div>
<div id="modules"></div>
<div class="footer">FX Flow Dashboard · SQLite → Python 复算 → Chart.js 渲染 · 离线可用</div>

<script>
/* ---- Chart.js ---- */
{chart_js}

/* ---- Chart.js Datalabels Plugin ---- */
{datalabels_js}

/* ---- Data ---- */
const DATA = {payload_js};
const MODULES = {modules_js};
const CHART_CONFIGS = {chart_configs_js};
const C = {colors_js};

Chart.register(ChartDataLabels);

// State
let currentRange = 'all';
let chartInstances = {{}};

// Navigation
function buildNav() {{
    const nav = document.getElementById('nav');
    MODULES.forEach((m, i) => {{
        const btn = document.createElement('button');
        btn.className = 'nav-btn' + (i === 0 ? ' active' : '');
        btn.textContent = m.name;
        btn.onclick = () => switchModule(m.id, btn);
        nav.appendChild(btn);
    }});
}}

function buildModules() {{
    const container = document.getElementById('modules');
    MODULES.forEach((m, i) => {{
        const div = document.createElement('div');
        div.className = 'module' + (i === 0 ? ' active' : '');
        div.id = 'module-' + m.id;
        container.appendChild(div);
    }});
}}

function switchModule(id, btn) {{
    document.querySelectorAll('.module').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    const mod = document.getElementById('module-' + id);
    if (mod) mod.classList.add('active');
    if (btn) btn.classList.add('active');
    if (!mod.dataset.rendered) renderModule(id, mod);
    updateDataThrough(id);
}}

function updateDataThrough(id) {{
    const latest = DATA.data_through[id];
    if (latest) document.getElementById('data-through').textContent = latest;
}}

// Range filtering
function getDateRange() {{
    const now = new Date();
    switch(currentRange) {{
        case '5y': return new Date(now.getFullYear() - 5, 0, 1).toISOString().slice(0,10);
        case '3y': return new Date(now.getFullYear() - 3, 0, 1).toISOString().slice(0,10);
        case '1y': return new Date(now.getFullYear() - 1, now.getMonth(), 1).toISOString().slice(0,10);
        case 'ytd': return new Date(now.getFullYear(), 0, 1).toISOString().slice(0,10);
        default: return null;
    }}
}}

function filterData(data, minDate) {{
    if (!minDate || !data) return data;
    return data.filter(p => p[0] >= minDate);
}}

// Chart rendering
function commonOptions(yLabel) {{
    return {{
        responsive: true,
        maintainAspectRatio: false,
        animation: {{ duration: 300 }},
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
            legend: {{ position: 'top', labels: {{ usePointStyle: true, padding: 16, font: {{ size: 12 }} }} }},
            tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString(undefined, {{minimumFractionDigits: 1, maximumFractionDigits: 2}}) }} }},
            datalabels: {{ display: false }},
        }},
        scales: {{
            x: {{ grid: {{ color: 'rgba(0,0,0,0.05)' }}, ticks: {{ maxTicksLimit: 10, maxRotation: 0, font: {{ size: 11 }} }} }},
            y: {{ grid: {{ color: 'rgba(0,0,0,0.05)' }}, title: {{ display: !!yLabel, text: yLabel || '', font: {{ size: 12 }} }} }},
        }},
    }};
}}

function makeDataset(data, label, colorKey, chartType) {{
    const color = C[colorKey] || C.blue;
    const bgColor = C[colorKey + '_bg'] || C.blue_bg;
    const config = {{
        label, data, borderColor: color, backgroundColor: bgColor,
        borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: 0.05,
        type: chartType || 'line', fill: chartType === 'bar' ? false : true,
    }};
    if (chartType === 'bar') {{
        config.backgroundColor = bgColor;
        config.borderColor = color;
    }}
    return config;
}}

function renderModule(id, modEl) {{
    modEl.dataset.rendered = '1';
    const modData = DATA.modules[id];
    const modInfo = MODULES.find(m => m.id === id);

    if (!modData || !modData.series.length) {{
        modEl.innerHTML = '<div class="placeholder"><div class="icon">📭</div><p>数据尚未导入</p><p style="font-size:13px;color:#ccc">模块: ' + (modInfo ? modInfo.name : id) + '</p></div>';
        return;
    }}

    const obs = modData.observations;
    const charts = CHART_CONFIGS[id] || [];

    let html = '<div class="module-title">' + (modInfo ? modInfo.name : id) + '</div>';
    html += '<div class="module-subtitle">' + modData.series.length + ' 个序列 · 数据截至 ' + (DATA.data_through[id] || 'N/A') + '</div>';

    if (charts.length === 0) {{
        html += '<div class="placeholder"><div class="icon">📋</div><p>图表配置待添加</p></div>';
    }} else {{
        html += '<div class="charts-grid">';
        charts.forEach(ch => {{
            const chartId = 'chart-' + id + '-' + ch.id;
            html += '<div class="chart-card">';
            html += '<h3>' + ch.title + '</h3>';
            html += '<div class="chart-wrap"><canvas id="' + chartId + '"></canvas></div>';
            html += '<div class="chart-actions">';
            html += '<button onclick="exportChartImage(\'' + chartId + '\', \'' + ch.title.replace(/'/g, "\\'") + '\')">📷 导出图片</button>';
            html += '<button onclick="exportChartData(\'' + chartId + '\', \'' + ch.title.replace(/'/g, "\\'") + '\')">📥 下载数据</button>';
            html += '</div>';
            html += '</div>';
        }});
        html += '</div>';
    }}

    // Summary table
    const keySeries = modData.series.filter(s => s.type === 'raw' && obs[s.id] && obs[s.id].length > 1).slice(0, 10);
    if (keySeries.length > 0) {{
        html += '<div class="summary-section"><h3>最新数据摘要</h3><table class="data-table"><thead><tr><th>指标</th><th>最新值</th><th>前值</th><th>环比变化</th><th>日期</th></tr></thead><tbody>';
        keySeries.forEach(s => {{
            const data = obs[s.id];
            if (!data || data.length < 2) return;
            const latest = data[data.length - 1];
            const prev = data[data.length - 2];
            const pctChange = prev[1] !== 0 ? ((latest[1] - prev[1]) / Math.abs(prev[1]) * 100) : 0;
            const arrow = pctChange > 0 ? '↑' : pctChange < 0 ? '↓' : '→';
            const color = pctChange > 0 ? '#e74c3c' : pctChange < 0 ? '#27ae60' : '#999';
            html += '<tr><td>' + s.name + '</td><td><b>' + latest[1].toLocaleString(undefined, {{maximumFractionDigits: 2}}) + '</b></td><td>' + prev[1].toLocaleString(undefined, {{maximumFractionDigits: 2}}) + '</td><td style="color:' + color + '">' + arrow + ' ' + Math.abs(pctChange).toFixed(2) + '%</td><td>' + latest[0] + '</td></tr>';
        }});
        html += '</tbody></table></div>';
    }}

    modEl.innerHTML = html;

    // Render charts
    const minDate = getDateRange();
    charts.forEach(ch => {{
        const chartId = 'chart-' + id + '-' + ch.id;
        const canvas = document.getElementById(chartId);
        if (!canvas) return;

        // Build datasets
        const allLabels = new Set();
        const datasets = [];
        ch.series.forEach(s => {{
            const rawData = obs[s.id];
            if (!rawData) return;
            const filtered = filterData(rawData, minDate);
            if (filtered.length === 0) return;
            filtered.forEach(p => allLabels.add(p[0]));
            datasets.push({{
                data: filtered,
                label: s.label,
                color: s.color,
                type: ch.type,
            }});
        }});

        if (datasets.length === 0) return;

        const labels = Array.from(allLabels).sort();

        // Build Chart.js data
        const chartDatasets = datasets.map(ds => {{
            const dataMap = {{}};
            ds.data.forEach(p => {{ dataMap[p[0]] = p[1]; }});
            const values = labels.map(l => dataMap[l] !== undefined ? dataMap[l] : null);
            return makeDataset(values, ds.label, ds.color, ds.type);
        }});

        const ctx = canvas.getContext('2d');
        const inst = new Chart(ctx, {{
            type: ch.type || 'line',
            data: {{ labels, datasets: chartDatasets }},
            options: commonOptions(null),
        }});

        // Store for export
        canvas._chartInstance = inst;
        canvas._chartTitle = ch.title;
        canvas._chartData = {{ labels, datasets: datasets.map(ds => ({{ label: ds.label, data: ds.data }})) }};
    }});
}}

// Export functions
function exportChartImage(chartId, title) {{
    const canvas = document.getElementById(chartId);
    if (!canvas) return;
    canvas.toBlob(blob => {{
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = (title || 'chart') + '.png'; a.click();
        URL.revokeObjectURL(url);
    }}, 'image/png', 2);
}}

function exportChartData(chartId, title) {{
    const canvas = document.getElementById(chartId);
    if (!canvas || !canvas._chartData) return;
    const cd = canvas._chartData;

    // Build CSV
    let csv = '\\uFEFFDate';
    cd.datasets.forEach(ds => csv += ',' + ds.label);
    csv += '\\n';
    cd.labels.forEach((label, i) => {{
        csv += label;
        cd.datasets.forEach(ds => {{
            const point = ds.data.find(p => p[0] === label);
            csv += ',' + (point ? point[1] : '');
        }});
        csv += '\\n';
    }});

    const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = (title || 'data') + '.csv'; a.click();
    URL.revokeObjectURL(url);
}}

// Range presets
document.addEventListener('click', e => {{
    if (e.target.classList.contains('range-preset')) {{
        document.querySelectorAll('.range-preset').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentRange = e.target.dataset.range;
        // Re-render all visible modules
        document.querySelectorAll('.module.active').forEach(mod => {{
            mod.dataset.rendered = '';
            const id = mod.id.replace('module-', '');
            renderModule(id, mod);
        }});
    }}
}});

// Init
document.addEventListener('DOMContentLoaded', () => {{
    buildNav();
    buildModules();
    updateDataThrough(MODULES[0].id);
    const firstMod = document.getElementById('module-' + MODULES[0].id);
    if (firstMod) renderModule(MODULES[0].id, firstMod);
}});
</script>
</body>
</html>'''

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding='utf-8')
    return output_path


def main():
    conn = get_db()

    # Ensure derived series exist
    from recompute_derived import recompute_all, start_update_run, finish_update_run
    run_id = start_update_run(conn, 0)
    print("Recomputing all derived indicators...")
    recompute_all(conn, run_id)
    finish_update_run(conn, run_id, "completed", successful=88, new_obs=0)

    print("\nBuilding data payload...")
    payload = build_payload(conn)

    for mod in MODULES:
        mid = mod["id"]
        mod_data = payload["modules"].get(mid, {})
        n_series = len(mod_data.get("series", []))
        latest = payload["data_through"].get(mid, "N/A")
        print(f"  {mid}: {n_series} series, through {latest}")

    output_path = REPORTS_DIR / "fx_flow_dashboard.html"
    print(f"\nGenerating: {output_path}")
    generate_html(payload, output_path)

    size_kb = output_path.stat().st_size / 1024
    print(f"Done: {output_path} ({size_kb:,.0f} KB)")

    conn.close()


if __name__ == "__main__":
    main()
