# KIMI AI量化多周期视角交易平台 - 数据库设计

**版本**: V1.0  
**日期**: 2026-06-06  
**文档编号**: KIMI-DB-001  
**数据库**: DuckDB (主数据库) + Parquet (历史数据)  
**设计原则**: 基于GitHub前沿开源项目独立设计，参考Vibe-Trading的数据架构和TradingAgents的持久化机制

---

## 一、数据库架构概述

### 1.1 存储架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           KIMI数据存储架构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────┐ │
│  │   DuckDB (主数据库)  │    │   Parquet (历史数据) │    │  SQLite (缓存)  │ │
│  │                     │    │                     │    │                 │ │
│  │ • 策略表            │    │ • OHLCV历史数据      │    │ • 计算缓存      │ │
│  │ • 回测结果          │    │ • Tick数据归档       │    │ • 会话数据      │ │
│  │ • Agent状态         │    │ • 回测详细记录       │    │ • 配置缓存      │ │
│  │ • 交易记录          │    │ • 特征工程数据       │    │                 │ │
│  │ • State Hex快照     │    │                     │    │                 │ │
│  │ • 观察记录          │    │                     │    │                 │ │
│  │ • 风险事件          │    │                     │    │                 │ │
│  └─────────────────────┘    └─────────────────────┘    └─────────────────┘ │
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐                        │
│  │   Redis (扩展缓存)   │    │   文件系统 (日志)    │                        │
│  │                     │    │                     │                        │
│  │ • 实时行情缓存      │    │ • 系统日志          │                        │
│  │ • Agent消息队列     │    │ • 交易日志          │                        │
│  │ • 计算结果缓存      │    │ • 审计日志          │                        │
│  │ • 会话状态          │    │ • Agent决策日志      │                        │
│  └─────────────────────┘    └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 数据保留策略

| 数据类型 | 存储位置 | 保留期限 | 说明 |
|----------|----------|----------|------|
| Tick数据 | Parquet | 7天 | 高频数据定期归档 |
| OHLCV数据 | Parquet | 永久 | 按年/月分区存储 |
| State Hex快照 | DuckDB | 90天 | 近期状态用于分析 |
| Agent消息 | DuckDB | 30天 | 消息历史定期清理 |
| 回测结果 | DuckDB | 永久 | 策略研发历史保留 |
| 交易记录 | DuckDB | 永久 | 合规要求永久保留 |
| 观察记录 | DuckDB | 永久 | 收缩-突破-趋势全链路 |
| 风险事件 | DuckDB | 永久 | 风控审计 |
| 系统日志 | 文件 | 30天 | 日志轮转 |

---

## 二、DuckDB Schema设计

### 2.1 数据库文件组织

```
data/
├── kimi_state.duckdb          # 主状态数据库
│   ├── strategies             # 策略表
│   ├── backtests              # 回测任务表
│   ├── backtest_results       # 回测结果表
│   ├── backtest_trades        # 回测交易明细
│   ├── agents                 # Agent注册表
│   ├── agent_messages         # Agent消息表
│   ├── agent_states           # Agent状态快照
│   ├── state_hex_snapshots    # State Hex快照
│   ├── contraction_events     # 收缩事件表
│   ├── breakout_events        # 突破事件表
│   ├── trend_tracking         # 趋势跟踪记录
│   ├── signals                # 交易信号表
│   ├── orders                 # 订单表
│   ├── positions              # 持仓表
│   ├── risk_events            # 风险事件表
│   ├── users                  # 用户表
│   ├── api_keys               # API密钥表
│   └── system_logs            # 系统日志表
│
├── observation_db.duckdb      # 观察数据库
│   ├── observation_sessions   # 观察会话
│   ├── daily_contraction_profiles  # 每日收缩特征
│   ├── symbol_signatures      # 品种收缩签名
│   ├── breakout_events        # 突破事件
│   └── trend_tracking_records # 趋势跟踪记录
│
└── parquet/                   # Parquet历史数据
    ├── ohlcv/
    │   ├── EURUSD_H1_2025.parquet
    │   ├── EURUSD_H1_2026.parquet
    │   └── ...
    └── ticks/
        └── EURUSD_20250606.parquet
```

### 2.2 核心表结构

#### 2.2.1 策略表 (strategies)

