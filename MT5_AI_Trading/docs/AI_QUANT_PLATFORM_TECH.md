# AI量化赋能平台 — 技术架构文档

> 版本: v1.0  
> 日期: 2026-06-06  
> 目标: 基于现有MT5_AI_Trading基础设施，设计可扩展的AI量化平台技术架构

---

## 1. 总体架构

### 1.1 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户交互层 (Presentation)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Web Dashboard │  │  Desktop App │  │  Telegram Bot │  │  API Gateway │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
└─────────┼─────────────────┼─────────────────┼─────────────────┼───────────┘
          │                 │                 │                 │
          └─────────────────┴────────┬────────┴─────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────────┐
│                         应用服务层 (Application)                             │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ │
│  │ Strategy       │ │ Backtest       │ │ Market         │ │ Deployment   │ │
│  │ Generator      │ │ Engine         │ │ Observer       │ │ Manager      │ │
│  │ (LLM + Template)│ │ (Walk-Forward) │ │ (Scan + Alert) │ │ (MT5 Bridge) │ │
│  └───────┬────────┘ └───────┬────────┘ └───────┬────────┘ └──────┬───────┘ │
└──────────┼──────────────────┼──────────────────┼─────────────────┼─────────┘
           │                  │                  │                 │
           └──────────────────┴────────┬─────────┴─────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                          领域核心层 (Domain Core)                            │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ │
│  │ State Hex      │ │ Signal Scorer  │ │ Risk Manager   │ │ Portfolio    │ │
│  │ Engine         │ │ & Attribution  │ │                │ │ Optimizer    │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ └──────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                          基础设施层 (Infrastructure)                         │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ │
│  │ Data Layer     │ │ Compute Layer  │ │ Execution Layer│ │ Storage      │ │
│  │ (MT5 Bridge)   │ │ (Feature Eng)  │ │ (Sim/Live)     │ │ (DuckDB)     │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ └──────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 技术选型对比

基于GitHub主流项目调研，我们的技术栈选择：

| 层级 | 候选方案 | 选择 | 理由 |
|------|----------|------|------|
| **回测引擎** | VectorBT / Backtrader / Zipline | **自研+VectorBT参考** | 需要State Hex专属指标，VectorBT理念借鉴（向量化） |
| **数据存储** | PostgreSQL / DuckDB / SQLite | **DuckDB** | 已在使用，嵌入式、高性能、支持复杂分析查询 |
| **AI/LLM** | OpenAI / Anthropic / Local | **OpenAI GPT-4 + Claude** | 策略生成需要强推理能力 |
| **任务调度** | Celery / APScheduler / Airflow | **APScheduler** | 轻量，适合个人交易者部署 |
| **Web前端** | React / Vue / Streamlit | **Streamlit (MVP) → React** | 快速原型→生产级 |
| **通知推送** | Telegram Bot / 飞书 / 邮件 | **Telegram + 飞书** | 国内外兼顾 |
| **部署** | Docker / 本地 / 云 | **本地优先 + Docker可选** | 降低用户使用门槛 |

---

## 2. 核心模块设计

### 2.1 策略生成引擎 (Strategy Generator)

```python
# 架构接口
class StrategyGenerator:
    """
    自然语言 → 可执行策略代码
    
    借鉴: FinRL-X的模块化策略管道 (Selection→Allocation→Timing→Risk)
    差异化: 自然语言输入 + State Hex专属模板
    """
    
    def generate(self, natural_language: str, context: Dict) -> StrategyBundle:
        """
        输入: "黄金H1收缩突破做多，持仓5根K线"
        输出: {
            strategy_code: str,      # Python代码
            backtest_config: Dict,   # 回测配置
            strategy_doc: str,       # 策略说明
            template_used: str,      # 使用的模板
            confidence: float        # AI置信度
        }
        """
        # 1. LLM解析 → 提取策略要素
        elements = self.llm_extractor.extract(natural_language)
        
        # 2. 模板匹配 → 选择最接近的模板
        template = self.template_registry.match(elements)
        
        # 3. 参数填充 → 生成策略代码
        code = template.render(elements)
        
        # 4. 语法检查 → 确保可执行
        self.code_validator.validate(code)
        
        # 5. 回测配置生成
        config = self.config_generator.generate(elements, context)
        
        return StrategyBundle(code, config, ...)
```

