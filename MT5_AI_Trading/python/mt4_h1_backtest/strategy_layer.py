"""
MT4-H1 策略层

职责: H1级别策略注册、信号生成。

核心设计:
- 复用现有策略基类
- H1策略可以访问D1气候状态 + H1时机状态
- 策略可以在H1级别开平仓（更精细）
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest_platform.strategy_layer import (
    BaseStrategy, Signal, PortfolioState,
    StrategyRegistry, P107StateHexStrategy,
)
from mt4_h1_backtest.compute_layer import H1Features


class SignalDirection:
    """信号方向枚举（兼容层）"""
    LONG = "long"
    SHORT = "short"

logger = logging.getLogger(__name__)


# ============================================================================
# H1 策略基类
# ============================================================================

class H1BaseStrategy(BaseStrategy):
    """
    H1策略基类

    H1策略与D1策略的区别:
    - on_h1_features: 接收H1Features（含D1气候 + H1时机）
    - 可以在H1级别生成信号（更细粒度入场/出场）
    """

    def on_h1_features(
        self,
        features: H1Features,
        portfolio: PortfolioState,
    ) -> Optional[Signal]:
        """
        H1策略主入口

        Args:
            features: H1特征（含D1三元组气候 + H1时机）
            portfolio: 当前账户状态

        Returns:
            Signal或None
        """
        raise NotImplementedError("子类必须实现on_h1_features")

    # 兼容D1接口（如果策略同时支持D1）
    def on_daily_features(self, features, portfolio):
        """D1兼容接口（H1策略默认不支持）"""
        return None


# ============================================================================
# H1 P107 StateHex 策略
# ============================================================================

class H1P107StateHexStrategy(H1BaseStrategy):
    """
    H1版P107 StateHex策略

    核心逻辑:
    1. D1三元组定义气候（多/空/震荡）
    2. H1在气候内部寻找最佳入场时机
    3. 利用H1位置优化止损/止盈

    参数:
    - min_confidence: 最低信心度
    - state_alignment_mode: strict/loose
    - sl_atr_multiplier: 止损ATR倍数
    - tp_atr_multiplier: 止盈ATR倍数
    - h1_entry_timing: H1入场时机偏好
        - "early": D1早期入场（第1-8根H1）
        - "mid": D1中期入场（第9-16根H1）
        - "late": D1晚期入场（第17-24根H1）
        - "any": 任意时机
    """

    def __init__(
        self,
        min_confidence: float = 0.6,
        state_alignment_mode: str = "strict",
        sl_atr_multiplier: float = 2.0,
        tp_atr_multiplier: float = 3.0,
        h1_entry_timing: str = "any",
    ):
        self.min_confidence = min_confidence
        self.state_alignment_mode = state_alignment_mode
        self.sl_atr_multiplier = sl_atr_multiplier
        self.tp_atr_multiplier = tp_atr_multiplier
        self.h1_entry_timing = h1_entry_timing
        self._name = "H1_P107_StateHex_v1"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "H1版P107 StateHex策略：D1气候+H1时机"

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "min_confidence": {"type": "float", "min": 0.3, "max": 0.9, "default": 0.6},
            "state_alignment_mode": {"type": "choice", "options": ["strict", "loose"], "default": "strict"},
            "sl_atr_multiplier": {"type": "float", "min": 1.0, "max": 5.0, "default": 2.0},
            "tp_atr_multiplier": {"type": "float", "min": 1.0, "max": 10.0, "default": 3.0},
            "h1_entry_timing": {"type": "choice", "options": ["early", "mid", "late", "any"], "default": "any"},
        }

    @property
    def params(self) -> Dict[str, Any]:
        return {
            "min_confidence": self.min_confidence,
            "state_alignment_mode": self.state_alignment_mode,
            "sl_atr_multiplier": self.sl_atr_multiplier,
            "tp_atr_multiplier": self.tp_atr_multiplier,
            "h1_entry_timing": self.h1_entry_timing,
        }

    def on_h1_features(
        self,
        features: H1Features,
        portfolio: PortfolioState,
    ) -> Optional[Signal]:
        """H1策略逻辑"""
        triplet = features.d1_triplet
        if triplet is None:
            return None

        # 1. 检查D1气候条件
        d1_score = self._get_d1_score(triplet)
        if d1_score == 0:
            return None

        # 2. 检查H1入场时机
        if not self._check_h1_timing(features):
            return None

        # 3. 检查信心度
        fused = features.fused_state
        confidence = fused.fused_confidence if fused else 0.0
        if confidence < self.min_confidence:
            return None

        # 4. 计算ATR
        atr = features.technical_indicators.get('atr_14', features.h1_ohlcv.close * 0.001)

        # 5. 生成信号
        direction_str = "long" if d1_score > 0 else "short"
        entry_price = features.h1_ohlcv.close

        if direction_str == "long":
            sl = entry_price - atr * self.sl_atr_multiplier
            tp = entry_price + atr * self.tp_atr_multiplier
        else:
            sl = entry_price + atr * self.sl_atr_multiplier
            tp = entry_price - atr * self.tp_atr_multiplier

        return Signal(
            direction=direction_str,
            size=0.1,
            entry_price=entry_price,
            stop_loss=sl,
            take_profit=tp,
            confidence=confidence,
            timestamp=features.timestamp,
            strategy_name=self.name,
            strategy_params=self.params,
            reasoning=f"D1三元组:{triplet.mn1_hex}|{triplet.w1_hex}|{triplet.d1_hex} H1位置:{features.h1_index_in_d1}",
        )

    def _get_d1_score(self, triplet) -> int:
        """获取D1方向评分"""
        from ai_engine.state_hex_encoding import StateHexEncoder
        d1_val = StateHexEncoder._from_signed_hex(triplet.d1_hex)

        if self.state_alignment_mode == "strict":
            # 三周期同向
            mn1_val = StateHexEncoder._from_signed_hex(triplet.mn1_hex)
            w1_val = StateHexEncoder._from_signed_hex(triplet.w1_hex)
            if mn1_val > 0 and w1_val > 0 and d1_val > 0:
                return 1
            if mn1_val < 0 and w1_val < 0 and d1_val < 0:
                return -1
            return 0
        else:
            # 只看D1
            return 1 if d1_val > 0 else -1 if d1_val < 0 else 0

    def _check_h1_timing(self, features: H1Features) -> bool:
        """检查H1入场时机"""
        if self.h1_entry_timing == "any":
            return True

        idx = features.h1_index_in_d1
        if self.h1_entry_timing == "early":
            return 0 <= idx <= 8
        elif self.h1_entry_timing == "mid":
            return 9 <= idx <= 16
        elif self.h1_entry_timing == "late":
            return 17 <= idx <= 24

        return True


# ============================================================================
# H1 策略注册表
# ============================================================================

class H1StrategyRegistry:
    """H1策略注册表"""

    _strategies: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, strategy_class):
        cls._strategies[name] = strategy_class

    @classmethod
    def create_instance(cls, name: str, **kwargs) -> H1BaseStrategy:
        strategy_class = cls._strategies.get(name)
        if strategy_class is None:
            raise ValueError(f"未知策略: {name}")
        return strategy_class(**kwargs)

    @classmethod
    def list_strategies(cls) -> List[str]:
        return list(cls._strategies.keys())


# 注册默认策略
H1StrategyRegistry.register("H1_P107_StateHex_v1", H1P107StateHexStrategy)
