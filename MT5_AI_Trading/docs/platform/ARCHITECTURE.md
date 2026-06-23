# AI量化平台技术架构文档

> 版本: v1.0 | 日期: 2026-06-06 | 状态: 草案
>
> 配合需求文档 `REQUIREMENTS.md` 阅读。

---

## 一、技术选型

### 1.1 语言与生态

| 层级 | 语言 | 理由 |
|------|------|------|
| **核心引擎** | Python 3.12 | 量化圈通用语言, pandas/numpy生态成熟, MT5 Python API原生支持 |
| **Web后端** | Python (FastAPI) | 与核心引擎同语言, 减少跨语言调用开销 |
| **Web前端** | TypeScript (React) | 现代仪表盘标准, 但Phase 1用CLI暂不需要 |
| **数据库** | SQLite (本地) + MySQL 8.0 (远端RDS) | SQLite存缓存, RDS存结构化策略数据 |

**为什么不全用Rust?**

对比了OpenFinClaw的Rust方案和nautilus_trader:
- **优点**: 性能极致, 类型安全
- **缺点**: 人才难找, 开发效率低, 与MT5 Python API不兼容
- **结论**: 当前阶段Python完全满足需求 (回测瓶颈在数据量而非语言), 后续如果涉及高频Tick级再考虑Rust重写底层

### 1.2 不重造轮子的依赖

| 组件 | 选型 | 理由 |
|------|------|------|
| **回测引擎** | 自研 (已有v5) | 需要as-of对齐、多Agent辩论、State视角, 现有引擎无法满足 |
| **技术指标** | `ta-lib` + 自研 | ADX/BB/SR等核心指标自研, 通用指标用ta-lib |
| **数据源** | MT5 Python API | 用户已有MT5终端, 数据质量和实时性最佳 |
| **LLM调用** | OpenAI API / 本地模型 | 策略生成、辩论合成需要LLM |
| **任务调度** | APScheduler | 定时扫描、日报生成 |
| **配置管理** | YAML + Pydantic | 策略参数、品种白名单等结构化配置 |
| **日志** | loguru | 结构化日志, 支持按模块/级别过滤 |

---

## 二、系统架构

### 2.1 总体分层

```
┌─────────────────────────────────────────────────────────────┐
│                    用户界面层 (UI Layer)                      │
│  CLI: pipeform scan/backtest/debate/summary                  │
│  Web Dashboard (Phase 2): React + FastAPI                     │
├─────────────────────────────────────────────────────────────┤
│                    调度层 (Orchestration Layer)               │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────┐  │
│  │ Task         │ │ Debate       │ │ Strategy Lifecycle   │  │
│  │ Scheduler    │ │ Orchestrator │ │ Manager              │  │
│  │ (定时/事件)   │ │ (Agent调度)   │ │ (版本/衰减/退役)      │  │
│  └─────────────┘ └──────────────┘ └──────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    核心引擎层 (Core Engine Layer)              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Pipeform Engine (继承v5架构)                │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │   │
│  │  │ Data     │ │ Signal   │ │ Backtest │ │ Report  │ │   │
│  │  │ Fetcher  │ │ Detector │ │ Engine   │ │ Builder │ │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Agent Framework (多Agent框架)               │   │
│  │  Agent_H1_Squeeze │ Agent_M15_Squeeze │ Agent_D1_Stocks │   │
│  │  Agent_W1_Stocks  │ Agent_State_Short │ ...             │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    数据层 (Data Layer)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ MT5 API  │ │ RDS MySQL│ │ SQLite   │ │ File Cache   │   │
│  │ (实时/历史)│ │ (策略数据) │ │ (本地缓存) │ │ (feather/pkl)│   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
MT5终端                    回测引擎                   Agent层
────────                   ────────                  ───────
OHLCV bars ──→ _fetch_from_mt5() ──→ DataFetcher ──→ Agent.get_data()
                 │                                       │
                 ▼                                       ▼
            [SQLite缓存]                          compute_squeeze()
            [feather快照]                         compute_trend()
                                                  run_backtest()
                                                      │
                                                      ▼
                                                  Agent.report()
                                                      │
                                                      ▼
                                               Debate.Orchestrator
                                                      │
                                                  ┌───┴───┐
                                                  ▼       ▼
                                             共识报告  异议标记
                                                  │
                                                  ▼
                                          模拟盘 / 用户决策
```

