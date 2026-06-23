# AI量化多周期视角交易平台 — 核心模块详细设计 (DeepSeek版)

> 版本: v2.0 | 日期: 2026-06-06 | 模型: DeepSeek
>
> 包含: 核心模块设计 + API接口规范 + 数据库设计 + 安全风控 + 路线图 + 验收标准
>
> 配合阅读: 产品功能规格说明 DeepSeek 版、技术架构设计 DeepSeek 版

---

## 第一部分: 核心模块详细设计

### 1. 策略生成引擎 (StrategyGenerator)

**模块路径**: `pipeform/generator/`

```
pipeform/generator/
├── __init__.py
├── strategy_parser.py      # 自然语言 → 策略骨架 (NL→JSON)
├── code_generator.py       # 策略骨架 → Python代码
├── template_library.py     # 已验证策略模板库
└── strategy_validator.py   # 策略语法校验 + 快速回测
```

#### 1.1 策略解析流程

```python
# pipeform/generator/strategy_parser.py

@dataclass
class StrategySpec:
    """策略规格 — LLM输出的中间表示"""
    strategy_type: str       # "squeeze_breakout" | "ma_cross" | ...
    name: str
    timeframe: str           # "M15" | "H1" | "H4" | "D1"
    symbols: List[str]       # ["GER40", "US30", ...]
    
    # 入场条件
    entry_indicators: List[str]    # ["bb_width", "sr_range", "adx"]
    squeeze_threshold: float       # ADX上限 (如 12.0)
    anchor_range_min_pct: float    # anchor最小百分比 (如 0.50)
    
    # 过滤条件
    filter_timeframes: List[str]   # ["H1", "H4"]
    trend_filter_enabled: bool
    confirmation_bars: int         # 突破后确认bar数 (如1)
    
    # 出场规则
    exit_rules: List[str]          # ["fixed_hold_5bar", "structure_stop"]
    stop_loss_pips: float          # 止损点数
    take_profit_ratio: float       # 盈亏比 (如3.0)
    
    # 元数据
    cooldown_bars: int = 5
    max_slippage_pips: int = 10

class StrategyParser:
    """LLM驱动的策略解析"""
    
    def parse(self, user_input: str) -> StrategySpec:
        """
        输入: "M15收缩后做空DAX, H1趋势过滤, 止损80点"
        输出: StrategySpec对象
        """
        # 调用LLM Gateway提取结构化参数
        llm = LLMGateway()
        spec_json = llm.extract_strategy(user_input)
        spec = StrategySpec(**spec_json)
        
        # 参数补全 — 对未指定的参数使用默认值
        spec = self._fill_defaults(spec)
        
        # 验证 — 检查参数合法性
        self._validate(spec)
        
        return spec
```

#### 1.2 代码生成模板

```python
# pipeform/generator/templates/squeeze_breakout.py.template

class {StrategyName}(BaseStrategy):
    """{Description}
    
    此代码由AI生成, 请验证后使用。
    生成时间: {GeneratedAt}
    """
    
    PARAMS = {Params}
    
    def setup_detection(self, df: pd.DataFrame) -> pd.DataFrame:
        """收缩检测 — 计算squeeze_score"""
        df['bb_width'] = SqueezeDetector.compute_bb_width(df['close'])
        df['sr_range'] = SqueezeDetector.compute_sr_range(df['high'], df['low'], df['close'])
        df['adx'] = SqueezeDetector.compute_adx(df['high'], df['low'], df['close'])
        df['squeeze_score'] = (
            (df['bb_width'] <= df['bb_width'].expanding(30).quantile(0.20)).astype(int) +
            (df['sr_range'] <= df['sr_range'].expanding(30).quantile(0.20)).astype(int) +
            (df['adx'] < {max_adx}).astype(int)
        )
        return df
    
    def trend_filter(self, df, h1_df, h4_df) -> pd.Series:
        """趋势过滤 — as-of对齐的多周期趋势"""
        # 使用pd.merge_asof防未来函数
        aligned = pd.merge_asof(
            df[['timestamp']].sort_values('timestamp'),
            h1_df[['timestamp', 'adx', 'trend']].sort_values('timestamp'),
            on='timestamp', direction='backward'
        )
        return aligned['trend']
    
    def breakout_check(self, df, setups) -> List[BreakoutSignal]:
        """突破检测 + 确认"""
        signals = []
        for setup in setups:
            # 突破检测
            if self._is_breakout(df, setup):
                # 等待确认bar
                if self._wait_confirmation(df, setup):
                    signals.append(BreakoutSignal(...))
        return signals
    
    def exit_logic(self, trade, current_bar) -> ExitDecision:
        """出场规则"""
        if trade.exit_rule == "fixed_hold_5bar":
            return ExitDecision.EXIT if trade.bars_held >= 5 else ExitDecision.HOLD
        elif trade.exit_rule == "structure_stop":
            return self._check_structure_stop(trade, current_bar)
        elif trade.exit_rule.startswith("1r_partial"):
            return self._check_1r_partial(trade, current_bar)
```

