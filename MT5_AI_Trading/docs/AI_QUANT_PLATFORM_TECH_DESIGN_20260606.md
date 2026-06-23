# AI量化策略平台技术方案 v0.1

> 日期: 2026-06-06
> 状态: 草案
> 对应需求文档: `AI_QUANT_PLATFORM_PRD_20260606.md`

## 1. 技术选型结论

平台不直接fork单个开源项目，而采用：

```text
自研编排层 + 自研审计层 + 自研策略资产库 + 可插拔开源引擎适配器
```

原因：

- 我们已有 State Hex、v5 squeeze、MT5观察数据库等资产，直接迁入大项目成本高。
- Lean/NautilusTrader 很强，但重型，适合做中后期严肃复核和实盘适配。
- Qlib/vn.py 的AI投研能力有参考价值，但和当前MT5/H1/M15研究线不完全重合。
- vectorbt/backtesting.py 适合快速研究，但许可证和事件真实性不适合直接作为唯一核心。
- Freqtrade/Hummingbot/Jesse偏加密交易，不应主导当前外汇/黄金/股指路线。

## 2. GitHub项目综合比较

| 项目 | 强项 | 限制 | 对我们的用法 |
|---|---|---|---|
| Microsoft Qlib | AI量化投研、因子、模型、RD-Agent自动因子挖掘 | 更偏股票/因子研究，生产执行不是重点 | 参考研究流程、因子库、自动R&D理念 |
| QuantConnect Lean | 专业事件驱动回测和实盘，多资产，Apache-2.0 | C#/.NET栈较重，接入成本高 | 中期作为严肃回测/实盘适配器候选 |
| vn.py | 国内生态强，交易接口丰富，4.0新增AI多因子投研 | 平台较大，和当前MT5结构不同 | 参考中国市场接口和投研模块；后续接A股/期货 |
| NautilusTrader | Rust核心，确定性事件驱动，研究到实盘一致性强 | LGPL-3.0，学习和工程成本较高 | 中后期作为专业执行/仿真内核候选 |
| vectorbt | 快速向量化扫描，适合大规模参数实验 | Apache 2.0 + Commons Clause，不适合做商业核心卖点 | 仅作为内部研究加速器或可替换适配器 |
| backtesting.py | 简洁、易用、结果指标完整 | AGPL-3.0，复杂撮合和多周期能力有限 | 教学/原型参考，不作为闭源服务核心依赖 |
| Freqtrade | 加密交易成熟，含FreqAI、lookahead-analysis、dry-run | GPL-3.0，偏crypto | 参考反未来函数检测、dry-run和WebUI；不嵌入核心 |
| Hummingbot | CEX/DEX连接器、做市/套利、Apache-2.0、MCP方向 | 偏高频加密做市 | 加密垂直线和AI工具接口参考 |
| Jesse | 加密策略研发体验好，MIT，内置AI优化/ML/Monte Carlo | 生态小于Freqtrade，偏crypto | 参考策略开发体验和优化模式 |
| FinRL/FinRL-X | RL/AI-native量化研究、环境和Agent | RL容易过拟合，生产落地需要强约束 | 作为实验沙箱，不进入MVP主线 |
| Vibe-Trading | AI交易工作台、自然语言、MCP、run card、shadow account | 新项目，快速变化，不执行实盘 | 参考产品体验、Agent编排和安全边界 |

## 3. 总体架构

```text
Web UI / CLI
    |
API Gateway (FastAPI)
    |
Application Services
    |-- Hypothesis Service
    |-- Data Audit Service
    |-- Strategy Service
    |-- Backtest Service
    |-- Observation Service
    |-- Report Service
    |-- Agent Orchestrator
    |
Core Libraries
    |-- PIT Join / merge_asof Validator
    |-- Cost Model
    |-- Event ID / Dedup Engine
    |-- Metrics Engine
    |-- Risk Gate Engine
    |
Storage
    |-- DuckDB metadata and run records
    |-- Parquet OHLCV/features/events/trades
    |-- Strategy code repository
    |-- Report artifacts
    |
Adapters
    |-- MT5 data and spread adapter
    |-- Existing MT5_AI_Trading scripts
    |-- vectorbt optional scanner
    |-- Lean/Nautilus optional engine adapter
    |-- LLM provider adapter
```

## 4. 核心模块设计

### 4.1 数据层

推荐：

- DuckDB: 查询、元数据、运行记录、观察数据库。
- Parquet: 大规模行情、特征、事件、交易明细。
- 文件制品: Markdown报告、CSV导出、策略包。

核心表：

