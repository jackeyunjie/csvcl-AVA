# Qoder AI量化多周期交易平台 - API接口规范

**版本**: V1.0  
**日期**: 2026-06-06  
**文档编号**: QODER-API-001  
**协议**: HTTP/REST + WebSocket  
**数据格式**: JSON  

---

## 一、接口概述

### 1.1 基础信息

| 项目 | 说明 |
|------|------|
| 基础URL | `http://localhost:8000/api/v1` |
| 认证方式 | JWT Bearer Token / API Key |
| 请求格式 | `Content-Type: application/json` |
| 响应格式 | `Content-Type: application/json` |
| 字符编码 | UTF-8 |

### 1.2 通用响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": "2026-06-06T10:30:00Z",
  "request_id": "req_abc123"
}
```

### 1.3 错误码定义

| 错误码 | 说明 | HTTP状态码 |
|--------|------|-----------|
| 200 | 成功 | 200 |
| 400 | 请求参数错误 | 400 |
| 401 | 未授权 | 401 |
| 403 | 禁止访问 | 403 |
| 404 | 资源不存在 | 404 |
| 429 | 请求过于频繁 | 429 |
| 500 | 服务器内部错误 | 500 |
| 1001 | 策略验证失败 | 400 |
| 1002 | 回测执行失败 | 500 |
| 1003 | Agent未找到 | 404 |
| 1004 | MT5连接断开 | 503 |
| 1005 | 风控限制触发 | 403 |

---

## 二、认证接口

### 2.1 用户登录

```
POST /auth/login
```

**请求参数**:
```json
{
  "username": "trader001",
  "password": "encrypted_password"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600,
    "token_type": "Bearer"
  }
}
```

### 2.2 API Key认证

所有API请求需在Header中携带:
```
Authorization: Bearer {access_token}
```
或
```
X-API-Key: {api_key}
```

---

## 三、策略管理接口

### 3.1 自然语言创建策略

```
POST /strategies/nl-create
```

**请求参数**:
```json
{
  "description": "创建一个均线金叉策略，MA5上穿MA20时买入，跌破MA10时卖出",
  "symbol": "EURUSD",
  "timeframe": "H1",
  "target_formats": ["python", "mql5"],
  "risk_params": {
    "stop_loss_pct": 0.02,
    "take_profit_pct": 0.04,
    "max_position_size": 5.0
  }
}
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "strategy_id": "str_abc123",
    "intent": {
      "strategy_type": "trend_following",
      "entry_conditions": [
        {
          "indicator": "MA",
          "condition": "CROSS_UP",
          "params": {"fast": 5, "slow": 20}
        }
      ],
      "exit_conditions": [
        {
          "indicator": "MA",
          "condition": "CROSS_DOWN",
          "params": {"fast": "close", "slow": 10}
        }
      ]
    },
    "generated_code": {
      "python": "import pandas as pd...",
      "mql5": "//+------------------------------------------------------------------+..."
    },
    "validation": {
      "is_valid": true,
      "warnings": [],
      "suggestions": ["建议添加成交量确认条件"]
    },
    "estimated_complexity": "medium"
  }
}
```

### 3.2 获取策略列表

```
GET /strategies?page=1&page_size=20&category=trend_following
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "total": 156,
    "page": 1,
    "page_size": 20,
    "strategies": [
      {
        "strategy_id": "str_abc123",
        "name": "MA金叉趋势策略",
        "type": "trend_following",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "status": "active",
        "created_at": "2026-06-01T10:00:00Z",
        "updated_at": "2026-06-05T15:30:00Z",
        "backtest_count": 12,
        "best_sharpe": 1.85
      }
    ]
  }
}
```

### 3.3 获取策略详情

```
GET /strategies/{strategy_id}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "strategy_id": "str_abc123",
    "name": "MA金叉趋势策略",
    "description": "基于MA5/MA20金叉死叉的趋势跟踪策略",
    "type": "trend_following",
    "symbol": "EURUSD",
    "timeframe": "H1",
    "code": {
      "python": "...",
      "mql5": "..."
    },
    "parameters": {
      "ma_fast": {"default": 5, "min": 2, "max": 50, "type": "int"},
      "ma_slow": {"default": 20, "min": 10, "max": 200, "type": "int"}
    },
    "risk_params": {
      "stop_loss_pct": 0.02,
      "take_profit_pct": 0.04
    },
    "backtest_history": [
      {
        "backtest_id": "bt_xyz789",
        "date": "2026-06-05",
        "sharpe_ratio": 1.85,
        "total_return": 25.3,
        "max_drawdown": -8.2
      }
    ]
  }
}
```

### 3.4 更新策略

```
PUT /strategies/{strategy_id}
```

**请求**:
```json
{
  "code": {
    "python": "updated code..."
  },
  "parameters": {
    "ma_fast": 10,
    "ma_slow": 30
  }
}
```

### 3.5 删除策略

```
DELETE /strategies/{strategy_id}
```

### 3.6 验证策略

```
POST /strategies/{strategy_id}/validate
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "is_valid": true,
    "syntax_check": {"passed": true, "errors": []},
    "logic_check": {"passed": true, "warnings": ["建议添加止损逻辑"]},
    "performance_check": {"passed": true, "notes": ["检测到循环计算，建议向量化"]},
    "risk_check": {"passed": true, "warnings": []}
  }
}
```

---

## 四、回测接口

### 4.1 创建回测任务

```
POST /backtests
```

**请求参数**:
```json
{
  "strategy_id": "str_abc123",
  "symbol": "EURUSD",
  "timeframe": "H1",
  "start_date": "2023-01-01",
  "end_date": "2025-12-31",
  "initial_balance": 10000,
  "leverage": 1,
  "slippage": {
    "model": "fixed",
    "points": 2
  },
  "commission": {
    "model": "fixed_per_lot",
    "per_lot": 7
  },
  "parameters": {
    "ma_fast": 5,
    "ma_slow": 20
  },
  "use_multi_timeframe": true,
  "timeframes": ["H1", "H4", "D1"]
}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "backtest_id": "bt_xyz789",
    "status": "queued",
    "estimated_duration": 15,
    "queue_position": 1,
    "created_at": "2026-06-06T10:30:00Z"
  }
}
```

### 4.2 查询回测状态

```
GET /backtests/{backtest_id}/status
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "backtest_id": "bt_xyz789",
    "status": "running",
    "progress": 65,
    "current_phase": "calculating_metrics",
    "elapsed_time": 12,
    "estimated_remaining": 6
  }
}
```

### 4.3 获取回测结果

```
GET /backtests/{backtest_id}/results
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "backtest_id": "bt_xyz789",
    "status": "completed",
    "metrics": {
      "total_return": 25.3,
      "annual_return": 12.1,
      "volatility": 15.2,
      "sharpe_ratio": 1.85,
      "sortino_ratio": 2.34,
      "max_drawdown": -8.2,
      "calmar_ratio": 1.47,
      "total_trades": 156,
      "win_rate": 58.3,
      "avg_profit": 125.5,
      "avg_loss": -89.2,
      "profit_factor": 1.92,
      "avg_holding_bars": 24
    },
    "trades": [
      {
        "entry_time": "2023-02-15T10:00:00Z",
        "exit_time": "2023-02-18T14:00:00Z",
        "direction": "LONG",
        "entry_price": 1.0850,
        "exit_price": 1.0920,
        "volume": 1.0,
        "pnl": 70.0,
        "pnl_pct": 0.65,
        "holding_bars": 78,
        "exit_reason": "signal"
      }
    ],
    "equity_curve": [
      {"time": "2023-01-01", "equity": 10000},
      {"time": "2023-01-02", "equity": 10050}
    ],
    "monthly_returns": {
      "2023-01": 2.5,
      "2023-02": -1.2
    },
    "drawdown_series": [
      {"time": "2023-01-01", "drawdown": 0},
      {"time": "2023-02-15", "drawdown": -3.2}
    ],
    "trade_distribution": {
      "by_hour": {"10": 15, "14": 23},
      "by_day_of_week": {"Mon": 12, "Tue": 15},
      "by_exit_reason": {"tp": 45, "sl": 32, "signal": 79}
    }
  }
}
```

### 4.4 获取回测报告

```
GET /backtests/{backtest_id}/report?format=html
```

**响应**: 返回HTML/PDF报告文件

### 4.5 参数优化

```
POST /backtests/{backtest_id}/optimize
```

**请求**:
```json
{
  "method": "grid_search",
  "objective": "sharpe_ratio",
  "param_grid": {
    "ma_fast": [5, 10, 15],
    "ma_slow": [20, 30, 50]
  },
  "constraints": {
    "max_drawdown": 0.15,
    "min_trades": 30
  }
}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "optimization_id": "opt_123",
    "best_params": {
      "ma_fast": 10,
      "ma_slow": 30
    },
    "best_sharpe": 2.15,
    "total_combinations": 9,
    "results": [
      {
        "params": {"ma_fast": 5, "ma_slow": 20},
        "sharpe_ratio": 1.85,
        "max_drawdown": -8.2
      }
    ],
    "param_heatmap": {
      "param1": "ma_fast",
      "param2": "ma_slow",
      "data": {
        "5": {"20": 1.85, "30": 1.92, "50": 1.78},
        "10": {"20": 1.95, "30": 2.15, "50": 1.88},
        "15": {"20": 1.72, "30": 1.89, "50": 1.65}
      }
    }
  }
}
```

### 4.6 多策略对比

```
POST /backtests/compare
```

**请求**:
```json
{
  "backtest_ids": ["bt_001", "bt_002", "bt_003"],
  "metrics": ["sharpe_ratio", "total_return", "max_drawdown"]
}
```

---

## 五、Agent管理接口

### 5.1 获取Agent列表

```
GET /agents
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "agents": [
      {
        "agent_id": "research_technical_001",
        "agent_type": "research_technical",
        "status": "running",
        "current_task": "analyzing EURUSD",
        "last_activity": "2026-06-06T10:29:55Z",
        "metrics": {
          "signals_generated": 156,
          "avg_confidence": 0.72
        }
      },
      {
        "agent_id": "trader_001",
        "agent_type": "trader",
        "status": "idle",
        "current_task": null,
        "last_activity": "2026-06-06T10:25:30Z",
        "metrics": {
          "orders_placed": 45,
          "win_rate": 62.5
        }
      },
      {
        "agent_id": "risk_001",
        "agent_type": "risk_management",
        "status": "running",
        "current_task": "monitoring exposure",
        "last_activity": "2026-06-06T10:30:00Z",
        "metrics": {
          "alerts_triggered": 3,
          "orders_blocked": 1
        }
      },
      {
        "agent_id": "observer_001",
        "agent_type": "observer",
        "status": "running",
        "current_task": "scanning contractions",
        "last_activity": "2026-06-06T10:30:00Z",
        "metrics": {
          "contractions_detected": 12,
          "breakouts_confirmed": 5,
          "trends_tracked": 8
        }
      }
    ]
  }
}
```

### 5.2 获取Agent详情

```
GET /agents/{agent_id}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "agent_id": "observer_001",
    "agent_type": "observer",
    "status": "running",
    "state": {
      "contraction_registry": {
        "EURUSD": {
          "contraction_score": 78,
          "duration_bars": 24,
          "upper_bound": 1.0950,
          "lower_bound": 1.0850
        }
      },
      "breakout_registry": {
        "GBPUSD": {
          "direction": "UP",
          "breakout_price": 1.2750,
          "target_price": 1.2910
        }
      }
    },
    "message_history": [
      {
        "msg_id": "msg_001",
        "from_agent": "observer_001",
        "to_agent": null,
        "msg_type": "CONTRACTION_ALERT",
        "timestamp": "2026-06-06T10:25:00Z",
        "payload": {"symbol": "EURUSD", "score": 78}
      }
    ],
    "performance": {
      "messages_processed": 1250,
      "avg_processing_time_ms": 15,
      "error_rate": 0.001
    }
  }
}
```

### 5.3 控制Agent

```
POST /agents/{agent_id}/control
```

**请求**:
```json
{
  "action": "pause"
}
```

**action可选值**: `start`, `pause`, `resume`, `stop`, `restart`

### 5.4 向Agent发送消息

```
POST /agents/{agent_id}/messages
```

**请求**:
```json
{
  "msg_type": "MARKET_DATA",
  "payload": {
    "symbol": "EURUSD",
    "price": 1.0850,
    "volume": 1250
  },
  "priority": "NORMAL"
}
```

### 5.5 获取Agent消息历史

```
GET /agents/{agent_id}/messages?limit=100&msg_type=SIGNAL
```

---

## 六、市场数据接口

### 6.1 获取实时行情

```
GET /market/quotes?symbols=EURUSD,GBPUSD,XAUUSD
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "quotes": [
      {
        "symbol": "EURUSD",
        "bid": 1.0845,
        "ask": 1.0847,
        "spread": 2,
        "timestamp": "2026-06-06T10:30:00.123Z",
        "change": 0.0012,
        "change_pct": 0.11
      }
    ]
  }
}
```

### 6.2 获取K线数据

```
GET /market/klines?symbol=EURUSD&timeframe=H1&start=2026-06-01&end=2026-06-06&limit=100
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "symbol": "EURUSD",
    "timeframe": "H1",
    "klines": [
      {
        "time": "2026-06-06T09:00:00Z",
        "open": 1.0840,
        "high": 1.0850,
        "low": 1.0835,
        "close": 1.0845,
        "volume": 1250
      }
    ]
  }
}
```

### 6.3 获取多周期共振状态

```
GET /market/resonance?symbol=EURUSD
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "symbol": "EURUSD",
    "timestamp": "2026-06-06T10:30:00Z",
    "state_hex": {
      "mn1": {"hex": "2", "state": "contraction_breakout", "duration": 5},
      "w1": {"hex": "A", "state": "bullish_trend", "duration": 12},
      "d1": {"hex": "A", "state": "bullish_trend", "duration": 8},
      "h4": {"hex": "3", "state": "bullish_start", "duration": 3},
      "h1": {"hex": "B", "state": "bullish_trend_expansion", "duration": 2}
    },
    "resonance": {
      "is_resonance": true,
      "type": "trend_resonance",
      "direction": "BULLISH",
      "strength": 0.85,
      "aligned_timeframes": ["W1", "D1", "H1"],
      "description": "W1/D1/H1同时处于bullish_trend状态，形成强趋势共振"
    },
    "contraction": {
      "is_contracting": false,
      "last_contraction": {
        "start": "2026-06-01T00:00:00Z",
        "end": "2026-06-05T00:00:00Z",
        "duration_bars": 96,
        "breakout_direction": "UP"
      }
    }
  }
}
```

### 6.4 获取收缩追踪列表

```
GET /market/contractions?status=active&min_score=60
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "contractions": [
      {
        "symbol": "EURUSD",
        "status": "active",
        "score": 78,
        "duration_bars": 24,
        "start_time": "2026-06-05T10:00:00Z",
        "upper_bound": 1.0950,
        "lower_bound": 1.0850,
        "indicators": {
          "bb_width": 0.15,
          "kaufman_width": 0.12,
          "atr_percentile": 18
        },
        "breakout_probability": {
          "up": 0.65,
          "down": 0.35
        },
        "estimated_target": {
          "up": 1.1050,
          "down": 1.0750
        }
      }
    ]
  }
}
```

### 6.5 获取品种状态卡片

```
GET /market/symbols/{symbol}/status
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "symbol": "EURUSD",
    "price": 1.0845,
    "change": 0.0012,
    "change_pct": 0.11,
    "volatility": 12.5,
    "state_hex_visual": {
      "mn1": {"hex": "2", "color": "#FF6B6B"},
      "w1": {"hex": "A", "color": "#4ECDC4"},
      "d1": {"hex": "A", "color": "#4ECDC4"},
      "h4": {"hex": "3", "color": "#45B7D1"},
      "h1": {"hex": "B", "color": "#96CEB4"}
    },
    "current_phase": "trend_following",
    "phase_since": "2026-06-05T14:00:00Z",
    "energy_label": "energy_supportive",
    "recent_signals": [
      {
        "time": "2026-06-06T09:00:00Z",
        "type": "BUY",
        "confidence": 0.85,
        "source": "multi_timeframe_resonance"
      }
    ],
    "performance_7d": {
      "signals": 5,
      "win_rate": 80,
      "avg_return": 0.45
    }
  }
}
```

### 6.6 获取行业轮动状态

```
GET /market/sector-rotation
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "sectors": [
      {
        "name": "forex_major",
        "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
        "avg_state_hex": "A",
        "trend_strength": 0.75,
        "momentum_score": 65,
        "rank": 1,
        "recommendation": "overweight"
      },
      {
        "name": "commodities",
        "symbols": ["XAUUSD", "XAGUSD"],
        "avg_state_hex": "8",
        "trend_strength": 0.45,
        "momentum_score": 42,
        "rank": 3,
        "recommendation": "neutral"
      }
    ],
    "rotation_signal": {
      "from": "commodities",
      "to": "forex_major",
      "strength": 0.68,
      "description": "资金从商品流向主要货币对"
    }
  }
}
```

---

## 七、交易接口

### 7.1 获取账户信息

```
GET /account/info
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "account_id": "ACC001",
    "balance": 15234.56,
    "equity": 15345.67,
    "margin": 1234.56,
    "free_margin": 14111.11,
    "margin_level": 1243.5,
    "currency": "USD",
    "leverage": 100
  }
}
```

### 7.2 获取持仓列表

```
GET /account/positions
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "positions": [
      {
        "ticket": "123456",
        "symbol": "EURUSD",
        "direction": "BUY",
        "volume": 1.0,
        "open_price": 1.0840,
        "current_price": 1.0845,
        "sl": 1.0800,
        "tp": 1.0900,
        "swap": -2.5,
        "commission": 7.0,
        "profit": 50.0,
        "profit_pct": 0.46,
        "open_time": "2026-06-06T08:00:00Z",
        "magic": 12345,
        "comment": "trend_resonance"
      }
    ]
  }
}
```

### 7.3 下单

```
POST /account/orders
```

**请求**:
```json
{
  "symbol": "EURUSD",
  "direction": "BUY",
  "volume": 1.0,
  "order_type": "MARKET",
  "sl": 1.0800,
  "tp": 1.0900,
  "magic": 12345,
  "comment": "multi_timeframe_resonance",
  "source": "trader_agent_001"
}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "order_id": "ord_abc123",
    "ticket": "123456",
    "status": "filled",
    "filled_price": 1.0845,
    "filled_volume": 1.0,
    "slippage": 0.5,
    "commission": 7.0,
    "execution_time": "2026-06-06T10:30:01.234Z"
  }
}
```

### 7.4 平仓

```
POST /account/positions/{ticket}/close
```

**请求**:
```json
{
  "volume": 1.0,
  "reason": "signal_reversal"
}
```

### 7.5 修改订单

```
PUT /account/orders/{ticket}
```

**请求**:
```json
{
  "sl": 1.0820,
  "tp": 1.0950
}
```

### 7.6 获取订单历史

```
GET /account/orders?start=2026-06-01&end=2026-06-06&status=filled
```

---

## 八、监控接口

### 8.1 获取系统状态

```
GET /system/status
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "status": "healthy",
    "uptime": 86400,
    "version": "1.0.0",
    "components": {
      "api_server": "running",
      "mt5_bridge": "connected",
      "database": "connected",
      "llm_gateway": "available"
    },
    "performance": {
      "cpu_percent": 25.5,
      "memory_percent": 45.2,
      "disk_percent": 62.1
    }
  }
}
```

### 8.2 获取实时日志

```
GET /system/logs?level=INFO&limit=100&agent_id=trader_001
```

### 8.3 WebSocket实时推送

**连接地址**: `ws://localhost:8000/ws`

