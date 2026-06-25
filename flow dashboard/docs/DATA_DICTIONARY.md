# Data Dictionary

> Auto-generated from SQLite `series` table by `gen_data_dictionary.py`
> Generated: 2026-06-24 22:05
> Single source of truth: `data/monthly_brief.sqlite` · `series` table

## Summary

| Metric | Count |
|--------|-------|
| Total Series (SQLite) | 383 |
| Raw | 158 |
| Derived | 223 |
| Manual | 2 |
| With Observations | 371 |
| Time Range | 1994-01-31 → 2026-05-31 |
| Column_* (Excel intermediate) | 86 |
| Unknown / empty unit | 139 |

## Known Issues

- **86** series still named `Column_*` (Excel intermediate columns; out of v1 display scope, retained in DB).
- **139** series with empty/unknown units (primarily DB-only intermediates; chart-critical series all have a real unit).
- `fx_fwd:AN` (USDCNY): raw external seed rate (`source=excel_seed`), history from an Excel VLOOKUP FX-rate lookup table; pending Wind USDCNY monthly-rate mapping.

## Series by Module

### 3.FDI (55 series)

| series_id | display_name | type | frequency | unit |
|-----------|-------------|------|-----------|------|
| fdi:A | 指标名称 | raw | monthly | unknown |
| fdi:AA | Column_AA | derived | monthly | unknown |
| fdi:AB | Column_AB | derived | monthly | unknown |
| fdi:AC | Column_AC | derived | monthly | unknown |
| fdi:AD | Column_AD | derived | monthly | unknown |
| fdi:AE | Column_AE | derived | monthly | unknown |
| fdi:AF | Column_AF | derived | monthly | unknown |
| fdi:AG | Column_AG | derived | monthly | unknown |
| fdi:AH | Column_AH | derived | monthly | unknown |
| fdi:AJ | Column_AJ | derived | monthly | unknown |
| fdi:AK | Column_AK | derived | monthly | unknown |
| fdi:AL | Column_AL | derived | monthly | unknown |
| fdi:AM | Column_AM | derived | monthly | unknown |
| fdi:AN | Column_AN | derived | monthly | unknown |
| fdi:AQ | 中国:金融账户:非储备性质的金融账户:直接投资:差额:当季值 | raw | monthly | balance |
| fdi:AR | 中国:金融账户:非储备性质的金融账户:直接投资:负债净产生:当季值 | raw | monthly | unknown |
| fdi:AS | 中国:金融账户:非储备性质的金融账户:直接投资:资产净获得:当季值 | raw | monthly | unknown |
| fdi:AT | 中国:金融账户:非储备性质的金融账户:直接投资:负债净产生:股权:当季值 | raw | monthly | unknown |
| fdi:AU | 中国:金融账户:非储备性质的金融账户:直接投资:负债净产生:关联企业债务:当季值 | raw | monthly | unknown |
| fdi:AV | 中国:金融账户:非储备性质的金融账户:直接投资:资产净获得:股权:当季值 | raw | monthly | unknown |
| fdi:AW | 中国:金融账户:非储备性质的金融账户:直接投资:资产净获得:关联企业债务:当季值 | raw | monthly | unknown |
| fdi:AY | FDI流入-股权 | derived | monthly | value |
| fdi:AZ | FDI流入-债权 | derived | monthly | value |
| fdi:B | 实际使用外资金额:外商直接投资:当月值 | raw | monthly | monthly_amount |
| fdi:BA | Column_BA | derived | monthly | unknown |
| fdi:BD | 中国:金融账户:非储备性质的金融账户:直接投资:差额:当季值:年度:合计值 | raw | monthly | balance |
| fdi:BE | 中国:金融账户:非储备性质的金融账户:直接投资:负债净产生:当季值:年度:合计值 | raw | monthly | unknown |
| fdi:BF | 中国:金融账户:非储备性质的金融账户:直接投资:资产净获得:当季值:年度:合计值 | raw | monthly | unknown |
| fdi:BG | 中国:金融账户:非储备性质的金融账户:直接投资:负债净产生:股权:当季值:年度:合计值 | raw | monthly | unknown |
| fdi:BH | 中国:金融账户:非储备性质的金融账户:直接投资:负债净产生:关联企业债务:当季值:年度:合计值 | raw | monthly | unknown |
| fdi:BI | 中国:金融账户:非储备性质的金融账户:直接投资:资产净获得:股权:当季值:年度:合计值 | raw | monthly | unknown |
| fdi:BJ | 中国:金融账户:非储备性质的金融账户:直接投资:资产净获得:关联企业债务:当季值:年度:合计值 | raw | monthly | unknown |
| fdi:BL | Column_BL | derived | monthly | unknown |
| fdi:BM | Column_BM | derived | monthly | unknown |
| fdi:BN | Column_BN | derived | monthly | unknown |
| fdi:C | 实际使用外资金额:合计:累计值 | raw | monthly | cumulative_amount |
| fdi:D | 实际使用外资金额:外商直接投资:累计值 | raw | monthly | cumulative_amount |
| fdi:E | 制造业:实际使用外商直接投资:累计值 | raw | monthly | cumulative_amount |
| fdi:F | 服务业:实际使用外商直接投资:累计值 | raw | monthly | cumulative_amount |
| fdi:G | 非金融类对外直接投资:当月值 | raw | monthly | monthly_amount |
| fdi:H | 非金融类对外直接投资:累计值 | raw | monthly | cumulative_amount |
| fdi:I | 银行代客结汇:直接投资:当月值 | raw | monthly | monthly_amount |
| fdi:J | 银行代客售汇:直接投资:当月值 | raw | monthly | monthly_amount |
| fdi:K | 中国:实际使用外资金额:外商直接投资:人民币:当月值 | raw | monthly | monthly_amount |
| fdi:L | 中国:实际使用外资金额:外商直接投资:人民币:累计值 | raw | monthly | cumulative_amount |
| fdi:M | 中国:中间价:美元兑人民币:月:平均值 | raw | monthly | 亿美元 |
| fdi:P | 实际使用外资 | derived | monthly | value |
| fdi:Q | 对外直接投资 | derived | monthly | value |
| fdi:R | FDI-ODI差额 | derived | monthly | net_flow |
| fdi:S | FDI结售汇差额3MMA | derived | monthly | moving_average |
| fdi:T | FDI结汇3MMA | derived | monthly | moving_average |
| fdi:U | FDI购汇3MMA | derived | monthly | moving_average |
| fdi:X | Column_X | raw | monthly | unknown |
| fdi:Y | Column_Y | derived | monthly | unknown |
| fdi:Z | Column_Z | derived | monthly | unknown |

