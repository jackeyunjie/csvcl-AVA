# 交易 SOP：NORMALIZED MACD + RSI 21/SMA 55 + MA 13

## 适用场景

- 品种：BTC/USD 等加密货币，也可测试外汇、指数
- 周期：1 小时（视频中默认），可回测其他周期
- 风格：趋势跟踪，三条件共振入场

## 工具设置

### 1. NORMALIZED MACD

| 参数 | 设置值 | 说明 |
|------|--------|------|
| Fast MA | 13 | 提高灵敏度，减少滞后 |
| Slow MA / Signal | 默认或参考视频 | 与 Fast MA 配合生成红/白线交叉 |

**信号**：红线与白线的金叉/死叉

### 2. 5 IN 1 指标（RSI + SMA）

| 参数 | 设置值 | 说明 |
|------|--------|------|
| RSI 周期 | 21 | 动量判断 |
| SMA 周期 | 55 | RSI 的平滑线 |
| RSI 颜色 | 白色 | 视觉清晰 |

**信号**：RSI 白线与红线的金叉/死叉

### 3. 移动平均线 MA

| 参数 | 设置值 | 说明 |
|------|--------|------|
| 周期 | 13 | 趋势过滤 |
| 颜色 | 蓝色 | 视觉区分 |

## 入场规则

### 多头入场

必须同时满足：

1. `N/MACD 红线` 由下向上穿过 `白线`
2. `RSI 白线` 由下向上穿过 `红线`（金叉）
3. 金叉对应的关键 K 线 `收盘价 > MA 13`

**入场价**：关键 K 线收盘价

### 空头入场

必须同时满足：

1. `N/MACD 红线` 由上向下穿过 `白线`
2. `RSI 白线` 由上向下穿过 `红线`（死叉）
3. 死叉对应的关键 K 线 `收盘价 < MA 13`

**入场价**：关键 K 线收盘价

## 风险管理

### 止损

| 场景 | 止损位置 |
|------|----------|
| 常规 | 近期波段低点（多）/ 高点（空） |
| 关键 K 线波动大 | 关键 K 线下方（多）/ 上方（空） |

### 止盈

- **第一批**：风险回报比 1:1 平仓一部分
- **第二批**：继续持有，博取趋势利润
- 可选：移动止损保护利润

## 操作流程

1. 打开 BTC/USD 1 小时图
2. 加载三个指标并按上述参数设置
3. 等待 N/MACD 与 RSI 同时出现金叉/死叉
4. 确认关键 K 线收盘价在 MA 13 上方/下方
5. 满足条件后在收盘价入场
6. 设置止损和分批止盈
7. 每日收盘后复盘信号质量

## 注意事项

- 必须三个条件同时满足，缺一不可
- 关键 K 线收盘价入场，避免盘中追单
- 高杠杆（如 10 倍）会放大风险，需严格控制仓位
- 建议先用历史数据回测，再小资金实盘验证

## 关联页面

- [[source-youtube-trading-sop]]
- [[sqx-module-mapping]]
- [[trading-sop-ema200-adx-stochrsi-atr]]
- [[sqx-module-mapping-ema200-adx-stochrsi]]
- [[trading-sop-impulse-macd]]
- [[sqx-module-mapping-impulse-macd]]
- [[trading-process-umar-ashraf]]
- [[six-stage-market-cycle]]
- [[three-part-position-sizing]]
- [[market-temperature-seasons]]
- [[crypto-bull-market-buy-strategy]]
- [[crypto-whale-coin-identification]]
- [[crypto-risk-warnings]]
- [[volume-profile]]
- [[mql5-kline-patterns]]
