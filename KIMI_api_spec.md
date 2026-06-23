# KIMI AI量化多周期视角交易平台 - API接口规范

**版本**: V1.0  
**日期**: 2026-06-06  
**文档编号**: KIMI-API-001  
**协议**: HTTP/REST + WebSocket + ZeroMQ + MCP  
**设计原则**: 基于GitHub前沿开源项目独立设计，参考Vibe-Trading的API设计和TradingAgents的通信协议

---

## 一、接口概述

### 1.1 接口分类

| 接口类型 | 协议 | 用途 | 适用场景 |
|----------|------|------|----------|
| REST API | HTTP/1.1 | 同步请求/响应 | 策略管理、回测任务、数据查询 |
| WebSocket | WS | 实时数据推送 | 行情推送、Agent状态、交易信号 |
| ZeroMQ | TCP | MT5桥接通信 | 实时行情接收、交易指令发送 |
| MCP | stdio/SSE | AI Agent工具调用 | Claude/Cursor等AI助手集成 |

### 1.2 通用约定

#### 1.2.1 基础URL

```
开发环境: http://localhost:8899/api/v1
生产环境: https://api.kimi-trading.com/api/v1
```

#### 1.2.2 认证方式

- **REST API**: Bearer Token (JWT)
- **WebSocket**: 连接时通过query参数传递token
- **ZeroMQ**: 基于IP白名单和消息签名
- **MCP**: 本地stdio或SSE连接，无额外认证

#### 1.2.3 通用响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "timestamp": "2026-06-06T10:30:00Z",
  "request_id": "req_abc123"
}
```

#### 1.2.4 错误码定义

| 错误码 | 含义 | HTTP状态码 |
|--------|------|-----------|
| 0 | 成功 | 200 |
| 1001 | 参数错误 | 400 |
| 1002 | 认证失败 | 401 |
| 1003 | 权限不足 | 403 |
| 1004 | 资源不存在 | 404 |
| 1005 | 请求过于频繁 | 429 |
| 2001 | 策略语法错误 | 400 |
| 2002 | 回测执行失败 | 500 |
| 2003 | 数据加载失败 | 500 |
| 3001 | Agent未启动 | 400 |
| 3002 | 风控限制触发 | 403 |
| 3003 | 交易执行失败 | 500 |
| 5001 | 内部服务器错误 | 500 |

---

## 二、REST API详细规范

### 2.1 认证接口

#### POST /auth/login
用户登录获取JWT Token

**请求参数**:
```json
{
  "username": "trader001",
  "password": "encrypted_password"
}
```

**响应示例**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600,
    "token_type": "Bearer"
  }
}
```

#### POST /auth/refresh
刷新Access Token

**请求参数**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

### 2.2 策略管理接口

#### POST /strategies/nl-create
自然语言创建策略

**请求参数**:
```json
{
  "description": "创建一个均线金叉策略，MA5上穿MA20时买入，跌破MA10时卖出",
  "target_formats": ["python", "mql5", "pine_script"],
  "risk_params": {
    "stop_loss_pips": 50,
    "take_profit_pips": 100,
    "max_position_size": 0.1
  }
}
```

**响应示例**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "strategy_id": "str_abc123",
    "intent": {
      "strategy_type": "trend_following",
      "entry_conditions": [
        {"indicator": "MA5", "condition": "cross_above", "reference": "MA20"}
      ],
      "exit_conditions": [
        {"indicator": "MA5", "condition": "cross_below", "reference": "MA10"}
      ]
    },
    "generated_code": {
      "python": "import vectorbt as vbt...",
      "mql5": "//+------------------------------------------------------------------+...",
      "pine_script": "//@version=6..."
    },
    "validation": {
      "is_valid": true,
      "errors": [],
      "warnings": ["建议添加仓位管理逻辑"]
    },
    "template_used": "ma_crossover",
    "created_at": "2026-06-06T10:30:00Z"
  }
}
```

#### GET /strategies
获取策略列表

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |
| strategy_type | string | 否 | 策略类型过滤 |
| status | string | 否 | 状态过滤 (draft/validated/active) |

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "total": 45,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "strategy_id": "str_abc123",
        "name": "MA Crossover Strategy",
        "type": "trend_following",
        "status": "validated",
        "created_at": "2026-06-06T10:30:00Z",
        "updated_at": "2026-06-06T10:30:00Z",
        "backtest_count": 3,
        "best_sharpe": 1.85
      }
    ]
  }
}
```

