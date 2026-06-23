# SQX 模块映射：EMA200 + ADX + Stoch RSI 趋势策略

## 一句话定义

将 YouTube 第二个交易 SOP（EMA 200 4H + ADX 50 + Stoch RSI + ATR 止损）拆解为 **StrategyQuant X (SQX)** 中的指标、条件、入场、出场模块组合。

## 为什么重要

该策略强调“趋势方向 + 趋势强度 + 超买超卖入场”三层过滤，非常适合用 SQX 的条件模块清晰表达。程序化后可回测不同品种、周期，并接入本项目的 CSV/邮件报告流程。

## SQX 模块拆分

### 1. 指标模块（Indicators）

| SQX 指标 | 参数 | 对应视频指标 |
|----------|------|--------------|
| EMA | Period = 200, Timeframe = 4H | EMA 200 趋势判断 |
| ADX | Period = 14, Level = 50 | 趋势强度过滤 |
| Stoch RSI | 默认参数 | 超买/超卖区入场 |
| ATR Stop / ATR | Period = 8 | 动态止损 |

> 注意：EMA 200 需要跨周期引用（4H 周期应用在 1H 图表上）。SQX 支持多时间框架指标。

### 2. 入场条件模块（Entry Conditions）

#### 多头入场

```text
Close > EMA(200) on 4H
AND ADX > 50
AND Stoch RSI K crosses above Stoch RSI D
AND Stoch RSI D < 20 (oversold zone)
```

#### 空头入场

```text
Close < EMA(200) on 4H
AND ADX > 50
AND Stoch RSI K crosses below Stoch RSI D
AND Stoch RSI D > 80 (overbought zone)
```

### 3. 入场动作模块（Entry Order）

| 设置 | 建议值 |
|------|--------|
| 入场类型 | Market at Close of Signal Candle |
| 方向 | Long / Short based on conditions |

### 4. 出场模块（Exit Conditions）

#### 止损（Stop Loss）

| 方向 | SQX 设置 |
|------|----------|
| 多 | ATR Stop below signal candle low |
| 空 | ATR Stop above signal candle high |

> 若 SQX 没有直接对应 ATR Stop Loss Finder，可用 `ATR * multiplier` 或 `Signal candle low - ATR(8)` 近似。

#### 止盈（Take Profit）

| 批次 | 方案 | SQX 设置 |
|------|------|----------|
| 第一批 | 1:1 风险回报比 | Fixed R:R = 1.0 |
| 第二批 | 利润奔跑 | Trailing Stop / ATR Trailing |

### 5. 过滤模块（Filters）

- **趋势过滤**：EMA 200 方向决定只做多或只做空
- **强度过滤**：ADX > 50 排除弱势行情
- **区域过滤**：Stoch RSI 只在超买/超卖区触发

## 与第一个 SOP 的对比

| 维度 | SOP 01（MACD + RSI/MA + MA13） | SOP 02（EMA200 + ADX + Stoch RSI） |
|------|----------------------------------|-------------------------------------|
| 趋势判断 | MA 13 | EMA 200（4H） |
| 强度过滤 | 无 | ADX > 50 |
| 入场触发 | MACD + RSI 金叉/死叉 | Stoch RSI 超买/超卖区金叉/死叉 |
| 止损 | 近期高低点 / 关键 K 线外侧 | ATR 动态止损 |
| 适用行情 | 趋势启动/动量 | 强趋势中的回调入场 |

## 与本项目 CSV/Excel 流程的结合

1. SQX 生成 MQL5 EA 并导出到 MT5
2. MT5 运行时输出信号/状态到 CSV
3. 本项目扫描 CSV，对 EMA 方向、ADX 强度、Stoch RSI 信号列着色
4. 生成邮件报告与截图

## 关联页面

- [[trading-sop-ema200-adx-stochrsi-atr]]
- [[source-youtube-trading-sop-02]]
- [[sqx-module-mapping]]
