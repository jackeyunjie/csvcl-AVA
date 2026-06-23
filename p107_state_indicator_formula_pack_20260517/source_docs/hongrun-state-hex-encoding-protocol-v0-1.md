# Hongrun State Hex Encoding Protocol v0.1

日期：2026-05-17

## 1. 定位

`state_hex` 是 Hermass / 弘运系统当前 state-first 主线中的核心状态编码。

它用于把单一周期的市场状态压缩成一个可组合、可切窗、可展示的编码。  
它不是线性强弱分数，也不是交易许可。

核心用途：

1. 多周期状态展示：`D_state_hex` / `W_state_hex` / `M_state_hex`。
2. 状态池主键：`pool_id = W1:{W_state_hex}|MN1:{M_state_hex}`。
3. State-Regime Walk-Forward（状态组合窗口验证）的状态窗切分。
4. 普通消费者页面的“月周日同状态”解释。
5. H1/M15/M5 独立系统里的高周期 context 编码。

## 2. 源码事实源

当前编码实现来自：

```text
data/mac_handoff_audit_20260508/source/ea_market_state.py
```

核心函数：

```text
calc_state_score(compression, trend, position, volatility)
to_signed_hex(value)
```

相关构建脚本会把 `state_score` 转成 `state_hex`。

## 3. 编码结构

`state_score` 是一个带方向符号的 bit mask（位掩码）。

绝对值由 4 个部分组成：

| bit | 数值 | 中文含义 | 来源层 |
|---:|---:|---|---|
| base | 0 或 8 | 收缩底座 / 非收缩底座 | compression / trend |
| bit 0 | 1 | 幅动活跃 | volatility |
| bit 1 | 2 | 关键位 / 突破位置触发 | position |
| bit 2 | 4 | 趋势触发 | trend |

即：

```text
abs(state_score) = base(0 or 8) + volatility_bit(1) + position_bit(2) + trend_bit(4)
```

方向由 trend / position 决定：

```text
bear_context 且没有 bull_context -> state_score 为负数
其他情况 -> state_score 为非负数
```

`state_hex` 是 `state_score` 的十六进制显示：

```text
state_score = 15  -> state_hex = F
state_score = 8   -> state_hex = 8
state_score = 7   -> state_hex = 7
state_score = -15 -> state_hex = -F
```

## 4. 0 与 8 是底座，不是强弱等级

`0` 和 `8` 是互斥底座。

| 底座 | 含义 |
|---:|---|
| 0 | contraction / closed storage，收缩或闭藏底座 |
| 8 | non-contraction，非收缩底座 |

因此：

```text
7  = 0 + 1 + 2 + 4
F  = 8 + 1 + 2 + 4
```

`7` 不一定比 `8` 弱，`F` 也不代表“可以买”。  
它们只是不同状态组件的组合。

## 5. 组件含义

### 5.1 volatility bit = 1

含义：

```text
幅动活跃
```

当前实现：

- 优先由 `classify_tbd` 判断。
- 如果没有 ATR percent 相关字段，则由 compression 的扩张状态兜底。

常见解释：

```text
市场幅动开始活跃，波动状态不再中性。
```

### 5.2 position bit = 2

含义：

```text
价格相对关键位出现位置触发
```

当前实现来自：

```text
classify_position(close, support, resistance)
```

典型 position：

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

只有 bull / bear 明确位置触发会贡献 bit 2。

### 5.3 trend bit = 4

含义：

```text
趋势触发
```

当前实现来自：

```text
classify_trend(adx, plus_di, minus_di)
```

典型 trend：

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

只有包含 bull / bear 的 trend 会贡献 bit 4。

### 5.4 base = 0 / 8

当前实现：

```text
is_contraction = compression == "closed" or trend == "closed"
magnitude = 0 if is_contraction else 8
```

这意味着：

- 如果处于 closed / contraction 语境，底座为 0。
- 否则底座为 8。

## 6. 方向符号

方向不是单独一个 bit，而是 `state_score` 的正负号。

当前实现：

```text
bull_context = trend contains "bull" OR position is bull-side
bear_context = trend contains "bear" OR position is bear-side

if bear_context and not bull_context:
    state_score = -magnitude
else:
    state_score = magnitude
```

因此：

- `F`：多向或非空向语境下，非收缩底座 + 1/2/4 全部触发。
- `-F`：空向语境下，非收缩底座 + 1/2/4 全部触发。
- `8`：非收缩底座，无 1/2/4 组件触发。
- `0`：收缩/闭藏底座，无 1/2/4 组件触发。

## 7. 常见编码表

