# MiniMax AI量化平台 — 安全与风控机制

> 版本: v1.0 (minmax标识)  
> 日期: 2026-06-06  
> 状态: 正式版

---

## 1. 安全架构

### 1.1 整体安全框架

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MiniMax 安全架构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                       应用安全层                                      │  │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐         │  │
│   │  │ 认证鉴权  │  │ 访问控制  │  │ 输入验证  │  │ CSRF防护  │         │  │
│   │  └───────────┘  └───────────┘  └───────────┘  └───────────┘         │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│   ┌────────────────────────────────▼────────────────────────────────────┐  │
│   │                       业务风控层                                      │  │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐         │  │
│   │  │ 资金管理  │  │ 仓位控制  │  │ 限额管理  │  │ 熔断机制  │         │  │
│   │  └───────────┘  └───────────┘  └───────────┘  └───────────┘         │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│   ┌────────────────────────────────▼────────────────────────────────────┐  │
│   │                       数据安全层                                      │  │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐         │  │
│   │  │ 传输加密  │  │ 存储加密  │  │ 审计日志  │  │ 备份恢复  │         │  │
│   │  └───────────┘  └───────────┘  └───────────┘  └───────────┘         │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│   ┌────────────────────────────────▼────────────────────────────────────┐  │
│   │                       基础设施安全                                    │  │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐         │  │
│   │  │ 网络隔离  │  │ 容器安全  │  │ 密钥管理  │  │ 入侵检测  │         │  │
│   │  └───────────┘  └───────────┘  └───────────┘  └───────────┘         │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 认证与授权

### 2.1 认证机制

```python
# mini_max/auth/jwt.py

class JWTAuth:
    """JWT认证"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        self.algorithm = "HS256"
        self.access_token_expire = 3600  # 1小时
        self.refresh_token_expire = 604800  # 7天
    
    def create_access_token(self, user_id: str, role: str) -> str:
        """创建访问令牌"""
        payload = {
            "sub": user_id,
            "role": role,
            "type": "access",
            "exp": datetime.utcnow() + timedelta(seconds=self.access_token_expire),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthError("Token已过期")
        except jwt.InvalidTokenError:
            raise AuthError("Token无效")
```

### 2.2 角色权限

| 角色 | 权限 | 说明 |
|------|------|------|
| **admin** | 全部权限 | 系统管理员 |
| **user** | 标准权限 | 普通用户 |
| **researcher** | 回测+分析 | 研究员 |
| **trader** | 模拟盘交易 | 模拟交易 |
| **guest** | 只读 | 访客 |

### 2.3 权限矩阵

| 操作 | admin | user | researcher | trader | guest |
|------|-------|------|------------|--------|-------|
| 创建策略 | ✓ | ✓ | ✓ | ✗ | ✗ |
| 执行回测 | ✓ | ✓ | ✓ | ✗ | ✗ |
| 部署模拟盘 | ✓ | ✓ | ✗ | ✓ | ✗ |
| 部署实盘 | ✓ | ✓ | ✗ | ✗ | ✗ |
| 查看分析 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 管理用户 | ✓ | ✗ | ✗ | ✗ | ✗ |

---

## 3. 资金风险管理

### 3.1 风控规则体系

```python
# mini_max/risk/rules.py

class RiskRuleEngine:
    """风控规则引擎"""
    
    def __init__(self):
        self.rules = [
            # 资金类规则
            MaxPositionSizeRule(max_pct=0.1),      # 单笔最大仓位10%
            MaxTotalExposureRule(max_pct=0.5),    # 总暴露50%
            MaxLossPerDayRule(max_pct=0.05),      # 单日最大亏损5%
            MaxLossTotalRule(max_pct=0.15),       # 总最大亏损15%
            
            # 仓位类规则
            MinAccountBalanceRule(min_balance=1000),  # 最小账户余额
            MaxOpenPositionsRule(max_positions=5),    # 最大持仓数
            MaxCorrelatedPositionsRule(max=2),         # 相关品种最大持仓
            
            # 频率类规则
            MaxTradesPerMinuteRule(max=3),             # 每分钟最大交易数
            MaxTradesPerDayRule(max=50),               # 每日最大交易数
            
            # 时间类规则
            NoTradingBeforeNewsRule(),                 # 新闻发布前禁交易
            NoTradingAfterHoursRule(),                 # 休市后禁交易
        ]
    
    async def check(self, order: Order, context: RiskContext) -> RiskResult:
        """检查订单风险"""
        violations = []
        
        for rule in self.rules:
            result = await rule.check(order, context)
            if not result.passed:
                violations.append(RuleViolation(
                    rule=rule.name,
                    message=result.message,
                    severity=result.severity
                ))
        
        return RiskResult(
            approved=len(violations) == 0,
            violations=violations
        )
```

