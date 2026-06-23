---
type: concept
created: 2026-05-09
tags: [hongrun, hermass, state, database, multi-timeframe, asof, support-resistance]
---

# 弘运多周期 as-of 一表框架 v0.1

## 一句话

富途牛牛里不强求一图多周期；弘运底层必须做到一表多周期。

也就是说，图表可以只显示当前周期，数据库必须把低周期时间戳与高周期已知状态对齐，让 Hermes、Hermass、回测器和基金经理助手在一行里同时读取 D/W/M，未来也包括 H1/D/W/M。

## 为什么重要

弘运是多周期为主的框架。月线/周线不是简单过滤器，而是环境和先验；日线或小时线是观察、触发和执行层。

补充原则：D1、H1、M15 等每个基准周期都必须作为独立系统建设，详见 `wiki/concepts/hongrun-base-timeframe-native-system-principle-v0-1.md`。H1/M15 不是 D1 的附属下钻，而是带有本周期 strict-prior 高周期上下文的原生系统。

如果这些信息分散在多张周期表里，Agent 每次都要临时拼接，容易出现口径漂移、未来函数、未完成周期误用和解释不一致。

因此我们定义：

- 图表层：允许单周期观察。
- 数据层：必须保留各周期连续轨迹。
- 决策层：使用 as-of 宽表读取多周期环境。

这仍然是一个待验证假设，不是已经证明的结论。

假设内容是：低周期决策如果天然读取同一时间戳下已经可见的高周期 state / SR / Pivot / ACD / 宽度 / 边界数据，应该比低周期单独决策更能识别大周期运化阶段，从而改善盈亏比、止损位置、假突破过滤和持仓管理。

验证标准必须回到数据：

- 小周期单独字段 vs 小周期 + 高周期 as-of 字段的对照实验。
- 5 窗口 walk-forward。
- 最差 PF、正窗口比例、cv_sqn、样本数。
- stop-first 比例是否下降。
- 目标先触达、跟踪止损盈利、时间离场等出场结果是否改善。

如果高周期字段只让当前样本更漂亮，但弱窗口变差，不能升格。

## 底层任务：收缩/扩张

收缩/扩张是弘运最底层的观察框架。

只要一个指标能够观察收缩、扩张、释放、再收缩，就不应只作为图表指标存在，而应进入多周期连续数据库。

这包括：

- state 的 compression / trend / volatility。
- 支撑阻力的间距、间距百分比、间距分位、间距变化。
- 枢轴几何的 1K/3K/6K 带宽和枢轴间距。
- VCP 的价格收缩、成交量萎缩、突破前收敛。
- Bollinger / PIRATE 的带宽分位和释放。
- Donchian 的通道宽度、突破后回踩空间。
- ACD 的 opening range / pivot range 宽度。
- 行业趋势的广度扩张、成员同步收缩/扩张。
- 财报、公告、异类事件窗口导致的波动扩张。

这些字段的目的不是“多存一些指标”，而是让系统能学习：

1. 哪些收缩会导致有效扩张。
2. 哪些扩张是趋势释放，哪些是失控风险。
3. 高周期收缩如何约束低周期突破。
4. 低周期扩张是否会反向改变中高周期状态。
5. 收缩/扩张从一个周期传导到另一个周期的时间差。

## 三类标准表

### 1. 周期窄表

```text
table: state_timeframe

symbol
timeframe              -- H1 / D / W / M 等
date                   -- 该周期记录日期
period_start
period_end
open/high/low/close
state fields
pivot fields
acd fields
support
resistance
```

作用：保存每个周期自己的原始计算轨迹。一切 state、支撑阻力、枢轴、ACD 都先在这里按周期独立产生。

### 2. 支撑阻力历史窄表

```text
table: sr_history

symbol
timeframe
date
support
resistance
sr_width
sr_width_pct
sr_width_rank_120
support_change
resistance_change
sr_width_change_pct
support_event
resistance_event
sr_event
sr_state_cn
```

作用：连续观察支撑阻力位的高低变化，以及支阻间距的收缩、扩张、再收缩。

这张表是结构运化的关键，不只是为了画线。

### 3. 基准周期 as-of 多周期宽表

