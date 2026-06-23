# 多周期共振收缩突破研究总结、审计与系统路线图

日期: 2026-06-05

## 一句话结论

多周期共振收缩突破 v2 已完成样本扩展和 H1/H4/D1 共振研究闭环，但当前结果仍只能作为“观察系统与研究方向”的依据，不能作为实盘交易策略。下一阶段重点不是继续扩大参数扫描，而是修正 as-of 多周期对齐、真实事件去重、short 目标判断、交易成本和 walk-forward 回测，然后再搭建实盘观察系统。

## 当前交付物

代码与报告:

- `squeeze_multi_timeframe_research.py`: 多周期共振收缩突破研究模块。
- `reports/squeeze/squeeze_mt_research_20260605_1215.md`: v2 研究报告。
- `reports/squeeze/squeeze_mt_samples_20260605_1215.csv`: v2 样本明细。
- `reports/squeeze/squeeze_mt_param_sweep_20260605_1215.csv`: 72 组参数扫描结果。
- `python/analytics/multi_timeframe_squeeze.py`: 多周期收缩观察与共振突破信号框架。
- `test_multi_timeframe_breakout.py`: 合成数据 smoke test，命令 `python .\MT5_AI_Trading\test_multi_timeframe_breakout.py` 通过。

v2 报告核心数据:

| 指标 | 数值 |
|---|---:|
| 品种数 | 24 |
| 回看周期 | 365 天 |
| 周期 | H1/H4/D1 |
| Setup 数 | 7928 |
| 报告突破样本 | 5608 |
| 报告突破率 | 70.7% |
| 报告 5bar 胜率 | 49.1% |
| 报告盈亏比 | 1.22 |
| 报告期望 | 0.019% |
| 报告顺势胜率 | 50.7% |
| 报告逆势胜率 | 47.6% |
| 验证状态 | 逻辑需要调整 |

## 复核后的关键发现

### 1. v2 样本规模确实扩大，但唯一事件口径仍需修正

报告中 `unique_breakouts=5608` 来自 `cluster_id` 去重，但当前 `cluster_id` 是 `symbol + setup timestamp hour`，本质上仍是 setup 级 ID，不是真实突破事件 ID。

按 `symbol + breakout_timestamp + breakout_direction` 复核:

| 指标 | 复核值 |
|---|---:|
| CSV 总行数 | 5608 |
| 实际唯一突破键 | 3520 |
| 重复突破键数量 | 1249 |
| 重复键内样本行数 | 3337 |
| 单一突破最大重复计入 | 5 |

按真实突破键简单去重后的粗略绩效:

| 指标 | 去重后估算 |
|---|---:|
| 唯一突破事件 | 3520 |
| 5bar 胜率 | 48.9% |
| 平均 PNL | 0.019% |
| 平均盈利 | 0.258% |
| 平均亏损 | -0.209% |
| 盈亏比 | 1.23 |
| 入场后止损率 | 14.6% |

结论: 样本量仍足够大，但不能使用当前报告的 `unique_breakouts=5608` 作为独立事件数。

### 2. 多周期趋势存在未来信息泄漏风险

`squeeze_multi_timeframe_research.py` 当前在 `_compute_trend_bias()` 中对完整 H4/D1 数据一次性计算趋势，再把同一个 H4/D1 bias 赋给全部 H1 setup。这样过去样本会看到未来的 H4/D1 收盘信息，属于 look-ahead bias。

必须改为 as-of 对齐:

- 对每个 H1 setup timestamp，只能使用该时间之前已经收盘的 H4/D1 bar。
- H4/D1 趋势应逐 bar 预计算，再用 `merge_asof` 或时间戳索引映射。
- 不允许用 `i // 4`、`i // 24` 这类假设映射跨周期数据，尤其对外汇、指数、商品、加密货币混合品种。

### 3. short 方向目标判断仍未修正

代码注释写了“修正short方向”，但实现仍为:

```python
(entry_price - future_prices['low']).min() >= abs(target)
```

short 方向应使用最大有利波动:

```python
(entry_price - future_prices['low']).max() >= abs(target)
```

这会影响 1R/2R/3R 达成率和目标质量评估。

### 4. 当前多周期共振有效性只能算弱正向

报告口径:

- 顺势胜率 50.7%
- 逆势胜率 47.6%

按真实突破键去重后的粗略口径:

| 类型 | 唯一事件 | 胜率 | 平均 PNL |
|---|---:|---:|---:|
| with_trend | 2058 | 49.4% | 0.026% |
| against_trend | 606 | 49.2% | 0.024% |
| neutral | 856 | 47.4% | 0.001% |

趋势共振的平均 PNL 好于 neutral，但胜率优势不明显。考虑到当前有未来信息泄漏风险，不能把“共振有效”作为实盘结论，只能作为下一轮无泄漏回测的假设。

### 5. 指标重复计分问题仍存在

`compute_pivot_range()` 与 `compute_sr_range()` 目前仍高度等价，`Pivot` 和 `SR` 同时进入 score，会放大结构收缩得分。下一版应只保留一个区间收缩指标，或重定义 Pivot 为真正的 pivot band/central pivot 变化。

### 6. 当前还没有交易级回测

v2 仍是事件收益统计，不是完整交易系统回测。缺少:

- 点差、滑点、手续费、隔夜成本。
- 入场/出场执行规则。
- 仓位管理和风险预算。
- 单品种最大同时持仓限制。
- 信号冲突处理。
- walk-forward 和 out-of-sample。
- 模拟盘执行记录对比。

## 多周期共振收缩观察系统设计

系统应拆成四层，而不是把研究脚本直接改成实盘:

### 1. 数据层

职责:

- 获取 H1/H4/D1，未来可扩展 M15/W1。
- 统一品种元数据，包括交易时段、点值、最小跳动、spread、合约规格。
- 保存每根 bar 的数据版本和采集时间。

最低要求:

- 所有跨周期数据必须 as-of 对齐。
- 每个信号记录使用的 H4/D1 bar timestamp 必须可追溯。
- 数据缺口、异常跳价、非交易时段必须标记。

### 2. 观察层

职责:

- 每个周期独立计算收缩状态，不直接产生交易。
- 输出结构化事实: squeeze_score、结构收缩、ADX低值、趋势方向、最近收缩距离、突破状态。
- 不使用未来数据，不跨周期偷看。

建议字段:

- `symbol`
- `timeframe`
- `bar_time`
- `squeeze_score`
- `structural_squeeze_score`
- `bb_squeezed`
- `range_squeezed`
- `adx_bucket`
- `trend_bias`
- `trend_strength`
- `last_squeeze_bars_ago`
- `breakout_direction`
- `breakout_strength`

### 3. 共振机会层

职责:

- 聚合 H1/H4/D1 观察事实。
- 识别机会阶段，而不是直接下单。

机会阶段建议:

| 阶段 | 含义 | 动作 |
|---|---|---|
| none | 无收缩无突破 | 忽略 |
| squeeze_setup | H1 或多周期收缩出现 | 加入观察列表 |
| leading_breakout | H1 已突破，高周期未确认 | 低优先级观察 |
| resonant_breakout | H1 突破且 H4/D1 趋势同向或不冲突 | 进入交易候选 |
| conflicted_breakout | H1 突破但 H4/D1 强反向 | 过滤或只做复盘 |

候选交易必须输出:

- `event_id`
- `setup_id`
- `cluster_id`
- `direction`
- `entry_rule`
- `stop_rule`
- `target_rule`
- `trend_alignment`
- `confidence`
- `risk_reward`
- `invalidation_reason`

### 4. 执行层

职责:

- 只接收通过回测验证的候选规则。
- 先模拟盘，不直接实盘。
- 记录每次信号、订单、成交、撤单、滑点和复盘结果。

实盘前置:

- 信号生成和订单执行必须解耦。
- 默认人工确认。
- 最大风险、最大持仓、最大日亏损硬编码保护。
- 失败时只允许降级为观察，不允许自动加仓。

## 共振突破交易机会规则草案

### 入选条件

基础条件:

- H1 出现收缩 setup。
- setup 后 `max_wait_bars` 内发生突破。
- 突破阈值使用真实 ATR 或改名为 anchor multiple。
- H4/D1 不得同时强烈反向。

趋势共振条件:

- long: H4 或 D1 为 bullish，且另一个不是 strong bearish。
- short: H4 或 D1 为 bearish，且另一个不是 strong bullish。
- neutral 高周期可允许，但降低 confidence。

过滤条件:

- 排除真实事件样本中持续负期望品种，至少先剔除 AUDUSD、GBPJPY、XAUUSD、EURGBP、USDCHF、USDCAD。
- 对样本不足的 XAGUSD 暂不纳入交易池。
- 优先观察 UKOIL、ETHUSD、US30、BTCUSD、NAS100、UK100、GER40、USOIL，但必须先做无泄漏回测。

### 出场规则候选

至少回测三组:

- 固定持有: 入场后 5bar/10bar。
- 结构止损: anchor opposite side。
- 1R/2R 分批: 1R 减仓，剩余用 H1 trailing stop。

注意:

- 当前 1R 达成率偏低，不能直接假设 R 多目标优于固定持有。
- 需要区分 MFE/MAE 与真实执行出场。

## 回测系统搭建路线

### P0: 修正研究口径

1. 新增 `squeeze_multi_timeframe_research_v3.py`。
2. 使用 as-of H4/D1 对齐。
3. 使用真实 `event_id = symbol + breakout_timestamp + direction + breakout_level_bucket` 去重。
4. 修复 short target。
5. 改名或修正 `min_breakout_atr`。
6. 去掉 Pivot/SR 重复计分。
7. 生成 raw setup、event、trade 三套 CSV。
8. 增加单元测试覆盖上述问题。

### P1: 交易级回测

1. 新增交易模拟器，不再只统计事件收益。
2. 加入成本模型。
3. 加入仓位和风控。
4. 输出交易列表、权益曲线、回撤、分品种表现。
5. 做 train/validation/test 或 walk-forward。

### P2: 实盘观察系统

1. 建立定时扫描任务。
2. 每小时生成 H1/H4/D1 共振观察表。
3. 把候选机会写入日报或 Obsidian。
4. 模拟盘记录每个候选信号的后续表现。
5. 累积至少 4 周观察数据后再评估是否允许人工确认交易。

## 实盘准入门槛

模拟盘观察门槛:

- 无泄漏真实事件数 >= 3000。
- 加入成本后 net expectancy > 0。
- walk-forward 测试段仍为正。
- with_trend 明显优于 neutral/against，且 bootstrap CI 支持。
- 每个入选品种真实事件数 >= 80。
- 至少 4 周模拟盘记录与回测偏差可解释。

实盘自动交易门槛:

- 当前阶段不允许直接进入。
- 先从人工确认、低频、单品种白名单开始。
- 单笔风险、日内最大亏损、最大持仓、最大滑点必须硬限制。
- 任何数据缺口或时间戳异常时自动停止交易，只保留观察。

## 下一步执行建议

第一优先级不是“继续扩大样本”，而是把 v2 的统计口径修成 v3:

1. as-of 多周期对齐。
2. 真实突破事件去重。
3. short 目标判断修复。
4. 指标重复计分处理。
5. 成本和 walk-forward。

完成 v3 后再决定是否进入“模拟盘观察系统”。当前 v2 的价值是证明系统能跑通、样本能扩大、多周期共振值得继续研究；它还没有证明策略可交易。