**订阅消息**:
```json
{
  "action": "subscribe",
  "channels": ["quotes", "agent_status", "signals", "alerts"]
}
```

**推送数据示例**:
```json
// 行情推送
{
  "channel": "quotes",
  "data": {
    "symbol": "EURUSD",
    "bid": 1.0845,
    "ask": 1.0847,
    "timestamp": "2026-06-06T10:30:00.123Z"
  }
}

// Agent状态推送
{
  "channel": "agent_status",
  "data": {
    "agent_id": "observer_001",
    "status": "running",
    "current_task": "detected_breakout_EURUSD"
  }
}

// 信号推送
{
  "channel": "signals",
  "data": {
    "signal_id": "sig_001",
    "symbol": "EURUSD",
    "direction": "BUY",
    "confidence": 0.85,
    "source": "research_technical_001",
    "timestamp": "2026-06-06T10:30:00Z"
  }
}

// 告警推送
{
  "channel": "alerts",
  "data": {
    "alert_id": "alt_001",
    "level": "warning",
    "type": "high_volatility",
    "symbol": "XAUUSD",
    "message": "XAUUSD波动率超过阈值: 25%",
    "timestamp": "2026-06-06T10:30:00Z"
  }
}
```

---

## 九、ZeroMQ通信接口

### 9.1 MT5 → Python (PUB/SUB)