```sql
CREATE TABLE strategies (
    strategy_id VARCHAR PRIMARY KEY,           -- 策略ID: str_xxx
    name VARCHAR NOT NULL,                     -- 策略名称
    description TEXT,                          -- 策略描述
    strategy_type VARCHAR NOT NULL,            -- 类型: trend_following/mean_reversion/breakout/multi_factor
    status VARCHAR DEFAULT 'draft',            -- 状态: draft/validated/active/archived
    
    -- 策略代码
    code_python TEXT,                          -- Python代码
    code_mql5 TEXT,                            -- MQL5代码
    code_pine TEXT,                            -- Pine Script代码
    code_tdx TEXT,                             -- TDX公式
    
    -- 策略意图JSON
    intent_json JSON,                          -- 结构化策略意图
    
    -- 参数定义
    parameters_json JSON,                      -- 参数定义 [{name, default, min, max}]
    
    -- 风控参数
    risk_params_json JSON,                     -- 风控参数
    
    -- 模板信息
    template_used VARCHAR,                     -- 使用的模板
    
    -- 验证信息
    validation_result JSON,                    -- 验证结果
    
    -- 统计信息
    backtest_count INTEGER DEFAULT 0,          -- 回测次数
    best_sharpe DECIMAL(10,4),                 -- 最佳夏普比率
    best_return DECIMAL(10,4),                 -- 最佳收益率
    
    -- 元数据
    created_by VARCHAR,                        -- 创建者
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_strategies_type ON strategies(strategy_type);
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategies_created ON strategies(created_at);
```

#### 2.2.2 回测任务表 (backtests)

```sql
CREATE TABLE backtests (
    backtest_id VARCHAR PRIMARY KEY,           -- 回测ID: bt_xxx
    strategy_id VARCHAR NOT NULL,              -- 关联策略ID
    status VARCHAR DEFAULT 'queued',           -- 状态: queued/running/completed/failed/cancelled
    
    -- 回测配置
    config_json JSON NOT NULL,                 -- 回测配置
    -- {
    --   "symbols": ["EURUSD"],
    --   "timeframe": "H1",
    --   "start_date": "2025-01-01",
    --   "end_date": "2026-01-01",
    --   "initial_balance": 10000,
    --   "commission": 0.001,
    --   "slippage": 0.0001
    -- }
    
    -- 优化配置
    optimization_json JSON,                    -- 参数优化配置
    
    -- 执行信息
    progress INTEGER DEFAULT 0,                -- 进度 0-100
    current_phase VARCHAR,                     -- 当前阶段
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- 错误信息
    error_message TEXT,
    
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
);

-- 索引
CREATE INDEX idx_backtests_strategy ON backtests(strategy_id);
CREATE INDEX idx_backtests_status ON backtests(status);
CREATE INDEX idx_backtests_created ON backtests(created_at);
```

#### 2.2.3 回测结果表 (backtest_results)

```sql
CREATE TABLE backtest_results (
    result_id VARCHAR PRIMARY KEY,             -- 结果ID
    backtest_id VARCHAR NOT NULL,              -- 关联回测ID
    
    -- 绩效指标
    total_return DECIMAL(10,4),                -- 总收益率
    annualized_return DECIMAL(10,4),           -- 年化收益率
    sharpe_ratio DECIMAL(10,4),                -- 夏普比率
    sortino_ratio DECIMAL(10,4),               -- 索提诺比率
    calmar_ratio DECIMAL(10,4),                -- 卡玛比率
    max_drawdown DECIMAL(10,4),                -- 最大回撤
    max_drawdown_duration INTEGER,             -- 最大回撤持续时间(天)
    win_rate DECIMAL(5,2),                     -- 胜率
    profit_factor DECIMAL(10,4),               -- 盈亏比
    total_trades INTEGER,                      -- 总交易次数
    avg_trade_return DECIMAL(10,4),            -- 平均交易收益
    
    -- 详细指标JSON
    metrics_json JSON,                         -- 完整指标
    
    -- 优化结果
    optimization_results_json JSON,            -- 参数优化结果
    
    -- 报告路径
    report_html_path VARCHAR,                  -- HTML报告路径
    report_pdf_path VARCHAR,                   -- PDF报告路径
    
    -- 数据文件路径
    equity_curve_path VARCHAR,                 -- 收益曲线数据
    trades_path VARCHAR,                       -- 交易明细数据
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (backtest_id) REFERENCES backtests(backtest_id)
);
```

#### 2.2.4 回测交易明细表 (backtest_trades)

