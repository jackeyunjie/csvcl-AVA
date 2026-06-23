# KIMI AI量化多周期视角交易平台 - 安全和风控机制设计

**版本**: V1.0  
**日期**: 2026-06-06  
**文档编号**: KIMI-SEC-001  
**设计原则**: 基于GitHub前沿开源项目独立设计，参考Vibe-Trading的安全边界和TradingAgents的决策日志机制

---

## 一、安全架构概述

### 1.1 安全目标

| 目标 | 说明 | 优先级 |
|------|------|--------|
| 资金安全 | 防止非授权交易和资金损失 | P0 |
| 数据安全 | 保护策略代码和交易数据 | P0 |
| 系统安全 | 防止系统入侵和恶意操作 | P1 |
| 合规安全 | 满足审计和合规要求 | P1 |

### 1.2 安全架构分层

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           KIMI安全架构分层                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    应用安全层 (Application Security)                  │   │
│  │  • API认证与授权  • 输入验证  • 防注入攻击  • 会话管理               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    交易安全层 (Trading Security)                      │   │
│  │  • 交易限额控制  • 风控规则引擎  • 异常检测  • 紧急平仓               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    数据安全层 (Data Security)                         │   │
│  │  • 加密存储  • 访问控制  • 审计日志  • 数据备份                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    基础设施安全层 (Infrastructure Security)           │   │
│  │  • 网络安全  • 主机安全  • 容器安全  • 密钥管理                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、应用安全

### 2.1 认证与授权

#### 2.1.1 用户认证

| 认证方式 | 适用场景 | 实现 |
|----------|----------|------|
| JWT Token | Web/API访问 | HS256签名，1小时过期 |
| API Key | 程序化访问 | 前缀+哈希存储，支持限流 |
| 双因素认证 | 敏感操作 | TOTP (Google Authenticator) |

```python
class AuthManager:
    """认证管理器"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.token_expiry = 3600  # 1小时
    
    def generate_jwt(self, user_id: str, role: str) -> str:
        """生成JWT Token"""
        payload = {
            "user_id": user_id,
            "role": role,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=self.token_expiry)
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_jwt(self, token: str) -> dict:
        """验证JWT Token"""
        try:
            return jwt.decode(token, self.secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token已过期")
        except jwt.InvalidTokenError:
            raise AuthenticationError("无效的Token")
```

#### 2.1.2 权限控制

| 角色 | 权限范围 |
|------|----------|
| admin | 所有权限，包括用户管理、系统配置 |
| trader | 策略管理、回测、交易执行、查看持仓 |
| viewer | 只读访问，查看市场数据、回测结果 |
| api | 程序化访问，限于配置的API权限范围 |

```python
class PermissionManager:
    """权限管理器"""
    
    PERMISSIONS = {
        "admin": ["*"],
        "trader": [
            "strategy:*",
            "backtest:*",
            "agent:read",
            "market:read",
            "account:*",
            "report:read"
        ],
        "viewer": [
            "strategy:read",
            "backtest:read",
            "agent:read",
            "market:read",
            "report:read"
        ],
        "api": [
            "strategy:read",
            "backtest:read",
            "market:read"
        ]
    }
    
    def check_permission(self, user_role: str, resource: str, action: str) -> bool:
        """检查权限"""
        permissions = self.PERMISSIONS.get(user_role, [])
        required = f"{resource}:{action}"
        
        for perm in permissions:
            if perm == "*" or perm == required:
                return True
            if perm.endswith(":*") and required.startswith(perm[:-1]):
                return True
        
        return False
```

### 2.2 输入验证

#### 2.2.1 API输入验证

