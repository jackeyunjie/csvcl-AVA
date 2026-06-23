# Qoder AI量化多周期交易平台 - 安全和风控机制

**版本**: V1.0  
**日期**: 2026-06-06  
**文档编号**: QODER-SR-001  

---

## 一、安全架构概述

### 1.1 安全设计原则

| 原则 | 说明 |
|------|------|
| **纵深防御** | 多层安全防护，单点失效不导致整体崩溃 |
| **最小权限** | 每个组件、每个用户只拥有必要的最小权限 |
| **零信任** | 默认不信任任何请求，所有操作需验证 |
| **审计追踪** | 所有敏感操作完整记录，支持事后追溯 |
| **故障安全** | 系统故障时默认进入安全状态（停止交易） |

### 1.2 安全架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                    安全防护层次                               │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: 应用安全                                           │
│  • API认证授权 • 输入验证 • SQL注入防护 • XSS防护            │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: 交易安全                                           │
│  • 指令签名 • 双因素认证 • 交易限额 • 异常检测               │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 资金安全                                           │
│  • 仓位限制 • 回撤控制 • 保证金监控 • 强制平仓               │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 通信安全                                           │
│  • TLS加密 • API密钥管理 • IP白名单 • 请求限流               │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: 系统安全                                           │
│  • 访问控制 • 日志审计 • 数据备份 • 灾难恢复                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、认证与授权

### 2.1 用户认证

**JWT Token认证**:
```python
# Token结构
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_001",           # 用户ID
    "username": "trader001",
    "role": "trader",            # admin/trader/viewer
    "permissions": ["read", "trade"],
    "iat": 1717672200,           # 签发时间
    "exp": 1717675800,           # 过期时间（1小时）
    "jti": "token_uuid"          # Token唯一标识
  },
  "signature": "..."
}
```

**认证流程**:
1. 用户提交用户名密码
2. 服务端验证密码（bcrypt哈希）
3. 生成Access Token（1小时有效期）和Refresh Token（7天有效期）
4. 客户端存储Token
5. 每次请求携带Access Token
6. Access Token过期后使用Refresh Token刷新

### 2.2 API Key认证

**使用场景**: 程序化交易、第三方集成

**设计**:
```sql
-- API密钥表结构
CREATE TABLE api_keys (
    key_id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,       -- 存储哈希值，不存储明文
    key_prefix VARCHAR(8),                 -- 前缀用于识别
    permissions JSON,                      -- ["read", "trade", "admin"]
    ip_whitelist JSON,                     -- ["192.168.1.1", "10.0.0.0/8"]
    rate_limit INTEGER DEFAULT 100,        -- 每分钟请求数
    daily_trade_limit DECIMAL(18, 4),      -- 日交易限额
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**安全要求**:
- API Key只显示一次（创建时），之后不可查看明文
- 支持IP白名单限制
- 支持权限细分（只读/交易/管理）
- 支持过期时间设置
- 支持随时撤销

### 2.3 角色权限控制

| 角色 | 权限 |
|------|------|
| **管理员** | 全部权限（用户管理、系统配置、交易、查看） |
| **交易员** | 策略管理、回测、交易执行、查看 |
| **观察员** | 只读权限（查看行情、报告、状态） |
| **Agent** | 根据Agent类型分配特定权限 |

---

## 三、交易风控体系

### 3.1 风控架构

```
┌─────────────────────────────────────────────────────────────┐
│                      风控决策流程                             │
│                                                              │
│  交易请求 → 前置检查 → 风险评估 → 决策 → 执行/拒绝            │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 前置检查     │  │ 风险评估     │  │ 决策引擎             │  │
│  │             │  │             │  │                     │  │
│  │ • 参数校验   │  │ • 账户风险   │  │ • 规则匹配           │  │
│  │ • 权限检查   │  │ • 品种风险   │  │ • 评分模型           │  │
│  │ • 时间检查   │  │ • 组合风险   │  │ • 人工复核(大额)      │  │
│  │ • 状态检查   │  │ • 市场风险   │  │ • 自动通过/拒绝       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 账户级风控

#### 3.2.1 日亏损限额

