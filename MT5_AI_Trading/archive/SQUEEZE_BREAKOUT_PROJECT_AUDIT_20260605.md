# 收缩突破项目进度审计与下一步建议

审计日期: 2026-06-05

## 一句话结论

收缩观测系统已经完成了从观测、样本生成、参数扫描到报告输出的研究闭环，但当前结果只能支持“继续研究观察器假设”，不能支持进入实盘自动交易。核心原因是胜率和期望偏弱，并且现有回测口径存在重复计样、止损窗口、目标判断、指标重复计分等需要修正的问题。

## 当前项目进度

已完成:

- `python/analytics/squeeze_observer.py`: 已实现 BB Width、Pivot Range、ADX、State、SR Range 等收缩观测框架。
- `squeeze_breakout_research.py`: 已实现从 MT5 获取 H1 OHLCV、识别收缩 setup、检测突破、生成统计报告和参数扫描。
- `reports/squeeze/squeeze_breakout_research_20260605_1105.md`: 已生成最新研究报告。
- `reports/squeeze/squeeze_breakout_samples_20260605_1105.csv`: 已输出 991 条突破样本明细。
- `reports/squeeze/squeeze_param_sweep_20260605_1105.csv`: 已输出 72 组参数扫描结果。
- `test_squeeze_breakout_research.py`: 11 个单元测试通过，验证了数据类和基础流程。
- 最新报告已同步到 Obsidian 的 `Trading/SqueezeObserver` 目录。

当前最好参数组合:

| 参数 | 当前最好值 |
|---|---:|
| min_squeeze_score | 3 |
| max_wait_bars | 30 |
| min_breakout_atr | 0.1 |
| require_structural | False |

当前最好组合表现:

| 指标 | 数值 |
|---|---:|
| Setup 数 | 1134 |
| 突破样本数 | 991 |
| 突破率 | 87.4% |
| 5bar 胜率 | 53.0% |
| 盈亏比 | 1.20 |
| 5bar 期望 | 0.038% |
| 1R 达成率 | 14.3% |
| 止损触发率 | 32.9% |
| 研究状态 | 逻辑需要调整 |

## 审计意见

### 1. 结论不能升级为“已验证有效”

当前最好组合只有 53.0% 的 5bar 胜率和 0.038% 的期望值，尚未覆盖点差、滑点、隔夜、交易时段差异和执行误差。10bar 胜率降至 49.2%，说明突破后优势不稳定。当前状态应维持为“逻辑需要调整”，不建议进入实盘自动交易。

### 2. 样本独立性不足，当前 991 条样本有重复突破计入

按 `symbol + breakout_timestamp + breakout_direction` 简单去重后，991 条突破样本约缩减为 672 个唯一突破键；有 210 个突破键被重复计入，重复样本合计 529 行，单个突破最多被计入 5 次。

简单去重后的粗略指标:

| 指标 | 去重后估算 |
|---|---:|
| 唯一突破键 | 672 |
| 5bar 胜率 | 51.0% |
| 平均 PNL | 0.024% |
| 盈亏比 | 1.16 |
| 止损率 | 31.4% |

这说明当前 53.0% 胜率和 0.038% 期望可能偏乐观。下一步必须按“事件簇”或“每品种同一突破只计一次”重建统计口径。

### 3. 止损统计窗口有明显口径风险

`detect_breakouts()` 当前在 setup 后的整个等待窗口里检查止损，而不是从 breakout entry 之后开始检查。这会把入场前触碰锚定区间另一侧的行情计为止损，导致止损率和风险统计失真。

建议修正为:

- 先确定突破入场 bar。
- 只在入场后的持仓窗口内检查 stop。
- 输出 `stop_after_entry`、`stop_before_entry_noise` 两类字段，避免混淆。

### 4. 1R/2R/3R 目标判断存在 short 方向错误

short 方向的目标判断使用了最小值逻辑，容易低估下跌方向目标达成率。应以 `entry_price - future_low` 的最大有利变动判断 short 目标是否达成。

### 5. `min_breakout_atr` 命名不准确

当前突破阈值实际是 `min_breakout_atr * anchor_range`，不是 ATR。报告中的“0.1 倍 ATR”容易误导。应二选一:

- 改名为 `min_breakout_anchor_multiple`。
- 或真正计算 ATR，并使用 `anchor_high + k * ATR` / `anchor_low - k * ATR`。

### 6. Pivot Range 和 SR Range 当前公式重复