```sql
CREATE TABLE backtest_trades (
    trade_id VARCHAR PRIMARY KEY,              -- 交易ID
    backtest_id VARCHAR NOT NULL,              -- 关联回测ID
    
    -- 交易信息
    symbol VARCHAR NOT NULL,                   -- 品种
    direction VARCHAR NOT NULL,                -- 方向: LONG/SHORT
    entry_time TIMESTAMP NOT NULL,             -- 入场时间
    exit_time TIMESTAMP,                       -- 出场时间
    entry_price DECIMAL(18,8),                 -- 入场价格
    exit_price DECIMAL(18,8),                  -- 出场价格
    size DECIMAL(18,8),                        -- 手数
    pnl DECIMAL(18,8),                         -- 盈亏金额
    pnl_pct DECIMAL(10,4),                     -- 盈亏百分比
    
    -- 费用
    commission DECIMAL(18,8),                  -- 手续费
    slippage DECIMAL(18,8),                    -- 滑点
    
    -- 持仓时间
    holding_bars INTEGER,                      -- 持仓K线数
    holding_duration INTEGER,                  -- 持仓时长(秒)
    
    -- 关联信号
    signal_id VARCHAR,                         -- 关联信号ID
    
    FOREIGN KEY (backtest_id) REFERENCES backtests(backtest_id)
);

-- 索引
CREATE INDEX idx_backtest_trades_backtest ON backtest_trades(backtest_id);
CREATE INDEX idx_backtest_trades_symbol ON backtest_trades(symbol);
CREATE INDEX idx_backtest_trades_entry ON backtest_trades(entry_time);
```

#### 2.2.5 Agent注册表 (agents)

```sql
CREATE TABLE agents (
    agent_id VARCHAR PRIMARY KEY,              -- Agent ID
    name VARCHAR NOT NULL,                     -- Agent名称
    agent_type VARCHAR NOT NULL,               -- 类型: research/trader/risk/execution/portfolio/observer
    
    -- 配置
    config_json JSON,                          -- Agent配置
    
    -- 状态
    status VARCHAR DEFAULT 'stopped',          -- 状态: idle/running/paused/error/stopped
    
    -- 统计
    uptime_seconds INTEGER DEFAULT 0,          -- 运行时长
    messages_processed INTEGER DEFAULT 0,      -- 处理消息数
    signals_generated INTEGER DEFAULT 0,       -- 生成信号数
    orders_executed INTEGER DEFAULT 0,         -- 执行订单数
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP,
    stopped_at TIMESTAMP
);

-- 索引
CREATE INDEX idx_agents_type ON agents(agent_type);
CREATE INDEX idx_agents_status ON agents(status);
```

#### 2.2.6 Agent消息表 (agent_messages)

```sql
CREATE TABLE agent_messages (
    msg_id VARCHAR PRIMARY KEY,                -- 消息ID
    from_agent VARCHAR NOT NULL,               -- 发送方
    to_agent VARCHAR NOT NULL,                 -- 接收方
    msg_type VARCHAR NOT NULL,                 -- 消息类型
    priority INTEGER DEFAULT 5,                -- 优先级 1-10
    
    -- 内容
    payload_json JSON NOT NULL,                -- 消息内容
    
    -- 状态
    requires_ack BOOLEAN DEFAULT FALSE,        -- 是否需要确认
    acknowledged BOOLEAN DEFAULT FALSE,        -- 是否已确认
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    
    FOREIGN KEY (from_agent) REFERENCES agents(agent_id),
    FOREIGN KEY (to_agent) REFERENCES agents(agent_id)
);

-- 索引
CREATE INDEX idx_agent_messages_from ON agent_messages(from_agent);
CREATE INDEX idx_agent_messages_to ON agent_messages(to_agent);
CREATE INDEX idx_agent_messages_type ON agent_messages(msg_type);
CREATE INDEX idx_agent_messages_created ON agent_messages(created_at);
```

#### 2.2.7 Agent状态快照表 (agent_states)

```sql
CREATE TABLE agent_states (
    snapshot_id VARCHAR PRIMARY KEY,           -- 快照ID
    agent_id VARCHAR NOT NULL,                 -- Agent ID
    
    -- 状态数据
    state_json JSON NOT NULL,                  -- 状态JSON
    -- {
    --   "state": "running",
    --   "context": {...},
    --   "active_positions": {...},
    --   "pending_signals": [...]
    -- }
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- 索引
CREATE INDEX idx_agent_states_agent ON agent_states(agent_id);
CREATE INDEX idx_agent_states_created ON agent_states(created_at);
```

#### 2.2.8 State Hex快照表 (state_hex_snapshots)

