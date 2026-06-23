#!/usr/bin/env python3
"""
generate_dashboard.py — Catalog-driven HTML dashboard generator.
Loads chart_catalog.json to drive all chart creation. Single-file, offline.
"""
import sys, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import get_db, REPORTS_DIR, TEMPLATES_DIR, CONFIG_DIR

# ── helpers ──────────────────────────────────────────────────
MODULE_SHEET_MAP = {
    "3.即远期":"fx-fwd","3.代客即期":"fx-cspot","3.涉外收付":"fx-crossborder",
    "3.货物贸易":"trade-goods","3.贸易商":"trade-merchant","3.服务贸易":"trade-services",
    "3.FDI":"fdi","3.证券EQ":"sec-eq","3.证券FI":"sec-fi",
}
MODULE_NAMES = {
    "3.即远期":"即远期供求","3.代客即期":"代客即期结构","3.涉外收付":"涉外收付",
    "3.货物贸易":"货物贸易","3.贸易商":"贸易商意愿","3.服务贸易":"服务贸易",
    "3.FDI":"FDI","3.证券EQ":"证券资金流 EQ","3.证券FI":"证券资金流 FI",
}
MODULE_PREFIX = {
    "3.即远期":"fx_fwd","3.代客即期":"fx_cspot","3.涉外收付":"fx_crossborder",
    "3.货物贸易":"trade_goods","3.贸易商":"trade_merchant","3.服务贸易":"trade_services",
    "3.FDI":"fdi","3.证券EQ":"sec_eq","3.证券FI":"sec_fi",
}

def load_chart_catalog():
    p = CONFIG_DIR / "chart_catalog.json"
    if p.exists():
        with open(p) as f:
            return json.load(f).get("modules", {})
    return {}

def build_modules():
    cat = load_chart_catalog()
    mods = []
    for sheet in ["3.即远期","3.代客即期","3.涉外收付","3.货物贸易",
                  "3.贸易商","3.服务贸易","3.FDI","3.证券EQ","3.证券FI"]:
        md = cat.get(sheet, {})
        charts_out = []
        for ch in md.get("charts", []):
            series_out = []
            for ds in ch.get("datasets", []):
                series_out.append({
                    "id": ds["series_id"], "label": ds["label"],
                    "color": ds.get("color","blue"), "type": ds.get("type","line"),
                    "axis": ds.get("axis","left"),
                })
            charts_out.append({
                "id": ch["chart_id"], "title": ch["title"],
                "subtitle": ch.get("subtitle",""), "type": ch["chart_type"],
                "family": ch.get("family","trend"), "priority": ch.get("priority","primary"),
                "range": ch.get("default_range","5y"), "zero_line": ch.get("zero_line",False),
                "dual_axis": ch.get("dual_axis",False),
                "seasonality_selector": ch.get("seasonality_selector",False),
                "series": series_out, "y_min": ch.get("y_min"), "y_max": ch.get("y_max"),
                "scatter": ch.get("scatter", False),
                "scatter_x": ch.get("scatter_x"), "scatter_y": ch.get("scatter_y"),
                "scatter_x_alt": ch.get("scatter_x_alt"),
            })
        mods.append({
            "id": MODULE_SHEET_MAP.get(sheet,sheet),
            "name": MODULE_NAMES.get(sheet,sheet),
            "sheet": sheet, "prefix": MODULE_PREFIX.get(sheet,""),
            "charts": charts_out,
        })
    return mods

MODULES = build_modules()

# ── color palette ───────────────────────────────────────────
COLORS_JS = """
const C = {
    blue: '#1a3a5c', blue_bg: 'rgba(26,58,92,0.15)',
    red: '#c0392b', red_bg: 'rgba(192,57,43,0.15)',
    green: '#27ae60', green_bg: 'rgba(39,174,96,0.15)',
    orange: '#d4841a', orange_bg: 'rgba(212,132,26,0.15)',
    purple: '#8e44ad', purple_bg: 'rgba(142,68,173,0.15)',
    teal: '#1abc9c', teal_bg: 'rgba(26,188,156,0.15)',
    grey: '#7f8c8d', grey_bg: 'rgba(127,140,141,0.15)',
    dark: '#2c3e50', gold: '#f39c12',
};
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1,3), 16);
    const g = parseInt(hex.slice(3,5), 16);
    const b = parseInt(hex.slice(5,7), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
}
"""

