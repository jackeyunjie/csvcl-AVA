# Qoder AI量化多周期交易平台 - 核心模块详细设计

**版本**: V1.0  
**日期**: 2026-06-06  
**文档编号**: QODER-MD-001  

---

## 一、自然语言处理模块 (NL-Strategy)

### 1.1 模块概述
将用户自然语言描述转换为结构化策略意图，并生成可执行代码。参考Vibe-Trading的自然语言策略生成理念和TradingAgents的LLM驱动架构。

### 1.2 核心类设计

```python
# ==================== 数据模型 ====================

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

class StrategyType(Enum):
    TREND_FOLLOWING = "trend_following"      # 趋势跟踪
    MEAN_REVERSION = "mean_reversion"        # 均值回归
    BREAKOUT = "breakout"                    # 突破
    MULTI_FACTOR = "multi_factor"            # 多因子
    STATISTICAL_ARBITRAGE = "stat_arb"       # 统计套利

class CodeTarget(Enum):
    PYTHON = "python"                        # Python回测代码
    MQL5 = "mql5"                           # MT5 EA代码
    PINE_SCRIPT = "pine_script"             # TradingView
    TDX = "tdx"                             # 通达信

@dataclass
class StrategyIntent:
    """策略意图结构化表示"""
    raw_text: str                            # 原始自然语言
    strategy_type: StrategyType              # 策略类型
    symbol: Optional[str] = None             # 交易品种
    timeframe: Optional[str] = None          # 时间周期
    entry_conditions: List[Dict] = field(default_factory=list)   # 入场条件
    exit_conditions: List[Dict] = field(default_factory=list)    # 出场条件
    risk_params: Dict[str, Any] = field(default_factory=dict)    # 风控参数
    indicators: List[Dict] = field(default_factory=list)         # 使用的指标
    parameters: Dict[str, Any] = field(default_factory=dict)     # 策略参数

@dataclass
class ValidationResult:
    """策略验证结果"""
    is_valid: bool
    syntax_errors: List[str] = field(default_factory=list)
    logic_warnings: List[str] = field(default_factory=list)
    performance_notes: List[str] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)

# ==================== 核心服务 ====================

class NLStrategyService:
    """
    自然语言策略生成服务
    
    工作流程:
    1. parse_natural_language: 解析自然语言 → StrategyIntent
    2. match_template: 匹配策略模板
    3. generate_code: 生成目标代码
    4. validate_strategy: 验证策略
    5. optimize_parameters: 参数优化建议
    """
    
    def __init__(self, llm_gateway: 'LLMGateway', template_registry: 'TemplateRegistry'):
        self.llm = llm_gateway
        self.templates = template_registry
        self.validator = StrategyValidator()
    
    def parse_natural_language(self, text: str) -> StrategyIntent:
        """
        使用LLM将自然语言解析为结构化意图
        
        Prompt设计:
        - 系统提示词包含完整的策略要素定义和示例
        - 使用结构化输出（JSON Schema）
        - Few-shot示例提高准确性
        """
        system_prompt = """你是一个专业的量化交易策略解析器。
        将用户的自然语言描述解析为结构化的策略意图。
        
        你需要提取以下要素:
        1. strategy_type: 策略类型 (trend_following/mean_reversion/breakout/multi_factor)
        2. symbol: 交易品种 (如 EURUSD, BTCUSD)
        3. timeframe: 时间周期 (如 H1, D1)
        4. entry_conditions: 入场条件列表
        5. exit_conditions: 出场条件列表
        6. risk_params: 风控参数 (止损、止盈、仓位)
        7. indicators: 使用的技术指标
        8. parameters: 策略参数
        
        输出格式必须是严格的JSON。"""
        
        schema = {
            "type": "object",
            "properties": {
                "strategy_type": {"type": "string", "enum": ["trend_following", "mean_reversion", "breakout", "multi_factor"]},
                "symbol": {"type": "string"},
                "timeframe": {"type": "string"},
                "entry_conditions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "indicator": {"type": "string"},
                            "condition": {"type": "string"},
                            "params": {"type": "object"}
                        }
                    }
                },
                "exit_conditions": {"type": "array", "items": {"type": "object"}},
                "risk_params": {"type": "object"},
                "indicators": {"type": "array", "items": {"type": "object"}},
                "parameters": {"type": "object"}
            },
            "required": ["strategy_type", "entry_conditions", "exit_conditions"]
        }
        
        response = self.llm.structured_output(
            system_prompt=system_prompt,
            user_prompt=text,
            schema=schema
        )
        
        return StrategyIntent(
            raw_text=text,
            strategy_type=StrategyType(response["strategy_type"]),
            symbol=response.get("symbol"),
            timeframe=response.get("timeframe"),
            entry_conditions=response.get("entry_conditions", []),
            exit_conditions=response.get("exit_conditions", []),
            risk_params=response.get("risk_params", {}),
            indicators=response.get("indicators", []),
            parameters=response.get("parameters", {})
        )
    
    def generate_code(self, intent: StrategyIntent, target: CodeTarget) -> str:
        """
        基于策略意图生成目标代码
        
        实现方式:
        1. 查找匹配的模板
        2. 用Jinja2渲染模板
        3. 使用LLM进行代码优化和补全
        """
        template = self.templates.get_template(intent.strategy_type, target)
        
        # 基础渲染
        base_code = template.render(
            symbol=intent.symbol or "EURUSD",
            timeframe=intent.timeframe or "H1",
            entry_conditions=intent.entry_conditions,
            exit_conditions=intent.exit_conditions,
            risk_params=intent.risk_params,
            indicators=intent.indicators,
            parameters=intent.parameters
        )
        
        # LLM优化（可选）
        if target == CodeTarget.PYTHON:
            base_code = self._optimize_python_code(base_code, intent)
        
        return base_code
    
    def validate_strategy(self, code: str, target: CodeTarget) -> ValidationResult:
        """验证生成的策略代码"""
        return self.validator.validate(code, target)
    
    def _optimize_python_code(self, code: str, intent: StrategyIntent) -> str:
        """使用LLM优化Python代码"""
        prompt = f"""优化以下量化交易策略代码，确保:
        1. 使用向量化计算（Pandas/NumPy）提高性能
        2. 添加完整的类型注解
        3. 添加详细的文档字符串
        4. 确保风控逻辑完整
        5. 代码符合PEP8规范
        
        原始代码:
        ```python
        {code}
        ```
        """
        return self.llm.chat(prompt)


class StrategyValidator:
    """策略代码验证器"""
    
    def validate(self, code: str, target: CodeTarget) -> ValidationResult:
        errors = []
        warnings = []
        notes = []
        
        # 1. 语法验证
        if target == CodeTarget.PYTHON:
            syntax_errors = self._check_python_syntax(code)
            errors.extend(syntax_errors)
        
        # 2. 逻辑校验
        logic_warnings = self._check_logic(code)
        warnings.extend(logic_warnings)
        
        # 3. 性能检查
        performance_notes = self._check_performance(code)
        notes.extend(performance_notes)
        
        # 4. 风控检查
        risk_warnings = self._check_risk_management(code)
        warnings.extend(risk_warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            syntax_errors=errors,
            logic_warnings=warnings,
            performance_notes=notes
        )
    
    def _check_python_syntax(self, code: str) -> List[str]:
        """检查Python语法"""
        import ast
        try:
            ast.parse(code)
            return []
        except SyntaxError as e:
            return [f"语法错误 (行 {e.lineno}): {e.msg}"]
    
    def _check_logic(self, code: str) -> List[str]:
        """检查逻辑问题"""
        warnings = []
        # 检查买入卖出条件是否可能同时触发
        if "buy" in code.lower() and "sell" in code.lower():
            if "elif" not in code and "else" not in code:
                warnings.append("买入和卖出条件可能同时触发，建议使用互斥条件")
        return warnings
    
    def _check_performance(self, code: str) -> List[str]:
        """检查性能问题"""
        notes = []
        # 检查是否有循环计算指标
        if "for" in code and "iloc" in code:
            notes.append("检测到循环中访问DataFrame，建议使用向量化操作")
        return notes
    
    def _check_risk_management(self, code: str) -> List[str]:
        """检查风控完整性"""
        warnings = []
        required_elements = ["stop", "loss", "risk"]
        if not any(elem in code.lower() for elem in required_elements):
            warnings.append("未检测到止损逻辑，建议添加风控措施")
        return warnings


class TemplateRegistry:
    """策略模板注册表"""
    
    def __init__(self, template_dir: str = "templates/strategies"):
        self.template_dir = template_dir
        self.templates: Dict[str, Dict[CodeTarget, Any]] = {}
        self._load_templates()
    
    def _load_templates(self):
        """从目录加载所有模板"""
        # 加载内置模板
        self.templates[StrategyType.TREND_FOLLOWING] = {
            CodeTarget.PYTHON: self._load_template("trend_following.py.j2"),
            CodeTarget.MQL5: self._load_template("trend_following.mq5.j2"),
            CodeTarget.PINE_SCRIPT: self._load_template("trend_following.pine.j2")
        }
        # ... 其他模板
    
    def get_template(self, strategy_type: StrategyType, target: CodeTarget):
        return self.templates.get(strategy_type, {}).get(target)
```

