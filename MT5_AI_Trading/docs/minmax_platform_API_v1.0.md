# MiniMax AI量化平台 — API接口规范

> 版本: v1.0 (minmax标识)  
> 日期: 2026-06-06  
> 状态: 正式版

---

## 1. API概述

### 1.1 基本信息

| 项目 | 说明 |
|------|------|
| Base URL | `http://localhost:8000/api/v1` |
| 协议 | HTTP/REST + WebSocket |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |
| 认证方式 | API Key |

### 1.2 通用响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "uuid",
  "timestamp": "2026-06-06T15:30:00Z"
}
```

**错误码定义**:
| code | 说明 |
|------|------|
| 0 | 成功 |
| 1000 | 参数错误 |
| 2000 | 认证失败 |
| 3000 | 资源不存在 |
| 4000 | 业务逻辑错误 |
| 5000 | 服务器内部错误 |

### 1.3 认证

```http
Authorization: Bearer <api_key>
```

---

## 2. 策略生成API

### 2.1 自然语言生成策略

**端点**: `POST /strategy/generate`

**请求**:
```json
{
  "natural_language": "MA5上穿MA20时买入，跌破MA10时卖出",
  "symbol": "XAUUSD",
  "timeframe": "H1",
  "context": {
    "risk_tolerance": "medium",
    "capital": 10000
  }
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "strategy_id": "strat_abc123",
    "name": "均线金叉策略_v1",
    "template_id": "ma_crossover",
    "code": "class MaCrossStrategy(Strategy):\n    ...",
    "params": {
      "fast_ma": 5,
      "slow_ma": 20,
      "exit_ma": 10
    },
    "confidence": 0.92,
    "backtest_config": {
      "start_date": "2020-01-01",
      "end_date": "2026-06-06",
      "symbols": ["XAUUSD"],
      "timeframes": ["H1"]
    }
  }
}
```

### 2.2 获取策略模板列表

**端点**: `GET /strategy/templates`

**响应**:
```json
{
  "code": 0,
  "data": {
    "templates": [
      {
        "id": "ma_crossover",
        "name": "均线交叉策略",
        "description": "快慢均线交叉产生信号",
        "params": ["fast_ma", "slow_ma", "exit_ma"],
        "min_samples": 30
      },
      {
        "id": "squeeze_breakout",
        "name": "收缩突破策略",
        "description": "布林带收缩后突破信号",
        "params": ["timeframe", "direction", "hold_bars"],
        "min_samples": 50
      }
    ]
  }
}
```

### 2.3 验证策略代码

**端点**: `POST /strategy/validate`

**请求**:
```json
{
  "code": "class CustomStrategy(Strategy):\n    def on_bar(self, bar):\n        ..."
}
```

**响应**:
```json
{
  "code": 0,
  "data": {
    "valid": true,
    "syntax_errors": [],
    "warnings": ["未设置止损"],
    "estimated_execution_time_ms": 150
  }
}
```

---

## 3. 回测API

### 3.1 执行回测

**端点**: `POST /backtest/run`

**请求**:
```json
{
  "strategy_id": "strat_abc123",
  "config": {
    "symbols": ["XAUUSD", "EURUSD"],
    "timeframes": ["H1", "M15"],
    "start_date": "2020-01-01",
    "end_date": "2026-06-06",
    "initial_capital": 10000,
    "commission": 0.0002,
    "spread_multiplier": 1.2,
    "walk_forward": {
      "train_pct": 0.6,
      "val_pct": 0.2,
      "test_pct": 0.2,
      "rolling": true
    }
  }
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "backtest_id": "bt_xyz789",
    "status": "completed",
    "elapsed_ms": 28500,
    "report": {
      "summary": {
        "total_return": 1.273,
        "annual_return": 0.185,
        "sharpe_ratio": 1.82,
        "max_drawdown": -0.123,
        "win_rate": 0.625,
        "profit_factor": 1.85,
        "total_trades": 847,
        "avg_trade_return": 0.0015
      },
      "walk_forward": {
        "train": {
          "period": "2020-2022",
          "expectancy": 0.0028,
          "sample_count": 423
        },
        "val": {
          "period": "2023-2024",
          "expectancy": 0.0025,
          "sample_count": 212
        },
        "test": {
          "period": "2025-2026",
          "expectancy": 0.0031,
          "sample_count": 212
        }
      },
      "risk_analysis": [
        {
          "event": "2020-03 新冠",
          "max_drawdown": -0.182,
          "recovery_days": 45
        }
      ],
      "optimization_suggestions": [
        "建议增加非农数据日历过滤",
        "建议在W1趋势向上时启用本策略"
      ]
    }
  }
}
```

### 3.2 获取回测结果

**端点**: `GET /backtest/{backtest_id}`

### 3.3 导出回测报告

**端点**: `GET /backtest/{backtest_id}/export`

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| format | string | pdf/html/json/sqx |

---

## 4. 市场分析API

### 4.1 获取市场状态

**端点**: `GET /market/state`

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 品种，如XAUUSD |
| timeframe | string | 否 | 周期，默认H1 |

**响应**:
```json
{
  "code": 0,
  "data": {
    "symbol": "XAUUSD",
    "timestamp": "2026-06-06T15:30:00Z",
    "timeframes": {
      "MN1": {"state_hex": "8", "contraction_pct": 15},
      "W1": {"state_hex": "6", "contraction_pct": 72},
      "D1": {"state_hex": "0", "contraction_pct": 89},
      "H4": {"state_hex": "8", "contraction_pct": 12},
      "H1": {"state_hex": "4", "contraction_pct": 45},
      "M15": {"state_hex": "C", "contraction_pct": 78}
    },
    "resonance": {
      "d1_h4_combo": "0_8",
      "resonance_score": 0.72,
      "direction": "long"
    }
  }
}
```

### 4.2 收缩突破追踪

**端点**: `GET /market/squeeze-process`

**响应**:
```json
{
  "code": 0,
  "data": {
    "symbol": "XAUUSD",
    "current_stage": "squeeze",
    "squeeze_duration_bars": 12,
    "breakout_probability": 0.78,
    "history": [
      {"timestamp": "2026-06-05T22:00", "stage": "normal", "indicator": 0.85},
      {"timestamp": "2026-06-06T02:00", "stage": "building", "indicator": 0.62},
      {"timestamp": "2026-06-06T06:00", "stage": "squeeze", "indicator": 0.18},
      {"timestamp": "2026-06-06T10:00", "stage": "squeeze", "indicator": 0.12}
    ]
  }
}
```

### 4.3 实时行情

**端点**: `WebSocket /market/realtime`

**订阅消息**:
```json
{
  "action": "subscribe",
  "symbols": ["XAUUSD", "EURUSD"]
}
```

**推送消息**:
```json
{
  "type": "tick",
  "symbol": "XAUUSD",
  "bid": 2315.50,
  "ask": 2316.00,
  "timestamp": "2026-06-06T15:30:00.123Z"
}
```

---

## 5. Agent API

### 5.1 获取Agent列表

**端点**: `GET /agents`

**响应**:
```json
{
  "code": 0,
  "data": {
    "agents": [
      {
        "id": "h1_squeeze",
        "name": "H1收缩Agent",
        "type": "research",
        "status": "active",
        "last_run": "2026-06-06T15:25:00Z"
      },
      {
        "id": "execution",
        "name": "执行Agent",
        "type": "execution",
        "status": "active",
        "last_run": "2026-06-06T15:29:55Z"
      },
      {
        "id": "risk",
        "name": "风控Agent",
        "type": "risk",
        "status": "active",
        "last_run": "2026-06-06T15:30:00Z"
      }
    ]
  }
}
```

### 5.2 触发Agent分析

**端点**: `POST /agents/{agent_id}/analyze`

**请求**:
```json
{
  "symbol": "XAUUSD",
  "timeframe": "H1",
  "options": {}
}
```

**响应**:
```json
{
  "code": 0,
  "data": {
    "task_id": "task_abc123",
    "status": "queued",
    "estimated_completion_ms": 5000
  }
}
```

### 5.3 获取Agent结果

**端点**: `GET /agents/tasks/{task_id}`

**响应**:
```json
{
  "code": 0,
  "data": {
    "task_id": "task_abc123",
    "status": "completed",
    "result": {
      "agent_id": "h1_squeeze",
      "signal_strength": 0.85,
      "confidence": 0.92,
      "analysis": "...",
      "recommendation": "推荐做多",
      "details": {...}
    }
  }
}
```

---

## 6. 部署API

### 6.1 部署到模拟盘

**端点**: `POST /deployment/simulation`

**请求**:
```json
{
  "strategy_id": "strat_abc123",
  "symbol": "XAUUSD",
  "lot_size": 0.1,
  "risk_per_trade": 0.02
}
```

**响应**:
```json
{
  "code": 0,
  "data": {
    "deployment_id": "dep_xyz789",
    "status": "deployed",
    "mt5_ticket": 12345678,
    "started_at": "2026-06-06T15:30:00Z"
  }
}
```

### 6.2 获取部署状态

**端点**: `GET /deployment/{deployment_id}`

**响应**:
```json
{
  "code": 0,
  "data": {
    "deployment_id": "dep_xyz789",
    "status": "active",
    "strategy_id": "strat_abc123",
    "symbol": "XAUUSD",
    "current_position": {
      "direction": "long",
      "volume": 0.1,
      "entry_price": 2315.50,
      "unrealized_pnl": 15.50,
      "unrealized_pnl_pct": 0.67
    },
    "backtest_deviation": 0.03,
    "started_at": "2026-06-06T15:30:00Z"
  }
}
```

### 6.3 停止部署

**端点**: `DELETE /deployment/{deployment_id}`

---

## 7. 复现检测API

### 7.1 触发复现检测

**端点**: `POST /reification/check`

**请求**:
```json
{
  "symbol": "XAUUSD",
  "timeframe": "M15",
  "current_profile": {
    "contraction_pct": 33,
    "max_daily_pct": 85,
    "std_daily_pct": 40,
    "max_contraction_streak": 20
  }
}
```

**响应**:
```json
{
  "code": 0,
  "data": {
    "matches": [
      {
        "session_id": 1,
        "signature_id": 5,
        "match_score": 95.3,
        "threshold": 80.0,
        "reference_date": "2026-06-04",
        "reference_return": 0.0285,
        "details": {
          "contraction_pct": 95.1,
          "max_daily": 98.2,
          "std_daily": 88.5,
          "symbol_match": 100.0
        }
      }
    ],
    "alert_triggered": true,
    "alert_type": "reification_80"
  }
}
```

### 7.2 获取历史关键观察

**端点**: `GET /reification/sessions`

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| start_date | string | 开始日期 |
| end_date | string | 结束日期 |
| symbol | string | 品种过滤 |

---

## 8. ZeroMQ内部接口

### 8.1 MT5 Bridge端口映射

| 端口 | 用途 | 协议 | 说明 |
|------|------|------|------|
| 5565 | 实时行情订阅 | PUB/SUB | Tick数据推送 |
| 5566 | 交易指令请求 | REQ/REP | 订单执行 |
| 5567 | 历史数据请求 | REQ/REP | K线数据 |
| 5568 | 实时点差 | PUB/SUB | 点差推送 |

### 8.2 消息格式

**Tick消息**:
```json
{
  "type": "tick",
  "symbol": "XAUUSD",
  "bid": 2315.50,
  "ask": 2316.00,
  "last": 2315.75,
  "volume": 100,
  "time_msc": 1717687800123
}
```

**订单请求**:
```json
{
  "type": "order_request",
  "action": "buy",
  "symbol": "XAUUSD",
  "volume": 0.1,
  "price": 2315.50,
  "sl": 2310.00,
  "tp": 2330.00,
  "comment": "MiniMax Strategy"
}
```

**订单结果**:
```json
{
  "type": "order_result",
  "success": true,
  "ticket": 12345678,
  "price": 2315.50,
  "sl": 2310.00,
  "tp": 2330.00,
  "error": null
}
```

---

## 9. WebSocket API

### 9.1 连接

```
ws://localhost:8000/ws?api_key=xxx
```

### 9.2 订阅主题

```json
{
  "action": "subscribe",
  "topics": ["market:XAUUSD", "signals:all", "deployments:active"]
}
```

### 9.3 推送事件

```json
{
  "topic": "signals:XAUUSD",
  "event": "squeeze_breakout",
  "data": {
    "symbol": "XAUUSD",
    "timeframe": "H1",
    "signal_strength": 0.85,
    "timestamp": "2026-06-06T15:30:00Z"
  }
}
```

---

## 10. 错误码详细

| code | 说明 | 解决方案 |
|------|------|----------|
| 1001 | 缺少必填参数 | 检查请求参数 |
| 1002 | 参数格式错误 | 参照API文档 |
| 1003 | 参数值越界 | 调整参数范围 |
| 2001 | API Key无效 | 检查API Key |
| 2002 | API Key已过期 | 续费或重新申请 |
| 3001 | 策略不存在 | 检查策略ID |
| 3002 | 回测不存在 | 检查回测ID |
| 4001 | 余额不足 | 充值或减少使用 |
| 4002 | 风控拦截 | 检查风控规则 |
| 4003 | 市场关闭 | 等待市场开放 |
| 5001 | 服务器繁忙 | 重试请求 |
| 5002 | 外部服务错误 | 联系技术支持 |

---

## 11. 限流规则

| 接口 | 限制 | 窗口 |
|------|------|------|
| `/strategy/generate` | 10次 | 每分钟 |
| `/backtest/run` | 5次 | 每分钟 |
| `/market/state` | 100次 | 每分钟 |
| WebSocket | 1000条 | 每分钟 |