### 3.2 风控规则详细

| 规则ID | 规则名称 | 参数 | 默认值 | 说明 |
|--------|----------|------|--------|------|
| R001 | 单笔最大仓位 | max_pct | 10% | 单笔交易不超过账户10% |
| R002 | 总暴露上限 | max_pct | 50% | 所有持仓不超过50% |
| R003 | 单日亏损限制 | max_pct | 5% | 单日亏损超5%停止交易 |
| R004 | 总亏损限制 | max_pct | 15% | 总亏损超15%停止所有交易 |
| R005 | 最小账户余额 | min_balance | $1000 | 余额低于此值禁止开仓 |
| R006 | 最大持仓数 | max_positions | 5 | 同时持仓最多5个 |
| R007 | 相关品种限制 | max_correlated | 2 | 相关品种最多2个 |
| R008 | 每分钟交易限制 | max_per_min | 3 | 每分钟最多3笔交易 |
| R009 | 每日交易限制 | max_per_day | 50 | 每日最多50笔交易 |
| R010 | 新闻过滤 | - | - | 新闻发布前30分钟禁交易 |

### 3.3 风险评分

```python
def calculate_risk_score(order: Order, context: RiskContext) -> float:
    """
    计算订单风险评分 (0-100)
    0 = 无风险, 100 = 极高风险
    """
    score = 0
    
    # 仓位风险 (0-30分)
    position_pct = order.volume / context.account_balance
    if position_pct > 0.1:
        score += 30
    elif position_pct > 0.05:
        score += 20
    elif position_pct > 0.02:
        score += 10
    
    # 相关性风险 (0-20分)
    correlation = context.get_correlation(order.symbol)
    if correlation > 0.8:
        score += 20
    elif correlation > 0.5:
        score += 10
    
    # 时间风险 (0-20分)
    if context.is_high_volatility:
        score += 10
    if context.near_news_time:
        score += 10
    
    # 历史风险 (0-30分)
    recent_losses = context.get_recent_losses(days=7)
    if recent_losses > 5:
        score += 30
    elif recent_losses > 3:
        score += 20
    elif recent_losses > 1:
        score += 10
    
    return min(score, 100)
```

---

## 4. 交易限额控制

### 4.1 账户级别限额