### 1.3 关键算法

**意图解析算法**:
1. 使用LLM进行实体提取（指标、条件、参数）
2. 规则引擎进行意图分类
3. 模板匹配确定策略框架
4. 参数填充和默认值设置

**代码生成算法**:
1. Jinja2模板渲染基础代码
2. AST遍历进行代码优化
3. LLM补全复杂逻辑
4. 代码格式化和注释添加

---

## 二、回测引擎模块 (Backtest Engine)

### 2.1 模块概述
高性能向量化回测引擎，支持多周期数据对齐、真实交易环境模拟、30秒内返回完整回测结果。

### 2.2 核心类设计

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
import numba
from numba import jit

class SlippageModel(Enum):
    FIXED = "fixed"                          # 固定滑点
    VOLATILITY_BASED = "volatility_based"    # 基于波动率
    LIQUIDITY_BASED = "liquidity_based"      # 基于流动性

class CommissionModel(Enum):
    FIXED_PER_LOT = "fixed_per_lot"          # 每手固定
    PERCENTAGE = "percentage"                # 百分比
    TIERED = "tiered"                        # 阶梯费率

@dataclass
class BacktestConfig:
    """回测配置"""
    strategy_code: str                       # 策略代码
    symbol: str                              # 品种
    timeframe: str                           # 周期
    start_date: str                          # 开始日期
    end_date: str                            # 结束日期
    initial_balance: float = 10000.0         # 初始资金
    leverage: float = 1.0                    # 杠杆
    slippage_model: SlippageModel = SlippageModel.FIXED
    slippage_points: float = 2.0             # 滑点点数
    commission_model: CommissionModel = CommissionModel.FIXED_PER_LOT
    commission_per_lot: float = 7.0          # 每手佣金
    use_multi_timeframe: bool = False        # 是否多周期
    timeframes: List[str] = field(default_factory=list)  # 多周期列表

@dataclass
class TradeRecord:
    """交易记录"""
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp]
    direction: int                           # 1=多, -1=空
    entry_price: float
    exit_price: Optional[float]
    volume: float
    pnl: float
    pnl_pct: float
    commission: float
    slippage: float
    holding_bars: int
    exit_reason: str                         # "tp", "sl", "signal", "end"

@dataclass
class BacktestResult:
    """回测结果"""
    trades: List[TradeRecord]
    equity_curve: pd.Series
    returns: pd.Series
    metrics: Dict[str, float]
    monthly_returns: pd.Series
    drawdown_series: pd.Series
    trade_distribution: Dict