| 表 | 说明 |
|---|---|
| `instruments` | 品种、市场、交易时段、点值、合约信息 |
| `bars` | 标准OHLCV，按symbol/timeframe分区 |
| `higher_tf_bars` | H4/D1/W1/MN1等高周期数据 |
| `features` | squeeze、ADX、SR、BB、State字段 |
| `state_views` | MN1/W1/D1/H4/H1 under H1 view 等状态视角 |
| `cost_snapshots` | MT5实际点差、手续费、滑点估计 |
| `hypotheses` | 策略假设 |
| `strategy_versions` | 策略代码、参数、manifest、hash |
| `backtest_runs` | 回测运行卡片 |
| `events` | setup/trigger事件，含event_id |
| `trades` | 交易明细 |
| `observations` | 模拟盘观察记录 |
| `audit_findings` | 数据、代码、未来函数、成本审计结果 |

### 4.2 PIT Join / merge_asof 服务

这是最高优先级。

接口建议：

```python
join_higher_tf_asof(
    lower_bars,
    higher_bars,
    lower_ts_col="timestamp",
    higher_close_ts_col="close_time",
    by="symbol",
    tolerance=None,
    allow_equal=True,
) -> DataFrame
```

强制规则：

- H1 bar 只能使用在该H1 timestamp之前已经收盘的H4/D1数据。
- 禁止 `i // 4`、`i // 24` 这种位置映射。
- 所有高周期字段必须带 `source_bar_close_time`。
- 审计输出必须证明 `source_bar_close_time <= lower_bar_timestamp`。

测试类型：

1. 边界测试：H4/D1刚形成但未收盘时不可使用。
2. 回放测试：逐bar replay，结果必须与批处理一致。
3. 时间错位测试：故意平移高周期数据，审计必须失败。
4. 时区测试：Asia/Shanghai、本地MT5时间、UTC边界一致。
5. 缺失bar测试：缺口不能自动向未来填充。

### 4.3 成本模型

成本模型分三层：

1. `fixed_cost`: 仅用于历史粗筛。
2. `snapshot_cost`: 使用MT5导入的点差快照。
3. `execution_cost`: 模拟成交时加入滑点、手续费和最小跳动。

正式结论必须使用 `snapshot_cost` 或更高等级。

字段：

```text
symbol
timestamp
bid
ask
spread_points
spread_pct
commission_pct
slippage_pct
source
cost_model_version
```

### 4.4 事件去重

统一event_id：

```text
sha256(
  strategy_family +
  strategy_version +
  symbol +
  timeframe +
  setup_start_ts +
  setup_end_ts +
  trigger_ts +
  direction
)
```

要求：

- 同一突破事件不能因为多个参数、多个观察bar重复计入。
- State和v5必须共用去重接口。
- 报告必须同时输出原始事件数和唯一事件数。

### 4.5 策略模板

每个策略由三部分组成：

```text
strategies/
  squeeze_v5/
    strategy.py
    strategy_manifest.yaml
    tests/
  state_h1_f_short/
    strategy.py
    strategy_manifest.yaml
    tests/
```

`strategy_manifest.yaml` 示例：

```yaml
name: squeeze_v5
family: squeeze_breakout
timeframe: H1
inputs:
  - h1_squeeze_score
  - h1_adx
  - anchor_range_pct
  - h4_trend_bias
  - d1_trend_bias
pit_required: true
cost_model_min_level: snapshot_cost
dedup_required: true
entry:
  type: breakout
exit:
  type: fixed_hold
  bars: 5
risk:
  max_daily_loss_pct: 1.0
  max_positions: 3
```

## 5. Agent架构

Agent只调用受控工具，不直接改核心生产代码或实盘下单。

| Agent | 职责 | 禁止 |
|---|---|---|
| Research Planner | 拆假设、列实验计划 | 禁止直接给交易建议 |
| Data Auditor | 检查PIT、缺失、时区、成本 | 禁止跳过一票否决项 |
| Strategy Coder | 生成策略插件和测试 | 禁止写入未授权路径 |
| Backtest Runner | 运行回测并生成Run Card | 禁止修改回测结果 |
| Risk Reviewer | 审计过拟合、样本、成本、回撤 | 禁止批准未观察策略 |
| Report Writer | 总结证据和下一步 | 禁止夸大结论 |
| Operator Assistant | 生成模拟盘/人工执行清单 | MVP禁止自动实盘 |

所有Agent输出必须落库：

- prompt摘要
- 工具调用
- 输入数据版本
- 输出文件
- 审计结论
- 人工确认状态

## 6. 回测引擎分层

### 6.1 Fast Scanner

用于快速参数扫描：

- 可自研pandas/NumPy实现。
- 可选接vectorbt作为适配器。
- 输出只作为候选，不作为最终结论。

### 6.2 Strict Backtester

用于正式结论：

- 逐bar事件驱动。
- 严格PIT Join。
- 真实event_id去重。
- 成本快照。
- 交易状态机。
- 结果可复现。

### 6.3 External Engine Adapter

中后期接入：

- Lean：多资产、专业回测和实盘。
- NautilusTrader：确定性事件驱动和研究到实盘一致性。
- vn.py：国内交易接口和实盘模块。