```sql
-- 账户限额表
CREATE TABLE account_limits (
    user_id UUID PRIMARY KEY REFERENCES users(user_id),
    
    -- 资金限额
    max_account_pct_per_trade DECIMAL(5, 4) DEFAULT 0.10,   -- 单笔最大比例
    max_total_exposure_pct DECIMAL(5, 4) DEFAULT 0.50,     -- 总暴露上限
    max_daily_loss_pct DECIMAL(5, 4) DEFAULT 0.05,         -- 单日亏损限制
    max_total_loss_pct DECIMAL(5, 4) DEFAULT 0.15,         -- 总亏损限制
    min_balance DECIMAL(12, 4) DEFAULT 1000,               -- 最小余额
    
    -- 交易限额
    max_positions INTEGER DEFAULT 5,                       -- 最大持仓数
    max_trades_per_day INTEGER DEFAULT 50,                  -- 每日最大交易
    max_trades_per_minute INTEGER DEFAULT 3,                 -- 每分钟最大交易
    
    -- 品种限额
    max_single_symbol_exposure_pct DECIMAL(5, 4) DEFAULT 0.30,  -- 单品种最大暴露
    
    -- 风控阈值
    risk_score_threshold INTEGER DEFAULT 70,                -- 风险评分阈值
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 品种级别限额

```sql
-- 品种限额表
CREATE TABLE symbol_limits (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    
    -- 交易时段
    trading_hours JSONB,  -- {"start": "09:00", "end": "17:00", "timezone": "UTC+8"}
    
    -- 限额
    max_lot_size DECIMAL(10, 4),     -- 最大手数
    min_lot_size DECIMAL(10, 4),     -- 最小手数
    max_slippage_points INTEGER,      -- 最大滑点
    
    -- 保证金要求
    margin_requirement_pct DECIMAL(5, 4) DEFAULT 0.01,
    
    -- 状态
    enabled BOOLEAN DEFAULT true,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 示例数据
INSERT INTO symbol_limits (symbol, max_lot_size, min_lot_size) VALUES
('XAUUSD', 50, 0.01),
('EURUSD', 100, 0.01),
('GER40', 20, 0.1),
('US30', 10, 0.1);
```

---

## 5. 异常交易监控

### 5.1 异常检测规则

```python
# mini_max/risk/anomaly_detection.py

class AnomalyDetector:
    """异常交易检测"""
    
    ANOMALY_RULES = {
        # 频率异常
        "high_frequency": {
            "condition": "trades_last_5min > 10",
            "severity": "critical",
            "action": "pause_trading"
        },
        
        # 亏损异常
        "excessive_loss": {
            "condition": "daily_loss_pct > max_daily_loss_pct * 0.8",
            "severity": "warning",
            "action": "reduce_position"
        },
        
        # 仓位异常
        "position_limit_breach": {
            "condition": "position_size > max_position_size * 1.1",
            "severity": "critical",
            "action": "close_position"
        },
        
        # 延迟异常
        "high_latency": {
            "condition": "execution_latency_ms > 5000",
            "severity": "warning",
            "action": "alert"
        },
        
        # 滑点异常
        "excessive_slippage": {
            "condition": "slippage_pct > 0.005",  # 0.5%
            "severity": "warning",
            "action": "review_orders"
        }
    }
    
    def check(self, context: TradingContext) -> List[AnomalyAlert]:
        """检测异常"""
        alerts = []
        
        for rule_name, rule_config in self.ANOMALY_RULES.items():
            if self._evaluate_condition(rule_config["condition"], context):
                alerts.append(AnomalyAlert(
                    rule=rule_name,
                    severity=rule_config["severity"],
                    action=rule_config["action"],
                    context=context
                ))
        
        return alerts
```

### 5.2 异常类型与响应

| 异常类型 | 严重性 | 自动响应 | 人工响应 |
|----------|--------|----------|----------|
| 高频交易 | 严重 | 暂停交易 | 审查策略 |
| 亏损超限 | 严重 | 暂停交易 | 联系用户 |
| 仓位超限 | 严重 | 平仓 | 审查策略 |
| 延迟过高 | 警告 | 降速 | 监控 |
| 滑点过大 | 警告 | 审查订单 | 调整参数 |
| 连胜后大量亏损 | 警告 | 降低仓位 | 分析原因 |

---

## 6. 熔断机制

### 6.1 熔断规则

```python
# mini_max/risk/circuit_breaker.py

class CircuitBreaker:
    """熔断器"""
    
    def __init__(self):
        self.states = {}  # user_id -> state
        self.config = {
            # 亏损熔断
            "loss_streak": {
                "threshold": 5,           # 5次连续亏损
                "cooldown_minutes": 30,    # 冷却30分钟
                "action": "pause_and_review"
            },
            
            # 回撤熔断
            "drawdown": {
                "threshold": 0.08,         # 8%回撤
                "cooldown_minutes": 60,     # 冷却1小时
                "action": "reduce_and_alert"
            },
            
            # 胜率熔断
            "win_rate": {
                "threshold": 0.35,          # 胜率低于35%
                "window_trades": 20,       # 最近20笔
                "cooldown_minutes": 120,    # 冷却2小时
                "action": "pause_strategy"
            },
            
            # 延迟熔断
            "latency": {
                "threshold_ms": 10000,      # 10秒延迟
                "consecutive": 3,           # 连续3次
                "cooldown_minutes": 5,
                "action": "retry_with_backup"
            }
        }
    
    async def check(self, user_id: str, context: TradingContext) -> CircuitBreakerResult:
        """检查是否触发熔断"""
        state = self.states.get(user_id, CircuitBreakerState())
        
        # 检查冷却期
        if state.in_cooldown:
            return CircuitBreakerResult(
                triggered=False,
                in_cooldown=True,
                remaining_minutes=state.remaining_cooldown()
            )
        
        # 检查各项规则
        for rule_name, config in self.config.items():
            if self._check_rule(rule_name, config, context):
                self._trigger_circuit_breaker(user_id, rule_name, config)
                return CircuitBreakerResult(
                    triggered=True,
                    rule=rule_name,
                    action=config["action"],
                    cooldown_minutes=config["cooldown_minutes"]
                )
        
        return CircuitBreakerResult(triggered=False)
```

### 6.2 熔断恢复流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         熔断恢复流程                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [熔断触发] ──→ [暂停交易] ──→ [冷却期] ──→ [恢复检查] ──→ [恢复/继续]  │
│      │             │             │             │              │        │
│      ▼             ▼             ▼             ▼              ▼        │
│  记录日志      取消待执行     倒计时30分钟    验证条件        重启交易  │
│  发送告警      保留持仓       监控数据        人工确认        或维持    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. 系统安全防护

### 7.1 输入验证

```python
# mini_max/security/input_validation.py

class InputValidator:
    """输入验证器"""
    
    # 策略代码安全检查
    DANGEROUS_PATTERNS = [
        r"import\s+os",           # 文件操作
        r"import\s+subprocess",    # 系统命令
        r"import\s+socket",        # 网络连接
        r"eval\s*\(",              # 代码执行
        r"exec\s*\(",              # 代码执行
        r"open\s*\(",               # 文件操作
        r"os\.system",             # 系统命令
        r"subprocess\.",           # 子进程
        r"requests\.get",          # HTTP请求
        r"urllib\.",               # 网络请求
    ]
    
    def validate_strategy_code(self, code: str) -> ValidationResult:
        """验证策略代码安全性"""
        violations = []
        
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                violations.append(f"禁止的模式: {pattern}")
        
        # 检查代码长度
        if len(code) > 10000:
            violations.append("代码长度超过限制")
        
        return ValidationResult(
            valid=len(violations) == 0,
            violations=violations
        )
    
    def validate_order_params(self, order: OrderRequest) -> ValidationResult:
        """验证订单参数"""
        errors = []
        
        # 数量验证
        if order.volume <= 0:
            errors.append("订单数量必须大于0")
        if order.volume > MAX_LOT_SIZE.get(order.symbol, 100):
            errors.append(f"订单数量超过限制: {MAX_LOT_SIZE.get(order.symbol, 100)}")
        
        # 价格验证
        if order.price <= 0:
            errors.append("价格必须大于0")
        
        # 止损止盈验证
        if order.sl and order.sl <= 0:
            errors.append("止损必须大于0")
        if order.tp and order.tp <= 0:
            errors.append("止盈必须大于0")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
```

### 7.2 SQL注入防护

```python
# 使用参数化查询
def get_strategy(user_id: str, strategy_id: str):
    # ❌ 错误: 字符串拼接
    # query = f"SELECT * FROM strategies WHERE user_id = '{user_id}'"
    
    # ✅ 正确: 参数化查询
    query = """
        SELECT * FROM strategies 
        WHERE user_id = $1 AND strategy_id = $2
    """
    return db.execute(query, [user_id, strategy_id])
```

### 7.3 API限流

```python
# mini_max/security/rate_limiter.py

class RateLimiter:
    """API限流器"""
    
    LIMITS = {
        "/strategy/generate": (10, 60),    # 10次/分钟
        "/backtest/run": (5, 60),         # 5次/分钟
        "/market/state": (100, 60),       # 100次/分钟
        "/deployment": (10, 60),           # 10次/分钟
    }
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def check(self, user_id: str, endpoint: str) -> bool:
        """检查限流"""
        limit, window = self.LIMITS.get(endpoint, (1000, 60))
        key = f"ratelimit:{user_id}:{endpoint}"
        
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, window)
        
        return current <= limit