#### GET /strategies/{strategy_id}
获取策略详情

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "strategy_id": "str_abc123",
    "name": "MA Crossover Strategy",
    "description": "均线金叉策略",
    "type": "trend_following",
    "status": "validated",
    "intent": {...},
    "code": {
      "python": "...",
      "mql5": "..."
    },
    "parameters": {
      "fast_ma": {"default": 5, "min": 2, "max": 50},
      "slow_ma": {"default": 20, "min": 10, "max": 200}
    },
    "risk_params": {...},
    "backtests": ["bt_001", "bt_002"],
    "created_at": "2026-06-06T10:30:00Z"
  }
}
```

#### PUT /strategies/{strategy_id}
更新策略

**请求参数**:
```json
{
  "code": {
    "python": "updated code..."
  },
  "parameters": {
    "fast_ma": 10
  }
}
```

#### DELETE /strategies/{strategy_id}
删除策略

#### POST /strategies/{strategy_id}/validate
验证策略

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "is_valid": true,
    "errors": [],
    "warnings": ["建议添加止损逻辑"],
    "ast_tree": {...},
    "quick_backtest": {
      "status": "success",
      "trades": 5,
      "win_rate": 0.6
    }
  }
}
```

---

### 2.3 回测接口

#### POST /backtests
创建回测任务

**请求参数**:
```json
{
  "strategy_id": "str_abc123",
  "config": {
    "symbols": ["EURUSD"],
    "timeframe": "H1",
    "start_date": "2025-01-01",
    "end_date": "2026-01-01",
    "initial_balance": 10000,
    "commission": 0.001,
    "slippage": 0.0001
  },
  "optimization": {
    "enabled": true,
    "method": "grid",
    "param_grid": {
      "fast_ma": [5, 10, 20],
      "slow_ma": [20, 50, 100]
    },
    "metric": "sharpe_ratio"
  }
}
```

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "backtest_id": "bt_xyz789",
    "status": "queued",
    "estimated_duration": 30,
    "created_at": "2026-06-06T10:30:00Z"
  }
}
```

#### GET /backtests/{backtest_id}/status
获取回测状态

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "backtest_id": "bt_xyz789",
    "status": "running",
    "progress": 65,
    "current_phase": "calculating_metrics",
    "started_at": "2026-06-06T10:30:05Z",
    "elapsed_seconds": 15
  }
}
```

#### GET /backtests/{backtest_id}/results
获取回测结果

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "backtest_id": "bt_xyz789",
    "status": "completed",
    "config": {...},
    "metrics": {
      "total_return": 25.5,
      "annualized_return": 25.5,
      "sharpe_ratio": 1.85,
      "sortino_ratio": 2.34,
      "calmar_ratio": 1.42,
      "max_drawdown": -18.0,
      "max_drawdown_duration": "45 days",
      "win_rate": 58.3,
      "profit_factor": 1.72,
      "total_trades": 120,
      "avg_trade_return": 0.21
    },
    "optimization_results": [
      {
        "params": {"fast_ma": 10, "slow_ma": 50},
        "sharpe_ratio": 1.85,
        "total_return": 25.5
      },
      {
        "params": {"fast_ma": 5, "slow_ma": 20},
        "sharpe_ratio": 1.62,
        "total_return": 22.1
      }
    ],
    "equity_curve": {
      "timestamps": ["2025-01-01", "2025-02-01", ...],
      "values": [10000, 10200, ...]
    },
    "trades": [
      {
        "entry_time": "2025-01-15T10:00:00Z",
        "exit_time": "2025-01-20T14:00:00Z",
        "symbol": "EURUSD",
        "direction": "LONG",
        "entry_price": 1.0850,
        "exit_price": 1.0920,
        "size": 0.1,
        "pnl": 70.0,
        "pnl_pct": 0.7
      }
    ],
    "report_url": "/reports/bt_xyz789.html",
    "completed_at": "2026-06-06T10:30:35Z"
  }
}
```

#### GET /backtests/{backtest_id}/report
获取回测报告

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| format | string | 否 | 报告格式 (html/pdf/json)，默认html |

---

### 2.4 Agent管理接口

#### GET /agents
获取Agent列表

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "agents": [
      {
        "agent_id": "research_tech_001",
        "name": "Technical Researcher",
        "type": "research",
        "state": "running",
        "uptime_seconds": 3600,
        "messages_processed": 150,
        "last_activity": "2026-06-06T10:29:00Z"
      },
      {
        "agent_id": "trader_001",
        "name": "Main Trader",
        "type": "trader",
        "state": "running",
        "uptime_seconds": 3600,
        "signals_generated": 12,
        "orders_executed": 8
      },
      {
        "agent_id": "risk_001",
        "name": "Risk Manager",
        "type": "risk",
        "state": "running",
        "checks_performed": 500,
        "alerts_triggered": 2
      }
    ]
  }
}
```

