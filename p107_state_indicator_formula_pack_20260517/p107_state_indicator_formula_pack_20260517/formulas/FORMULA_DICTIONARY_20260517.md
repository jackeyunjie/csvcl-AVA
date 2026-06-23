# 指标计算公式字典

日期：2026-05-17

## 1. 基础价格字段

| 字段 | 公式 / 含义 |
|---|---|
| open | 开盘价 |
| high | 最高价 |
| low | 最低价 |
| close | 收盘价 |
| volume | 成交量；MT5 外汇/CFD 中常是 tick volume |
| amount | 成交额 |

OHLC 合法性：

```text
open > 0
high > 0
low > 0
close > 0
high >= low
high >= open
high >= close
low <= open
low <= close
```

## 2. True Range 与 ATR

True Range：

```text
TR = max(
  high - low,
  abs(high - previous_close),
  abs(low - previous_close)
)
```

ATR(14)：

```text
ATR_14 = rolling_mean(TR, 14)
```

ATR stop 参考：

```text
atr_stop_price = close - 3 * ATR_14
```

注意：ATR stop 是策略参考字段，不等于执行指令。

## 3. ADX / DI 趋势指标

基础方向：

```text
+DM = high_t - high_{t-1}, 若其大于 low_{t-1} - low_t 且为正，否则 0
-DM = low_{t-1} - low_t, 若其大于 high_t - high_{t-1} 且为正，否则 0
```

方向指标：

```text
+DI = 100 * smoothed(+DM) / ATR
-DI = 100 * smoothed(-DM) / ATR
DX  = 100 * abs(+DI - -DI) / (+DI + -DI)
ADX = smoothed(DX)
```

Hermass 趋势分类使用：

```text
ADX
+DI
-DI
```

典型状态：

```text
bull_start
bull_trend
bull_hidden
bear_start
bear_trend
bear_hidden
closed
flat_hidden
contraction
neutral
```

## 4. Bollinger Bands 布林带

中轨：

```text
BB_MID_N = rolling_mean(close, N)
```

标准差：

```text
BB_STD_N = rolling_std(close, N)
```

上轨 / 下轨：

```text
BB_UPPER = BB_MID_N + k * BB_STD_N
BB_LOWER = BB_MID_N - k * BB_STD_N
```

常用：

```text
N = 20
k = 2
```

带宽：

```text
BB_WIDTH = (BB_UPPER - BB_LOWER) / BB_MID_N
```

%B：

```text
BBP = (close - BB_LOWER) / (BB_UPPER - BB_LOWER)
```

布林强盗常用观察：

```text
bandwidth_squeeze = BB_WIDTH 位于历史低分位
band_expansion = BB_WIDTH 开始扩张
close_outside_band = close > BB_UPPER 或 close < BB_LOWER
```

## 5. Kaufman Width / 压缩宽度

Hermass 状态压缩层会比较：

```text
kaufman_width_20
bb_width_20
bb_width_50
kaufman_width_50
```

典型状态：

```text
closed
expansion_start
expansion
strong_expansion
contraction_start
contraction
neutral
```

## 6. state_score / state_hex

核心公式：

```text
state_score = base(0 或 8) + volatility(1) + position(2) + trend(4)
state_hex = signed_hex(state_score)
```

底座：

```text
base = 0  若 compression == closed 或 trend == closed
base = 8  其他情况
```

组件：

```text
volatility = 1 若 volatility != neutral
position   = 2 若 position 属于明确上方/下方/突破
trend      = 4 若 trend 包含 bull 或 bear
```

方向：

```text
若 bear_context 且没有 bull_context，则 state_score 为负
否则 state_score 为非负
```

示例：

```text
F  = 15  = 8 + 1 + 2 + 4
7  = 7   = 0 + 1 + 2 + 4
-F = -15 = 空向语境下的 F
```

## 7. 支撑 / 阻力与位置层

position 使用 close 与 support / resistance 判断。

典型状态：

```text
above_extreme
above
break_up
below_extreme
below
break_down
near_resistance
near_support
neutral
```

支阻间距：

```text
sr_width_pct = (resistance - support) / close * 100
```

支阻间距分位：

```text
sr_width_rank_120 = percentile_rank(sr_width_pct, 120)
```

## 8. Pivot 枢轴

N 窗口高低点：