```

---

## 8. 审计日志

### 8.1 日志记录规范

```sql
-- 审计日志表
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 审计信息
    user_id UUID,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    
    -- 请求信息
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(100),
    
    -- 变更详情
    old_value JSONB,
    new_value JSONB,
    
    -- 结果
    result VARCHAR(20),  -- success/failure
    error_message TEXT,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
```

### 8.2 审计事件类型

| 事件类型 | 说明 | 记录内容 |
|----------|------|----------|
| AUTH_LOGIN | 登录 | 用户ID、IP、结果 |
| AUTH_LOGOUT | 登出 | 用户ID、会话时长 |
| STRATEGY_CREATE | 创建策略 | 策略ID、模板 |
| STRATEGY_UPDATE | 更新策略 | 策略ID、变更 |
| BACKTEST_RUN | 执行回测 | 回测ID、配置 |
| DEPLOYMENT_START | 开始部署 | 部署ID、策略 |
| DEPLOYMENT_STOP | 停止部署 | 部署ID、时长 |
| ORDER_PLACED | 下单 | 订单详情 |
| ORDER_CANCELLED | 取消订单 | 订单ID |
| RISK_BLOCKED | 风控拦截 | 订单、风控规则 |
| SETTINGS_CHANGE | 设置变更 | 变更内容 |

---

## 9. 紧急止损机制

### 9.1 紧急止损流程

```python
# mini_max/risk/emergency_stop.py