```text
table: state_<base_tf>_multitf_asof

symbol
date                   -- 基准周期时间戳，例如 H1 / D / W / M
base_timeframe

base OHLCV
base state/action fields

D_state_*
D_sr_*
D_price_to_support_pct
D_price_to_resistance_pct
D_price_in_sr_range_pct

W_state_*
W_sr_*
W_price_to_support_pct
W_price_to_resistance_pct
W_price_in_sr_range_pct

M_state_*
M_sr_*
M_price_to_support_pct
M_price_to_resistance_pct
M_price_in_sr_range_pct

asof_join_policy
asof_schema_version
```

作用：一行就是一个可分析、可排序、可回测、可给 Agent 读取的多周期状态快照。

工程原则：

- 窄表是事实源，宽表是决策缓存。
- Agent 默认读宽表，不在决策时临时跨周期拼表。
- 宽表只能使用 as-of 已知数据，不能使用未来周期结果。
- 高频查询、排序、回测和自然语言解释优先读宽表，提高效率并减少口径漂移。

不同基准周期必须单独建表，因为站在不同层次观察，问题不同：

| 表 | 基准视角 | 主要问题 |
|---|---|---|
| `state_h1_multitf_asof` | 小时/盘中执行 | H1 是否改善盈亏比，是否追高，是否适合等待回踩 |
| `state_d1_multitf_asof` | 日线波段/候选排序 | 日线触发是否得到周线/月线环境支持 |
| `state_w1_multitf_asof` | 周线中线/持仓管理 | 周线运化是否进入趋势释放或转入风险压制 |
| `state_mn1_multitf_asof` | 月线长期/配置视角 | 长期大势、产业周期、公司周期是否进入长期同力 |

因此，一表多周期不是只有“日线宽表”。日线只是第一张样板表。

标准建设顺序：

```text
state_timeframe            -- 周期事实源
sr_history                 -- 各周期 SR 轨迹
pivot_geometry_timeframe   -- 各周期 Pivot 轨迹
state_d1_multitf_asof      -- 日线视角
state_w1_multitf_asof      -- 周线视角
state_mn1_multitf_asof     -- 月线视角
state_h1_multitf_asof      -- 小时视角，等 H1 数据稳定后再做
```

## 指标接入规范

任何新指标接入弘运底层时，必须判断是否包含收缩/扩张观察能力。

如果包含，标准字段至少包括：

```text
indicator_family        -- state / sr / pivot / vcp / bollinger / donchian / acd / alt_event
timeframe
date
value_main
upper_boundary
lower_boundary
width
width_pct
width_rank_lookback
width_change
width_slope
contraction_flag
expansion_flag
release_flag
boundary_break_flag
boundary_reclaim_flag
completed_asof_date
calculation_version
quality_flag
```

边界字段必须显式记录。没有边界，就不能谈盈亏比；没有连续宽度，就不能谈收缩/扩张；没有 as-of 时间戳，就不能进入强化学习和 walk-forward。

## as-of 对齐原则

低周期表只能看见同一时间点之前已经完成或已经确认的高周期数据。

标准策略：

```text
join_policy = backward_allow_exact_matches
asof_schema_version = multitf_asof_v0.2
```

含义：

- `backward`：只向过去找最近一条高周期记录。
- `allow_exact_matches`：如果日期正好相同，可以使用当天已确认记录。
- 不允许向未来找值。

对于不同市场和执行时间，是否允许当天高周期记录，要由 `observe_mode` 决定：

- `postclose`：收盘后复盘，可以使用当天完成记录。
- `preopen`：盘前决策，只能使用上一已完成周期记录。
- `intraday`：盘中观察，必须更严格处理未完成周期。

当前 v0.3 已落地 `postclose` / `preopen` 双观察模式。`postclose` 适合盘后复盘和 outcome-labelled 回测；`preopen` 适合 T 日盘前或盘中决策，W/M 的 state、level、SR、Pivot 源日期都必须严格早于基准 `date`。

## 当前港股落地

当前港股 10 支测试库已经落地：

```text
hk_state_timeframe
hk_sr_history
hk_state_d1_asof
hk_state_d1_asof_labels
hk_state_d1_multitf_asof
hk_state_d1_multitf_asof_postclose
hk_state_d1_multitf_asof_preopen
hk_state_w1_multitf_asof
hk_state_mn1_multitf_asof
```