```python
from pydantic import BaseModel, Field, validator

class CreateStrategyRequest(BaseModel):
    """创建策略请求验证"""
    description: str = Field(..., min_length=10, max_length=1000)
    target_formats: List[str] = Field(default=["python"])
    risk_params: Optional[Dict] = None
    
    @validator('target_formats')
    def validate_formats(cls, v):
        allowed = ["python", "mql5", "pine_script", "tdx"]
        for fmt in v:
            if fmt not in allowed:
                raise ValueError(f"不支持的格式: {fmt}")
        return v
    
    @validator('risk_params')
    def validate_risk(cls, v):
        if v:
            if 'stop_loss_pips' in v and v['stop_loss_pips'] < 0:
                raise ValueError("止损点数不能为负")
            if 'max_position_size' in v and v['max_position_size'] <= 0:
                raise ValueError("最大持仓必须大于0")
        return v

class PlaceOrderRequest(BaseModel):
    """下单请求验证"""
    symbol: str = Field(..., regex=r'^[A-Z]{3,6}$')
    direction: str = Field(..., regex=r'^(BUY|SELL)$')
    size: float = Field(..., gt=0, le=100)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    @validator('stop_loss', 'take_profit')
    def validate_prices(cls, v, values):
        if v is not None and v <= 0:
            raise ValueError("价格必须大于0")
        return v
```

#### 2.2.2 代码注入防护

| 防护措施 | 说明 |
|----------|------|
| AST解析 | 策略代码提交前进行语法树分析 |
| 黑名单 | 禁止导入os, sys, subprocess等危险模块 |
| 沙箱执行 | 回测代码在受限环境中执行 |
| 超时控制 | 策略执行超时自动终止 |

```python
class CodeSecurityChecker:
    """代码安全检查器"""
    
    FORBIDDEN_MODULES = {'os', 'sys', 'subprocess', 'importlib', 'eval', 'exec'}
    FORBIDDEN_FUNCTIONS = {'eval', 'exec', 'compile', '__import__'}
    
    def check(self, code: str) -> SecurityCheckResult:
        """检查代码安全性"""
        issues = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return SecurityCheckResult(False, [f"语法错误: {e}"])
        
        for node in ast.walk(tree):
            # 检查危险导入
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.FORBIDDEN_MODULES:
                        issues.append(f"禁止导入模块: {alias.name}")
            
            # 检查危险函数调用
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.FORBIDDEN_FUNCTIONS:
                        issues.append(f"禁止调用函数: {node.func.id}")
            
            # 检查文件操作
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in {'open', 'read', 'write'}:
                        issues.append(f"禁止文件操作: {node.func.attr}")
        
        return SecurityCheckResult(len(issues) == 0, issues)
```

### 2.3 限流与防刷

```python
class RateLimiter:
    """限流器"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.limits = {
            "default": (100, 60),      # 100请求/分钟
            "backtest": (10, 60),      # 10回测/分钟
            "order": (5, 60),          # 5订单/分钟
            "strategy_create": (20, 60) # 20策略创建/分钟
        }
    
    async def check(self, key: str, limit_type: str = "default") -> bool:
        """检查是否超过限流"""
        max_requests, window = self.limits.get(limit_type, self.limits["default"])
        
        current = await self.redis.get(f"rate_limit:{key}")
        if current and int(current) >= max_requests:
            return False
        
        pipe = self.redis.pipeline()
        pipe.incr(f"rate_limit:{key}")
        pipe.expire(f"rate_limit:{key}", window)
        await pipe.execute()
        
        return True
```

---

## 三、交易安全与风控

### 3.1 资金风险管理

#### 3.1.1 四级回撤控制

| 级别 | 触发条件 | 措施 | 通知方式 |
|------|----------|------|----------|
| 预警 (Warning) | 回撤达5% | 邮件/短信提醒 | 邮件+Web通知 |
| 限制 (Limit) | 回撤达10% | 暂停新开仓 | 邮件+短信+Web |
| 强制 (Forced) | 回撤达15% | 减仓50% | 邮件+短信+电话 |
| 紧急 (Emergency) | 回撤达20% | 全部平仓+系统锁定 | 所有渠道+自动执行 |

