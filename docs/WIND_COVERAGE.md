# Wind EDB Coverage

> 最后更新：2026-06-22

## 概述

本文档追踪每个 raw 序列的 Wind EDB 映射状态。

## 映射状态定义

| 状态 | 含义 |
|------|------|
| `verified` | Wind EDB 查询结果与 Excel 缓存值完全匹配 |
| `verified_with_transform` | 匹配但需要变换（单位缩放、符号反转等） |
| `mapping_pending` | 已从 Excel 指标名称提取候选映射，待 Wind MCP 验证 |
| `unsupported` | 该序列不是 Wind EDB 数据（手工维护、政策参数等） |
| `no_result` | Wind EDB 查询无返回结果 |
| `manual` | 人工维护序列，不需要 Wind 映射 |

## 总体覆盖

- **Raw 序列总数：** 150（不含日期列 :A）
- **已提取 Wind 指标名：** 141（94%）
- **已验证映射：** 0（待 Wind MCP 可用）
- **Mapping pending：** 141
- **无指标名（需人工）：** 9

## 按模块覆盖

| 模块 | Raw 序列 | 有 Wind 指标名 | Mapping Pending | 缺失 |
|------|----------|---------------|-----------------|------|
| 3.即远期 | 15 | 15 | 15 | 0 |
| 3.代客即期 | 17 | 17 | 17 | 0 |
| 3.涉外收付 | 23 | 22 | 22 | 1 (fx_crossborder:AN) |
| 3.货物贸易 | 13 | 11 | 11 | 2 (trade_goods:AF, AY) |
| 3.贸易商 | 11 | 11 | 11 | 0 |
| 3.服务贸易 | 6 | 6 | 6 | 0 |
| 3.FDI | 28 | 27 | 27 | 1 (fdi:X) |
| 3.证券EQ | 10 | 10 | 10 | 0 |
| 3.证券FI | 27 | 22 | 22 | 5 (sec_fi:BE, BF, +3) |
| **合计** | **150** | **141** | **141** | **9** |

## Wind 指标命名规范

所有指标名称从 Excel 工作表的「指标名称」行提取，格式为：

```
{类别}:{子类别}:...:{频率}
```

示例：
- `银行自身结汇:当月值` → Wind EDB: `银行自身结汇:当月值`
- `出口金额:当月值` → Wind EDB: `出口金额:当月值`
- `中国:金融账户:非储备性质的金融账户:直接投资:差额:当季值` → Wind EDB (fully qualified)

## 缺失指标名的序列

以下 9 个序列在 Excel 中无指标名称头（可能为衍生列或内部引用列）：

| Series ID | Module | 说明 |
|-----------|--------|------|
| fdi:X | 3.FDI | 无指标名 |
| fx_cspot:AH | 3.代客即期 | 无指标名 |
| fx_cspot:BB | 3.代客即期 | 无指标名 |
| fx_crossborder:AN | 3.涉外收付 | 无指标名 |
| fx_crossborder:BH | 3.涉外收付 | 无指标名 |
| sec_fi:BE | 3.证券FI | 无指标名 |
| sec_fi:BF | 3.证券FI | 无指标名 |
| trade_goods:AF | 3.货物贸易 | 无指标名 |
| trade_goods:AY | 3.货物贸易 | 无指标名 |

这些需要人工查阅 Wind EDB 目录或原始 Excel 公式来确定映射。

## 验证流程（待 Wind MCP 可用）

对每个 `mapping_pending` 序列：

1. 使用 `wind_indicator` 查询 Wind EDB，取最近 3-5 个点
2. 与 Excel 缓存值比较最近 2 个可用点
3. 确认频率、单位、方向和日期标签一致
4. 通过 → 标记 `verified`
5. 需要变换 → 标记 `verified_with_transform`（记录变换公式）
6. 无结果 → 标记 `no_result` 并尝试变体查询
7. 确认不可用 → 标记 `unsupported`

## Wind EDB 查询方法

Wind MCP 预期接口（待配置）：

```
wsd(codes="{wind_indicator}", beginDate="{start}", endDate="{end}",
    options="period={frequency};unit={unit}")
```

常用参数：
- `period`: M (月), D (日), Q (季)
- `unit`: 1 (原始单位), 0.0001 (bps)
- `fill`: blank (不填充缺失)
