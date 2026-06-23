# codex AI量化多周期视角交易平台技术架构与详细设计

版本: v1.0-codex
日期: 2026-06-06
对应产品文档: `codex_ai_quant_platform_product_spec_20260606.md`

## 1. 技术目标

建设一个可审计、可扩展、可从研究演进到模拟观察和受控执行的AI量化平台。平台以现有 `MT5_AI_Trading` 为核心，不推翻已有成果，而是把当前脚本、State数据库、回测系统、MT5/MT4桥接和邮件通知整合成模块化系统。

核心目标:

- 自然语言策略生成后可以进入受控策略DSL、manifest和代码生成流程。
- 回测系统支持30秒快速反馈和严格事件驱动复核。
- 多Agent系统以“研究、实现、审计、风控、执行、报告”的职责边界协作。
- 实时市场分析能记录多周期多指标收缩、共振突破和趋势跟踪全过程。
- 与MT5/MT4连接时默认安全，不让LLM绕过风控直接下单。

## 2. 现有项目资产映射

| 资产 | 当前路径 | 新平台角色 |
|---|---|---|
| MT5 ZeroMQ方案 | `MT5_AI量化交易系统技术方案.md` | 分布式通信设计依据 |
| MT5 ZeroMQ Python桥 | `python/core/mt5_bridge.py`、`mt5_bridge_dual.py` | 行情订阅、交易指令、心跳、双MT5 |
| MT5 EA桥 | `mql5/Experts/AI_Trading_Bridge.mq5` | MT5端PUB/REP桥接 |
| MT5 Python API桥 | `python/core/mt5_python_api.py`、`config/trading_config.yaml` | 本地官方API接入、默认执行桥 |
| 主控制器 | `python/core/main_controller.py` | 现有实时交易编排和安全开关参考 |
| MT4 CSV桥 | `MT4/EA/AI_MT4_Bridge.mq4`、`python/core/mt4_bridge_csv.py` | MT4数据回退和并行观察 |
| 回测平台雏形 | `python/backtest_platform/` | 数据层、计算层、策略层、执行层、展示层基础 |
| State契约 | `docs/STATE_VIEWPOINT_AGENT_CONTRACT.md` | 多周期视角Agent硬约束 |
| 多周期收缩研究 | `squeeze_multi_timeframe_research_v5.py`、`python/analytics/multi_timeframe_squeeze.py` | 收缩/共振/突破研究核心 |
| State升级方案 | `docs/SQUEEZE_MT_STATE_STRATEGY_UPGRADE_20260605.md` | State Gate与OpportunityScore依据 |
| 观察数据库 | `observation_db.py` | 模拟盘观察、复现提醒和日报基础 |
| MT4数据处理 | `process_real_mt4_data.py`、`csv_color_marker.py` | CSV转Excel/截图、颜色标记、报告附件 |
| 邮件系统 | `email_sender.py`、`scheduler.py` | 日报、预警、观察报告推送 |

## 3. 总体架构

### 3.1 分层架构

```text
Client/UI Layer
  |-- Web Dashboard
  |-- CLI
  |-- Email/Report Viewer

Application/API Layer (FastAPI)
  |-- Strategy Generation API
  |-- Backtest API
  |-- Agent Orchestration API
  |-- Market Analysis API
  |-- Risk/Execution API
  |-- Report API

Agent Orchestration Layer
  |-- Research Planner Agent
  |-- Strategy Coder Agent
  |-- Data Auditor Agent
  |-- Backtest Agent
  |-- Research Agent
  |-- Risk Agent
  |-- Execution Agent
  |-- Portfolio Manager Agent
  |-- Report Agent

Core Quant Layer
  |-- Strategy DSL and Manifest
  |-- PIT Join / Multi-timeframe Aligner
  |-- Indicator and State Feature Engine
  |-- Squeeze/Resonance/Breakout Engine
  |-- Backtest Engine
  |-- Metrics Engine
  |-- Cost and Slippage Engine
  |-- Risk Gate Engine

Bridge/Adapter Layer
  |-- MT5 ZeroMQ Adapter
  |-- MT5 Python API Adapter
  |-- MT4 CSV Adapter
  |-- SQX Export Adapter
  |-- Email Adapter
  |-- Optional External Engine Adapters (Lean/Qlib/FinRL)

Storage Layer
  |-- DuckDB: 本地研究、状态、观察、运行记录
  |-- SQLite: 轻量回退和单机缓存
  |-- Parquet/CSV: 大规模行情、特征、事件、交易明细
  |-- Markdown/HTML/JSON: 报告制品
  |-- Git: 策略代码版本
```

