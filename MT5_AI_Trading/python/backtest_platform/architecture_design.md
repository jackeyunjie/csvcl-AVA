# KVB 自主回测平台架构设计文档

> 版本: v1.0 | 日期: 2026-05-18
> 核心目标: 完全自主知识产权的回测平台，Market State + MISS 融合架构

---

## 一、设计原则

### 1.1 第一性原理（不可违背）

```
最小分析单元: 三元组 (MN1, W1, D1)
同一时刻的三周期混沌值作为一个不可分割的整体单元进行分析

⛔ 禁止单独分析日线D1
⛔ 禁止忽略MN1和W1只看D1
⛔ 禁止将不同时间戳的数据混合分析

✅ 必须观察三元组随时间的连续演化规律
✅ 必须关注三周期如何相互传导、转化
✅ 必须将(MN1,W1,D1)作为最小分析单元进行状态定义
```

### 1.2 状态优先原则

```
Price State 决定观察环境
Strategy Condition 决定候选筛选
Moneyflow/Chip 只做二级确认，永不替代 State Gate
```

### 1.3 知识产权边界

| 层级 | 自研/外购 | 说明 |
|------|----------|------|
| State Hex 编码引擎 | 自研 | P107 核心IP |
| MISS 框架 | 自研 | 4维25子状态 |
| 资金流能量层 | 自研 | P106 黑狼框架 |
| 数据获取 | 外购/桥接 | MT5 API / CSV导入 |
| 执行模拟 | 自研 | 撮合引擎 |
| 报告展示 | 自研 | 可导出SQX格式 |

---

## 二、五层架构总览

```
┌─────────────────────────────────────────────────────────────┐
│  第五层: 展示层 (Presentation)                                │
│  ├── 回测报告生成器 (HTML/PDF/JSON)                          │
│  ├── State-Regime 可视化                                     │
│  ├── 权益曲线绘制                                            │
│  └── SQX 格式导出 (兼容StrategyQuant)                        │
├─────────────────────────────────────────────────────────────┤
│  第四层: 执行层 (Execution)                                   │
│  ├── 模拟撮合引擎                                            │
│  ├── 滑点/点差模型                                           │
│  ├── 手续费/隔夜利息计算                                      │
│  ├── 仓位管理器                                              │
│  └── 绩效统计器 (Sharpe/Drawdown/WinRate)                    │
├─────────────────────────────────────────────────────────────┤
│  第三层: 策略层 (Strategy)                                    │
│  ├── 策略注册中心 (StrategyRegistry)                         │
│  ├── P107 State Hex 策略插件                                 │
│  ├── P106 资金流确认插件                                     │
│  ├── 策略组合器 (多策略并行回测)                              │
│  └── 参数优化器 (Walk-Forward)                               │
├─────────────────────────────────────────────────────────────┤
│  第二层: 计算层 (Compute)                                     │
│  ├── State Hex 编码引擎 (KVBStateHexEngine)                  │
│  ├── MISS 融合引擎 (4维25子状态)                             │
│  ├── 资金流能量层 (MoneyflowEnergyLayer)                     │
│  ├── 特征计算管线 (FeaturePipeline)                          │
│  └── 状态演化追踪器 (StateEvolutionTracker)                  │
├─────────────────────────────────────────────────────────────┤
│  第一层: 数据层 (Data)                                        │
│  ├── MT5 数据桥接器 (MT5DataBridge)                          │
│  ├── CSV/Parquet 数据导入器                                   │
│  ├── 数据缓存层 (DuckDB/SQLite)                              │
│  ├── 数据质量检查器                                          │
│  └── 多周期数据对齐器 (MN1/W1/D1/D4/H1)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、各层详细设计

### 3.1 第一层: 数据层 (Data Layer)

**职责**: 负责所有数据的获取、清洗、存储和对齐。

**核心模块**:

#### 3.1.1 MT5DataBridge
```python
class MT5DataBridge:
    """MT5 数据桥接器

    通过 MetaTrader5 Python API 或 ZeroMQ 从 MT5 提取历史数据。
    支持多周期数据一次性提取。
    """

    def __init__(self, mt5_path: Optional[str] = None):
        self.mt5_initialized = False

    def connect(self) -> bool:
        """连接MT5终端"""
        pass

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,      # "MN1" | "W1" | "D1" | "H4" | "H1"
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """获取OHLCV数据"""
        pass

    def fetch_multi_timeframe(
        self,
        symbol: str,
        timeframes: List[str],
        start: datetime,
        end: datetime,
    ) -> Dict[str, pd.DataFrame]:
        """一次性获取多周期数据，自动对齐时间戳"""
        pass

    def fetch_tick_data(
        self,
        symbol: str,
        date: datetime,
    ) -> pd.DataFrame:
        """获取指定日期的tick数据"""
        pass
