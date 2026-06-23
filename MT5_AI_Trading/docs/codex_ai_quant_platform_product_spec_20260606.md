# codex AI量化多周期视角交易平台产品功能规格说明

版本: v1.0-codex
日期: 2026-06-06
适用项目: `MT5_AI_Trading`、MT4数据处理与邮件通知工具链、State Hex/P106/P107研究资产

## 1. 产品定位

本平台定位为“AI辅助量化策略工厂 + 多周期市场观察与执行工作站”。它不是一个让大模型直接下单的黑盒交易机器人，而是把用户的交易经验、现有MT5/MT4基础设施、多周期State视角、回测审计、Agent协作、模拟观察和受控执行组织成一条可追溯的闭环。

核心闭环:

```text
自然语言策略想法
  -> 策略DSL/策略模板
  -> 数据审计
  -> 可执行策略代码
  -> 严格回测与风险报告
  -> 多Agent复核
  -> 模拟盘观察
  -> 人工审批
  -> MT5/MT4执行或仅生成执行建议
  -> 交易与信号复盘
```

平台必须做到与现有项目“1+1>2”:

- 复用 `MT5_AI量化交易系统技术方案.md` 中的ZeroMQ分布式架构、Python AI引擎和回测架构设想。
- 复用 `MT5_AI_Trading/python/core/mt5_bridge.py`、`mt5_bridge_dual.py`、`mt5_python_api.py`、`main_controller.py` 的连接、心跳、下单安全开关和多账户能力。
- 复用 `MT5_AI_Trading/python/backtest_platform/` 已有的数据层、计算层、策略层、执行层和报告层雏形。
- 复用 `squeeze_multi_timeframe_research_v5.py`、`python/analytics/multi_timeframe_squeeze.py`、`SQUEEZE_MT_STATE_STRATEGY_UPGRADE_20260605.md` 的多周期收缩、共振突破、State Gate、成本和Walk-Forward口径。
- 复用 `STATE_VIEWPOINT_AGENT_CONTRACT.md` 的周期视角Agent契约，避免把原生高周期状态简单拼接成低周期视角。
- 复用 `observation_db.py`、`reification_agent.py`、`run_v5_simulation.py`、`run_v5_daily_summary.py` 的观察数据库、复现提醒和日报机制。
- 复用 `process_real_mt4_data.py`、`csv_color_marker.py`、`email_sender.py`、`scheduler.py` 的MT4数据处理、截图/Excel标记和邮件通知基础设施。

## 2. 外部开源项目启发

本规格参考了截至2026-06-06可检索的开源项目。它们不建议被整体fork为平台核心，而应作为架构和体验参考。

| 项目 | 近期状态/定位 | 可借鉴能力 | 本平台落地方式 |
|---|---|---|---|
| TradingAgents | 多Agent LLM金融交易框架，2026年仍在发布，包含研究经理、交易员、组合经理、持久决策日志和LangGraph checkpoint | 角色化Agent、辩论、Portfolio Manager最终审批、决策日志 | 建设“研究Agent、策略Agent、风控Agent、执行Agent、组合经理Agent”，但必须接入本项目回测和风控硬门槛 |
| FinRobot | 金融分析AI Agent平台，结合LLM、强化学习和量化分析 | 财务/市场/新闻工具化Agent、金融报告生成 | 作为股票基本面、行业轮动和报告Agent参考 |
| RD-Agent | 面向量化金融的R&D多Agent框架，强调假设、实现、实验、反馈迭代 | 自动因子/模型研发循环 | 自然语言策略生成后的“假设-实现-回测-反馈”循环 |
| Qlib | AI导向量化投资平台，包含数据处理、模型训练、回测、风险建模、组合优化和订单执行链路 | 研究到生产的ML pipeline和回测评估 | 用于A股/美股因子研究与行业轮动模块参考，不替代当前MT5主线 |
| FinRL/FinRL-X | 金融强化学习框架，FinRL-X强调AI-native、模块化和生产化 | RL Agent、交易环境、风险控制思想 | 中期接入为实验Agent，不作为MVP下单依据 |
| QuantConnect Lean | 事件驱动、模块化、支持回测和实盘的专业量化引擎 | IDataFeed、Algorithm、Transaction、Result模块化 | 作为严格事件驱动回测和未来多资产实盘适配参考 |
| LangGraph | 长时、有状态Agent编排，支持持久执行、人工介入、记忆和可观测性 | Agent图编排、checkpoint、human-in-the-loop | 多Agent编排优先参考，但核心交易审批仍由本平台风控服务控制 |
| AutoGen | 多Agent应用框架，当前维护模式并建议新项目迁移到Microsoft Agent Framework | 多Agent消息、工具调用、GUI原型经验 | 只参考分层和工具化思想，不作为新核心依赖 |
| vn.py | Python开源量化交易平台开发框架，国内交易接口生态成熟 | 国内市场接口、CTA/Portfolio应用、工程规范 | 后续接A股/QMT/期货时参考 |

