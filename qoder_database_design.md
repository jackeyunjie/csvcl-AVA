# Qoder AI量化多周期交易平台 - 数据库设计

**版本**: V1.0  
**日期**: 2026-06-06  
**文档编号**: QODER-DB-001  
**数据库**: DuckDB (主数据库) + Parquet (历史数据归档)  

---

## 一、设计原则

### 1.1 核心原则

| 原则 | 说明 |
|------|------|
| **统一存储** | 所有结构化数据统一存储于DuckDB，避免数据分散 |
| **时序优化** | 市场数据按时间分区，支持高效时间范围查询 |
| **状态分离** | 实时状态与历史数据分离，实时状态存DuckDB，历史数据存Parquet |
| **扩展兼容** | Schema设计兼容未来扩展，新增字段不影响现有查询 |

### 1.2 数据库选型

| 数据类型 | 存储方案 | 理由 |
|----------|----------|------|
| 实时状态 | DuckDB | 已有基础，支持SQL，单文件部署 |
| 历史行情 | Parquet文件 | 列式存储，压缩率高，适合分析 |
| 回测结果 | DuckDB | 结构化数据，需要关联查询 |
| Agent状态 | DuckDB | 实时更新，需要事务支持 |
| 日志数据 | 文本文件/ES | 量大，顺序写入 |

---

## 二、数据库Schema设计

### 2.1 数据库文件规划

```
data/
├── qoder_state.duckdb          # 主状态数据库
│   ├── strategies              # 策略表
│   ├── backtests               # 回测任务表
│   ├── backtest_results        # 回测结果表
│   ├── backtest_trades         # 回测交易记录表
│   ├── agents                  # Agent注册表
│   ├── agent_messages          # Agent消息历史表
│   ├── agent_states            # Agent状态快照表
│   ├── market_states           # 市场状态表
│   ├── state_hex_snapshots     # State Hex快照表
│   ├── contraction_events      # 收缩事件表
│   ├── breakout_events         # 突破事件表
│   ├── trend_tracking          # 趋势跟踪记录表
│   ├── signals                 # 交易信号表
│   ├── orders                  # 订单记录表
│   ├── positions               # 持仓记录表
│   ├── risk_events             # 风险事件表
│   ├── users                   # 用户表
│   ├── api_keys                # API密钥表
│   └── system_logs             # 系统日志表
│
├── observation_db.duckdb       # 观察数据库（已有）
│   ├── observation_sessions    # 观察会话
│   ├── daily_contraction_profiles  # 每日收缩特征
│   ├── symbol_signatures       # 品种收缩签名
│   └── reification_alerts      # 复现提醒
│
├── hermass_state.duckdb        # Hermass状态数据库（已有）
├── stock_state.duckdb          # 股票状态数据库（已有）
├── h1_state.duckdb             # H1 State数据库（已有）
│
└── historical/                 # 历史数据Parquet文件
    ├── EURUSD_H1.parquet
    ├── GBPUSD_H1.parquet
    └── ...
```

### 2.2 核心表设计

#### 2.2.1 策略表 (strategies)

```sql
CREATE TABLE strategies (
    strategy_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL,  -- trend_following/mean_reversion/breakout/multi_factor
    symbol VARCHAR(20),
    timeframe VARCHAR(10),
    code_python TEXT,
    code_mql5 TEXT,
    code_pine TEXT,
    parameters JSON,                       -- 策略参数定义
    risk_params JSON,                      -- 风控参数
    intent_json JSON,                      -- 自然语言解析结果
    validation_status VARCHAR(20),         -- valid/invalid/warning
    validation_result JSON,
    author VARCHAR(100),
    is_template BOOLEAN DEFAULT FALSE,
    template_category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE
);

-- 索引
CREATE INDEX idx_strategies_type ON strategies(strategy_type);
CREATE INDEX idx_strategies_symbol ON strategies(symbol);
CREATE INDEX idx_strategies_active ON strategies(is_active);
```

#### 2.2.2 回测任务表 (backtests)