### 2. 多Agent辩论引擎 (DebateOrchestrator)

**模块路径**: `pipeform/debate/`

```
pipeform/debate/
├── orchestrator.py      # 辩论编排核心
├── agent_registry.py    # Agent注册表
├── consensus.py         # 共识分析引擎
├── report_schema.py     # AgentReport标准格式
└── visualization.py     # 辩论结果可视化
```

#### 2.1 Agent基类

```python
# pipeform/agents/base.py

@dataclass
class AgentReport:
    """Agent标准输出 — 所有Agent必须实现此接口"""
    agent_id: str
    asset_class: str
    report_date: datetime
    
    # 核心指标
    total_setups: int = 0
    unique_events: int = 0
    net_win_rate: float = 0.0
    net_expectancy_pct: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_pct: float = 0.0
    
    # Walk-Forward
    train_expectancy_pct: float = 0.0
    val_expectancy_pct: float = 0.0
    test_expectancy_pct: float = 0.0
    test_sample_n: int = 0
    
    # Agent判断
    confidence: str = "low"
    recommendation: str = "数据不足,无法判断"
    limitations: List[str] = None
    
    # 原始数据引用
    raw_data_ref: str = ""

class BaseAgent(ABC):
    """Agent基类 — 所有周期/策略Agent继承此类"""
    
    def __init__(self, agent_id: str, asset_class: str):
        self.agent_id = agent_id
        self.asset_class = asset_class
    
    @abstractmethod
    def get_data(self) -> Dict[str, pd.DataFrame]:
        """获取分析所需数据"""
        pass
    
    @abstractmethod
    def analyze(self, force_refresh=False) -> AgentReport:
        """执行分析, 返回标准化报告"""
        pass
    
    @abstractmethod
    def get_claims(self) -> List[Dict]:
        """
        获取Agent的核心论点, 用于辩论。
        每一条论点必须有数据支持。
        """
        pass
```

#### 2.2 辩论编排流程

```python
# pipeform/debate/orchestrator.py

class DebateOrchestrator:
    """
    辩论编排器
    
    参考: TradingAgents的多空研究员辩论 + sudo-trade的牛熊辩论裁判模式
    我们的创新: 不同周期的Agent互相质疑, 而非单周期内的牛熊辩论
    """
    
    def debate(self, topic: str, agents: List[BaseAgent]) -> DebateResult:
        """执行一轮辩论"""
        
        # Step 1: 各Agent产出独立报告
        reports = {}
        for agent in agents:
            reports[agent.agent_id] = agent.analyze()
        
        # Step 2: 交叉验证
        cross_checks = self._cross_validate(reports)
        
        # Step 3: 识别共识
        consensus = ConsensusEngine.find_consensus(reports)
        
        # Step 4: 标记分歧
        disagreements = ConsensusEngine.find_disagreements(reports)
        
        # Step 5: 生成推荐
        recommendation = self._make_recommendation(consensus, disagreements)
        
        return DebateResult(
            topic=topic,
            agents=[a.agent_id for a in agents],
            reports=reports,
            cross_checks=cross_checks,
            consensus=consensus,
            disagreements=disagreements,
            recommendation=recommendation,
        )
    
    def _cross_validate(self, reports):
        """交叉验证: 对比各Agent的关键指标"""
        checks = []
        agent_ids = list(reports.keys())
        for i in range(len(agent_ids)):
            for j in range(i+1, len(agent_ids)):
                a1, a2 = reports[agent_ids[i]], reports[agent_ids[j]]
                # 检查Test段期望是否同方向
                same_direction = (a1.test_expectancy_pct > 0) == (a2.test_expectancy_pct > 0)
                checks.append({
                    "agents": [a1.agent_id, a2.agent_id],
                    "same_direction": same_direction,
                    "expectancy_diff": abs(a1.test_expectancy_pct - a2.test_expectancy_pct),
                })
        return checks
```