**模板库设计**:

| 模板ID | 描述 | 参数 |
|--------|------|------|
| `state_hex_direction` | State Hex方向策略 | state_pattern, direction, hold_bars |
| `squeeze_breakout` | 收缩突破策略 | timeframe, direction, hold_bars, sl_type |
| `ma_crossover` | 均线交叉策略 | fast_ma, slow_ma, direction |
| `pivot_squeeze` | ACD枢轴收缩策略 | pivot_type, contraction_threshold |
| `momentum_state` | 动量状态策略 | momentum_period, state_filter |

### 2.2 回测引擎 (Backtest Engine)

```python
class WalkForwardBacktester:
    """
    Walk-Forward回测引擎
    
    借鉴: VectorBT的向量化回测理念
    差异化: State Hex专属指标 + MT5实际点差
    """
    
    def run(self, strategy: Strategy, config: BacktestConfig) -> BacktestReport:
        # 1. 数据加载 (Data Layer)
        data = self.data_layer.load(config.symbols, config.timeframes, config.date_range)
        
        # 2. 特征计算 (Compute Layer)
        features = self.compute_layer.calculate(data, strategy.required_features)
        
        # 3. Walk-Forward分割
        splits = self._walk_forward_split(data, config.train_pct, config.val_pct)
        
        # 4. 逐段回测
        results = []
        for train, val, test in splits:
            # 训练期: 策略参数优化
            params = self.optimizer.optimize(strategy, train)
            
            # 验证期: 防止过拟合
            val_result = self._run_single(strategy.with_params(params), val)
            
            # 测试期: 真实性能
            test_result = self._run_single(strategy.with_params(params), test)
            
            results.append(WalkForwardResult(train, val, test))
        
        # 5. 汇总报告
        return BacktestReport(results, self.metrics_calculator.calculate(results))
```

**关键设计决策**:

| 决策 | 选择 | 理由 |
|------|------|------|
| 回测方式 | 向量化 + 事件驱动混合 | 向量化用于快速筛选，事件驱动用于精确模拟 |
| 成本模型 | MT5实际点差 | 非固定成本，更贴近实盘 |
| 滑点模型 | 基于波动率的动态滑点 | 高波动期滑点更大 |
| 数据对齐 | merge_asof (需验证无未来函数) | 多周期数据对齐 |

### 2.3 市场观察站 (Market Observer)

```python
class MarketObserver:
    """
    7×24市场扫描 + 复现检测
    
    借鉴: Qlib的实时数据管道
    差异化: State Hex组合观察 + 复现提醒
    """
    
    def __init__(self):
        self.scanners = [
            StateHexScanner(),      # State Hex组合变化
            SqueezeBreakoutScanner(), # 收缩突破检测
            ReificationScanner(),     # 复现检测 (70%/80%阈值)
        ]
        self.notifiers = [
            TelegramNotifier(),
            LarkNotifier(),
            WebDashboardUpdater(),
        ]
    
    async def scan(self, symbols: List[str], timeframes: List[str]):
        # 1. 获取最新数据
        data = await self.data_feed.get_latest(symbols, timeframes)
        
        # 2. 计算State Hex
        states = self.state_engine.calculate(data)
        
        # 3. 各扫描器检测
        alerts = []
        for scanner in self.scanners:
            alerts.extend(scanner.scan(states))
        
        # 4. 去重 + 优先级排序
        alerts = self._deduplicate(alerts)
        alerts = self._prioritize(alerts)
        
        # 5. 推送通知
        for alert in alerts:
            for notifier in self.notifiers:
                await notifier.send(alert)
        
        # 6. 更新观察数据库
        self.observation_db.save_scan_result(alerts)
```

**观察维度详细设计**:

| 扫描器 | 检测内容 | 触发条件 | 优先级 |
|--------|----------|----------|--------|
| StateHexScanner | H1视角D1/H4的0,8组合 | 0→8或8→0转换 | 高 |
| SqueezeBreakoutScanner | Bollinger Band收缩+突破 | 收缩持续3+根K线后突破 | 高 |
| ReificationScanner | 当前状态与历史关键观察匹配 | 匹配度≥70%或≥80% | 最高 |
| MomentumScanner | 动量异常变化 | 动量偏离2σ | 中 |
| VolumeScanner | 成交量异常 | 成交量偏离3σ | 中 |

### 2.4 部署管理器 (Deployment Manager)

```python
class DeploymentManager:
    """
    策略部署: 回测 → 模拟盘 → 实盘
    
    借鉴: FinRL-X的统一weight接口
    差异化: MT5专属桥接 + 风控层
    """
    
    async def deploy(self, strategy: Strategy, target: DeploymentTarget):
        if target == DeploymentTarget.SIMULATION:
            # 模拟盘: 直接部署到MT5模拟账户
            await self.mt5_bridge.deploy_simulation(strategy)
            
        elif target == DeploymentTarget.LIVE:
            # 实盘: 需风控审核
            risk_check = self.risk_manager.evaluate(strategy)
            if not risk_check.passed:
                raise RiskCheckFailed(risk_check.reasons)
            
            # 二次确认
            if not await self._user_confirm():
                raise DeploymentCancelled()
            
            await self.mt5_bridge.deploy_live(strategy)
    
    async def sync_performance(self, deployment_id: str):
        # 同步实盘/模拟盘绩效
        live_trades = await self.mt5_bridge.get_trades(deployment_id)
        backtest_expectation = self.backtest_db.get_expectation(deployment_id)
        
        # 检测偏差
        deviation = self._calculate_deviation(live_trades, backtest_expectation)
        if deviation > 0.20:  # 偏差>20%告警
            await self.notifier.send_deviation_alert(deployment_id, deviation)
```

---

## 3. 数据流架构

### 3.1 实时数据流

```
MT5 Terminal ──→ MT5DataBridge ──→ DuckDB (raw_data)
                                      │
                                      ▼
                              Compute Layer
                              (State Hex / Features)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              Strategy Layer    Observer Layer    Backtest Layer
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      ▼
                              Storage Layer
                         (observation_db.duckdb)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              Web Dashboard    Telegram Bot    Report Generator
```

### 3.2 数据模型

```sql
-- 核心表结构 (DuckDB)

-- 1. 原始K线数据
CREATE TABLE ohlcv_data (
    symbol VARCHAR,
    timeframe VARCHAR,
    timestamp TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    PRIMARY KEY (symbol, timeframe, timestamp)
);

-- 2. State Hex状态
CREATE TABLE state_hex_snapshots (
    symbol VARCHAR,
    timeframe VARCHAR,
    timestamp TIMESTAMP,
    state_hex VARCHAR(1),  -- 0-F
    base_state INTEGER,     -- 0/8
    volatility_state INTEGER, -- 0/1
    position_state INTEGER,   -- 0/2
    trend_state INTEGER,      -- 0/4
    PRIMARY KEY (symbol, timeframe, timestamp)
);

-- 3. 策略定义
CREATE TABLE strategies (
    strategy_id INTEGER PRIMARY KEY,
    name VARCHAR,
    description TEXT,
    template_id VARCHAR,
    code TEXT,
    params JSON,
    created_by VARCHAR,
    created_at TIMESTAMP,
    status VARCHAR  -- 'draft' | 'validated' | 'deployed' | 'retired'
);

-- 4. 回测结果
CREATE TABLE backtest_results (
    result_id INTEGER PRIMARY KEY,
    strategy_id INTEGER,
    symbol VARCHAR,
    timeframe VARCHAR,
    start_date DATE,
    end_date DATE,
    total_return DOUBLE,
    sharpe_ratio DOUBLE,
    max_drawdown DOUBLE,
    win_rate DOUBLE,
    profit_factor DOUBLE,
    train_metrics JSON,
    val_metrics JSON,
    test_metrics JSON,
    created_at TIMESTAMP
);

-- 5. 观察记录 (已有)
-- observation_sessions, daily_contraction_profiles, symbol_signatures, key_observations

-- 6. 部署记录
CREATE TABLE deployments (
    deployment_id INTEGER PRIMARY KEY,
    strategy_id INTEGER,
    target VARCHAR,  -- 'simulation' | 'live'
    status VARCHAR,  -- 'active' | 'paused' | 'stopped'
    started_at TIMESTAMP,
    stopped_at TIMESTAMP,
    live_return DOUBLE,
    backtest_deviation DOUBLE
);
```