```sql
CREATE TABLE state_hex_snapshots (
    snapshot_id VARCHAR PRIMARY KEY,           -- 快照ID
    symbol VARCHAR NOT NULL,                   -- 品种
    timestamp TIMESTAMP NOT NULL,              -- 时间戳
    
    -- 五元组State Hex
    mn1_state VARCHAR(1),                      -- MN1状态
    w1_state VARCHAR(1),                       -- W1状态
    d1_state VARCHAR(1),                       -- D1状态
    h4_state VARCHAR(1),                       -- H4状态
    h1_state VARCHAR(1),                       -- H1状态
    
    -- 状态描述
    mn1_description VARCHAR,                   -- MN1状态描述
    w1_description VARCHAR,                    -- W1状态描述
    d1_description VARCHAR,                    -- D1状态描述
    h4_description VARCHAR,                    -- H4状态描述
    h1_description VARCHAR,                    -- H1状态描述
    
    -- 共振信息
    resonance_score INTEGER,                   -- 共振评分 0-100
    resonance_type VARCHAR,                    -- 共振类型
    bullish_count INTEGER,                     -- 看涨周期数
    bearish_count INTEGER,                     -- 看跌周期数
    neutral_count INTEGER,                     -- 中性周期数
    
    -- 原始数据JSON
    raw_data_json JSON,                        -- 原始计算数据
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_state_hex_symbol ON state_hex_snapshots(symbol);
CREATE INDEX idx_state_hex_timestamp ON state_hex_snapshots(timestamp);
CREATE INDEX idx_state_hex_symbol_time ON state_hex_snapshots(symbol, timestamp);
```

#### 2.2.9 收缩事件表 (contraction_events)

```sql
CREATE TABLE contraction_events (
    event_id VARCHAR PRIMARY KEY,              -- 事件ID
    symbol VARCHAR NOT NULL,                   -- 品种
    timeframe VARCHAR NOT NULL,                -- 周期
    
    -- 收缩信息
    contraction_score INTEGER,                 -- 收缩评分 0-100
    duration_bars INTEGER,                     -- 持续K线数
    
    -- 各指标百分位
    bb_width_percentile INTEGER,               -- BB Width百分位
    kaufman_width_percentile INTEGER,          -- Kaufman Width百分位
    atr_percentile INTEGER,                    -- ATR百分位
    
    -- 突破预测
    breakout_probability DECIMAL(5,4),         -- 突破概率
    predicted_direction VARCHAR,               -- 预测方向
    target_price DECIMAL(18,8),                -- 目标价格
    
    -- 时间
    detected_at TIMESTAMP NOT NULL,            -- 检测时间
    ended_at TIMESTAMP,                        -- 结束时间
    
    -- 关联突破事件
    breakout_event_id VARCHAR,                 -- 关联突破事件ID
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_contraction_symbol ON contraction_events(symbol);
CREATE INDEX idx_contraction_timeframe ON contraction_events(timeframe);
CREATE INDEX idx_contraction_detected ON contraction_events(detected_at);
```

#### 2.2.10 突破事件表 (breakout_events)

```sql
CREATE TABLE breakout_events (
    event_id VARCHAR PRIMARY KEY,              -- 事件ID
    symbol VARCHAR NOT NULL,                   -- 品种
    timeframe VARCHAR NOT NULL,                -- 周期
    
    -- 关联收缩
    contraction_event_id VARCHAR,              -- 关联收缩事件
    
    -- 突破信息
    direction VARCHAR NOT NULL,                -- 方向: bullish/bearish
    breakout_price DECIMAL(18,8),              -- 突破价格
    breakout_volume DECIMAL(18,8),             -- 突破成交量
    
    -- 确认评分
    confirmation_score INTEGER,                -- 确认评分
    price_breakout BOOLEAN,                    -- 价格突破
    volume_confirmation BOOLEAN,               -- 成交量确认
    state_hex_change BOOLEAN,                  -- State Hex变化
    multi_timeframe_resonance BOOLEAN,         -- 多周期共振
    
    -- 目标位
    target_price DECIMAL(18,8),                -- 目标价格
    stop_loss_price DECIMAL(18,8),             -- 止损价格
    
    -- 时间
    occurred_at TIMESTAMP NOT NULL,            -- 发生时间
    
    -- 结果跟踪
    result_json JSON,                          -- 结果JSON
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contraction_event_id) REFERENCES contraction_events(event_id)
);

-- 索引
CREATE INDEX idx_breakout_symbol ON breakout_events(symbol);
CREATE INDEX idx_breakout_timeframe ON breakout_events(timeframe);
CREATE INDEX idx_breakout_occurred ON breakout_events(occurred_at);
```

#### 2.2.11 趋势跟踪记录表 (trend_tracking)