参考链接:

- TradingAgents: https://github.com/TauricResearch/TradingAgents
- FinRobot: https://github.com/AI4Finance-Foundation/FinRobot
- RD-Agent: https://github.com/microsoft/RD-Agent
- Qlib: https://github.com/microsoft/qlib
- FinRL: https://github.com/AI4Finance-Foundation/FinRL
- Lean: https://github.com/QuantConnect/Lean
- LangGraph: https://github.com/langchain-ai/langgraph
- AutoGen: https://github.com/microsoft/autogen
- vn.py: https://github.com/vnpy/vnpy

## 3. 目标用户与核心场景

### 3.1 目标用户

| 用户 | 核心诉求 | 平台响应 |
|---|---|---|
| 策略研究员 | 快速把经验转成可回测策略，知道是否有统计优势 | 自然语言生成、策略模板、自动回测、Agent复核 |
| 交易执行者 | 看到当前市场状态、信号依据、风险边界和执行建议 | 多周期市场分析、信号卡片、MT5/MT4状态、执行审批 |
| 风控复核者 | 检查未来函数、成本、重复事件、过拟合、回撤 | 数据审计、Run Card、风险报告、硬风控规则 |
| 平台开发者 | 模块可扩展，能接入新数据源、新Agent、新策略 | DSL、API、插件、数据库模型和统一接口 |

### 3.2 典型用户路径

用户输入:

```text
创建一个均线金叉策略，MA5上穿MA20时买入，跌破MA10时卖出。
只在H1趋势与H4/D1方向一致时交易，单笔风险不超过1%，先回测EURUSD、XAUUSD、GER40。
```

平台输出:

1. 策略草案卡片:
   - 策略名: `ma_cross_h1_resonance_v1`
   - 交易方向: long only
   - 主周期: H1
   - 高周期过滤: H4/D1 as-of trend bias
   - 入场: MA5 cross above MA20
   - 出场: close below MA10 / stop loss / max hold
   - 风控: risk_per_trade <= 1%

2. 策略DSL与manifest:
   - 输入字段、时间点约束、指标计算、事件去重、成本模型、出场规则。

3. 代码生成与验证:
   - 生成Python策略插件。
   - 禁止生成直接下单代码。
   - 运行静态检查、PIT检查、单元测试、样本回测。

4. 回测报告:
   - 30秒内返回缓存数据上的初版结果。
   - 输出胜率、净期望、回撤、夏普、盈亏比、交易数、成本影响。
   - 标注Train/Validation/Test与Walk-Forward结果。

5. 多Agent复核:
   - 研究Agent: 统计优势是否足够。
   - 数据审计Agent: 是否存在未来函数和数据缺口。
   - 风控Agent: 是否满足资金风险边界。
   - 执行Agent: 是否适合MT5实际点差和滑点。
   - Portfolio Manager Agent: 仅给出“进入观察/拒绝/需人工确认”。

6. 模拟盘观察:
   - 若通过准入，进入观察数据库。
   - 每日自动记录信号、市场状态、是否触发、实际后续走势。
   - 邮件/报告推送复用现有MT4处理和邮件系统。

## 4. 产品模块总览