```python
class DrawdownController:
    """回撤控制器"""
    
    LEVELS = {
        "warning": 0.05,
        "limit": 0.10,
        "forced": 0.15,
        "emergency": 0.20
    }
    
    def __init__(self, account_monitor: 'AccountMonitor'):
        self.account = account_monitor
        self.current_level = None
    
    async def check_drawdown(self):
        """检查回撤状态"""
        balance = await self.account.get_balance()
        equity = await self.account.get_equity()
        peak = await self.account.get_peak_equity()
        
        drawdown = (peak - equity) / peak
        
        # 确定当前级别
        new_level = None
        for level, threshold in sorted(self.LEVELS.items(), key=lambda x: x[1], reverse=True):
            if drawdown >= threshold:
                new_level = level
                break
        
        if new_level != self.current_level:
            await self._trigger_action(new_level, drawdown)
            self.current_level = new_level
    
    async def _trigger_action(self, level: str, drawdown: float):
        """触发风控措施"""
        actions = {
            "warning": self._action_warning,
            "limit": self._action_limit,
            "forced": self._action_forced,
            "emergency": self._action_emergency
        }
        
        action = actions.get(level)
        if action:
            await action(drawdown)
    
    async def _action_warning(self, drawdown: float):
        """预警措施"""
        await self._send_alert(
            level="warning",
            message=f"回撤达到 {drawdown*100:.1f}%，请注意风险",
            channels=["email", "web"]
        )
    
    async def _action_limit(self, drawdown: float):
        """限制措施"""
        await self._send_alert(
            level="limit",
            message=f"回撤达到 {drawdown*100:.1f}%，暂停新开仓",
            channels=["email", "sms", "web"]
        )
        # 暂停新开仓
        await self.account.set_trading_enabled(False)
    
    async def _action_forced(self, drawdown: float):
        """强制措施"""
        await self._send_alert(
            level="forced",
            message=f"回撤达到 {drawdown*100:.1f}%，强制减仓50%",
            channels=["email", "sms", "phone", "web"]
        )
        # 减仓50%
        await self.account.reduce_positions(0.5)
    
    async def _action_emergency(self, drawdown: float):
        """紧急措施"""
        await self._send_alert(
            level="emergency",
            message=f"回撤达到 {drawdown*100:.1f}%，全部平仓",
            channels=["email", "sms", "phone", "web"]
        )
        # 全部平仓
        await self.account.close_all_positions()
        # 锁定系统
        await self.account.lock_trading()
```

#### 3.1.2 持仓限额控制

| 限额类型 | 默认值 | 说明 |
|----------|--------|------|
| 单品种最大持仓 | 1.0手 | 单一品种最大持仓手数 |
| 总敞口上限 | 5.0手 | 所有品种合计最大敞口 |
| 单笔订单大小 | 0.5手 | 单笔订单最大手数 |
| 日交易次数 | 20次 | 每日最大交易次数 |
| 日亏损限额 | 2% | 每日最大亏损百分比 |
| 保证金使用率 | 50% | 最大保证金使用率 |