class VectorizedBacktestEngine:
    """
    向量化回测引擎
    
    核心优化:
    1. 使用Pandas/NumPy向量化操作，避免Python循环
    2. 关键路径使用Numba JIT编译
    3. 多周期数据预对齐，避免运行时重采样
    4. 增量计算指标，避免重复计算
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.data: Optional[pd.DataFrame] = None
        self.multi_tf_data: Optional[Dict[str, pd.DataFrame]] = None
    
    def load_data(self, data_source: 'DataSource') -> 'VectorizedBacktestEngine':
        """加载历史数据"""
        # 加载主周期数据
        self.data = data_source.get_ohlcv(
            symbol=self.config.symbol,
            timeframe=self.config.timeframe,
            start=self.config.start_date,
            end=self.config.end_date
        )
        
        # 加载多周期数据（如需要）
        if self.config.use_multi_timeframe:
            self.multi_tf_data = {}
            for tf in self.config.timeframes:
                self.multi_tf_data[tf] = data_source.get_ohlcv(
                    symbol=self.config.symbol,
                    timeframe=tf,
                    start=self.config.start_date,
                    end=self.config.end_date
                )
            # 多周期数据对齐
            self._align_multi_timeframe_data()
        
        return self
    
    def _align_multi_timeframe_data(self):
        """多周期数据对齐"""
        # 以最小周期为基准
        base_tf = min(self.config.timeframes, key=lambda x: self._tf_to_minutes(x))
        base_data = self.multi_tf_data[base_tf]
        
        for tf, df in self.multi_tf_data.items():
            if tf != base_tf:
                # 前向填充对齐
                df_aligned = df.reindex(base_data.index, method='ffill')
                self.multi_tf_data[tf] = df_aligned
    
    @staticmethod
    def _tf_to_minutes(tf: str) -> int:
        """时间周期转分钟数"""
        mapping = {'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30, 
                   'H1': 60, 'H4': 240, 'D1': 1440, 'W1': 10080}
        return mapping.get(tf, 60)
    
    def run(self, strategy_func: Callable) -> BacktestResult:
        """
        执行向量化回测
        
        核心流程:
        1. 预计算所有指标（向量化）
        2. 生成信号序列（向量化）
        3. 模拟持仓和盈亏（向量化）
        4. 计算绩效指标
        """
        # 1. 预计算指标
        indicators = self._calculate_indicators()
        
        # 2. 生成信号
        signals = strategy_func(self.data, indicators, self.multi_tf_data)
        
        # 3. 模拟交易（向量化）
        trades, equity = self._simulate_trades_vectorized(signals)
        
        # 4. 计算绩效
        metrics = self._calculate_metrics(trades, equity)
        
        return BacktestResult(
            trades=trades,
            equity_curve=equity,
            returns=equity.pct_change(),
            metrics=metrics,
            monthly_returns=self._calculate_monthly_returns(equity),
            drawdown_series=self._calculate_drawdown(equity),
            trade_distribution=self._analyze_trades(trades)
        )
    
    def _calculate_indicators(self) -> Dict[str, pd.Series]:
        """预计算常用指标（向量化）"""
        close = self.data['close']
        high = self.data['high']
        low = self.data['low']
        
        indicators = {}
        
        # 移动平均线
        for period in [5, 10, 20, 50, 200]:
            indicators[f'MA_{period}'] = close.rolling(period).mean()
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        indicators['RSI'] = 100 - (100 / (1 + gain / loss))
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        indicators['MACD'] = ema12 - ema26
        indicators['MACD_signal'] = indicators['MACD'].ewm(span=9).mean()
        
        # ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        indicators['ATR'] = tr.rolling(14).mean()
        
        # Bollinger Bands
        ma20 = indicators['MA_20']
        std20 = close.rolling(20).std()
        indicators['BB_upper'] = ma20 + 2 * std20
        indicators['BB_lower'] = ma20 - 2 * std20
        indicators['BB_width'] = (indicators['BB_upper'] - indicators['BB_lower']) / ma20
        
        return indicators
    
    def _simulate_trades_vectorized(self, signals: pd.Series) -> (List[TradeRecord], pd.Series):
        """
        向量化交易模拟
        
        signals: Series of int, 1=买入, -1=卖出, 0=无信号
        """
        close = self.data['close']
        n = len(signals)
        
        # 持仓状态 (1=多头, -1=空头, 0=空仓)
        position = np.zeros(n)
        
        # 生成持仓序列
        # 当信号与当前持仓方向不同时，切换持仓
        current_pos = 0
        for i in range(n):
            if signals.iloc[i] != 0 and signals.iloc[i] != current_pos:
                current_pos = signals.iloc[i]
            position[i] = current_pos
        
        # 计算持仓收益（向量化）
        returns = close.pct_change()
        strategy_returns = position[:-1] * returns.iloc[1:].values
        
        # 计算滑点和手续费
        trades_mask = np.diff(position) != 0
        n_trades = np.sum(trades_mask)
        
        # 扣除交易成本
        commission_cost = n_trades * self.config.commission_per_lot / self.config.initial_balance
        slippage_cost = n_trades * self.config.slippage_points * 0.0001  # 假设1点=0.0001
        
        # 权益曲线
        cumulative_returns = (1 + strategy_returns).cumprod()
        equity = self.config.initial_balance * cumulative_returns
        
        # 生成交易记录
        trades = self._extract_trades(position, close)
        
        return trades, equity
    
    def _extract_trades(self, position: np.ndarray, close: pd.Series) -> List[TradeRecord]:
        """从持仓序列提取交易记录"""
        trades = []
        entry_idx = None
        entry_price = None
        direction = 0
        
        for i in range(len(position)):
            if position[i] != direction:
                # 平仓
                if direction != 0 and entry_idx is not None:
                    pnl = (close.iloc[i] - entry_price) * direction
                    trades.append(TradeRecord(
                        entry_time=close.index[entry_idx],
                        exit_time=close.index[i],
                        direction=direction,
                        entry_price=entry_price,
                        exit_price=close.iloc[i],
                        volume=1.0,
                        pnl=pnl,
                        pnl_pct=pnl / entry_price * 100,
                        commission=self.config.commission_per_lot,
                        slippage=self.config.slippage_points * 0.0001,
                        holding_bars=i - entry_idx,
                        exit_reason="signal"
                    ))
                
                # 开仓
                if position[i] != 0:
                    entry_idx = i
                    entry_price = close.iloc[i]
                    direction = position[i]
        
        return trades
    
    def _calculate_metrics(self, trades: List[TradeRecord], equity: pd.Series) -> Dict[str, float]:
        """计算绩效指标"""
        returns = equity.pct_change().dropna()
        
        # 基础指标
        total_return = (equity.iloc[-1] / equity.iloc[0] - 1) * 100
        
        # 年化收益
        n_years = len(equity) / 252  # 假设日数据
        annual_return = ((1 + total_return / 100) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
        
        # 波动率
        volatility = returns.std() * np.sqrt(252) * 100
        
        # 夏普比率
        risk_free_rate = 0.02
        sharpe = (annual_return / 100 - risk_free_rate) / (volatility / 100) if volatility > 0 else 0
        
        # 最大回撤
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_drawdown = drawdown.min() * 100
        
        # 交易指标
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        avg_profit = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        profit_factor = abs(sum(t.pnl for t in winning_trades) / sum(t.pnl for t in losing_trades)) if losing_trades and sum(t.pnl for t in losing_trades) != 0 else float('inf')
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'calmar_ratio': abs(annual_return / max_drawdown) if max_drawdown != 0 else 0
        }
    
    def _calculate_monthly_returns(self, equity: pd.Series) -> pd.Series:
        """计算月度收益"""
        return equity.resample('ME').last().pct_change() * 100
    
    def _calculate_drawdown(self, equity: pd.Series) -> pd.Series:
        """计算回撤序列"""
        cummax = equity.cummax()
        return (equity - cummax) / cummax * 100
    
    def _analyze_trades(self, trades: List[TradeRecord]) -> Dict:
        """交易分布分析"""
        if not trades:
            return {}
        
        pnls = [t.pnl for t in trades]
        holding_times = [t.holding_bars for t in trades]
        
        return {
            'pnl_distribution': {
                'mean': np.mean(pnls),
                'std': np.std(pnls),
                'min': min(pnls),
                'max': max(pnls),
                'median': np.median(pnls)
            },
            'holding_time_distribution': {
                'mean': np.mean(holding_times),
                'median': np.median(holding_times),
                'max': max(holding_times)
            },
            'exit_reason_distribution': self._count_exit_reasons(trades)
        }
    
    def _count_exit_reasons(self, trades: List[TradeRecord]) -> Dict[str, int]:
        """统计出场原因分布"""
        from collections import Counter
        return dict(Counter(t.exit_reason for t in trades))


class ParameterOptimizer:
    """参数优化器"""
    
    def __init__(self, engine: VectorizedBacktestEngine):
        self.engine = engine
    
    def optimize(self, strategy_func: Callable, param_grid: Dict[str, List], 
                 objective: str = 'sharpe_ratio', n_jobs: int = -1) -> Dict:
        """
        参数优化
        
        支持方法:
        - grid_search: 网格搜索
        - random_search: 随机搜索
        - bayesian: 贝叶斯优化 (Optuna)
        """
        import itertools
        
        # 生成参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))
        
        results = []
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            # 创建带参数的策略函数
            def parameterized_strategy(data, indicators, multi_tf):
                return strategy_func(data, indicators, multi_tf, **params)
            
            # 运行回测
            result = self.engine.run(parameterized_strategy)
            
            results.append({
                'params': params,
                'objective': result.metrics.get(objective, 0),
                'metrics': result.metrics
            })
        
        # 排序并返回最优结果
        results.sort(key=lambda x: x['objective'], reverse=True)
        
        return {
            'best_params': results[0]['params'],
            'best_objective': results[0]['objective'],
            'all_results': results,
            'param_heatmap': self._generate_heatmap(results, param_names)
        }
    
    def _generate_heatmap(self, results: List[Dict], param_names: List[str]) -> Dict:
        """生成参数热力图数据"""
        # 简化实现：返回前两个参数的二维热力图
        if len(param_names) < 2:
            return {}
        
        p1, p2 = param_names[0], param_names[1]
        
        heatmap = {}
        for r in results:
            v1 = r['params'][p1]
            v2 = r['params'][p2]
            if v1 not in heatmap:
                heatmap[v1] = {}
            heatmap[v1][v2] = r['objective']
        
        return {
            'param1': p1,
            'param2': p2,
            'data': heatmap
        }
```

---

## 三、多Agent协作系统模块

### 3.1 模块概述
构建模拟真实交易公司的多Agent协作系统，各Agent具备独立决策能力，通过消息总线进行协作。

### 3.2 核心类设计

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import uuid
import json

class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"

class MessageType(Enum):
    SIGNAL = "signal"                        # 交易信号
    RESEARCH_REPORT = "research_report"      # 研究报告
    RISK_CHECK = "risk_check"                # 风险检查请求
    RISK_RESPONSE = "risk_response"          # 风险检查响应
    ORDER = "order"                          # 交易指令
    EXECUTION_REPORT = "execution_report"    # 执行报告
    MARKET_DATA = "market_data"              # 市场数据
    SYSTEM_EVENT = "system_event"            # 系统事件
    CONTRACTION_ALERT = "contraction_alert"  # 收缩预警
    BREAKOUT_CONFIRMED = "breakout_confirmed" # 突破确认
    TREND_UPDATE = "trend_update"            # 趋势更新

class Priority(Enum):
    CRITICAL = 1                             # 紧急（如风控强制平仓）
    HIGH = 2                                 # 高（如突破信号）
    NORMAL = 3                               # 正常（如研究报告）
    LOW = 4                                  # 低（如日志）

@dataclass
class AgentMessage:
    """Agent间消息"""
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: Optional[str] = None           # None表示广播
    msg_type: MessageType = MessageType.SYSTEM_EVENT
    priority: Priority = Priority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    payload: Dict[str, Any] = field(default_factory=dict)
    requires_ack: bool = False
    correlation_id: Optional[str] = None     # 关联消息ID

@dataclass
class AgentState:
    """Agent状态"""
    agent_id: str
    agent_type: str
    status: AgentStatus
    current_task: Optional[str] = None
    last_activity: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)


class MessageBus:
    """
    Agent消息总线
    
    支持两种模式:
    1. 单机模式: Python asyncio Queue
    2. 扩展模式: Redis Pub/Sub
    """
    
    def __init__(self, mode: str = "local"):
        self.mode = mode
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_history: List[AgentMessage] = []
        self.max_history = 10000
        
        if mode == "local":
            self.queue = asyncio.Queue()
        elif mode == "redis":
            import redis
            self.redis_client = redis.Redis()
    
    def subscribe(self, agent_id: str, handler: Callable[[AgentMessage], None]):
        """订阅消息"""
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(handler)
    
    def unsubscribe(self, agent_id: str, handler: Callable):
        """取消订阅"""
        if agent_id in self.subscribers:
            self.subscribers[agent_id].remove(handler)
    
    async def publish(self, message: AgentMessage):
        """发布消息"""
        # 记录历史
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
        
        # 本地模式
        if self.mode == "local":
            if message.to_agent:
                # 点对点
                if message.to_agent in self.subscribers:
                    for handler in self.subscribers[message.to_agent]:
                        try:
                            await handler(message)
                        except Exception as e:
                            print(f"消息处理错误: {e}")
            else:
                # 广播
                for agent_id, handlers in self.subscribers.items():
                    for handler in handlers:
                        try:
                            await handler(message)
                        except Exception as e:
                            print(f"消息处理错误: {e}")
    
    def get_message_history(self, agent_id: Optional[str] = None, 
                           msg_type: Optional[MessageType] = None,
                           limit: int = 100) -> List[AgentMessage]:
        """获取消息历史"""
        messages = self.message_history
        
        if agent_id:
            messages = [m for m in messages if m.from_agent == agent_id or m.to_agent == agent_id]
        
        if msg_type:
            messages = [m for m in messages if m.msg_type == msg_type]
        
        return messages[-limit:]


class BaseAgent(ABC):
    """
    Agent基类
    
    所有具体Agent的抽象基类，定义通用接口和生命周期。
    """
    
    def __init__(self, agent_id: str, agent_type: str, message_bus: MessageBus):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.message_bus = message_bus
        self.status = AgentStatus.IDLE
        self.state: Dict[str, Any] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        
        # 订阅消息
        self.message_bus.subscribe(self.agent_id, self._on_message)
    
    @abstractmethod
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息，返回响应消息（如有）"""
        pass
    
    @abstractmethod
    async def run(self):
        """Agent主循环"""
        pass
    
    async def _on_message(self, message: AgentMessage):
        """消息处理入口"""
        if self.status == AgentStatus.STOPPED:
            return
        
        self.status = AgentStatus.RUNNING
        try:
            response = await self.process(message)
            if response and message.requires_ack:
                response.correlation_id = message.msg_id
                await self.message_bus.publish(response)
        except Exception as e:
            self.status = AgentStatus.ERROR
            print(f"Agent {self.agent_id} 处理错误: {e}")
        finally:
            self.status = AgentStatus.IDLE
    
    async def send_message(self, to_agent: str, msg_type: MessageType, 
                          payload: Dict, priority: Priority = Priority.NORMAL,
                          requires_ack: bool = False):
        """发送消息"""
        msg = AgentMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            msg_type=msg_type,
            priority=priority,
            payload=payload,
            requires_ack=requires_ack
        )
        await self.message_bus.publish(msg)
    
    async def broadcast(self, msg_type: MessageType, payload: Dict,
                       priority: Priority = Priority.NORMAL):
        """广播消息"""
        msg = AgentMessage(
            from_agent=self.agent_id,
            to_agent=None,
            msg_type=msg_type,
            priority=priority,
            payload=payload
        )
        await self.message_bus.publish(msg)
    
    def get_state(self) -> AgentState:
        """获取Agent状态"""
        return AgentState(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            status=self.status,
            current_task=None,
            metrics=self.state.get('metrics', {})
        )


