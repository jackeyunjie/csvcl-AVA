# 多周期指标系统 × State 系统交易策略提升方案

日期: 2026-06-05

## 一句话结论

当前 v3 已经把多周期收缩突破研究修正到更可信的口径：as-of 对齐、真实 event_id 去重、成本模型、walk-forward 都已纳入。结果显示，原始信号有弱正期望，但扣除成本后净期望为负，测试段也为负。因此下一步提升策略的核心不是继续放大样本或扩大参数扫描，而是用 State regime 做大门过滤，只在有统计优势的市场环境中触发多周期共振突破。

## 当前基线

v3 报告: `reports/squeeze/squeeze_mt_research_v3_20260605_1333.md`

| 指标 | 数值 |
|---|---:|
| Setup 数 | 7230 |
| 原始突破事件 | 5187 |
| 真实唯一突破事件 | 3286 |
| 唯一事件 5bar 胜率 | 50.8% |
| 唯一事件 Gross 期望 | 0.015% |
| 成本后净胜率 | 47.3% |
| 成本后净期望 | -0.005% |
| Test 段净期望 | -0.026% |
| 当前状态 | 逻辑需要调整 |

结论:

- 多周期共振有研究价值，但还没有交易级优势。
- 成本吃掉了很薄的 gross edge。
- 必须减少低质量交易，只保留高 regime、高共振、高突破质量的事件。

## 策略提升总框架

把现有策略拆成五层:

1. **State Regime Gate**: 先判断市场环境是否值得交易。
2. **Multi-Timeframe Setup Gate**: 再判断 H1/H4/D1 是否存在收缩或趋势共振。
3. **Breakout Trigger Gate**: 只在突破质量足够时触发。
4. **Execution Cost Gate**: 过滤成本太高、波动不足、时间段不合适的机会。
5. **Trade Management Gate**: 用不同 regime 对应不同出场规则。

这意味着:

- State 是“大门”，决定能不能交易。
- 多周期收缩是“准备状态”，决定是否进入观察。
- H1 突破是“触发器”，不是独立交易理由。
- 成本和 walk-forward 是“准入审计”，决定能否进入模拟盘观察。

## State 系统的使用方式

必须遵守 `STATE_VIEWPOINT_AGENT_CONTRACT.md`:

```text
structure_tf = where structure comes from
view_tf      = which observer price timestamps the calculation
state_hex    = structure_tf state under view_tf
```

对 H1 交易系统，推荐使用 H1 Agent:

```text
timestamp = H1 bar timestamp
view_price = H1 close

MN1@H1_view
W1@H1_view
D1@H1_view
H4@H1_view
H1@H1_view
```

不能把原生 D1@D1、H4@H4 简单对齐到 H1 后当作 H1 视角状态。State 里的 position 必须使用 H1 close 相对高周期结构 SR 计算。

## 推荐新增字段

在 v4 中，把 v3 events/trades 扩展为 State enriched events。

### State 字段

- `mn1_hex_h1_view`
- `w1_hex_h1_view`
- `d1_hex_h1_view`
- `h4_hex_h1_view`
- `h1_hex_h1_view`
- `mn1_semantic`
- `w1_semantic`
- `d1_semantic`
- `h4_semantic`
- `h1_semantic`
- `ef_count`
- `state_contraction_count`
- `state_breakout_count`
- `state_trend_strength_sum`
- `state_direction_alignment`
- `state_transition_1`
- `state_transition_3`

### 多周期指标字段

- `h1_squeeze_score`
- `h4_squeeze_score`
- `d1_squeeze_score`
- `h1_structural_squeeze`
- `h4_recent_squeeze`
- `d1_recent_squeeze`
- `squeeze_resonance_score`
- `h4_trend_bias`
- `d1_trend_bias`
- `trend_alignment`
- `breakout_strength_anchor`
- `breakout_strength_atr`
- `anchor_range_pct`
- `mfe_5bar`
- `mae_5bar`
- `session_bucket`
- `cost_pct`

## 组合评分模型

先不要训练复杂模型。建议使用透明评分:

```text
OpportunityScore =
  0.35 * StateScore
  + 0.25 * TrendResonanceScore
  + 0.20 * SqueezeQualityScore
  + 0.15 * BreakoutQualityScore
  - 0.05 * CostPenalty
```

