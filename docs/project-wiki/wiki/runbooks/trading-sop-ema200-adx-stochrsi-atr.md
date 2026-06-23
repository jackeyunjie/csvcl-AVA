# 交易 SOP：EMA 200 + ADX + Stoch RSI + ATR 止损

## 适用场景

- 品种：BTC/USD 等加密货币，可测试外汇、指数
- 主周期：1 小时
- 趋势周期：4 小时（EMA 200）
- 风格：趋势跟踪，强调趋势强度过滤

## 工具设置

### 1. EMA（指数移动平均线）

| 参数 | 设置值 | 作用 |
|------|--------|------|
| 长度 | 200 | 长期趋势判断 |
| 时间周期 | 4 小时 | 站在更高周期看趋势 |
| 颜色 | 浅蓝色 | 视觉区分 |

**信号**：价格相对于 EMA 200 的位置

### 2. ADX and DI

| 参数 | 设置值 | 作用 |
|------|--------|------|
| 显示 | 只保留 ADX 线 | 趋势强度 |
| 等级 | 50 | 强趋势阈值 |

**信号**：ADX > 50 表示趋势动能强劲，大概率延续

### 3. Stoch RSI（随机相对强弱指标）

| 参数 | 设置值 | 作用 |
|------|--------|------|
| 默认参数 | 不变 | 超买/超卖区入场 |
| K 线颜色 | 蓝色 | 快線 |
| D 线颜色 | 黄色 | 慢線 |

**信号**：
- 超卖区（20 以下）K 线上穿 D 线 → 金叉做多
- 超买区（80 以上）K 线下穿 D 线 → 死叉做空

### 4. ATR Stop Loss Finder

| 参数 | 设置值 | 作用 |
|------|--------|------|
| 长度 | 8 | 动态止损 |

**信号**：关键 K 线对应的 ATR 止损线位置

## 入场规则

### 多头入场

必须同时满足：

1. 当前价格 > EMA 200（4H）
2. ADX 线 > 50
3. Stoch RSI 蓝色 K 线在超卖区由下向上穿过黄色 D 线（金叉）

**入场价**：金叉对应的关键 K 线收盘价

### 空头入场

必须同时满足：

1. 当前价格 < EMA 200（4H）
2. ADX 线 > 50
3. Stoch RSI 蓝色 K 线在超买区由上向下穿过黄色 D 线（死叉）

**入场价**：死叉对应的关键 K 线收盘价

## 风险管理

### 止损

| 方向 | 止损位置 |
|------|----------|
| 多 | 关键 K 线对应的 ATR 蓝线下方 |
| 空 | 关键 K 线对应的 ATR 红线上方 |

### 止盈

- **第一批**：风险回报比 1:1 平仓一部分
- **第二批**：继续持有，让利润奔跑
- 可选：跟随 ATR 移动止损

## 操作流程

1. 打开 BTC/USD 1 小时图
2. 加载 EMA 200（绑定到 4H）
3. 加载 ADX，只显示 ADX 线，等级 50
4. 加载 Stoch RSI
5. 加载 ATR Stop Loss Finder，长度 8
6. 等待价格、ADX、Stoch RSI 三条件共振
7. 在关键 K 线收盘价入场
8. 设置 ATR 止损和分批止盈
9. 记录每笔交易，定期复盘

## 注意事项

- EMA 200 使用 4 小时周期，避免短期噪音
- ADX > 50 是强趋势过滤，可能错过温和趋势
- Stoch RSI 必须在超买/超卖区交叉才入场
- ATR 止损会根据波动率自动调整，避免固定点数止损的不适配

## 关联页面

- [[source-youtube-trading-sop-02]]
- [[sqx-module-mapping-ema200-adx-stochrsi]]
- [[trading-sop-normalized-macd-rsi-ma]]
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