class ResearchAgent(BaseAgent):
    """
    研究Agent
    
    负责市场研究、策略发现、信号生成。
    子类型: 技术分析师、基本面分析师、情绪分析师、量化研究员
    """
    
    def __init__(self, agent_id: str, message_bus: MessageBus, 
                 research_type: str = "technical",
                 state_hex_engine: Optional[Any] = None,
                 llm_analyzer: Optional[Any] = None):
        super().__init__(agent_id, f"research_{research_type}", message_bus)
        self.research_type = research_type
        self.state_hex_engine = state_hex_engine
        self.llm_analyzer = llm_analyzer
        self.signals: List[Dict] = []
    
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        if message.msg_type == MessageType.MARKET_DATA:
            # 收到市场数据，进行分析
            await self._analyze_market(message.payload)
        
        elif message.msg_type == MessageType.CONTRACTION_ALERT:
            # 收到收缩预警，进行突破方向预测
            prediction = await self._predict_breakout_direction(message.payload)
            return AgentMessage(
                from_agent=self.agent_id,
                to_agent="trader",
                msg_type=MessageType.RESEARCH_REPORT,
                priority=Priority.HIGH,
                payload={
                    "type": "breakout_prediction",
                    "symbol": message.payload.get("symbol"),
                    "prediction": prediction,
                    "confidence": prediction.get("confidence", 0.5)
                }
            )
        
        return None
    
    async def run(self):
        """研究Agent主循环"""
        while self.status != AgentStatus.STOPPED:
            # 定期执行研究任务
            await self._perform_research()
            await asyncio.sleep(60)  # 每分钟执行一次
    
    async def _analyze_market(self, data: Dict):
        """分析市场数据"""
        symbol = data.get("symbol")
        
        if self.research_type == "technical":
            # 技术分析
            signals = await self._technical_analysis(symbol)
        elif self.research_type == "sentiment":
            # 情绪分析
            signals = await self._sentiment_analysis(symbol)
        else:
            signals = []
        
        # 发送信号给交易员Agent
        for signal in signals:
            await self.send_message(
                to_agent="trader",
                msg_type=MessageType.SIGNAL,
                payload=signal,
                priority=Priority.HIGH if signal.get("confidence", 0) > 0.8 else Priority.NORMAL
            )
    
    async def _technical_analysis(self, symbol: str) -> List[Dict]:
        """技术分析"""
        signals = []
        
        # 使用State Hex引擎获取状态
        if self.state_hex_engine:
            state = self.state_hex_engine.get_current_state(symbol)
            
            # 检测多周期共振
            if self._check_resonance(state):
                signals.append({
                    "symbol": symbol,
                    "signal_type": "resonance",
                    "direction": self._get_resonance_direction(state),
                    "confidence": self._calculate_resonance_strength(state),
                    "state_hex": state,
                    "reasoning": f"多周期共振: {state}"
                })
        
        return signals
    
    def _check_resonance(self, state: Dict) -> bool:
        """检查多周期共振"""
        # 检查MN1/W1/D1是否同向
        hex_values = [state.get(f"{tf}_hex", "8") for tf in ["mn1", "w1", "d1"]]
        
        # 简化判断：所有hex值相同且不为8（中性）
        return len(set(hex_values)) == 1 and hex_values[0] != "8"
    
    def _get_resonance_direction(self, state: Dict) -> str:
        """获取共振方向"""
        hex_val = state.get("d1_hex", "8")
        # 根据hex值判断方向（简化逻辑）
        bullish_hex = ["1", "2", "3", "A", "B", "C"]
        return "BUY" if hex_val in bullish_hex else "SELL"
    
    def _calculate_resonance_strength(self, state: Dict) -> float:
        """计算共振强度"""
        # 基于周期权重计算
        weights = {"mn1": 0.4, "w1": 0.35, "d1": 0.25}
        strength = 0
        
        for tf, weight in weights.items():
            hex_val = state.get(f"{tf}_hex", "8")
            if hex_val != "8":
                strength += weight
        
        return min(strength, 1.0)
    
    async def _predict_breakout_direction(self, contraction_data: Dict) -> Dict:
        """预测突破方向"""
        symbol = contraction_data.get("symbol")
        
        # 基于历史统计预测
        # 实际实现中应查询历史数据库
        return {
            "direction": "UP",  # 或 "DOWN"
            "confidence": 0.65,
            "target_price": contraction_data.get("upper_bound") * 1.02,
            "reasoning": "基于收缩区间统计，向上突破概率较高"
        }
    
    async def _perform_research(self):
        """执行定期研究任务"""
        # 扫描所有监控品种
        # 生成研究报告
        pass