MVP不依赖这些重型引擎完成第一版。

## 7. 审计门槛

策略进入模拟观察前必须全部通过：

1. `PIT_JOIN_PASS`
2. `COST_MODEL_PASS`
3. `DEDUP_PASS`
4. `TRAIN_VAL_TEST_PASS`
5. `MIN_SAMPLE_PASS`
6. `OOS_POSITIVE_OR_EXPLAINED`
7. `UNIT_TEST_PASS`
8. `RISK_LIMIT_DEFINED`

策略进入人工执行前必须额外通过：

1. 模拟盘至少4周。
2. 每个入选品种实时信号不少于5个。
3. 回测和模拟盘偏差可解释。
4. 最大日亏损、最大持仓、单笔风险已配置。
5. 人工审批。

## 8. State路线复核方案

针对 `H1=-F/short/5bars`：

必须重跑：

1. 是否扣除MT5实际成本。
2. 是否按统一event_id去重。
3. 是否存在同一bar、同一symbol、同一direction重复计入。
4. 是否有高周期状态未来函数。
5. 是否和v5使用同一Train/Val/Test划分。
6. 是否按品种、年份、市场状态分层稳定。

输出：

- `state_h1_f_short_audit_YYYYMMDD.md`
- `state_h1_f_short_events_YYYYMMDD.csv`
- `state_h1_f_short_trades_YYYYMMDD.csv`
- `state_h1_f_short_run_card_YYYYMMDD.json`

如果重跑后仍保持高胜率且净期望稳定，State路线优先级提升到v5之上。

## 9. MVP实施路线

### Milestone 0: 工程清理

- `MT5_AI_Trading/` 和 `mt4-data-processor/` 分开提交。
- 新增 `platform/` 或 `MT5_AI_Trading/platform/` 作为平台化代码入口。
- 把现有研究脚本归档或改造成策略插件。

### Milestone 1: 数据审计核心

- 实现 PIT Join 服务。
- 实现 `merge_asof` replay测试。
- 实现成本快照表。
- 实现event_id统一生成。

### Milestone 2: v5策略平台化

- 将 `squeeze_multi_timeframe_research_v5.py` 拆成策略插件。
- 生成manifest。
- 补单元测试。
- 输出Run Card。

### Milestone 3: State路线复核

- 将 `H1=-F/short/5bars` 放入同一审计框架。
- 重跑成本、去重、walk-forward。
- 与v5在同一Dashboard比较。

### Milestone 4: AI研究助手MVP

- 实现自然语言创建假设。
- Agent生成实验计划。
- Agent调用受控回测命令。
- Agent输出报告草稿。
- 人工确认后归档。

### Milestone 5: 模拟观察Dashboard

- 接入 `observation_db.py`。
- 展示策略信号、期望、实际、异常。
- 输出日报和周报。

## 10. 许可证和商业化注意

- Lean: Apache-2.0，适合商业集成。
- Qlib: MIT，适合参考和集成。
- vn.py: MIT，适合参考和二次开发。
- NautilusTrader: LGPL-3.0，需注意链接和修改发布义务。
- vectorbt: Apache-2.0 with Commons Clause，不能把它作为主要商业售卖的软件能力。
- backtesting.py: AGPL-3.0，闭源SaaS嵌入风险高。
- Freqtrade: GPL-3.0，不建议嵌入闭源核心。
- Hummingbot: Apache-2.0，可作为加密连接器/做市参考。
- Jesse: MIT，可参考策略体验。

## 11. 当前仓库落地建议

短期目录建议：

```text
MT5_AI_Trading/
  platform/
    data/
    audit/
    costs/
    strategies/
    backtest/
    agents/
    reports/
    api/
  docs/
    AI_QUANT_PLATFORM_PRD_20260606.md
    AI_QUANT_PLATFORM_TECH_DESIGN_20260606.md
```

第一批代码任务：

1. `platform/audit/pit_join.py`
2. `platform/audit/test_pit_join.py`
3. `platform/costs/mt5_spread_snapshot.py`
4. `platform/events/event_id.py`
5. `platform/strategies/squeeze_v5/`
6. `platform/strategies/state_h1_f_short/`

## 12. 参考来源

- Qlib: https://github.com/microsoft/qlib
- QuantConnect Lean: https://github.com/QuantConnect/Lean
- vn.py: https://github.com/vnpy/vnpy
- NautilusTrader: https://github.com/nautechsystems/nautilus_trader
- vectorbt: https://github.com/polakowo/vectorbt
- backtesting.py: https://github.com/kernc/backtesting.py
- Freqtrade: https://github.com/freqtrade/freqtrade
- Hummingbot: https://github.com/hummingbot/hummingbot
- Jesse: https://github.com/jesse-ai/jesse
- FinRL: https://github.com/AI4Finance-Foundation/FinRL
- Vibe-Trading: https://github.com/HKUDS/Vibe-Trading