```sql
CREATE TABLE trend_tracking (
    track_id VARCHAR PRIMARY KEY,              -- 跟踪ID
    symbol VARCHAR NOT NULL,                   -- 品种
    timeframe VARCHAR NOT NULL,                -- 周期
    
    -- 关联突破
    breakout_event_id VARCHAR,                 -- 关联突破事件
    
    -- 趋势信息
    direction VARCHAR NOT NULL,                -- 方向
    entry_price DECIMAL(18,8),                 -- 入场价格
    current_price DECIMAL(18,8),               -- 当前价格
    highest_price DECIMAL(18,8),               -- 最高价
    lowest_price DECIMAL(18,8),                -- 最低价
    
    -- 持仓状态
    status VARCHAR DEFAULT 'active',           -- 状态: active/closed
    unrealized_pnl DECIMAL(18,8),              -- 未实现盈亏
    realized_pnl DECIMAL(18,8),                -- 已实现盈亏
    
    -- 跟踪参数
    trailing_stop DECIMAL(18,8),               -- 移动止损
    target_price DECIMAL(18,8),                -- 目标价格
    
    -- 时间
    started_at TIMESTAMP NOT NULL,             -- 开始时间
    ended_at TIMESTAMP,                        -- 结束时间
    duration_bars INTEGER,                     -- 持续K线数
    
    -- 结果
    result VARCHAR,                            -- 结果: target_hit/stopped/reversed
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (breakout_event_id) REFERENCES breakout_events(event_id)
);

-- 索引
CREATE INDEX idx_trend_symbol ON trend_tracking(symbol);
CREATE INDEX idx_trend_timeframe ON trend_tracking(timeframe);
CREATE INDEX idx_trend_status ON trend_tracking(status);
```

#### 2.2.12 交易信号表 (signals)

```sql
CREATE TABLE signals (
    signal_id VARCHAR PRIMARY KEY,             -- 信号ID
    symbol VARCHAR NOT NULL,                   -- 品种
    
    -- 信号信息
    signal_type VARCHAR NOT NULL,              -- 类型: BUY/SELL
    direction VARCHAR NOT NULL,                -- 方向: LONG/SHORT
    confidence DECIMAL(5,4),                   -- 置信度 0-1
    
    -- 价格
    suggested_entry DECIMAL(18,8),             -- 建议入场价
    suggested_sl DECIMAL(18,8),                -- 建议止损
    suggested_tp DECIMAL(18,8),                -- 建议止盈
    
    -- 来源
    source_agent VARCHAR,                      -- 来源Agent
    source_strategy VARCHAR,                   -- 来源策略
    
    -- 理由
    reasoning TEXT,                            -- 信号理由
    
    -- 状态
    status VARCHAR DEFAULT 'active',           -- 状态: active/executed/expired/cancelled
    
    -- 执行信息
    executed_order_id VARCHAR,                 -- 执行订单ID
    executed_price DECIMAL(18,8),              -- 执行价格
    
    -- 时间
    generated_at TIMESTAMP NOT NULL,           -- 生成时间
    expired_at TIMESTAMP,                      -- 过期时间
    executed_at TIMESTAMP,                     -- 执行时间
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_generated ON signals(generated_at);
```

#### 2.2.13 订单表 (orders)

```sql
CREATE TABLE orders (
    order_id VARCHAR PRIMARY KEY,              -- 订单ID
    signal_id VARCHAR,                         -- 关联信号ID
    
    -- 订单信息
    symbol VARCHAR NOT NULL,                   -- 品种
    direction VARCHAR NOT NULL,                -- 方向: BUY/SELL
    order_type VARCHAR NOT NULL,               -- 类型: MARKET/LIMIT/STOP
    size DECIMAL(18,8) NOT NULL,               -- 手数
    
    -- 价格
    entry_price DECIMAL(18,8),                 -- 入场价格
    fill_price DECIMAL(18,8),                  -- 成交价格
    stop_loss DECIMAL(18,8),                   -- 止损
    take_profit DECIMAL(18,8),                 -- 止盈
    
    -- 状态
    status VARCHAR DEFAULT 'pending',          -- 状态: pending/filled/partial/cancelled/rejected
    
    -- 费用
    commission DECIMAL(18,8),                  -- 手续费
    slippage DECIMAL(18,8),                    -- 滑点
    
    -- 元数据
    comment VARCHAR,                           -- 备注
    mt5_ticket INTEGER,                        -- MT5订单号
    
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP,                       -- 成交时间
    cancelled_at TIMESTAMP,                    -- 取消时间
    
    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
);

-- 索引
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at);
```

#### 2.2.14 持仓表 (positions)