class RiskAgent(BaseAgent):
    """
    风控Agent
    
    负责实时监控风险、触发风控措施、生成风险报告。
    """
    
    def __init__(self, agent_id: str, message_bus: MessageBus,
                 risk_limits: Dict[str, Any]):
        super().__init__(agent_id, "risk_management", message_bus)
        self.risk_limits = risk_limits
        self.current_exposure: Dict[str, float] = {}
        self.daily_pnl: float = 0.0
        self.risk_events: List[Dict] = []
    
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        if message.msg_type == MessageType.RISK_CHECK:
            # 风险检查请求
            order = message.payload.get("order")
            risk_result = await self._check_order_risk(order)
            
            return AgentMessage(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                msg_type=MessageType.RISK_RESPONSE,
                priority=Priority.HIGH,
                payload=risk_result
            )
        
        elif message.msg_type == MessageType.EXECUTION_REPORT:
            # 更新风险状态
            await self._update_risk_state(message.payload)
        
        elif message.msg_type == MessageType.MARKET_DATA:
            # 检查市场风险
            await self._check_market_risk(message.payload)
        
        return None
    
    async def run(self):
        """风控Agent主循环"""
        while self.status != AgentStatus.STOPPED:
            # 定期风险评估
            await self._perform_risk_assessment()
            await asyncio.sleep(30)  # 每30秒评估一次
    
    async def _check_order_risk(self, order: Dict) -> Dict:
        """检查订单风险"""
        symbol = order.get("symbol")
        volume = order.get("volume", 0)
        direction = order.get("direction", "")
        
        checks = {
            "position_limit": self._check_position_limit(symbol, volume),
            "exposure_limit": self._check_exposure_limit(symbol, volume, direction),
            "daily_loss_limit": self._check_daily_loss_limit(),
            "margin_limit": self._check_margin_limit(order)
        }
        
        approved = all(checks.values())
        
        return {
            "approved": approved,
            "checks": checks,
            "suggested_volume": self._suggest_volume(order) if not approved else None,
            "reason": None if approved else self._get_rejection_reason(checks)
        }
    
    def _check_position_limit(self, symbol: str, volume: float) -> bool:
        """检查持仓限额"""
        limit = self.risk_limits.get("max_position_per_symbol", 10)
        current = self.current_exposure.get(symbol, 0)
        return (current + volume) <= limit
    
    def _check_exposure_limit(self, symbol: str, volume: float, direction: str) -> bool:
        """检查敞口限额"""
        limit = self.risk_limits.get("max_total_exposure", 100)
        total = sum(self.current_exposure.values()) + volume
        return total <= limit
    
    def _check_daily_loss_limit(self) -> bool:
        """检查日亏损限额"""
        limit = self.risk_limits.get("max_daily_loss", -1000)
        return self.daily_pnl > limit
    
    def _check_margin_limit(self, order: Dict) -> bool:
        """检查保证金限额"""
        # 简化实现
        return True
    
    def _suggest_volume(self, order: Dict) -> float:
        """建议调整后的交易量"""
        symbol = order.get("symbol")
        limit = self.risk_limits.get("max_position_per_symbol", 10)
        current = self.current_exposure.get(symbol, 0)
        return max(0, limit - current)
    
    def _get_rejection_reason(self, checks: Dict) -> str:
        """获取拒绝原因"""
        failed = [k for k, v in checks.items() if not v]
        return f"风控检查未通过: {', '.join(failed)}"
    
    async def _update_risk_state(self, execution: Dict):
        """更新风险状态"""
        symbol = execution.get("symbol")
        volume = execution.get("volume", 0)
        pnl = execution.get("pnl", 0)
        
        self.current_exposure[symbol] = self.current_exposure.get(symbol, 0) + volume
        self.daily_pnl += pnl
    
    async def _check_market_risk(self, market_data: Dict):
        """检查市场风险"""
        # 检查异常波动
        volatility = market_data.get("volatility", 0)
        if volatility > self.risk_limits.get("max_volatility_threshold", 0.05):
            await self.broadcast(
                msg_type=MessageType.SYSTEM_EVENT,
                payload={
                    "event": "high_volatility_alert",
                    "symbol": market_data.get("symbol"),
                    "volatility": volatility
                },
                priority=Priority.CRITICAL
            )
    
    async def _perform_risk_assessment(self):
        """执行定期风险评估"""
        # 生成风险报告
        # 检查是否需要触发风控措施
        pass