```text
AI自然语言策略工作台
  |-- 策略假设中心
  |-- 策略DSL/manifest生成器
  |-- 策略代码生成与验证

智能回测与研究工作台
  |-- 快速回测
  |-- 严格回测
  |-- 多周期数据审计
  |-- 风险与绩效报告

多Agent协作系统
  |-- Research Agent
  |-- Strategy Coder Agent
  |-- Backtest Agent
  |-- Data Auditor Agent
  |-- Risk Agent
  |-- Execution Agent
  |-- Portfolio Manager Agent
  |-- Report/Notification Agent

实时市场分析系统
  |-- 多周期State Viewpoint Agent
  |-- 多指标收缩过程记录
  |-- 多周期共振突破识别
  |-- 突破后趋势跟踪
  |-- 行业轮动与个股状态评估

执行与风控系统
  |-- MT5/MT4桥接
  |-- 模拟盘/实盘安全开关
  |-- 资金与订单风控
  |-- 异常监控与熔断
```

## 5. 功能规格

### 5.1 自然语言策略生成

#### 5.1.1 功能目标

用户可以用对话描述交易想法，平台自动转为可审计、可回测、可版本管理的策略。

必须支持的表达类型:

- 技术指标规则: 均线、RSI、MACD、ADX、ATR、布林带、Pivot/SR、Keltner、SuperTrend等。
- 多周期条件: H1入场，H4/D1过滤；M15触发，H1确认；D1交易，W1/MN1过滤。
- State条件: `MN1/W1/D1/H4/H1 @ H1_view` 的方向一致、收缩、突破、趋势强度。
- 出场规则: 跌破均线、固定持仓bar、结构止损、ATR止损、1R部分止盈、移动止损。
- 成本和风控: 单笔风险、最大手数、最大回撤、最大点差、冷却期。
- 品种和市场: 外汇、黄金、白银、股指、加密、股票。

#### 5.1.2 用户交互

页面或CLI提供三个区域:

- 左侧: 策略对话输入。
- 中间: 策略DSL和规则解释。
- 右侧: 验证状态、回测结果、Agent复核意见。

交互步骤:

1. 用户输入策略描述。
2. 平台显示“策略理解卡片”，让用户确认关键规则。
3. 用户点击“生成策略草案”。
4. 平台生成DSL、manifest和Python策略代码。
5. 平台自动执行验证。
6. 用户可点击“一键回测”或继续追问修改。

#### 5.1.3 策略DSL示例

```yaml
strategy_id: ma_cross_h1_resonance_v1
source: natural_language
description: MA5上穿MA20买入，跌破MA10卖出，H4/D1同向过滤
market_scope:
  symbols: [EURUSD, XAUUSD, GER40]
  main_timeframe: H1
  context_timeframes: [H4, D1]
inputs:
  indicators:
    - ma_fast: SMA(close, 5)
    - ma_mid: SMA(close, 10)
    - ma_slow: SMA(close, 20)
    - h4_trend_bias
    - d1_trend_bias
  state_views:
    - h1_view_snapshot
entry:
  long:
    all:
      - cross_up(ma_fast, ma_slow)
      - h4_trend_bias in [bullish, neutral]
      - d1_trend_bias in [bullish, neutral]
exit:
  long:
    any:
      - close < ma_mid
      - stop_loss_hit
      - max_hold_bars >= 120
risk:
  risk_per_trade_pct: 1.0
  max_positions: 3
  max_spread_points: 20
audit:
  pit_required: true
  cost_model_min_level: snapshot_cost
  event_dedup_required: true
```

#### 5.1.4 策略验证

生成后必须通过:

- 语义完整性: 入场、出场、周期、品种、风控必须明确。
- 时间点约束: 高周期字段必须来自已收盘bar，禁止未来函数。
- 代码安全: 禁止网络下载、文件删除、直接下单、读取密钥、动态执行未授权代码。
- 数据可用性: 所需品种和周期有足够历史数据。
- 最小回测: 至少运行一个小窗口，确认策略可执行。

### 5.2 智能策略回测

#### 5.2.1 功能目标

用户点击“一键回测”后，平台应在30秒内返回缓存数据上的初步结果，并在后台继续生成严格报告。