其中 `hk_state_d1_multitf_asof` 是向后兼容 VIEW，指向 `hk_state_d1_multitf_asof_postclose`。v0.3 已补齐 W/M Pivot as-of，并完成 label 物理隔离与 D1 preopen/postclose 分表：

- 一行一个 `symbol × 日线 date`。
- 同时保留 D/W/M state。
- 同时保留 D/W/M 支撑、阻力、支阻宽度、宽度百分比、宽度分位。
- 同时保留 D/W/M Pivot 1K/3K/6K 上下轨、宽度百分比、层级间距。
- 同时保留价格到 D/W/M 支撑和阻力的距离。
- `hk_state_d1_asof_labels` 独立保存 `next_*` / `future_*` forward-return label，按 `(symbol, date)` 显式回连。
- `hk_state_d1_multitf_asof_postclose` 允许 W/M 同日 exact match。
- `hk_state_d1_multitf_asof_preopen` 禁止 W/M 同日 exact match，W/M state、level、SR、Pivot 全部严格回退。

同时已落地：

- `hk_state_w1_multitf_asof`：周线基准多周期宽表。
- `hk_state_mn1_multitf_asof`：月线基准多周期宽表。

仍需补齐：

- W1/MN1 基准宽表的 `preopen` 双轨版本。
- `hk_state_h1_multitf_asof`：小时基准多周期宽表，等待 H1 数据源稳定后接入。

## 对其他指标的要求

其他指标也应参考这种“执行数据记录方式”：

1. 先在各自周期窄表中独立计算。
2. 连续保留轨迹，不只保留最新值。
3. 记录变化事件和变化方向。
4. 再通过低周期 as-of 宽表对齐到执行时间戳。
5. 所有字段保留计算口径和版本号。

适用对象包括：

- state
- 支撑阻力
- 枢轴几何
- ACD
- VCP
- Donchian
- PIRATE/Bollinger
- 行业趋势先验
- 异类事件数据

Hermes 和 Obsidian 的沉淀任务也按这个框架组织：不是只记录“今天某指标是什么”，而是记录多周期收缩/扩张带来的周期变化、边界约束和相互影响。

Obsidian 中每只股票长期专家库至少要能追问：

- 月线收缩持续了多久？
- 周线扩张是否发生在月线允许的边界内？
- 日线突破时，支撑阻力宽度是收缩低分位还是扩张高分位？
- H1 改善的是盈亏比，还是只是制造追高噪音？
- 过去同类收缩到扩张的转化，成功样本和失败样本分别是什么？

Hermes 在排序和解释时，必须优先读取这些连续记录，而不是只读最新快照。

## 关键边界

1. 不用图表限制反推数据库设计。
2. 不用近似周期污染真实周期聚合。
3. 不把中文注释当计算公式。
4. 不在 as-of 表里引入未来函数。
5. 策略升格仍必须通过 5 窗口 walk-forward。

## 产品意义

一表多周期是 Hermass Agent 的底座。

它让基金经理助手可以在同一行回答：

- 当前价格离日线支撑多远？
- 周线支撑是否正在上移？
- 月线支阻间距是在收缩还是扩张？
- 日线突破是否得到周线/月线环境支持？
- 盈亏比是否来自真实结构，而不是事后画线？

这就是“不能一图多周期，但能一表多周期”的工程化版本。

## 自然语言层

用户不应该直接面对 200 个字段。

Hermes/Hermass 的自然对话层应把表字段翻译成问题：

- 长线用户问：“这家公司长期还值得跟吗？”
  - 系统读取 `state_mn1_multitf_asof`、公司周期、产业周期。
- 中线用户问：“周线是否还支持持有？”
  - 系统读取 `state_w1_multitf_asof`、W/M 支撑阻力、周线 Pivot。
- 波段用户问：“现在追还是等回踩？”
  - 系统读取 `state_d1_multitf_asof`、D/W/M 边界、盈亏比。
- 短线/执行用户问：“H1 有没有给更好的止损位置？”
  - 系统读取 `state_h1_multitf_asof`，并检查高周期 veto。

回答模板应包含：

```text
当前基准视角
高周期支持/压制
当前边界
收缩/扩张状态
可交易区/不可交易区
可用止损/止盈方案
先验概率证据
需要补充的人类判断
```

边界：

- 不说“必涨必跌”。
- 不直接替用户下最终交易决定。
- 每个自然语言结论都要能回指到数据库字段、样本统计或人工标注。
