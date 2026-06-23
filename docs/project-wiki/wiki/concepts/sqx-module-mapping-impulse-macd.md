# SQX 模块映射：Impulse MACD 策略

## 一句话定义

将 YouTube 第四个视频中的两种 Impulse MACD 交易策略拆解为 **StrategyQuant X (SQX)** 的指标、条件、入场、出场模块组合。

## 策略一：Impulse MACD + 超买超卖线

### 指标模块

| SQX 指标 | 参数 | 说明 |
|----------|------|------|
| Impulse MACD | 默认 | 若 SQX 无内置，需导入自定义指标 |
| 水平线 | 手动或动态阈值 | 超买/超卖边界 |

### 入场条件

#### 多头

```text
Impulse MACD Pulse crosses above Signal Line
AND Pulse < OversoldLevel
```

#### 空头

```text
Impulse MACD Pulse crosses below Signal Line
AND Pulse > OverboughtLevel
```

### 动态超买超卖设置

由于视频中超买超卖线是手动目测的，SQX 中可替换为：

- 近期 N 根 K 线的 Pulse 极值（如最高/最低 5%）
- 固定百分位阈值（如 ±0.5 标准差）
- ATR 倍数阈值

---

## 策略二：Impulse MACD + 成交量支撑阻力区

### 指标模块

| SQX 指标 | 参数 | 说明 |
|----------|------|------|
| Impulse MACD Histo | 默认 | 柱状图颜色变化 |
| Volume-based Support/Resistance | 多时间框架 | 4H + 日线（1H 交易时） |

### 入场条件

#### 多头

```text
Impulse MACD Histo was red below zero and turns green
AND Close is inside or near Support Zone
```

#### 空头

```text
Impulse MACD Histo was blue above zero and turns yellow
AND Close is inside or near Resistance Zone
```

> 注：颜色定义需根据 TradingView 原指标对应。SQX 中通常用 Histo 数值由负转正/由正转负来模拟颜色变化。

---

## 通用出场模块

### 止损

| 方案 | SQX 设置 |
|------|----------|
| 关键 K 线外侧 | Stop below/above signal candle |
| 波段高低点 | Swing Low/High Stop |
| 支撑阻力区外侧 | Stop below support / above resistance |

### 止盈

| 批次 | 方案 | SQX 设置 |
|------|------|----------|
| 第一批 | 1:1 风险回报比 | Fixed R:R = 1.0 |
| 第二批 | 利润奔跑 | Trailing Stop / Target at next S/R zone |

---

## 盘整过滤

Impulse MACD 的特性：Pulse 和 Signal 在零线附近趋于平坦时，市场处于盘整。

SQX 过滤条件：

```text
ABS(Pulse - Signal) > Threshold
OR ABS(Pulse) > Threshold
```

避免在 Pulse/Signal 差值过小时入场。

---

## 与本项目 CSV/Excel 流程的结合

1. SQX 生成 MQL5 EA 导出到 MT5
2. MT5 输出信号状态到 CSV
3. 本项目对以下字段着色：
   - Pulse/Signal 交叉状态
   - 超买超卖区位置
   - 支撑阻力区命中状态
   - 关键 K 线收盘价位置
4. 生成邮件报告与截图

## 关联页面

- [[trading-sop-impulse-macd]]
- [[source-youtube-trading-sop-04]]
- [[volume-profile]]