---

## 4. AI/LLM集成设计

### 4.1 策略生成Prompt工程

```python
STRATEGY_GENERATION_PROMPT = """
你是一位专业的量化交易策略工程师。请将用户的交易想法转化为结构化的策略要素。

用户输入: {user_input}

请提取以下要素（如未提及则标记为null）：
1. 交易品种 (symbol): 如 XAUUSD, EURUSD
2. 时间周期 (timeframe): 如 H1, M15, D1
3. 交易方向 (direction): long / short / both
4. 入场条件 (entry_conditions): 列表形式
5. 出场条件 (exit_conditions): 列表形式
6. 持仓周期 (hold_bars): 数字或null
7. 止损方式 (stop_loss): 如 "前低", "固定点数", "ATR倍数"
8. 止盈方式 (take_profit): 如 "固定点数", "风险回报比", "持仓周期"
9. 过滤器 (filters): 如 "仅在W1趋势向上时"

输出格式（严格JSON）:
{
    "symbol": "...",
    "timeframe": "...",
    "direction": "...",
    "entry_conditions": [...],
    "exit_conditions": [...],
    "hold_bars": ...,
    "stop_loss": "...",
    "take_profit": "...",
    "filters": [...],
    "confidence": 0.0-1.0
}

注意:
- 如果用户描述模糊，请给出最合理的推断
- 如果涉及State Hex状态，请使用标准格式如 "D1=6,H1=4"
- 如果涉及收缩突破，请标注 "squeeze_breakout"
"""
```

### 4.2 策略解释Prompt

```python
STRATEGY_EXPLANATION_PROMPT = """
请为以下策略生成人类可读的解释报告：

策略代码:
{strategy_code}

回测结果:
{backtest_results}

请生成:
1. 策略逻辑简述（2-3句话）
2. 核心假设（策略基于什么市场规律）
3. 风险点（什么情况下会失效）
4. 与回测数据的吻合度评价
5. 建议（是否建议实盘测试）

输出为Markdown格式。
"""
```

---

## 5. 部署架构

### 5.1 本地部署（推荐个人交易者）

```yaml
# docker-compose.yml (可选)
version: '3.8'
services:
  ai-quant-platform:
    build: .
    volumes:
      - ./data:/app/data
      - ./strategies:/app/strategies
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MT5_PATH=${MT5_PATH}
    ports:
      - "8501:8501"  # Streamlit
      - "5000:5000"  # API
    depends_on:
      - duckdb
  
  duckdb:
    image: duckdb/duckdb
    volumes:
      - ./data:/data
```

### 5.2 组件依赖关系

```
ai_runner.py (主入口)
    ├── strategy_generator/ (策略生成)
    │       └── llm_client.py
    │       └── template_registry.py
    │       └── code_validator.py
    ├── backtest_platform/ (回测平台 - 已有)
    │       ├── data_layer.py
    │       ├── compute_layer.py
    │       ├── strategy_layer.py
    │       ├── execution_layer.py
    │       └── presentation_layer.py
    ├── market_observer/ (市场观察)
    │       ├── scanners/
    │       │       ├── state_hex_scanner.py
    │       │       ├── squeeze_scanner.py
    │       │       └── reification_scanner.py
    │       └── notifiers/
    │               ├── telegram_bot.py
    │               └── lark_webhook.py
    ├── deployment/ (部署管理)
    │       ├── mt5_bridge.py (已有)
    │       └── risk_manager.py
    └── storage/ (数据存储)
            ├── duckdb_manager.py
            └── observation_db.py (已有)
```