**端口**: 5555 (默认)

**消息格式**:
```json
{
  "type": "tick",
  "symbol": "EURUSD",
  "bid": 1.08450,
  "ask": 1.08470,
  "spread": 20,
  "time": "2026.06.06 10:30:00",
  "volume": 125
}
```

### 9.2 Python → MT5 (REQ/REP)

**端口**: 5556 (默认)

**请求格式**:
```json
{
  "action": "ORDER_SEND",
  "payload": {
    "symbol": "EURUSD",
    "cmd": "BUY",
    "volume": 1.0,
    "price": 0,
    "slippage": 10,
    "stoploss": 1.08000,
    "takeprofit": 1.09000,
    "magic": 12345,
    "comment": "qoder_agent_signal"
  }
}
```

**响应格式**:
```json
{
  "status": "success",
  "ticket": 123456,
  "open_price": 1.08450,
  "volume": 1.0,
  "error": null
}
```

### 9.3 心跳检测

**频率**: 每5秒

**心跳消息**:
```json
{
  "type": "heartbeat",
  "from": "python_bridge",
  "timestamp": "2026-06-06T10:30:00Z"
}
```

---

## 十、MCP工具接口

### 10.1 工具列表

| 工具名 | 描述 | 输入 | 输出 |
|--------|------|------|------|
| `analyze_market` | 市场分析 | symbol, timeframe | 分析报告 |
| `run_backtest` | 运行回测 | strategy_code, config | 回测结果 |
| `get_signal` | 获取信号 | symbol, filters | 信号列表 |
| `get_portfolio` | 组合查询 | - | 组合状态 |
| `place_order` | 下单 | order_params | 订单确认 |
| `get_state_hex` | 获取State Hex | symbol | 五元组状态 |
| `get_contractions` | 获取收缩列表 | filters | 收缩列表 |