```sql
CREATE TABLE backtests (
    backtest_id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32) NOT NULL,
    strategy_version INTEGER DEFAULT 1,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_balance DECIMAL(18, 2) DEFAULT 10000.00,
    leverage DECIMAL(5, 2) DEFAULT 1.00,
    slippage_model VARCHAR(20),            -- fixed/volatility_based/liquidity_based
    slippage_points DECIMAL(10, 5),
    commission_model VARCHAR(20),          -- fixed_per_lot/percentage/tiered
    commission_value DECIMAL(10, 5),
    parameters JSON,                       -- 实际使用的参数值
    use_multi_timeframe BOOLEAN DEFAULT FALSE,
    timeframes JSON,                       -- 多周期列表
    status VARCHAR(20) NOT NULL,           -- queued/running/completed/failed/cancelled
    progress INTEGER DEFAULT 0,            -- 0-100
    current_phase VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    elapsed_seconds INTEGER,
    
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
);

CREATE INDEX idx_backtests_strategy ON backtests(strategy_id);
CREATE INDEX idx_backtests_status ON backtests(status);
CREATE INDEX idx_backtests_created ON backtests(created_at);
```

#### 2.2.3 回测结果表 (backtest_results)

```sql
CREATE TABLE backtest_results (
    result_id VARCHAR(32) PRIMARY KEY,
    backtest_id VARCHAR(32) NOT NULL UNIQUE,
    
    -- 收益指标
    total_return DECIMAL(10, 4),
    annual_return DECIMAL(10, 4),
    excess_return DECIMAL(10, 4),
    
    -- 风险指标
    volatility DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    max_drawdown_duration INTEGER,         -- 最大回撤持续天数
    var_95 DECIMAL(10, 4),                 -- 95% VaR
    cvar_95 DECIMAL(10, 4),                -- 95% CVaR
    downside_deviation DECIMAL(10, 4),
    
    -- 效率指标
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    calmar_ratio DECIMAL(10, 4),
    information_ratio DECIMAL(10, 4),
    omega_ratio DECIMAL(10, 4),
    
    -- 交易指标
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    break_even_trades INTEGER,
    win_rate DECIMAL(5, 2),
    avg_profit DECIMAL(18, 4),
    avg_loss DECIMAL(18, 4),
    profit_factor DECIMAL(10, 4),
    expectancy DECIMAL(18, 4),
    avg_holding_bars DECIMAL(10, 2),
    max_consecutive_wins INTEGER,
    max_consecutive_losses INTEGER,
    
    -- 其他
    equity_curve JSON,                     -- 权益曲线数据（压缩存储）
    monthly_returns JSON,
    drawdown_series JSON,
    trade_distribution JSON,
    report_html TEXT,                      -- HTML报告
    report_pdf BLOB,                       -- PDF报告
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (backtest_id) REFERENCES backtests(backtest_id)
);
```

#### 2.2.4 回测交易记录表 (backtest_trades)

```sql
CREATE TABLE backtest_trades (
    trade_id VARCHAR(32) PRIMARY KEY,
    backtest_id VARCHAR(32) NOT NULL,
    trade_number INTEGER,
    
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,        -- LONG/SHORT
    
    entry_price DECIMAL(18, 8) NOT NULL,
    exit_price DECIMAL(18, 8),
    volume DECIMAL(18, 4) NOT NULL,
    
    pnl DECIMAL(18, 4),
    pnl_pct DECIMAL(10, 4),
    commission DECIMAL(18, 4),
    slippage DECIMAL(18, 4),
    swap DECIMAL(18, 4),
    
    holding_bars INTEGER,
    exit_reason VARCHAR(50),               -- tp/sl/signal/end/liquidation
    
    max_favorable_excursion DECIMAL(18, 4),  -- 最大有利偏移
    max_adverse_excursion DECIMAL(18, 4),    -- 最大不利偏移
    
    FOREIGN KEY (backtest_id) REFERENCES backtests(backtest_id)
);

CREATE INDEX idx_bt_trades_backtest ON backtest_trades(backtest_id);
CREATE INDEX idx_bt_trades_symbol ON backtest_trades(symbol);
```

#### 2.2.5 Agent注册表 (agents)

```sql
CREATE TABLE agents (
    agent_id VARCHAR(32) PRIMARY KEY,
    agent_type VARCHAR(50) NOT NULL,       -- research_technical/research_sentiment/trader/risk/observer/portfolio
    agent_name VARCHAR(100),
    description TEXT,
    config JSON,                           -- Agent配置参数
    llm_provider VARCHAR(20),              -- openai/anthropic/deepseek
    llm_model VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.2.6 Agent消息历史表 (agent_messages)

```sql
CREATE TABLE agent_messages (
    message_id VARCHAR(32) PRIMARY KEY,
    from_agent VARCHAR(32) NOT NULL,
    to_agent VARCHAR(32),                  -- NULL表示广播
    msg_type VARCHAR(50) NOT NULL,         -- SIGNAL/RESEARCH_REPORT/RISK_CHECK/ORDER/etc
    priority INTEGER DEFAULT 3,            -- 1=CRITICAL, 2=HIGH, 3=NORMAL, 4=LOW
    payload JSON NOT NULL,
    requires_ack BOOLEAN DEFAULT FALSE,
    correlation_id VARCHAR(32),
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (from_agent) REFERENCES agents(agent_id)
);