---

## 6. 关键技术决策

### 6.1 为什么不用VectorBT/Backtrader作为核心回测引擎？

| 维度 | VectorBT | 自研引擎 |
|------|----------|----------|
| State Hex指标 | ❌ 不支持 | ✅ 原生支持 |
| MT5点差模拟 | ⚠️ 需改造 | ✅ 原生支持 |
| Walk-Forward | ⚠️ 需改造 | ✅ 原生支持 |
| 多周期对齐 | ⚠️ 需改造 | ✅ 原生支持 |
| 性能 | ✅ 极快 | ⚠️ 够用 |
| 学习成本 | ⚠️ 较高 | ✅ 低（自研可控） |

**决策**: 自研引擎为主，借鉴VectorBT向量化理念优化性能瓶颈。

### 6.2 为什么DuckDB而非PostgreSQL？

| 维度 | PostgreSQL | DuckDB |
|------|------------|--------|
| 部署复杂度 | 需独立服务 | 嵌入式，零部署 |
| 分析查询 | 需复杂JOIN | 原生支持复杂分析 |
| 数据量 | 适合TB级 | 适合GB级（个人交易足够） |
| 与Pandas集成 | 需转换 | 零拷贝 |
| 已有基础 | ❌ | ✅ 项目已使用 |

**决策**: 继续使用DuckDB，未来数据量增长后可迁移到PostgreSQL。

### 6.3 为什么APScheduler而非Celery？

| 维度 | Celery | APScheduler |
|------|--------|-------------|
| 依赖 | Redis/RabbitMQ | 无额外依赖 |
| 复杂度 | 高 | 低 |
| 适用场景 | 分布式任务 | 本地定时任务 |
| 观察站扫描 | 过度设计 | 足够 |

**决策**: APScheduler用于本地定时扫描，未来需要分布式时再引入Celery。

---

## 7. 性能优化策略

### 7.1 回测性能

```python
# 向量化回测（快速筛选）
def vectorized_backtest(signal_array, price_array):
    """NumPy向量化计算，秒级完成多年回测"""
    positions = np.where(signal_array == 1, 1, 0)
    returns = np.diff(price_array) / price_array[:-1]
    strategy_returns = positions[:-1] * returns
    return calculate_metrics(strategy_returns)

# 事件驱动回测（精确模拟）
def event_driven_backtest(signals, market_data, execution_model):
    """逐事件模拟，分钟级完成，但精度高"""
    portfolio = Portfolio()
    for event in market_data.events():
        if event.timestamp in signals:
            order = execution_model.simulate(event, signals[event.timestamp])
            portfolio.execute(order)
    return portfolio.report()
```

**策略**: 先用向量化快速筛选，对通过筛选的策略再用事件驱动精确验证。

### 7.2 数据缓存

```python
# 多级缓存
class DataCache:
    def __init__(self):
        self.l1 = {}  # 内存缓存 (最近1天)
        self.l2 = duckdb  # 本地数据库 (最近1年)
        self.l3 = MT5  # MT5历史 (全部)
    
    def get(self, symbol, timeframe, start, end):
        # 1. 查内存
        if self.l1.hit(symbol, timeframe, start, end):
            return self.l1.get(symbol, timeframe, start, end)
        
        # 2. 查DuckDB
        if self.l2.hit(symbol, timeframe, start, end):
            data = self.l2.get(symbol, timeframe, start, end)
            self.l1.put(data)
            return data
        
        # 3. 从MT5加载
        data = self.l3.get(symbol, timeframe, start, end)
        self.l2.put(data)
        self.l1.put(data)
        return data
```

---

## 8. 安全设计

### 8.1 代码安全