```sql
CREATE TABLE positions (
    position_id VARCHAR PRIMARY KEY,           -- 持仓ID
    order_id VARCHAR NOT NULL,                 -- 关联订单ID
    
    -- 持仓信息
    symbol VARCHAR NOT NULL,                   -- 品种
    direction VARCHAR NOT NULL,                -- 方向: LONG/SHORT
    size DECIMAL(18,8) NOT NULL,               -- 手数
    entry_price DECIMAL(18,8) NOT NULL,        -- 入场价格
    
    -- 当前状态
    current_price DECIMAL(18,8),               -- 当前价格
    unrealized_pnl DECIMAL(18,8),              -- 未实现盈亏
    unrealized_pnl_pct DECIMAL(10,4),          -- 未实现盈亏百分比
    
    -- 风控
    stop_loss DECIMAL(18,8),                   -- 止损
    take_profit DECIMAL(18,8),                 -- 止盈
    
    -- 状态
    status VARCHAR DEFAULT 'open',             -- 状态: open/closed
    
    -- 平仓信息
    exit_price DECIMAL(18,8),                  -- 平仓价格
    realized_pnl DECIMAL(18,8),                -- 已实现盈亏
    realized_pnl_pct DECIMAL(10,4),            -- 已实现盈亏百分比
    
    -- 时间
    opened_at TIMESTAMP NOT NULL,              -- 开仓时间
    closed_at TIMESTAMP,                       -- 平仓时间
    holding_bars INTEGER,                      -- 持仓K线数
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- 索引
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_opened ON positions(opened_at);
```

#### 2.2.15 风险事件表 (risk_events)

```sql
CREATE TABLE risk_events (
    event_id VARCHAR PRIMARY KEY,              -- 事件ID
    event_type VARCHAR NOT NULL,               -- 类型: drawdown/daily_loss/position_limit/margin/volatility
    level VARCHAR NOT NULL,                    -- 级别: warning/limit/forced/emergency
    
    -- 触发信息
    triggered_by VARCHAR,                      -- 触发源
    triggered_value DECIMAL(18,8),             -- 触发值
    threshold_value DECIMAL(18,8),             -- 阈值
    
    -- 描述
    description TEXT,                          -- 描述
    
    -- 处理
    action_taken VARCHAR,                      -- 采取的措施
    resolved_at TIMESTAMP,                     -- 解决时间
    
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_risk_events_type ON risk_events(event_type);
CREATE INDEX idx_risk_events_level ON risk_events(level);
CREATE INDEX idx_risk_events_created ON risk_events(created_at);
```

#### 2.2.16 用户表 (users)