### 3.2 关键设计原则

1. `State Viewpoint` 是硬契约  
   H1 Agent必须输出 `MN1/W1/D1/H4/H1 @ H1_view`，M15 Agent是独立视角系统，不允许用原生高周期state简单对齐替代。

2. 数据审计先于回测  
   所有正式回测必须有PIT对齐证明、缺失数据报告、成本模型和event_id去重。

3. 快速回测不等于正式结论  
   快速回测用于反馈和筛选，严格回测用于报告和准入。

4. Agent只能调用受控工具  
   Agent不直接写生产路径、不直接下单、不覆盖风控。

5. 默认只观察和dry-run  
   现有配置 `live_trading=false`、`dry_run=true` 作为平台默认。

## 4. 核心模块详细设计

### 4.1 自然语言处理模块

#### 4.1.1 职责

- 解析用户策略描述。
- 提取品种、周期、指标、条件、出场、风控、回测范围。
- 生成策略理解卡片。
- 生成策略DSL和 `strategy_manifest.yaml`。
- 将无法确定的条件标记为待确认，不直接猜测成交易规则。

#### 4.1.2 组件

```text
NaturalLanguageStrategyService
  |-- IntentParser
  |-- StrategySlotExtractor
  |-- AmbiguityResolver
  |-- StrategyDSLBuilder
  |-- ManifestBuilder
  |-- SafetyPolicyChecker
```

#### 4.1.3 输入输出

输入:

```json
{
  "user_id": "u001",
  "text": "创建一个均线金叉策略，MA5上穿MA20时买入，跌破MA10时卖出",
  "defaults": {
    "symbols": ["EURUSD"],
    "main_timeframe": "H1",
    "risk_per_trade_pct": 1.0
  }
}
```

输出:

```json
{
  "strategy_id": "ma_cross_h1_v1",
  "status": "draft",
  "understanding": {
    "entry": "MA5 cross above MA20",
    "exit": "close below MA10",
    "direction": "long",
    "main_timeframe": "H1"
  },
  "dsl": {},
  "manifest_path": "MT5_AI_Trading/platform/strategies/ma_cross_h1_v1/strategy_manifest.yaml",
  "missing_fields": [],
  "safety_flags": []
}
```

### 4.2 策略生成引擎

#### 4.2.1 职责

- 将DSL编译为策略插件。
- 使用模板优先，不自由生成底层框架。
- 生成单元测试和小样本验证。
- 保存策略版本、代码hash和manifest。

#### 4.2.2 目录建议

```text
MT5_AI_Trading/
  platform/
    strategies/
      ma_cross_h1_v1/
        strategy.py
        strategy_manifest.yaml
        tests/
          test_strategy.py
        generated_by.json
```

#### 4.2.3 策略插件接口

```python
class BaseStrategyPlugin:
    strategy_id: str
    version: str

    def required_features(self) -> list[str]:
        ...

    def generate_events(self, feature_frame) -> list[StrategyEvent]:
        ...

    def generate_orders(self, event, portfolio_state) -> list[OrderIntent]:
        ...

    def validate_manifest(self) -> ValidationResult:
        ...
```

生成策略不得调用 `MT5Bridge.send_order` 或 `MT5PythonAPIBridge.order_send`。所有订单必须先变成 `OrderIntent`，交由风控和执行服务处理。

### 4.3 数据处理模块

#### 4.3.1 数据源

- MT5 Python API: 默认历史数据与行情轮询。
- MT5 ZeroMQ: 分布式实时行情和执行指令。
- MT4 CSV: 通过 `AI_MT4_Bridge.mq4` 定时写CSV，Python读取。
- 本地CSV/Parquet/DuckDB: 回测和复盘。

#### 4.3.2 PIT Join服务

正式接口:

```python
def join_higher_tf_asof(
    lower_bars: pd.DataFrame,
    higher_bars: pd.DataFrame,
    by: str = "symbol",
    lower_ts_col: str = "timestamp",
    higher_close_ts_col: str = "close_time",
    suffix: str = "h4",
    tolerance: str | None = None
) -> pd.DataFrame:
    """把已经收盘的高周期bar as-of对齐到低周期bar。"""
```

硬规则:

- `higher_close_time <= lower.timestamp`。
- 输出每个高周期字段的 `source_close_time`。
- 禁止用数组位置映射。
- 批处理结果必须与逐bar replay一致。

