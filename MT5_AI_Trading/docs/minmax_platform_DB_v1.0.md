# MiniMax AI量化平台 — 数据库设计

> 版本: v1.0 (minmax标识)  
> 日期: 2026-06-06  
> 状态: 正式版

---

## 1. 数据库架构

### 1.1 存储选型

| 数据类型 | 存储方案 | 理由 |
|----------|----------|------|
| **策略数据** | PostgreSQL | 结构化、事务支持、多租户 |
| **市场数据** | DuckDB | 分析查询高效、嵌入式 |
| **实时数据** | Redis | 低延迟、高并发 |
| **文件存储** | 本地文件系统 | K线CSV、报告PDF |
| **观察数据** | DuckDB | 已有observation_db基础 |

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MiniMax 数据库架构                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐    │
│   │   PostgreSQL    │      │     DuckDB      │      │     Redis       │    │
│   │   (主数据库)     │      │   (分析数据)     │      │   (缓存)        │    │
│   ├─────────────────┤      ├─────────────────┤      ├─────────────────┤    │
│   │ • users         │      │ • ohlcv_data    │      │ • session       │    │
│   │ • strategies    │      │ • state_hex    │      │ • rate_limit    │    │
│   │ • backtests     │      │ • observation  │      │ • market_cache  │    │
│   │ • deployments   │      │ • experiments   │      │ • locks         │    │
│   │ • trades        │      │ • signals       │      │                │    │
│   │ • alerts        │      │                │      │                │    │
│   └────────┬────────┘      └────────┬────────┘      └────────┬────────┘    │
│            │                       │                       │              │
│            └───────────────────────┼───────────────────────┘              │
│                                    │                                      │
│                                    ▼                                      │
│                          ┌─────────────────┐                              │
│                          │  数据同步层      │                              │
│                          │  (CDC + Cache)  │                              │
│                          └─────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. PostgreSQL数据模型

### 2.1 用户管理

```sql
-- 用户表
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key VARCHAR(64) UNIQUE,
    api_key_expires_at TIMESTAMP,
    
    -- 用户配置
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    notification_enabled BOOLEAN DEFAULT true,
    notification_channels VARCHAR[] DEFAULT ARRAY['email'],
    
    -- 配额
    quota_backtests INTEGER DEFAULT 100,
    quota_strategies INTEGER DEFAULT 50,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

CREATE INDEX idx_users_api_key ON users(api_key);
CREATE INDEX idx_users_status ON users(status);
```

### 2.2 策略管理

```sql
-- 策略表
CREATE TABLE strategies (
    strategy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    
    -- 基本信息
    name VARCHAR(100) NOT NULL,
    description TEXT,
    template_id VARCHAR(50) NOT NULL,
    
    -- 代码与参数
    code TEXT NOT NULL,
    params JSONB DEFAULT '{}',
    
    -- 状态
    status VARCHAR(20) DEFAULT 'draft',  -- draft/validated/deployed/retired
    
    -- 统计
    backtest_count INTEGER DEFAULT 0,
    deployment_count INTEGER DEFAULT 0,
    
    -- 版本控制
    version INTEGER DEFAULT 1,
    parent_strategy_id UUID REFERENCES strategies(strategy_id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_strategies_user ON strategies(user_id);
CREATE INDEX idx_strategies_template ON strategies(template_id);
CREATE INDEX idx_strategies_status ON strategies(status);

-- 策略版本历史
CREATE TABLE strategy_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(strategy_id),
    version INTEGER NOT NULL,
    code TEXT NOT NULL,
    params JSONB,
    changelog TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(strategy_id, version)
);
```

### 2.3 回测管理

```sql
-- 回测表
CREATE TABLE backtests (
    backtest_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    strategy_id UUID NOT NULL REFERENCES strategies(strategy_id),
    
    -- 配置
    config JSONB NOT NULL,  -- {symbols, timeframes, date_range, ...}
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',  -- pending/running/completed/failed
    
    -- 结果
    result JSONB,  -- 完整回测报告
    
    -- 性能指标
    total_return DECIMAL(10, 4),
    annual_return DECIMAL(10, 4),
    sharpe_ratio DECIMAL(8, 4),
    max_drawdown DECIMAL(10, 4),
    win_rate DECIMAL(8, 4),
    profit_factor DECIMAL(8, 4),
    total_trades INTEGER,
    
    -- 时间
    elapsed_ms INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_backtests_user ON backtests(user_id);
CREATE INDEX idx_backtests_strategy ON backtests(strategy_id);
CREATE INDEX idx_backtests_status ON backtests(status);
CREATE INDEX idx_backtests_created ON backtests(created_at DESC);
```