# ── seasonality computation (Loop 10) ────────────────────────
def compute_seasonality(points, history_start_year, history_end_year, current_year):
    """Build 1-12 month seasonality from [[date_str, value], ...].

    Returns list of 12 dicts: {month, min, max, mean, current}.
    History = years in [history_start_year, history_end_year] (excl current).
    current = the value for current_year in that month, or None if unpublished.
    """
    from collections import defaultdict
    by_month_hist = defaultdict(list)
    current = {}
    for d, v in points:
        if v is None:
            continue
        try:
            y = int(d[:4]); m = int(d[5:7])
        except (ValueError, IndexError):
            continue
        if y == current_year:
            current[m] = v
        elif history_start_year <= y <= history_end_year:
            by_month_hist[m].append(v)

    out = []
    for month in range(1, 13):
        hist = by_month_hist.get(month, [])
        out.append({
            "month": month,
            "min": min(hist) if hist else None,
            "max": max(hist) if hist else None,
            "mean": (sum(hist) / len(hist)) if hist else None,
            "current": current.get(month),
        })
    return out


# ── generate ────────────────────────────────────────────────
def generate_html(output_path):
    chart_js = (TEMPLATES_DIR / "chart.min.js").read_text()
    datalabels_js = (TEMPLATES_DIR / "datalabels.min.js").read_text()

    conn = get_db()
    conn.row_factory = None
    cur = conn.execute

    payload = {"modules": {}, "data_through": {}}
    for mod in MODULES:
        mid = mod["id"]
        prefix = mod["prefix"]
        # Series list
        rows = cur("SELECT series_id,display_name,series_type,unit FROM series WHERE module=? ORDER BY series_id",
                   (mod["sheet"],)).fetchall()
        series_list = [{"id": r[0], "name": r[1] or r[0], "type": r[2], "unit": r[3] or ""} for r in rows]
        # Observations
        obs = {}
        data_through = ""
        for r in rows:
            sid = r[0]
            pts = cur("SELECT date,value FROM observations WHERE series_id=? AND value IS NOT NULL AND value!=0 ORDER BY date",
                      (sid,)).fetchall()
            obs[sid] = [[p[0], p[1]] for p in pts]
            if pts:
                data_through = max(data_through, pts[-1][0]) if data_through else pts[-1][0]
        payload["modules"][mid] = {"series": series_list, "observations": obs}
        payload["data_through"][mid] = data_through

    conn.close()

    # Serialize for JS embedding
    mods_js = json.dumps([{"id":m["id"],"name":m["name"],"sheet":m["sheet"],"prefix":m["prefix"]} for m in MODULES], ensure_ascii=False)
    payload_js = json.dumps(payload, ensure_ascii=False)
    chart_configs = {}
    for mod in MODULES:
        chart_configs[mod["id"]] = mod["charts"]
    chart_configs_js = json.dumps(chart_configs, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>FX Flow Dashboard — 结售汇与跨境资金流</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#333}}
.nav{{display:flex;gap:2px;padding:8px 24px;background:white;border-bottom:2px solid #e0e0e0;overflow-x:auto;position:sticky;top:0;z-index:100}}
.nav-btn{{padding:6px 14px;border:1px solid #ddd;border-radius:4px;background:white;cursor:pointer;font-size:12px;white-space:nowrap;transition:all .2s}}
.nav-btn:hover{{background:#1a3a5c;color:white;border-color:#1a3a5c}}
.nav-btn.active{{background:#1a3a5c;color:white;border-color:#1a3a5c}}
.module{{display:none;padding:20px 24px}}
.module.active{{display:block}}
.module-title{{font-size:20px;font-weight:700;color:#1a3a5c;margin-bottom:4px}}
.module-subtitle{{font-size:12px;color:#999;margin-bottom:16px}}
.charts-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:16px}}
.chart-card{{background:white;border-radius:8px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
.chart-card h3{{font-size:13px;color:#666;margin-bottom:2px}}
.chart-card .chart-subtitle{{font-size:11px;color:#bbb;margin-bottom:8px}}
.chart-wrap{{position:relative;height:300px}}
.chart-wrap canvas{{width:100%!important;height:100%!important}}
.chart-actions{{display:flex;gap:8px;margin-top:8px}}
.chart-actions button{{padding:4px 10px;border:1px solid #ddd;border-radius:4px;background:white;cursor:pointer;font-size:11px;color:#666}}
.chart-actions button:hover{{background:#f5f5f5}}
.season-selector{{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0 4px}}
.season-sel-btn{{padding:3px 9px;border:1px solid #ddd;border-radius:12px;background:white;cursor:pointer;font-size:11px;color:#666;white-space:nowrap}}
.season-sel-btn:hover{{background:#eef}}
.season-sel-btn.active{{background:#1a3a5c;color:white;border-color:#1a3a5c}}
.placeholder{{text-align:center;padding:40px;color:#bbb}}
.placeholder .icon{{font-size:40px;margin-bottom:8px}}
.range-bar{{display:flex;gap:4px;padding:0 24px 12px}}
.range-preset{{padding:4px 12px;border:1px solid #ddd;border-radius:4px;background:white;cursor:pointer;font-size:11px;color:#666}}
.range-preset:hover,.range-preset.active{{background:#1a3a5c;color:white;border-color:#1a3a5c}}
.summary-section{{margin-top:20px;background:white;border-radius:8px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
.summary-section h3{{font-size:13px;color:#666;margin-bottom:8px}}
.data-table{{width:100%;border-collapse:collapse;font-size:12px}}
.data-table th,.data-table td{{padding:6px 10px;border-bottom:1px solid #f0f0f0;text-align:left}}
.data-table th{{font-weight:600;color:#999;font-size:11px}}
.data-table td b{{color:#1a3a5c}}
@@media(max-width:768px){{.charts-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="nav" id="nav-bar"></div>
<div class="range-bar">
    <span style="font-size:11px;color:#999;line-height:24px;margin-right:4px">时间范围:</span>
    <button class="range-preset active" data-range="all">全部</button>
    <button class="range-preset" data-range="5y">5年</button>
    <button class="range-preset" data-range="3y">3年</button>
    <button class="range-preset" data-range="1y">1年</button>
    <button class="range-preset" data-range="ytd">YTD</button>
    <span style="margin-left:auto;font-size:12px;color:#999">点击图表下方按钮导出图片/数据</span>
</div>
<div id="modules-container"></div>

<script>{chart_js}</script>
<script>{datalabels_js}</script>
<script>
const DATA = {payload_js};
const MODULES = {mods_js};
const CHART_CONFIGS = {chart_configs_js};
let currentRange = 'all';
{COLORS_JS}

// ── range filter ──────────────────────────────────────
function filterByRange(dates) {{
    if (currentRange === 'all' || !dates.length) return dates;
    const last = dates[dates.length-1][0];
    const lastDt = new Date(last);
    let cutoff;
    if (currentRange === '5y') {{ cutoff = new Date(lastDt); cutoff.setFullYear(cutoff.getFullYear()-5); }}
    else if (currentRange === '3y') {{ cutoff = new Date(lastDt); cutoff.setFullYear(cutoff.getFullYear()-3); }}
    else if (currentRange === '1y') {{ cutoff = new Date(lastDt); cutoff.setFullYear(cutoff.getFullYear()-1); }}
    else if (currentRange === 'ytd') {{ cutoff = new Date(lastDt.getFullYear(), 0, 1); }}
    else return dates;
    const cs = cutoff.toISOString().slice(0,10);
    return dates.filter(d => d[0] >= cs);
}}

// ── chart builder ─────────────────────────────────────
function computeOLS(points) {{
    // points: [{{x, y}}]; returns {{slope, intercept, r, n}}
    const n = points.length;
    if (n < 2) return null;
    let sx=0, sy=0, sxy=0, sxx=0, syy=0;
    points.forEach(p => {{ sx+=p.x; sy+=p.y; sxy+=p.x*p.y; sxx+=p.x*p.x; syy+=p.y*p.y; }});
    const denom = (n*sxx - sx*sx);
    if (denom === 0) return null;
    const slope = (n*sxy - sx*sy) / denom;
    const intercept = (sy - slope*sx) / n;
    const rDenom = Math.sqrt((n*sxx - sx*sx) * (n*syy - sy*sy));
    const r = rDenom === 0 ? 0 : (n*sxy - sx*sy) / rDenom;
    return {{ slope, intercept, r, n }};
}}

function buildScatterConfig(ch, obs) {{
    // Pair x and y series by date
    const xs = obs[ch.scatter_x.series_id] || [];
    const ys = obs[ch.scatter_y.series_id] || [];
    const xMap = {{}}; xs.forEach(p => xMap[p[0]] = p[1]);
    const yMap = {{}}; ys.forEach(p => yMap[p[0]] = p[1]);
    let points = [];
    Object.keys(xMap).forEach(d => {{
        if (d in yMap) points.push({{ x: xMap[d], y: yMap[d], date: d }});
    }});
    // Apply range filter by date
    if (currentRange !== 'all' && points.length) {{
        const sorted = points.map(p => [p.date, 0]).sort();
        const allowed = new Set(filterByRange(sorted).map(p => p[0]));
        points = points.filter(p => allowed.has(p.date));
    }}
    if (points.length < 3) return null;

    const ols = computeOLS(points);
    // Build regression line endpoints
    const xVals = points.map(p => p.x);
    const xMin = Math.min(...xVals), xMax = Math.max(...xVals);
    const regLine = ols ? [
        {{ x: xMin, y: ols.slope*xMin + ols.intercept }},
        {{ x: xMax, y: ols.slope*xMax + ols.intercept }},
    ] : [];

    const subtitle = ols ?
        ('n=' + ols.n + ' · r=' + ols.r.toFixed(3) + ' · R²=' + (ols.r*ols.r).toFixed(3) +
         ' · y=' + ols.slope.toFixed(2) + 'x+' + ols.intercept.toFixed(1)) : '';

    return {{
        config: {{
            type: 'scatter',
            data: {{
                datasets: [
                    {{ label: '观测点', data: points, backgroundColor: hexToRgba('#1a3a5c', 0.45),
                       pointRadius: 3, pointHoverRadius: 5, type: 'scatter' }},
                    {{ label: 'OLS回归线', data: regLine, type: 'line', borderColor: '#c0392b',
                       borderWidth: 2, pointRadius: 0, fill: false }},
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                animation: {{ duration: 300 }},
                plugins: {{
                    legend: {{ position: 'top', labels: {{ usePointStyle: true, padding: 12, font: {{ size: 11 }} }} }},
                    tooltip: {{ callbacks: {{ label: ctx => '(' + ctx.parsed.x.toFixed(2) + ', ' + ctx.parsed.y.toFixed(1) + ')' }} }},
                    datalabels: {{ display: false }},
                }},
                scales: {{
                    x: {{ type: 'linear', title: {{ display: true, text: ch.scatter_x.label, font: {{ size: 11 }} }},
                          grid: {{ color: 'rgba(0,0,0,0.05)' }} }},
                    y: {{ title: {{ display: true, text: ch.scatter_y.label, font: {{ size: 11 }} }},
                          grid: {{ color: 'rgba(0,0,0,0.05)' }} }},
                }},
            }},
        }},
        subtitle: subtitle,
    }};
}}

function buildSeasonalityConfig(ch, obs, selectorIdx) {{
    // selectorIdx: which dataset in ch.series to show (default 0)
    const sIdx = (selectorIdx === undefined) ? 0 : selectorIdx;
    const s = ch.series[sIdx];
    if (!s) return null;
    const data = obs[s.id] || [];
    if (!data.length) return null;

    // Determine current year = max year in data
    let maxYear = 0;
    data.forEach(p => {{ const y = parseInt(p[0].slice(0,4)); if (y > maxYear) maxYear = y; }});
    if (!maxYear) return null;
    const histStart = 2010;  // history range

    // Group by month: history (excl current year) + current year
    const hist = Array.from({{length:12}}, () => []);
    const cur = Array(12).fill(null);
    data.forEach(p => {{
        if (p[1] === null || p[1] === undefined || p[1] === 0) return;
        const y = parseInt(p[0].slice(0,4));
        const m = parseInt(p[0].slice(5,7));
        if (m < 1 || m > 12) return;
        if (y === maxYear) cur[m-1] = p[1];
        else if (y >= histStart && y < maxYear) hist[m-1].push(p[1]);
    }});

    const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
    const minData = hist.map(h => h.length ? Math.min(...h) : null);
    const maxData = hist.map(h => h.length ? Math.max(...h) : null);
    const meanData = hist.map(h => h.length ? h.reduce((a,b)=>a+b,0)/h.length : null);
    // band = [min, max] for fillBetween via two datasets
    const config = {{
        type: 'line',
        data: {{
            labels: months,
            datasets: [
                {{ label: '历史上限', data: maxData, borderColor: 'rgba(127,140,141,0.3)',
                   backgroundColor: 'rgba(127,140,141,0.12)', borderWidth: 1, fill: false,
                   pointRadius: 0, tension: 0.3, order: 3 }},
                {{ label: '历史下限', data: minData, borderColor: 'rgba(127,140,141,0.3)',
                   backgroundColor: 'rgba(127,140,141,0.12)', borderWidth: 1,
                   fill: '-1',  // fill to previous dataset (upper) -> band
                   pointRadius: 0, tension: 0.3, order: 3 }},
                {{ label: '历史均值', data: meanData, borderColor: '#7f8c8d',
                   borderWidth: 1.5, borderDash: [4,3], fill: false,
                   pointRadius: 0, tension: 0.3, order: 2 }},
                {{ label: s.label + ' 当年(' + maxYear + ')', data: cur,
                   borderColor: s.color || '#1a3a5c', backgroundColor: hexToRgba(s.color||'#1a3a5c', 0.1),
                   borderWidth: 2.5, fill: false, pointRadius: 3, pointHoverRadius: 5,
                   tension: 0.2, order: 1 }},
            ]
        }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            animation: {{ duration: 300 }},
            interaction: {{ mode: 'index', intersect: false }},
            plugins: {{
                legend: {{ position: 'top', labels: {{ usePointStyle: true, padding: 10, font: {{ size: 11 }} }} }},
                tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' +
                    (ctx.parsed.y==null ? '未发布' : ctx.parsed.y.toLocaleString(undefined, {{maximumFractionDigits:2}})) }} }},
                datalabels: {{ display: false }},
            }},
            scales: {{
                x: {{ type: 'category', grid: {{ color: 'rgba(0,0,0,0.05)' }},
                      ticks: {{ font: {{ size: 11 }} }} }},
                y: {{ grid: {{ color: 'rgba(0,0,0,0.05)' }} }},
            }},
        }},
    }};
    return config;
}}

function buildChartConfig(ch, obs) {{
    const datasets = [];
    let hasRightAxis = false;

    // Build a unified sorted label axis from all series in this chart
    const labelSet = new Set();
    ch.series.forEach(s => {{
        const data = obs[s.id];
        if (!data) return;
        filterByRange(data).forEach(p => labelSet.add(p[0]));
    }});
    const labels = Array.from(labelSet).sort();
    if (!labels.length) return null;
    const labelIdx = {{}}; labels.forEach((l, i) => labelIdx[l] = i);

    ch.series.forEach(s => {{
        const data = obs[s.id];
        if (!data || !data.length) return;
        const filtered = filterByRange(data);
        if (!filtered.length) return;
        const valMap = {{}}; filtered.forEach(p => valMap[p[0]] = p[1]);
        // Align to label axis (null for missing — no future placeholder zeros)
        const aligned = labels.map(l => l in valMap ? valMap[l] : null);

        const color = s.color || '#1a3a5c';
        const ds = {{
            label: s.label, data: aligned,
            borderColor: color, backgroundColor: s.type === 'bar' ? hexToRgba(color, 0.6) : hexToRgba(color, 0.1),
            borderWidth: s.type === 'bar' ? 0 : 2, pointRadius: 0, pointHoverRadius: 4,
            tension: 0.05, fill: false, spanGaps: true,
        }};

        if (s.type === 'bar') {{
            ds.type = 'bar';
            if (s.stack) ds.stack = s.stack;
            ds.order = 1;
        }} else {{
            ds.type = 'line';
            ds.order = 0;
        }}

        if (s.axis === 'right') {{ ds.yAxisID = 'y1'; hasRightAxis = true; }}
        datasets.push(ds);
    }});

    if (!datasets.length) return null;

    const config = {{
        type: 'bar', data: {{ labels, datasets }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            animation: {{ duration: 300 }},
            interaction: {{ mode: 'index', intersect: false }},
            plugins: {{
                legend: {{ position: 'top', labels: {{ usePointStyle: true, padding: 12, font: {{ size: 11 }} }} }},
                tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + (ctx.parsed.y==null?'—':ctx.parsed.y.toLocaleString(undefined, {{maximumFractionDigits: 2}})) }} }},
                datalabels: {{ display: false }},
            }},
            scales: {{
                x: {{ type: 'category',
                      grid: {{ color: 'rgba(0,0,0,0.05)' }},
                      ticks: {{ maxTicksLimit: 10, maxRotation: 0, autoSkip: true, font: {{ size: 10 }},
                                callback: function(val, i) {{ const l = this.getLabelForValue(val); return l ? l.slice(0,7) : l; }} }} }},
                y: {{ grid: {{ color: 'rgba(0,0,0,0.05)' }},
                      title: {{ display: true, text: '亿美元', font: {{ size: 11 }} }} }},
            }},
        }},
    }};

    if (ch.zero_line) {{
        config.options.scales.y.beginAtZero = false;
        config.options.scales.y.grid.color = (ctx) => ctx.tick.value === 0 ? 'rgba(0,0,0,0.4)' : 'rgba(0,0,0,0.05)';
    }}

    if (hasRightAxis) {{
        config.options.scales.y1 = {{
            position: 'right', grid: {{ drawOnChartArea: false }},
            title: {{ display: true, text: '右轴', font: {{ size: 11 }} }},
        }};
    }}

    if (ch.y_min !== undefined && ch.y_min !== null) config.options.scales.y.min = ch.y_min;
    if (ch.y_max !== undefined && ch.y_max !== null) config.options.scales.y.max = ch.y_max;

    return config;
}}

// ── render ────────────────────────────────────────────
function renderModule(id, modEl) {{
    modEl.dataset.rendered = '1';
    const modData = DATA.modules[id];
    const modInfo = MODULES.find(m => m.id === id);
    if (!modData || !modData.series.length) {{
        modEl.innerHTML = '<div class="placeholder"><div class="icon">📭</div><p>数据尚未导入</p></div>';
        return;
    }}

    const obs = modData.observations;
    const charts = CHART_CONFIGS[id] || [];

    let html = '<div class="module-title">' + (modInfo ? modInfo.name : id) + '</div>';
    html += '<div class="module-subtitle">' + modData.series.length + ' 序列 · 数据截至 ' + (DATA.data_through[id] || 'N/A') + '</div>';

    if (!charts.length) {{
        html += '<div class="placeholder"><div class="icon">📋</div><p>图表配置待添加</p><p style="font-size:12px;color:#ddd">编辑 config/chart_catalog.json 添加图表定义</p></div>';
    }} else {{
        html += '<div class="charts-grid">';
        charts.forEach(ch => {{
            const cid = 'chart-' + id + '-' + ch.id;
            html += '<div class="chart-card">';
            html += '<h3>' + ch.title + '</h3>';
            if (ch.subtitle) html += '<div class="chart-subtitle">' + ch.subtitle + '</div>';
            // Seasonality selector (switch indicator)
            if (ch.type === 'seasonality_band' && ch.series.length > 1) {{
                html += '<div class="season-selector" data-chart-cid="' + cid + '">';
                ch.series.forEach((s, i) => {{
                    html += '<button class="season-sel-btn' + (i===0 ? ' active' : '') + '" data-chart-cid="' + cid + '" data-idx="' + i + '">' + s.label + '</button>';
                }});
                html += '</div>';
            }}
            html += '<div class="chart-wrap"><canvas id="' + cid + '"></canvas></div>';
            html += '<div class="chart-actions">';
            html += '<button data-export="png" data-chart-id="' + cid + '" data-chart-title="' + ch.title.replace(/"/g, '&quot;') + '">📷 导出图片</button>';
            html += '<button data-export="csv" data-chart-id="' + cid + '" data-chart-title="' + ch.title.replace(/"/g, '&quot;') + '">📥 下载数据</button>';
            html += '</div></div>';
        }});
        html += '</div>';
    }}

    // Summary table — top 8 raw series
    const keySeries = modData.series.filter(s => s.type === 'raw' && obs[s.id] && obs[s.id].length > 1).slice(0, 10);
    if (keySeries.length) {{
        html += '<div class="summary-section"><h3>核心指标摘要</h3><table class="data-table"><thead><tr><th>指标</th><th>最新值</th><th>前值</th><th>变化</th><th>日期</th></tr></thead><tbody>';
        keySeries.forEach(s => {{
            const d = obs[s.id]; if (!d || d.length < 2) return;
            const latest = d[d.length-1], prev = d[d.length-2];
            const chg = prev[1] !== 0 ? ((latest[1]-prev[1])/Math.abs(prev[1])*100) : 0;
            const arrow = chg > 0 ? '↑' : chg < 0 ? '↓' : '→';
            html += '<tr><td>' + s.name + '</td><td><b>' + latest[1].toLocaleString(undefined, {{maximumFractionDigits:1}}) + '</b></td><td>' + prev[1].toLocaleString(undefined, {{maximumFractionDigits:1}}) + '</td><td style="color:' + (chg>0?'#e74c3c':chg<0?'#27ae60':'#999') + '">' + arrow + ' ' + Math.abs(chg).toFixed(1) + '%</td><td>' + latest[0] + '</td></tr>';
        }});
        html += '</tbody></table></div>';
    }}

    modEl.innerHTML = html;

    // Render charts AFTER DOM is set
    setTimeout(() => {{
        charts.forEach(ch => {{
            const cid = 'chart-' + id + '-' + ch.id;
            const canvas = document.getElementById(cid);
            if (!canvas) return;
            let config, subtitleOverride = null;
            if (ch.scatter) {{
                const sc = buildScatterConfig(ch, obs);
                if (!sc) return;
                config = sc.config;
                subtitleOverride = sc.subtitle;
            }} else if (ch.type === 'seasonality_band') {{
                config = buildSeasonalityConfig(ch, obs, 0);
                if (!config) return;
                canvas._seasonalityChart = ch;  // for selector switching
            }} else {{
                config = buildChartConfig(ch, obs);
            }}
            if (!config) return;
            const inst = new Chart(canvas, config);
            canvas._chartInstance = inst;
            canvas._chartTitle = ch.title;
            if (ch.scatter) {{
                canvas._chartData = {{ scatter: true, datasets: config.data.datasets.map(ds => ({{ label: ds.label, data: ds.data.map(p => [p.x, p.y]) }})) }};
            }} else {{
                canvas._chartData = {{ labels: config.data.labels, datasets: config.data.datasets.map(ds => ({{ label: ds.label, data: ds.data }})) }};
            }}
            if (subtitleOverride) {{
                const card = canvas.closest('.chart-card');
                if (card) {{
                    let sub = card.querySelector('.chart-subtitle');
                    if (!sub) {{ sub = document.createElement('div'); sub.className = 'chart-subtitle'; card.querySelector('h3').after(sub); }}
                    sub.textContent = subtitleOverride;
                }}
            }}
        }});
    }}, 0);
}}

// ── export ────────────────────────────────────────────
function exportChartImage(chartId, title) {{
    const canvas = document.getElementById(chartId);
    if (!canvas) return;
    canvas.toBlob(blob => {{
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = (title||'chart') + '.png'; a.click();
        URL.revokeObjectURL(url);
    }}, 'image/png', 2);
}}

function exportChartData(chartId, title) {{
    const canvas = document.getElementById(chartId);
    if (!canvas || !canvas._chartData) return;
    const cd = canvas._chartData;
    let csv;
    if (cd.scatter) {{
        // scatter: x,y pairs per dataset
        csv = '\\uFEFF';
        cd.datasets.forEach(ds => {{
            csv += ds.label + '_x,' + ds.label + '_y\\n';
            ds.data.forEach(p => {{ csv += p[0] + ',' + p[1] + '\\n'; }});
            csv += '\\n';
        }});
    }} else {{
        // category: shared labels axis, aligned arrays
        const labels = cd.labels || [];
        csv = '\\uFEFFDate';
        cd.datasets.forEach(ds => csv += ',' + ds.label);
        csv += '\\n';
        labels.forEach((label, i) => {{
            csv += label;
            cd.datasets.forEach(ds => {{
                const v = ds.data[i];
                csv += ',' + (v == null ? '' : v);
            }});
            csv += '\\n';
        }});
    }}
    const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = (title||'data') + '.csv'; a.click();
    URL.revokeObjectURL(url);
}}

// ── nav & events ──────────────────────────────────────
function switchModule(id, btn) {{
    document.querySelectorAll('.module').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    const mod = document.getElementById('module-' + id);
    if (mod) mod.classList.add('active');
    if (btn) btn.classList.add('active');
    if (mod && !mod.dataset.rendered) renderModule(id, mod);
}}

// Export delegated handler
document.addEventListener('click', e => {{
    const btn = e.target.closest('[data-export]');
    if (!btn) {{}}
    else {{
        const et = btn.dataset.export, cid = btn.dataset.chartId, t = btn.dataset.chartTitle || 'chart';
        if (et === 'png') exportChartImage(cid, t);
        else if (et === 'csv') exportChartData(cid, t);
    }}
}});

// Range presets
document.addEventListener('click', e => {{
    if (e.target.classList.contains('range-preset')) {{
        document.querySelectorAll('.range-preset').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentRange = e.target.dataset.range;
        document.querySelectorAll('.module.active').forEach(mod => {{
            mod.dataset.rendered = '';
            renderModule(mod.id.replace('module-', ''), mod);
        }});
    }}
}});

// Seasonality selector — switch indicator without re-rendering whole module
document.addEventListener('click', e => {{
    const btn = e.target.closest('.season-sel-btn');
    if (!btn) return;
    const cid = btn.dataset.chartCid, idx = parseInt(btn.dataset.idx);
    const canvas = document.getElementById(cid);
    if (!canvas || !canvas._seasonalityChart) return;
    // toggle active state within this selector group
    btn.parentElement.querySelectorAll('.season-sel-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    // find the module's obs
    const modEl = canvas.closest('.module');
    const modId = modEl ? modEl.id.replace('module-','') : null;
    if (!modId) return;
    const obs = DATA.modules[modId].observations;
    const ch = canvas._seasonalityChart;
    const cfg = buildSeasonalityConfig(ch, obs, idx);
    if (!cfg) return;
    if (canvas._chartInstance) canvas._chartInstance.destroy();
    canvas._chartInstance = new Chart(canvas, cfg);
    canvas._chartData = {{ labels: cfg.data.labels, datasets: cfg.data.datasets.map(ds => ({{ label: ds.label, data: ds.data }})) }};
}});

// Init
document.addEventListener('DOMContentLoaded', () => {{
    const nav = document.getElementById('nav-bar');
    const container = document.getElementById('modules-container');
    MODULES.forEach((m, i) => {{
        nav.innerHTML += '<button class="nav-btn' + (i===0?' active':'') + '" onclick="switchModule(\\'' + m.id + '\\',this)">' + m.name + '</button>';
        container.innerHTML += '<div class="module' + (i===0?' active':'') + '" id="module-' + m.id + '"></div>';
    }});
    if (MODULES.length) switchModule(MODULES[0].id, nav.querySelector('.nav-btn'));
}});
</script>
</body>
</html>'''

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding='utf-8')
    size_kb = round(len(html) / 1024)
    print(f"Done: {output_path} ({size_kb} KB)")
    return output_path


if __name__ == "__main__":
    out = REPORTS_DIR / "fx_flow_dashboard.html"
    generate_html(out)
