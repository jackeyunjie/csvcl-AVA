# 成交量分布图（Volume Profile, VP）

## 一句话定义

成交量分布图（Volume Profile）是一种横向显示成交量在价格上分布的指标，用于识别市场中成交量最大、买卖双方最认可的价格区域，从而判断支撑/阻力、供需区以及潜在反转点。

## 为什么重要

传统成交量指标按时间展示，只能知道“什么时候交易活跃”；Volume Profile 按价格展示，能知道“在什么价格交易活跃”。这对识别关键价位、确认支撑阻力、过滤假突破具有独特价值。

## 具体内容

### 与传统 Volume 的区别

```text
Volume:        时间 → 成交量
Volume Profile: 价格 → 成交量
```

### 核心概念

| 术语 | 全称 | 含义 |
|------|------|------|
| POC | Point of Control | 控制点，成交量最大的价格 |
| VA | Value Area | 价值区域，通常指占总量 70% 成交量的价格区间 |
| VAH | Value Area High | 价值区域上沿 |
| VAL | Value Area Low | 价值区域下沿 |

### 五种 VP 类型

| 类型 | 适用场景 |
|------|----------|
| Fixed Range Volume Profile | 自定义范围，如某段单边行情、震荡箱体 |
| Periodic Volume Profile | 按 K 线周期，如 7 根 K 线、7 天 |
| Session Volume Profile | 按交易时段，常用于识别日内的 POC 变化 |
| Session Volume Profile HD | 更精细的日内 VP |
| Visible Range Volume Profile (VPVR) | 自动适配当前可见图表范围 |

### 实战逻辑

#### 支撑与阻力

- POC 是买卖双方最认可的价格，常成为强支撑/阻力
- 价格首次接近 POC 时，通常难以一次突破，会震荡或反转

#### 供需区识别

- 下跌趋势中 POC 连续下降 → 空头主导
- POC 停止下降并开始抬升 → 可能出现需求区（多头吸筹）
- 上涨趋势中 POC 连续抬升 → 多头主导
- POC 首次下落 → 可能出现供给区（多头派发）

#### 与其他指标共振

当 VP 的关键位与以下工具重合时，信号更可靠：

- 斐波那契回撤位（如 0.382、0.5、0.618）
- 供给需求区
- 移动平均线
- K 线形态（头肩顶、双顶等）
- MACD 背离

### 参数设置建议

| 参数 | 默认值 | 调整建议 |
|------|--------|----------|
| Rows（行数） | 24 | 增加到 100 更精细 |
| Value Area | 70% | 100% 看全部，<20% 只看最密集区 |
| VAH/VAL | 关闭 | 建议打开，显示价值区域边界 |
| Width % | 30% | 影响美观，不影响分析 |

## 与本项目的结合

- 可在 CSV 输出中增加 `POC`、`VAH`、`VAL` 字段
- 价格接近 POC/VAH/VAL 时，可标记为“量能关键位”并着色
- 与本项目已有的 K 线形态、突破策略结合，提高入场确定性

## 关联页面

- [[source-youtube-trading-sop-03]]
- [[trading-sop-normalized-macd-rsi-ma]]
- [[trading-sop-ema200-adx-stochrsi-atr]]
- [[candle-range-theory]]
- [[mql5-kline-patterns]]

## 来源

- [[2026-06-23-youtube-trading-sop-03-transcript]]