### 2.4 部署管理

```sql
-- 部署表
CREATE TABLE deployments (
    deployment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    strategy_id UUID NOT NULL REFERENCES strategies(strategy_id),
    
    -- 配置
    symbol VARCHAR(20) NOT NULL,
    lot_size DECIMAL(10, 4),
    risk_per_trade DECIMAL(8, 4),
    
    -- MT5关联
    mt5_ticket INTEGER,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',  -- pending/active/paused/stopped/failed
    target VARCHAR(20) DEFAULT 'simulation',  -- simulation/live
    
    -- 绩效
    current_pnl DECIMAL(12, 4) DEFAULT 0,
    current_pnl_pct DECIMAL(10, 4) DEFAULT 0,
    backtest_deviation DECIMAL(10, 4),  -- 实盘vs回测偏差
    
    -- 风控
    daily_loss_limit DECIMAL(10, 4),
    total_loss_limit DECIMAL(10, 4),
    
    -- 时间
    started_at TIMESTAMP,
    stopped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_deployments_user ON deployments(user_id);
CREATE INDEX idx_deployments_strategy ON deployments(strategy_id);
CREATE INDEX idx_deployments_status ON deployments(status);

-- 部署交易记录
CREATE TABLE deployment_trades (
    trade_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID NOT NULL REFERENCES deployments(deployment_id),
    
    -- 交易信息
    mt5_ticket INTEGER,
    direction VARCHAR(10),  -- long/short
    entry_price DECIMAL(15, 6),
    exit_price DECIMAL(15, 6),
    volume DECIMAL(10, 4),
    
    -- 盈亏
    pnl DECIMAL(12, 4),
    pnl_pct DECIMAL(10, 4),
    commission DECIMAL(10, 4),
    swap DECIMAL(10, 4),
    
    -- 时间
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    holding_bars INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_deployment_trades_deployment ON deployment_trades(deployment_id);
```

### 2.5 告警管理

```sql
-- 告警表
CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    
    -- 告警类型
    type VARCHAR(50) NOT NULL,  -- reification/squeeze/resonance/risk
    severity VARCHAR(20) DEFAULT 'info',  -- info/warning/critical
    
    -- 告警内容
    title VARCHAR(200),
    message TEXT,
    data JSONB,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'new',  -- new/acknowledged/resolved/dismissed
    
    -- 时间
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_alerts_user ON alerts(user_id);
CREATE INDEX idx_alerts_type ON alerts(type);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_triggered ON alerts(triggered_at DESC);
```

---

## 3. DuckDB数据模型

### 3.1 K线数据

```sql
-- OHLCV数据表
CREATE TABLE ohlcv_data (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    PRIMARY KEY (symbol, timeframe, timestamp)
);

-- 分区存储
CREATE INDEX idx_ohlcv_symbol_time ON ohlcv_data(symbol, timeframe);

-- 点差历史
CREATE TABLE spread_history (
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    spread_points INTEGER,
    spread_value DOUBLE,
    PRIMARY KEY (symbol, timestamp)
);
```

### 3.2 State Hex数据

```sql
-- State Hex快照
CREATE TABLE state_hex_snapshots (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- State Hex编码
    state_hex VARCHAR(1),        -- 0-F
    base_state INTEGER,           -- 0/8 收缩/非收缩底座
    volatility_state INTEGER,      -- 0/1 低/高波动
    position_state INTEGER,       -- 0/2 低位/高位
    trend_state INTEGER,          -- 0/4 无/有趋势
    
    -- 收缩分析
    contraction_pct DOUBLE,       -- 收缩占比
    bb_width DOUBLE,              -- Bollinger带宽
    squeeze_bars INTEGER,         -- 连续收缩K线数
    
    PRIMARY KEY (symbol, timeframe, timestamp)
);

CREATE INDEX idx_state_symbol_time ON state_hex_snapshots(symbol, timeframe);
```