### 3.代客即期 (47 series)

| series_id | display_name | type | frequency | unit |
|-----------|-------------|------|-----------|------|
| fx_cspot:A | 指标名称 | raw | monthly | unknown |
| fx_cspot:AC | 经常账户结售汇6MMA | derived | monthly | moving_average |
| fx_cspot:AD | 金融账户结售汇6MMA | derived | monthly | moving_average |
| fx_cspot:AE | 结售汇差额6MMA合计 | derived | monthly | moving_average |
| fx_cspot:AF | 货物贸易/TOTAL | derived | monthly | unknown |
| fx_cspot:AH | Column_AH | raw | monthly | unknown |
| fx_cspot:AI | Column_AI | derived | monthly | unknown |
| fx_cspot:AJ | Column_AJ | derived | monthly | unknown |
| fx_cspot:AK | Column_AK | derived | monthly | unknown |
| fx_cspot:AL | Column_AL | derived | monthly | unknown |
| fx_cspot:AM | Column_AM | derived | monthly | unknown |
| fx_cspot:AN | Column_AN | derived | monthly | unknown |
| fx_cspot:AO | Column_AO | derived | monthly | unknown |
| fx_cspot:AP | Column_AP | derived | monthly | unknown |
| fx_cspot:AQ | Column_AQ | derived | monthly | unknown |
| fx_cspot:AR | Column_AR | derived | monthly | unknown |
| fx_cspot:AS | Column_AS | derived | monthly | unknown |
| fx_cspot:AT | Column_AT | derived | monthly | unknown |
| fx_cspot:AW | Column_AW | derived | monthly | unknown |
| fx_cspot:AX | 不含2022年 | derived | monthly | unknown |
| fx_cspot:AY | Column_AY | derived | monthly | unknown |
| fx_cspot:AZ | Column_AZ | derived | monthly | unknown |
| fx_cspot:B | 银行代客结汇:经常项目:当月值 | raw | monthly | monthly_amount |
| fx_cspot:BA | Column_BA | derived | monthly | unknown |
| fx_cspot:BB | Column_BB | raw | monthly | unknown |
| fx_cspot:C | 银行代客结汇:货物贸易:当月值 | raw | monthly | monthly_amount |
| fx_cspot:D | 银行代客结汇:服务贸易:当月值 | raw | monthly | monthly_amount |
| fx_cspot:E | 银行代客结汇:收益和经常转移:当月值 | raw | monthly | monthly_amount |
| fx_cspot:F | 银行代客结汇:资本与金融项目:当月值 | raw | monthly | monthly_amount |
| fx_cspot:G | 银行代客结汇:直接投资:当月值 | raw | monthly | monthly_amount |
| fx_cspot:H | 银行代客结汇:证券投资:当月值 | raw | monthly | monthly_amount |
| fx_cspot:I | 银行代客售汇:经常项目:当月值 | raw | monthly | monthly_amount |
| fx_cspot:J | 银行代客售汇:货物贸易:当月值 | raw | monthly | monthly_amount |
| fx_cspot:K | 银行代客售汇:服务贸易:当月值 | raw | monthly | monthly_amount |
| fx_cspot:L | 银行代客售汇:收益和经常转移:当月值 | raw | monthly | monthly_amount |
| fx_cspot:M | 银行代客售汇:资本与金融项目:当月值 | raw | monthly | monthly_amount |
| fx_cspot:N | 银行代客售汇:直接投资:当月值 | raw | monthly | monthly_amount |
| fx_cspot:O | 银行代客售汇:证券投资:当月值 | raw | monthly | monthly_amount |
| fx_cspot:R | 货物贸易结售汇差额 | derived | monthly | net_flow |
| fx_cspot:S | 服务贸易结售汇差额 | derived | monthly | net_flow |
| fx_cspot:T | 收益和经常转移结售汇差额 | derived | monthly | net_flow |
| fx_cspot:U | 直接投资结售汇差额 | derived | monthly | net_flow |
| fx_cspot:V | 证券投资结售汇差额 | derived | monthly | net_flow |
| fx_cspot:W | 其他金融项目结售汇差额 | derived | monthly | net_flow |
| fx_cspot:X | 经常账户结售汇差额 | derived | monthly | net_flow |
| fx_cspot:Y | 金融账户结售汇差额 | derived | monthly | net_flow |
| fx_cspot:Z | 代客即期结售汇差额 | derived | monthly | net_flow |