```python
class PositionLimitController:
    """持仓限额控制器"""
    
    DEFAULT_LIMITS = {
        "max_position_per_symbol": 1.0,
        "max_total_exposure": 5.0,
        "max_order_size": 0.5,
        "max_daily_trades": 20,
        "max_daily_loss_pct": 0.02,
        "max_margin_usage_pct": 0.50
    }
    
    def __init__(self, account_monitor: 'AccountMonitor'):
        self.account = account_monitor
        self.limits = self.DEFAULT_LIMITS.copy()
    
    async def check_trade(self, symbol: str, size: float, direction: str) -> RiskCheckResult:
        """检查交易是否合规"""
        issues = []
        
        # 检查单品种限额
        current_symbol_position = await self.account.get_symbol_position(symbol)
        if abs(current_symbol_position + size) > self.limits["max_position_per_symbol"]:
            issues.append(f"单品种持仓将超过限额: {self.limits['max_position_per_symbol']}手")
        
        # 检查总敞口
        total_exposure = await self.account.get_total_exposure()
        if total_exposure + size > self.limits["max_total_exposure"]:
            issues.append(f"总敞口将超过限额: {self.limits['max_total_exposure']}手")
        
        # 检查单笔订单大小
        if size > self.limits["max_order_size"]:
            issues.append(f"单笔订单超过限额: {self.limits['max_order_size']}手")
        
        # 检查日交易次数
        daily_trades = await self.account.get_daily_trade_count()
        if daily_trades >= self.limits["max_daily_trades"]:
            issues.append(f"日交易次数已达上限: {self.limits['max_daily_trades']}次")
        
        # 检查日亏损
        daily_pnl = await self.account.get_daily_pnl()
        balance = await self.account.get_balance()
        if daily_pnl < -balance * self.limits["max_daily_loss_pct"]:
            issues.append(f"日亏损已达上限: {self.limits['max_daily_loss_pct']*100}%")
        
        # 检查保证金使用率
        margin_usage = await self.account.get_margin_usage()
        if margin_usage > self.limits["max_margin_usage_pct"]:
            issues.append(f"保证金使用率超过限额: {self.limits['max_margin_usage_pct']*100}%")
        
        return RiskCheckResult(len(issues) == 0, issues)
```

### 3.2 异常交易监控

#### 3.2.1 价格波动率监控

```python
class VolatilityMonitor:
    """波动率监控器"""
    
    def __init__(self, data_source: 'DataSource'):
        self.data = data_source
        self.thresholds = {
            "normal": 2.0,      # 2倍ATR为正常
            "warning": 3.0,     # 3倍ATR为警告
            "extreme": 5.0      # 5倍ATR为极端
        }
    
    async def check_volatility(self, symbol: str):
        """检查波动率异常"""
        # 获取最近价格变化
        recent_data = await self.data.get_recent_data(symbol, bars=20)
        
        current_price = recent_data['close'].iloc[-1]
        prev_price = recent_data['close'].iloc[-2]
        price_change = abs(current_price - prev_price) / prev_price
        
        # 计算ATR
        atr = self._calculate_atr(recent_data)
        
        # 计算波动率倍数
        volatility_multiple = price_change / atr if atr > 0 else 0
        
        if volatility_multiple > self.thresholds["extreme"]:
            return VolatilityAlert("extreme", volatility_multiple, symbol)
        elif volatility_multiple > self.thresholds["warning"]:
            return VolatilityAlert("warning", volatility_multiple, symbol)
        
        return None
```

#### 3.2.2 策略衰减检测

```python
class StrategyDecayDetector:
    """策略衰减检测器"""
    
    def __init__(self, backtest_service: 'BacktestService'):
        self.backtest = backtest_service
        self.decay_threshold = 0.3  # 夏普比率下降30%视为衰减
    
    async def check_decay(self, strategy_id: str) -> Optional[DecayAlert]:
        """检查策略是否衰减"""
        # 获取历史回测结果
        results = await self.backtest.get_historical_results(strategy_id, months=6)
        
        if len(results) < 3:
            return None  # 数据不足
        
        # 计算夏普比率趋势
        sharpe_values = [r.sharpe_ratio for r in results]
        
        # 线性回归分析趋势
        slope = self._calculate_trend(sharpe_values)
        
        # 计算衰减程度
        initial_sharpe = sharpe_values[0]
        current_sharpe = sharpe_values[-1]
        decay_pct = (initial_sharpe - current_sharpe) / initial_sharpe if initial_sharpe > 0 else 0
        
        if decay_pct > self.decay_threshold:
            return DecayAlert(
                strategy_id=strategy_id,
                decay_pct=decay_pct,
                initial_sharpe=initial_sharpe,
                current_sharpe=current_sharpe,
                trend_slope=slope
            )
        
        return None
```

#### 3.2.3 数据质量监控