```

#### 3.1.2 DataStore
```python
class DataStore:
    """数据缓存层

    使用 DuckDB 作为本地缓存，支持:
    - 按品种+周期分区存储
    - 自动去重和增量更新
    - 数据质量元数据记录
    """

    def __init__(self, db_path: str = "data/cache.duckdb"):
        pass

    def save_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
    ) -> bool:
        """保存OHLCV数据，自动处理重复"""
        pass

    def load_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """读取OHLCV数据"""
        pass

    def get_data_quality_report(
        self,
        symbol: str,
        timeframe: str,
    ) -> DataQualityReport:
        """获取数据质量报告（缺失值、跳空、异常值）"""
        pass
```

#### 3.1.3 MultiTimeframeAligner
```python
class MultiTimeframeAligner:
    """多周期数据对齐器

    核心职责: 确保MN1/W1/D1数据在同一时间戳上对齐，
    为三元组计算提供干净的数据输入。

    对齐规则:
    - D1数据: 每日一根
    - W1数据: 周五收盘值对齐到当周所有D1
    - MN1数据: 月末收盘值对齐到当月所有D1
    """

    def align(
        self,
        d1_df: pd.DataFrame,
        w1_df: pd.DataFrame,
        mn1_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        返回对齐后的DataFrame，每行包含:
        - timestamp, open, high, low, close, volume (D1)
        - w1_open, w1_high, w1_low, w1_close (W1)
        - mn1_open, mn1_high, mn1_low, mn1_close (MN1)
        """
        pass
```

---

### 3.2 第二层: 计算层 (Compute Layer)

**职责**: 所有状态计算、特征工程、MISS融合。

**核心模块**:

#### 3.2.1 StateHexComputeEngine
```python
class StateHexComputeEngine:
    """State Hex 计算引擎

    封装现有的 KVBStateHexEngine + StateHexEncoder，
    提供统一的计算接口供回测平台调用。
    """

    def __init__(self):
        self.encoder = StateHexEncoder()
        self.engine = KVBStateHexEngine()

    def compute_triplet_series(
        self,
        aligned_df: pd.DataFrame,   # 来自 MultiTimeframeAligner
    ) -> pd.DataFrame:
        """
        计算三元组时间序列

        返回每行的三元组状态:
        - mn1_hex, w1_hex, d1_hex
        - mn1_duration, w1_duration, d1_duration
        - mn1_desc, w1_desc, d1_desc
        """
        pass

    def compute_state_transitions(
        self,
        triplet_series: pd.DataFrame,
    ) -> pd.DataFrame:
        """计算状态转移矩阵（演化追踪）"""
        pass

    def get_state_regime_at(
        self,
        timestamp: datetime,
    ) -> StateRegime:
        """获取指定时间点的状态环境"""
        pass
```

#### 3.2.2 MISSEngine (新增)
```python
class MISSEngine:
    """MISS 融合引擎

    Market Information State Segmentation
    4个正交维度 × 25个子状态

    维度:
    1. Price (价格): 趋势/震荡/反转/突破
    2. Volume (成交量): 放量/缩量/均量/异常
    3. Liquidity (流动性): 充裕/紧张/枯竭/恢复
    4. Information (信息): 平静/预期/发布/消化

    与 State Hex 的关系:
    - State Hex 提供"体检码"（当前状态快照）
    - MISS 提供"环境画像"（市场生态描述）
    - 两者融合形成完整的观察环境
    """

    def __init__(self):
        self.price_states = PriceStateAnalyzer()
        self.volume_states = VolumeStateAnalyzer()
        self.liquidity_states = LiquidityStateAnalyzer()
        self.info_states = InformationStateAnalyzer()

    def compute_miss_snapshot(
        self,
        d1_df: pd.DataFrame,
        lookback: int = 20,
    ) -> MISSSnapshot:
        """计算MISS快照"""
        pass

    def fuse_with_state_hex(
        self,
        miss_snapshot: MISSSnapshot,
        triplet: StateHexTriplet,
    ) -> FusedState:
        """
        将MISS与State Hex融合

        融合规则:
        - State Hex 为主裁决（方向+强度）
        - MISS 为环境修饰（确认/警告/中性）
        - 输出: 增强型状态描述
        """
        pass
```

#### 3.2.3 FeaturePipeline
```python
class FeaturePipeline:
    """特征计算管线

    将原始数据 → 状态特征 → 策略可用特征
    支持增量计算（回测时逐日推进）
    """

    def __init__(self):
        self.state_engine = StateHexComputeEngine()
        self.miss_engine = MISSEngine()
        self.moneyflow_layer = MoneyflowEnergyLayer()

    def compute_daily_features(
        self,
        data_up_to_today: pd.DataFrame,
    ) -> DailyFeatures:
        """
        计算截至今日的所有特征

        关键约束: 严格只用今天及之前的数据
        （Walk-Forward 防前视偏差）
        """
        pass

    def compute_for_backtest_day(
        self,
        historical_df: pd.DataFrame,   # 截至当前回测日的所有数据
        current_idx: int,
    ) -> DailyFeatures:
        """回测专用: 逐日计算特征"""
        pass
```

---

### 3.3 第三层: 策略层 (Strategy Layer)

**职责**: 策略定义、注册、组合、参数优化。

**核心模块**:

#### 3.3.1 StrategyRegistry
```python
class StrategyRegistry:
    """策略注册中心

    统一管理所有可回测策略，支持:
    - 策略注册/注销
    - 策略参数schema定义
    - 多策略并行回测
    """

    def __init__(self):
        self._strategies: Dict[str, Type[BaseStrategy]] = {}

    def register(
        self,
        name: str,
        strategy_class: Type[BaseStrategy],
        param_schema: Dict[str, Any],
    ) -> None:
        """注册策略"""
        pass

    def get(self, name: str) -> Type[BaseStrategy]:
        """获取策略类"""
        pass

    def list_strategies(self) -> List[StrategyInfo]:
        """列出所有已注册策略"""
        pass
```

#### 3.3.2 BaseStrategy (抽象基类)
```python
class BaseStrategy(ABC):
    """策略基类

    所有回测策略必须继承此类。
    策略只负责"在什么条件下产生什么信号"，
    不负责执行细节（由执行层处理）。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass

    @property
    @abstractmethod
    def param_schema(self) -> Dict[str, Any]:
        """参数schema（用于优化器）"""
        pass

    @abstractmethod
    def on_daily_bar(
        self,
        features: DailyFeatures,
        current_price: float,
        portfolio: PortfolioState,
    ) -> Optional[Signal]:
        """
        每日触发

        Args:
            features: 当日特征（含State Hex三元组、MISS、资金流）
            current_price: 当前价格
            portfolio: 当前账户状态

        Returns:
            Signal 或 None
        """
        pass

    @abstractmethod
    def on_tick(
        self,
        tick: TickData,
        portfolio: PortfolioState,
    ) -> Optional[Signal]:
        """Tick级触发（可选实现）"""
        pass
```

#### 3.3.3 P107StateHexStrategy (现有引擎封装)
```python
class P107StateHexStrategy(BaseStrategy):
    """P107 State Hex 策略插件

    将现有的 TradingStrategy 封装为回测平台策略插件。
    """

    name = "P107_StateHex_v1"

    param_schema = {
        "min_confidence": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.6},
        "state_alignment_mode": {"type": "choice", "options": ["strict", "loose"], "default": "loose"},
        "max_positions": {"type": "int", "min": 1, "max": 10, "default": 5},
    }

    def __init__(self, **params):
        self.inner_strategy = TradingStrategy(
            min_confidence=params.get("min_confidence", 0.6),
            state_alignment_mode=params.get("state_alignment_mode", "loose"),
        )
        self.moneyflow_enabled = params.get("enable_moneyflow", False)

    def on_daily_bar(self, features, current_price, portfolio) -> Optional[Signal]:
        # 1. 从 features 提取三元组
        triplet = features.triplet

        # 2. 状态门检查
        alignment_score, alignment_reason = self._check_alignment(triplet)
        if alignment_score < self.min_confidence:
            return None

        # 3. 价格行为验证
        price_valid, price_reason = self._validate_price(features)

        # 4. 资金流二级确认（如启用）
        if self.moneyflow_enabled and features.moneyflow:
            energy = features.moneyflow.assess()
            if energy.label == EnergyLabel.ENERGY_DIVERGENT:
                return None  # 资金流背离，过滤

        # 5. 生成信号
        return self._build_signal(triplet, alignment_score, features)