#### 2.3 辩论输出示例

```yaml
debate_id: "debate_20260606_index_fx_short"
topic: "股指/外汇的做空策略验证"
timestamp: "2026-06-06T15:00:00Z"

consensus:
  - "H1和M15都支持GER40做空方向, 数据一致"
  - "H1 v5的Test期望+0.299%, 具备统计可信度"
  - "建议H1 v5立即进入模拟盘, M15等Phase 2完整回测"
  
disagreements:
  - topic: "M15能否独立产生交易信号"
    r_h1_claim: "M15 Phase1只有密度数据, 没有完整回测期望值"
    r_m15_claim: "但M15共振25.2%, density 18.7%, 两者都达到通过标准"
    resolution: "同意M15进入Phase 2完整回测, 但不跳过Phase 2直接实盘"

risk_flags:
  - "H1 Test段58笔样本, 统计显著性中等"
  - "当前策略未在极端行情(2020/2022)中测试"
  - "消息面驱动行情会被ADX过滤, 可能错过趋势行情"
```

### 3. 风控Agent (RiskAgent)

```python
# pipeform/agents/risk_agent.py
# 参考: CryptoTrader AI的硬编码风控门 (不依赖LLM)

class RiskAgent:
    """
    风控Agent — 所有决策用确定性规则, 不依赖LLM
    
    设计理念 (来自CryptoTrader AI):
    "风控是最后一道防线, 不能用可能出错的LLM来做"
    """
    
    # 风控规则 (可配置)
    RISK_RULES = [
        {"name": "max_total_position", "check": lambda p: p.total_exposure < 0.30, "limit_pct": 30},
        {"name": "max_symbol_position", "check": lambda p, s: p.symbol_exposure(s) < 0.10, "limit_pct": 10},
        {"name": "max_daily_loss", "check": lambda p: p.daily_pnl > -0.05, "limit_pct": 5},
        {"name": "max_consecutive_losses", "check": lambda p: p.consecutive_losses < 5, "limit": 5},
        {"name": "strategy_health_green", "check": lambda p: p.strategy_health == "GREEN"},
        {"name": "no_news_blackout", "check": lambda t: not is_near_economic_event(t)},
    ]
    
    def approve_trade(self, signal: TradeSignal, portfolio: Portfolio) -> RiskDecision:
        """
        审批交易 — 所有规则通过才放行
        
        Returns:
            RiskDecision: APPROVED / REJECTED / MODIFIED
        """
        for rule in self.RISK_RULES:
            if not rule["check"](portfolio, signal.symbol):
                return RiskDecision(
                    status="REJECTED",
                    reason=f"{rule['name']}: 超过限制 {rule.get('limit_pct', rule.get('limit'))}",
                )
        return RiskDecision(status="APPROVED", reason="所有风控规则通过")
    
    def check_health(self, strategy_id: str) -> HealthStatus:
        """策略健康度检查 — 三色灯"""
        recent_perf = self._get_recent_performance(strategy_id)
        backtest_exp = self._get_backtest_expectancy(strategy_id)
        
        deviation = abs(recent_perf - backtest_exp) / abs(backtest_exp) if backtest_exp != 0 else 1.0
        
        if deviation < 0.20:
            return HealthStatus.GREEN
        elif deviation < 0.50:
            return HealthStatus.YELLOW
        else:
            return HealthStatus.RED
    
    def check_decay(self, strategy_id: str, window_days=90) -> bool:
        """检测策略是否在衰减"""
        perf_trend = self._get_performance_trend(strategy_id, window_days)
        # 如果最近30天净期望比前60天下降>50%, 判定为衰减
        return perf_trend.recent_expectancy < perf_trend.prior_expectancy * 0.5
```

### 4. 实时市场分析模块

#### 4.1 收缩状态扫描器

