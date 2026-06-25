"""
Build complete chart_catalog.json from chart_inventory.json + CHART_MIGRATION_PLAN.md.
Maps Excel column references to series_ids and applies migration decisions.
"""
import json, re, os, sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Module name to series_id prefix mapping
MODULE_PREFIX = {
    '3.即远期': 'fx_fwd',
    '3.代客即期': 'fx_cspot',
    '3.涉外收付': 'fx_crossborder',
    '3.货物贸易': 'trade_goods',
    '3.贸易商': 'trade_merchant',
    '3.服务贸易': 'trade_services',
    '3.FDI': 'fdi',
    '3.证券EQ': 'sec_eq',
    '3.证券FI': 'sec_fi',
}

CHART_COLORS = {
    'blue': '#1a3a5c', 'red': '#c0392b', 'green': '#27ae60',
    'orange': '#d4841a', 'purple': '#8e44ad', 'teal': '#1abc9c',
    'grey': '#7f8c8d', 'dark': '#2c3e50', 'gold': '#f39c12',
    'pink': '#e74c3c', 'cyan': '#3498db', 'lime': '#2ecc71',
}

def load_chart_inventory():
    # chart_inventory.json moved to 相关开发文档/.inspection/ during folder reorg
    inv_path = PROJECT_ROOT.parent / '相关开发文档' / '.inspection' / 'chart_inventory.json'
    with open(inv_path) as f:
        return json.load(f)

def col_to_series_id(sheet, col):
    """Map Excel sheet + column letter to series_id."""
    prefix = MODULE_PREFIX.get(sheet)
    if not prefix:
        return None
    return f"{prefix}:{col}"