#### 4.3.3 数据质量检查

字段:

- `missing_values`
- `duplicate_bars`
- `gap_count`
- `timezone`
- `first_timestamp`
- `last_timestamp`
- `price_anomalies`
- `source`
- `quality_score`

质量低于阈值时只允许研究，不允许正式回测。

### 4.4 指标与State特征模块

#### 4.4.1 指标引擎

支持:

- MA/SMA/EMA
- RSI/MACD/ADX/ATR
- BB Width
- SR Range
- Pivot/ACD Pivot Range
- Keltner/Donchian/SuperTrend
- Volume/Moneyflow
- 自定义MT4/MT5指标导入

#### 4.4.2 State View Engine

必须基于 `STATE_VIEWPOINT_AGENT_CONTRACT.md`:

```text
state_view_snapshot
  timestamp
  view_tf
  structure_tf
  state_hex
  base_component
  trend_component
  volatility_component
  position_component
  view_close
  structure_sr_high
  structure_sr_low
  source_structure_close_time
```

H1视角宽表可包含:

- `mn1_hex_h1_view`
- `w1_hex_h1_view`
- `d1_hex_h1_view`
- `h4_hex_h1_view`
- `h1_hex_h1_view`
- `state_direction_alignment`
- `state_contraction_count`
- `state_breakout_count`
- `state_transition_1`
- `state_transition_3`

### 4.5 多指标收缩与共振突破模块

#### 4.5.1 收缩评分

建议沿用并规范化v5思想:

```text
SqueezeScore =
  bb_width_low
  + sr_range_low
  + pivot_range_low
  + adx_low
  + atr_low_or_stable
  + volume_contracting
```

M15可使用更高门槛，避免信号过密。

#### 4.5.2 OpportunityScore

继承 `SQUEEZE_MT_STATE_STRATEGY_UPGRADE_20260605.md`:

```text
OpportunityScore =
  0.35 * StateScore
  + 0.25 * TrendResonanceScore
  + 0.20 * SqueezeQualityScore
  + 0.15 * BreakoutQualityScore
  - 0.05 * CostPenalty
```

评分结果只作为过滤和排序依据，不单独作为下单理由。

#### 4.5.3 事件生命周期表

生命周期:

```text
NO_SETUP
CONTRACTION_DISCOVERED
CONTRACTION_BUILDING
RESONANCE_ARMED
BREAKOUT_TRIGGERED
BREAKOUT_CONFIRMED
TREND_TRACKING
EXITED
POST_MORTEM
```

每次状态变化写入 `market_process_events`。

### 4.6 回测引擎

#### 4.6.1 两级回测

快速回测:

- 输入已缓存特征。
- 向量化或半向量化。
- 用于30秒反馈。
- 输出不作为最终上线依据。

严格回测:

- 逐bar事件驱动。
- PIT Join replay。
- 真实成本。
- event_id去重。
- 订单状态机。
- 输出正式Run Card。

#### 4.6.2 回测Run Card

```json
{
  "run_id": "bt_20260606_001",
  "strategy_id": "squeeze_state_h1_v1",
  "strategy_hash": "sha256...",
  "data_version": "data_20260606",
  "symbols": ["EURUSD", "XAUUSD"],
  "timeframes": ["H1", "H4", "D1"],
  "start": "2024-06-01",
  "end": "2026-06-01",
  "cost_model": "snapshot_cost_v1",
  "pit_audit_id": "pit_20260606_001",
  "dedup_policy": "event_id_v1",
  "train_val_test": {
    "train": ["2024-06-01", "2025-06-01"],
    "validation": ["2025-06-02", "2025-12-31"],
    "test": ["2026-01-01", "2026-06-01"]
  },
  "status": "completed"
}
```

#### 4.6.3 绩效指标

必须输出:

- gross/net pnl
- win_rate
- profit_factor
- expectancy
- sharpe/sortino/calmar
- max_drawdown
- max_consecutive_losses
- avg_mfe/avg_mae
- cost_drag
- per_symbol/per_direction/per_state/per_session metrics

### 4.7 多Agent系统

#### 4.7.1 编排模型

建议使用图式工作流:

```text
START
  -> ResearchPlanner
  -> StrategyCoder
  -> DataAuditor
  -> BacktestRunner
  -> ResearchReviewer
  -> RiskReviewer
  -> ExecutionReviewer
  -> PortfolioManager
  -> ReportWriter
END
```