### 3.即远期 (44 series)

| series_id | display_name | type | frequency | unit |
|-----------|-------------|------|-----------|------|
| fx_fwd:A | 指标名称 | raw | monthly | unknown |
| fx_fwd:AA | 远期和期权敞口变动=签约-履约 | derived | monthly | unknown |
| fx_fwd:AB | 即期代客结售汇差额（Headline） | derived | monthly | balance |
| fx_fwd:AC | 由于黄金买卖行为经常发生，而且规模较大，所以在多数时间里，影响“银行自身结售汇”数据波动的主要因素是国际金价的波动，这种波动和黄金市场的波动关系密切，和人民币升贬值预期基本无直接无关。 | derived | monthly | unknown |
| fx_fwd:AD | 代客衍生品净结汇 | derived | monthly | net_flow |
| fx_fwd:AE | 与当前市场情绪和预期变化毫无关系。计算方法：远期结售汇累计未到期额变动+本月远期结售汇签约额 | derived | monthly | cumulative_amount |
| fx_fwd:AF | 正数流入 | derived | monthly | unknown |
| fx_fwd:AG | 负数流出 | derived | monthly | unknown |
| fx_fwd:AH | 远期结汇签约 | derived | monthly | unknown |
| fx_fwd:AI | 远期购汇签约 | derived | monthly | unknown |
| fx_fwd:AJ | 期权Delta净变动 | derived | monthly | 亿美元 |
| fx_fwd:AL | 即期汇率:美元兑人民币:月 | raw | monthly | exchange_rate |
| fx_fwd:AN | USDCNY | raw | monthly | CNY/USD |
| fx_fwd:AO | 代客衍生品签约 | derived | monthly | unknown |
| fx_fwd:AP | 代客衍生品签约3MMA | derived | monthly | moving_average |
| fx_fwd:AQ | 外汇市场供求 | derived | monthly | unknown |
| fx_fwd:B | 银行自身结汇:当月值 | raw | monthly | monthly_amount |
| fx_fwd:C | 银行自身售汇:当月值 | raw | monthly | monthly_amount |
| fx_fwd:D | 银行自身结售汇差额:当月值 | raw | monthly | monthly_amount |
| fx_fwd:E | 银行代客远期结汇签约:当月值 | raw | monthly | monthly_amount |
| fx_fwd:F | 银行代客远期售汇签约:当月值 | raw | monthly | monthly_amount |
| fx_fwd:G | 银行代客远期净结汇:当月值 | raw | monthly | monthly_amount |
| fx_fwd:H | 银行代客远期结汇累计未到期额 | raw | monthly | cumulative_amount |
| fx_fwd:I | 银行代客远期售汇累计未到期额 | raw | monthly | cumulative_amount |
| fx_fwd:J | 银行代客远期净结汇累计未到期额 | raw | monthly | cumulative_amount |
| fx_fwd:K | 银行代客结汇:当月值 | raw | monthly | monthly_amount |
| fx_fwd:L | 银行代客售汇:当月值 | raw | monthly | monthly_amount |
| fx_fwd:M | 银行代客结售汇顺差:当月值 | raw | monthly | monthly_amount |
| fx_fwd:N | 银行结售汇:未到期期权Delta净敞口 | raw | monthly | 亿美元 |
| fx_fwd:Q | 银行对外股息和红利支付、海外利润汇回和注资、客户黄金买卖在国际市场平盘带来的结售汇需求（规模大常波动） | derived | monthly | unknown |
| fx_fwd:R | 企业和个人当月真实的结售汇操作，是企业和个人根据当前市场形势作出判断后的操作结果（即期代客-远期履约） | derived | monthly | monthly_amount |
| fx_fwd:S | 反映市场情绪非常直接；净结汇看升值；净售汇看贬值 | derived | monthly | net_flow |
| fx_fwd:T | 未到期期权Delta净敞口变动 | derived | monthly | unknown |
| fx_fwd:U | 银行自身结售汇+即期代客结售汇差额当月发生额+远期签约额+期权Delta净敞口变化（含期权，不含远期履约） | derived | monthly | monthly_amount |
| fx_fwd:V | 即远期结售汇合计6MMA | derived | monthly | moving_average |
| fx_fwd:W | 即远期结售汇合计12MMA | derived | monthly | moving_average |
| fx_fwd:X | 银行自身结售汇+即期代客结售汇差额当月发生额=（headline-远期履约） | derived | monthly | monthly_amount |
| fx_fwd:Y | 远期新增签约 | derived | monthly | 亿美元 |
| fx_fwd:Z | 银行自身结售汇+代客即期结售汇（含远期履约） | derived | monthly | unknown |
| fx_fwd:deriv_flow | 衍生品当月净签约（远期+期权） | derived | monthly | net_flow |
| fx_fwd:spot_flow | 即期结售汇发生额（银行自身+代客） | derived | monthly | net_flow |
| fx_fwd:supply_demand | 外汇市场即远期总供求 | derived | monthly | net_flow |
| fx_fwd:supply_demand_12mma | 外汇市场即远期总供求（12MMA） | derived | monthly | moving_average |
| fx_fwd:supply_demand_3mma | 外汇市场即远期总供求（3MMA） | derived | monthly | moving_average |