---

## 三、核心模块设计

### 3.1 Pipeform Engine (继承v5)

**现状**: `squeeze_multi_timeframe_research_v5.py` 已经是事实上的引擎核心。

**重构方向**: 将v5拆分为可复用的模块:

```python
# pipeform/engine/data.py
class DataFetcher:
    """数据获取: MT5 → DataFrame → Cache"""
    def fetch(symbol, timeframes, lookback_days) -> Dict[str, pd.DataFrame]
    def cache_to_sqlite(df, key) -> None
    def load_from_cache(symbol, tf, start, end) -> pd.DataFrame

# pipeform/engine/signal.py  
class SqueezeDetector:
    """收缩检测: 继承SqueezeObserver的逻辑"""
    def compute_bb_width(close) -> pd.Series
    def compute_sr_range(high, low, close) -> pd.Series
    def compute_adx(high, low, close, period=14) -> pd.Series
    def compute_squeeze_score(df) -> pd.DataFrame  # 返回带squeeze_score的df
    def find_setups(df, params) -> List[SqueezeSetup]

# pipeform/engine/backtest.py
class BacktestEngine:
    """回测引擎: Walk-Forward + 多出场规则"""
    def run_trade_backtest(setups, events, exit_rules) -> List[Trade]
    def walk_forward_analysis(trades, n_folds=5) -> dict
    def compute_metrics(trades, exit_rule_filter=None) -> MetricsReport

# pipeform/engine/report.py
class ReportBuilder:
    """报告生成: Markdown + JSON"""
    def build_markdown(metrics, trades) -> str
    def build_json(metrics, trades) -> dict
    def compare_exit_rules(results) -> str  # 出场规则对比表
```

### 3.2 Agent Framework

**设计原则**: 每个Agent是独立的Python模块, 实现统一接口:

```python
# pipeform/agents/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class AgentReport:
    """每个Agent的标准输出"""
    agent_id: str           # "h1_squeeze_v5"
    asset_class: str        # "index_fx"
    timeframes: List[str]   # ["H1", "H4", "D1"]
    symbols: List[str]      # ["GER40", "US30", ...]
    
    # 回测统计
    total_setups: int
    unique_events: int
    net_win_rate: float     # 扣成本后
    net_expectancy: float   # 净期望(%)
    sharpe_ratio: float
    max_drawdown: float
    
    # Walk-Forward三段
    train_expectancy: float
    val_expectancy: float
    test_expectancy: float
    test_sample_n: int      # Test段样本量
    
    # Agent自身的判断
    confidence: str         # "high" / "medium" / "low"
    recommendation: str     # "推荐" / "观望" / "不推荐"
    limitations: List[str]  # 自己发现的局限性
    
    # 原始数据引用
    raw_report_path: str    # 完整回测报告路径


class BaseAgent(ABC):
    """Agent基类"""
    
    @abstractmethod
    def get_data(self) -> Dict[str, pd.DataFrame]:
        """获取数据"""
        pass
    
    @abstractmethod
    def analyze(self) -> AgentReport:
        """执行分析, 返回标准报告"""
        pass
    
    @abstractmethod
    def get_claims(self) -> List[str]:
        """Agent的核心论点 (用于辩论)"""
        pass
```

**已有Agent实现**:

| Agent | 文件 | 状态 |
|-------|------|------|
| Agent_H1_Squeeze_v5 | `squeeze_multi_timeframe_research_v5.py` | ✅ 需适配接口 |
| Agent_M15_Squeeze | `squeeze_m15_phase1_diagnosis.py` | ✅ Phase1完成 |
| Agent_State_Short | `reports/strategy_mining_report_*.md` (手动) | ⚠️ 需整合 |

### 3.3 辩论编排器 (Debate Orchestrator)