未来可用LangGraph实现checkpoint、human-in-the-loop和可观测性；MVP可先用自研状态机。

#### 4.7.2 Agent输出协议

```json
{
  "agent_id": "risk_agent",
  "run_id": "agent_run_001",
  "input_refs": ["bt_20260606_001"],
  "decision": "reject|pass|needs_human_review",
  "confidence": "low|medium|high",
  "findings": [
    {
      "severity": "high",
      "title": "Test sample too small",
      "evidence": "test_trades=42 < 300"
    }
  ],
  "next_actions": [],
  "artifact_paths": []
}
```

#### 4.7.3 Agent安全边界

- Agent不能直接访问交易密码。
- Agent不能直接调用下单API。
- Agent不能修改已有策略版本，只能创建新版本。
- Agent输出必须落库。
- Agent建议必须经过Risk Gate和人工审批。

### 4.8 实时市场分析模块

#### 4.8.1 数据流

```text
MT5/MT4 tick or bar
  -> Bar Aggregator
  -> Feature Engine
  -> State View Engine
  -> Squeeze Process Tracker
  -> Resonance Detector
  -> Trend Tracking Engine
  -> Observation DB
  -> Report/Alert
```

#### 4.8.2 市场状态快照

```json
{
  "symbol": "XAUUSD",
  "timestamp": "2026-06-06T10:00:00",
  "view_tf": "H1",
  "stage": "RESONANCE_ARMED",
  "squeeze_score": 5,
  "state_alignment": 1,
  "trend_resonance_score": 2,
  "opportunity_score": 7.2,
  "cost_pct": 0.015,
  "agent_summary": "H1/H4 support, D1 neutral"
}
```

### 4.9 执行与风控模块

#### 4.9.1 执行链路

```text
StrategySignal
  -> RiskGate
  -> ExecutionPlan
  -> HumanApproval
  -> ExecutionAdapter
  -> BrokerResult
  -> TradeJournal
```

#### 4.9.2 RiskGate硬规则

- `live_trading=false` 时拒绝真实下单。
- `dry_run=true` 时只记录模拟执行。
- 单笔风险超过阈值拒绝。
- 手数超过 `hard_max_lot_size` 拒绝。
- 点差超过 `max_spread_points` 拒绝。
- MT5断线或心跳超时拒绝。
- 当前回撤超过 `max_drawdown` 拒绝。
- 单日亏损超过 `max_risk_per_day` 拒绝。
- 信号冷却期内拒绝。
- 数据审计未通过拒绝。

## 5. API接口规范

### 5.1 REST API

#### 策略生成

`POST /api/v1/strategies/generate`

请求:

```json
{
  "text": "MA5上穿MA20买入，跌破MA10卖出",
  "symbols": ["EURUSD"],
  "main_timeframe": "H1"
}
```

响应:

```json
{
  "strategy_id": "ma_cross_h1_v1",
  "status": "generated",
  "manifest": {},
  "artifact_paths": []
}
```

#### 策略验证

`POST /api/v1/strategies/{strategy_id}/validate`

响应:

```json
{
  "strategy_id": "ma_cross_h1_v1",
  "validation_status": "pass",
  "checks": [
    {"name": "syntax", "status": "pass"},
    {"name": "no_direct_order", "status": "pass"},
    {"name": "pit_required", "status": "pass"}
  ]
}
```

#### 回测

`POST /api/v1/backtests`

请求:

```json
{
  "strategy_id": "ma_cross_h1_v1",
  "mode": "quick|strict",
  "symbols": ["EURUSD", "XAUUSD"],
  "start": "2024-06-01",
  "end": "2026-06-01",
  "cost_model": "snapshot_cost_v1"
}
```

响应:

```json
{
  "run_id": "bt_20260606_001",
  "status": "queued|running|completed|failed",
  "summary": {
    "net_expectancy": 0.0012,
    "win_rate": 0.54,
    "max_drawdown_pct": 6.4
  },
  "report_path": "MT5_AI_Trading/reports/..."
}
```

#### Agent复核

`POST /api/v1/agent-runs`

```json
{
  "topic": "review_strategy",
  "strategy_id": "ma_cross_h1_v1",
  "backtest_run_id": "bt_20260606_001",
  "agents": ["data_auditor", "research", "risk", "execution", "portfolio_manager"]
}
```

#### 市场状态

`GET /api/v1/market/state?symbol=XAUUSD&view_tf=H1`

响应:

```json
{
  "symbol": "XAUUSD",
  "view_tf": "H1",
  "snapshot": {},
  "process_stage": "CONTRACTION_BUILDING",
  "opportunity_score": 5.8
}
```

#### 执行计划

`POST /api/v1/execution/plans`

```json
{
  "signal_id": "sig_001",
  "account_id": "avatrade_demo",
  "mode": "dry_run"
}
```

响应:

```json
{
  "plan_id": "exec_plan_001",
  "risk_status": "pass|reject",
  "orders": [],
  "requires_human_approval": true
}
```

### 5.2 MT5/MT4 ZeroMQ接口

#### PUB行情消息

MT5 EA当前已支持:

```json
{
  "type": "tick",
  "symbol": "EURUSD",
  "bid": 1.08501,
  "ask": 1.08513,
  "last": 0,
  "volume": 123,
  "time": 1717040000,
  "time_msc": 1717040000123,
  "spread": 0.00012
}
```

建议扩展bar消息:

```json
{
  "type": "bar",
  "symbol": "EURUSD",
  "timeframe": "H1",
  "timestamp": "2026-06-06T10:00:00",
  "open": 1.08,
  "high": 1.09,
  "low": 1.07,
  "close": 1.085,
  "volume": 1000,
  "closed": true
}
```

#### REQ/REP心跳

请求:

```json
{"type": "ping", "request_id": "req_001"}
```

响应:

```json
{"type": "pong", "time": 12345678, "request_id": "req_001"}
```

#### 订单请求

必须增加安全字段:

```json
{
  "type": "order",
  "request_id": "ord_001",
  "strategy_id": "ma_cross_h1_v1",
  "signal_id": "sig_001",
  "risk_approval_id": "risk_001",
  "action": "BUY",
  "symbol": "EURUSD",
  "volume": 0.01,
  "sl": 1.0800,
  "tp": 1.0950,
  "max_slippage_points": 10,
  "comment": "AI_dryrun_or_approved"
}
```

响应:

```json
{
  "type": "order_result",
  "request_id": "ord_001",
  "success": true,
  "ticket": 123456,
  "volume": 0.01,
  "price": 1.08513,
  "symbol": "EURUSD",
  "action": "BUY"
}
```

### 5.3 内部事件总线

建议事件类型:

- `strategy.generated`
- `strategy.validated`
- `backtest.started`
- `backtest.completed`
- `agent.review.completed`
- `market.contraction_detected`
- `market.resonance_armed`
- `market.breakout_triggered`
- `risk.rejected`
- `execution.plan_created`
- `execution.order_sent`
- `report.generated`

事件格式:

```json
{
  "event_id": "evt_001",
  "event_type": "market.breakout_triggered",
  "timestamp": "2026-06-06T10:00:00",
  "entity_type": "symbol",
  "entity_id": "XAUUSD",
  "payload": {},
  "trace_id": "trace_001"
}
```

## 6. 数据库设计

### 6.1 存储选型

- DuckDB: 默认本地分析库，承载回测、观察、状态和运行记录。
- Parquet: 大表按 `symbol/timeframe/date` 分区。
- SQLite: 无DuckDB环境时回退。
- Markdown/HTML/JSON: 报告制品。

### 6.2 核心表

#### instruments