### StateScore

参考:

- 高周期方向一致: +2
- State semantic 为 BREAKOUT_CONTRACTION 或 STRONG_TREND_CONTRACTION: +2
- ef_count >= 2: +1
- 最近 3 根 H1 state transition 从 contraction 转 breakout: +2
- 高周期强反向: -3

### TrendResonanceScore

参考:

- H4/D1 同向: +2
- H4 或 D1 同向，另一个 neutral: +1
- H4/D1 同时强反向: -3
- 方向混杂: 0

### SqueezeQualityScore

参考:

- H1 structural squeeze: +1
- H4 recent squeeze: +1
- D1 recent squeeze: +1
- anchor_range_pct 在品种历史中位区间附近: +1
- anchor_range 过窄或过宽: -1

### BreakoutQualityScore

参考:

- close 突破 anchor 且超过真实 ATR 阈值: +2
- 突破 bar 实体占比高: +1
- 突破后首根未快速回到 anchor 内: +1
- 假突破或低流动性时间段: -2

### CostPenalty

参考:

- `expected_edge_gross < 2 * cost_pct`: 强制过滤。
- crypto/oil/metals 单独配置成本，不使用外汇成本。
- 当前 v3 已证明成本足以把策略从正期望打成负期望，成本过滤必须前置。

## State Regime 候选方向

从现有 `h1_regime_strategy_report.md` 和 `h1_regime_short_report.md` 看，已有一些高周期 regime 在 H1 触发上表现更好。它们不能直接实盘，但可以作为 v4 初筛假设。

### Long 候选 Regime

优先验证:

- `MN1:C|W1:E`
- `MN1:E|W1:E`
- `MN1:E|W1:C`
- `MN1:4|W1:C`
- `MN1:4|W1:8`

典型触发:

- `mn1_w1_h4_h1_alignment`
- `weekly_breakout_rsi`
- `monthly_breakout_rsi`
- RSI 阈值 50/55/60
- Hold 24 或 120 H1 bars

### Short 候选 Regime

优先验证:

- `MN1:-D|W1:-D`
- `MN1:-C|W1:-F`
- `MN1:-8|W1:-E`
- `MN1:-F|W1:-D`
- `MN1:-C|W1:-A`

典型触发:

- `mn1_w1_h4_h1_alignment`
- `weekly_breakout_rsi`
- `monthly_breakout_rsi`
- RSI 阈值 40/45/50
- Hold 24 或 120 H1 bars

注意:

- 上述 regime 是候选白名单，不是交易结论。
- 必须在 v4 中与多周期收缩突破事件 JOIN 后重新验证。
- 若 regime 样本不足、测试段净期望为负，直接剔除。

## 品种池调整

基于 v3 净 PNL 分组，先做研究池而非交易池。

### 优先研究池

这些品种 v3 中成本后相对更好，适合优先验证 State 过滤:

- `XAGUSD`
- `UK100`
- `ETHUSD`
- `NAS100`
- `GER40`
- `XAUUSD`
- `US30`

### 观察池

净优势很薄，必须依赖 regime 过滤:

- `GBPUSD`
- `AUDJPY`
- `CADJPY`
- `EURJPY`
- `USDCAD`
- `EURUSD`
- `USDJPY`

### 暂缓池

v3 成本后表现偏弱，除非 State regime 明显改善，否则不进入模拟观察:

- `USOIL`
- `GBPJPY`
- `NZDUSD`
- `EURGBP`
- `USDCHF`
- `US500`
- `BTCUSD`
- `AUDUSD`

说明:

- `BTCUSD` gross 为正但成本后转负，优先从成本模型和出场方式重新评估。
- `XAGUSD` 样本较少，不能因单次 v3 排名靠前就直接交易。

## 具体策略模板

### 模板 A: State-Filtered Resonant Breakout

入场前置:

- State regime 属于候选白名单。
- H4/D1 不强反向。
- H1 出现收缩 setup。
- H1 在等待窗口内突破 anchor。
- `OpportunityScore >= 6`。

Long:

```text
state_direction_alignment >= 1
d1/h4 trend not bearish
h1 breakout_direction = up
breakout_strength_atr >= threshold
expected_edge_gross >= 2 * cost_pct
```

Short:

```text
state_direction_alignment <= -1
d1/h4 trend not bullish
h1 breakout_direction = down
breakout_strength_atr >= threshold
expected_edge_gross >= 2 * cost_pct
```

出场:

- 先回测 fixed_hold_24h、fixed_hold_120h、structure_stop、1R_partial。
- 不默认使用 5bar，因为 v3 的 5bar 净期望偏弱。

### 模板 B: State Transition Breakout

核心思想:

只交易 state 从 contraction 转 breakout 的事件，而不是所有 squeeze breakout。

入场前置:

```text
previous H1/H4 state semantic contains contraction
current H1 state semantic contains breakout
higher timeframe state direction not conflicting
```

重点验证:

- transition_1: 最近 1 根 H1 的 state 变化。
- transition_3: 最近 3 根 H1 的 state 变化。
- transition 后的 24h/120h 收益是否优于普通突破。

### 模板 C: Regime-Specific Exit

核心思想:

不同 State regime 使用不同持仓周期，而不是统一 5bar。

示例:

- 高周期趋势一致: hold 24/120 H1 bars。
- 高周期 neutral: 只做 5/10bar 快速出场。
- 强反向: 不交易。
- 高波动扩张后: structure stop 或 trailing stop。

## v4 实施计划

### P0: State Enrichment

新增脚本:

`squeeze_mt_state_enriched_research_v4.py`

输入:

- `squeeze_mt_events_v3_20260605_1333.csv`
- `squeeze_mt_trades_v3_20260605_1333.csv`
- `data/h1_state.duckdb` 或 `data/hermass_h1_state.db`

输出:

- `reports/squeeze/squeeze_mt_state_events_v4_YYYYMMDD_HHMM.csv`
- `reports/squeeze/squeeze_mt_state_trades_v4_YYYYMMDD_HHMM.csv`
- `reports/squeeze/squeeze_mt_state_research_v4_YYYYMMDD_HHMM.md`

必须实现:

- H1 Agent viewpoint state join。
- State regime 分组。
- State transition 分组。
- StateScore 和 OpportunityScore。
- 成本后净期望统计。

### P1: Filter Search

只搜索过滤条件，不搜索入场本身:

- Regime whitelist。
- OpportunityScore 阈值。
- breakout_strength 阈值。
- session_bucket。
- symbol whitelist。
- exit_rule。

目标:

- 减少交易数。
- 提高 net expectancy。
- 保持测试段稳定。

### P2: Walk-Forward

最低门槛:

- train/validation/test 全部输出。
- 参数只在 train/validation 选择。
- test 只评估。
- 输出每个 regime 的 test 表现。

### P3: 模拟盘观察

只有满足以下条件才进入:

- test net expectancy > 0。
- test trades >= 300。
- with State filter 的 test 表现优于无 State filter。
- 每个入选品种 test trades >= 30。
- 最大回撤和连续亏损可接受。

## 验收门槛

策略从“研究”升级到“模拟盘观察”的最低标准:

| 项目 | 门槛 |
|---|---:|
| Test net expectancy | > 0 |
| Test net win rate | > 50% |
| Test trades | >= 300 |
| 入选品种 | 每个 >= 30 trades |
| State filter 增益 | 明显优于 v3 baseline |
| 成本模型 | 已纳入 |
| 数据对齐 | as-of，无未来信息 |
| 实盘权限 | 仍禁止自动下单 |

当前不满足这些条件。

## 不建议做的事

- 不要继续盲目扩大品种和参数扫描。
- 不要只看 gross PNL。
- 不要把 H1 突破本身当作交易信号。
- 不要把高周期原生 state 简单对齐到 H1 后使用。
- 不要在 test 段调参。
- 不要进入实盘自动交易。

## 下一步给执行代理的任务

直接任务:

1. 新增 v4 State-enriched 研究脚本。
2. 将 v3 events/trades 与 H1 Agent State 表 as-of JOIN。
3. 生成 StateScore、OpportunityScore。
4. 只搜索过滤条件和出场规则。
5. 输出 v4 报告，比较:
   - v3 baseline
   - State-filtered
   - State + multi-timeframe resonance
   - State + resonance + cost/session filter
6. 若 test 段净期望仍为负，继续停留研究阶段。

最终目标:

把当前“所有突破都统计”的观察器，升级为“只在有优势 State regime 中捕捉多周期共振突破”的交易候选系统。

