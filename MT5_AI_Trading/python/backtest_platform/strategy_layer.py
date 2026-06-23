"""
策略层 (Strategy Layer)

职责: 策略定义、注册、组合、参数优化。

模块:
- StrategyRegistry: 策略注册中心
- BaseStrategy: 策略抽象基类
- P107StateHexStrategy: P107 State Hex策略插件（封装现有TradingStrategy）
- WalkForwardOptimizer: Walk-Forward参数优化器

核心原则:
- 策略只负责"在什么条件下产生什么信号"
- 策略不负责执行细节（由执行层处理）
- 信号包含元数据（三元组、标签等），供执行层和展示层使用
- 禁止策略输出动作语义
"""

import os
import sys
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any, Type
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_engine.state_hex_encoding import StateHexEncoder
from ai_engine.state_hex_engine import StateHexEngine, StateHexTriplet
from ai_engine.moneyflow_energy_layer import (
    MoneyflowEnergyLayer, EnergyLabel, EnergyAssessment
)
from ai_engine.trading_strategy import TradingStrategy, RiskParameters
from backtest_platform.compute_layer import (
    DailyFeatures, FeaturePipeline, FusedState
)

logger = logging.getLogger(__name__)


# ============================================================================
# 核心数据类
# ============================================================================

@dataclass
class Signal:
    """交易信号（策略层输出，执行层输入）"""
    direction: str              # "long" | "short" | "close"
    size: float                 # 手数
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    confidence: float           # 0.0 ~ 1.0
    timestamp: datetime

    # 元数据（State Hex上下文）
    symbol: str = ""
    triplet: Optional[StateHexTriplet] = None
    state_tags: List[str] = field(default_factory=list)
    state_alignment: str = ""
    fused_confidence: Optional[float] = None

    # 元数据（资金流）
    energy_label: Optional[str] = None
    energy_assessment: Optional[EnergyAssessment] = None

    # 元数据（策略来源）
    strategy_name: str = ""
    strategy_params: Dict[str, Any] = field(default_factory=dict)

    # 元数据（理由）
    reasoning: str = ""


@dataclass
class PortfolioState:
    """账户状态（策略决策时传入）"""
    balance: float
    equity: float
    open_positions: List[Dict[str, Any]] = field(default_factory=list)
    daily_pnl: float = 0.0
    total_trades_today: int = 0


@dataclass
class StrategyInfo:
    """策略信息"""
    name: str
    description: str
    param_schema: Dict[str, Any]
    strategy_class: Type['BaseStrategy']


@dataclass
class WalkForwardResult:
    """Walk-Forward优化结果"""
    strategy_name: str
    optimal_params: Dict[str, Any]
    train_metrics: List[Dict[str, float]]
    test_metrics: List[Dict[str, float]]
    combined_sharpe: float
    param_stability: float


# ============================================================================
# 策略抽象基类
# ============================================================================