| state_hex | state_score | 解释 |
|---|---:|---|
| 0 | 0 | 收缩/闭藏底座，无额外组件 |
| 1 | 1 | 收缩底座 + 幅动活跃 |
| 2 | 2 | 收缩底座 + 位置触发 |
| 3 | 3 | 收缩底座 + 幅动活跃 + 位置触发 |
| 4 | 4 | 收缩底座 + 趋势触发 |
| 5 | 5 | 收缩底座 + 幅动活跃 + 趋势触发 |
| 6 | 6 | 收缩底座 + 位置触发 + 趋势触发 |
| 7 | 7 | 收缩底座 + 幅动活跃 + 位置触发 + 趋势触发 |
| 8 | 8 | 非收缩底座，无额外组件 |
| 9 | 9 | 非收缩底座 + 幅动活跃 |
| A | 10 | 非收缩底座 + 位置触发 |
| B | 11 | 非收缩底座 + 幅动活跃 + 位置触发 |
| C | 12 | 非收缩底座 + 趋势触发 |
| D | 13 | 非收缩底座 + 幅动活跃 + 趋势触发 |
| E | 14 | 非收缩底座 + 位置触发 + 趋势触发 |
| F | 15 | 非收缩底座 + 幅动活跃 + 位置触发 + 趋势触发 |
| -F | -15 | 空向语境下的 F |

负号版本同理，例如：

```text
-E = 空向语境下的 14
-7 = 空向语境下的 7
```

## 8. 正向、负向、veto 语义

当前若用于多头策略的高周期支持 / 阻断，常见集合为：

```text
positive values:
2, 3, 6, 7, 10, 11, 14, 15

veto values:
-2, -3, -6, -7, -10, -11, -14, -15
```

注意：

1. 这是多头策略语境下的支持 / 阻断。
2. 不是所有策略族都使用同一支持集合。
3. 如果未来引入空头策略，veto 条件需要反向定义。
4. H1/M15/M5 独立系统必须重新验证这些集合是否适用。

## 9. 与旧 chaos_code 的区别

`chaos_code` 是历史核心语言和先验资产。  
`state_hex` 是当前 state-first 主线里的状态编码。

二者不能混用。

主要区别：

| 项目 | chaos_code | state_hex |
|---|---|---|
| 定位 | 历史混沌值编码 / prior evidence | 当前 state-first 状态编码 |
| 组件 | ATR / SR / trend / squeeze 等历史组件 | base + volatility + position + trend |
| 表达 | 数字组合 | 带方向符号的十六进制 |
| 当前用途 | 历史证据、审计资产 | 状态池、as-of context、P17 切窗 |
| 是否许可动作 | 否 | 否 |

## 10. 与多周期系统的关系

单周期：

```text
D_state_hex
W_state_hex
M_state_hex
```

多周期组合：

```text
mwd_hex = M_state_hex + W_state_hex + D_state_hex
```

状态池主键通常使用高周期：

```text
pool_id = W1:{W_state_hex}|MN1:{M_state_hex}
```

原因：

```text
P17 主裁决看 W1/MN1 大周期状态组合
D1 或 H1 是基准周期事件/观察层
```

## 11. 与 base-timeframe native 的关系

每个周期视角都必须用自己的 timestamp/close 独立计算高周期 context。

例如：

```text
D1 Agent：用 D1 timestamp / D1 close 生成 MN1/W1/D1 @ D1_view
H1 Agent：用 H1 timestamp / H1 close 生成 MN1/W1/D1/H4/H1 @ H1_view
M15 Agent：用 M15 timestamp / M15 close 生成 MN1/W1/D1/H4/H1/M30/M15 @ M15_view
```

不能把 D1 视角 state_hex 直接下沉给 H1/M15/M5。

## 12. 对前端与用户的解释

前端可以解释：

```text
F = 当前周期处于非收缩底座，并同时出现幅动、位置、趋势三类组件。
```

不要解释为：

```text
F = 最强，可以买
```

推荐普通用户解释：

```text
这个编码不是分数，而是体检报告。它告诉我们当前价格状态里有哪些组件同时出现：波动、关键位、趋势，以及是否处于收缩底座。
```

## 13. 禁止事项

1. 不把 `state_hex` 当线性强弱分数。
2. 不把 `F` 写成必然更好。
3. 不把 `state_hex` 写成交易许可。
4. 不把 `state_hex` 和旧 `chaos_code` 混为一谈。
5. 不跳过 as-of 审计。
6. 不把 D1 的 state_hex 直接用于 H1/M15/M5 的原生裁决。
7. 不用 Time-Drift Audit 替代 State-Regime Walk-Forward。