```python
class DailyLossLimit:
    """日亏损限额控制"""
    
    def __init__(self, limit: float = -1000.0):
        self.limit = limit
        self.daily_pnl: Dict[str, float] = {}  # date -> pnl
    
    def check(self, account_id: str, proposed_order: Dict) -> RiskCheckResult:
        today = datetime.now().date().isoformat()
        current_pnl = self.daily_pnl.get(today, 0)
        
        # 估算订单潜在亏损
        estimated_risk = self._estimate_order_risk(proposed_order)
        projected_pnl = current_pnl - estimated_risk
        
        if projected_pnl < self.limit:
            return RiskCheckResult(
                approved=False,
                reason=f"日亏损限额触发: 当前{current_pnl}, 预计{projected_pnl}, 限额{self.limit}",
                suggested_action="暂停交易"
            )
        
        return RiskCheckResult(approved=True)
    
    def update_pnl(self, account_id: str, pnl: float):
        """更新日盈亏"""
        today = datetime.now().date().isoformat()
        self.daily_pnl[today] = self.daily_pnl.get(today, 0) + pnl
```

#### 3.2.2 最大回撤控制

```python
class MaxDrawdownControl:
    """最大回撤控制"""
    
    def __init__(self, max_drawdown_pct: float = 0.20):
        self.max_drawdown = max_drawdown_pct
        self.peak_equity: Dict[str, float] = {}
        self.current_equity: Dict[str, float] = {}
    
    def check(self, account_id: str) -> RiskCheckResult:
        peak = self.peak_equity.get(account_id, 0)
        current = self.current_equity.get(account_id, 0)
        
        if peak > 0:
            drawdown = (peak - current) / peak
            
            if drawdown >= self.max_drawdown:
                return RiskCheckResult(
                    approved=False,
                    reason=f"最大回撤触发: 当前回撤{drawdown:.2%}, 限额{self.max_drawdown:.2%}",
                    suggested_action="强制平仓并锁定账户"
                )
            elif drawdown >= self.max_drawdown * 0.8:
                # 预警：达到80%限额
                return RiskCheckResult(
                    approved=True,
                    warning=f"回撤预警: 当前回撤{drawdown:.2%}, 接近限额{self.max_drawdown:.2%}",
                    suggested_action="减仓或暂停新开仓"
                )
        
        return RiskCheckResult(approved=True)
    
    def update_equity(self, account_id: str, equity: float):
        """更新权益"""
        self.current_equity[account_id] = equity
        
        # 更新峰值
        if equity > self.peak_equity.get(account_id, 0):
            self.peak_equity[account_id] = equity
```

#### 3.2.3 保证金监控

```python
class MarginMonitor:
    """保证金监控"""
    
    def __init__(self):
        self.warning_level = 0.50    # 50%预警
        self.critical_level = 0.30   # 30%强制减仓
        self.liquidation_level = 0.20  # 20%强制平仓
    
    def check(self, account_info: Dict) -> RiskCheckResult:
        margin_level = account_info.get("margin_level", 100)
        
        if margin_level <= self.liquidation_level * 100:
            return RiskCheckResult(
                approved=False,
                reason=f"保证金不足: 当前{margin_level:.1f}%, 强制平仓线{self.liquidation_level*100:.0f}%",
                suggested_action="强制平仓所有持仓"
            )
        elif margin_level <= self.critical_level * 100:
            return RiskCheckResult(
                approved=False,
                reason=f"保证金临界: 当前{margin_level:.1f}%, 减仓线{self.critical_level*100:.0f}%",
                suggested_action="减仓50%"
            )
        elif margin_level <= self.warning_level * 100:
            return RiskCheckResult(
                approved=True,
                warning=f"保证金预警: 当前{margin_level:.1f}%, 预警线{self.warning_level*100:.0f}%",
                suggested_action="关注风险，准备减仓"
            )
        
        return RiskCheckResult(approved=True)
```

### 3.3 品种级风控

#### 3.3.1 单一品种持仓限制