```text
high_N = rolling_max(high, N)
low_N  = rolling_min(low, N)
```

Pivot：

```text
pivot_N = (high_N + low_N + close) / 3
pivot_N_low = (pivot_N + low_N) / 2
pivot_N_high = (pivot_N + high_N) / 2
pivot_N_width_pct = (pivot_N_high - pivot_N_low) / close * 100
```

常见 N：

```text
1K
3K
6K
```

## 9. Donchian / Turtle 海龟

N 周期通道：

```text
donchian_high_N = rolling_max(high, N).shift(1)
donchian_low_N  = rolling_min(low, N).shift(1)
```

突破候选：

```text
high_break_candidate = close > donchian_high_N
low_break_candidate  = close < donchian_low_N
```

常见：

```text
20 / 55 breakout
10 / 20 channel boundary
```

必须使用 shift(1)，避免当前 K 线读取自己的高低点。

## 10. VCP Price-Only

VCP 中文：波动收缩形态。

price-only 首版只用价格，不使用量能。

需要：

```text
swing_high
swing_low
contraction_leg_width
range_narrowing
breakout_reference
invalidation_reference
```

收缩段：

```text
leg_width_i = swing_high_i - swing_low_i
range_narrowing = leg_width_i < leg_width_{i-1}
```

必须标记：

```text
energy_increment_deferred = true
```

## 11. 25/60

D1：

```text
MA_25_D1 = rolling_mean(close, 25 trading days)
MA_60_D1 = rolling_mean(close, 60 trading days)
```

H1：

```text
MA_25_H1 = rolling_mean(close, 25 H1 bars)
MA_60_H1 = rolling_mean(close, 60 H1 bars)
```

注意：

```text
H1 的 25/60 bars 不等于 D1 的 25/60 trading days
```

必须分开注册。

## 12. 6-day / 6-session Axis

D1：

```text
six_day_high = rolling_max(high, 6).shift(1)
six_day_low  = rolling_min(low, 6).shift(1)
six_day_mid  = (six_day_high + six_day_low) / 2
six_day_range = six_day_high - six_day_low
```

H1：

```text
使用前 6 个 completed sessions
不能读取当前 session 尚未完成的信息
```

## 13. 换手率

如果供应商直接提供：

```text
turnover_rate = supplier_turnover_rate
```

如果需要自算：

```text
turnover_rate = volume / float_share
```

自由流通换手：

```text
turnover_rate_free = volume / free_float_share
```

没有 `float_share` 或 `free_float_share` 时，不得伪造换手率。

## 14. 成交额活跃度

20 日平均成交额：

```text
avg_amount_20d = rolling_mean(amount, 20)
avg_amount_20d_yi = avg_amount_20d / 100000000
```

成交额只做 liquidity confirmation（流动性确认），不做主裁决。

## 15. 资金流

主力净流入：

```text
main_net_inflow = super_large_net_inflow + large_net_inflow
```

主动净买：

```text
active_net_amount = active_buy_amount - active_sell_amount
```

大小单背离：

```text
large_small_divergence = large_net_inflow - small_net_inflow
```

连续性：

```text
main_persistence_3d = rolling_sum(main_net_inflow > 0, 3)
main_persistence_5d = rolling_sum(main_net_inflow > 0, 5)
```

资金流只做 energy-increment（能量增量证据），不替代 price/state 主裁决。

## 16. 筹码峰

筹码峰是成本分布观察，不是资金流本身。

距离主要筹码峰：

```text
chip_peak_distance_pct = (close - chip_peak_price) / close * 100
```

集中度：

```text
chip_concentration_score = supplier_defined 或基于成本分布计算
```

必须记录供应商口径。

## 17. State-Regime Walk-Forward

状态池主键：

```text
pool_id = W1:{W_state_hex}|MN1:{M_state_hex}
```

主裁决：

```text
按 W1/MN1 状态组合切窗
```

旁路：

```text
Time-Drift Audit 只检查时间漂移，不替代状态窗主裁决
```

## 18. 禁止事项

1. 不把 `state_hex` 当线性强弱分数。
2. 不把资金流当买入理由。
3. 不把换手率当主裁决。
4. 不把 H1 的 25/60 当 D1 的 25/60。
5. 不跳过 shift(1) / strict-prior as-of。
6. 不把结果层字段混入原语空跑。