```python
# pipeform/debate/orchestrator.py

class DebateOrchestrator:
    """多Agent辩论编排"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
    
    def register(self, agent: BaseAgent):
        """注册Agent"""
        self.agents[agent.agent_id] = agent
    
    def debate(self, asset_class: str, topic: str) -> DebateResult:
        """
        对特定资产类+主题发起辩论
        
        Args:
            asset_class: "index_fx" / "stocks" / "metals"
            topic: "squeeze_breakout" / "trend_direction" / "optimal_timeframe"
        
        Returns:
            DebateResult: 含共识/异议/各Agent论据
        """
        relevant_agents = [a for a in self.agents.values() 
                          if a.asset_class == asset_class]
        
        # 1. 各Agent产生报告
        reports = {a.agent_id: a.analyze() for a in relevant_agents}
        
        # 2. 交叉验证
        # 对比Walk-Forward Test段期望
        # 检查统计显著性 (样本量)
        # 识别数据冲突
        
        # 3. 生成共识/异议
        consensus = self._build_consensus(reports)
        disagreements = self._find_disagreements(reports)
        
        return DebateResult(
            topic=topic,
            asset_class=asset_class,
            agent_reports=reports,
            consensus=consensus,
            disagreements=disagreements,
            recommendation=self._make_recommendation(consensus, disagreements)
        )

    def _build_consensus(self, reports) -> List[str]:
        """找出所有Agent一致同意的点"""
        pass
    
    def _find_disagreements(self, reports) -> List[Disagreement]:
        """找出Agent之间的分歧"""
        pass
```

### 3.4 模拟盘观测器

**现状**: `run_v5_simulation.py` + `run_v5_daily_summary.py` + `observation_db.py`

**整合方向**:

```python
# pipeform/observation/scanner.py
class SimulationScanner:
    """模拟盘扫描 (代替run_v5_simulation.py)"""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.fetcher = DataFetcher()
        self.detector = SqueezeDetector()
    
    def scan_once(self) -> ScanReport:
        """单次扫描所有品种"""
        pass
    
    def scan_continuous(self, interval_minutes=15):
        """持续扫描模式"""
        pass

# pipeform/observation/reporter.py  
class DailyReporter:
    """日报/周报生成"""
    
    def generate_daily(self, date=None) -> str:
        """生成日报Markdown"""
        pass
    
    def generate_weekly(self, week_start, week_end) -> str:
        """生成周报, 含绩效归因"""
        pass
```

### 3.5 策略生命周期管理

```python
# pipeform/lifecycle/manager.py
@dataclass
class StrategyVersion:
    strategy_id: str
    version: str          # "v5"
    params: dict          # {"max_adx": 12, "min_range": 0.50}
    backtest_result: AgentReport
    status: str           # "active" / "paper_trading" / "retired"
    created_at: datetime
    last_evaluated_at: datetime

class StrategyLifecycleManager:
    """策略生命周期管理"""
    
    def register(self, strategy: StrategyVersion):
        """注册新策略版本"""
        pass
    
    def evaluate_health(self, strategy_id) -> HealthStatus:
        """
        健康度评估:
        - 模拟盘vs回测偏差
        - Walk-Forward Test段稳定性
        - 参数敏感性
        """
        pass
    
    def check_decay(self, strategy_id) -> bool:
        """检测策略是否衰减"""
        pass
```

---

## 四、数据库设计

### 4.1 SQLite (本地缓存)

```sql
-- 数据缓存
CREATE TABLE data_cache (
    symbol VARCHAR(20),
    timeframe VARCHAR(5),
    bar_time DATETIME,
    open FLOAT, high FLOAT, low FLOAT, close FLOAT, volume BIGINT,
    PRIMARY KEY (symbol, timeframe, bar_time)
);

-- 扫描记录
CREATE TABLE scan_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_time DATETIME,
    symbol VARCHAR(20),
    squeeze_score INT,
    adx FLOAT,
    anchor_range_pct FLOAT,
    trend_align VARCHAR(20),
    is_setup BOOLEAN
);
```