```python
class PositionLimit:
    """单一品种持仓限制"""
    
    def __init__(self, max_position_size: float = 10.0):
        self.max_position = max_position_size
    
    def check(self, symbol: str, current_position: float, 
              proposed_volume: float, direction: str) -> RiskCheckResult:
        # 计算新持仓
        if direction == "BUY":
            new_position = current_position + proposed_volume
        else:
            new_position = current_position - proposed_volume
        
        if abs(new_position) > self.max_position:
            return RiskCheckResult(
                approved=False,
                reason=f"品种持仓超限: {symbol} 当前{current_position}, 拟{new_position}, 限额±{self.max_position}",
                suggested_volume=self.max_position - abs(current_position)
            )
        
        return RiskCheckResult(approved=True)
```

#### 3.3.2 品种波动率限制

```python
class VolatilityLimit:
    """波动率限制 - 高波动时限制交易"""
    
    def __init__(self, max_volatility: float = 0.05):
        self.max_volatility = max_volatility
    
    def check(self, symbol: str, current_volatility: float) -> RiskCheckResult:
        if current_volatility > self.max_volatility:
            return RiskCheckResult(
                approved=False,
                reason=f"波动率过高: {symbol} 当前{current_volatility:.2%}, 限额{self.max_volatility:.2%}",
                suggested_action="暂停该品种交易"
            )
        
        return RiskCheckResult(approved=True)
```

### 3.4 组合级风控

#### 3.4.1 相关性风险

```python
class CorrelationRisk:
    """相关性风险控制"""
    
    def __init__(self, max_correlation: float = 0.80):
        self.max_correlation = max_correlation
    
    def check(self, new_position: Dict, current_positions: List[Dict]) -> RiskCheckResult:
        new_symbol = new_position["symbol"]
        
        for pos in current_positions:
            corr = self._get_correlation(new_symbol, pos["symbol"])
            
            if corr > self.max_correlation:
                # 同向持仓时检查
                if new_position["direction"] == pos["direction"]:
                    return RiskCheckResult(
                        approved=False,
                        reason=f"相关性风险: {new_symbol}与{pos['symbol']}相关性{corr:.2f}, 超过限额{self.max_correlation}",
                        suggested_action="选择低相关性品种或反向对冲"
                    )
        
        return RiskCheckResult(approved=True)
    
    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """获取品种相关性（从历史数据计算）"""
        # 实际实现中查询历史收益率相关性
        return 0.5  # 示例
```

#### 3.4.2 总敞口限制

```python
class TotalExposureLimit:
    """总敞口限制"""
    
    def __init__(self, max_total_exposure: float = 50.0):
        self.max_exposure = max_total_exposure
    
    def check(self, current_positions: List[Dict], proposed_order: Dict) -> RiskCheckResult:
        # 计算当前总敞口
        current_exposure = sum(abs(p["volume"]) for p in current_positions)
        
        # 加上新订单
        new_exposure = current_exposure + proposed_order["volume"]
        
        if new_exposure > self.max_exposure:
            return RiskCheckResult(
                approved=False,
                reason=f"总敞口超限: 当前{current_exposure}, 拟{new_exposure}, 限额{self.max_exposure}",
                suggested_volume=self.max_exposure - current_exposure
            )
        
        return RiskCheckResult(approved=True)
```

### 3.5 策略级风控

#### 3.5.1 策略衰减检测

```python
class StrategyDecayDetector:
    """策略衰减检测"""
    
    def __init__(self, lookback_window: int = 30):
        self.window = lookback_window
        self.sharpe_threshold = 0.5  # 夏普比率低于此值认为衰减
    
    def check(self, strategy_id: str, recent_performance: List[Dict]) -> RiskCheckResult:
        if len(recent_performance) < self.window:
            return RiskCheckResult(approved=True)
        
        # 计算近期夏普比率
        recent_sharpe = self._calculate_sharpe(recent_performance[-self.window:])
        
        # 计算历史夏普比率
        historical_sharpe = self._calculate_sharpe(recent_performance)
        
        if recent_sharpe < self.sharpe_threshold:
            return RiskCheckResult(
                approved=False,
                reason=f"策略衰减: 近期夏普{recent_sharpe:.2f}, 历史夏普{historical_sharpe:.2f}, 阈值{self.sharpe_threshold}",
                suggested_action="暂停策略，进行重新优化"
            )
        elif recent_sharpe < historical_sharpe * 0.5:
            return RiskCheckResult(
                approved=True,
                warning=f"策略表现下降: 近期夏普{recent_sharpe:.2f}, 历史夏普{historical_sharpe:.2f}",
                suggested_action="关注策略表现，准备优化"
            )
        
        return RiskCheckResult(approved=True)
```