### 3.服务贸易 (6 series)

| series_id | display_name | type | frequency | unit |
|-----------|-------------|------|-----------|------|
| trade_services:A | 指标名称 | raw | monthly | unknown |
| trade_services:B | 中国:服务出口金额:人民币:累计值 | raw | monthly | cumulative_amount |
| trade_services:C | 中国:服务进口金额:人民币:累计值 | raw | monthly | cumulative_amount |
| trade_services:D | 中国:旅行服务出口金额:人民币:累计同比 | raw | monthly | cumulative_amount |
| trade_services:E | 中国:旅行服务进口金额:人民币:累计同比 | raw | monthly | cumulative_amount |
| trade_services:F | 中国:中间价:美元兑人民币:月:平均值 | raw | monthly | 亿美元 |

### 3.涉外收付 (55 series)

| series_id | display_name | type | frequency | unit |
|-----------|-------------|------|-----------|------|
| fx_crossborder:A | 指标名称 | raw | monthly | unknown |
| fx_crossborder:AA | 6 | derived | monthly | unknown |
| fx_crossborder:AB | 7 | derived | monthly | unknown |
| fx_crossborder:AC | 货物贸易差额 | derived | monthly | net_flow |
| fx_crossborder:AD | 服务贸易差额 | derived | monthly | net_flow |
| fx_crossborder:AE | 其他经常项目差额 | derived | monthly | net_flow |
| fx_crossborder:AF | 直接投资差额 | derived | monthly | net_flow |
| fx_crossborder:AG | 证券投资差额 | derived | monthly | net_flow |
| fx_crossborder:AH | 其他金融项目差额 | derived | monthly | net_flow |
| fx_crossborder:AI | 经常账户差额 | derived | monthly | net_flow |
| fx_crossborder:AJ | 金融账户差额 | derived | monthly | net_flow |
| fx_crossborder:AK | 总顺差 | derived | monthly | net_flow |
| fx_crossborder:AL | 外币净流入(顺差-人民币净流入) | derived | monthly | net_flow |
| fx_crossborder:AN | Column_AN | raw | monthly | unknown |
| fx_crossborder:AO | Column_AO | derived | monthly | unknown |
| fx_crossborder:AP | Column_AP | derived | monthly | unknown |
| fx_crossborder:AQ | Column_AQ | derived | monthly | unknown |
| fx_crossborder:AR | Column_AR | derived | monthly | unknown |
| fx_crossborder:AS | Column_AS | derived | monthly | unknown |
| fx_crossborder:AT | Column_AT | derived | monthly | unknown |
| fx_crossborder:AU | Column_AU | derived | monthly | unknown |
| fx_crossborder:AV | Column_AV | derived | monthly | unknown |
| fx_crossborder:AW | Column_AW | derived | monthly | unknown |
| fx_crossborder:AX | Column_AX | derived | monthly | unknown |
| fx_crossborder:AY | Column_AY | derived | monthly | unknown |
| fx_crossborder:B | 境内银行代客涉外收付款顺差:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:BC | Column_BC | derived | monthly | unknown |
| fx_crossborder:BD | 过去5年 | derived | monthly | unknown |
| fx_crossborder:BE | Column_BE | derived | monthly | unknown |
| fx_crossborder:BF | Column_BF | derived | monthly | unknown |
| fx_crossborder:BG | Column_BG | derived | monthly | unknown |
| fx_crossborder:BH | Column_BH | raw | monthly | unknown |
| fx_crossborder:C | 境内银行代客对外付款:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:D | 境内银行代客涉外收入:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:E | 境内银行代客涉外收付款顺差:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:F | 银行代客涉外收付款:收入币种:美元 | raw | monthly | 亿美元 |
| fx_crossborder:G | 银行代客涉外收付款:收入币种:人民币 | raw | monthly | 亿元 |
| fx_crossborder:H | 银行代客涉外收付款:支出币种:美元 | raw | monthly | 亿美元 |
| fx_crossborder:I | 银行代客涉外收付款:支出币种:人民币 | raw | monthly | 亿元 |
| fx_crossborder:J | 境内银行代客涉外收入:经常项目:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:K | 境内银行代客涉外支出:经常项目:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:L | 境内银行代客涉外收入:货物贸易:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:M | 境内银行代客涉外支出:货物贸易:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:N | 境内银行代客涉外收入:服务贸易:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:O | 境内银行代客涉外支出:服务贸易:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:P | 境内银行代客涉外收入:资本与金融项目:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:Q | 境内银行代客涉外支出:资本与金融项目:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:R | 境内银行代客涉外收入:证券投资:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:S | 境内银行代客涉外支出:证券投资:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:T | 境内银行代客涉外收入:直接投资:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:U | 境内银行代客涉外支出:直接投资:当月值 | raw | monthly | monthly_amount |
| fx_crossborder:W | 美元净流入 | derived | monthly | net_flow |
| fx_crossborder:X | 人民币净流入 | derived | monthly | net_flow |
| fx_crossborder:Y | 其他货币净流入 | derived | monthly | net_flow |
| fx_crossborder:Z | 净流入合计 | derived | monthly | net_flow |