```sql
CREATE TABLE users (
    user_id VARCHAR PRIMARY KEY,               -- 用户ID
    username VARCHAR NOT NULL UNIQUE,          -- 用户名
    email VARCHAR NOT NULL UNIQUE,             -- 邮箱
    password_hash VARCHAR NOT NULL,            -- 密码哈希
    
    -- 权限
    role VARCHAR DEFAULT 'trader',             -- 角色: admin/trader/viewer
    permissions_json JSON,                     -- 权限JSON
    
    -- 状态
    status VARCHAR DEFAULT 'active',           -- 状态: active/inactive/banned
    
    -- 元数据
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.2.17 API密钥表 (api_keys)

```sql
CREATE TABLE api_keys (
    key_id VARCHAR PRIMARY KEY,                -- 密钥ID
    user_id VARCHAR NOT NULL,                  -- 关联用户ID
    
    -- 密钥信息
    key_hash VARCHAR NOT NULL,                 -- 密钥哈希
    key_prefix VARCHAR NOT NULL,               -- 密钥前缀 (用于显示)
    
    -- 权限
    permissions_json JSON,                     -- 权限范围
    
    -- 限制
    rate_limit INTEGER DEFAULT 100,            -- 每分钟请求限制
    
    -- 状态
    status VARCHAR DEFAULT 'active',           -- 状态: active/revoked/expired
    
    -- 时间
    expires_at TIMESTAMP,                      -- 过期时间
    last_used_at TIMESTAMP,                    -- 最后使用时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

#### 2.2.18 系统日志表 (system_logs)

```sql
CREATE TABLE system_logs (
    log_id BIGINT PRIMARY KEY,                 -- 日志ID (自增)
    level VARCHAR NOT NULL,                    -- 级别: DEBUG/INFO/WARNING/ERROR/CRITICAL
    
    -- 来源
    source VARCHAR,                            -- 来源模块
    agent_id VARCHAR,                          -- 关联Agent
    
    -- 内容
    message TEXT NOT NULL,                     -- 消息
    details_json JSON,                         -- 详细数据
    
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_source ON system_logs(source);
CREATE INDEX idx_system_logs_created ON system_logs(created_at);
```

---

## 三、观察数据库 Schema

### 3.1 观察会话表 (observation_sessions)

```sql
CREATE TABLE observation_sessions (
    session_id VARCHAR PRIMARY KEY,            -- 会话ID
    symbol VARCHAR NOT NULL,                   -- 品种
    timeframe VARCHAR NOT NULL,                -- 周期
    
    -- 会话状态
    status VARCHAR DEFAULT 'active',           -- 状态: active/completed
    
    -- 收缩信息
    contraction_detected_at TIMESTAMP,         -- 收缩检测时间
    contraction_ended_at TIMESTAMP,            -- 收缩结束时间
    contraction_duration_bars INTEGER,         -- 收缩持续K线数
    
    -- 突破信息
    breakout_occurred_at TIMESTAMP,            -- 突破时间
    breakout_direction VARCHAR,                -- 突破方向
    breakout_price DECIMAL(18,8),              -- 突破价格
    
    -- 趋势信息
    trend_started_at TIMESTAMP,                -- 趋势开始时间
    trend_ended_at TIMESTAMP,                  -- 趋势结束时间
    trend_result VARCHAR,                      -- 趋势结果
    
    -- 绩效
    total_return DECIMAL(10,4),                -- 总收益
    max_drawdown DECIMAL(10,4),                -- 最大回撤
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 每日收缩特征表 (daily_contraction_profiles)

```sql
CREATE TABLE daily_contraction_profiles (
    profile_id VARCHAR PRIMARY KEY,            -- 特征ID
    symbol VARCHAR NOT NULL,                   -- 品种
    date DATE NOT NULL,                        -- 日期
    
    -- 收缩特征
    is_contracting BOOLEAN,                    -- 是否收缩
    contraction_score INTEGER,                 -- 收缩评分
    bb_width DECIMAL(18,8),                    -- BB Width
    kaufman_width DECIMAL(18,8),               -- Kaufman Width
    atr_value DECIMAL(18,8),                   -- ATR值
    
    -- 历史百分位
    bb_width_percentile INTEGER,               -- BB Width百分位
    kaufman_width_percentile INTEGER,          -- Kaufman Width百分位
    atr_percentile INTEGER,                    -- ATR百分位
    
    -- 其他指标
    pivot_range DECIMAL(18,8),                 -- 枢轴区间
    volume_avg DECIMAL(18,8),                  -- 平均成交量
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3 品种收缩签名表 (symbol_signatures)

```sql
CREATE TABLE symbol_signatures (
    signature_id VARCHAR PRIMARY KEY,          -- 签名ID
    symbol VARCHAR NOT NULL,                   -- 品种
    
    -- 签名特征 (用于模式匹配)
    contraction_pattern VARCHAR,               -- 收缩模式
    avg_contraction_duration INTEGER,          -- 平均收缩时长
    avg_breakout_magnitude DECIMAL(10,4),      -- 平均突破幅度
    success_rate DECIMAL(5,4),                 -- 成功率
    
    -- 统计
    total_cases INTEGER,                       -- 总案例数
    bullish_cases INTEGER,                     -- 看涨案例数
    bearish_cases INTEGER,                     -- 看跌案例数
    
    -- 更新时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 四、数据流与ETL

### 4.1 实时数据流

```
MT5 Tick → ZeroMQ PUB → Python接收器 → 数据标准化 → DuckDB写入
                                                    ↓
                                              Parquet归档
                                                    ↓
                                              特征计算 → State Hex更新
                                                    ↓
                                              Agent通知
```

### 4.2 批量数据流

```
历史数据源 → 数据下载 → 清洗校验 → Parquet存储 → DuckDB加载
                                                    ↓
                                              特征工程
                                                    ↓
                                              回测引擎
```

### 4.3 数据清理任务

| 任务 | 频率 | 操作 |
|------|------|------|
| Tick数据归档 | 每日 | 7天前的Tick数据压缩归档到Parquet |
| State Hex清理 | 每周 | 删除90天前的State Hex快照 |
| Agent消息清理 | 每周 | 删除30天前的Agent消息 |
| 系统日志清理 | 每日 | 删除30天前的DEBUG/INFO日志 |
| 回测数据压缩 | 每月 | 压缩历史回测的详细交易数据 |

---

## 五、查询示例

### 5.1 查询品种最新State Hex

```sql
SELECT 
    symbol,
    d1_state,
    d1_description,
    w1_state,
    w1_description,
    mn1_state,
    mn1_description,
    resonance_score,
    resonance_type
FROM state_hex_snapshots
WHERE symbol = 'EURUSD'
ORDER BY timestamp DESC
LIMIT 1;
```

### 5.2 查询当前收缩列表

```sql
SELECT 
    symbol,
    timeframe,
    contraction_score,
    duration_bars,
    breakout_probability,
    predicted_direction,
    target_price
FROM contraction_events
WHERE ended_at IS NULL
ORDER BY contraction_score DESC;
```

### 5.3 查询策略回测历史

```sql
SELECT 
    b.backtest_id,
    b.status,
    br.total_return,
    br.sharpe_ratio,
    br.max_drawdown,
    br.total_trades,
    br.win_rate
FROM backtests b
LEFT JOIN backtest_results br ON b.backtest_id = br.backtest_id
WHERE b.strategy_id = 'str_abc123'
ORDER BY b.created_at DESC;
```

### 5.4 查询Agent消息历史

```sql
SELECT 
    msg_id,
    from_agent,
    to_agent,
    msg_type,
    priority,
    payload_json,
    created_at
FROM agent_messages
WHERE (from_agent = 'trader_001' OR to_agent = 'trader_001')
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 100;
```

### 5.5 查询收缩-突破-趋势全链路

```sql
SELECT 
    ce.symbol,
    ce.timeframe,
    ce.contraction_score,
    ce.detected_at as contraction_start,
    be.occurred_at as breakout_time,
    be.direction as breakout_direction,
    be.confirmation_score,
    tt.started_at as trend_start,
    tt.ended_at as trend_end,
    tt.realized_pnl,
    tt.result
FROM contraction_events ce
LEFT JOIN breakout_events be ON ce.breakout_event_id = be.event_id
LEFT JOIN trend_tracking tt ON be.event_id = tt.breakout_event_id
WHERE ce.symbol = 'EURUSD'
  AND ce.detected_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
ORDER BY ce.detected_at DESC;
```

### 5.6 查询多周期共振历史

```sql
SELECT 
    timestamp,
    mn1_state,
    w1_state,
    d1_state,
    h4_state,
    h1_state,
    resonance_score,
    bullish_count,
    bearish_count
FROM state_hex_snapshots
WHERE symbol = 'EURUSD'
  AND resonance_score >= 80
  AND timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

---

## 六、数据库初始化脚本

```sql
-- 创建主数据库
-- 运行: duckdb data/kimi_state.duckdb < init.sql

-- 启用外键约束
PRAGMA foreign_keys = ON;

-- 创建所有表
-- (上述所有CREATE TABLE语句)

-- 创建观察数据库
-- 运行: duckdb data/observation_db.duckdb < init_observation.sql

-- 创建观察表
-- (上述观察数据库CREATE TABLE语句)

-- 插入默认数据
INSERT INTO users (user_id, username, email, password_hash, role) 
VALUES ('user_admin', 'admin', 'admin@kimi-trading.com', 'HASH_VALUE', 'admin');

-- 创建视图
CREATE VIEW v_active_signals AS
SELECT * FROM signals WHERE status = 'active';

CREATE VIEW v_open_positions AS
SELECT * FROM positions WHERE status = 'open';

CREATE VIEW v_recent_breakouts AS
SELECT * FROM breakout_events 
WHERE occurred_at > CURRENT_TIMESTAMP - INTERVAL '24 hours';

CREATE VIEW v_agent_performance AS
SELECT 
    a.agent_id,
    a.name,
    a.agent_type,
    COUNT(s.signal_id) as signals_generated,
    AVG(CASE WHEN s.status = 'executed' THEN 1 ELSE 0 END) as execution_rate,
    AVG(p.realized_pnl) as avg_pnl
FROM agents a
LEFT JOIN signals s ON a.agent_id = s.source_agent
LEFT JOIN positions p ON s.signal_id = p.signal_id
WHERE a.status = 'running'
GROUP BY a.agent_id, a.name, a.agent_type;
```

---

## 七、附录

### 7.1 数据库连接配置

```python
import duckdb

# 主数据库连接
conn = duckdb.connect('data/kimi_state.duckdb')

# 观察数据库连接
obs_conn = duckdb.connect('data/observation_db.duckdb')

# 使用示例
cursor = conn.cursor()
cursor.execute("SELECT * FROM state_hex_snapshots WHERE symbol = 'EURUSD' ORDER BY timestamp DESC LIMIT 1")
result = cursor.fetchone()
```

### 7.2 备份策略

| 备份类型 | 频率 | 方式 |
|----------|------|------|
| 全量备份 | 每日 | DuckDB导出 + Parquet复制 |
| 增量备份 | 每小时 | 关键表数据导出 |
| 实时同步 | 持续 | 双写机制（主库+备库） |

### 7.3 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| V1.0 | 2026-06-06 | 初始版本，包含18张核心表和4张观察表 |