```python
# pipeform/observation/squeeze_scanner.py

class SqueezeScanner:
    """
    多周期收缩状态扫描器
    
    功能:
    - 每15分钟扫描14个品种的M15/H1/H4收缩状态
    - 检测多周期共振
    - 记录到观察数据库
    """
    
    def scan(self, symbols, timeframes=["M15", "H1", "H4"]) -> ScanReport:
        """单次扫描"""
        results = {}
        for symbol in symbols:
            symbol_results = {}
            for tf in timeframes:
                df = DataPipeline().fetch(symbol, [tf], lookback_days=30)[tf]
                latest = df.iloc[-1]
                symbol_results[tf] = {
                    "squeeze_score": self._compute_squeeze_score(latest),
                    "adx": latest.get("adx", None),
                    "trend": latest.get("trend", "neutral"),
                }
            # 共振检查
            symbol_results["resonance"] = self._check_resonance(symbol_results)
            results[symbol] = symbol_results
        return ScanReport(results=results)

    def _check_resonance(self, symbol_results):
        """检查多周期共振"""
        h1 = symbol_results.get("H1", {})
        h4 = symbol_results.get("H4", {})
        m15 = symbol_results.get("M15", {})
        
        if (h1.get("squeeze_score", 0) >= 2 and 
            h4.get("squeeze_score", 0) >= 2):
            return "H1+H4共振收缩 ⬆️⬆️"
        elif h1.get("squeeze_score", 0) >= 2:
            return "H1收缩 ⬆️"
        elif m15.get("squeeze_score", 0) >= 3:
            return "M15收缩 ⚡"
        else:
            return "无收缩"
```

---

## 第二部分: API 接口规范

### 1. ZeroMQ 通信协议 (MT5 ↔ Python)

#### 1.1 PUB/SUB 行情格式

```json
{
  "symbol": "GER40",
  "bid": 24910.5,
  "ask": 24912.0,
  "time": 1717689600,
  "spread": 1.5
}
```

#### 1.2 REQ/REP 交易指令格式

**请求**:
```json
{
  "action": "ORDER_SEND",
  "symbol": "GER40",
  "type": "OP_SELL",
  "volume": 0.01,
  "price": 24910.5,
  "sl": 24990.5,
  "tp": 24830.5,
  "comment": "pipeform-squeeze-v5",
  "max_slippage_points": 10
}
```

**响应**:
```json
{
  "status": "FILLED",
  "ticket": 90519236,
  "filled_price": 24910.5,
  "slippage_points": 0.0,
  "error": ""
}
```

### 2. FastAPI REST 接口 (Web后端)

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/strategy/create` | 从自然语言创建策略 |
| POST | `/api/strategy/{id}/backtest` | 运行回测 |
| GET | `/api/strategy/{id}/report` | 获取回测报告 |
| GET | `/api/strategy/list` | 策略列表 |
| POST | `/api/debate/start` | 发起Agent辩论 |
| GET | `/api/debate/{id}/result` | 获取辩论结果 |
| GET | `/api/scan/status` | 当前扫描状态 |
| GET | `/api/scan/history?date=2026-06-06` | 历史扫描记录 |
| GET | `/api/report/daily?date=2026-06-06` | 日报 |
| GET | `/api/report/weekly?start=2026-06-01` | 周报 |
| GET | `/api/health` | 系统健康检查 |

### 3. Agent内部接口

每个Agent必须实现:

```python
def get_data() -> Dict[str, pd.DataFrame]
def analyze(force_refresh=False) -> AgentReport  
def get_claims() -> List[Dict]
```

每个Agent可以调用的共享服务:

```python
# 数据
DataPipeline.fetch(symbol, timeframes, days)

# 指标
SqueezeDetector.compute_bb_width(close)
SqueezeDetector.compute_sr_range(high, low, close)
SqueezeDetector.compute_adx(high, low, close, period=14)

# 回测
BacktestEngine.run(setups, events, exit_rules)
BacktestEngine.walk_forward(trades, n_folds=5)
```

---

## 第三部分: 数据库设计

### 1. SQLite 本地缓存 (`data/cache.db`)

```sql
-- 数据缓存 (替代每次MT5拉取)
CREATE TABLE data_cache (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    bar_time DATETIME NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    tick_volume BIGINT,
    spread INT,
    PRIMARY KEY (symbol, timeframe, bar_time)
);