#### POST /agents/{agent_id}/control
控制Agent状态

**请求参数**:
```json
{
  "action": "start"  // start/stop/pause/resume/restart
}
```

#### GET /agents/{agent_id}/messages
获取Agent消息历史

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | int | 否 | 返回数量，默认50 |
| msg_type | string | 否 | 消息类型过滤 |

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "messages": [
      {
        "msg_id": "msg_001",
        "from_agent": "research_tech_001",
        "to_agent": "trader_001",
        "msg_type": "SIGNAL",
        "priority": 1,
        "timestamp": "2026-06-06T10:30:00Z",
        "payload": {
          "signal_type": "BUY",
          "symbol": "EURUSD",
          "confidence": 0.85
        }
      }
    ]
  }
}
```

#### GET /agents/{agent_id}/status
获取Agent详细状态

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "agent_id": "trader_001",
    "name": "Main Trader",
    "type": "trader",
    "state": "running",
    "context": {
      "active_positions": {
        "EURUSD": {
          "direction": "LONG",
          "size": 0.1,
          "entry_price": 1.0850,
          "current_pnl": 25.0
        }
      },
      "pending_signals": 2
    },
    "performance": {
      "signals_total": 50,
      "signals_executed": 45,
      "win_rate": 0.62,
      "avg_profit": 35.0,
      "avg_loss": -20.0
    }
  }
}
```

---

### 2.5 市场数据接口

#### GET /market/quotes
获取实时行情

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbols | string | 是 | 品种列表，逗号分隔 |

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "quotes": [
      {
        "symbol": "EURUSD",
        "bid": 1.0850,
        "ask": 1.0852,
        "spread": 0.0002,
        "timestamp": "2026-06-06T10:30:00.100Z"
      }
    ]
  }
}
```

#### GET /market/klines
获取K线数据

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 品种 |
| timeframe | string | 是 | 周期 |
| start | string | 否 | 开始时间 |
| end | string | 否 | 结束时间 |
| limit | int | 否 | 数量限制 |

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "symbol": "EURUSD",
    "timeframe": "H1",
    "klines": [
      {
        "timestamp": "2026-06-06T09:00:00Z",
        "open": 1.0845,
        "high": 1.0855,
        "low": 1.0840,
        "close": 1.0850,
        "volume": 1250
      }
    ]
  }
}
```

#### GET /market/resonance
获取多周期共振分析

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 品种 |
| timeframes | string | 否 | 周期列表，默认MN1,W1,D1,H4,H1 |

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "symbol": "EURUSD",
    "resonance_score": 85,
    "resonance_type": "trend_bullish",
    "timeframes": {
      "MN1": {"state": "A", "description": "bullish_trend+expansion", "direction": "bullish"},
      "W1": {"state": "2", "description": "contraction_breakout", "direction": "bullish"},
      "D1": {"state": "A", "description": "bullish_trend+expansion", "direction": "bullish"},
      "H4": {"state": "6", "description": "bullish_contraction", "direction": "neutral"},
      "H1": {"state": "A", "description": "bullish_trend+expansion", "direction": "bullish"}
    },
    "alignment": {
      "bullish_count": 4,
      "bearish_count": 0,
      "neutral_count": 1
    },
    "last_updated": "2026-06-06T10:30:00Z"
  }
}
```

#### GET /market/contractions
获取收缩监控列表

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "contractions": [
      {
        "symbol": "EURUSD",
        "timeframe": "D1",
        "contraction_score": 78,
        "duration_bars": 15,
        "bb_width_percentile": 15,
        "kaufman_width_percentile": 20,
        "atr_percentile": 18,
        "breakout_probability": 0.75,
        "predicted_direction": "bullish",
        "target_price": 1.0950,
        "detected_at": "2026-06-01T00:00:00Z"
      }
    ]
  }
}
```