回测分两级:

- 快速回测: 用缓存特征和向量化逻辑快速返回候选结果。
- 严格回测: 逐bar事件驱动，检查PIT、成本、滑点、去重、出场状态机，用作正式结论。

#### 5.2.2 必备能力

- 多周期数据对齐:
  - H1/H4/D1/W1/MN1必须使用as-of对齐。
  - H1视角只能使用H1时间点之前已经收盘的H4/D1结构。
  - State字段必须遵守 `STATE_VIEWPOINT_AGENT_CONTRACT.md`。

- 成本模拟:
  - 固定成本只用于粗筛。
  - 正式报告使用MT5实际点差快照或经纪商成本配置。
  - 支持滑点、手续费、隔夜利息、最小跳动、拒单。

- 出场模拟:
  - fixed_hold_n_bars
  - structure_stop
  - atr_stop
  - ma_exit
  - 1r_partial_trailing
  - trend_decay_exit

- 风险与绩效指标:
  - 总收益、净收益、年化收益。
  - 胜率、盈亏比、Profit Factor、Expectancy。
  - Sharpe、Sortino、Calmar。
  - 最大回撤、回撤持续时间、连续亏损。
  - 分品种、分方向、分周期、分State regime、分session统计。
  - 成本前后对比。

#### 5.2.3 回测报告用户界面

回测结果必须分层展示:

- 顶部摘要:
  - 是否通过准入。
  - 净期望是否大于0。
  - Test样本数是否充足。
  - 数据审计是否通过。
  - 风控是否通过。

- 中部指标:
  - 权益曲线、回撤曲线、交易分布。
  - 分品种/分方向/分State表格。
  - 成本侵蚀分析。

- 底部审计:
  - 数据窗口、数据版本、代码hash。
  - 高周期对齐证明。
  - event_id去重统计。
  - Agent复核意见。

### 5.3 多Agent协作系统

#### 5.3.1 功能目标

平台内Agent是“有职责边界的审计与研究工作流”，不是自由下单的自治机器人。

#### 5.3.2 Agent角色

| Agent | 职责 | 输入 | 输出 | 禁止 |
|---|---|---|---|---|
| Research Planner Agent | 拆解策略假设、设计实验 | 用户自然语言、历史报告 | 研究计划、变量清单、实验矩阵 | 禁止直接批准交易 |
| Strategy Coder Agent | 生成策略DSL、manifest、策略插件 | 研究计划、模板库 | 可执行策略代码、测试用例 | 禁止写下单逻辑 |
| Data Auditor Agent | 检查数据、PIT、缺失、时区、成本 | 数据表、回测Run Card | 审计通过/失败和原因 | 禁止忽略一票否决项 |
| Backtest Agent | 调用回测引擎并汇总结果 | 策略版本、数据版本 | 回测报告、指标、交易明细 | 禁止改写回测结果 |
| Research Agent | 分析策略优势和局限 | 回测报告、市场状态 | 研究结论和下一步 | 禁止只报喜不报忧 |
| Risk Agent | 评估资金风险、模型风险、市场风险 | 策略、回测、持仓、风控配置 | 风险评级、风控参数建议 | 禁止绕过硬限制 |
| Execution Agent | 生成模拟盘/执行建议、检查MT5可交易性 | 信号、账户、点差、交易时段 | 执行计划、拒绝原因 | MVP禁止自动实盘 |
| Portfolio Manager Agent | 汇总各Agent意见，做准入裁决 | 所有Agent报告 | 进入观察/拒绝/需人工确认 | 禁止单独覆盖风控 |
| Report/Notification Agent | 生成日报、周报、邮件/消息推送 | 观察数据库、交易日志 | Markdown、HTML、邮件内容 | 禁止夸大结论 |

#### 5.3.3 协作机制

标准流程:

```text
Research Planner
  -> Strategy Coder
  -> Data Auditor
  -> Backtest Agent
  -> Research Agent
  -> Risk Agent
  -> Execution Agent
  -> Portfolio Manager
  -> Report/Notification
```

分歧处理:

