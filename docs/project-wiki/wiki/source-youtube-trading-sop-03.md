# 来源：YouTube 教学《Volume Profile 成交量分布图》

## 一句话定义

YouTube 视频 [wImxox0QYm8](https://www.youtube.com/watch?v=wImxox0QYm8) 系统讲解了 TradingView 中 **Volume Profile（成交量分布图，VP）** 指标组的五种类型、核心概念（POC、Value Area、VAH/VAL）及其在支撑/阻力、供需区识别中的应用。

## 为什么保留

Volume Profile 是“量能维度”的价格行为分析工具，与本项目已有的 K 线形态、趋势突破、开盘区间等策略可形成互补。理解 VP 有助于在 CSV/Excel 中增加“量能关键位”字段，或在 SQX 中开发基于成交量的过滤模块。

## 关键结论

### Volume Profile 与 Volume 的区别

| 指标 | 维度 | 含义 |
|------|------|------|
| Volume | 时间维度 | 某时间周期内的总成交量 |
| Volume Profile | 价格维度 | 某价格区间内的成交量分布 |

### 核心概念

| 术语 | 英文 | 含义 |
|------|------|------|
| POC | Point of Control | 控制点，成交量最大的价格水平 |
| VA | Value Area | 以 POC 为中心、占设定比例（默认 70%）成交量的区域 |
| VAH | Value Area High | 价值区域最高价 |
| VAL | Value Area Low | 价值区域最低价 |

### 五种 Volume Profile 指标

| 指标 | 用途 |
|------|------|
| Fixed Range Volume Profile | 观察任意选定价格范围的成交量分布 |
| Periodic Volume Profile | 观察一根或多根 K 线周期的成交量分布 |
| Session Volume Profile | 观察每个交易时段（日）的成交量分布 |
| Session Volume Profile HD | 更精细的日内成交量分布 |
| Visible Range Volume Profile (VPVR) | 自动显示当前可见图表范围的成交量分布 |

### 实战用法

- POC 所在位置常被视为支撑/阻力
- 密集成交区与其他关键位（斐波那契、供需区）重合时，确认效力更强
- 下跌趋势中 POC 持续下降 → 空头主导；POC 开始抬升 → 可能出现需求区
- 上涨趋势中 POC 持续抬升 → 多头主导；POC 首次下落 → 可能出现供给区

### 参数设置要点

- 行数（Rows）：越大越精细
- Value Area 数值：默认 70%，改 100% 显示全部，改 20% 以下只看最密集区
- VAH/VAL：打开后显示价值区域边界
- Width %：成交量柱宽度，主要影响美观

## 来源

- [[2026-06-23-youtube-trading-sop-03-transcript]]（原始字幕转录，逐句保留）
- 视频地址：https://www.youtube.com/watch?v=wImxox0QYm8

## 关联页面

- [[volume-profile]]
- [[trading-sop-normalized-macd-rsi-ma]]
- [[trading-sop-ema200-adx-stochrsi-atr]]