```

#### 3.3.4 WalkForwardOptimizer
```python
class WalkForwardOptimizer:
    """Walk-Forward 参数优化器

    避免过拟合的核心方法:
    1. 将数据分为N个训练/测试窗口
    2. 每个窗口: 训练集优化参数 → 测试集验证
    3. 汇总所有测试集结果作为最终评估
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        train_size: int = 252,    # 约1年
        test_size: int = 63,      # 约3个月
        n_splits: int = 5,
    ):
        pass

    def optimize(
        self,
        param_grid: Dict[str, List],
        metric: str = "sharpe_ratio",
    ) -> WalkForwardResult:
        """
        执行Walk-Forward优化

        Returns:
            包含每个窗口的最优参数和测试集表现的报告
        """
        pass
```

---

### 3.4 第四层: 执行层 (Execution Layer)

**职责**: 模拟真实交易执行，计算绩效指标。

**核心模块**:

#### 3.4.1 SimulationEngine
```python
class SimulationEngine:
    """模拟撮合引擎

    模拟MT5的真实执行环境:
    - 点差模型 (固定/浮动/基于波动率)
    - 滑点模型 (固定/正态分布/基于流动性)
    - 手续费模型 (按手数/按成交额)
    - 隔夜利息 (Swap)
    - 部分成交/拒单模拟
    """

    def __init__(
        self,
        spread_model: SpreadModel = FixedSpreadModel(1.0),
        slippage_model: SlippageModel = ZeroSlippageModel(),
        commission_model: CommissionModel = PerLotCommissionModel(5.0),
        swap_model: Optional[SwapModel] = None,
    ):
        pass

    def execute_order(
        self,
        order: Order,
        bar: OHLCVBar,
        current_time: datetime,
    ) -> ExecutionResult:
        """
        执行订单

        返回实际成交价格、成本、是否成交
        """
        pass
```

#### 3.4.2 PortfolioManager
```python
class PortfolioManager:
    """仓位管理器

    跟踪所有持仓、可用保证金、已实现/未实现盈亏。
    """

    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions: List[Position] = []
        self.closed_trades: List[Trade] = []

    def open_position(self, signal: Signal, execution: ExecutionResult) -> Position:
        """开新仓位"""
        pass

    def close_position(
        self,
        position: Position,
        execution: ExecutionResult,
        reason: str,
    ) -> Trade:
        """平仓"""
        pass

    def update_equity(self, current_prices: Dict[str, float]):
        """更新权益（按当前市价）"""
        pass

    def get_margin_used(self) -> float:
        """已用保证金"""
        pass

    def get_free_margin(self) -> float:
        """可用保证金"""
        pass
```

#### 3.4.3 PerformanceAnalyzer
```python
class PerformanceAnalyzer:
    """绩效统计器

    计算标准回测指标 + State-Regime 专属指标
    """

    def analyze(self, trades: List[Trade], daily_stats: List[DailyStats]) -> PerformanceReport:
        """
        生成绩效报告

        标准指标:
        - Total Return, Win Rate, Profit Factor
        - Sharpe Ratio, Sortino Ratio
        - Max Drawdown, Calmar Ratio
        - Average Trade, Expectancy

        State-Regime 专属指标:
        - 各状态组合(W1|MN1)下的胜率分布
        - 状态持续时间的盈亏相关性
        - 状态转移前后的盈亏模式
        """
        pass

    def calculate_state_regime_metrics(
        self,
        trades: List[Trade],
    ) -> Dict[str, StateRegimeMetrics]:
        """计算各状态组合下的专属指标"""
        pass
```

---

### 3.5 第五层: 展示层 (Presentation Layer)

**职责**: 报告生成、可视化、外部系统对接。

**核心模块**:

#### 3.5.1 ReportGenerator
```python
class ReportGenerator:
    """回测报告生成器

    支持多种输出格式:
    - HTML: 交互式图表 (Plotly)
    - PDF: 静态报告
    - JSON: 机器可读，供外部系统消费
    - SQX: StrategyQuant X 兼容格式
    """

    def generate_html(self, result: BacktestResult) -> str:
        """生成HTML报告"""
        pass

    def generate_json(self, result: BacktestResult) -> Dict:
        """生成JSON报告"""
        pass

    def export_sqx(self, result: BacktestResult, filepath: str):
        """
        导出为SQX兼容格式

        字段映射:
        - NetProfit → total_pnl
        - ProfitFactor → profit_factor
        - SharpeRatio → sharpe_ratio
        - MaxDrawdown → max_drawdown_pct
        - TotalTrades → total_trades
        - WinPercent → win_rate
        """
        pass
```

#### 3.5.2 StateRegimeVisualizer
```python
class StateRegimeVisualizer:
    """State-Regime 可视化器

    专属可视化:
    - 三元组热力图 (时间 × 周期)
    - 状态转移桑基图
    - 状态-盈亏散点矩阵
    - 权益曲线 + 状态背景色
    """

    def plot_triplet_heatmap(self, triplet_series: pd.DataFrame) -> str:
        """三元组热力图（返回HTML）"""
        pass

    def plot_equity_with_state(self, result: BacktestResult) -> str:
        """权益曲线叠加状态背景"""
        pass

    def plot_state_regime_performance(self, result: BacktestResult) -> str:
        """各状态组合绩效对比"""
        pass
```

---

## 四、MISS 融合点详细设计

### 4.1 MISS 与 State Hex 的融合位置

融合发生在 **计算层 → 策略层** 的边界:

```
计算层输出: DailyFeatures
├── triplet: StateHexTriplet          (P107)
├── miss_snapshot: MISSSnapshot       (MISS)
├── moneyflow: EnergyAssessment       (P106)
└── raw_indicators: Dict              (原始指标)

策略层输入: DailyFeatures
策略层规则:
1. 优先使用 triplet 做状态门判断
2. miss_snapshot 做环境确认（增强/削弱信心度）
3. moneyflow 做二级过滤（仅否决，不提议）
```

### 4.2 融合规则表

| State Hex 状态 | MISS Price | MISS Volume | 融合结果 |
|---------------|-----------|-------------|---------|
| 多头对齐 (1,2,3) | 趋势确认 | 放量 | 信心度 +15% |
| 多头对齐 (1,2,3) | 趋势确认 | 缩量 | 信心度 +5%（警惕） |
| 多头对齐 (1,2,3) | 震荡 | 放量 | 信心度 -10%（分歧） |
| 空头对齐 (-1,-2,-3) | 趋势确认 | 放量 | 信心度 +15% |
| 收缩底座 (c) | 任何 | 任何 | 保持观望，不操作 |

### 4.3 信心度调整公式

```python
def fuse_confidence(
    base_confidence: float,      # State Hex 基础信心度
    miss_snapshot: MISSSnapshot,
    moneyflow: EnergyAssessment,
) -> float:
    """
    融合后的信心度计算

    规则:
    1. MISS Price 与 State Hex 方向一致: +0.10
    2. MISS Volume 确认（放量同向）: +0.05
    3. MISS Liquidity 紧张: -0.10
    4. Moneyflow ENERGY_SUPPORTIVE: +0.05
    5. Moneyflow ENERGY_DIVERGENT: -0.20（强过滤）
    6. Moneyflow ENERGY_OVERHEATED: -0.10（警惕）
    """
    adjusted = base_confidence

    # MISS Price 确认
    if miss_snapshot.price_state.aligns_with(triplet_direction):
        adjusted += 0.10
    else:
        adjusted -= 0.10

    # MISS Volume 确认
    if miss_snapshot.volume_state.confirms_trend():
        adjusted += 0.05

    # MISS Liquidity
    if miss_snapshot.liquidity_state.is_tight():
        adjusted -= 0.10

    # Moneyflow
    if moneyflow.label == EnergyLabel.ENERGY_SUPPORTIVE:
        adjusted += 0.05
    elif moneyflow.label == EnergyLabel.ENERGY_DIVERGENT:
        adjusted -= 0.20
    elif moneyflow.label == EnergyLabel.ENERGY_OVERHEATED:
        adjusted -= 0.10

    return max(0.0, min(1.0, adjusted))
```

---

## 五、与现有代码的集成方案

### 5.1 现有代码清单

| 文件 | 路径 | 角色 | 集成方式 |
|------|------|------|---------|
| `trading_strategy.py` | `ai_engine/trading_strategy.py` | 策略核心 | 封装为 P107StateHexStrategy |
| `state_hex_backtest.py` | `backtest/state_hex_backtest.py` | 回测引擎 | 功能拆分至执行层+策略层 |
| `moneyflow_energy_layer.py` | `ai_engine/moneyflow_energy_layer.py` | 资金流 | 作为计算层模块 |
| `kvb_state_hex_engine.py` | `ai_engine/kvb_state_hex_engine.py` | State引擎 | 作为计算层核心 |
| `state_hex_encoding.py` | `ai_engine/state_hex_encoding.py` | 编码器 | 作为计算层基础 |

### 5.2 集成步骤

```
Step 1: 数据层 (本周)
├── 创建 MT5DataBridge
├── 创建 DataStore (DuckDB)
├── 创建 MultiTimeframeAligner
└── 测试: 从MT5提取EURUSD D1/W1/MN1，验证对齐

Step 2: 计算层扩展 (本周)
├── 创建 StateHexComputeEngine（封装现有引擎）
├── 创建 FeaturePipeline
├── 创建 MISSEngine（骨架，后续填充25子状态）
└── 测试: 计算三元组序列，对比手工验证

Step 3: 策略层重构 (下周)
├── 创建 BaseStrategy 抽象类
├── 创建 StrategyRegistry
├── 将 TradingStrategy 封装为 P107StateHexStrategy
├── 创建 WalkForwardOptimizer
└── 测试: 单策略回测，对比现有 backtest 结果

Step 4: 执行层完善 (下周)
├── 创建 SimulationEngine
├── 创建 PortfolioManager
├── 创建 PerformanceAnalyzer
└── 测试: 完整回测流程，验证指标计算

Step 5: 展示层 (第3周)
├── 创建 ReportGenerator
├── 创建 StateRegimeVisualizer
├── 实现 SQX 导出
└── 测试: 生成HTML报告，导入SQX
```

### 5.3 向后兼容性

```python
# 现有代码调用方式（保持可用）
from backtest.state_hex_backtest import StateHexBacktestEngine
engine = StateHexBacktestEngine(...)
engine.load_d1_data(df)
result = engine.run()

# 新平台调用方式（推荐）
from backtest_platform import BacktestPlatform
platform = BacktestPlatform()
platform.load_data(symbol="EURUSD", timeframe="D1")
platform.register_strategy(P107StateHexStrategy(min_confidence=0.6))
result = platform.run_backtest()
report = platform.generate_report(format="html")
```

---

## 六、接口总览

### 6.1 跨层接口

```python
# 数据层 → 计算层
DataStore.load_ohlcv() → pd.DataFrame
MultiTimeframeAligner.align() → pd.DataFrame

# 计算层 → 策略层
FeaturePipeline.compute_daily_features() → DailyFeatures
StateHexComputeEngine.compute_triplet_series() → pd.DataFrame

# 策略层 → 执行层
BaseStrategy.on_daily_bar() → Optional[Signal]
Signal(direction, size, stop_loss, take_profit, metadata)

# 执行层 → 展示层
PerformanceAnalyzer.analyze() → PerformanceReport
BacktestResult(trades, daily_stats, state_regime_stats)
```

### 6.2 核心数据类

```python
@dataclass
class DailyFeatures:
    """每日特征包（计算层输出，策略层输入）"""
    timestamp: datetime
    triplet: StateHexTriplet
    miss_snapshot: Optional[MISSSnapshot]
    moneyflow: Optional[EnergyAssessment]
    ohlcv: OHLCVBar
    technical_indicators: Dict[str, float]

@dataclass
class Signal:
    """交易信号（策略层输出，执行层输入）"""
    direction: str          # "long" | "short" | "close"
    size: float             # 手数
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    confidence: float
    metadata: Dict[str, Any]   # 状态标签、三元组等

@dataclass
class BacktestResult:
    """回测结果（执行层输出，展示层输入）"""
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_balance: float
    final_balance: float
    total_return_pct: float
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: List[Trade]
    daily_stats: List[DailyStats]
    state_regime_stats: Dict[str, StateRegimeMetrics]
```

---

## 七、技术栈

| 层级 | 技术选型 | 理由 |
|------|---------|------|
| 数据层 | DuckDB + pandas | 高性能本地分析，零配置 |
| 计算层 | Python + NumPy | 现有代码复用，生态成熟 |
| 策略层 | Python | 灵活，支持动态加载 |
| 执行层 | Python | 与策略层同语言，低延迟 |
| 展示层 | Plotly (HTML) + Jinja2 | 交互式图表，模板引擎 |
| 配置 | YAML/JSON | 人类可读，版本控制友好 |
| 日志 | Python logging | 标准库，无依赖 |

---

## 八、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| MT5 API 不稳定 | 数据获取中断 | 实现CSV回退路径 |
| 计算性能不足 | 大数据量回测慢 | DuckDB加速，支持采样 |
| MISS 25子状态复杂 | 开发周期长 | 先实现骨架，逐步填充 |
| 与现有代码冲突 | 功能重复 | 保持现有代码可用，新平台并行开发 |
| SQX 格式变更 | 导出失效 | 版本化导出器，单元测试覆盖 |

---

## 九、验收标准

### 9.1 MVP (第1周)
- [ ] 能从MT5提取D1数据并存储到DuckDB
- [ ] 能计算三元组序列并输出到DataFrame
- [ ] 能运行单策略回测并输出基础指标
- [ ] 能生成JSON格式回测报告

### 9.2 完整版 (第3周)
- [ ] 支持MN1/W1/D1多周期自动对齐
- [ ] MISS框架骨架可用（至少Price维度）
- [ ] Walk-Forward参数优化
- [ ] HTML交互式报告（含State-Regime可视化）
- [ ] SQX格式导出
- [ ] 与现有 `state_hex_backtest.py` 结果一致性验证

---

*文档结束*