```python
class CodeSandbox:
    """策略代码沙箱执行"""
    
    def execute(self, code: str, data: pd.DataFrame):
        # 1. 静态分析: 禁止危险操作
        if self._has_dangerous_imports(code):
            raise SecurityError("策略代码包含危险导入")
        
        # 2. 资源限制: CPU/内存/时间
        with resource_limits(cpu=30, memory=512MB, time=60s):
            result = self._safe_execute(code, data)
        
        # 3. 网络隔离: 禁止外部请求
        if self._has_network_access(code):
            raise SecurityError("策略代码尝试网络访问")
        
        return result
```

### 8.2 交易安全

| 层级 | 措施 |
|------|------|
| 策略层 | 最大持仓限制、品种分散要求 |
| 风控层 | 单日最大亏损、连续亏损暂停 |
| 执行层 | 订单大小限制、价格偏离检查 |
| 账户层 | 模拟盘→实盘过渡要求 |

---

## 9. 测试策略

### 9.1 测试金字塔

```
        /\
       /  \     E2E Tests (端到端)
      /____\      - 完整流程: 生成→回测→部署
     /      \   
    /________\   Integration Tests (集成测试)
   /          \    - 数据层+计算层
  /____________\   - 策略层+执行层
 /              \
/________________\ Unit Tests (单元测试)
                   - State Hex计算
                   - 信号生成
                   - 绩效指标计算
```

### 9.2 关键测试用例

| 模块 | 测试用例 | 验证点 |
|------|----------|--------|
| Data Layer | merge_asof对齐 | 无未来函数 |
| Compute Layer | State Hex编码 | 边界条件正确 |
| Strategy Layer | 信号生成 | 符合策略逻辑 |
| Execution Layer | 成本计算 | MT5点差正确应用 |
| Observer | 复现检测 | 70%/80%阈值正确触发 |
| Generator | 代码生成 | 生成代码可执行 |

---

## 10. 参考与借鉴

### 10.1 开源项目借鉴清单

| 项目 | 借鉴内容 | 差异化 |
|------|----------|--------|
| **Microsoft Qlib** | 数据处理器设计、模型训练管道 | 更贴近MT5实盘，支持外汇/CFD |
| **FinRL-X** | 模块化策略管道 (S-A-T-R)、部署一致性 | 自然语言输入、State Hex专属 |
| **VectorBT** | 向量化回测理念、Numba加速 | 端到端闭环、多周期对齐 |
| **NautilusTrader** | Rust+Python混合架构、事件驱动 | 更轻量、AI策略生成 |
| **QuantConnect Lean** | 券商集成、实盘部署 | 本地化部署、个人友好 |
| **Jesse** | 统一代码库（回测/模拟/实盘） | 多策略模板、AI生成 |

### 10.2 关键论文

- FinRL-X: An AI-Native Modular Infrastructure for Quantitative Trading (2025)
- Qlib: An AI-oriented Quantitative Investment Platform (Microsoft Research)
- Advances in Financial Machine Learning (Marcos López de Prado)

---

## 11. 附录

### 11.1 术语对照表

| 英文术语 | 中文 | 说明 |
|----------|------|------|
| Walk-Forward | 滚动回测 | 训练/验证/测试三段分离的回测方法 |
| State Hex | 状态十六进制 | P107标准，0-F表示市场状态 |
| Squeeze | 收缩 | Bollinger Band收窄，预示波动率即将扩大 |
| Reification | 复现 | 当前市场状态与历史关键状态的匹配 |
| Overfitting | 过拟合 | 策略在历史数据上表现好但实盘差 |
| Lookahead Bias | 未来函数 | 使用未来信息指导当前决策 |
| Slippage | 滑点 | 下单价格与实际成交价格的差异 |
| Drawdown | 回撤 | 从峰值到谷底的资金下降幅度 |

### 11.2 文件索引

| 文件 | 说明 |
|------|------|
| `docs/AI_QUANT_PLATFORM_PRD.md` | 产品需求文档 |
| `docs/AI_QUANT_PLATFORM_TECH.md` | 技术架构文档（本文档） |
| `python/backtest_platform/` | 回测平台五层架构 |
| `python/ai_engine/` | AI引擎（State Hex、策略挖掘） |
| `observation_db.py` | 观察数据库 |
| `reification_agent.py` | 复现检测Agent |