---

### 2.6 交易接口

#### GET /account/positions
获取持仓列表

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "positions": [
      {
        "position_id": "pos_001",
        "symbol": "EURUSD",
        "direction": "LONG",
        "size": 0.1,
        "entry_price": 1.0850,
        "current_price": 1.0875,
        "unrealized_pnl": 25.0,
        "unrealized_pnl_pct": 0.25,
        "stop_loss": 1.0800,
        "take_profit": 1.0950,
        "open_time": "2026-06-06T09:00:00Z"
      }
    ],
    "summary": {
      "total_positions": 1,
      "total_exposure": 0.1,
      "total_unrealized_pnl": 25.0,
      "margin_used": 100.0
    }
  }
}
```

#### POST /account/orders
下单

**请求参数**:
```json
{
  "symbol": "EURUSD",
  "direction": "BUY",
  "order_type": "MARKET",
  "size": 0.1,
  "stop_loss": 1.0800,
  "take_profit": 1.0950,
  "comment": "MA Crossover Signal"
}
```

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "order_id": "ord_001",
    "status": "filled",
    "symbol": "EURUSD",
    "direction": "BUY",
    "size": 0.1,
    "fill_price": 1.0851,
    "fill_time": "2026-06-06T10:30:00Z"
  }
}
```

#### GET /account/orders
获取订单历史

#### DELETE /account/orders/{order_id}
撤单

---

### 2.7 监控接口

#### GET /monitor/system
系统状态监控

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "system": {
      "uptime_seconds": 3600,
      "cpu_usage": 35.2,
      "memory_usage": 2048,
      "disk_usage": 15.5
    },
    "mt5_connection": {
      "status": "connected",
      "latency_ms": 12,
      "last_heartbeat": "2026-06-06T10:30:00Z"
    },
    "data_pipeline": {
      "status": "running",
      "symbols_tracked": 10,
      "ticks_per_second": 5
    },
    "agents": {
      "total": 6,
      "running": 6,
      "errors": 0
    }
  }
}
```

#### GET /monitor/performance
性能指标

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "api_latency": {
      "p50": 15,
      "p95": 45,
      "p99": 120
    },
    "backtest_throughput": {
      "jobs_per_minute": 5,
      "avg_duration_seconds": 25
    },
    "agent_message_latency": {
      "p50": 5,
      "p95": 20
    }
  }
}
```

---

## 三、WebSocket实时推送协议

### 3.1 连接方式

```javascript
const ws = new WebSocket('ws://localhost:8899/ws?token=YOUR_JWT_TOKEN');
```

### 3.2 消息格式

```json
{
  "channel": "market",
  "event": "tick",
  "data": {...},
  "timestamp": "2026-06-06T10:30:00Z"
}
```

### 3.3 频道说明

| 频道 | 事件 | 说明 |
|------|------|------|
| market | tick | 实时Tick推送 |
| market | kline | K线更新 |
| agent | status_change | Agent状态变化 |
| agent | message | Agent间消息 |
| signal | new_signal | 新交易信号 |
| risk | alert | 风险告警 |
| system | heartbeat | 系统心跳 |

### 3.4 订阅示例

```javascript
// 订阅市场行情
ws.send(JSON.stringify({
  "action": "subscribe",
  "channels": ["market"],
  "symbols": ["EURUSD", "GBPUSD"]
}));

// 订阅Agent状态
ws.send(JSON.stringify({
  "action": "subscribe",
  "channels": ["agent"],
  "agents": ["trader_001", "risk_001"]
}));
```

---

## 四、ZeroMQ通信接口

### 4.1 MT5 → Python (PUB/SUB)

**端口**: 5555  
**模式**: PUB/SUB  
**用途**: MT5推送实时行情和状态

#### 4.1.1 Tick数据消息

```json
{
  "msg_type": "TICK",
  "symbol": "EURUSD",
  "bid": 1.0850,
  "ask": 1.0852,
  "spread": 0.0002,
  "timestamp": "2026-06-06T10:30:00.100Z"
}
```

#### 4.1.2 OHLCV数据消息