#### 3.5.2 信号质量监控

```python
class SignalQualityMonitor:
    """信号质量监控"""
    
    def __init__(self):
        self.min_win_rate = 0.45
        self.min_signals_per_month = 10
    
    def check(self, agent_id: str, signals: List[Dict]) -> RiskCheckResult:
        if len(signals) < self.min_signals_per_month:
            return RiskCheckResult(approved=True)
        
        win_rate = sum(1 for s in signals if s.get("outcome") == "win") / len(signals)
        
        if win_rate < self.min_win_rate:
            return RiskCheckResult(
                approved=False,
                reason=f"信号质量低: {agent_id} 胜率{win_rate:.1%}, 最低要求{self.min_win_rate:.0%}",
                suggested_action="暂停Agent，检查逻辑"
            )
        
        return RiskCheckResult(approved=True)
```

---

## 四、异常交易监控

### 4.1 异常检测规则

| 异常类型 | 检测规则 | 响应措施 |
|----------|----------|----------|
| **价格异常** | 价格跳空超过3倍ATR | 暂停交易，人工确认 |
| **成交量异常** | 成交量超过均值10倍 | 记录日志，降低仓位 |
| **频率异常** | 1分钟内超过10笔订单 | 限制下单频率 |
| **滑点异常** | 实际滑点超过预期3倍 | 检查流动性，调整策略 |
| **盈亏异常** | 单笔盈亏超过账户5% | 检查订单参数 |
| **时间异常** | 非交易时段下单 | 拒绝订单 |
| **重复异常** | 相同订单重复提交 | 去重处理 |

### 4.2 异常检测实现

```python
class AnomalyDetector:
    """异常交易检测器"""
    
    def __init__(self):
        self.rules: List[AnomalyRule] = []
        self._init_rules()
    
    def _init_rules(self):
        """初始化检测规则"""
        self.rules = [
            PriceGapRule(max_gap_atr_multiple=3),
            VolumeSpikeRule(max_volume_multiple=10),
            FrequencyRule(max_orders_per_minute=10),
            SlippageRule(max_slippage_multiple=3),
            PnLSpikeRule(max_pnl_pct=0.05),
            TradingHoursRule()
        ]
    
    def check(self, order: Dict, market_data: Dict, account_info: Dict) -> List[AnomalyAlert]:
        """检查异常"""
        alerts = []
        
        for rule in self.rules:
            alert = rule.check(order, market_data, account_info)
            if alert:
                alerts.append(alert)
        
        return alerts


class PriceGapRule:
    """价格跳空检测"""
    
    def __init__(self, max_gap_atr_multiple: float = 3.0):
        self.max_gap = max_gap_atr_multiple
    
    def check(self, order: Dict, market_data: Dict, account_info: Dict) -> Optional[AnomalyAlert]:
        current_price = market_data.get("close", 0)
        previous_price = market_data.get("previous_close", 0)
        atr = market_data.get("atr", 0)
        
        if atr > 0 and previous_price > 0:
            gap = abs(current_price - previous_price) / atr
            
            if gap > self.max_gap:
                return AnomalyAlert(
                    level="critical",
                    type="price_gap",
                    message=f"价格跳空异常: 跳空{gap:.1f}倍ATR, 超过限额{self.max_gap}",
                    suggested_action="暂停交易，人工确认"
                )
        
        return None
```

---

## 五、系统安全防护

### 5.1 API安全

#### 5.1.1 请求限流

```python
class RateLimiter:
    """请求限流器"""
    
    def __init__(self):
        # 基于Redis的滑动窗口限流
        self.limits = {
            "default": {"requests": 100, "window": 60},      # 100请求/分钟
            "backtest": {"requests": 10, "window": 60},       # 10次回测/分钟
            "trade": {"requests": 30, "window": 60},          # 30次交易/分钟
            "agent_control": {"requests": 20, "window": 60}   # 20次控制/分钟
        }
    
    def is_allowed(self, api_key: str, endpoint: str) -> bool:
        """检查是否允许请求"""
        limit = self.limits.get(endpoint, self.limits["default"])
        
        # Redis滑动窗口计数
        key = f"rate_limit:{api_key}:{endpoint}"
        current = redis.get(key) or 0
        
        if int(current) >= limit["requests"]:
            return False
        
        redis.incr(key)
        redis.expire(key, limit["window"])
        
        return True
```

