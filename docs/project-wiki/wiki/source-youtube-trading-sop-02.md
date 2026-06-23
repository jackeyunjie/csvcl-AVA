# 来源：YouTube 交易 SOP《EMA200 + ADX + Stoch RSI 趋势策略》

## 一句话定义

YouTube 视频 [gfEqy4uGe8c](https://www.youtube.com/watch?v=gfEqy4uGe8c) 介绍了一套针对震荡行情过滤、趋势入场时机优化的 BTC/USD 1小时交易系统，使用 **EMA 200（4H）+ ADX（50）+ Stoch RSI + ATR Stop Loss Finder** 四指标共振。

## 为什么保留

该策略与第一个 SOP 形成互补：第一个偏日内动量突破，这个偏趋势强度过滤。提取其完整规则有助于构建多元化的信号库，并研究不同过滤条件对胜率/赔率的影响。

## 关键结论

### 工具清单

| 指标 | 参数 | 作用 |
|------|------|------|
| EMA（指数移动平均线） | 长度 200，周期 4H | 判断主趋势方向 |
| ADX and DI | 只保留 ADX 线，参数等级 50 | 衡量趋势强度 |
| Stoch RSI | 默认参数 | 在超买/超卖区寻找入场时机 |
| ATR Stop Loss Finder | 长度 8 | 动态止损 |

### 多头入场条件（必须全部满足）

1. 价格处于 EMA 200（4H）上方
2. ADX 线处于 50 上方
3. Stoch RSI 蓝色 K 线在超卖区由下向上穿过黄色 D 线，形成金叉

**关键 K 线**：金叉对应的 K 线
**入场价**：关键 K 线收盘价
**止损**：关键 K 线对应的 ATR 蓝线下方
**止盈**：分批止盈，1:1 出一部分，剩余博取利润

### 空头入场条件（必须全部满足）

1. 价格处于 EMA 200（4H）下方
2. ADX 线处于 50 上方
3. Stoch RSI 蓝色 K 线在超买区由上向下穿过黄色 D 线，形成死叉

**关键 K 线**：死叉对应的 K 线
**入场价**：关键 K 线收盘价
**止损**：关键 K 线对应的 ATR 红线上方
**止盈**：分批止盈

### 核心理念

- 用 EMA 200 过滤大趋势方向
- 用 ADX > 50 过滤弱势/震荡行情
- 用 Stoch RSI 在超买/超卖区寻找高概率入场点
- ATR 动态止损适应波动率

## 来源

- [[2026-06-23-youtube-trading-sop-02-transcript]]（原始字幕转录，逐句保留）
- 视频地址：https://www.youtube.com/watch?v=gfEqy4uGe8c

## 关联页面

- [[trading-sop-ema200-adx-stochrsi-atr]]
- [[sqx-module-mapping-ema200-adx-stochrsi]]
- [[trading-sop-normalized-macd-rsi-ma]]