```sql
CREATE TABLE instruments (
    symbol VARCHAR PRIMARY KEY,
    market VARCHAR,
    broker_symbol VARCHAR,
    asset_class VARCHAR,
    point_size DOUBLE,
    tick_size DOUBLE,
    lot_size DOUBLE,
    min_lot DOUBLE,
    max_lot DOUBLE,
    trading_hours_json JSON,
    enabled BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### bars

```sql
CREATE TABLE bars (
    symbol VARCHAR,
    timeframe VARCHAR,
    timestamp TIMESTAMP,
    close_time TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    source VARCHAR,
    data_version VARCHAR,
    PRIMARY KEY (symbol, timeframe, timestamp)
);
```

#### state_view_snapshots

```sql
CREATE TABLE state_view_snapshots (
    snapshot_id VARCHAR PRIMARY KEY,
    symbol VARCHAR,
    view_tf VARCHAR,
    timestamp TIMESTAMP,
    view_close DOUBLE,
    mn1_hex VARCHAR,
    w1_hex VARCHAR,
    d1_hex VARCHAR,
    h4_hex VARCHAR,
    h1_hex VARCHAR,
    m30_hex VARCHAR,
    m15_hex VARCHAR,
    state_direction_alignment DOUBLE,
    state_contraction_count INTEGER,
    state_breakout_count INTEGER,
    transition_1 JSON,
    transition_3 JSON,
    source_detail JSON
);
```

#### feature_snapshots

```sql
CREATE TABLE feature_snapshots (
    feature_id VARCHAR PRIMARY KEY,
    symbol VARCHAR,
    timeframe VARCHAR,
    timestamp TIMESTAMP,
    bb_width_pctile DOUBLE,
    sr_range_pctile DOUBLE,
    pivot_range_pctile DOUBLE,
    adx DOUBLE,
    atr DOUBLE,
    atr_pctile DOUBLE,
    squeeze_score INTEGER,
    h4_trend_bias VARCHAR,
    d1_trend_bias VARCHAR,
    trend_alignment DOUBLE,
    data_version VARCHAR
);
```

#### market_process_events

```sql
CREATE TABLE market_process_events (
    process_event_id VARCHAR PRIMARY KEY,
    symbol VARCHAR,
    view_tf VARCHAR,
    stage VARCHAR,
    timestamp TIMESTAMP,
    setup_id VARCHAR,
    event_id VARCHAR,
    direction VARCHAR,
    squeeze_score INTEGER,
    opportunity_score DOUBLE,
    state_score DOUBLE,
    trend_resonance_score DOUBLE,
    squeeze_quality_score DOUBLE,
    breakout_quality_score DOUBLE,
    cost_penalty DOUBLE,
    payload JSON,
    created_at TIMESTAMP
);
```

#### strategy_versions

```sql
CREATE TABLE strategy_versions (
    strategy_id VARCHAR,
    version VARCHAR,
    family VARCHAR,
    source VARCHAR,
    status VARCHAR,
    manifest_json JSON,
    code_hash VARCHAR,
    created_by VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (strategy_id, version)
);
```

#### backtest_runs

```sql
CREATE TABLE backtest_runs (
    run_id VARCHAR PRIMARY KEY,
    strategy_id VARCHAR,
    strategy_version VARCHAR,
    mode VARCHAR,
    data_version VARCHAR,
    cost_model_id VARCHAR,
    pit_audit_id VARCHAR,
    start_ts TIMESTAMP,
    end_ts TIMESTAMP,
    status VARCHAR,
    metrics_json JSON,
    run_card_json JSON,
    report_path VARCHAR,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### strategy_events

```sql
CREATE TABLE strategy_events (
    event_id VARCHAR PRIMARY KEY,
    run_id VARCHAR,
    strategy_id VARCHAR,
    symbol VARCHAR,
    timeframe VARCHAR,
    setup_start_ts TIMESTAMP,
    setup_end_ts TIMESTAMP,
    trigger_ts TIMESTAMP,
    direction VARCHAR,
    event_type VARCHAR,
    dedup_key VARCHAR,
    feature_json JSON,
    state_json JSON
);
```

#### trades

```sql
CREATE TABLE trades (
    trade_id VARCHAR PRIMARY KEY,
    run_id VARCHAR,
    event_id VARCHAR,
    symbol VARCHAR,
    direction VARCHAR,
    entry_ts TIMESTAMP,
    exit_ts TIMESTAMP,
    entry_price DOUBLE,
    exit_price DOUBLE,
    gross_pnl DOUBLE,
    net_pnl DOUBLE,
    pnl_pct DOUBLE,
    cost_pct DOUBLE,
    mfe DOUBLE,
    mae DOUBLE,
    exit_rule VARCHAR,
    payload JSON
);
```

#### cost_snapshots

```sql
CREATE TABLE cost_snapshots (
    cost_id VARCHAR PRIMARY KEY,
    symbol VARCHAR,
    timestamp TIMESTAMP,
    bid DOUBLE,
    ask DOUBLE,
    spread_points DOUBLE,
    spread_pct DOUBLE,
    commission_pct DOUBLE,
    slippage_pct DOUBLE,
    source VARCHAR,
    cost_model_version VARCHAR
);
```

#### agent_runs

```sql
CREATE TABLE agent_runs (
    agent_run_id VARCHAR PRIMARY KEY,
    agent_id VARCHAR,
    trace_id VARCHAR,
    input_refs JSON,
    decision VARCHAR,
    confidence VARCHAR,
    findings_json JSON,
    artifact_paths JSON,
    created_at TIMESTAMP
);
```

#### observation_records

可兼容并扩展 `observation_db.py`:

```sql
CREATE TABLE observation_records (
    observation_id VARCHAR PRIMARY KEY,
    strategy_id VARCHAR,
    symbol VARCHAR,
    timestamp TIMESTAMP,
    stage VARCHAR,
    signal_json JSON,
    expected_metrics_json JSON,
    actual_followup_json JSON,
    status VARCHAR,
    notes VARCHAR
);
```

### 6.3 event_id规范

```text
event_id = sha256(
  strategy_family + "|" +
  strategy_version + "|" +
  symbol + "|" +
  timeframe + "|" +
  setup_start_ts + "|" +
  setup_end_ts + "|" +
  trigger_ts + "|" +
  direction
)
```

同一真实突破事件不能因多参数、多观察bar、多出场规则重复计入胜率。

## 7. 安全与风控机制

### 7.1 资金风险管理

- 单笔风险: 默认不超过账户权益1%到2%。
- 单日风险: 默认不超过6%。
- 最大回撤: 默认10%，触发后停止新开仓。
- 最大持仓数: 全局和单品种双限制。
- 最大手数: `hard_max_lot_size` 为不可被策略覆盖的硬上限。
- 品种风险权重: 黄金、加密、股指可设置更低仓位。

### 7.2 交易限额控制

- max_lot_size
- max_notional
- max_positions
- max_symbol_positions
- signal_cooldown_seconds
- max_spread_points
- max_slippage_points
- allowed_sessions
- blocked_news_windows

### 7.3 异常交易监控

触发条件:

- MT5心跳失败。
- 成交价偏离预期超过阈值。
- 连续拒单。
- 点差异常放大。
- 短时间内重复信号。
- 账户权益突降。
- 持仓和系统记录不一致。
- 数据源停止更新。

处理动作:

- 停止新信号。
- 切换观察模式。
- 邮件告警。
- 标记策略暂停。
- 必要时执行人工确认的紧急平仓。

### 7.4 系统安全防护

- 密钥只放环境变量或密钥管理服务。
- API使用认证、权限和审计日志。
- ZeroMQ端口仅允许白名单IP。
- 生产环境和研究环境分端口、分账户、分配置。
- Agent工具权限最小化。
- 所有执行请求必须带 `risk_approval_id`。
- LLM输出不得直接进入MT5执行适配器。

## 8. 分阶段实施路线图

### Phase 0: 文档与边界整理，1周

交付:

- codex PRD与技术设计。
- 现有代码资产映射。
- 平台目录规划。
- 策略生命周期和风控边界确认。

验收:

- 文档包含产品、技术、API、数据库、风控、路线图、验收。
- 文件名包含 `codex`。

### Phase 1: 数据审计与策略manifest，2-3周

任务:

- 新建 `MT5_AI_Trading/platform/`。
- 实现策略manifest schema。
- 实现PIT Join服务和测试。
- 实现cost snapshot导入。
- 实现event_id生成和去重。
- 把v5 squeeze策略包装为策略插件。

交付:

- `platform/audit/pit_join.py`
- `platform/costs/cost_model.py`
- `platform/events/event_id.py`
- `platform/strategies/squeeze_state_h1/`

验收:

- PIT replay测试通过。
- v5策略可从manifest加载。
- 正式回测输出event_id去重统计。

### Phase 2: 自然语言策略生成MVP，3-4周

任务:

- 实现自然语言到DSL。
- 实现策略理解卡片。
- 实现模板式代码生成。
- 实现安全检查和小样本验证。
- 支持均线、ADX、BB/SR、State Gate四类策略。

验收:

- 20个典型策略描述中18个可生成DSL。
- 生成策略不能直接下单。
- 每个策略生成manifest和至少一个测试。

### Phase 3: 智能回测与报告，3-5周

任务:

- 快速回测API。
- 严格回测API。
- 成本/滑点/手续费模型。
- Run Card。
- Markdown/HTML报告。
- 分State、分品种、分方向统计。

验收:

- 缓存数据单品种回测30秒内返回。
- 严格回测输出PIT、成本、去重、Train/Val/Test。
- 结果可复现。

### Phase 4: 多Agent协作系统，4-6周

任务:

- Agent状态机。
- Research/Data/Risk/Execution/Portfolio Manager Agent。
- Agent输出落库。
- 分歧报告。
- 人工确认机制。

验收:

- 每次策略复核至少4类Agent输出。
- Data Auditor失败会中断流程。
- Risk Agent拒绝时执行计划不可生成。

### Phase 5: 实时市场分析与观察，4-6周

任务:

- 多周期状态快照。
- 收缩生命周期记录。
- 共振突破事件。
- 趋势跟踪指标。
- 对接 `observation_db.py`。
- 对接邮件/日报。

验收:

- 实时扫描14品种10秒内完成。
- 每个setup有完整生命周期。
- 每日报告包含观察、信号、实际后续走势和异常。

### Phase 6: 受控执行与Web工作台，6-10周

任务:

- Web Dashboard。
- 执行计划与人工审批。
- MT5/MT4连接状态页。
- 风控页和kill switch。
- 多账户双MT5管理。

验收:

- 默认只dry-run。
- 所有真实执行请求必须人工批准并带risk approval。
- 断线、超点差、超手数、超回撤均拒绝下单。

## 9. 验收标准

### 9.1 自然语言策略生成

- 输入普通中文策略描述后生成DSL、manifest、策略代码。
- 不确定条件必须提示用户或使用显式默认值。
- 代码通过安全扫描。

### 9.2 回测

- 快速回测30秒内返回初版。
- 严格回测保存Run Card。
- PIT Join、成本模型、event_id去重、Train/Val/Test全部有记录。
- 回测报告能追溯到数据版本、代码hash和参数。

### 9.3 多Agent

- Agent有固定职责和禁止事项。
- Agent输出落库。
- Portfolio Manager只能基于审计和风控结果做准入裁决。

### 9.4 实时市场分析

- 收缩阶段、共振阶段、突破阶段、趋势跟踪阶段都有记录。
- H1/M15视角遵守State契约。
- 成本和高周期冲突会显示为风险标签。

### 9.5 执行风控

- 默认不允许实盘。
- 所有订单经过RiskGate。
- MT5断线停止信号生成。
- 邮件/报告失败不影响风控。

## 10. 风险评估

| 风险 | 类型 | 影响 | 应对 |
|---|---|---|---|
| 大模型误解策略 | 产品/技术 | 生成错误策略 | 策略理解卡片、manifest验证、人工确认 |
| 未来函数 | 技术 | 回测虚高 | PIT Join服务、replay测试、高周期close_time审计 |
| 成本低估 | 市场/技术 | 实盘亏损 | MT5 spread snapshot、滑点模型、成本前置过滤 |
| 重复事件计数 | 技术 | 胜率虚高 | 统一event_id和去重统计 |
| 策略过拟合 | 量化 | 模拟/实盘衰减 | Walk-Forward、Test只评估、Monte Carlo、模拟观察 |
| Agent越权 | 安全 | 误操作或下单 | 工具权限控制、禁止直接下单、人工审批 |
| MT5/网络断线 | 运行 | 交易中断或数据过期 | 心跳、自动重连、断线停止信号、告警 |
| 数据源差异 | 技术 | 回测和执行不一致 | 数据版本、broker symbol mapping、成本快照 |
| 开源许可证 | 商业 | 影响商业化 | 优先自研核心，外部项目作为参考或适配器 |
| 用户过度信任AI | 产品/风控 | 风险扩大 | 报告明确准入等级和拒绝理由，MVP禁止自动实盘 |

## 11. 第一批开发任务清单

建议立即创建:

```text
MT5_AI_Trading/platform/
  __init__.py
  api/
  agents/
  audit/
    pit_join.py
    tests/
  backtest/
  costs/
    cost_model.py
  data/
  events/
    event_id.py
  execution/
  reports/
  strategies/
    squeeze_state_h1/
      strategy_manifest.yaml
      strategy.py
      tests/
```

第一批任务:

1. `pit_join.py`: 实现高周期as-of join和审计输出。
2. `event_id.py`: 实现统一事件ID。
3. `cost_model.py`: 固定成本、快照成本、执行成本三层模型。
4. `strategy_manifest.yaml` schema: 约束策略输入、PIT、成本、去重、风险。
5. `squeeze_state_h1`插件: 包装现有v5与State Gate。
6. `RunCardBuilder`: 统一回测运行记录。
7. `AgentRun` schema: 固定Agent输出。

## 12. 与现有代码的兼容策略

- 不覆盖 `squeeze_multi_timeframe_research_v5.py`，先包装为插件。
- 不删除MT4邮件工具线，作为通知和可视化附件能力复用。
- 不修改现有 `main_controller.py` 的默认安全开关，平台执行层复用其风控思想。
- 不把 `MT5_AI量化交易系统技术方案.md` 旧方案废弃，而是作为ZeroMQ和长期架构蓝图引用。
- 新代码优先进入 `platform/`，减少和研究脚本互相污染。