`compute_pivot_range()` 与 `compute_sr_range()` 当前都等价于 rolling high-low 区间除以 close。这样 `Pivot` 和 `SR` 在 score 中高度重复，导致 squeeze_score 不是独立信号数量，`require_structural=True` 的过滤价值也被削弱。

建议:

- 若保留 SR，则 Pivot 应改为真正的 pivot point 变化或 pivot band 宽度。
- 或在 score 中只保留一个高低区间类指标，避免重复加分。

### 7. State=0 尚未进入突破研究逻辑

`SqueezeSetup.state_is_zero` 当前固定为 False，说明突破研究还没有纳入状态编码数据库中的 State=0 维度。若项目目标是验证 P107/Hermass 状态逻辑，下一轮必须接入状态库并按 state 分组。

### 8. 参数扫描仍是样本内优化

当前 72 组参数在同一批 180 天 H1 数据上扫描并择优，没有 train/validation/test 划分，也没有 walk-forward。最佳参数更像样本内最佳，而不是可迁移参数。

## 下一步建议

### 优先级 P0: 修正研究口径

1. 建立唯一事件模型:
   - 每个 symbol 的同一突破只计一次。
   - 为重复 setup 生成 `cluster_id`，保留 setup 明细，但绩效以 cluster/event 统计为主。

2. 修正突破交易逻辑:
   - 入场后再计算止损、目标、MFE、MAE。
   - 修复 short 方向 1R/2R/3R 目标判断。
   - 明确 1bar/5bar/10bar 是“入场后第 N 根”还是“含入场 bar”。

3. 修正指标定义:
   - 处理 Pivot 和 SR 重复计分。
   - 将 `min_breakout_atr` 改名或改成真实 ATR。
   - 接入 State=0 或明确本轮不纳入 State。

4. 补充单元测试:
   - setup 重复但同一突破只计一次。
   - short 方向目标达成。
   - 入场前触止损不算交易止损。
   - 5bar 持仓周期语义稳定。

### 优先级 P1: 做统计验证

1. 加入交易成本:
   - 外汇、黄金、指数、BTC 分品种配置 spread/slippage。
   - 报告同时输出 gross 和 net 指标。

2. 加入置信区间:
   - 胜率 binomial CI。
   - 期望 bootstrap CI。
   - 与随机突破基线、随机方向基线对比。

3. 做时间切分和 walk-forward:
   - 训练段选参。
   - 验证段筛选。
   - 测试段只评估，不再调参。

4. 重新评估品种:
   - 当前 XAUUSD、BTCUSD 表现较好，但样本仍少且未去重充分。
   - AUDUSD、GER40 当前表现偏弱，建议先从候选交易池剔除或单独建模。

### 优先级 P2: 增强策略逻辑

1. 多周期过滤:
   - H1 只做触发。
   - H4/D1 判断趋势方向和波动 regime。

2. 趋势方向过滤:
   - ADX + DI、均线斜率、状态编码方向。
   - 避免在明显反向趋势中做突破。

3. 风险控制:
   - 按 anchor_range 或 ATR 归一化止损。
   - 加入最大等待时间、最小 anchor 宽度、最大 anchor 宽度过滤。

## 阶段门槛

进入模拟盘观察的最低门槛:

- 去重后唯一突破事件数 >= 500。
- 加入成本后 5bar 或 10bar 期望仍为正。
- bootstrap 期望下界不明显为负。
- 胜率 95% 置信区间下界不低于 50%。
- 每个入选品种至少 80 个唯一事件。
- 报告中明确区分 setup 数、breakout 数、unique event 数。

进入实盘自动交易前的最低门槛:

- 完成 walk-forward 验证。
- 最近独立测试段仍为正期望。
- 交易成本、滑点、时段过滤、最大回撤均纳入。
- 至少连续 4 周模拟盘观测无重大偏差。
- 实盘只允许从低风险、低频、人工确认开始。

## 建议给 KIMI 的任务方向

下一轮不要继续直接扩大参数扫描，而应先修正研究口径并重跑 v2。建议 KIMI 任务目标为:

1. 修复 `squeeze_breakout_research.py` 的样本独立性、止损、目标、周期和指标命名问题。
2. 生成 `squeeze_breakout_research_v2` 报告，明确 gross/net、raw/dedup、train/test。
3. 补充针对上述问题的单元测试。
4. 输出是否仍值得继续研究的结论，不允许把当前策略升级为实盘交易策略。

对应的完整提示词已保存为 `KIMI_PROMPT_SQUEEZE_BREAKOUT_V2_20260605.md`。