### 4.2 RDS MySQL (远端, 阿里云 rm-2zeh695s5607s218p)

```sql
-- 策略版本
CREATE TABLE strategy_versions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    strategy_id VARCHAR(50),
    version VARCHAR(20),
    agent_id VARCHAR(50),
    params JSON,
    asset_class VARCHAR(20),
    symbols JSON,
    backtest_metrics JSON,
    status ENUM('research', 'paper_trading', 'live', 'retired'),
    created_at DATETIME,
    updated_at DATETIME,
    INDEX idx_status (status),
    INDEX idx_agent (agent_id)
);

-- Agent报告
CREATE TABLE agent_reports (
    id INT PRIMARY KEY AUTO_INCREMENT,
    agent_id VARCHAR(50),
    report_date DATE,
    net_win_rate FLOAT,
    net_expectancy FLOAT,
    train_expectancy FLOAT,
    val_expectancy FLOAT,
    test_expectancy FLOAT,
    test_sample_n INT,
    report_json JSON,
    created_at DATETIME,
    INDEX idx_agent_date (agent_id, report_date)
);

-- 辩论记录
CREATE TABLE debate_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    topic VARCHAR(200),
    asset_class VARCHAR(20),
    consensus JSON,
    disagreements JSON,
    recommendation VARCHAR(50),
    created_at DATETIME
);

-- 模拟盘交易记录
CREATE TABLE paper_trades (
    id INT PRIMARY KEY AUTO_INCREMENT,
    strategy_id VARCHAR(50),
    signal_time DATETIME,
    symbol VARCHAR(20),
    direction ENUM('LONG', 'SHORT'),
    entry_price FLOAT,
    exit_price FLOAT,
    pnl_pct FLOAT,
    exit_rule VARCHAR(50),
    created_at DATETIME,
    INDEX idx_strategy_date (strategy_id, signal_time)
);
```

---

## 五、接口规范

### 5.1 Agent标准接口

每个Agent必须输出:

```yaml
# agent_report.yaml (Agent标准输出格式)
agent_id: "h1_squeeze_v5"
asset_class: "index_fx"
report_date: "2026-06-06"

metrics:
  total_setups: 1309
  unique_events: 305
  gross_win_rate: 0.695
  net_win_rate: 0.685
  net_expectancy_pct: 0.271
  profit_factor: 1.85
  max_drawdown_pct: 8.2

walk_forward:
  train:
    expectancy_pct: 0.205
    sample_n: 198
  validation:
    expectancy_pct: 0.424
    sample_n: 49
  test:
    expectancy_pct: 0.299
    sample_n: 58

exit_rules:
  fixed_hold_5bar:
    net_win_rate: 0.685
    net_expectancy_pct: 0.271
  structure_stop:
    net_win_rate: 0.620
    net_expectancy_pct: 0.185
  1r_partial_trail:
    net_win_rate: 0.653
    net_expectancy_pct: 0.234

recommendation: "推荐进入模拟盘"
confidence: "high"
limitations:
  - "Test段仅58个样本, 统计显著性中等"
  - "未测试2022年以前市场环境"
  - "消息面驱动的极端行情会被ADX过滤, 但无法识别为利空/利多"
```

### 5.2 辩论结果标准接口

```yaml
# debate_result.yaml
debate_id: "debate_20260606_index_fx_squeeze"
topic: "股指/外汇的收缩突破策略"
asset_class: "index_fx"

agents:
  - agent_id: "h1_squeeze_v5"
    recommendation: "推荐"
    test_expectancy_pct: 0.299
  - agent_id: "m15_squeeze_phase1"
    recommendation: "Phase1通过, 建议Phase2"
    resonance_pct: 0.252

consensus:
  - "H1收缩突破具有正期望 (Test段+0.299%), 建议进入模拟盘"
  - "M15收缩密度正常 (18.7%), 共振25.2%, 值得继续研究"
  - "GER40是核心品种 (用户实盘验证+数据支持)"

disagreements:
  - topic: "M15能否独立产生交易信号"
    agent_m15: "M15 density 18.7%说明信号充足"
    agent_h1: "但M15无完整回测, 不能给出期望值结论, 需要Phase2"

recommendation: "H1立即进入模拟盘, M15启动Phase2完整回测"
risk_flags:
  - "H1 Test段58笔样本, 如果前4周模拟盘<5笔信号, 需调整参数"
```