CREATE INDEX idx_msg_from ON agent_messages(from_agent);
CREATE INDEX idx_msg_to ON agent_messages(to_agent);
CREATE INDEX idx_msg_type ON agent_messages(msg_type);
CREATE INDEX idx_msg_created ON agent_messages(created_at);
```

#### 2.2.7 Agent状态快照表 (agent_states)

```sql
CREATE TABLE agent_states (
    snapshot_id VARCHAR(32) PRIMARY KEY,
    agent_id VARCHAR(32) NOT NULL,
    status VARCHAR(20) NOT NULL,           -- idle/running/paused/error/stopped
    current_task VARCHAR(255),
    state_data JSON,                       -- Agent状态数据
    metrics JSON,                          -- 性能指标
    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX idx_agent_states_agent ON agent_states(agent_id);
CREATE INDEX idx_agent_states_time ON agent_states(snapshot_time);
```

#### 2.2.8 State Hex快照表 (state_hex_snapshots)

```sql
CREATE TABLE state_hex_snapshots (
    snapshot_id VARCHAR(32) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- 各周期State Hex
    mn1_hex VARCHAR(2),
    w1_hex VARCHAR(2),
    d1_hex VARCHAR(2),
    h4_hex VARCHAR(2),
    h1_hex VARCHAR(2),
    m30_hex VARCHAR(2),
    m15_hex VARCHAR(2),
    
    -- 状态持续天数
    mn1_duration INTEGER DEFAULT 0,
    w1_duration INTEGER DEFAULT 0,
    d1_duration INTEGER DEFAULT 0,
    h4_duration INTEGER DEFAULT 0,
    h1_duration INTEGER DEFAULT 0,
    
    -- 共振信息
    is_resonance BOOLEAN DEFAULT FALSE,
    resonance_type VARCHAR(50),            -- trend_resonance/contraction_resonance/breakout_resonance
    resonance_strength DECIMAL(5, 4),
    resonance_timeframes JSON,
    
    -- 原始组件（可选，用于调试）
    components_json JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_shs_symbol ON state_hex_snapshots(symbol);
CREATE INDEX idx_shs_time ON state_hex_snapshots(timestamp);
CREATE INDEX idx_shs_symbol_time ON state_hex_snapshots(symbol, timestamp);
```

#### 2.2.9 收缩事件表 (contraction_events)

```sql
CREATE TABLE contraction_events (
    event_id VARCHAR(32) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    
    -- 收缩阶段
    contraction_start TIMESTAMP NOT NULL,
    contraction_end TIMESTAMP,
    duration_bars INTEGER,
    
    -- 收缩特征
    contraction_score DECIMAL(5, 2),       -- 0-100
    upper_bound DECIMAL(18, 8),
    lower_bound DECIMAL(18, 8),
    range_height DECIMAL(18, 8),
    
    -- 指标值
    bb_width DECIMAL(10, 6),
    kaufman_width DECIMAL(10, 6),
    atr_percentile DECIMAL(5, 2),
    
    -- 状态
    status VARCHAR(20),                    -- active/completed/expired
    
    -- 关联突破（完成后填充）
    breakout_event_id VARCHAR(32),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ce_symbol ON contraction_events(symbol);
CREATE INDEX idx_ce_status ON contraction_events(status);
CREATE INDEX idx_ce_start ON contraction_events(contraction_start);
```

#### 2.2.10 突破事件表 (breakout_events)

```sql
CREATE TABLE breakout_events (
    event_id VARCHAR(32) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    
    -- 关联收缩
    contraction_event_id VARCHAR(32),
    
    -- 突破信息
    breakout_time TIMESTAMP NOT NULL,
    direction VARCHAR(10) NOT NULL,        -- UP/DOWN
    breakout_price DECIMAL(18, 8) NOT NULL,
    
    -- 预测目标
    target_price DECIMAL(18, 8),
    stop_loss_price DECIMAL(18, 8),
    
    -- 确认信息
    confidence DECIMAL(5, 4),
    volume_ratio DECIMAL(10, 4),           -- 突破时成交量/平均成交量
    
    -- 结果（后续更新）
    reached_target BOOLEAN,
    reached_stop BOOLEAN,
    actual_exit_price DECIMAL(18, 8),
    actual_exit_time TIMESTAMP,
    actual_return_pct DECIMAL(10, 4),
    
    FOREIGN KEY (contraction_event_id) REFERENCES contraction_events(event_id)
);

CREATE INDEX idx_be_symbol ON breakout_events(symbol);
CREATE INDEX idx_be_time ON breakout_events(breakout_time);
```

#### 2.2.11 趋势跟踪记录表 (trend_tracking)

```sql
CREATE TABLE trend_tracking (
    track_id VARCHAR(32) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    
    -- 关联突破
    breakout_event_id VARCHAR(32),
    
    -- 趋势信息
    trend_start TIMESTAMP NOT NULL,
    trend_end TIMESTAMP,
    trend_hex VARCHAR(2),
    trend_strength VARCHAR(20),            -- strong/moderate/weak
    
    -- 持仓信息
    entry_price DECIMAL(18, 8),
    exit_price DECIMAL(18, 8),
    max_price DECIMAL(18, 8),
    min_price DECIMAL(18, 8),
    
    -- 跟踪指标
    adx_at_start DECIMAL(10, 4),
    adx_max DECIMAL(10, 4),
    
    -- 结果
    total_return_pct DECIMAL(10, 4),
    max_drawdown_pct DECIMAL(10, 4),
    duration_bars INTEGER,
    
    FOREIGN KEY (breakout_event_id) REFERENCES breakout_events(event_id)
);
```

#### 2.2.12 交易信号表 (signals)

```sql
CREATE TABLE signals (
    signal_id VARCHAR(32) PRIMARY KEY,
    
    -- 信号来源
    source_agent VARCHAR(32) NOT NULL,
    source_type VARCHAR(50),               -- technical/fundamental/sentiment/multi_factor
    
    -- 信号内容
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,        -- BUY/SELL
    signal_type VARCHAR(50),               -- trend_resonance/contraction_breakout/mean_reversion/etc
    confidence DECIMAL(5, 4) NOT NULL,
    
    -- 价格信息
    suggested_entry DECIMAL(18, 8),
    suggested_sl DECIMAL(18, 8),
    suggested_tp DECIMAL(18, 8),
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',  -- pending/approved/rejected/executed/expired
    
    -- 执行关联
    order_id VARCHAR(32),
    
    -- 结果追踪
    outcome VARCHAR(20),                   -- win/loss/break_even/pending
    actual_return_pct DECIMAL(10, 4),
    
    -- 时间
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expired_at TIMESTAMP,
    executed_at TIMESTAMP,
    
    -- 上下文
    state_hex_at_signal JSON,
    market_context JSON,
    reasoning TEXT,
    
    FOREIGN KEY (source_agent) REFERENCES agents(agent_id)
);

CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_time ON signals(generated_at);
CREATE INDEX idx_signals_agent ON signals(source_agent);
```

#### 2.2.13 订单记录表 (orders)

```sql
CREATE TABLE orders (
    order_id VARCHAR(32) PRIMARY KEY,
    ticket VARCHAR(32) UNIQUE,
    
    -- 订单信息
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,        -- BUY/SELL
    order_type VARCHAR(20) NOT NULL,       -- MARKET/LIMIT/STOP
    volume DECIMAL(18, 4) NOT NULL,
    
    -- 价格
    requested_price DECIMAL(18, 8),
    filled_price DECIMAL(18, 8),
    sl DECIMAL(18, 8),
    tp DECIMAL(18, 8),
    
    -- 执行信息
    status VARCHAR(20),                    -- pending/filled/partial/cancelled/rejected
    filled_volume DECIMAL(18, 4),
    slippage DECIMAL(18, 8),
    commission DECIMAL(18, 4),
    
    -- 来源
    source_agent VARCHAR(32),
    signal_id VARCHAR(32),
    magic INTEGER,
    comment VARCHAR(255),
    
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP,
    
    FOREIGN KEY (source_agent) REFERENCES agents(agent_id),
    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
);

CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_time ON orders(created_at);
```

#### 2.2.14 持仓记录表 (positions)

```sql
CREATE TABLE positions (
    position_id VARCHAR(32) PRIMARY KEY,
    ticket VARCHAR(32) NOT NULL UNIQUE,
    
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    volume DECIMAL(18, 4) NOT NULL,
    
    open_price DECIMAL(18, 8) NOT NULL,
    current_price DECIMAL(18, 8),
    sl DECIMAL(18, 8),
    tp DECIMAL(18, 8),
    
    profit DECIMAL(18, 4),
    profit_pct DECIMAL(10, 4),
    swap DECIMAL(18, 4),
    commission DECIMAL(18, 4),
    
    open_time TIMESTAMP NOT NULL,
    magic INTEGER,
    comment VARCHAR(255),
    
    is_active BOOLEAN DEFAULT TRUE,
    closed_at TIMESTAMP,
    close_price DECIMAL(18, 8),
    close_reason VARCHAR(50)
);

CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_active ON positions(is_active);
```

#### 2.2.15 风险事件表 (risk_events)

```sql
CREATE TABLE risk_events (
    event_id VARCHAR(32) PRIMARY KEY,
    
    event_type VARCHAR(50) NOT NULL,       -- position_limit/exposure_limit/daily_loss/margin_call/volatility_alert
    severity VARCHAR(20) NOT NULL,         -- info/warning/critical/emergency
    
    symbol VARCHAR(20),
    description TEXT NOT NULL,
    
    -- 触发值
    triggered_value DECIMAL(18, 4),
    limit_value DECIMAL(18, 4),
    
    -- 处理结果
    action_taken VARCHAR(50),              -- alert/limit_position/force_close/system_lock
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    
    -- 关联
    related_order_id VARCHAR(32),
    related_position_id VARCHAR(32),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_re_severity ON risk_events(severity);
CREATE INDEX idx_re_type ON risk_events(event_type);
CREATE INDEX idx_re_time ON risk_events(created_at);
```

#### 2.2.16 用户表 (users)

```sql
CREATE TABLE users (
    user_id VARCHAR(32) PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    
    role VARCHAR(20) DEFAULT 'trader',     -- admin/trader/viewer
    is_active BOOLEAN DEFAULT TRUE,
    
    risk_limits JSON,                      -- 用户级风控限额
    preferences JSON,                      -- 用户偏好设置
    
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.2.17 API密钥表 (api_keys)

```sql
CREATE TABLE api_keys (
    key_id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL,
    
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_name VARCHAR(100),
    
    permissions JSON,                      -- ["read", "trade", "admin"]
    rate_limit INTEGER DEFAULT 100,        -- 每分钟请求数
    
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

#### 2.2.18 系统日志表 (system_logs)

```sql
CREATE TABLE system_logs (
    log_id BIGINT PRIMARY KEY,
    
    level VARCHAR(10) NOT NULL,            -- DEBUG/INFO/WARNING/ERROR/CRITICAL
    source VARCHAR(50),                    -- 模块名
    agent_id VARCHAR(32),
    
    message TEXT NOT NULL,
    context JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_logs_level ON system_logs(level);
CREATE INDEX idx_logs_source ON system_logs(source);
CREATE INDEX idx_logs_time ON system_logs(created_at);
```

---

## 三、数据流与ETL

### 3.1 实时数据流

```
MT5 ZeroMQ Tick → 行情接收器 → 数据标准化 → DuckDB market_states (实时更新)
                                    ↓
                              State Hex引擎 → DuckDB state_hex_snapshots
                                    ↓
                              收缩检测引擎 → DuckDB contraction_events
                                    ↓
                              突破检测 → DuckDB breakout_events
                                    ↓
                              Agent消息 → DuckDB agent_messages
```

### 3.2 批量数据流

```
历史数据下载 → Parquet文件 → 数据质量检查 → DuckDB (回测时加载)
                                    ↓
                              回测执行 → DuckDB backtests/backtest_results/backtest_trades
```

### 3.3 数据保留策略

| 数据类型 | 保留策略 | 说明 |
|----------|----------|------|
| Tick数据 | 7天 | 仅保留最近7天，用于实时分析 |
| State Hex快照 | 90天 | 保留最近90天，支持趋势分析 |
| Agent消息 | 30天 | 保留最近30天，用于调试和审计 |
| 回测结果 | 永久 | 所有回测结果永久保留 |
| 交易记录 | 永久 | 所有交易记录永久保留 |
| 系统日志 | 30天 | 保留最近30天，定期归档 |

---

## 四、查询示例

### 4.1 查询品种当前State Hex

```sql
SELECT symbol, timestamp,
       mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex,
       is_resonance, resonance_type, resonance_strength
FROM state_hex_snapshots
WHERE symbol = 'EURUSD'
ORDER BY timestamp DESC
LIMIT 1;
```

### 4.2 查询活跃收缩事件

```sql
SELECT symbol, contraction_start, duration_bars, contraction_score,
       upper_bound, lower_bound,
       (upper_bound - lower_bound) / lower_bound * 100 as range_pct
FROM contraction_events
WHERE status = 'active'
ORDER BY contraction_score DESC;
```

### 4.3 查询Agent消息历史

```sql
SELECT m.message_id, m.from_agent, m.to_agent, m.msg_type, m.priority,
       m.payload, m.created_at
FROM agent_messages m
WHERE m.from_agent = 'observer_001'
   OR m.to_agent = 'observer_001'
ORDER BY m.created_at DESC
LIMIT 100;
```

### 4.4 查询策略回测绩效排名

```sql
SELECT s.strategy_id, s.name, s.strategy_type,
       r.sharpe_ratio, r.total_return, r.max_drawdown,
       r.total_trades, r.win_rate
FROM strategies s
JOIN backtests b ON s.strategy_id = b.strategy_id
JOIN backtest_results r ON b.backtest_id = r.backtest_id
WHERE b.status = 'completed'
  AND b.created_at >= '2026-01-01'
ORDER BY r.sharpe_ratio DESC
LIMIT 20;
```

### 4.5 查询信号绩效归因

```sql
SELECT 
    source_agent,
    signal_type,
    COUNT(*) as total_signals,
    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
    ROUND(SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
    ROUND(AVG(actual_return_pct), 4) as avg_return
FROM signals
WHERE generated_at >= '2026-01-01'
GROUP BY source_agent, signal_type
ORDER BY win_rate DESC;
```

### 4.6 查询收缩→突破→趋势完整链路

```sql
SELECT 
    c.symbol,
    c.contraction_start,
    c.contraction_score,
    b.breakout_time,
    b.direction,
    b.confidence,
    b.breakout_price,
    t.trend_start,
    t.trend_strength,
    t.total_return_pct
FROM contraction_events c
LEFT JOIN breakout_events b ON c.breakout_event_id = b.event_id
LEFT JOIN trend_tracking t ON b.event_id = t.breakout_event_id
WHERE c.contraction_start >= '2026-05-01'
ORDER BY c.contraction_start DESC;
```

---

## 五、数据库初始化脚本

```sql
-- 创建序列
CREATE SEQUENCE seq_strategy_id START 1;
CREATE SEQUENCE seq_backtest_id START 1;
CREATE SEQUENCE seq_agent_id START 1;
CREATE SEQUENCE seq_signal_id START 1;
CREATE SEQUENCE seq_order_id START 1;
CREATE SEQUENCE seq_log_id START 1;

-- 创建所有表（见上文）

-- 创建视图
CREATE VIEW v_active_signals AS
SELECT s.*, a.agent_type, a.agent_name
FROM signals s
JOIN agents a ON s.source_agent = a.agent_id
WHERE s.status = 'pending'
  AND s.expired_at > CURRENT_TIMESTAMP;

CREATE VIEW v_position_summary AS
SELECT 
    symbol,
    SUM(CASE WHEN direction = 'BUY' THEN volume ELSE -volume END) as net_volume,
    SUM(profit) as total_profit,
    COUNT(*) as position_count
FROM positions
WHERE is_active = TRUE
GROUP BY symbol;

CREATE VIEW v_daily_performance AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_signals,
    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
    ROUND(AVG(actual_return_pct), 4) as avg_return
FROM signals
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

---

## 六、附录

### 6.1 与现有数据库的集成

| 现有数据库 | 集成方式 | 说明 |
|------------|----------|------|
| observation_db.duckdb | 保留独立 | 观察数据继续独立存储 |
| hermass_state.duckdb | 保留独立 | Hermass策略数据独立存储 |
| h1_state.duckdb | 保留独立 | H1 State数据独立存储 |
| qoder_state.duckdb | 新建 | 新平台主数据库 |

### 6.2 数据迁移策略

1. **State Hex数据**: 从现有h1_state.duckdb同步到qoder_state.duckdb
2. **观察数据**: 保持observation_db.duckdb不变，通过DuckDB ATTACH功能跨库查询
3. **策略数据**: 手动导入现有策略到strategies表

### 6.3 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-06 | 初始版本 | Qoder AI |