class TraderAgent(BaseAgent):
    """
    交易员Agent
    
    综合各方信息做出交易决策。
    """
    
    def __init__(self, agent_id: str, message_bus: MessageBus,
                 signal_scorer: Optional[Any] = None):
        super().__init__(agent_id, "trader", message_bus)
        self.signal_scorer = signal_scorer
        self.pending_signals: List[Dict] = []
        self.active_orders: Dict[str, Dict] = {}
    
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        if message.msg_type == MessageType.SIGNAL:
            # 收到交易信号
            await self._evaluate_signal(message.payload, message.from_agent)
        
        elif message.msg_type == MessageType.RESEARCH_REPORT:
            # 收到研究报告
            await self._process_research_report(message.payload)
        
        elif message.msg_type == MessageType.RISK_RESPONSE:
            # 收到风控响应
            await self._process_risk_response(message.payload)
        
        elif message.msg_type == MessageType.BREAKOUT_CONFIRMED:
            # 收到突破确认
            await self._process_breakout(message.payload)
        
        return None
    
    async def run(self):
        """交易员Agent主循环"""
        while self.status != AgentStatus.STOPPED:
            # 处理待处理信号
            await self._process_pending_signals()
            await asyncio.sleep(10)
    
    async def _evaluate_signal(self, signal: Dict, source: str):
        """评估交易信号"""
        # 1. 信号质量评分
        if self.signal_scorer:
            score = self.signal_scorer.score_signal(signal)
            signal["quality_score"] = score
        
        # 2. 检查信号置信度
        confidence = signal.get("confidence", 0)
        if confidence < 0.6:
            return  # 置信度太低，忽略
        
        # 3. 发送风控检查
        order = self._signal_to_order(signal)
        await self.send_message(
            to_agent="risk",
            msg_type=MessageType.RISK_CHECK,
            payload={"order": order},
            priority=Priority.HIGH,
            requires_ack=True
        )
        
        # 暂存信号等待风控响应
        self.pending_signals.append({
            "signal": signal,
            "order": order,
            "source": source,
            "timestamp": datetime.now()
        })
    
    def _signal_to_order(self, signal: Dict) -> Dict:
        """将信号转换为订单"""
        return {
            "symbol": signal.get("symbol"),
            "direction": signal.get("direction"),
            "volume": self._calculate_position_size(signal),
            "entry_type": "market",
            "sl": signal.get("stop_loss"),
            "tp": signal.get("take_profit")
        }
    
    def _calculate_position_size(self, signal: Dict) -> float:
        """计算仓位大小"""
        # 基于Kelly准则简化版
        confidence = signal.get("confidence", 0.5)
        return min(confidence * 10, 5)  # 最大5手
    
    async def _process_risk_response(self, response: Dict):
        """处理风控响应"""
        if response.get("approved"):
            # 风控通过，发送执行指令
            order = response.get("order")
            await self.send_message(
                to_agent="execution",
                msg_type=MessageType.ORDER,
                payload=order,
                priority=Priority.HIGH
            )
        else:
            # 风控拒绝，记录原因
            print(f"订单被风控拒绝: {response.get('reason')}")
    
    async def _process_breakout(self, breakout_data: Dict):
        """处理突破确认"""
        # 突破确认后，快速生成交易指令
        signal = {
            "symbol": breakout_data.get("symbol"),
            "direction": "BUY" if breakout_data.get("direction") == "UP" else "SELL",
            "confidence": breakout_data.get("confidence", 0.7),
            "entry_price": breakout_data.get("breakout_price"),
            "stop_loss": breakout_data.get("stop_loss"),
            "take_profit": breakout_data.get("target_price"),
            "reasoning": f"突破确认: {breakout_data.get('reasoning')}"
        }
        
        await self._evaluate_signal(signal, "observer")
    
    async def _process_pending_signals(self):
        """处理待处理信号"""
        # 清理超时信号
        now = datetime.now()
        self.pending_signals = [
            s for s in self.pending_signals 
            if (now - s["timestamp"]).seconds < 300  # 5分钟超时
        ]


class ObserverAgent(BaseAgent):
    """
    观察Agent（特色Agent）
    
    专门追踪收缩-突破-趋势全生命周期。
    """
    
    def __init__(self, agent_id: str, message_bus: MessageBus,
                 contraction_engine: Any, state_hex_engine: Any):
        super().__init__(agent_id, "observer", message_bus)
        self.contraction_engine = contraction_engine
        self.state_hex_engine = state_hex_engine
        self.contraction_registry: Dict[str, Dict] = {}  # 品种 -> 收缩状态
        self.breakout_registry: Dict[str, Dict] = {}     # 品种 -> 突破状态
        self.trend_registry: Dict[str, Dict] = {}        # 品种 -> 趋势状态
    
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        if message.msg_type == MessageType.MARKET_DATA:
            # 处理市场数据，更新观察状态
            await self._update_observation(message.payload)
        
        return None
    
    async def run(self):
        """观察Agent主循环"""
        while self.status != AgentStatus.STOPPED:
            # 扫描所有品种的收缩/突破/趋势状态
            await self._scan_all_symbols()
            await asyncio.sleep(5)  # 每5秒扫描一次
    
    async def _update_observation(self, market_data: Dict):
        """更新观察状态"""
        symbol = market_data.get("symbol")
        
        # 1. 检查收缩状态
        contraction = await self._check_contraction(symbol, market_data)
        if contraction:
            self.contraction_registry[symbol] = contraction
            
            # 发送收缩预警
            if contraction.get("is_new"):
                await self.broadcast(
                    msg_type=MessageType.CONTRACTION_ALERT,
                    payload=contraction,
                    priority=Priority.HIGH
                )
        
        # 2. 检查突破（如果处于收缩状态）
        if symbol in self.contraction_registry:
            breakout = await self._check_breakout(symbol, market_data)
            if breakout:
                self.breakout_registry[symbol] = breakout
                del self.contraction_registry[symbol]  # 移除收缩记录
                
                # 发送突破确认
                await self.broadcast(
                    msg_type=MessageType.BREAKOUT_CONFIRMED,
                    payload=breakout,
                    priority=Priority.CRITICAL
                )
        
        # 3. 检查趋势状态（如果处于突破状态）
        if symbol in self.breakout_registry:
            trend_update = await self._check_trend(symbol, market_data)
            if trend_update:
                self.trend_registry[symbol] = trend_update
                
                # 发送趋势更新
                await self.broadcast(
                    msg_type=MessageType.TREND_UPDATE,
                    payload=trend_update,
                    priority=Priority.NORMAL
                )
    
    async def _check_contraction(self, symbol: str, data: Dict) -> Optional[Dict]:
        """检查收缩状态"""
        # 使用收缩检测引擎
        result = self.contraction_engine.detect(symbol, data)
        
        if result.get("is_contracting"):
            return {
                "symbol": symbol,
                "is_new": symbol not in self.contraction_registry,
                "contraction_score": result.get("score", 0),
                "duration_bars": result.get("duration", 0),
                "upper_bound": result.get("upper_bound"),
                "lower_bound": result.get("lower_bound"),
                "indicators": result.get("indicators", {})
            }
        
        return None
    
    async def _check_breakout(self, symbol: str, data: Dict) -> Optional[Dict]:
        """检查突破"""
        contraction = self.contraction_registry.get(symbol)
        if not contraction:
            return None
        
        price = data.get("close")
        upper = contraction.get("upper_bound")
        lower = contraction.get("lower_bound")
        
        if not all([price, upper, lower]):
            return None
        
        # 突破判定
        breakout_up = price > upper
        breakout_down = price < lower
        
        if breakout_up or breakout_down:
            direction = "UP" if breakout_up else "DOWN"
            
            # 计算目标位（基于收缩区间高度投影）
            range_height = upper - lower
            if direction == "UP":
                target = upper + range_height * 1.618  # 斐波那契扩展
                stop = lower
            else:
                target = lower - range_height * 1.618
                stop = upper
            
            return {
                "symbol": symbol,
                "direction": direction,
                "breakout_price": price,
                "target_price": target,
                "stop_loss": stop,
                "contraction_duration": contraction.get("duration_bars"),
                "confidence": self._calculate_breakout_confidence(data, direction)
            }
        
        return None
    
    def _calculate_breakout_confidence(self, data: Dict, direction: str) -> float:
        """计算突破置信度"""
        # 基于成交量、波动率等计算
        volume_ratio = data.get("volume_ratio", 1)
        volatility = data.get("volatility", 0)
        
        score = 0.5
        if volume_ratio > 3:
            score += 0.2
        if volatility > 0.02:
            score += 0.15
        
        return min(score, 1.0)
    
    async def _check_trend(self, symbol: str, data: Dict) -> Optional[Dict]:
        """检查趋势状态"""
        # 使用State Hex判断趋势
        state = self.state_hex_engine.get_current_state(symbol)
        
        return {
            "symbol": symbol,
            "trend_state": state.get("d1_hex"),
            "trend_strength": self._get_trend_strength(state),
            "recommendation": self._get_trend_recommendation(state)
        }
    
    def _get_trend_strength(self, state: Dict) -> str:
        """获取趋势强度"""
        hex_val = state.get("d1_hex", "8")
        # 简化判断
        strong_trend = ["1", "F"]
        moderate_trend = ["2", "E", "3", "D"]
        
        if hex_val in strong_trend:
            return "strong"
        elif hex_val in moderate_trend:
            return "moderate"
        return "weak"
    
    def _get_trend_recommendation(self, state: Dict) -> str:
        """获取趋势建议"""
        strength = self._get_trend_strength(state)
        hex_val = state.get("d1_hex", "8")
        
        bullish = ["1", "2", "3", "A", "B", "C"]
        
        if hex_val in bullish:
            if strength == "strong":
                return "hold_long"
            return "consider_long"
        else:
            if strength == "strong":
                return "hold_short"
            return "consider_short"
    
    async def _scan_all_symbols(self):
        """扫描所有品种"""
        # 实际实现中从配置读取监控品种列表
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
        
        for symbol in symbols:
            # 获取最新数据并更新观察
            pass