---

## 六、部署方案

### 6.1 开发环境 (当前)

```
[本地 Windows PC]
  ├── Python 3.12 (C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312)
  ├── MT5终端 (AvaTrade)
  ├── 项目目录: d:\qoder\csvcl - AVA\MT5_AI_Trading\
  └── RDS MySQL (阿里云, rm-2zeh695s5607s218p)
```

### 6.2 生产环境 (远期)

```
[阿里云 ECS Windows Server 2022]  (已有: iZ6w2tu6dc6tfbZ)
  ├── MT5终端 (24h运行)
  ├── Python定时任务 (APScheduler)
  ├── Web服务 (FastAPI + Nginx, 仅内网)
  └── RDS MySQL (同上)

[用户本地PC]
  └── 访问Web仪表盘 / CLI远程连接
```

---

## 七、与竞品的继承与差异化

### 7.1 我们继承/借鉴的

| 来源 | 借鉴什么 | 如何整合 |
|------|----------|----------|
| **Qlib** | 回测引擎设计、交易成本建模、PIT数据对齐 | 回测引擎接口设计参考 |
| **RD-Agent** | R&D Loop (假设→实现→回测→反馈) | 策略自动生成的循环逻辑 |
| **ContestTrade** | 多Agent竞赛、内部排名机制 | 辩论编排器的竞赛维度 |
| **Freqtrade** | 定时扫描、Telegram推送、Web UI | 模拟盘观测器 |
| **vnpy** | MT5 Gateway对接模式 | MT5数据获取层 |
| **OpenFinClaw** | Agent Debate Arena理念 | 我们的辩论系统直接借这个概念 |

### 7.2 我们独有的

1. **State视角**: 市场被抽象为"状态", 策略与状态的匹配度量化 — 这是现有开源项目都没有的
2. **跨周期Agent分层**: 股指用H1+M15, 股票用D1+W1, 不是简单的多周期叠加而是不同资产类独立Agent
3. **用户经验注入**: 不是纯AI黑盒, 用户可以"我的感觉是DAX在M15收缩后做空" → AI验证而非替代
4. **MT5原生对接**: 不需要额外的数据源/券商API, 用交易者已在用的MT5

---

## 八、当前代码映射

| 需求模块 | 现有文件 | 需要做 |
|----------|----------|--------|
| DataFetcher | `python/analytics/squeeze_observer.py::_fetch_from_mt5` | 抽离为独立模块 |
| SqueezeDetector | `python/analytics/multi_timeframe_squeeze.py` | 同上 |
| BacktestEngine | `squeeze_multi_timeframe_research_v5.py` | 拆分为独立类 |
| ReportBuilder | 各文件内嵌的report生成 | 统一为ReportBuilder |
| Agent定义 | 无 | 新建`pipeform/agents/` |
| DebateOrchestrator | 无 | 新建`pipeform/debate/` |
| SimulationScanner | `run_v5_simulation.py` | 重构为类 |
| DailyReporter | `run_v5_daily_summary.py` | 重构为类 |
| CLI入口 | 无 | 新建`pipeform/cli.py` |

---

## 九、第一优先级开发任务

按依赖顺序:

1. **创建 `pipeform/` 目录结构** — 建好模块骨架
2. **重构DataFetcher** — 从v5中抽离数据获取, 加入SQLite缓存
3. **重构SqueezeDetector** — 从v5中抽离信号检测
4. **重构BacktestEngine** — 接口化, 支持多出场规则
5. **定义BaseAgent接口** — 让v5和M15 Phase1适配
6. **实现DebateOrchestrator v0.1** — 对比两个Agent的报告输出
7. **CLI入口** — `pipeform debate --asset index_fx` 能跑通第一个辩论