```python
class DataQualityMonitor:
    """数据质量监控器"""
    
    def __init__(self, data_source: 'DataSource'):
        self.data = data_source
    
    async def check_data_quality(self, symbol: str, timeframe: str) -> DataQualityReport:
        """检查数据质量"""
        issues = []
        
        # 获取最近数据
        data = await self.data.get_ohlcv(symbol, timeframe, days=1)
        
        # 检查缺失值
        missing_count = data.isnull().sum().sum()
        if missing_count > 0:
            issues.append(f"发现{missing_count}个缺失值")
        
        # 检查时间连续性
        expected_interval = self._get_interval(timeframe)
        time_diffs = data.index.to_series().diff().dropna()
        gaps = time_diffs[time_diffs > expected_interval * 2]
        if len(gaps) > 0:
            issues.append(f"发现{len(gaps)}个时间缺口")
        
        # 检查OHLC逻辑
        invalid_ohlc = data[data['high'] < data['low']]
        if len(invalid_ohlc) > 0:
            issues.append(f"发现{len(invalid_ohlc)}条无效OHLC记录")
        
        # 检查价格异常
        price_changes = data['close'].pct_change().abs()
        extreme_changes = price_changes[price_changes > 0.1]  # 10%以上为异常
        if len(extreme_changes) > 0:
            issues.append(f"发现{len(extreme_changes)}个极端价格变动")
        
        # 检查数据延迟
        last_bar_time = data.index[-1]
        delay = datetime.now() - last_bar_time
        if delay > timedelta(minutes=5):
            issues.append(f"数据延迟: {delay}")
        
        return DataQualityReport(
            symbol=symbol,
            timeframe=timeframe,
            total_bars=len(data),
            issues=issues,
            is_healthy=len(issues) == 0
        )
```

### 3.3 风控规则引擎

```python
class RiskRuleEngine:
    """风控规则引擎"""
    
    def __init__(self):
        self.rules: List[RiskRule] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认风控规则"""
        self.rules = [
            # 回撤控制规则
            RiskRule(
                name="max_drawdown",
                condition=lambda ctx: ctx.drawdown > 0.20,
                action="emergency_close",
                priority=1
            ),
            
            # 日亏损限额规则
            RiskRule(
                name="daily_loss_limit",
                condition=lambda ctx: ctx.daily_pnl < -ctx.balance * 0.02,
                action="stop_trading",
                priority=2
            ),
            
            # 保证金使用率规则
            RiskRule(
                name="margin_usage",
                condition=lambda ctx: ctx.margin_usage > 0.50,
                action="reduce_positions",
                priority=3
            ),
            
            # 波动率异常规则
            RiskRule(
                name="volatility_spike",
                condition=lambda ctx: ctx.volatility_multiple > 5.0,
                action="pause_trading",
                priority=2
            ),
            
            # 连续亏损规则
            RiskRule(
                name="consecutive_losses",
                condition=lambda ctx: ctx.consecutive_losses >= 5,
                action="reduce_size",
                priority=4
            ),
            
            # 策略衰减规则
            RiskRule(
                name="strategy_decay",
                condition=lambda ctx: ctx.strategy_decay_pct > 0.30,
                action="alert_and_review",
                priority=5
            )
        ]
    
    async def evaluate(self, context: RiskContext) -> List[RiskAction]:
        """评估所有规则"""
        actions = []
        
        for rule in sorted(self.rules, key=lambda r: r.priority):
            if rule.condition(context):
                actions.append(RiskAction(
                    rule_name=rule.name,
                    action_type=rule.action,
                    priority=rule.priority
                ))
        
        return actions
```

---

## 四、数据安全

### 4.1 加密存储

#### 4.1.1 敏感数据加密

| 数据类型 | 加密方式 | 密钥管理 |
|----------|----------|----------|
| API密钥 | AES-256-GCM | 环境变量 + 密钥管理服务 |
| 密码 | bcrypt哈希 | 自动盐值 |
| 交易指令 | HMAC-SHA256签名 | 对称密钥 |
| 策略代码 | 不加密(业务数据) | - |