-- 扫描记录
CREATE TABLE scan_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_time DATETIME NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    squeeze_score INT,
    adx DOUBLE,
    sr_range_pct DOUBLE,
    bb_width DOUBLE,
    pivot_range_pct DOUBLE,
    trend_align VARCHAR(20),
    is_setup BOOLEAN DEFAULT 0,
    resonance_level VARCHAR(50)
);
CREATE INDEX idx_scan_time ON scan_records(scan_time);
CREATE INDEX idx_scan_symbol ON scan_records(symbol, scan_time);

-- 模拟盘交易记录
CREATE TABLE paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_time DATETIME,
    entry_time DATETIME,
    exit_time DATETIME,
    symbol VARCHAR(20),
    direction VARCHAR(10),
    entry_price DOUBLE,
    exit_price DOUBLE,
    stop_loss DOUBLE,
    take_profit DOUBLE,
    pnl_pct DOUBLE,
    pnl_usd DOUBLE,
    exit_rule VARCHAR(50),
    strategy_id VARCHAR(50)
);
```

### 2. RDS MySQL 远端 (`rm-2zeh695s5607s218p`)

```sql
-- 策略版本管理
CREATE TABLE strategy_versions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    strategy_id VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT 'v1',
    name VARCHAR(200),
    strategy_type ENUM('squeeze_breakout','ma_cross','trend_follow','mean_reversion','state','custom'),
    asset_class ENUM('index','fx','metal','stock','crypto'),
    timeframes JSON,       -- ["H1","H4","D1"]
    symbols JSON,          -- ["GER40","US30",...]
    params JSON,           -- {"max_adx":12,"min_anchor_range_pct":0.50,...}
    status ENUM('draft','research','paper_trading','live','retired') DEFAULT 'draft',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_strategy_version (strategy_id, version),
    INDEX idx_status (status)
);

-- Agent报告存档
CREATE TABLE agent_reports (
    id INT PRIMARY KEY AUTO_INCREMENT,
    agent_id VARCHAR(50) NOT NULL,
    report_date DATE NOT NULL,
    strategy_id VARCHAR(50),
    asset_class VARCHAR(20),
    net_win_rate DOUBLE,
    net_expectancy_pct DOUBLE,
    profit_factor DOUBLE,
    max_drawdown_pct DOUBLE,
    train_expectancy_pct DOUBLE,
    val_expectancy_pct DOUBLE,
    test_expectancy_pct DOUBLE,
    test_sample_n INT,
    confidence VARCHAR(20),
    recommendation TEXT,
    metrics_json JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_agent_date (agent_id, report_date),
    INDEX idx_strategy (strategy_id)
);

