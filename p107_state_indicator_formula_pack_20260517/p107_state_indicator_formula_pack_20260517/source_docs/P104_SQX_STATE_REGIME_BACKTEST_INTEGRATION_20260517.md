# P104 SQX 与 State-Regime 回测集成说明

日期：2026-05-17

## 1. 总结论

SQX 可以用于 Hermass 的市场分状态回测，但定位必须清楚：

```text
Hermass 负责切状态池
SQX 负责在状态池里执行策略回测
Hermass 再负责汇总状态窗裁决
```

SQX 不能替代 Hermass 的 State-Regime Walk-Forward 主裁决。

SQX 很适合做：

1. 策略回测执行。
2. 参数优化。
3. Walk-Forward Matrix 展示借鉴。
4. Monte Carlo 鲁棒性测试。
5. 多市场批量测试。
6. 策略工厂和策略实验。

但 Hermass 的核心是：

```text
按 W1/MN1 状态组合切窗
同状态跨年份拼接
Time-Drift Audit 只做旁路审计
```

因此，SQX 是外部回测引擎，不是状态裁决大脑。

## 2. 推荐架构

### 2.1 Hermass 生成状态池

Hermass 先根据 D1/H1/M15 等 base timeframe 的原生状态系统，生成状态池。

示例：

```text
pool_id = W1:F|MN1:F
pool_id = W1:8|MN1:F
pool_id = W1:0|MN1:8
```

每个状态池可以导出为单独 CSV：

```text
AAPL_H1_pool_W1F_MN1F.csv
MSFT_H1_pool_W1F_MN1F.csv
```

### 2.2 SQX 执行策略回测

将状态池 CSV 导入 SQX，在 SQX 中测试策略族：

1. VCP。
2. Turtle / 海龟。
3. Bollinger Pirate / 布林强盗。
4. 25/60。
5. Donchian。
6. Pivot / ACD reference。

SQX 输出每个策略在每个状态池中的回测结果。

### 2.3 Hermass 汇总状态窗裁决

SQX 回测结果导回 Hermass 后，由 Hermass 汇总：

```text
strategy
symbol
pool_id
parameter_set
sample_count
coverage_status
state_pool_result
time_drift_audit_status
monte_carlo_status
research_only_flag
```

最终裁决仍然由 Hermass 完成。

## 3. 为什么不能直接用 SQX 的 Walk-Forward 替代 P17

SQX 的 Walk-Forward 默认是传统时间切分。

Hermass 的 State-Regime Walk-Forward 是状态组合窗口验证：

```text
主裁决 = 按 W1/MN1 大周期状态组合切窗
旁路审计 = Time-Drift Audit
```

这两者不是同一件事。

传统时间切分回答的是：

```text
这个策略在不同时间段是否稳定？
```

Hermass 状态切分回答的是：

```text
这个策略是否只在某类市场状态里具备研究价值？
```

因此，SQX 的 Walk-Forward Matrix 可以借鉴展示方式和鲁棒性思想，但不能替代 P17 的状态主裁决。

## 4. 状态池 CSV 的关键风险

Hermass 的状态池可能把不同年份的同状态片段拼接到一起。

这正是 State-Regime Walk-Forward 的核心价值，但导入 SQX 时要小心：

```text
SQX 可能把拼接后的片段当成连续时间序列
```

这会影响：

1. 指标 warmup。
2. 隔夜处理。
3. 持仓跨段。
4. 滑点和成本。
5. segment 之间的虚假连续性。

## 5. 解决方案

### 5.1 每个 segment 单独回测

最稳妥方式：

```text
每个状态片段单独导出
每个状态片段单独回测
Hermass 汇总片段结果
```

优点：

- 不产生虚假连续时间。
- 不跨 segment 持有。
- 指标 warmup 更清楚。

缺点：

- 文件数量多。
- SQX 批处理复杂度上升。

### 5.2 拼接时加入 gap

如果必须拼接，可以在 segment 之间加入明显 gap，并强制：

```text
flat-at-segment-end
```

中文含义：每个状态片段结束时强制归零，不允许跨片段持有。

### 5.3 使用 segment_id

每条数据必须带：

```text
segment_id
pool_id
source_start_time
source_end_time
```

如果 SQX 无法识别这些字段，至少要在导出文件和结果文件中保留映射。

## 6. 推荐执行路线

第一阶段：

```text
P1：Hermass 导出状态池 CSV
P2：SQX 跑单策略 + 单状态池
P3：SQX 导出结果 CSV
P4：Hermass 导回结果
P5：Hermass 生成 State-Regime Matrix
```

第二阶段：

```text
P6：引入 Time-Drift Audit
P7：引入 Monte Carlo
P8：引入参数邻域审计
P9：生成研究报告卡
```

## 7. 适合先试的最小实验

建议先用一个最小实验验证链路：

```text
市场：美股
标的：AAPL
周期：H1
状态池：W1:F|MN1:F 或当前样本最多的 pool
策略：Donchian / Turtle 简化版
输出：SQX 回测结果 CSV
汇总：Hermass 生成状态池结果表
```

这个实验只验证：

1. 状态池 CSV 能否导入 SQX。
2. SQX 能否跑策略。
3. 结果能否导回 Hermass。
4. Hermass 能否按 pool_id 汇总。

不用于对外展示策略有效性。

## 8. 数据字段建议

Hermass 导给 SQX 的 CSV 至少包含：

```text
datetime
open
high
low
close
volume
symbol
pool_id
segment_id
base_timeframe
source_start_time
source_end_time
research_only_flag
```

如果 SQX 只能识别标准 OHLCV，则 metadata 另存：

```text
sqx_export_manifest.json
```

## 9. SQX 结果导回字段

SQX 结果导回 Hermass 时，建议字段：

```text
strategy_name
symbol
base_timeframe
pool_id
segment_id
parameter_set
sample_count
trade_count
net_profit
drawdown
profit_factor
monte_carlo_status
source_file
research_only_flag
```

注意：这些字段进入 Hermass 后仍然是研究层结果，不直接构成用户行动建议。

## 10. 边界

1. SQX 是回测执行层，不是状态裁决层。
2. SQX 的时间切分 Walk-Forward 不替代 Hermass 的 State-Regime Walk-Forward。
3. Time-Drift Audit 是旁路审计，不替代状态窗主裁决。
4. 状态池拼接必须处理 segment 边界。
5. SQX 结果导回 Hermass 后仍然需要语义审计。
6. 对普通用户展示时，应表达为“历史同状态研究模拟”，不表达为收益承诺或交易建议。