```python
from cryptography.fernet import Fernet
import bcrypt

class EncryptionManager:
    """加密管理器"""
    
    def __init__(self, master_key: bytes):
        self.cipher = Fernet(master_key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """加密API密钥"""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted: str) -> str:
        """解密API密钥"""
        return self.cipher.decrypt(encrypted.encode()).decode()
    
    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode(), hashed.encode())
    
    def sign_order(self, order: dict, secret: str) -> str:
        """签名交易指令"""
        import hmac
        import hashlib
        
        message = json.dumps(order, sort_keys=True)
        return hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
```

### 4.2 访问控制

#### 4.2.1 数据库访问控制

```python
class DatabaseAccessControl:
    """数据库访问控制"""
    
    PERMISSION_MATRIX = {
        "admin": {
            "strategies": ["SELECT", "INSERT", "UPDATE", "DELETE"],
            "backtests": ["SELECT", "INSERT", "UPDATE", "DELETE"],
            "orders": ["SELECT", "INSERT", "UPDATE", "DELETE"],
            "users": ["SELECT", "INSERT", "UPDATE", "DELETE"]
        },
        "trader": {
            "strategies": ["SELECT", "INSERT", "UPDATE"],
            "backtests": ["SELECT", "INSERT"],
            "orders": ["SELECT", "INSERT"],
            "users": ["SELECT"]
        },
        "viewer": {
            "strategies": ["SELECT"],
            "backtests": ["SELECT"],
            "orders": ["SELECT"],
            "users": []
        }
    }
    
    def check_permission(self, user_role: str, table: str, operation: str) -> bool:
        """检查数据库操作权限"""
        permissions = self.PERMISSION_MATRIX.get(user_role, {})
        table_perms = permissions.get(table, [])
        return operation in table_perms
```

### 4.3 审计日志

#### 4.3.1 审计事件类型

| 事件类型 | 说明 | 记录内容 |
|----------|------|----------|
| USER_LOGIN | 用户登录 | 用户名、IP、时间、结果 |
| STRATEGY_CREATE | 创建策略 | 策略ID、创建者、时间 |
| BACKTEST_RUN | 运行回测 | 回测ID、策略ID、执行者 |
| ORDER_PLACE | 下单 | 订单详情、执行者、时间 |
| ORDER_CANCEL | 撤单 | 订单ID、执行者、时间 |
| POSITION_CLOSE | 平仓 | 持仓ID、盈亏、执行者 |
| RISK_TRIGGER | 风控触发 | 规则名、触发值、措施 |
| AGENT_CONTROL | Agent控制 | AgentID、操作、执行者 |
| SETTINGS_CHANGE | 配置变更 | 变更项、旧值、新值 |

```python
class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def log(self, event_type: str, user_id: str, 
                  details: dict, ip_address: str = None):
        """记录审计日志"""
        
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "event_type": event_type,
            "user_id": user_id,
            "details_json": json.dumps(details),
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # 写入数据库
        await self.db.execute("""
            INSERT INTO audit_logs (log_id, event_type, user_id, 
                                   details_json, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            log_entry["log_id"],
            log_entry["event_type"],
            log_entry["user_id"],
            log_entry["details_json"],
            log_entry["ip_address"],
            log_entry["created_at"]
        ))
        
        # 同时写入文件日志（防篡改）
        self._write_to_file(log_entry)
    
    def _write_to_file(self, log_entry: dict):
        """写入防篡改日志文件"""
        log_file = f"logs/audit/{datetime.now().strftime('%Y-%m')}.log"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
```

---

## 五、基础设施安全

### 5.1 网络安全

| 措施 | 说明 |
|------|------|
| TLS加密 | 所有API通信使用HTTPS |
| CORS限制 | 只允许指定域名访问 |
| IP白名单 | 关键接口限制访问IP |
| DDoS防护 | 请求频率限制和异常检测 |

### 5.2 主机安全

| 措施 | 说明 |
|------|------|
| 最小权限 | 服务以非root用户运行 |
| 防火墙 | 仅开放必要端口 |
| 安全更新 | 定期更新系统补丁 |
| 入侵检测 | 异常行为监控和告警 |