- 若Data Auditor失败，流程立即停止。
- 若Backtest净期望为负，除非用户明确研究失败原因，否则不进入模拟观察。
- 若Risk Agent给出高风险，Portfolio Manager只能输出“拒绝”或“人工确认”。
- 若Research Agent和Risk Agent结论冲突，生成冲突报告，不允许自动执行。

### 5.4 实时市场分析

#### 5.4.1 功能目标

实时处理多维度市场数据，输出可操作的状态报告、观察提醒和风险提示。

#### 5.4.2 多周期结构共振分析

必须覆盖:

- State Viewpoint:
  - `MN1/W1/D1/H4/H1 @ H1_view`
  - `MN1/W1/D1/H4/H1/M30/M15 @ M15_view`
  - 股票路线可扩展 `MN1/W1/D1 @ D1_view`

- 多指标收缩:
  - BB宽度分位数。
  - SR范围分位数。
  - Pivot/ACD枢轴范围。
  - ADX低趋势过滤。
  - ATR/波动率收缩。
  - 成交量萎缩或异常。

- 共振条件:
  - H1收缩，H4/D1未强反向。
  - H1/H4/D1同时或连续收缩。
  - State语义从contraction转breakout。
  - 高周期趋势方向与突破方向一致。

#### 5.4.3 多指标收缩到共振突破的过程记录

平台必须把“过程”记录下来，而不只记录最终信号。

事件生命周期:

```text
NO_SETUP
  -> CONTRACTION_DISCOVERED
  -> CONTRACTION_BUILDING
  -> RESONANCE_ARMED
  -> BREAKOUT_TRIGGERED
  -> BREAKOUT_CONFIRMED
  -> TREND_TRACKING
  -> EXITED
  -> POST_MORTEM
```

每个生命周期阶段必须记录:

- 时间戳、品种、主周期、视角周期。
- squeeze_score及分项: `bb_width_pctile`、`sr_range_pctile`、`pivot_range_pctile`、`adx`、`atr_pctile`。
- State字段: `mn1_hex_h1_view`、`w1_hex_h1_view`、`d1_hex_h1_view`、`h4_hex_h1_view`、`h1_hex_h1_view`。
- 高周期趋势: H4/D1 trend bias、direction alignment。
- 收缩锚点: anchor high/low、anchor range、anchor start/end。
- 突破质量: breakout direction、breakout strength ATR、close outside anchor、body ratio。
- 成本状态: spread、commission、expected edge vs cost。
- Agent意见: 哪些Agent支持/反对，理由是什么。

#### 5.4.4 突破后趋势跟踪

突破后不应只看5bar胜负。平台必须记录趋势跟踪过程:

- `mfe_1/5/24/120_bars`
- `mae_1/5/24/120_bars`
- 趋势延续评分: ADX变化、均线斜率、ATR扩张、State transition。
- 回踩行为: 是否回到anchor内、是否假突破。
- 出场触发: fixed hold、structure stop、trailing stop、trend decay。
- 复盘标签:
  - `clean_breakout`
  - `false_breakout`
  - `trend_continuation`
  - `news_driven_no_squeeze`
  - `cost_killed_edge`
  - `higher_tf_conflict`

### 5.5 行业轮动与个股状态评估

#### 5.5.1 行业轮动

面向股票路线，平台应提供:

- 行业指数/ETF强弱排名。
- 行业内个股相对强弱。
- 行业State regime分布。
- 资金流/基本面二级确认。
- 轮动阶段: 低位蓄力、启动、主升、扩散、衰退。

#### 5.5.2 个股状态评估

必须输出:

- 多周期State视角。
- 多指标收缩/扩张状态。
- 基本面摘要。
- 行业内相对强度。
- 观察建议: 观察、待突破、趋势跟随、风险回避。

## 6. 策略生命周期

状态流:

```text
draft
  -> generated
  -> data_audit
  -> quick_backtest
  -> strict_backtest
  -> agent_review
  -> paper_observation
  -> approved_for_manual_execution
  -> live_gated
  -> paused
  -> retired
```

准入门槛:

- `data_audit` 通过才允许正式回测。
- `strict_backtest` 通过才允许Agent复核。
- `agent_review` 通过才允许模拟观察。
- `paper_observation` 至少4周且偏差可解释才允许人工审批执行。
- MVP阶段默认不允许自动实盘。

## 7. 关键界面规格

### 7.1 AI策略生成页

核心组件:

- 对话输入框。
- 策略理解卡片。
- DSL预览。
- 代码版本与manifest。
- 验证状态条。
- 一键回测按钮。

### 7.2 回测报告页

核心组件:

- 准入结论。
- 风险指标概览。
- 权益/回撤图。
- 交易列表。
- 分品种/分State表。
- 成本分析。
- Run Card与审计结论。

### 7.3 实时市场分析页

核心组件:

- 多周期状态矩阵。
- 收缩过程时间线。
- 共振突破雷达。
- 趋势跟踪面板。
- 当前观察名单。
- 异常风险提示。

### 7.4 Agent协作页

核心组件:

- Agent状态流。
- 每个Agent的输入、输出、结论。
- 分歧清单。
- Portfolio Manager裁决。
- 人工确认按钮。

### 7.5 执行与风控页

核心组件:

- MT5/MT4连接状态。
- 账户权益、保证金、持仓。
- 当前信号与执行建议。
- 风控规则命中情况。
- Kill switch。
- dry-run/live状态。

## 8. 非功能需求

### 8.1 性能

- 自然语言策略草案生成: 10秒内返回策略理解卡片。
- 缓存数据快速回测: 单策略、单品种、2年H1数据30秒内返回初版。
- 严格回测: 单策略14品种H1/H4/D1两年数据5分钟内完成。
- 实时扫描: 14个品种H1/M15观察10秒内完成一次状态刷新。
- Agent复核: 可异步执行，页面显示进度和中间结论。

### 8.2 可靠性

- MT5断线必须停止信号生成并告警。
- 回测必须可复现，保存数据版本、代码hash、参数和随机种子。
- 所有正式结论必须保存Run Card。
- 观察和邮件推送失败不得影响主交易风控。

### 8.3 安全性

- 默认 `live_trading=false`、`dry_run=true`。
- LLM不能直接调用MT5下单接口。
- 所有实盘相关操作必须人工确认。
- API密钥、交易密码只允许环境变量或密钥服务，不进入文档、日志和git。

### 8.4 可解释性

每个信号必须能回答:

- 为什么现在进入观察或交易。
- 哪些周期支持，哪些周期反对。
- 收缩过程持续了多久。
- 突破质量如何。
- 成本是否足以吃掉优势。
- 风控为什么允许或拒绝。

## 9. MVP范围与不做清单

### 9.1 MVP必须做

- 自然语言到策略DSL/manifest。
- 基于模板的策略代码生成。
- 快速回测与严格回测。
- 多周期PIT数据审计。
- 成本、滑点、手续费模拟。
- 多Agent复核工作流。
- 观察数据库和日报/邮件通知。
- MT5/MT4连接状态和安全执行建议。

### 9.2 MVP不做

- 不做全自动实盘下单。
- 不做没有审计的Agent自由修改生产代码。
- 不做未通过模拟观察的策略上线。
- 不承诺收益。
- 不把单次高胜率结果作为交易结论。

## 10. 产品验收摘要

| 模块 | 验收标准 |
|---|---|
| 自然语言策略生成 | 20个典型策略描述中，至少18个能生成可读DSL和manifest |
| 代码生成 | 生成策略通过静态检查、禁止直接下单、至少有一条单元测试 |
| 快速回测 | 缓存数据单策略单品种30秒内返回初版指标 |
| 严格回测 | 100%输出Run Card、PIT证明、成本模型、event_id去重统计 |
| 多Agent | 每次复核至少输出研究、数据审计、风控、执行四类意见 |
| 实时分析 | 能输出收缩生命周期、共振突破事件和趋势跟踪记录 |
| 风控 | 默认拒绝实盘；超点差、超手数、超回撤、断线时拒绝交易 |
| 通知 | 复用现有邮件能力输出日报/观察报告，失败有日志 |