#### 5.1.2 输入验证

```python
from pydantic import BaseModel, validator

class OrderRequest(BaseModel):
    """订单请求验证"""
    symbol: str
    direction: str
    volume: float
    order_type: str = "MARKET"
    sl: Optional[float] = None
    tp: Optional[float] = None
    
    @validator('symbol')
    def validate_symbol(cls, v):
        allowed = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US30", "GER40"]
        if v not in allowed:
            raise ValueError(f"不支持的品种: {v}")
        return v
    
    @validator('direction')
    def validate_direction(cls, v):
        if v not in ["BUY", "SELL"]:
            raise ValueError("方向必须是BUY或SELL")
        return v
    
    @validator('volume')
    def validate_volume(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("交易量必须在0-100之间")
        return round(v, 2)
    
    @validator('sl', 'tp')
    def validate_prices(cls, v, values):
        if v is not None and v <= 0:
            raise ValueError("价格必须大于0")
        return v
```

### 5.2 数据安全

#### 5.2.1 敏感数据加密

```python
from cryptography.fernet import Fernet

class SensitiveDataEncryptor:
    """敏感数据加密"""
    
    def __init__(self, master_key: str):
        self.cipher = Fernet(master_key.encode())
    
    def encrypt(self, data: str) -> str:
        """加密数据"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted: str) -> str:
        """解密数据"""
        return self.cipher.decrypt(encrypted.encode()).decode()
    
    def hash_api_key(self, api_key: str) -> str:
        """API Key哈希（不可逆）"""
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()
```

#### 5.2.2 数据备份

| 数据类型 | 备份频率 | 保留周期 | 存储位置 |
|----------|----------|----------|----------|
| 数据库 | 每日 | 30天 | 本地 + 云存储 |
| 交易记录 | 实时 | 永久 | 本地 + 云存储 |
| 配置文件 | 变更时 | 10个版本 | Git仓库 |
| 日志文件 | 每日 | 7天 | 本地 |

### 5.3 网络安全

#### 5.3.1 ZeroMQ安全

```python
class SecureZMQBridge:
    """安全ZeroMQ桥接"""
    
    def __init__(self):
        self.context = zmq.Context()
        
        # 使用Curve加密
        self.server_public, self.server_secret = zmq.curve_keypair()
        
    def create_secure_socket(self, socket_type: int):
        """创建加密Socket"""
        socket = self.context.socket(socket_type)
        
        # 启用Curve加密
        socket.curve_server = True
        socket.curve_secretkey = self.server_secret
        socket.curve_publickey = self.server_public
        
        return socket
```

#### 5.3.2 IP白名单

```python
class IPWhitelist:
    """IP白名单"""
    
    def __init__(self, allowed_ips: List[str]):
        self.allowed = set(allowed_ips)
    
    def is_allowed(self, ip: str) -> bool:
        """检查IP是否允许"""
        return ip in self.allowed
    
    def add_ip(self, ip: str):
        """添加IP"""
        self.allowed.add(ip)
    
    def remove_ip(self, ip: str):
        """移除IP"""
        self.allowed.discard(ip)
```

---

## 六、审计与合规

### 6.1 审计日志

```sql
-- 审计日志表
CREATE TABLE audit_logs (
    audit_id BIGINT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 操作信息
    action VARCHAR(50) NOT NULL,           -- CREATE/UPDATE/DELETE/EXECUTE/LOGIN
    resource_type VARCHAR(50),             -- strategy/backtest/order/account
    resource_id VARCHAR(32),
    
    -- 用户信息
    user_id VARCHAR(32),
    api_key_id VARCHAR(32),
    ip_address VARCHAR(50),
    user_agent VARCHAR(255),
    
    -- 操作详情
    request_payload JSON,
    response_status VARCHAR(20),
    
    -- 变更前后（用于UPDATE）
    before_state JSON,
    after_state JSON,
    
    -- 结果
    success BOOLEAN,
    error_message TEXT
);

CREATE INDEX idx_audit_time ON audit_logs(timestamp);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
```