### 5.3 密钥管理

```python
class SecretManager:
    """密钥管理器"""
    
    def __init__(self):
        self._secrets = {}
        self._load_from_env()
    
    def _load_from_env(self):
        """从环境变量加载密钥"""
        import os
        
        self._secrets = {
            "jwt_secret": os.getenv("JWT_SECRET_KEY"),
            "db_password": os.getenv("DB_PASSWORD"),
            "api_key_encryption": os.getenv("API_KEY_ENCRYPTION_KEY"),
            "mt5_signature": os.getenv("MT5_SIGNATURE_KEY")
        }
    
    def get(self, key: str) -> str:
        """获取密钥"""
        return self._secrets.get(key)
    
    def rotate_key(self, key: str, new_value: str):
        """轮换密钥"""
        # 更新内存中的密钥
        self._secrets[key] = new_value
        
        # 更新环境变量
        os.environ[key.upper()] = new_value
        
        # 记录密钥轮换审计日志
        # ...
```

---

## 六、应急响应

### 6.1 应急响应流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           应急响应流程                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. 检测异常                                                                 │
│     ↓                                                                       │
│  2. 评估影响 (高/中/低)                                                      │
│     ↓                                                                       │
│  3. 触发响应                                                                 │
│     ├── 高风险: 立即平仓 + 锁定系统 + 通知管理员                               │
│     ├── 中风险: 限制交易 + 详细检查 + 邮件通知                                 │
│     └── 低风险: 记录日志 + 持续监控                                            │
│     ↓                                                                       │
│  4. 执行恢复                                                                 │
│     ├── 数据恢复: 从备份恢复                                                   │
│     ├── 系统恢复: 重启服务/切换备用                                            │
│     └── 交易恢复: 逐步恢复交易权限                                             │
│     ↓                                                                       │
│  5. 事后分析                                                                 │
│     ├── 根因分析                                                              │
│     ├── 改进措施                                                              │
│     └── 更新风控规则                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 紧急联系方式

| 场景 | 响应时间 | 联系方式 |
|------|----------|----------|
| 系统被入侵 | 5分钟 | 安全团队 + 管理层 |
| 大额异常交易 | 1分钟 | 风控团队 + 交易员 |
| 数据泄露 | 10分钟 | 安全团队 + 法务 |
| 服务不可用 | 15分钟 | 运维团队 |

---

## 七、合规要求

### 7.1 数据保留

| 数据类型 | 保留期限 | 法规依据 |
|----------|----------|----------|
| 交易记录 | 7年 | 金融监管要求 |
| 审计日志 | 3年 | 信息安全要求 |
| 用户数据 | 账户注销后2年 | 隐私保护要求 |
| 策略代码 | 永久 | 知识产权要求 |

### 7.2 审计要求

- 所有交易操作必须记录完整审计日志
- 审计日志不可修改、不可删除
- 定期审计报告生成（月度/季度）
- 支持监管机构的审计查询

---

## 八、附录

### 8.1 安全清单

#### 部署前检查

- [ ] 所有密码已更改为强密码
- [ ] API密钥已加密存储
- [ ] JWT密钥已安全生成
- [ ] 数据库访问已配置权限
- [ ] 防火墙规则已配置
- [ ] TLS证书已安装
- [ ] 日志记录已启用
- [ ] 备份策略已配置
- [ ] 监控告警已配置
- [ ] 应急响应流程已确认

#### 日常检查

- [ ] 检查异常登录尝试
- [ ] 检查异常交易行为
- [ ] 检查系统资源使用
- [ ] 检查数据备份状态
- [ ] 检查安全补丁更新

### 8.2 参考标准

- OWASP Top 10
- ISO 27001信息安全管理
- PCI DSS支付卡行业安全标准
- GDPR通用数据保护条例

### 8.3 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| V1.0 | 2026-06-06 | 初始版本，包含应用安全、交易风控、数据安全、基础设施安全四大体系 |
