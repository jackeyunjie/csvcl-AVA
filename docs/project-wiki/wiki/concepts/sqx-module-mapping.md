# SQX 模块映射：交易 SOP 的策略实现

## 一句话定义

将 YouTube 交易 SOP（NORMALIZED MACD + RSI 21/SMA 55 + MA 13）拆解为 **StrategyQuant X (SQX)** 中的指标、条件、入场、出场模块组合，实现可回测、可优化的程序化策略。

## 为什么重要

手动执行三条件共振策略容易受情绪影响。通过 SQX 模块化实现后：

- 可以回测不同品种、周期、参数
- 可以自动生成 MQL5/MQL4 代码
- 可以接入本项目的 CSV/Excel 处理流程
- 可以批量优化止损止盈方案

## SQX 模块拆分

### 1. 指标模块（Indicators）

| SQX 指标 | 参数 | 对应视频指标 |
|----------|------|--------------|
| MACD / Normalized MACD | Fast = 13 | N/MACD |
| RSI | Period = 21 | RSI 白线 |
| SMA (应用于 RSI) | Period = 55 | RSI 红线 |
| SMA / EMA | Period = 13 | MA 13 趋势线 |

> 若 SQX 内置没有 Normalized MACD，可用标准 MACD 替代，或导入自定义指标。

### 2. 入场条件模块（Entry Conditions）

#### 多头入场

```text
MACD Line crosses above MACD Signal Line
AND RSI(21) crosses above SMA(RSI, 55)
AND Close > SMA(13)
```

#### 空头入场

```text
MACD Line crosses below MACD Signal Line
AND RSI(21) crosses below SMA(RSI, 55)
AND Close < SMA(13)
```

### 3. 入场动作模块（Entry Order）

| 设置 | 建议值 |
|------|--------|
| 入场类型 | Market at Close of Signal Candle |
| 方向 | Long / Short based on conditions |

> 视频强调在关键 K 线收盘价入场，因此入场模式应选择“信号 K 线收盘后下一根开盘市价入场”或“收盘限价单”。

### 4. 出场模块（Exit Conditions）

#### 止损（Stop Loss）

| 方案 | SQX 设置 |
|------|----------|
| 近期低点/高点 | ATR Stop / Swing Low-High Stop |
| 关键 K 线外 | Stop below/above entry candle |

#### 止盈（Take Profit）

| 批次 | 方案 | SQX 设置 |
|------|------|----------|
| 第一批 | 1:1 风险回报比 | Fixed R:R = 1.0 |
| 第二批 | 利润奔跑 | Trailing Stop / ATR Trailing |

> SQX 可通过 Partial Close 模块实现分批平仓。

### 5. 过滤模块（Filters）

- 趋势过滤：`Close > SMA(13)` 只做多；`Close < SMA(13)` 只做空
- 波动过滤：可加入 ATR 阈值，避免极低波动时段入场
- 时间过滤：可限定交易时段（如亚盘、欧盘、美盘）

## 与本项目 CSV/Excel 流程的结合

1. SQX 生成的 MQL5 EA 导出到 MT5
2. MT5 运行时输出状态码/信号到 CSV
3. 本项目 `process_real_mt4_data.py` 扫描 CSV
4. 对信号列按本项目颜色规则着色
5. 生成邮件报告或截图

## 关联页面

- [[trading-sop-normalized-macd-rsi-ma]]
- [[source-youtube-trading-sop]]
- [[trading-sop-ema200-adx-stochrsi-atr]]
- [[sqx-module-mapping-ema200-adx-stochrsi]]
- [[mql5-kline-patterns]]
- [[sqx-module-mapping-impulse-macd]]
- [[sqx-module-mapping-hong-inki-theme-momentum]]

## 来源

- [[2026-06-23-youtube-trading-sop-transcript]]
