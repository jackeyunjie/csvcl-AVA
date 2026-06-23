# P107 State Hex 编码规则说明

日期：2026-05-17

## 1. 一句话解释

`state_hex` 是弘运系统当前 state-first 主线的状态编码。

它不是线性强弱分数，也不是行动许可。  
它是把某一个周期的市场状态压缩成一个十六进制体检码。

完整概念源：

```text
wiki/concepts/hongrun-state-hex-encoding-protocol-v0-1.md
```

## 2. 编码结构

`state_score` 由 4 个部分组成：

```text
state_score = base(0 或 8) + volatility(1) + position(2) + trend(4)
```

然后转成十六进制：

```text
state_score = 15 -> state_hex = F
state_score = 8  -> state_hex = 8
state_score = -15 -> state_hex = -F
```

## 3. 四个组件

| 组件 | 数值 | 中文含义 |
|---|---:|---|
| base | 0 或 8 | 收缩底座 / 非收缩底座 |
| volatility | 1 | 幅动活跃 |
| position | 2 | 关键位 / 突破位置触发 |
| trend | 4 | 趋势触发 |

所以：

```text
F = 8 + 1 + 2 + 4
7 = 0 + 1 + 2 + 4
```

`F` 和 `7` 不是强弱排序，而是不同底座下的组件组合。

## 4. 正负号

正负号表示方向语境。

```text
F  = 多向或非空向语境
-F = 空向语境
```

方向来自趋势和关键位位置：

- trend 包含 bull，或 position 在上方/向上突破 -> 多向语境。
- trend 包含 bear，或 position 在下方/向下突破 -> 空向语境。

## 5. 常见编码

| state_hex | 含义 |
|---|---|
| 0 | 收缩/闭藏底座，无额外组件 |
| 1 | 收缩底座 + 幅动活跃 |
| 2 | 收缩底座 + 位置触发 |
| 4 | 收缩底座 + 趋势触发 |
| 7 | 收缩底座 + 幅动活跃 + 位置触发 + 趋势触发 |
| 8 | 非收缩底座，无额外组件 |
| 9 | 非收缩底座 + 幅动活跃 |
| A | 非收缩底座 + 位置触发 |
| C | 非收缩底座 + 趋势触发 |
| F | 非收缩底座 + 幅动活跃 + 位置触发 + 趋势触发 |
| -F | 空向语境下的 F |

## 6. P93 为什么筛 M/W/D 都是 F

P93 普通消费者版使用：

```text
M_state_hex = F
W_state_hex = F
D_state_hex = F
```

它的意思是：

```text
月线、周线、日线都处于非收缩底座，并同时出现幅动、位置、趋势三类组件。
```

它不等于：

```text
一定上涨
可以直接买
最强分数
策略已经验证
```

正确解释：

```text
这是一个非常明确的状态观察条件，适合进入观察池和后续策略适配验证。
```

## 7. 与状态池的关系

State-Regime Walk-Forward 的主裁决按高周期状态组合切窗。

常见状态池主键：

```text
pool_id = W1:{W_state_hex}|MN1:{M_state_hex}
```

例如：

```text
pool_id = W1:F|MN1:F
pool_id = W1:8|MN1:F
pool_id = W1:-E|MN1:8
```

这意味着策略要在对应大周期状态池里被验证，而不是只按日历时间回测。

## 8. 与 D1/H1/M15 独立视角 Agent 的关系

`state_hex` 必须在每个周期视角 Agent 里独立生成。周期（structure timeframe）和周期视角（viewpoint）是正交维度。

中文含义：

```text
D1、H1、M15、M5 都是独立视角 Agent。
```

例如：

```text
D1 Agent：D1 timestamp / D1 close 作为视角基准，输出 MN1/W1/D1 @ D1_view
H1 Agent：H1 timestamp / H1 close 作为视角基准，输出 MN1/W1/D1/H4/H1 @ H1_view
M15 Agent：M15 timestamp / M15 close 作为视角基准，输出 MN1/W1/D1/H4/H1/M30/M15 @ M15_view
```

不能把 D1 的原生视角 state_hex 直接下沉给 H1。H1 视角下的 D1 state 使用 D1 结构指标，但 position 使用 H1 close vs D1 SR。

## 9. 与资金流的关系

资金流不是 state_hex 的组成部分。

顺序应该是：

```text
state_hex 先定义价格状态
资金流再作为 energy-increment 能量增量证据
```

资金流可以帮助解释：

- 有没有资金关注。
- 成交是否活跃。
- 是否出现主买/主卖分化。
- 是否接近筹码峰压力区。

但不能替代 state_hex。

## 10. 禁止误读

禁止：

1. 把 `state_hex` 当线性分数。
2. 把 `F` 当成“最强一定好”。
3. 把 `state_hex` 当成买卖许可。
4. 把旧 `chaos_code` 和 `state_hex` 混用。
5. 把 D1 的 state_hex 直接下沉给 H1。
6. 用时间切分替代 State-Regime Walk-Forward。

推荐表达：

```text
state_hex 是体检码，不是分数。
F 代表状态组件齐全，不代表行动结论。
状态池验证决定策略是否具备进一步研究价值。
```