### 3.证券EQ (30 series)

| series_id | display_name | type | frequency | unit |
|-----------|-------------|------|-----------|------|
| sec_eq:A | 指标名称 | raw | daily | unknown |
| sec_eq:AB | USDCNY | derived | daily | unknown |
| sec_eq:AC | CNYX | derived | daily | unknown |
| sec_eq:AD | 南下3M | derived | daily | unknown |
| sec_eq:AE | 北上3M | derived | daily | unknown |
| sec_eq:AF | Net Equity Flow（3MMA） | derived | daily | moving_average |
| sec_eq:AG | CNYX 3M Change（%）Lagging 2M | manual | daily | pct_change |
| sec_eq:AH | CNYX 3M Change（%） | derived | daily | pct_change |
| sec_eq:AI | USDCNY 3M Change（%）Lagging 2M | manual | daily | pct_change |
| sec_eq:AJ | USDCNY 3M Change（%） | derived | daily | pct_change |
| sec_eq:B | 即期汇率:美元兑人民币 | raw | daily | exchange_rate |
| sec_eq:C | 巨潮人民币名义有效汇率指数 | raw | daily | index |
| sec_eq:D | Wind人民币汇率预估指数 | raw | daily | index |
| sec_eq:E | 沪深300指数 | raw | daily | index |
| sec_eq:F | 恒生指数 | raw | daily | index |
| sec_eq:H | 港股通:当日买入成交净额(人民币) | raw | daily | 亿元 |
| sec_eq:I | 港股通:累计买入成交净额(人民币) | raw | daily | cumulative_amount |
| sec_eq:J | 陆股通:当日买入成交净额(人民币) | raw | daily | 亿元 |
| sec_eq:K | 陆股通:累计买入成交净额(人民币) | raw | daily | cumulative_amount |
| sec_eq:N | 港股通累计买入成交净额 | derived | daily | cumulative_amount |
| sec_eq:O | 陆股通累计买入成交净额 | derived | daily | cumulative_amount |
| sec_eq:P | 陆港通净流入 | derived | daily | net_flow |
| sec_eq:Q | 沪深300指数 | derived | daily | index |
| sec_eq:R | 恒生指数 | derived | daily | index |
| sec_eq:U | 南下资金滚动20日净流入 | derived | daily | net_flow |
| sec_eq:V | 北上资金滚动20日净流入 | derived | daily | net_flow |
| sec_eq:W | 陆港通滚动20日净流入 | derived | daily | net_flow |
| sec_eq:X | 沪深300滚动20日涨跌幅 | derived | daily | unknown |
| sec_eq:Y | Column_Y | derived | daily | unknown |
| sec_eq:Z | Column_Z | derived | daily | unknown |