def build_catalog():
    inventory = load_chart_inventory()

    # ===================================================================
    # Chart definitions following CHART_MIGRATION_PLAN.md decisions
    # ===================================================================

    modules = {
        '3.即远期': {
            '_source_sheet': '3.即远期',
            'charts': [
                {
                    'chart_id': 'fx_fwd_total_supply',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'bar_line_combo',
                    'title': '外汇市场即远期总供求',
                    'subtitle': '亿美元，月度 · 含12MMA趋势线',
                    'source_excel_charts': ['3.即远期#01', '3.即远期#04'],
                    'analysis_question': '外汇市场总供给方向与动能如何？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'fx_fwd:AB', 'label': '银行净结汇当月发生', 'type': 'bar', 'color': '#1a3a5c', 'stack': 'supply'},
                        {'series_id': 'fx_fwd:AJ', 'label': '期权Delta净变动', 'type': 'bar', 'color': '#d4841a', 'stack': 'supply'},
                        {'series_id': 'fx_fwd:AD', 'label': '远期签约净额', 'type': 'bar', 'color': '#8e44ad', 'stack': 'supply'},
                        {'series_id': 'fx_fwd:supply_demand', 'label': '即远期合计', 'type': 'line', 'color': '#c0392b', 'line_width': 2},
                        {'series_id': 'fx_fwd:supply_demand_12mma', 'label': '12MMA', 'type': 'line', 'color': '#e67e22', 'line_dash': [5, 3]},
                    ]
                },
                {
                    'chart_id': 'fx_fwd_spot_breakdown',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'bar_line_combo',
                    'title': '即期结售汇发生额与远期履约',
                    'subtitle': '亿美元，月度 · 桥接分解',
                    'source_excel_charts': ['3.即远期#05'],
                    'analysis_question': '即期结售汇结构由哪些因素驱动？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'fx_fwd:AE', 'label': '远期履约/平仓', 'type': 'bar', 'color': '#7f8c8d', 'stack': 'bridge'},
                        {'series_id': 'fx_fwd:spot_flow', 'label': '即期结售汇发生额', 'type': 'line', 'color': '#1a3a5c', 'line_width': 2},
                        {'series_id': 'fx_fwd:AB', 'label': '银行净结汇', 'type': 'line', 'color': '#c0392b'},
                    ]
                },
                {
                    'chart_id': 'fx_fwd_deriv_components',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'bar_line_combo',
                    'title': '衍生品签约分解：远期+期权',
                    'subtitle': '亿美元，月度',
                    'source_excel_charts': ['3.即远期#06'],
                    'analysis_question': '衍生品签约由远期还是期权驱动？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'fx_fwd:E', 'label': '远期结汇签约', 'type': 'bar', 'color': '#27ae60', 'stack': 'fwd'},
                        {'series_id': 'fx_fwd:F', 'label': '远期购汇签约', 'type': 'bar', 'color': '#e74c3c', 'stack': 'fwd'},
                        {'series_id': 'fx_fwd:AJ', 'label': '期权Delta净变动', 'type': 'bar', 'color': '#8e44ad', 'stack': 'fwd'},
                        {'series_id': 'fx_fwd:deriv_flow', 'label': '衍生品合计', 'type': 'line', 'color': '#2c3e50', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'fx_fwd_deriv_vs_usdcny',
                    'priority': 'drilldown',
                    'family': 'relationship',
                    'chart_type': 'dual_axis',
                    'title': '代客衍生品与USDCNY汇率',
                    'subtitle': '左轴：亿美元 · 右轴：人民币/美元',
                    'source_excel_charts': ['3.即远期#07'],
                    'analysis_question': '衍生品签约是否与汇率走势相关？',
                    'default_range': '5y',
                    'zero_line': True,
                    'dual_axis': True,
                    'datasets': [
                        {'series_id': 'fx_fwd:Y', 'label': '衍生品签约', 'type': 'line', 'color': '#1a3a5c', 'axis': 'left'},
                        {'series_id': 'fx_fwd:AN', 'label': 'USDCNY', 'type': 'line', 'color': '#c0392b', 'axis': 'right'},
                    ]
                },
                {
                    'chart_id': 'fx_fwd_bank_own',
                    'priority': 'drilldown',
                    'family': 'trend',
                    'chart_type': 'signed_bar',
                    'title': '银行自身结售汇',
                    'subtitle': '亿美元，月度',
                    'source_excel_charts': ['3.即远期#02'],
                    'analysis_question': '银行自身交易方向与规模？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'fx_fwd:B', 'label': '银行自身结汇', 'type': 'bar', 'color': '#27ae60'},
                        {'series_id': 'fx_fwd:C', 'label': '银行自身售汇', 'type': 'bar', 'color': '#e74c3c'},
                        {'series_id': 'fx_fwd:D', 'label': '差额', 'type': 'line', 'color': '#1a3a5c', 'line_width': 2},
                    ]
                },
            ]
        },
        '3.代客即期': {
            '_source_sheet': '3.代客即期',
            'charts': [
                {
                    'chart_id': 'fx_cspot_current_financial',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'bar_line_combo',
                    'title': '经常账户与金融账户结售汇',
                    'subtitle': '亿美元，月度 · 含6MMA',
                    'source_excel_charts': ['3.代客即期#01', '3.代客即期#05'],
                    'analysis_question': '经常 vs 金融账户谁是结售汇主力？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'fx_cspot:X', 'label': '经常账户差额', 'type': 'bar', 'color': '#1a3a5c', 'stack': 'caf'},
                        {'series_id': 'fx_cspot:Y', 'label': '金融账户差额', 'type': 'bar', 'color': '#d4841a', 'stack': 'caf'},
                        {'series_id': 'fx_cspot:Z', 'label': '代客即期合计', 'type': 'line', 'color': '#c0392b', 'line_width': 2},
                        {'series_id': 'fx_cspot:AE', 'label': '合计6MMA', 'type': 'line', 'color': '#e67e22', 'line_dash': [5, 3]},
                    ]
                },
                {
                    'chart_id': 'fx_cspot_full_decomp',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'stacked_bar_line',
                    'title': '六类账户结售汇完整分解',
                    'subtitle': '亿美元，月度',
                    'source_excel_charts': ['3.代客即期#02'],
                    'analysis_question': '各类账户分别贡献多少结售汇？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'fx_cspot:R', 'label': '货物贸易', 'type': 'bar', 'color': '#1a3a5c', 'stack': 'accounts'},
                        {'series_id': 'fx_cspot:S', 'label': '服务贸易', 'type': 'bar', 'color': '#27ae60', 'stack': 'accounts'},
                        {'series_id': 'fx_cspot:T', 'label': '收益转移', 'type': 'bar', 'color': '#8e44ad', 'stack': 'accounts'},
                        {'series_id': 'fx_cspot:U', 'label': '直接投资', 'type': 'bar', 'color': '#d4841a', 'stack': 'accounts'},
                        {'series_id': 'fx_cspot:V', 'label': '证券投资', 'type': 'bar', 'color': '#e74c3c', 'stack': 'accounts'},
                        {'series_id': 'fx_cspot:W', 'label': '其他金融', 'type': 'bar', 'color': '#7f8c8d', 'stack': 'accounts'},
                        {'series_id': 'fx_cspot:Z', 'label': '合计', 'type': 'line', 'color': '#2c3e50', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'fx_cspot_seasonality',
                    'priority': 'drilldown',
                    'family': 'seasonality',
                    'chart_type': 'seasonality_band',
                    'title': '代客即期结售汇季节性',
                    'subtitle': '亿美元 · 1-12月历史区间',
                    'source_excel_charts': ['3.代客即期#06', '3.代客即期#07', '3.代客即期#08', '3.代客即期#09'],
                    'analysis_question': '各类账户结售汇有什么季节性规律？',
                    'default_range': 'all',
                    'seasonality_selector': True,
                    'datasets': [
                        {'series_id': 'fx_cspot:R', 'label': '货物贸易', 'color': '#1a3a5c'},
                        {'series_id': 'fx_cspot:S', 'label': '服务贸易', 'color': '#27ae60'},
                        {'series_id': 'fx_cspot:T', 'label': '收益转移', 'color': '#8e44ad'},
                        {'series_id': 'fx_cspot:U', 'label': '直接投资', 'color': '#d4841a'},
                    ]
                },
            ]
        },
        '3.涉外收付': {
            '_source_sheet': '3.涉外收付',
            'charts': [
                {
                    'chart_id': 'fx_cross_full_decomp',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'stacked_bar_line',
                    'title': '涉外收付六类账户分解',
                    'subtitle': '亿美元，月度',
                    'source_excel_charts': ['3.涉外收付#01'],
                    'analysis_question': '各类跨境收付差额如何分布？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'fx_crossborder:W', 'label': '货物贸易', 'type': 'bar', 'color': '#1a3a5c', 'stack': 'xborder'},
                        {'series_id': 'fx_crossborder:X', 'label': '服务贸易', 'type': 'bar', 'color': '#27ae60', 'stack': 'xborder'},
                        {'series_id': 'fx_crossborder:Y', 'label': '收益转移', 'type': 'bar', 'color': '#8e44ad', 'stack': 'xborder'},
                        {'series_id': 'fx_crossborder:Z', 'label': '直接投资', 'type': 'bar', 'color': '#d4841a', 'stack': 'xborder'},
                        {'series_id': 'fx_crossborder:AC', 'label': '证券投资', 'type': 'bar', 'color': '#e74c3c', 'stack': 'xborder'},
                        {'series_id': 'fx_crossborder:AD', 'label': '其他金融', 'type': 'bar', 'color': '#7f8c8d', 'stack': 'xborder'},
                        {'series_id': 'fx_crossborder:AE', 'label': '合计', 'type': 'line', 'color': '#2c3e50', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'fx_cross_currency_decomp',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'stacked_bar_line',
                    'title': '分币种跨境净流入',
                    'subtitle': '亿美元，月度',
                    'source_excel_charts': ['3.涉外收付#02'],
                    'analysis_question': '美元、人民币、其他货币净流入如何？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'fx_crossborder:G', 'label': '人民币净流入', 'type': 'bar', 'color': '#e74c3c', 'stack': 'currency'},
                        {'series_id': 'fx_crossborder:F', 'label': '美元净流入', 'type': 'bar', 'color': '#1a3a5c', 'stack': 'currency'},
                        {'series_id': 'fx_crossborder:AF', 'label': '其他货币', 'type': 'bar', 'color': '#7f8c8d', 'stack': 'currency'},
                        {'series_id': 'fx_crossborder:AH', 'label': '合计', 'type': 'line', 'color': '#2c3e50', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'fx_cross_cny_usd_share',
                    'priority': 'primary',
                    'family': 'trend',
                    'chart_type': 'multi_line',
                    'title': '人民币与美元跨境收付占比',
                    'subtitle': '百分比，月度 · 0-100%固定轴',
                    'source_excel_charts': ['3.涉外收付#04'],
                    'analysis_question': '人民币国际化在跨境收付中的进展？',
                    'default_range': 'all',
                    'y_min': 0, 'y_max': 100,
                    'datasets': [
                        {'series_id': 'fx_crossborder:AG', 'label': '人民币跨境收付占比', 'type': 'line', 'color': '#e74c3c'},
                        {'series_id': 'fx_crossborder:AI', 'label': '美元跨境收付占比', 'type': 'line', 'color': '#1a3a5c'},
                    ]
                },
                {
                    'chart_id': 'fx_cross_seasonality',
                    'priority': 'drilldown',
                    'family': 'seasonality',
                    'chart_type': 'seasonality_band',
                    'title': '涉外收付季节性',
                    'subtitle': '亿美元 · 1-12月历史区间',
                    'source_excel_charts': ['3.涉外收付#05', '3.涉外收付#06', '3.涉外收付#07', '3.涉外收付#08'],
                    'analysis_question': '各类跨境收付有什么季节性规律？',
                    'default_range': 'all',
                    'seasonality_selector': True,
                    'datasets': [
                        {'series_id': 'fx_crossborder:W', 'label': '货物贸易', 'color': '#1a3a5c'},
                        {'series_id': 'fx_crossborder:X', 'label': '服务贸易', 'color': '#27ae60'},
                        {'series_id': 'fx_crossborder:Y', 'label': '收益转移', 'color': '#8e44ad'},
                        {'series_id': 'fx_crossborder:Z', 'label': '直接投资', 'color': '#d4841a'},
                    ]
                },
            ]
        },
        '3.货物贸易': {
            '_source_sheet': '3.货物贸易',
            'charts': [
                {
                    'chart_id': 'trade_goods_ttm_panel',
                    'priority': 'primary',
                    'family': 'trend',
                    'chart_type': 'multi_line',
                    'title': '货物贸易TTM：顺差/流入/结汇',
                    'subtitle': '亿美元，滚动12个月',
                    'source_excel_charts': ['3.货物贸易#02'],
                    'analysis_question': '贸易商结汇意愿是否与顺差匹配？',
                    'default_range': '5y',
                    'zero_line': False,
                    'datasets': [
                        {'series_id': 'trade_goods:V', 'label': '顺差TTM', 'type': 'line', 'color': '#1a3a5c', 'line_width': 2},
                        {'series_id': 'trade_goods:W', 'label': '流入TTM', 'type': 'line', 'color': '#27ae60'},
                        {'series_id': 'trade_goods:X', 'label': '即期结汇TTM', 'type': 'line', 'color': '#d4841a'},
                        {'series_id': 'trade_goods:Z', 'label': '总结汇TTM', 'type': 'line', 'color': '#c0392b', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'trade_goods_unsettled_position',
                    'priority': 'primary',
                    'family': 'trend',
                    'chart_type': 'multi_line',
                    'title': '未结汇头寸：跨境-结汇与顺差-结汇',
                    'subtitle': '亿美元，滚动12个月余额',
                    'source_excel_charts': ['3.货物贸易#04'],
                    'analysis_question': '贸易商积累了多大的未结汇头寸？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'trade_goods:AA', 'label': '跨境-结汇(TTM)', 'type': 'line', 'color': '#1a3a5c', 'line_width': 2},
                        {'series_id': 'trade_goods:AB', 'label': '顺差-结汇(TTM)', 'type': 'line', 'color': '#d4841a', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'trade_goods_percentile',
                    'priority': 'drilldown',
                    'family': 'percentile',
                    'chart_type': 'percentile_line',
                    'title': '未结汇头寸滚动分位',
                    'subtitle': '分位值 · 0-100%',
                    'source_excel_charts': ['3.货物贸易#03'],
                    'analysis_question': '当前未结汇头寸在历史上什么分位？',
                    'default_range': 'all',
                    'y_min': 0, 'y_max': 100,
                    'datasets': [
                        {'series_id': 'trade_goods:AC', 'label': '已跨境未结汇头寸分位', 'type': 'line', 'color': '#1a3a5c'},
                        {'series_id': 'trade_goods:AD', 'label': '顺差未结汇头寸分位', 'type': 'line', 'color': '#d4841a'},
                    ]
                },
                {
                    'chart_id': 'trade_goods_seasonality',
                    'priority': 'drilldown',
                    'family': 'seasonality',
                    'chart_type': 'seasonality_band',
                    'title': '货物贸易季节性',
                    'subtitle': '亿美元 · 1-12月历史区间',
                    'source_excel_charts': ['3.货物贸易#05', '3.货物贸易#06', '3.货物贸易#07', '3.货物贸易#08'],
                    'analysis_question': '货物贸易顺差和结售汇有什么季节性？',
                    'default_range': 'all',
                    'seasonality_selector': True,
                    'datasets': [
                        {'series_id': 'trade_goods:R', 'label': '贸易顺差', 'color': '#1a3a5c'},
                        {'series_id': 'trade_goods:S', 'label': '涉外收付顺差', 'color': '#27ae60'},
                        {'series_id': 'trade_goods:U', 'label': '即远期结汇', 'color': '#d4841a'},
                    ]
                },
            ]
        },
        '3.贸易商': {
            '_source_sheet': '3.贸易商',
            'charts': [
                {
                    'chart_id': 'trade_merchant_settlement_ratio',
                    'priority': 'primary',
                    'family': 'trend',
                    'chart_type': 'multi_line',
                    'title': '贸易商结汇率与购汇率',
                    'subtitle': '百分比',
                    'source_excel_charts': ['3.贸易商#01', '3.贸易商#04', '3.贸易商#05'],
                    'analysis_question': '贸易商结汇意愿在什么水平？',
                    'default_range': '5y',
                    'datasets': [
                        {'series_id': 'trade_merchant:H', 'label': '收汇结汇率', 'type': 'line', 'color': '#1a3a5c', 'line_width': 2},
                        {'series_id': 'trade_merchant:K', 'label': '付汇购汇率', 'type': 'line', 'color': '#c0392b', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'trade_merchant_willingness_pmi',
                    'priority': 'primary',
                    'family': 'relationship',
                    'chart_type': 'dual_axis',
                    'title': '净结汇意愿与PMI',
                    'subtitle': '左轴：亿美元 · 右轴：PMI指数',
                    'source_excel_charts': ['3.贸易商#02'],
                    'analysis_question': '结汇意愿是否与经济景气同步？',
                    'default_range': '5y',
                    'dual_axis': True,
                    'datasets': [
                        {'series_id': 'trade_merchant:L', 'label': '收付顺差净结汇意愿', 'type': 'line', 'color': '#1a3a5c', 'axis': 'left'},
                        {'series_id': 'trade_merchant:N', 'label': '贸易顺差净结汇意愿', 'type': 'line', 'color': '#27ae60', 'axis': 'left'},
                        {'series_id': 'trade_merchant:AA', 'label': 'PMI 3MMA', 'type': 'line', 'color': '#d4841a', 'axis': 'right'},
                    ]
                },
                {
                    'chart_id': 'trade_merchant_zscore',
                    'priority': 'drilldown',
                    'family': 'distribution',
                    'chart_type': 'multi_line',
                    'title': '结汇率与购汇率Z-Score',
                    'subtitle': '标准差单位 · 37月滚动窗口',
                    'source_excel_charts': ['3.贸易商#06', '3.贸易商#07'],
                    'analysis_question': '当前结汇率偏离历史均值多少标准差？',
                    'default_range': 'all',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'trade_merchant:AM', 'label': '收汇结汇率Z-Score', 'type': 'line', 'color': '#1a3a5c', 'line_width': 2},
                        {'series_id': 'trade_merchant:AN', 'label': '付汇购汇率Z-Score', 'type': 'line', 'color': '#c0392b', 'line_width': 2},
                    ]
                },
            ]
        },
        '3.服务贸易': {
            '_source_sheet': '3.服务贸易',
            'charts': [
                {
                    'chart_id': 'trade_services_balance',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'bar_line_combo',
                    'title': '服务进出口与差额',
                    'subtitle': '亿美元，月度 · 累计值转当期',
                    'source_excel_charts': [],
                    'analysis_question': '服务贸易逆差趋势如何？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'trade_services:B', 'label': '服务出口', 'type': 'bar', 'color': '#27ae60'},
                        {'series_id': 'trade_services:D', 'label': '服务进口', 'type': 'bar', 'color': '#e74c3c'},
                    ]
                },
                {
                    'chart_id': 'trade_services_yoy',
                    'priority': 'primary',
                    'family': 'trend',
                    'chart_type': 'multi_line',
                    'title': '旅行服务进出口增速',
                    'subtitle': '累计同比，百分比',
                    'source_excel_charts': [],
                    'analysis_question': '旅行服务恢复情况如何？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'trade_services:C', 'label': '旅行服务出口增速', 'type': 'line', 'color': '#27ae60', 'line_width': 2},
                        {'series_id': 'trade_services:E', 'label': '旅行服务进口增速', 'type': 'line', 'color': '#e74c3c', 'line_width': 2},
                    ]
                },
            ]
        },
        '3.FDI': {
            '_source_sheet': '3.FDI',
            'charts': [
                {
                    'chart_id': 'fdi_flow',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'bar_line_combo',
                    'title': 'FDI流入流出与净额',
                    'subtitle': '亿美元，月度/季度',
                    'source_excel_charts': ['3.FDI#02', '3.FDI#04', '3.FDI#05', '3.FDI#06'],
                    'analysis_question': 'FDI净流入趋势如何？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'fdi:B', 'label': 'FDI流入', 'type': 'bar', 'color': '#27ae60', 'stack': 'fdi'},
                        {'series_id': 'fdi:D', 'label': 'ODI流出', 'type': 'bar', 'color': '#e74c3c', 'stack': 'fdi'},
                        {'series_id': 'fdi:P', 'label': '净流入', 'type': 'line', 'color': '#1a3a5c', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'fdi_fx_settlement',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'bar_line_combo',
                    'title': 'FDI结汇购汇与差额',
                    'subtitle': '亿美元，月度 · 3MMA',
                    'source_excel_charts': ['3.FDI#03'],
                    'analysis_question': 'FDI相关结售汇方向与规模？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'fdi:Q', 'label': 'FDI结汇', 'type': 'bar', 'color': '#27ae60'},
                        {'series_id': 'fdi:R', 'label': 'FDI购汇', 'type': 'bar', 'color': '#e74c3c'},
                        {'series_id': 'fdi:S', 'label': '差额3MMA', 'type': 'line', 'color': '#1a3a5c', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'fdi_seasonality',
                    'priority': 'primary',
                    'family': 'seasonality',
                    'chart_type': 'seasonality_band',
                    'title': '实际利用外资季节性',
                    'subtitle': '亿美元 · 1-12月历史区间',
                    'source_excel_charts': ['3.FDI#01'],
                    'analysis_question': 'FDI流入有什么季节性规律？',
                    'default_range': 'all',
                    'datasets': [
                        {'series_id': 'fdi:B', 'label': 'FDI当月值', 'color': '#1a3a5c'},
                    ]
                },
            ]
        },
        '3.证券EQ': {
            '_source_sheet': '3.证券EQ',
            'charts': [
                {
                    'chart_id': 'sec_eq_north_south',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'bar_line_combo',
                    'title': '沪深港通：北上与南下资金',
                    'subtitle': '亿元，日度 · 20日滚动',
                    'source_excel_charts': ['3.证券EQ#01'],
                    'analysis_question': '外资通过互联互通是净流入还是净流出？',
                    'default_range': '1y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'sec_eq:B', 'label': '北上资金(20日)', 'type': 'bar', 'color': '#e74c3c'},
                        {'series_id': 'sec_eq:F', 'label': '南下资金(20日)', 'type': 'bar', 'color': '#27ae60'},
                        {'series_id': 'sec_eq:P', 'label': '净流入(20日)', 'type': 'line', 'color': '#1a3a5c', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'sec_eq_vs_csi300',
                    'priority': 'primary',
                    'family': 'relationship',
                    'chart_type': 'dual_axis',
                    'title': '北上资金与沪深300',
                    'subtitle': '左轴：亿元(20日) · 右轴：指数点',
                    'source_excel_charts': ['3.证券EQ#04'],
                    'analysis_question': '外资流入是否与A股走势同步？',
                    'default_range': '2y',
                    'dual_axis': True,
                    'datasets': [
                        {'series_id': 'sec_eq:P', 'label': '北上净流入(20日)', 'type': 'bar', 'color': '#e74c3c', 'axis': 'left'},
                        {'series_id': 'sec_eq:E', 'label': '沪深300', 'type': 'line', 'color': '#1a3a5c', 'axis': 'right', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'sec_eq_flow_vs_fx_scatter',
                    'priority': 'drilldown',
                    'family': 'scatter',
                    'chart_type': 'scatter_regression',
                    'title': '净权益Flow与汇率变动散点',
                    'subtitle': 'X：汇率3M变动(%) · Y：Net Equity Flow 3MMA(亿元)',
                    'source_excel_charts': ['3.证券EQ#05', '3.证券EQ#02', '3.证券EQ#03'],
                    'analysis_question': '权益资金流与汇率变动是否相关？相关性多强？',
                    'default_range': 'all',
                    'scatter': True,
                    'scatter_x': {'series_id': 'sec_eq:AJ', 'label': 'USDCNY 3M变动(%)'},
                    'scatter_y': {'series_id': 'sec_eq:AF', 'label': 'Net Equity Flow 3MMA'},
                    'scatter_x_alt': {'series_id': 'sec_eq:AH', 'label': 'CNYX 3M变动(%)'},
                    'datasets': [
                        {'series_id': 'sec_eq:AF', 'label': 'Net Equity Flow 3MMA', 'color': '#1a3a5c'},
                        {'series_id': 'sec_eq:AJ', 'label': 'USDCNY 3M变动', 'color': '#c0392b'},
                        {'series_id': 'sec_eq:AH', 'label': 'CNYX 3M变动', 'color': '#d4841a'},
                    ]
                },
            ]
        },
        '3.证券FI': {
            '_source_sheet': '3.证券FI',
            'charts': [
                {
                    'chart_id': 'sec_fi_bond_flows',
                    'priority': 'primary',
                    'family': 'trend_decomposition',
                    'chart_type': 'stacked_bar_line',
                    'title': '境外机构债券持有量变动',
                    'subtitle': '亿元，月度',
                    'source_excel_charts': ['3.证券FI#01'],
                    'analysis_question': '外资在增持还是减持中国债券？',
                    'default_range': '5y',
                    'zero_line': True,
                    'datasets': [
                        {'series_id': 'sec_fi:AS', 'label': '国债持仓变动', 'type': 'bar', 'color': '#1a3a5c', 'stack': 'bonds'},
                        {'series_id': 'sec_fi:AT', 'label': '政金债持仓变动', 'type': 'bar', 'color': '#27ae60', 'stack': 'bonds'},
                        {'series_id': 'sec_fi:AU', 'label': '同业存单持仓变动', 'type': 'bar', 'color': '#8e44ad', 'stack': 'bonds'},
                        {'series_id': 'sec_fi:BA', 'label': '利率债合计变动', 'type': 'line', 'color': '#c0392b', 'line_width': 2},
                    ]
                },
                {
                    'chart_id': 'sec_fi_ratebond_vs_spread_scatter',
                    'priority': 'drilldown',
                    'family': 'scatter',
                    'chart_type': 'scatter_regression',
                    'title': '利率债流入与中美利差散点',
                    'subtitle': 'X：中美利差(%) · Y：利率债inflow(亿元)',
                    'source_excel_charts': ['3.证券FI#02'],
                    'analysis_question': '债券资金流入是否由中美利差驱动？',
                    'default_range': 'all',
                    'scatter': True,
                    'scatter_x': {'series_id': 'sec_fi:BJ', 'label': '中美利差(%)'},
                    'scatter_y': {'series_id': 'sec_fi:BK', 'label': '利率债inflow(亿元)'},
                    'datasets': [
                        {'series_id': 'sec_fi:BK', 'label': '利率债inflow', 'color': '#1a3a5c'},
                        {'series_id': 'sec_fi:BJ', 'label': '中美利差', 'color': '#c0392b'},
                    ]
                },
            ]
        },
    }

    # ===================================================================
    # Validation
    # ===================================================================
    total_primary = sum(
        sum(1 for ch in m['charts'] if ch['priority'] == 'primary')
        for m in modules.values()
    )
    total_drilldown = sum(
        sum(1 for ch in m['charts'] if ch['priority'] == 'drilldown')
        for m in modules.values()
    )
    total = sum(len(m['charts']) for m in modules.values())

    catalog = {
        '_meta': {
            'version': '1.0.0',
            'created': '2026-06-23',
            'total_charts': total,
            'primary_charts': total_primary,
            'drilldown_charts': total_drilldown,
            'original_excel_charts': 66,
            'note': 'All 66 original charts mapped: retained/merged/redone/deleted per CHART_MIGRATION_PLAN.md'
        },
        'modules': modules
    }

    return catalog, total_primary, total_drilldown, total


if __name__ == '__main__':
    catalog, prim, dd, tot = build_catalog()

    output_path = PROJECT_ROOT / 'config' / 'chart_catalog.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"✅ chart_catalog.json built: {tot} charts ({prim} primary, {dd} drill-down)")
    print(f"   Saved to: {output_path}")

    # Module summary
    for mod_name, mod_data in catalog['modules'].items():
        charts = mod_data['charts']
        prim_count = sum(1 for c in charts if c['priority'] == 'primary')
        dd_count = sum(1 for c in charts if c['priority'] == 'drilldown')
        print(f"  {mod_name}: {prim_count}p + {dd_count}d = {len(charts)} charts")
