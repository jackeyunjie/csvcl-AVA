# 交易 SOP：Impulse MACD 两种策略

## 适用场景

- 品种：BTC/USD 等加密货币，可测试外汇、指数
- 周期：1 小时（策略一默认），15 分钟（策略二示例）
- 风格：动量反转 + 关键位共振

## 策略一：Impulse MACD + 超买超卖线

### 工具设置

| 元素 | 参数/样式 |
|------|-----------|
| Impulse MACD 脉冲线 | 绿色，线形图 |
| Impulse MACD Histo | 红色，柱状图 |
| Impulse MACD 信号线 | 黄色，线形图 |
| 超买线 | 手动水平线（前期死叉不易到达的位置） |
| 超卖线 | 与超买线对称的负值位置 |

### 多头入场

1. 绿色脉冲线在超卖区上穿黄色信号线（金叉）
2. 金叉对应的关键 K 线收盘价 > 入场位置

### 空头入场

1. 绿色脉冲线在超买区下穿黄色信号线（死叉）
2. 死叉对应的关键 K 线收盘价 < 入场位置

### 止损

- 多：关键 K 线下方，或前波段低点
- 空：关键 K 线上方，或前波段高点

### 止盈

- 第一批：1:1 风险回报比
- 第二批：继续持有，让利润奔跑

---

## 策略二：Impulse MACD + 成交量支撑阻力区

### 工具设置

| 元素 | 参数/样式 |
|------|-----------|
| Impulse MACD 脉冲线 | 柱状图 |
| Impulse MACD Histo | 蓝色，柱状图 |
| Impulse MACD 信号线 | 黄色，线形图 |
| Volume-based Support & Resistance Zones | 交易 1H 时显示 4H + 日线 |

### 多头入场

1. Impulse MACD 柱状图在零线下方由红变绿
2. 对应 K 线回踩到支撑区域
3. 关键 K 线收盘价入场

### 空头入场

1. Impulse MACD 柱状图在零线上方由蓝变黄
2. 对应 K 线回抽到阻力区域
3. 关键 K 线收盘价入场

### 止损

- 多：支撑区域下方，或波段低点
- 空：阻力区域上方，或波段高点

### 止盈

- 第一批：1:1 风险回报比
- 第二批：拿到上方阻力/下方支撑位置

---

## 注意事项

- Impulse MACD 在零线附近趋于平坦时，表明市场处于盘整，应减少交易频次
- 单一指标信号较片面，建议结合关键支撑/阻力、K 线形态、其他指标共振确认
- 使用前务必对目标品种回测至少 500 次以上，统计数据建立信任
- 交易需要持续复盘优化和实战，不能一蹴而就

## 关联页面

- [[source-youtube-trading-sop-04]]
- [[sqx-module-mapping-impulse-macd]]
- [[trading-process-umar-ashraf]]
- [[six-stage-market-cycle]]
- [[three-part-position-sizing]]
- [[market-temperature-seasons]]
- [[crypto-bull-market-buy-strategy]]
- [[crypto-whale-coin-identification]]
- [[crypto-risk-warnings]]
- [[volume-profile]]
- [[trading-sop-normalized-macd-rsi-ma]]
- [[trading-sop-ema200-adx-stochrsi-atr]]
- [[trading-sop-hong-inki-theme-momentum]]
