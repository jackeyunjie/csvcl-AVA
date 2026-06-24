# SQX 模块映射：Vegas 隧道交易系统

## 一句话定义

将 YouTube 第 16 个视频中的 **Vegas 隧道交易系统** 拆解为 **StrategyQuant X (SQX)** 的指标、条件、入场、出场模块组合。

## SQX 模块拆分

### 1. 指标模块（Indicators）

| SQX 指标 | 参数 | 对应视频指标 |
|----------|------|--------------|
| EMA | Period 144 | EMA 144（隧道上轨） |
| EMA | Period 169 | EMA 169（隧道下轨） |
| EMA | Period 576 | EMA 576（长期趋势上轨） |
| EMA | Period 676 | EMA 676（长期趋势下轨） |
| EMA | Period 12 | EMA 12（过滤线） |
| Volume Oscillator | Short=1, Long=14 | Volume Osc 短线/长线 |

### 2. 入场条件模块（Entry Conditions）

#### 多头入场

```text
EMA(144) > EMA(576)
AND EMA(169) > EMA(676)
AND Close < EMA(144) AND Close > EMA(169)  // 价格位于隧道内或附近
AND EMA(12) > EMA(144)
```

#### 空头入场

```text
EMA(144) < EMA(576)
AND EMA(169) < EMA(676)
AND Close > EMA(144) AND Close < EMA(169)  // 价格位于隧道内或附近
AND EMA(12) < EMA(144)
```

### 3. 入场动作模块（Entry Order）

| 设置 | 建议值 |
|------|--------|
| 入场类型 | Limit Order 在隧道区间内；或 Next Bar Open |
| 方向 | Long / Short |
| 订单拆分 | 同一价格区间拆成 2–3 个小单 |

### 4. 出场模块（Exit Conditions）

#### 止损（Stop Loss）

| 方案 | SQX 设置 |
|------|----------|
| Volume Osc 确认止损 | Volume Oscillator > 144（多头）时平仓 |
| 24h 时间止损 | 自定义时间条件 + 未回到隧道上方则平仓 |
| EMA 676 硬止损 | Close < EMA(676)（多头）时平仓 |
| 短期低点止损 | ATR 或近期低点作为动态止损 |

#### 止盈（Take Profit）

| 批次 | 方案 | SQX 设置 |
|------|------|----------|
| 第一批 | R:R = 1:1 | 止盈位 = 入场价 + 1×止损距离 |
| 第二批 | 趋势跟踪 | Close 跌破 EMA(676) 或 Volume Osc 确认反转时平仓 |

### 5. 过滤模块（Filters）

- 大趋势过滤：EMA 144/169 与 EMA 576/676 必须同向排列。
- 过滤线过滤：EMA12 必须位于隧道同侧。
- 震荡过滤：若隧道与长期均线缠绕（如 EMA144 与 EMA576 差值小于 ATR×0.5）→ 禁止入场。
- 单趋势加仓次数 ≤ 2 次。

## 参数优化建议

| 参数 | 优化范围 | 说明 |
|------|----------|------|
| Volume Osc 零线 | 89 / 144 | <1H 用 89，≥1H 用 144 |
| EMA 隧道周期 | (144,169) ~ (150,180) | 保持 1.17 倍左右比例 |
| 大趋势线周期 | (576,676) | 四倍于隧道周期 |
| 震荡过滤阈值 | 0.3~1.0 × ATR | 越小越严格 |

## 代码输出方向

### MQL5 (MT5)

- 使用 `iMA` 获取 EMA 序列；自定义 `VolumeOscillator` 指标或调用 `iCustom`。
- 在 `OnTick` 中检查趋势排列与回踩条件。
- 使用 `CTrade` 进行分批次入场；用 `PositionModify` 移动止损。
- 将信号状态写入 `MQL5/Files/...csv`，供 Python 着色流程读取。

### MQL4 (MT4)

- 使用 `iMA` 计算 EMA；自定义 Volume Osc 或简化用 `iVolumes` 差值。
- 在 `OnTick` 或 `start()` 中执行入场逻辑。
- 使用 `OrderSend`、`OrderModify`、`OrderClose` 管理订单。
- 输出 CSV 到 `MQL4/Files/...csv`。

### Python

- 数据源：`yfinance` / CCXT / akshare / tushare。
- 回测框架：Backtrader / VectorBT。
- 实现要点：
  - 用 `pandas`/`pandas-ta` 计算 EMA 与 Volume Osc。
  - 定义回调入场信号、分层止损逻辑、分批止盈逻辑。
  - 输出信号 CSV：`signal,ema144,ema169,ema576,ema676,ema12,vol_osc` 等。

## 与本项目 CSV/Excel 流程的结合

1. SQX 生成 MQL5 EA 导出到 MT5。
2. MT5 输出信号状态到 CSV，例如：
   - `trend_state`：多头/空头/震荡
   - `entry_signal`：0 / 1 / -1
   - `stop_level`：EMA676 或短期低点
3. 本项目对以下字段着色：
   - 趋势状态列（红/绿）
   - 入场信号列（黄/红/绿）
   - 止损触发列（红）
4. 生成 `_colored.xlsx`、截图与邮件报告。

## 关联页面

- [[trading-sop-vegas-tunnel-system]]
- [[vegas-tunnel-system]]
- [[source-youtube-trading-sop-16]]
- [[sqx-module-mapping]]
