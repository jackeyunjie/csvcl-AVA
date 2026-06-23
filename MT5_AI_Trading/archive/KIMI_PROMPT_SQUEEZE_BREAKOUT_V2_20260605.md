# 给 KIMI 的提示词: 收缩突破统计验证 v2

你是交易研究工程师。请在 `D:\qoder\csvcl - AVA\MT5_AI_Trading` 项目中继续推进“收缩突破统计验证研究”。本轮目标不是上线交易，而是修正研究口径，重跑 v2 验证，并输出可审计报告。

## 当前背景

已有交付物:

- `squeeze_breakout_research.py`
- `test_squeeze_breakout_research.py`
- `python/analytics/squeeze_observer.py`
- `reports/squeeze/squeeze_breakout_research_20260605_1105.md`
- `reports/squeeze/squeeze_breakout_samples_20260605_1105.csv`
- `reports/squeeze/squeeze_param_sweep_20260605_1105.csv`

当前最好参数:

- `min_squeeze_score=3`
- `max_wait_bars=30`
- `min_breakout_atr=0.1`
- `require_structural=False`

当前报告结果:

- Setup 数: 1134
- 突破样本数: 991
- 突破率: 87.4%
- 5bar 胜率: 53.0%
- 盈亏比: 1.20
- 5bar 期望: 0.038%
- 1R 达成率: 14.3%
- 止损率: 32.9%
- 验证状态: 逻辑需要调整

已发现的关键审计问题:

1. 991 条突破样本按 `symbol + breakout_timestamp + breakout_direction` 简单去重后约为 672 个唯一突破键，存在重复 setup 计入同一突破的问题。
2. 当前止损检查在 setup 后的整个等待窗口执行，可能把入场前触碰止损也算入交易止损。
3. short 方向 1R/2R/3R 目标判断逻辑有误，应使用最大有利变动判断。
4. `min_breakout_atr` 实际使用的是 `anchor_range`，不是 ATR。
5. `compute_pivot_range()` 和 `compute_sr_range()` 当前公式重复，导致 score 重复计分。
6. `state_is_zero` 在突破研究中固定为 False，State=0 尚未真正接入。
7. 当前参数扫描是样本内优化，没有 walk-forward，也没有成本、滑点和置信区间。

## 任务目标

请完成 v2 研究版本，目标是“可审计、可复现、统计口径正确”。不要改动实盘交易模块，不要启动实盘交易。

## 必做任务

### 1. 重构或新增 v2 研究脚本

优先新增 `squeeze_breakout_research_v2.py`，避免破坏 v1 交付物。若必须修改 v1，请保留兼容入口。

v2 必须实现:

- `event_id`: 唯一突破事件 ID。
- `cluster_id`: 同一 symbol 相近 setup 触发同一突破时的事件簇 ID。
- 原始 setup 统计和去重 event 统计分开输出。
- 绩效统计以 unique event 为主，setup 明细仅用于诊断。

### 2. 修正突破、止损、目标与周期语义

请明确并实现:

- 突破入场 bar 之后才开始计算 stop、target、MFE、MAE。
- 入场前触碰 anchor 另一侧只能记录为 `pre_entry_noise`，不能算交易止损。
- short 方向目标判断使用 `max(entry_price - future_low)`。
- 1bar、5bar、10bar、20bar 统一定义为入场后第 N 根 K 线的收盘收益，不要把入场 bar 当作 1bar。
- MFE/MAE 使用 high/low，而不仅是 close。

### 3. 修正指标定义

请处理以下问题:

- 将 `min_breakout_atr` 改名为 `min_breakout_anchor_multiple`，或真正计算 ATR 并改为 ATR 阈值。
- 如果保留 Pivot 和 SR 两个指标，必须让公式有实际差异。
- 如果无法合理区分 Pivot 和 SR，则在 score 中只保留一个区间类结构收缩指标。
- 尝试接入 State=0。如果状态数据库无法稳定接入，请在报告中明确说明原因，并保留 `state_available=false` 字段。

### 4. 加入交易成本和统计置信区间

输出 gross 和 net 两套指标。

成本模型可以先用配置字典:

- 外汇: 固定 spread/slippage 百分比或点值近似。
- XAUUSD: 单独配置。
- 指数: 单独配置。
- BTCUSD: 单独配置。

统计报告至少包含:

- win_rate bootstrap 或 binomial CI。
- expectancy bootstrap CI。
- raw setup 指标。
- unique event 指标。
- 每个 symbol 的 unique event 指标。
- 随机方向基线或随机入场基线对比。

### 5. 做时间切分验证

至少实现一种:

- train/validation/test 时间切分。
- 或 walk-forward 窗口。

参数只能在训练段选择，测试段只评估，不允许在测试段调参。

### 6. 补充测试

新增或更新测试文件，例如 `test_squeeze_breakout_research_v2.py`。

必须覆盖:

- 同一突破被多个 setup 捕捉时，unique event 只计一次。
- 入场前触及 stop 不算交易止损。
- short 方向 1R 目标判断正确。
- 1bar/5bar 周期定义正确。
- gross/net 成本扣减正确。
- Pivot/SR 不再重复计分，或重复计分被显式禁用。

运行:

```powershell
python -m pytest .\test_squeeze_breakout_research.py .\test_squeeze_breakout_research_v2.py -q
```

如果 v2 测试文件路径不同，请在报告中写清楚实际命令。

## 输出要求

请生成以下文件:

- `reports/squeeze/squeeze_breakout_research_v2_YYYYMMDD_HHMM.md`
- `reports/squeeze/squeeze_breakout_events_v2_YYYYMMDD_HHMM.csv`
- `reports/squeeze/squeeze_breakout_setups_v2_YYYYMMDD_HHMM.csv`
- `reports/squeeze/squeeze_param_sweep_v2_YYYYMMDD_HHMM.csv`
- `docs/SQUEEZE_BREAKOUT_V2_RESEARCH_NOTES_YYYYMMDD.md`

报告必须明确给出:

- 是否仍为“逻辑需要调整”。
- 是否可以进入模拟盘观察。
- 是否禁止进入实盘自动交易。
- 哪些品种保留，哪些品种剔除。
- v1 和 v2 指标差异表。

## 决策门槛

只有满足以下条件，才允许建议进入模拟盘观察:

- unique event 数 >= 500。
- net expectancy > 0。
- 期望 bootstrap 95% CI 下界不明显为负。
- 胜率 CI 下界 >= 50%。
- 单品种保留池中每个品种 unique event >= 80。
- 测试段表现没有明显劣化。

不得建议进入实盘自动交易，除非另有明确授权并完成至少 4 周模拟盘观测。

## 工作纪律

- 不要改动无关模块。
- 不要删除 v1 报告和 CSV。
- 不要启动实盘交易。
- 不要将样本内最优参数包装成可交易结论。
- 所有统计口径必须在报告中写清楚。