### 6.2 审计事件类型

| 事件类型 | 记录内容 | 保留期限 |
|----------|----------|----------|
| 用户登录 | 时间、IP、结果 | 2年 |
| 策略创建/修改 | 完整代码变更 | 永久 |
| 回测执行 | 参数、结果 | 永久 |
| 交易执行 | 订单详情、执行结果 | 永久 |
| 风控触发 | 触发原因、处理结果 | 2年 |
| Agent操作 | 消息内容、状态变更 | 90天 |
| 配置变更 | 变更前后值 | 1年 |

---

## 七、灾难恢复

### 7.1 故障响应流程

```
故障检测 → 故障分级 → 应急响应 → 故障恢复 → 事后复盘
    ↓          ↓          ↓          ↓          ↓
  监控告警   P0/P1/P2   自动/人工   数据恢复   根因分析
```

### 7.2 故障分级

| 级别 | 定义 | 响应时间 | 处理措施 |
|------|------|----------|----------|
| **P0** | 系统完全不可用/资金风险 | 5分钟 | 立即停止交易，人工介入 |
| **P1** | 核心功能异常/数据丢失风险 | 15分钟 | 降级运行，紧急修复 |
| **P2** | 非核心功能异常 | 1小时 | 计划修复 |
| **P3** | 性能下降/轻微异常 | 4小时 | 排期优化 |

### 7.3 自动故障恢复

```python
class FaultRecovery:
    """故障恢复管理"""
    
    def __init__(self):
        self.recovery_strategies = {
            "mt5_disconnect": self._recover_mt5,
            "database_error": self._recover_database,
            "agent_crash": self._recover_agent,
            "memory_exhaustion": self._recover_memory
        }
    
    def handle_fault(self, fault_type: str, context: Dict):
        """处理故障"""
        strategy = self.recovery_strategies.get(fault_type)
        
        if strategy:
            return strategy(context)
        
        # 默认：进入安全模式
        return self._enter_safe_mode(context)
    
    def _recover_mt5(self, context: Dict) -> RecoveryResult:
        """恢复MT5连接"""
        # 1. 停止新订单发送
        # 2. 尝试重连（指数退避）
        # 3. 重连成功后恢复交易
        # 4. 超过最大重试次数则告警
        pass
    
    def _enter_safe_mode(self, context: Dict) -> RecoveryResult:
        """进入安全模式"""
        # 1. 暂停所有Agent
        # 2. 取消所有待处理订单
        # 3. 发送紧急告警
        # 4. 等待人工介入
        pass
```

---

## 八、附录

### 8.1 安全配置清单

```yaml
# security_config.yaml

authentication:
  jwt_secret: "${JWT_SECRET}"           # 环境变量注入
  token_expiry: 3600                     # 1小时
  refresh_token_expiry: 604800           # 7天
  password_min_length: 8
  require_2fa_for_admin: true

api_security:
  rate_limit_default: 100                # 请求/分钟
  rate_limit_backtest: 10
  rate_limit_trade: 30
  require_ip_whitelist: false
  max_request_size: 10485760             # 10MB

trading_security:
  max_position_per_symbol: 10.0
  max_total_exposure: 50.0
  max_daily_loss: -1000.0
  max_drawdown: 0.20
  margin_warning: 0.50
  margin_critical: 0.30
  margin_liquidation: 0.20
  max_slippage_points: 10
  max_order_size: 100.0
  trading_hours:
    start: "00:00"
    end: "23:59"

risk_management:
  strategy_decay_lookback: 30
  strategy_decay_sharpe_threshold: 0.5
  min_signal_win_rate: 0.45
  min_signals_per_month: 10
  volatility_limit: 0.05
  max_correlation: 0.80

system_security:
  enable_audit_log: true
  audit_log_retention_days: 730
  database_backup_frequency: "daily"
  database_backup_retention: 30
  log_level: "INFO"
  enable_ip_whitelist: false
```

### 8.2 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-06 | 初始版本 | Qoder AI |