class EmergencyStop:
    """紧急止损"""
    
    TRIGGERS = {
        # 账户级
        "account_loss_exceed": 0.20,      # 账户亏损超20%
        "balance_below": 500,             # 余额低于500
        
        # 市场级
        "market_gap_exceed": 0.05,        # 跳空超5%
        "extreme_volatility": True,       # 极端波动
        
        # 系统级
        "mt5_disconnected": True,          # MT5断开
        "execution_failure_streak": 5,    # 连续执行失败
    }
    
    async def execute(self, reason: str):
        """执行紧急止损"""
        logger.critical(f"紧急止损触发: {reason}")
        
        # 1. 取消所有待执行订单
        pending_orders = await self.mt5.get_pending_orders()
        for order in pending_orders:
            await self.mt5.cancel_order(order.ticket)
        
        # 2. 平仓所有持仓
        positions = await self.mt5.get_positions()
        for pos in positions:
            await self.mt5.close_position(pos.ticket)
        
        # 3. 发送告警
        await self.notifier.send_emergency_alert(
            title="紧急止损触发",
            message=f"原因: {reason}\n"
                   f"时间: {datetime.now()}\n"
                   f"持仓: {len(positions)}\n"
                   f"待执行: {len(pending_orders)}"
        )
        
        # 4. 暂停所有策略
        await self.deployment_manager.pause_all()
        
        # 5. 记录日志
        await self.audit_log.record(
            action="EMERGENCY_STOP",
            details={"reason": reason, "positions_closed": len(positions)}
        )
```

### 9.2 紧急联系人

```sql
-- 紧急联系人表
CREATE TABLE emergency_contacts (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    name VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(255),
    role VARCHAR(20),  -- primary/secondary
    priority INTEGER DEFAULT 1,
    enabled BOOLEAN DEFAULT true
);
```

---

## 10. 安全运维

### 10.1 密钥管理

```bash
# 使用环境变量或密钥管理服务
export MT5_PASSWORD="encrypted_password"
export DB_PASSWORD="encrypted_password"
export JWT_SECRET="random_256_bit_key"

# 或使用 AWS Secrets Manager / HashiCorp Vault
```

### 10.2 定期安全检查

| 检查项 | 频率 | 负责人 |
|--------|------|--------|
| 漏洞扫描 | 每周 | 安全团队 |
| 渗透测试 | 季度 | 外部团队 |
| 日志审计 | 每日 | 风控团队 |
| 备份验证 | 每周 | 运维团队 |
| 密钥轮换 | 季度 | 安全团队 |
| 权限审计 | 每月 | 合规团队 |

---

## 11. 合规性

### 11.1 数据保护

| 合规要求 | 实现方式 |
|----------|----------|
| GDPR | 数据加密、访问控制、删除权 |
| 数据加密 | AES-256传输和存储 |
| 访问日志 | 完整审计日志 |
| 数据保留 | 按法规保留，超期删除 |

### 11.2 交易合规

| 合规项 | 实现方式 |
|--------|----------|
| 最佳执行 | 订单路由优化 |
| 交易记录 | 完整交易日志 |
| 风险披露 | 用户协议和风险提示 |