class AgentOrchestrator:
    """
    Agent编排器
    
    管理所有Agent的生命周期和协作调度。
    """
    
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {}
    
    def register_agent(self, agent: BaseAgent) -> str:
        """注册Agent"""
        self.agents[agent.agent_id] = agent
        return agent.agent_id
    
    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
    
    async def start_agent(self, agent_id: str):
        """启动Agent"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} 未注册")
        
        agent = self.agents[agent_id]
        task = asyncio.create_task(agent.run())
        self.agent_tasks[agent_id] = task
    
    async def stop_agent(self, agent_id: str):
        """停止Agent"""
        if agent_id in self.agent_tasks:
            self.agent_tasks[agent_id].cancel()
            del self.agent_tasks[agent_id]
        
        if agent_id in self.agents:
            self.agents[agent_id].status = AgentStatus.STOPPED
    
    async def start_all(self):
        """启动所有Agent"""
        for agent_id in self.agents:
            await self.start_agent(agent_id)
    
    async def stop_all(self):
        """停止所有Agent"""
        for agent_id in list(self.agent_tasks.keys()):
            await self.stop_agent(agent_id)
    
    def get_agent_status(self, agent_id: str) -> Optional[AgentState]:
        """获取Agent状态"""
        if agent_id in self.agents:
            return self.agents[agent_id].get_state()
        return None
    
    def get_all_status(self) -> List[AgentState]:
        """获取所有Agent状态"""
        return [agent.get_state() for agent in self.agents.values()]
    
    async def broadcast_system_event(self, event_type: str, payload: Dict):
        """广播系统事件"""
        msg = AgentMessage(
            from_agent="orchestrator",
            to_agent=None,
            msg_type=MessageType.SYSTEM_EVENT,
            priority=Priority.HIGH,
            payload={"event_type": event_type, **payload}
        )
        await self.message_bus.publish(msg)
```

---

## 四、数据处理模块

### 4.1 模块概述
统一数据接口，支持MT4/MT5实时数据、历史数据加载、多周期数据对齐和数据质量监控。

### 4.2 核心类设计

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class DataSource(ABC):
    """数据源抽象基类"""
    
    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, 
                  start: str, end: str) -> pd.DataFrame:
        """获取OHLCV数据"""
        pass
    
    @abstractmethod
    def get_tick(self, symbol: str) -> Dict:
        """获取最新Tick"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass


class MT5DataSource(DataSource):
    """MT5数据源"""
    
    def __init__(self, bridge: 'MT5Bridge'):
        self.bridge = bridge
        self.cache: Dict[str, pd.DataFrame] = {}
    
    def get_ohlcv(self, symbol: str, timeframe: str,
                  start: str, end: str) -> pd.DataFrame:
        """从MT5获取历史数据"""
        cache_key = f"{symbol}_{timeframe}_{start}_{end}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 通过ZeroMQ请求数据
        data = self.bridge.request_history(symbol, timeframe, start, end)
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        self.cache[cache_key] = df
        return df
    
    def get_tick(self, symbol: str) -> Dict:
        """获取最新Tick"""
        return self.bridge.get_latest_tick(symbol)
    
    def is_connected(self) -> bool:
        return self.bridge.is_connected()


class ParquetDataSource(DataSource):
    """Parquet文件数据源（历史数据）"""
    
    def __init__(self, data_dir: str = "data/historical"):
        self.data_dir = data_dir
    
    def get_ohlcv(self, symbol: str, timeframe: str,
                  start: str, end: str) -> pd.DataFrame:
        """从Parquet文件加载"""
        filepath = f"{self.data_dir}/{symbol}_{timeframe}.parquet"
        
        df = pd.read_parquet(filepath)
        df = df[(df.index >= start) & (df.index <= end)]
        
        return df
    
    def get_tick(self, symbol: str) -> Dict:
        raise NotImplementedError("Parquet数据源不支持Tick")
    
    def is_connected(self) -> bool:
        return True