### 3.证券FI (54 series)

| series_id | display_name | type | frequency | unit |
|-----------|-------------|------|-----------|------|
| sec_fi:A | 指标名称 | raw | monthly | unknown |
| sec_fi:AA | 上清所:债券托管量:其他公司信用类债券:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:AB | 上清所:债券托管量:熊猫债:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:AC | 上清所:债券托管量:其他债券:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:AD | 上清所:债券托管量:标准化票据:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:AE | 上清所:债券托管量:资产支持证券:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:AF | 境外投资者专项统计:债券托管量 | raw | monthly | custody_amount |
| sec_fi:AG | 上清所合计 | derived | monthly | unknown |
| sec_fi:AH | 国债持仓 | derived | monthly | stock |
| sec_fi:AI | 政金债持仓 | derived | monthly | stock |
| sec_fi:AJ | 同业存单持仓 | derived | monthly | stock |
| sec_fi:AK | 其他债券 | derived | monthly | unknown |
| sec_fi:AL | 合计 | derived | monthly | unknown |
| sec_fi:AM | 合计-含估算 | derived | monthly | unknown |
| sec_fi:AN | 合计-含估算(美元） | derived | monthly | unknown |
| sec_fi:AO | 中债-境外机构 | derived | monthly | unknown |
| sec_fi:AP | 上清-境外机构 | derived | monthly | unknown |
| sec_fi:AS | 国债持仓变动 | derived | monthly | flow |
| sec_fi:AT | 政金债持仓变动 | derived | monthly | flow |
| sec_fi:AU | 同业存单持仓变动 | derived | monthly | flow |
| sec_fi:AV | 其他债券 | derived | monthly | unknown |
| sec_fi:AW | -11088.832300000002 | derived | monthly | unknown |
| sec_fi:AY | Column_AY | derived | monthly | unknown |
| sec_fi:B | 中债:债券托管量:国债:境外机构 | raw | monthly | custody_amount |
| sec_fi:BA | 利率债合计变动 | derived | monthly | flow |
| sec_fi:BB | 国债+政金债变动3MMA | derived | monthly | moving_average |
| sec_fi:BH | 中债国债到期收益率:10年:月 | raw | monthly | yield_pct |
| sec_fi:BI | 美国:国债收益率:10年:月 | raw | monthly | yield_pct |
| sec_fi:BJ | 中美利差 | derived | monthly | bp |
| sec_fi:BK | 利率债inflow | derived | monthly | flow |
| sec_fi:C | 中债:债券托管量:国家开发银行债:境外机构 | raw | monthly | custody_amount |
| sec_fi:D | 中债:债券托管量:中国进出口银行债:境外机构 | raw | monthly | custody_amount |
| sec_fi:E | 中债:债券托管量:中国农业发展银行债:境外机构 | raw | monthly | custody_amount |
| sec_fi:F | 中债:债券托管量:商业银行普通债:境外机构 | raw | monthly | custody_amount |
| sec_fi:G | 中债:债券托管量:商业银行次级债:境外机构 | raw | monthly | custody_amount |
| sec_fi:H | 中债:债券托管量:商业银行混合资本债:境外机构 | raw | monthly | custody_amount |
| sec_fi:I | 中债:债券托管量:二级资本工具:境外机构 | raw | monthly | custody_amount |
| sec_fi:J | 中债:债券托管量:企业债:境外机构 | raw | monthly | custody_amount |
| sec_fi:K | 中债:债券托管量:中期票据:境外机构 | raw | monthly | custody_amount |
| sec_fi:L | 全市场:债券托管量:中期票据:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:M | 上清所:债券托管量:短期融资券:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:N | 上清所:债券托管量:超短期融资券:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:O | 上清所:债券托管量:中期票据:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:P | 上清所:债券托管量:同业存单:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:Q | 上清所:债券托管量:区域集优中小企业集合票据:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:R | 上清所:债券托管量:金融企业短期融资券:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:S | 上清所:债券托管量:信贷资产支持证券:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:T | 上清所:债券托管量:资产管理公司金融债:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:U | 上清所:债券托管量:政府支持机构债券:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:V | 上清所:债券托管量:绿色债务融资工具:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:W | 中债:债券托管量:政策性银行债:境外机构 | raw | monthly | custody_amount |
| sec_fi:X | 中债:债券托管量:商业银行债券:境外机构 | raw | monthly | custody_amount |
| sec_fi:Y | 上清所:债券托管量:金融债券:人民银行批准的境外机构 | raw | monthly | custody_amount |
| sec_fi:Z | 上清所:债券托管量:非公开定向债务融资工具:人民银行批准的境外机构 | raw | monthly | custody_amount |

### 3.货物贸易 (46 series)

| series_id | display_name | type | frequency | unit |
|-----------|-------------|------|-----------|------|
| trade_goods:A | 指标名称 | raw | monthly | unknown |
| trade_goods:AA | 滚动12个月 跨境-结汇(TTM) | derived | monthly | ttm |
| trade_goods:AB | 滚动12个月 顺差-结汇(TTM) | derived | monthly | ttm |
| trade_goods:AC | 已跨境未结汇头寸-滚动分位置 | derived | monthly | 分位(0-100) |
| trade_goods:AD | 顺差未结汇头寸-滚动分位置 | derived | monthly | balance |
| trade_goods:AF | Column_AF | raw | monthly | unknown |
| trade_goods:AG | Column_AG | derived | monthly | unknown |
| trade_goods:AH | Column_AH | derived | monthly | unknown |
| trade_goods:AI | Column_AI | derived | monthly | unknown |
| trade_goods:AJ | Column_AJ | derived | monthly | unknown |
| trade_goods:AK | Column_AK | derived | monthly | unknown |
| trade_goods:AL | Column_AL | derived | monthly | unknown |
| trade_goods:AM | Column_AM | derived | monthly | unknown |
| trade_goods:AN | Column_AN | derived | monthly | unknown |
| trade_goods:AO | Column_AO | derived | monthly | unknown |
| trade_goods:AP | Column_AP | derived | monthly | unknown |
| trade_goods:AQ | Column_AQ | derived | monthly | unknown |
| trade_goods:AT | Column_AT | derived | monthly | unknown |
| trade_goods:AU | Column_AU | derived | monthly | unknown |
| trade_goods:AV | Column_AV | derived | monthly | unknown |
| trade_goods:AW | Column_AW | derived | monthly | unknown |
| trade_goods:AX | Column_AX | derived | monthly | unknown |
| trade_goods:AY | Column_AY | raw | monthly | unknown |
| trade_goods:B | 出口金额:当月值 | raw | monthly | monthly_amount |
| trade_goods:C | 境内银行代客涉外收入:货物贸易:当月值 | raw | monthly | monthly_amount |
| trade_goods:D | 银行代客结汇:货物贸易:当月值 | raw | monthly | monthly_amount |
| trade_goods:E | 进口金额:当月值 | raw | monthly | monthly_amount |
| trade_goods:F | 境内银行代客涉外支出:货物贸易:当月值 | raw | monthly | monthly_amount |
| trade_goods:G | 银行代客售汇:货物贸易:当月值 | raw | monthly | monthly_amount |
| trade_goods:H | 中国:银行代客远期结汇签约:当月值 | raw | monthly | monthly_amount |
| trade_goods:I | 中国:银行代客远期售汇签约:当月值 | raw | monthly | monthly_amount |
| trade_goods:J | 中国:银行代客远期净结汇:当月值 | raw | monthly | monthly_amount |
| trade_goods:K | 出口增速 | derived | monthly | yoy_pct |
| trade_goods:L | 出口增速3MMA | derived | monthly | moving_average |
| trade_goods:N | 即期汇率:美元兑人民币:月:平均值 | raw | monthly | exchange_rate |
| trade_goods:O | Column_O | derived | monthly | unknown |
| trade_goods:P | Column_P | derived | monthly | unknown |
| trade_goods:R | 进出口差额 | derived | monthly | net_flow |
| trade_goods:S | 涉外收付差额 | derived | monthly | net_flow |
| trade_goods:T | 即期结汇差额 | derived | monthly | net_flow |
| trade_goods:U | 即远期结汇(估） | derived | monthly | 亿美元 |
| trade_goods:V | 顺差TTM | derived | monthly | ttm |
| trade_goods:W | 流入TTM | derived | monthly | ttm |
| trade_goods:X | 即期结汇TTM | derived | monthly | ttm |
| trade_goods:Y | 假定75%为贸易商贡献 | derived | monthly | ttm |
| trade_goods:Z | 总结汇TTM | derived | monthly | ttm |

### 3.贸易商 (46 series)

| series_id | display_name | type | frequency | unit |
|-----------|-------------|------|-----------|------|
| trade_merchant:A | 指标名称 | raw | monthly | unknown |
| trade_merchant:AA | PMI | raw | monthly | index |
| trade_merchant:AB | PMI:小型企业 | raw | monthly | index |
| trade_merchant:AC | 中债国债到期收益率:10年:月:平均值 | raw | monthly | yield_pct |
| trade_merchant:AD | 美国:国债收益率:10年:月:平均值 | raw | monthly | yield_pct |
| trade_merchant:AE | Column_AE | derived | monthly | unknown |
| trade_merchant:AG | PMI 3MMA | derived | monthly | moving_average |
| trade_merchant:AH | PMI小型企业 | derived | monthly | unknown |
| trade_merchant:AI | 10Y国债利率 | derived | monthly | unknown |
| trade_merchant:AJ | 中美利差3MMA | derived | monthly | moving_average |
| trade_merchant:AL | 进出口差额 | derived | monthly | net_flow |
| trade_merchant:AM | 涉外收付差额 | derived | monthly | net_flow |
| trade_merchant:AN | 结售汇差额 | derived | monthly | net_flow |
| trade_merchant:AO | Column_AO | derived | monthly | unknown |
| trade_merchant:AP | Column_AP | derived | monthly | unknown |
| trade_merchant:AQ | Column_AQ | derived | monthly | unknown |
| trade_merchant:AS | Column_AS | derived | monthly | unknown |
| trade_merchant:AT | Column_AT | derived | monthly | unknown |
| trade_merchant:AU | 结售汇差额3MMA | derived | monthly | moving_average |
| trade_merchant:AV | 进出口差额3MMA | derived | monthly | moving_average |
| trade_merchant:AW | 涉外收付差额3MMA | derived | monthly | moving_average |
| trade_merchant:AX | 滚动3个月净结汇比例 | derived | monthly | ratio |
| trade_merchant:AY | 当月净结汇比例 | derived | monthly | ratio |
| trade_merchant:AZ | Column_AZ | derived | monthly | unknown |
| trade_merchant:B | 出口金额:当月值 | raw | monthly | monthly_amount |
| trade_merchant:BA | Column_BA | derived | monthly | unknown |
| trade_merchant:C | 境内银行代客涉外收入:货物贸易:当月值 | raw | monthly | monthly_amount |
| trade_merchant:D | 银行代客结汇:货物贸易:当月值 | raw | monthly | monthly_amount |
| trade_merchant:E | 进口金额:当月值 | raw | monthly | monthly_amount |
| trade_merchant:F | 境内银行代客涉外支出:货物贸易:当月值 | raw | monthly | monthly_amount |
| trade_merchant:G | 银行代客售汇:货物贸易:当月值 | raw | monthly | monthly_amount |
| trade_merchant:H | 顺差 | derived | monthly | net_flow |
| trade_merchant:K | 结汇/出口 | derived | monthly | ratio |
| trade_merchant:L | 结汇/收入 | derived | monthly | ratio |
| trade_merchant:M | 收入/出口 | derived | monthly | ratio |
| trade_merchant:N | 购汇/进口 | derived | monthly | ratio |
| trade_merchant:O | 购汇/支出 | derived | monthly | ratio |
| trade_merchant:P | 支出/进口 | derived | monthly | ratio |
| trade_merchant:Q | 货物贸易收汇结汇率 Z-Score | derived | monthly | z_score |
| trade_merchant:R | 货物贸易付汇购汇率 Z-Score | derived | monthly | z_score |
| trade_merchant:T | 贸易顺差净结汇意愿 3M | derived | monthly | ratio_3m |
| trade_merchant:U | 收付顺差结汇意愿 3M | derived | monthly | ratio_3m |
| trade_merchant:V | 购汇/进口 3M | derived | monthly | ratio_3m |
| trade_merchant:W | 购汇/支出 3M | derived | monthly | ratio_3m |
| trade_merchant:X | 收付顺差净结汇意愿 | derived | monthly | ratio |
| trade_merchant:Y | 贸易顺差净结汇意愿 | derived | monthly | ratio |