```json
{
  "msg_type": "OHLCV",
  "symbol": "EURUSD",
  "timeframe": "H1",
  "open": 1.0845,
  "high": 1.0855,
  "low": 1.0840,
  "close": 1.0850,
  "volume": 1250,
  "timestamp": "2026-06-06T10:00:00Z"
}
```

#### 4.1.3 账户状态消息

```json
{
  "msg_type": "ACCOUNT",
  "balance": 10500.0,
  "equity": 10525.0,
  "margin": 100.0,
  "free_margin": 10425.0,
  "margin_level": 10525.0,
  "timestamp": "2026-06-06T10:30:00Z"
}
```

### 4.2 Python → MT5 (REQ/REP)

**端口**: 5556  
**模式**: REQ/REP  
**用途**: Python发送交易指令

#### 4.2.1 下单请求

```json
{
  "action": "ORDER_SEND",
  "symbol": "EURUSD",
  "cmd": "BUY",
  "volume": 0.1,
  "price": 0,
  "slippage": 3,
  "stoploss": 1.0800,
  "takeprofit": 1.0950,
  "comment": "KIMI Signal",
  "request_id": "req_001"
}
```

#### 4.2.2 下单响应

```json
{
  "status": "success",
  "order_id": 12345,
  "ticket": 12345,
  "price": 1.0851,
  "request_id": "req_001"
}
```

#### 4.2.3 查询持仓请求

```json
{
  "action": "GET_POSITIONS",
  "request_id": "req_002"
}
```

#### 4.2.4 查询持仓响应

```json
{
  "status": "success",
  "positions": [
    {
      "ticket": 12345,
      "symbol": "EURUSD",
      "type": "BUY",
      "volume": 0.1,
      "open_price": 1.0850,
      "current_price": 1.0875,
      "profit": 25.0
    }
  ],
  "request_id": "req_002"
}
```

### 4.3 心跳协议

**频率**: 每5秒  
**超时**: 500ms无响应判定断线

#### 4.3.1 心跳请求

```json
{
  "action": "PING",
  "timestamp": "2026-06-06T10:30:00Z"
}
```

#### 4.3.2 心跳响应

```json
{
  "action": "PONG",
  "timestamp": "2026-06-06T10:30:00Z"
}
```

---

## 五、MCP工具接口

### 5.1 工具列表

| 工具名 | 描述 | 输入参数 | 返回值 |
|--------|------|----------|--------|
| analyze_market | 分析市场状态 | symbol, timeframe | 市场分析报告 |
| run_backtest | 运行策略回测 | strategy_code, symbol, timeframe, days | 回测结果 |
| get_signal | 获取交易信号 | symbol | 最新信号 |
| get_portfolio | 获取组合状态 | - | 组合持仓和绩效 |
| get_state_hex | 获取State Hex | symbol, timeframes | 五元组状态 |
| get_contractions | 获取收缩列表 | symbol(可选) | 收缩监控列表 |
| get_resonance | 获取共振分析 | symbol | 多周期共振评分 |
| create_strategy | 创建策略 | description | 生成的策略代码 |
| validate_strategy | 验证策略 | code, target | 验证结果 |
| place_order | 下单 | symbol, direction, size, sl, tp | 订单结果 |
| get_positions | 获取持仓 | - | 持仓列表 |
| cancel_order | 撤单 | order_id | 撤单结果 |
| get_agent_status | 获取Agent状态 | agent_id | Agent状态 |
| get_backtest_report | 获取回测报告 | backtest_id | 报告内容 |
| get_market_data | 获取市场数据 | symbol, timeframe, limit | K线数据 |
| get_account_info | 获取账户信息 | - | 账户余额和权益 |

### 5.2 工具定义示例

```json
{
  "name": "analyze_market",
  "description": "分析指定品种的市场状态，包括趋势、波动率、支撑阻力位等",
  "inputSchema": {
    "type": "object",
    "properties": {
      "symbol": {
        "type": "string",
        "description": "交易品种，如EURUSD"
      },
      "timeframe": {
        "type": "string",
        "description": "分析周期",
        "enum": ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"],
        "default": "H1"
      }
    },
    "required": ["symbol"]
  }
}
```

### 5.3 调用示例