class DataPipeline:
    """
    数据处理管道
    
    统一数据入口，支持多数据源切换和数据质量监控。
    """
    
    def __init__(self):
        self.sources: Dict[str, DataSource] = {}
        self.primary_source: Optional[str] = None
        self.quality_metrics: Dict[str, Any] = {}
    
    def register_source(self, name: str, source: DataSource, primary: bool = False):
        """注册数据源"""
        self.sources[name] = source
        if primary:
            self.primary_source = name
    
    def get_data(self, symbol: str, timeframe: str,
                 start: str, end: str, source: Optional[str] = None) -> pd.DataFrame:
        """获取数据（自动选择数据源）"""
        src_name = source or self.primary_source
        
        if not src_name or src_name not in self.sources:
            raise ValueError(f"数据源 {src_name} 未注册")
        
        source_obj = self.sources[src_name]
        
        if not source_obj.is_connected():
            # 尝试备用数据源
            for name, src in self.sources.items():
                if src.is_connected():
                    source_obj = src
                    break
        
        df = source_obj.get_ohlcv(symbol, timeframe, start, end)
        
        # 数据质量检查
        self._check_quality(df, symbol, timeframe)
        
        return df
    
    def _check_quality(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """数据质量检查"""
        checks = {
            "missing_values": df.isnull().sum().sum(),
            "duplicate_timestamps": df.index.duplicated().sum(),
            "gaps": self._detect_gaps(df),
            "outliers": self._detect_outliers(df)
        }
        
        self.quality_metrics[f"{symbol}_{timeframe}"] = checks
    
    def _detect_gaps(self, df: pd.DataFrame) -> List:
        """检测数据缺口"""
        # 简化实现
        return []
    
    def _detect_outliers(self, df: pd.DataFrame) -> int:
        """检测异常值"""
        # 使用IQR方法
        Q1 = df['close'].quantile(0.25)
        Q3 = df['close'].quantile(0.75)
        IQR = Q3 - Q1
        outliers = ((df['close'] < (Q1 - 3 * IQR)) | (df['close'] > (Q3 + 3 * IQR))).sum()
        return int(outliers)


class MultiTimeframeAligner:
    """
    多周期数据对齐器
    
    将不同周期的数据对齐到统一时间轴。
    """
    
    def __init__(self, base_timeframe: str = "H1"):
        self.base_tf = base_timeframe
    
    def align(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        对齐多周期数据
        
        策略:
        1. 以最小周期为基准时间轴
        2. 大周期数据前向填充
        3. 添加周期标识列
        """
        # 找到最小周期
        base_tf = min(data_dict.keys(), key=lambda x: self._tf_to_minutes(x))
        base_index = data_dict[base_tf].index
        
        aligned_data = pd.DataFrame(index=base_index)
        
        for tf, df in data_dict.items():
            # 重命名列添加周期前缀
            prefix = tf.lower()
            renamed = df.add_prefix(f"{prefix}_")
            
            # 对齐到基准时间轴
            aligned = renamed.reindex(base_index, method='ffill')
            
            # 合并
            aligned_data = pd.concat([aligned_data, aligned], axis=1)
        
        return aligned_data
    
    @staticmethod
    def _tf_to_minutes(tf: str) -> int:
        mapping = {'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30,
                   'H1': 60, 'H4': 240, 'D1': 1440, 'W1': 10080}
        return mapping.get(tf, 60)
```

---

## 五、监控与报告模块

### 5.1 模块概述
实时监控系统状态、Agent状态、交易执行情况，生成各类报告。

### 5.2 核心类设计

```python
from typing import Dict, List, Any
from datetime import datetime
import json

class MonitoringService:
    """监控服务"""
    
    def __init__(self, orchestrator: AgentOrchestrator, message_bus: MessageBus):
        self.orchestrator = orchestrator
        self.message_bus = message_bus
        self.metrics: Dict[str, Any] = {}
        self.alerts: List[Dict] = []
    
    async def collect_metrics(self):
        """收集指标"""
        # Agent状态
        agent_status = self.orchestrator.get_all_status()
        self.metrics["agents"] = [
            {
                "id": s.agent_id,
                "type": s.agent_type,
                "status": s.status.value,
                "metrics": s.metrics
            }
            for s in agent_status
        ]
        
        # 消息吞吐量
        self.metrics["message_count"] = len(self.message_bus.message_history)
        
        # 系统资源
        import psutil
        self.metrics["system"] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
    
    def get_dashboard_data(self) -> Dict:
        """获取监控面板数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "agents": self.metrics.get("agents", []),
            "system": self.metrics.get("system", {}),
            "recent_alerts": self.alerts[-10:],
            "message_stats": {
                "total": self.metrics.get("message_count", 0),
                "by_type": self._count_messages_by_type()
            }
        }
    
    def _count_messages_by_type(self) -> Dict:
        """按类型统计消息"""
        from collections import Counter
        types = [m.msg_type.value for m in self.message_bus.message_history[-1000:]]
        return dict(Counter(types))


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, template_dir: str = "templates/reports"):
        self.template_dir = template_dir
    
    def generate_backtest_report(self, result: BacktestResult, 
                                  format: str = "html") -> str:
        """生成回测报告"""
        if format == "html":
            return self._generate_html_report(result)
        elif format == "pdf":
            return self._generate_pdf_report(result)
        elif format == "json":
            return json.dumps(self._report_to_dict(result))
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def _generate_html_report(self, result: BacktestResult) -> str:
        """生成HTML报告"""
        # 使用Jinja2模板
        from jinja2 import Template
        
        template_str = """
        <!DOCTYPE html>
        <html>
        <head><title>回测报告</title></head>
        <body>
            <h1>策略回测报告</h1>
            <h2>绩效指标</h2>
            <table>
                <tr><td>总收益率</td><td>{{ metrics.total_return }}%</td></tr>
                <tr><td>年化收益</td><td>{{ metrics.annual_return }}%</td></tr>
                <tr><td>夏普比率</td><td>{{ metrics.sharpe_ratio }}</td></tr>
                <tr><td>最大回撤</td><td>{{ metrics.max_drawdown }}%</td></tr>
                <tr><td>胜率</td><td>{{ metrics.win_rate }}%</td></tr>
            </table>
            <h2>交易统计</h2>
            <p>总交易次数: {{ metrics.total_trades }}</p>
            <p>盈亏比: {{ metrics.profit_factor }}</p>
        </body>
        </html>
        """
        
        template = Template(template_str)
        return template.render(metrics=result.metrics)
    
    def _generate_pdf_report(self, result: BacktestResult) -> str:
        """生成PDF报告"""
        # 使用weasyprint或reportlab
        html = self._generate_html_report(result)
        # 转换为PDF...
        return "report.pdf"
    
    def _report_to_dict(self, result: BacktestResult) -> Dict:
        """转换为字典"""
        return {
            "metrics": result.metrics,
            "trade_summary": {
                "total_trades": len(result.trades),
                "winning_trades": len([t for t in result.trades if t.pnl > 0]),
                "losing_trades": len([t for t in result.trades if t.pnl <= 0])
            },
            "monthly_returns": result.monthly_returns.to_dict(),
            "generated_at": datetime.now().isoformat()
        }
```

---

## 六、附录

### 6.1 模块依赖关系

```
nl_strategy.py
  ├── llm_gateway.py
  ├── template_registry.py
  └── strategy_validator.py

backtest_engine.py
  ├── data_pipeline.py
  ├── multi_timeframe_aligner.py
  └── metrics_calculator.py

agent_system.py
  ├── message_bus.py
  ├── base_agent.py
  ├── research_agent.py
  ├── trader_agent.py
  ├── risk_agent.py
  ├── observer_agent.py
  └── agent_orchestrator.py

data_pipeline.py
  ├── data_source.py (abstract)
  ├── mt5_data_source.py
  └── parquet_data_source.py

monitoring.py
  └── report_generator.py
```

### 6.2 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-06 | 初始版本 | Qoder AI |
