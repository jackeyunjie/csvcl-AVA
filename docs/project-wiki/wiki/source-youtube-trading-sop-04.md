# 来源：YouTube 交易 SOP《Impulse MACD 两种高胜率策略》

## 一句话定义

YouTube 视频 [pI1D2lpJCOk](https://www.youtube.com/watch?v=pI1D2lpJCOk) 介绍了基于 **Impulse MACD** 指标的两种交易策略：一是结合手动超买超卖线的金叉/死叉入场；二是结合成交量支撑阻力区的颜色反转入场。

## 为什么保留

Impulse MACD 被描述为“MACD 的终极版本”，其在盘整区间会趋于平坦，能有效过滤假突破。提取这两种策略有助于丰富本项目的信号库，并研究如何在 SQX/MQL5 中实现基于动量指标的多策略模块。

## 关键结论

### 策略一：Impulse MACD + 超买超卖线

**工具设置**

| 元素 | 设置 |
|------|------|
| 脉冲线（Pulse） | 绿色，线形图 |
| 柱状图（Histo） | 红色，柱状图 |
| 信号线（Signal） | 黄色，线形图 |
| 超买/超卖线 | 手动添加水平线 |

**多头入场**

1. 在超卖区，绿色脉冲线上穿黄色信号线，形成金叉
2. 金叉对应的关键 K 线收盘价入场

**空头入场**

1. 在超买区，绿色脉冲线下穿黄色信号线，形成死叉
2. 死叉对应的关键 K 线收盘价入场

### 策略二：Impulse MACD + 成交量支撑阻力区

**工具设置**

| 元素 | 设置 |
|------|------|
| 脉冲线（Pulse） | 柱状图 |
| Histo | 蓝色，柱状图 |
| 信号线（Signal） | 黄色，线形图 |
| Volume-based Support & Resistance Zones | 显示 4H 和日线支撑阻力（1H 交易时） |

**多头入场**

1. Impulse MACD 柱状图在零线下方由红变绿
2. 对应 K 线回踩到支撑区域
3. 两个条件满足后，关键 K 线收盘价入场

**空头入场**

1. Impulse MACD 柱状图在零线上方由蓝变黄
2. 对应 K 线回抽到阻力区域
3. 两个条件满足后，关键 K 线收盘价入场

### 通用风控

- 止损：关键 K 线外侧，或前波段高低点
- 止盈：分批止盈，1:1 出一部分，剩余博取更高利润

## 来源

- [[2026-06-23-youtube-trading-sop-04-transcript]]（原始字幕转录，逐句保留）
- 视频地址：https://www.youtube.com/watch?v=pI1D2lpJCOk

## 关联页面

- [[trading-sop-impulse-macd]]
- [[sqx-module-mapping-impulse-macd]]
- [[volume-profile]]