```python
# Claude/Cursor中调用MCP工具
# 用户: "分析EURUSD的市场状态"

# MCP客户端自动调用:
result = await mcp_client.call_tool("analyze_market", {
    "symbol": "EURUSD",
    "timeframe": "H1"
})

# 返回:
{
  "symbol": "EURUSD",
  "current_price": 1.0850,
  "trend": "bullish",
  "trend_strength": 0.75,
  "volatility": "low",
  "support_levels": [1.0800, 1.0750],
  "resistance_levels": [1.0900, 1.0950],
  "recommendation": "Consider long positions with SL at 1.0800"
}
```

---

## 六、SDK示例

### 6.1 Python SDK

```python
import requests
from typing import Optional

class KIMIClient:
    """KIMI AI Trading API Client"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def create_strategy(self, description: str) -> dict:
        """自然语言创建策略"""
        response = requests.post(
            f"{self.base_url}/api/v1/strategies/nl-create",
            headers=self.headers,
            json={"description": description}
        )
        return response.json()
    
    def run_backtest(self, strategy_id: str, config: dict) -> dict:
        """运行回测"""
        response = requests.post(
            f"{self.base_url}/api/v1/backtests",
            headers=self.headers,
            json={"strategy_id": strategy_id, "config": config}
        )
        return response.json()
    
    def get_backtest_results(self, backtest_id: str) -> dict:
        """获取回测结果"""
        response = requests.get(
            f"{self.base_url}/api/v1/backtests/{backtest_id}/results",
            headers=self.headers
        )
        return response.json()
    
    def get_market_resonance(self, symbol: str) -> dict:
        """获取多周期共振分析"""
        response = requests.get(
            f"{self.base_url}/api/v1/market/resonance",
            headers=self.headers,
            params={"symbol": symbol}
        )
        return response.json()
    
    def place_order(self, symbol: str, direction: str, size: float, 
                    sl: Optional[float] = None, tp: Optional[float] = None) -> dict:
        """下单"""
        payload = {
            "symbol": symbol,
            "direction": direction,
            "order_type": "MARKET",
            "size": size
        }
        if sl:
            payload["stop_loss"] = sl
        if tp:
            payload["take_profit"] = tp
        
        response = requests.post(
            f"{self.base_url}/api/v1/account/orders",
            headers=self.headers,
            json=payload
        )
        return response.json()

# 使用示例
client = KIMIClient("http://localhost:8899", "your_api_key")

# 创建策略
result = client.create_strategy(
    "创建一个均线金叉策略，MA5上穿MA20时买入，跌破MA10时卖出"
)
strategy_id = result["data"]["strategy_id"]

# 运行回测
backtest = client.run_backtest(strategy_id, {
    "symbols": ["EURUSD"],
    "timeframe": "H1",
    "start_date": "2025-01-01",
    "end_date": "2026-01-01"
})
backtest_id = backtest["data"]["backtest_id"]

# 获取结果
results = client.get_backtest_results(backtest_id)
print(f"Sharpe Ratio: {results['data']['metrics']['sharpe_ratio']}")
```

### 6.2 JavaScript SDK

```javascript
class KIMIClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    };
  }

  async createStrategy(description) {
    const response = await fetch(`${this.baseUrl}/api/v1/strategies/nl-create`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ description })
    });
    return response.json();
  }

  async getMarketResonance(symbol) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/market/resonance?symbol=${symbol}`,
      { headers: this.headers }
    );
    return response.json();
  }

  connectWebSocket(onMessage) {
    const ws = new WebSocket(`ws://localhost:8899/ws?token=${this.apiKey}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };
    return ws;
  }
}
```

---

## 七、附录

### 7.1 接口变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| V1.0 | 2026-06-06 | 初始版本，包含REST API、WebSocket、ZeroMQ、MCP四大接口体系 |

### 7.2 参考文档

- Vibe-Trading API文档: https://github.com/HKUDS/Vibe-Trading
- TradingAgents通信协议: https://github.com/TauricResearch/TradingAgents
- MCP协议规范: https://modelcontextprotocol.io

### 7.3 测试环境

```
Base URL: http://localhost:8899/api/v1
WebSocket: ws://localhost:8899/ws
ZeroMQ PUB: tcp://localhost:5555
ZeroMQ REQ: tcp://localhost:5556
MCP Server: stdio (vibe-trading-mcp)
```