### 10.2 MCP调用示例

```json
{
  "name": "analyze_market",
  "arguments": {
    "symbol": "EURUSD",
    "timeframe": "H1",
    "analysis_type": "multi_timeframe_resonance"
  }
}
```

---

## 十一、附录

### 11.1 接口版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| V1.0 | 2026-06-06 | 初始版本，包含策略、回测、Agent、市场数据、交易、监控接口 |

### 11.2 Postman集合

建议创建Postman集合进行接口测试，包含以下文件夹：
- 认证
- 策略管理
- 回测
- Agent管理
- 市场数据
- 交易
- 监控

### 11.3 SDK示例 (Python)

```python
import requests

class QoderClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def create_strategy(self, description: str) -> dict:
        resp = requests.post(
            f"{self.base_url}/strategies/nl-create",
            json={"description": description},
            headers=self.headers
        )
        return resp.json()
    
    def run_backtest(self, strategy_id: str, config: dict) -> dict:
        resp = requests.post(
            f"{self.base_url}/backtests",
            json={"strategy_id": strategy_id, **config},
            headers=self.headers
        )
        return resp.json()
    
    def get_market_status(self, symbol: str) -> dict:
        resp = requests.get(
            f"{self.base_url}/market/symbols/{symbol}/status",
            headers=self.headers
        )
        return resp.json()

# 使用示例
client = QoderClient("http://localhost:8000/api/v1", "your_api_key")
result = client.create_strategy("MA5上穿MA20买入策略")
print(result)
```

### 11.4 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-06 | 初始版本 | Qoder AI |