### 3.3 观察数据库（扩展现有）

基于现有 `observation_db.py` 扩展：

```sql
-- 观察会话
CREATE TABLE observation_sessions (
    session_id INTEGER PRIMARY KEY,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 日收缩画像
CREATE TABLE daily_contraction_profiles (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES observation_sessions(session_id),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    contraction_pct DOUBLE,
    max_contraction_streak INTEGER,
    breakout_bars INTEGER,
    direction VARCHAR(10),
    UNIQUE(session_id, symbol, timeframe, date)
);

-- 品种签名
CREATE TABLE symbol_signatures (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES observation_sessions(session_id),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    overall_contraction_pct DOUBLE,
    max_daily_contraction_pct DOUBLE,
    std_daily_contraction_pct DOUBLE,
    d1_h4_combo VARCHAR(10),
    reification_threshold DOUBLE DEFAULT 70.0,
    UNIQUE(session_id, symbol, timeframe)
);

-- 关键观察
CREATE TABLE key_observations (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES observation_sessions(session_id),
    observation_type VARCHAR(50),
    symbol VARCHAR(20),
    timeframe VARCHAR(10),
    description TEXT,
    significance VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 复现告警
CREATE TABLE reification_alerts (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    signature_id INTEGER REFERENCES symbol_signatures(id),
    alert_time TIMESTAMP,
    match_score DOUBLE,
    threshold_used DOUBLE,
    triggered BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.4 实验数据

```sql
-- 实验结果（策略挖掘）
CREATE TABLE experiments (
    experiment_id VARCHAR(100) PRIMARY KEY,
    session_id INTEGER,
    config JSONB,
    results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Redis数据结构

### 4.1 会话管理

```
# 用户会话
session:{user_id} -> {
    "token": "xxx",
    "last_activity": timestamp,
    "settings": {...}
}
TTL: 24h
```

### 4.2 市场缓存

```
# 最新行情
market:tick:{symbol} -> {
    "bid": 2315.50,
    "ask": 2316.00,
    "timestamp": timestamp
}
TTL: 5s

# State Hex缓存
market:state:{symbol}:{timeframe} -> {
    "state_hex": "0",
    "contraction_pct": 0.89,
    "timestamp": timestamp
}
TTL: 60s
```

### 4.3 限流

```
# API限流
ratelimit:{user_id}:{endpoint} -> count
TTL: 60s
```

### 4.4 分布式锁

```
# 部署锁
lock:deployment:{deployment_id} -> holder_id
TTL: 30s
```

---

## 5. 数据流设计

### 5.1 实时数据流

```
MT5 Terminal
     │
     │ ZeroMQ PUB (5565)
     ▼
MT5Bridge
     │
     ├─→ Redis (market:tick:*)
     │
     ├─→ DuckDB (ohlcv_data) [批量]
     │
     └─→ StateHexEngine
              │
              ├─→ DuckDB (state_hex_snapshots)
              │
              └─→ Agent Pipeline
```

### 5.2 策略数据流

```
User Request
     │
     ▼
FastAPI (Strategy API)
     │
     ├─→ PostgreSQL (strategies)
     │
     ├─→ Backtest Engine
     │        │
     │        ├─→ DuckDB (ohlcv_data)
     │        │
     │        └─→ DuckDB (experiments)
     │
     └─→ Redis (session)
```

### 5.3 观察数据流

```
Market Observer
     │
     ▼
Scanners (StateHex, Squeeze, Resonance)
     │
     ▼
Reification Detection
     │
     ▼
DuckDB (observation_sessions, key_observations)
     │
     ▼
Alert System
     │
     ├─→ PostgreSQL (alerts)
     │
     └─→ Notification (Telegram, Email)
```

---

## 6. 索引设计

### 6.1 PostgreSQL索引

```sql
-- 用户查询优化
CREATE INDEX idx_users_email ON users(email);

-- 策略查询优化
CREATE INDEX idx_strategies_user_status ON strategies(user_id, status);
CREATE INDEX idx_strategies_template_created ON strategies(template_id, created_at DESC);

-- 回测查询优化
CREATE INDEX idx_backtests_user_created ON backtests(user_id, created_at DESC);
CREATE INDEX idx_backtests_strategy_perf ON backtests(strategy_id, total_return DESC);

-- 部署查询优化
CREATE INDEX idx_deployments_user_status ON deployments(user_id, status);
CREATE INDEX idx_deployments_active ON deployments(status) WHERE status = 'active';

-- 告警查询优化
CREATE INDEX idx_alerts_user_unread ON alerts(user_id, status) WHERE status IN ('new', 'acknowledged');
```

### 6.2 DuckDB索引

```sql
-- K线查询优化
CREATE INDEX idx_ohlcv_ts ON ohlcv_data(timestamp);
CREATE INDEX idx_ohlcv_symbol_range ON ohlcv_data(symbol, timeframe, timestamp);

-- State Hex查询优化
CREATE INDEX idx_state_ts ON state_hex_snapshots(timestamp);
CREATE INDEX idx_state_contraction ON state_hex_snapshots(contraction_pct DESC);
```

---

## 7. 数据保留策略

| 数据类型 | 保留期限 | 归档策略 |
|----------|----------|----------|
| Tick数据 | 1天 | 聚合后删除 |
| M15 K线 | 90天 | 压缩归档 |
| H1 K线 | 2年 | 压缩归档 |
| D1+ K线 | 永久 | 长期存储 |
| State Hex | 1年 | 聚合后删除 |
| 回测结果 | 永久 | 长期存储 |
| 策略代码 | 永久 | 版本控制 |
| 观察数据 | 永久 | 长期存储 |

---

## 8. 数据安全

### 8.1 敏感数据加密

```sql
-- API Key加密存储
ALTER TABLE users ADD COLUMN api_key_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN api_key_iv VARCHAR(32);

-- 加密函数
CREATE OR REPLACE FUNCTION encrypt_api_key(key TEXT)
RETURNS JSONB AS $$
DECLARE
    iv_bytes BYTEA;
    encrypted BYTEA;
BEGIN
    iv_bytes := gen_random_bytes(16);
    encrypted := encrypt(key::bytea, current_setting('app.secret_key')::bytea, 'aes', iv_bytes);
    RETURN jsonb_build_object(
        'encrypted', encode(encrypted, 'hex'),
        'iv', encode(iv_bytes, 'hex')
    );
END;
$$ LANGUAGE plpgsql;
```

### 8.2 访问控制

```sql
-- 行级安全策略
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategies FORCE ROW LEVEL SECURITY;

CREATE POLICY strategy_user_access ON strategies
    USING (user_id = current_setting('app.current_user_id')::UUID);

ALTER TABLE backtests ENABLE ROW LEVEL SECURITY;
ALTER TABLE deployments ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
```

---

## 9. 备份策略

| 数据类型 | 备份频率 | 保留期限 | 恢复目标 |
|----------|----------|----------|----------|
| PostgreSQL | 每日全量 | 30天 | RPO<1天, RTO<1小时 |
| DuckDB | 每周全量 | 90天 | RPO<1周, RTO<4小时 |
| Redis | 主从同步 | - | RPO<1秒 |
| 文件存储 | 每周增量 | 1年 | RPO<1周 |

---

## 10. 现有数据迁移

基于现有 `observation_db.py` 的表结构：

```sql
-- 现有表（保持兼容）
observation_sessions
daily_contraction_profiles
symbol_signatures
key_observations
reification_alerts

-- 新增表
CREATE SEQUENCE IF NOT EXISTS observation_sessions_session_id_seq;
ALTER TABLE observation_sessions ALTER COLUMN session_id 
    SET DEFAULT nextval('observation_sessions_session_id_seq');

CREATE SEQUENCE IF NOT EXISTS daily_contraction_profiles_id_seq;
ALTER TABLE daily_contraction_profiles ALTER COLUMN id 
    SET DEFAULT nextval('daily_contraction_profiles_id_seq');
```