class BaseStrategy(ABC):
    """
    策略基类

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
    def description(self) -> str:
        """策略描述"""
        pass

    @property
    @abstractmethod
    def param_schema(self) -> Dict[str, Any]:
        """
        参数schema（用于优化器）

        格式:
        {
            "param_name": {
                "type": "float" | "int" | "choice",
                "min": 0.0,
                "max": 1.0,
                "default": 0.6,
                "options": ["a", "b"]  # 仅choice类型
            }
        }
        """
        pass

    def __init__(self, **params):
        """初始化策略参数"""
        self.params = self._apply_defaults(params)
        self.signal_history: List[Signal] = []
        self._validate_params()

    def _apply_defaults(self, user_params: Dict[str, Any]) -> Dict[str, Any]:
        """应用默认参数"""
        result = {}
        for key, schema in self.param_schema.items():
            if key in user_params:
                result[key] = user_params[key]
            else:
                result[key] = schema.get("default")
        return result

    def _validate_params(self):
        """验证参数合法性"""
        for key, value in self.params.items():
            if key not in self.param_schema:
                logger.warning(f"未知参数: {key}")
                continue

            schema = self.param_schema[key]
            param_type = schema.get("type")

            if param_type == "float":
                min_val = schema.get("min")
                max_val = schema.get("max")
                if min_val is not None and value < min_val:
                    logger.warning(f"参数 {key}={value} 低于最小值 {min_val}")
                if max_val is not None and value > max_val:
                    logger.warning(f"参数 {key}={value} 超过最大值 {max_val}")

            elif param_type == "int":
                min_val = schema.get("min")
                max_val = schema.get("max")
                if min_val is not None and value < min_val:
                    logger.warning(f"参数 {key}={value} 低于最小值 {min_val}")
                if max_val is not None and value > max_val:
                    logger.warning(f"参数 {key}={value} 超过最大值 {max_val}")

            elif param_type == "choice":
                options = schema.get("options", [])
                if options and value not in options:
                    logger.warning(f"参数 {key}={value} 不在选项 {options} 中")

    @abstractmethod
    def on_daily_features(
        self,
        features: DailyFeatures,
        portfolio: PortfolioState,
    ) -> Optional[Signal]:
        """
        每日触发

        Args:
            features: 当日特征（含State Hex三元组、MISS、资金流）
            portfolio: 当前账户状态

        Returns:
            Signal 或 None
        """
        pass

    def on_tick(
        self,
        tick: Dict[str, Any],
        portfolio: PortfolioState,
    ) -> Optional[Signal]:
        """
        Tick级触发（可选实现）

        默认不实现，子类可覆盖
        """
        return None

    def reset(self):
        """重置策略状态"""
        self.signal_history = []

    def get_signal_summary(self) -> Dict[str, Any]:
        """获取信号统计摘要"""
        signals = self.signal_history
        if not signals:
            return {"total_signals": 0}

        long_signals = [s for s in signals if s.direction == "long"]
        short_signals = [s for s in signals if s.direction == "short"]

        return {
            "total_signals": len(signals),
            "long_signals": len(long_signals),
            "short_signals": len(short_signals),
            "avg_confidence": np.mean([s.confidence for s in signals]) if signals else 0,
            "last_signal": signals[-1].direction if signals else None,
            "last_confidence": signals[-1].confidence if signals else 0,
        }


# ============================================================================
# P107 State Hex 策略插件
# ============================================================================

class P107StateHexStrategy(BaseStrategy):
    """
    P107 State Hex 策略插件

    将现有的 TradingStrategy 封装为回测平台策略插件。

    主线顺序:
    1. D1/W1/MN1 状态对齐（状态门）
    2. 策略条件接近（价格行为验证）
    3. 成交活跃度确认
    4. 资金流增量证据（如可用）
    5. 筹码峰结构解释（如可用）
    6. 输出信号（含元数据，不输出动作语义）
    """

    name = "P107_StateHex_v1"
    description = "基于P107 State Hex编码规则的三元组驱动策略"

    param_schema = {
        "min_confidence": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "default": 0.6,
        },
        "state_alignment_mode": {
            "type": "choice",
            "options": ["strict", "loose"],
            "default": "loose",
        },
        "max_positions": {
            "type": "int",
            "min": 1,
            "max": 20,
            "default": 5,
        },
        "enable_moneyflow": {
            "type": "choice",
            "options": [True, False],
            "default": False,
        },
        "moneyflow_threshold": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "default": 0.5,
        },
        "risk_per_trade": {
            "type": "float",
            "min": 0.001,
            "max": 0.1,
            "default": 0.02,
        },
        "sl_atr_multiplier": {
            "type": "float",
            "min": 0.5,
            "max": 5.0,
            "default": 2.0,
        },
        "tp_atr_multiplier": {
            "type": "float",
            "min": 0.5,
            "max": 10.0,
            "default": 3.0,
        },
    }

    def __init__(self, **params):
        super().__init__(**params)
        self.encoder = StateHexEncoder()
        self._init_inner_strategy()

    def _init_inner_strategy(self):
        """初始化内部TradingStrategy"""
        risk_params = RiskParameters(
            max_risk_per_trade=self.params["risk_per_trade"],
            max_positions=self.params["max_positions"],
        )
        self.inner_strategy = TradingStrategy(
            risk_params=risk_params,
            min_confidence=self.params["min_confidence"],
            state_alignment_mode=self.params["state_alignment_mode"],
        )

    def on_daily_features(
        self,
        features: DailyFeatures,
        portfolio: PortfolioState,
    ) -> Optional[Signal]:
        """
        每日触发：P107 State Hex策略逻辑
        """
        # 0. 检查持仓限制
        open_count = len(portfolio.open_positions)
        if open_count >= self.params["max_positions"]:
            return None

        # 1. 获取三元组
        triplet = features.triplet
        if triplet is None:
            return None

        # 2. 状态门检查（核心：三周期对齐）
        alignment_score, alignment_reason = self._check_state_alignment(triplet)
        if alignment_score < self.params["min_confidence"]:
            return None

        # 3. 价格行为验证（price-first）
        price_valid, price_reason = self._validate_price_action(features)
        if not price_valid:
            return None

        # 4. 资金流二级确认（如启用）
        energy_ok = True
        energy_label = None
        energy_assessment = None
        if self.params["enable_moneyflow"] and features.fused_state:
            energy_ok, energy_label, energy_assessment = self._check_energy_confirmation(features)
            if not energy_ok:
                return None

        # 5. 计算止损止盈
        atr = features.technical_indicators.get("atr")
        current_price = features.ohlcv.close
        direction = self._determine_direction(triplet)

        if direction == "neutral":
            return None

        sl, tp = self._calculate_sl_tp(current_price, direction, atr)

        # 6. 计算仓位
        position_size = self._calculate_position_size(
            portfolio.balance, current_price, sl, direction
        )

        # 7. 生成信号
        confidence = alignment_score
        if features.fused_state:
            confidence = features.fused_state.fused_confidence

        # 资金流调整
        if energy_label:
            if energy_label == EnergyLabel.ENERGY_SUPPORTIVE:
                confidence = min(1.0, confidence + 0.05)
            elif energy_label == EnergyLabel.ENERGY_DIVERGENT:
                confidence = max(0.0, confidence - 0.08)
            elif energy_label == EnergyLabel.ENERGY_OVERHEATED:
                confidence = max(0.0, confidence - 0.10)

        if confidence < self.params["min_confidence"]:
            return None

        # 构建标签
        tags = []
        if alignment_score >= 1.0:
            tags.append("状态同向")
        elif alignment_score >= 0.8:
            tags.append("高周期支撑")

        d1_score, d1_contraction, d1_vol, d1_pos, d1_trend = self.encoder.decode(triplet.d1_hex)
        if d1_contraction:
            tags.append("收缩底座")
        if d1_vol:
            tags.append("幅动活跃")
        if d1_pos:
            tags.append("位置触发")
        if d1_trend:
            tags.append("趋势触发")
        if triplet.d1_duration >= 3:
            tags.append(f"D1持续{triplet.d1_duration}天")
        if triplet.w1_duration >= 2:
            tags.append(f"W1持续{triplet.w1_duration}周")

        # 融合标签
        if features.fused_state:
            tags.extend(features.fused_state.fused_tags)

        # 构建理由（解释性语义，非动作建议）
        reasoning = (
            f"状态观察 | 三元组({triplet.mn1_hex},{triplet.w1_hex},{triplet.d1_hex}) | "
            f"{alignment_reason}"
        )
        if features.fused_state:
            reasoning += f" | {features.fused_state.explanation}"
        if energy_assessment:
            reasoning += f" | 能量: {energy_assessment.explanation}"

        signal = Signal(
            direction=direction,
            size=position_size,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            confidence=confidence,
            timestamp=features.timestamp,
            symbol="",  # 由上层填充
            triplet=triplet,
            state_tags=tags,
            state_alignment=alignment_reason,
            fused_confidence=features.fused_state.fused_confidence if features.fused_state else None,
            energy_label=energy_label.value if energy_label else None,
            energy_assessment=energy_assessment,
            strategy_name=self.name,
            strategy_params=self.params.copy(),
            reasoning=reasoning,
        )

        self.signal_history.append(signal)
        return signal

    def _check_state_alignment(self, triplet: StateHexTriplet) -> Tuple[float, str]:
        """检查三周期状态对齐"""
        mn1 = triplet.mn1_hex
        w1 = triplet.w1_hex
        d1 = triplet.d1_hex

        mn1_score = self.encoder._from_signed_hex(mn1)
        w1_score = self.encoder._from_signed_hex(w1)
        d1_score = self.encoder._from_signed_hex(d1)

        mn1_bull = mn1_score > 0
        w1_bull = w1_score > 0
        d1_bull = d1_score > 0
        mn1_bear = mn1_score < 0
        w1_bear = w1_score < 0
        d1_bear = d1_score < 0

        mode = self.params["state_alignment_mode"]

        if mode == "strict":
            if mn1_bull and w1_bull and d1_bull:
                return 1.0, f"三周期多向对齐 ({mn1},{w1},{d1})"
            elif mn1_bear and w1_bear and d1_bear:
                return 1.0, f"三周期空向对齐 ({mn1},{w1},{d1})"
            else:
                return 0.0, f"三周期未对齐 ({mn1},{w1},{d1})"
        else:
            if mn1_bull and w1_score >= 0 and d1_bull:
                score = 0.8
                if w1_bull:
                    score += 0.1
                if triplet.w1_duration >= 2:
                    score += 0.05
                if triplet.d1_duration >= 2:
                    score += 0.05
                return min(score, 1.0), f"高周期支撑多头 ({mn1},{w1},{d1})"
            elif mn1_bear and w1_score <= 0 and d1_bear:
                score = 0.8
                if w1_bear:
                    score += 0.1
                if triplet.w1_duration >= 2:
                    score += 0.05
                if triplet.d1_duration >= 2:
                    score += 0.05
                return min(score, 1.0), f"高周期支撑空头 ({mn1},{w1},{d1})"

            return 0.0, f"状态不支持 ({mn1},{w1},{d1})"

    def _validate_price_action(self, features: DailyFeatures) -> Tuple[bool, str]:
        """价格行为验证"""
        triplet = features.triplet
        if triplet is None:
            return False, "无三元组"

        d1_score = self.encoder._from_signed_hex(triplet.d1_hex)
        current_price = features.ohlcv.close

        # 使用技术指标辅助验证
        sma20 = features.technical_indicators.get("sma20")
        if sma20 is not None:
            if d1_score > 0 and current_price < sma20:
                return False, "状态多向但价格低于SMA20"
            if d1_score < 0 and current_price > sma20:
                return False, "状态空向但价格高于SMA20"

        return True, "价格行为与状态一致"

    def _check_energy_confirmation(
        self,
        features: DailyFeatures,
    ) -> Tuple[bool, Optional[EnergyLabel], Optional[EnergyAssessment]]:
        """资金流能量确认"""
        if features.fused_state is None or features.fused_state.miss_snapshot is None:
            return True, None, None

        # 简化：基于MISS的volume_state判断
        miss = features.fused_state.miss_snapshot

        # 如果MISS显示成交萎缩，可能能量不足
        if miss.volume_state == "shrinking":
            return True, EnergyLabel.ENERGY_INSUFFICIENT, None

        return True, None, None

    def _determine_direction(self, triplet: StateHexTriplet) -> str:
        """确定方向"""
        d1_score = self.encoder._from_signed_hex(triplet.d1_hex)
        if d1_score > 0:
            return "long"
        elif d1_score < 0:
            return "short"
        return "neutral"

    def _calculate_sl_tp(
        self,
        current_price: float,
        direction: str,
        atr: Optional[float],
    ) -> Tuple[Optional[float], Optional[float]]:
        """计算止损止盈"""
        if atr is None or atr <= 0:
            atr = current_price * 0.005

        sl_mult = self.params["sl_atr_multiplier"]
        tp_mult = self.params["tp_atr_multiplier"]

        if direction == "long":
            sl = current_price - atr * sl_mult
            tp = current_price + atr * tp_mult
        else:
            sl = current_price + atr * sl_mult
            tp = current_price - atr * tp_mult

        return sl, tp

    def _calculate_position_size(
        self,
        balance: float,
        entry_price: float,
        stop_loss: Optional[float],
        direction: str,
    ) -> float:
        """计算仓位大小"""
        if not stop_loss or stop_loss <= 0 or entry_price <= 0:
            return 0.01

        risk_amount = balance * self.params["risk_per_trade"]
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit <= 0:
            return 0.01

        position_size = risk_amount / risk_per_unit
        return min(position_size, 1.0)  # 最大1手


# ============================================================================
# 策略注册中心
# ============================================================================

class StrategyRegistry:
    """
    策略注册中心

    统一管理所有可回测策略，支持:
    - 策略注册/注销
    - 策略参数schema定义
    - 多策略并行回测
    """

    def __init__(self):
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        self._infos: Dict[str, StrategyInfo] = {}

        # 自动注册内置策略
        self._register_builtin_strategies()

    def _register_builtin_strategies(self):
        """注册内置策略"""
        self.register(
            name=P107StateHexStrategy.name,
            strategy_class=P107StateHexStrategy,
            description=P107StateHexStrategy.description,
        )

    def register(
        self,
        name: str,
        strategy_class: Type[BaseStrategy],
        description: str = "",
    ) -> None:
        """
        注册策略

        Args:
            name: 策略唯一名称
            strategy_class: 策略类（继承BaseStrategy）
            description: 策略描述
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"策略类必须继承BaseStrategy: {strategy_class}")

        self._strategies[name] = strategy_class

        # 获取参数schema
        instance = strategy_class()  # 用默认参数实例化以获取schema
        self._infos[name] = StrategyInfo(
            name=name,
            description=description or strategy_class.description,
            param_schema=instance.param_schema,
            strategy_class=strategy_class,
        )

        logger.info(f"策略注册成功: {name}")

    def unregister(self, name: str) -> bool:
        """注销策略"""
        if name in self._strategies:
            del self._strategies[name]
            del self._infos[name]
            logger.info(f"策略已注销: {name}")
            return True
        return False

    def get(self, name: str) -> Type[BaseStrategy]:
        """获取策略类"""
        if name not in self._strategies:
            raise KeyError(f"未注册的策略: {name}")
        return self._strategies[name]

    def create_instance(self, name: str, **params) -> BaseStrategy:
        """创建策略实例"""
        strategy_class = self.get(name)
        return strategy_class(**params)

    def list_strategies(self) -> List[StrategyInfo]:
        """列出所有已注册策略"""
        return list(self._infos.values())

    def get_info(self, name: str) -> StrategyInfo:
        """获取策略信息"""
        if name not in self._infos:
            raise KeyError(f"未注册的策略: {name}")
        return self._infos[name]

    def get_param_schema(self, name: str) -> Dict[str, Any]:
        """获取策略参数schema"""
        return self.get_info(name).param_schema