-- 辩论记录
CREATE TABLE debate_records (
    id INT PRIMARY KEY AUTOINCREMENT,
    topic VARCHAR(200),
    asset_class VARCHAR(20),
    agent_ids JSON,
    consensus JSON,
    disagreements JSON,
    recommendation TEXT,
    risk_flags JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 策略健康度日志
CREATE TABLE strategy_health_log (
    id INT PRIMARY KEY AUTOINCREMENT,
    strategy_id VARCHAR(50),
    check_date DATE,
    status ENUM('GREEN','YELLOW','RED'),
    recent_expectancy DOUBLE,
    backtest_expectancy DOUBLE,
    deviation_pct DOUBLE,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy_date (strategy_id, check_date)
);
```

---

## 第四部分: 安全与风控机制

### 1. 资金风险管理

| 层级 | 规则 | 触发动作 |
|------|------|---------|
| L1: 仓位控制 | 总仓位 < 30%总资金 | 拒绝新开仓 |
| L2: 品种分散 | 单品种 < 10%总资金 | 拒绝该品种新开仓 |
| L3: 日内止损 | 当日累计亏损 > 5%总资金 | 平掉所有仓位, 当日停交易 |
| L4: 连续亏损 | 连续5笔亏损 | 暂停该策略, 人工检查 |

### 2. 交易限额控制

```python
class PositionLimits:
    """仓位限制 — 从配置加载"""
    MAX_TOTAL_EXPOSURE = 0.30     # 总仓位不超过30%
    MAX_SYMBOL_EXPOSURE = 0.10    # 单品种不超过10%
    MAX_DAILY_LOSS = 0.05         # 日亏损不超过5%
    MAX_CONSECUTIVE_LOSSES = 5    # 连续亏损不超过5笔
    MIN_TRADE_INTERVAL_SEC = 60   # 最小交易间隔60秒
```

### 3. 系统安全防护

| 防护项 | 措施 |
|--------|------|
| API密钥 | 存 `.env` 文件, 不提交git |
| MT5密码 | 不存磁盘明文, 每次启动手动输入或从加密keyring读取 |
| ZeroMQ端口 | Windows防火墙限制, 仅允许localhost (单机部署) 或指定IP (分布式) |
| LLM API | 设置月度费用上限, 超限报警 |
| 交易确认 | 每笔真实交易需二次确认 (CLI输入"y"或Web弹窗) |
| 审计日志 | 所有交易指令记录到日志文件 + RDS |

### 4. 异常交易监控

```python
class AnomalyDetector:
    """异常交易检测"""
    
    def check(self, signal: TradeSignal) -> bool:
        # 1. 频率检查: 同一品种60秒内不能重复下单
        if self._is_duplicate(signal):
            return False, "60秒内重复信号"
        # 2. 量级检查: 单笔不超过最大仓位
        if signal.volume > self.max_position:
            return False, f"超过最大仓位 {self.max_position}"
        # 3. 价格检查: 与市场价偏差不超过2%
        market_price = self._get_market_price(signal.symbol)
        if abs(signal.price - market_price) / market_price > 0.02:
            return False, "价格偏差超过2%"
        return True, "OK"
```

---

## 第五部分: 分阶段实施路线图

### Phase 1: 单机工作站 (第1-4周) — 当前阶段

**目标**: 将现有v5引擎+模拟盘扫描重构为模块化 `pipeform` 项目

| 周 | 任务 | 验收标准 |
|----|------|---------|
| W1 | 创建 `pipeform/` 目录结构, 抽离 DataPipeline + SignalDetector | 现有v5回测脚本能通过新模块运行 |
| W2 | 重构 BacktestEngine + ReportBuilder, 定义 BaseAgent | `python -m pipeform.cli backtest` 能跑通 |
| W3 | 实现 DebateOrchestrator v0.1 (对比2个Agent) | `python -m pipeform.cli debate` 输出辩论报告 |
| W4 | CLI入口完成, 接入日报模拟盘扫描 | 完整的 `pipeform scan/backtest/debate/report` 可用 |

**不引入**: Web前端、LLM策略生成、实盘执行

### Phase 2: AI赋能 (第5-8周)

**目标**: 引入LLM策略生成 + Web仪表盘

| 周 | 任务 | 验收标准 |
|----|------|---------|
| W5 | LLM Gateway + StrategyParser | 输入"M15收缩做空DAX", 输出可运行策略代码 |
| W6 | M15 Phase 2 完整回测 | M15的Walk-Forward三阶段报告 |
| W7 | FastAPI后端 + 基础Web仪表盘 | 浏览器访问能看到策略列表+回测报告 |
| W8 | 整合多Agent + 策略生命周期管理 | 策略健康度三色灯, 自动衰减检测 |

### Phase 3: 平台化 (第9-16周)

**目标**: 多用户, 实盘对接, 策略市场

| 周 | 任务 | 验收标准 |
|----|------|---------|
| W9-10 | MT5 ZeroMQ实盘对接 | 模拟盘下单→MT5执行成功 |
| W11-12 | 实时风控上线 | 所有风控规则在模拟盘中验证 |
| W13-14 | 策略市场 + 自动化因子挖掘 (RD-Agent启发) | LLM自动生成的因子通过回测验证 |
| W15-16 | 部署到阿里云ECS, 24h自动运行 | ECS上稳定运行72h+无中断 |

### Phase 4: 扩展 (第17周+)

- 股票 D1/W1 Agent
- 多账户管理
- 移动端App
- 开放API给第三方

---

## 第六部分: 验收标准

### 1. 策略生成

| 编号 | 标准 | 验证方法 |
|------|------|---------|
| GEN-01 | 从自然语言生成策略成功率 > 80% (20个典型输入中≥16个成功) | 手动测试20个不同风格输入 |
| GEN-02 | LLM提取的策略参数准确率 > 90% | 对比人工标注 |
| GEN-03 | 代码生成后导入无语法错误 | `python -m py_compile` 通过 |

### 2. 回测引擎

| 编号 | 标准 | 验证方法 |
|------|------|---------|
| BT-01 | 单品种365天回测 ≤ 30秒 | 计时 |
| BT-02 | 无未来函数泄漏 | 专用检测脚本: 使用未来数据时抛出异常 |
| BT-03 | Walk-Forward三段自动分割正确 | Train(60%) + Val(20%) + Test(20%), 时间不重叠 |
| BT-04 | 出场规则对比正确 | structure_stop/1r_partial的PnL统计与逐笔核算一致 |

### 3. Agent辩论

| 编号 | 标准 | 验证方法 |
|------|------|---------|
| DB-01 | 两个Agent产生报告后能生成共识/分歧 | 手动构造两个报告的差异 |
| DB-02 | 样本不足(<30)时自动降权 | Test段<30笔的报告标注"统计不可信" |
| DB-03 | 辩论输出包含每个Agent的数据引用 | 检查输出确保有具体数字而非泛泛意见 |

### 4. 模拟盘扫描

| 编号 | 标准 | 验证方法 |
|------|------|---------|
| SC-01 | 14品种单次扫描 ≤ 10秒 | 计时 |
| SC-02 | 扫描结果与手工计算一致 | 取3个品种手工计算squeeze_score对照 |
| SC-03 | 日报在每天指定时间自动生成 | 检查文件创建时间 |

### 5. 安全风控

| 编号 | 标准 | 验证方法 |
|------|------|---------|
| RK-01 | 超过仓位限制的交易被拒绝 | 模拟超限后检查日志 |
| RK-02 | 连续5笔亏损后自动暂停 | 模拟连续亏损 |
| RK-03 | ZeroMQ断线后30秒内自动告警 | 模拟断线 |

---

## 附录: 项目目录结构

```
MT5_AI_Trading/
├── pipeform/                     # 新平台核心
│   ├── __init__.py
│   ├── cli.py                    # CLI入口
│   ├── config.py                 # 全局配置
│   │
│   ├── engine/                   # 核心引擎 (继承v5)
│   │   ├── data_pipeline.py      # 数据获取
│   │   ├── signal_detector.py    # 收缩信号检测
│   │   ├── backtest_engine.py    # 回测引擎
│   │   └── report_builder.py     # 报告生成
│   │
│   ├── agents/                   # Agent层
│   │   ├── base.py               # BaseAgent 基类
│   │   ├── agent_h1_squeeze.py   # H1收缩突破Agent
│   │   ├── agent_m15_squeeze.py  # M15收缩突破Agent
│   │   └── agent_risk.py         # 风控Agent
│   │
│   ├── debate/                   # 辩论引擎
│   │   ├── orchestrator.py       # 辩论编排
│   │   └── consensus.py          # 共识分析
│   │
│   ├── generator/                # 策略生成
│   │   ├── strategy_parser.py    # NL→策略骨架
│   │   └── code_generator.py     # 骨架→代码
│   │
│   ├── observation/              # 模拟盘观察
│   │   ├── scanner.py            # 收缩状态扫描
│   │   └── reporter.py           # 日报/周报
│   │
│   ├── ai/                       # AI/LLM层
│   │   └── llm_gateway.py        # 统一LLM接入
│   │
│   └── bridge/                   # 外部桥接
│       └── mt5_bridge.py         # MT5 ZeroMQ桥
│
├── python/                       # 现有基础设施 (保持)
│   ├── analytics/                # 指标计算
│   ├── backtest_platform/        # MT5 API
│   └── ...
│
├── docs/
│   ├── platform/                 # 新平台文档
│   │   ├── PRODUCT_SPEC_DeepSeek.md
│   │   ├── TECH_ARCHITECTURE_DeepSeek.md
│   │   └── MODULE_DESIGN_DeepSeek.md  # 本文件
│   ├── AGENTS.md                 # Agent经验记录
│   └── FINAL_DELIVERY_v5.md
│
├── data/                         # 本地数据缓存
│   └── cache.db                  # SQLite缓存
│
├── reports/                      # 报告输出
│   └── squeeze/
│
└── archive/                      # 归档的旧代码
    ├── v3/
    ├── v4/
    └── scripts/
```