# ============================================================================
# Walk-Forward 参数优化器
# ============================================================================

class WalkForwardOptimizer:
    """
    Walk-Forward 参数优化器

    避免过拟合的核心方法:
    1. 将数据分为N个训练/测试窗口
    2. 每个窗口: 训练集优化参数 → 测试集验证
    3. 汇总所有测试集结果作为最终评估
    """

    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        train_size: int = 252,    # 约1年
        test_size: int = 63,      # 约3个月
        n_splits: int = 5,
    ):
        self.strategy_class = strategy_class
        self.data = data.copy()
        self.train_size = train_size
        self.test_size = test_size
        self.n_splits = n_splits

    def optimize(
        self,
        param_grid: Dict[str, List],
        metric: str = "sharpe_ratio",
    ) -> WalkForwardResult:
        """
        执行Walk-Forward优化

        Args:
            param_grid: 参数网格，如 {"min_confidence": [0.5, 0.6, 0.7]}
            metric: 优化指标

        Returns:
            WalkForwardResult
        """
        logger.info(f"Walk-Forward优化开始 | 策略: {self.strategy_class.name} | 窗口数: {self.n_splits}")

        # 生成所有参数组合
        param_combinations = self._generate_param_combinations(param_grid)
        logger.info(f"参数组合数: {len(param_combinations)}")

        train_metrics = []
        test_metrics = []
        best_params_per_window = []

        # 生成窗口
        total_size = self.train_size + self.test_size
        step = (len(self.data) - total_size) // max(1, self.n_splits - 1)

        for i in range(self.n_splits):
            train_start = i * step
            train_end = train_start + self.train_size
            test_end = min(train_end + self.test_size, len(self.data))

            if train_end >= len(self.data):
                break

            train_data = self.data.iloc[train_start:train_end]
            test_data = self.data.iloc[train_end:test_end]

            logger.info(f"窗口 {i+1}/{self.n_splits}: 训练{len(train_data)}条 | 测试{len(test_data)}条")

            # 在训练集上寻找最优参数
            best_params, best_train_metric = self._find_best_params(
                train_data, param_combinations, metric
            )

            # 在测试集上验证
            test_metric = self._evaluate_params(test_data, best_params, metric)

            train_metrics.append(best_train_metric)
            test_metrics.append(test_metric)
            best_params_per_window.append(best_params)

            train_metric_val = best_train_metric.get(metric, 0) if isinstance(best_train_metric, dict) else best_train_metric
            test_metric_val = test_metric.get(metric, 0) if isinstance(test_metric, dict) else test_metric
            logger.info(f"  最优参数: {best_params} | 训练{metric}: {train_metric_val:.4f} | 测试{metric}: {test_metric_val:.4f}")

        # 计算参数稳定性
        param_stability = self._calc_param_stability(best_params_per_window)

        # 综合评估
        combined_sharpe = np.mean([m.get("sharpe_ratio", 0) for m in test_metrics]) if test_metrics else 0

        # 选择最稳定的参数
        optimal_params = self._select_most_stable_params(best_params_per_window)

        result = WalkForwardResult(
            strategy_name=self.strategy_class.name,
            optimal_params=optimal_params,
            train_metrics=train_metrics,
            test_metrics=test_metrics,
            combined_sharpe=combined_sharpe,
            param_stability=param_stability,
        )

        logger.info(f"Walk-Forward优化完成 | 综合Sharpe: {combined_sharpe:.4f} | 参数稳定性: {param_stability:.4f}")
        return result

    def _generate_param_combinations(self, param_grid: Dict[str, List]) -> List[Dict[str, Any]]:
        """生成参数组合"""
        from itertools import product

        keys = list(param_grid.keys())
        values = [param_grid[k] for k in keys]

        combinations = []
        for combo in product(*values):
            combinations.append(dict(zip(keys, combo)))

        return combinations

    def _find_best_params(
        self,
        train_data: pd.DataFrame,
        param_combinations: List[Dict[str, Any]],
        metric: str,
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """在训练集上寻找最优参数"""
        best_params = param_combinations[0]
        best_metric_value = -float('inf')
        best_metrics = {}

        for params in param_combinations:
            metrics = self._evaluate_params(train_data, params, metric)
            metric_value = metrics.get(metric, -float('inf'))

            if metric_value > best_metric_value:
                best_metric_value = metric_value
                best_params = params
                best_metrics = metrics

        return best_params, best_metrics

    def _evaluate_params(
        self,
        data: pd.DataFrame,
        params: Dict[str, Any],
        metric: str,
    ) -> Dict[str, float]:
        """评估参数组合"""
        # 简化评估：计算信号数量和方向一致性
        strategy = self.strategy_class(**params)
        pipeline = FeaturePipeline()

        signals = []
        for i in range(len(data)):
            try:
                features = pipeline.compute_for_backtest_day(data, i)
                portfolio = PortfolioState(balance=10000, equity=10000)
                signal = strategy.on_daily_features(features, portfolio)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.debug(f"评估异常: {e}")
                continue

        # 计算指标
        if not signals:
            return {"sharpe_ratio": 0, "win_rate": 0, "total_trades": 0}

        long_count = sum(1 for s in signals if s.direction == "long")
        short_count = sum(1 for s in signals if s.direction == "short")
        avg_confidence = np.mean([s.confidence for s in signals])

        # 简化夏普（用信号信心度模拟）
        returns = [s.confidence * (1 if s.direction == "long" else -1) for s in signals]
        sharpe = 0
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)

        return {
            "sharpe_ratio": sharpe,
            "win_rate": long_count / len(signals) if signals else 0,
            "total_trades": len(signals),
            "avg_confidence": avg_confidence,
        }

    def _calc_param_stability(self, params_list: List[Dict[str, Any]]) -> float:
        """计算参数稳定性（各窗口参数的一致性）"""
        if not params_list or len(params_list) < 2:
            return 1.0

        # 对每个参数计算变异系数
        stabilities = []
        keys = params_list[0].keys()

        for key in keys:
            values = [p[key] for p in params_list if key in p]
            if len(values) < 2:
                continue

            if isinstance(values[0], (int, float)):
                mean_val = np.mean(values)
                std_val = np.std(values)
                if mean_val != 0:
                    cv = std_val / abs(mean_val)
                    stabilities.append(1.0 - min(cv, 1.0))
                else:
                    stabilities.append(1.0)
            else:
                # 类别参数：计算众数比例
                from collections import Counter
                most_common = Counter(values).most_common(1)[0][1]
                stabilities.append(most_common / len(values))

        return np.mean(stabilities) if stabilities else 1.0

    def _select_most_stable_params(self, params_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """选择最稳定的参数"""
        if not params_list:
            return {}

        # 对每个参数选择出现最频繁的值
        result = {}
        keys = params_list[0].keys()

        for key in keys:
            values = [p[key] for p in params_list if key in p]
            if not values:
                continue

            if isinstance(values[0], (int, float)):
                result[key] = float(np.median(values))
            else:
                from collections import Counter
                result[key] = Counter(values).most_common(1)[0][0]

        return result


# ============================================================================
# 策略组合器
# ============================================================================

class StrategyCombiner:
    """
    策略组合器

    支持多策略并行回测，信号聚合方式:
    - consensus: 共识模式（多数策略同意才发信号）
    - weighted: 加权模式（按信心度加权）
    - best: 最优模式（选信心度最高的信号）
    """

    def __init__(self, strategies: List[BaseStrategy], mode: str = "consensus"):
        self.strategies = strategies
        self.mode = mode
        self.min_agreement = 0.5  # 共识模式最小同意比例

    def combine_signals(
        self,
        signals_by_strategy: Dict[str, Optional[Signal]],
    ) -> Optional[Signal]:
        """
        聚合多策略信号

        Args:
            signals_by_strategy: {策略名: Signal}

        Returns:
            聚合后的Signal或None
        """
        valid_signals = [
            (name, s) for name, s in signals_by_strategy.items()
            if s is not None
        ]

        if not valid_signals:
            return None

        if self.mode == "consensus":
            return self._consensus_mode(valid_signals)
        elif self.mode == "weighted":
            return self._weighted_mode(valid_signals)
        elif self.mode == "best":
            return self._best_mode(valid_signals)
        else:
            return self._consensus_mode(valid_signals)

    def _consensus_mode(self, signals: List[Tuple[str, Signal]]) -> Optional[Signal]:
        """共识模式"""
        long_votes = sum(1 for _, s in signals if s.direction == "long")
        short_votes = sum(1 for _, s in signals if s.direction == "short")
        total = len(signals)

        if long_votes / total >= self.min_agreement:
            # 选信心度最高的多头信号
            best = max((s for _, s in signals if s.direction == "long"), key=lambda x: x.confidence)
            best.state_tags.append(f"共识:{long_votes}/{total}")
            return best
        elif short_votes / total >= self.min_agreement:
            best = max((s for _, s in signals if s.direction == "short"), key=lambda x: x.confidence)
            best.state_tags.append(f"共识:{short_votes}/{total}")
            return best

        return None

    def _weighted_mode(self, signals: List[Tuple[str, Signal]]) -> Optional[Signal]:
        """加权模式"""
        long_signals = [s for _, s in signals if s.direction == "long"]
        short_signals = [s for _, s in signals if s.direction == "short"]

        long_weight = sum(s.confidence for s in long_signals)
        short_weight = sum(s.confidence for s in short_signals)

        if long_weight > short_weight and long_signals:
            best = max(long_signals, key=lambda x: x.confidence)
            best.state_tags.append(f"加权多头:{long_weight:.2f}")
            return best
        elif short_signals:
            best = max(short_signals, key=lambda x: x.confidence)
            best.state_tags.append(f"加权空头:{short_weight:.2f}")
            return best

        return None

    def _best_mode(self, signals: List[Tuple[str, Signal]]) -> Optional[Signal]:
        """最优模式"""
        best = max(signals, key=lambda x: x[1].confidence)
        best[1].state_tags.append(f"最优策略:{best[0]}")
        return best[1]


# ============================================================================
# 便捷函数
# ============================================================================

def create_strategy(name: str, **params) -> BaseStrategy:
    """便捷函数: 创建策略实例"""
    registry = StrategyRegistry()
    return registry.create_instance(name, **params)


def list_available_strategies() -> List[StrategyInfo]:
    """便捷函数: 列出可用策略"""
    registry = StrategyRegistry()
    return registry.list_strategies()


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Strategy Layer Test")
    print("=" * 70)

    # 1. 测试 StrategyRegistry
    print("\n[1] StrategyRegistry 测试")
    registry = StrategyRegistry()
    strategies = registry.list_strategies()
    print(f"  已注册策略数: {len(strategies)}")
    for info in strategies:
        print(f"  - {info.name}: {info.description}")
        print(f"    参数: {list(info.param_schema.keys())}")

    # 2. 测试 P107StateHexStrategy
    print("\n[2] P107StateHexStrategy 测试")
    strategy = registry.create_instance(
        "P107_StateHex_v1",
        min_confidence=0.6,
        state_alignment_mode="loose",
        enable_moneyflow=False,
    )
    print(f"  策略名称: {strategy.name}")
    print(f"  参数: {strategy.params}")

    # 3. 生成测试特征数据
    print("\n[3] 生成测试特征")
    np.random.seed(42)
    n_days = 120
    base_price = 1.0850
    dates = pd.date_range(start="2025-01-01", periods=n_days, freq="B")
    trend = np.sin(np.linspace(0, 3 * np.pi, n_days)) * 0.015
    noise = np.cumsum(np.random.randn(n_days) * 0.003)
    prices = base_price + trend + noise

    test_df = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.randn(n_days) * 0.001,
        'high': prices + abs(np.random.randn(n_days)) * 0.005,
        'low': prices - abs(np.random.randn(n_days)) * 0.005,
        'close': prices,
        'volume': np.random.randint(10000, 100000, n_days),
    })

    # 4. 测试策略信号生成
    print("\n[4] 策略信号生成测试")
    pipeline = FeaturePipeline()
    portfolio = PortfolioState(balance=10000, equity=10000)

    signals_generated = 0
    for i in range(50, len(test_df)):  # 从第50天开始
        features = pipeline.compute_for_backtest_day(test_df, i)
        signal = strategy.on_daily_features(features, portfolio)
        if signal:
            signals_generated += 1
            if signals_generated <= 3:
                print(f"  信号 {signals_generated}:")
                print(f"    方向: {signal.direction} | 信心度: {signal.confidence:.2%}")
                print(f"    三元组: ({signal.triplet.mn1_hex},{signal.triplet.w1_hex},{signal.triplet.d1_hex})")
                print(f"    标签: {', '.join(signal.state_tags)}")
                print(f"    理由: {signal.reasoning[:80]}...")

    print(f"\n  总信号数: {signals_generated}")

    # 5. 测试策略摘要
    print("\n[5] 策略摘要")
    summary = strategy.get_signal_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # 6. 测试 WalkForwardOptimizer（简化）
    print("\n[6] WalkForwardOptimizer 测试（简化）")
    optimizer = WalkForwardOptimizer(
        strategy_class=P107StateHexStrategy,
        data=test_df,
        train_size=40,
        test_size=20,
        n_splits=2,
    )

    param_grid = {
        "min_confidence": [0.5, 0.6],
        "state_alignment_mode": ["loose"],
    }

    result = optimizer.optimize(param_grid, metric="sharpe_ratio")
    print(f"  最优参数: {result.optimal_params}")
    print(f"  综合Sharpe: {result.combined_sharpe:.4f}")
    print(f"  参数稳定性: {result.param_stability:.4f}")

    # 7. 测试 StrategyCombiner
    print("\n[7] StrategyCombiner 测试")
    strategy2 = registry.create_instance(
        "P107_StateHex_v1",
        min_confidence=0.5,
        state_alignment_mode="strict",
    )

    combiner = StrategyCombiner([strategy, strategy2], mode="consensus")

    # 模拟信号
    mock_signals = {
        "strategy1": Signal(direction="long", size=0.1, entry_price=1.08,
                           stop_loss=1.05, take_profit=1.12, confidence=0.7,
                           timestamp=datetime.now(), state_tags=["test"]),
        "strategy2": Signal(direction="long", size=0.1, entry_price=1.08,
                           stop_loss=1.05, take_profit=1.12, confidence=0.6,
                           timestamp=datetime.now(), state_tags=["test"]),
    }

    combined = combiner.combine_signals(mock_signals)
    if combined:
        print(f"  聚合信号: {combined.direction} | 信心度: {combined.confidence:.2%}")
        print(f"  标签: {combined.state_tags}")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
