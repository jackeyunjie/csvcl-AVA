"""
State Hex 引擎 - D1/W1/MN1 三元组状态计算

基于 P107 State Hex 编码规则：
- 从 D1 OHLCV 数据计算 compression / trend / position / volatility 组件
- 生成 state_hex (0-F, 支持正负方向)
- D1 数据聚合为真实 W1/MN1 K线，再计算各周期 state_hex
- 每个 D1 时间戳输出对齐的三元组 (MN1_hex, W1_hex, D1_hex)

组件计算逻辑（来自 FORMULA_DICTIONARY_20260517）：
- compression: Kaufman Width / BB Width 判断 closed/contraction/expansion
- trend: ADX/DI 判断 bull_start/bull_trend/bear_start/bear_trend/neutral
- position: 收盘价相对支撑/阻力位判断 above/below/break_up/break_down/neutral
- volatility: ATR percent 或 compression 扩张状态判断 active/neutral
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np

try:
    from ai_engine.state_hex_encoding import (
        StateHexEncoder, StateComponents,
        CompressionState, TrendState, PositionState, VolatilityState
    )
except ImportError:
    from state_hex_encoding import (
        StateHexEncoder, StateComponents,
        CompressionState, TrendState, PositionState, VolatilityState
    )

logger = logging.getLogger(__name__)


@dataclass
class KLine:
    """K线数据"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class StateHexTriplet:
    """State Hex 三元组 (MN1, W1, D1)"""
    timestamp: datetime          # D1 时间戳（对齐基准）
    mn1_hex: str                 # 月线 state_hex
    w1_hex: str                  # 周线 state_hex
    d1_hex: str                  # 日线 state_hex
    mn1_duration: int = 0        # MN1状态持续天数
    w1_duration: int = 0         # W1状态持续天数
    d1_duration: int = 0         # D1状态持续天数


@dataclass
class StateHexQuintuplet:
    """H1 视角 State Hex 五元组 (MN1, W1, D1, H4, H1) - H1 时间戳对齐"""
    timestamp: datetime          # H1 时间戳（对齐基准）
    mn1_hex: str = "8"
    w1_hex: str = "8"
    d1_hex: str = "8"
    h4_hex: str = "8"
    h1_hex: str = "8"
    mn1_duration: int = 0
    w1_duration: int = 0
    d1_duration: int = 0
    h4_duration: int = 0
    h1_duration: int = 0


class StateHexEngine:
    """
    State Hex 引擎

    核心流程：
    1. 接收 D1 OHLCV 数据
    2. 计算 D1 级别的 compression / trend / position / volatility
    3. 用 StateHexEncoder 生成 D1_state_hex
    4. 聚合 D1 → 真实 W1 K线 → 计算 W1_state_hex
    5. 聚合 D1 → 真实 MN1 K线 → 计算 MN1_state_hex
    6. 每个 D1 时间戳输出 (MN1, W1, D1) 三元组
    
    注: 本引擎为通用State Hex计算引擎，支持多周期状态编码。
    """

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        atr_period: int = 14,
        adx_period: int = 14,
        kaufman_period: int = 20,
        pivot_period: int = 20,
        contraction_lookback: int = 5,
        contraction_threshold: float = 0.6
    ):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.atr_period = atr_period
        self.adx_period = adx_period
        self.kaufman_period = kaufman_period
        self.pivot_period = pivot_period
        self.contraction_lookback = contraction_lookback
        self.contraction_threshold = contraction_threshold
        self.encoder = StateHexEncoder()

        # 数据存储
        self.d1_data: List[KLine] = []
        self.w1_data: Dict[str, KLine] = {}
        self.mn1_data: Dict[str, KLine] = {}
        self.h4_data: List[KLine] = []
        self.h1_data: List[KLine] = []
        # 独立数据（每个周期自己的 OHLCV）
        self.mn1_independent: List[KLine] = []
        self.w1_independent: List[KLine] = []

        # 状态历史
        self.d1_states: List[Tuple[datetime, str]] = []
        self.w1_states: List[Tuple[datetime, str]] = []
        self.mn1_states: List[Tuple[datetime, str]] = []
        self.h4_states: List[Tuple[datetime, str]] = []
        self.h1_states: List[Tuple[datetime, str]] = []
        self.triplets: List[StateHexTriplet] = []
        self.quintuplets: List[StateHexQuintuplet] = []

        logger.info("StateHexEngine初始化完成")

    # ========================================================================
    # 数据输入
    # ========================================================================

    def add_d1_bar(self, timestamp: datetime, open_p: float, high: float,
                   low: float, close: float, volume: float = 0.0):
        """添加一根D1 K线"""
        kline = KLine(timestamp, open_p, high, low, close, volume)
        self.d1_data.append(kline)
        self._update_aggregated(kline)

    def add_d1_dataframe(self, df: pd.DataFrame):
        """批量添加D1数据"""
        required = ['timestamp', 'open', 'high', 'low', 'close']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")
        for _, row in df.iterrows():
            ts = row['timestamp']
            if isinstance(ts, str):
                ts = pd.to_datetime(ts)
            self.add_d1_bar(ts, row['open'], row['high'],
                           row['low'], row['close'],
                           row.get('volume', 0.0))

    def add_h4_dataframe(self, df: pd.DataFrame):
        """批量添加H4数据（独立计算，不聚合）"""
        required = ['timestamp', 'open', 'high', 'low', 'close']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")
        for _, row in df.iterrows():
            ts = row['timestamp']
            if isinstance(ts, str):
                ts = pd.to_datetime(ts)
            self.h4_data.append(KLine(ts, row['open'], row['high'],
                                      row['low'], row['close'],
                                      row.get('volume', 0.0)))
        self.h4_data.sort(key=lambda k: k.timestamp)

    def add_h1_dataframe(self, df: pd.DataFrame):
        """批量添加H1数据（独立计算，不聚合）"""
        required = ['timestamp', 'open', 'high', 'low', 'close']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")
        for _, row in df.iterrows():
            ts = row['timestamp']
            if isinstance(ts, str):
                ts = pd.to_datetime(ts)
            self.h1_data.append(KLine(ts, row['open'], row['high'],
                                      row['low'], row['close'],
                                      row.get('volume', 0.0)))
        self.h1_data.sort(key=lambda k: k.timestamp)

    def _update_aggregated(self, d1: KLine):
        """用D1 K线更新W1和MN1聚合"""
        year, week, _ = d1.timestamp.isocalendar()
        w1_key = f"{year}-{week:02d}"

        if w1_key not in self.w1_data:
            self.w1_data[w1_key] = KLine(
                timestamp=d1.timestamp, open=d1.open,
                high=d1.high, low=d1.low, close=d1.close, volume=d1.volume
            )
        else:
            w1 = self.w1_data[w1_key]
            w1.high = max(w1.high, d1.high)
            w1.low = min(w1.low, d1.low)
            w1.close = d1.close
            w1.volume += d1.volume

        mn1_key = d1.timestamp.strftime("%Y-%m")
        if mn1_key not in self.mn1_data:
            self.mn1_data[mn1_key] = KLine(
                timestamp=d1.timestamp, open=d1.open,
                high=d1.high, low=d1.low, close=d1.close, volume=d1.volume
            )
        else:
            mn1 = self.mn1_data[mn1_key]
            mn1.high = max(mn1.high, d1.high)
            mn1.low = min(mn1.low, d1.low)
            mn1.close = d1.close
            mn1.volume += d1.volume

    # ========================================================================
    # 组件计算
    # ========================================================================

    def _calculate_components(
        self, klines: List[KLine], viewpoint_close: Optional[float] = None
    ) -> StateComponents:
        """
        计算状态组件 (compression, trend, position, volatility)
        """
        if len(klines) < self.bb_period + 5:
            return StateComponents()

        df = pd.DataFrame([
            {'open': k.open, 'high': k.high, 'low': k.low,
             'close': k.close, 'volume': k.volume}
            for k in klines
        ])

        # 1. Compression 计算 (BB Width + Kaufman Width)
        compression = self._calculate_compression(df)

        # 2. Trend 计算 (ADX/DI)
        trend = self._calculate_trend(df)

        # 3. Position 计算 (支撑阻力相对位置)
        position = self._calculate_position(df, viewpoint_close=viewpoint_close)

        # 4. Volatility 计算 (ATR percent)
        volatility = self._calculate_volatility(df)

        return StateComponents(compression, trend, position, volatility)

    def _calculate_compression(self, df: pd.DataFrame) -> CompressionState:
        """计算压缩状态"""
        if len(df) < self.bb_period:
            return CompressionState.NEUTRAL

        # BB Width
        bb_mid = df['close'].rolling(self.bb_period).mean()
        bb_std = df['close'].rolling(self.bb_period).std()
        bb_upper = bb_mid + self.bb_std * bb_std
        bb_lower = bb_mid - self.bb_std * bb_std
        bb_width = (bb_upper - bb_lower) / bb_mid

        # Kaufman Width (简化版：用价格范围/均线)
        price_range = df['high'] - df['low']
        kaufman_width = price_range / bb_mid

        current_bb_width = bb_width.iloc[-1]
        current_kaufman = kaufman_width.iloc[-1]

        if pd.isna(current_bb_width) or pd.isna(current_kaufman):
            return CompressionState.NEUTRAL

        # 历史分位
        bb_width_hist = bb_width.dropna()
        kaufman_hist = kaufman_width.dropna()

        if len(bb_width_hist) < 20:
            return CompressionState.NEUTRAL

        bb_rank = (bb_width_hist < current_bb_width).mean()
        kaufman_rank = (kaufman_hist < current_kaufman).mean()

        # 判断
        if bb_rank < 0.1 or kaufman_rank < 0.1:
            return CompressionState.CLOSED
        elif bb_rank < 0.3 or kaufman_rank < 0.3:
            return CompressionState.CONTRACTION
        elif bb_rank > 0.9 or kaufman_rank > 0.9:
            return CompressionState.STRONG_EXPANSION
        elif bb_rank > 0.7 or kaufman_rank > 0.7:
            return CompressionState.EXPANSION

        return CompressionState.NEUTRAL

    def _calculate_trend(self, df: pd.DataFrame) -> TrendState:
        """计算趋势状态（ADX/DI简化版）"""
        if len(df) < self.adx_period + 5:
            return TrendState.NEUTRAL

        # +DM / -DM
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # True Range
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Smoothed
        atr = tr.rolling(self.adx_period).mean()
        plus_di = 100 * plus_dm.rolling(self.adx_period).mean() / atr
        minus_di = 100 * minus_dm.rolling(self.adx_period).mean() / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(self.adx_period).mean()

        if pd.isna(adx.iloc[-1]):
            return TrendState.NEUTRAL

        current_adx = adx.iloc[-1]
        current_plus = plus_di.iloc[-1]
        current_minus = minus_di.iloc[-1]

        if current_adx < 20:
            return TrendState.CLOSED if current_adx < 15 else TrendState.NEUTRAL

        if current_plus > current_minus:
            if current_adx > 30:
                return TrendState.BULL_TREND
            else:
                return TrendState.BULL_START
        else:
            if current_adx > 30:
                return TrendState.BEAR_TREND
            else:
                return TrendState.BEAR_START

    def _calculate_position(
        self, df: pd.DataFrame, viewpoint_close: Optional[float] = None
    ) -> PositionState:
        """计算位置状态（视角基准价 vs 结构周期支撑阻力）"""
        if len(df) < self.pivot_period:
            return PositionState.NEUTRAL

        close = df['close'].iloc[-1] if viewpoint_close is None else viewpoint_close

        # 支撑 = N周期低点，阻力 = N周期高点
        support = df['low'].rolling(self.pivot_period).min().iloc[-1]
        resistance = df['high'].rolling(self.pivot_period).max().iloc[-1]

        if pd.isna(support) or pd.isna(resistance):
            return PositionState.NEUTRAL

        # 突破判断（用前一周期的支撑阻力，避免lookahead）
        prev_support = df['low'].rolling(self.pivot_period).min().shift(1).iloc[-1]
        prev_resistance = df['high'].rolling(self.pivot_period).max().shift(1).iloc[-1]

        if not pd.isna(prev_resistance) and close > prev_resistance:
            return PositionState.BREAK_UP
        if not pd.isna(prev_support) and close < prev_support:
            return PositionState.BREAK_DOWN

        # 相对位置
        range_pct = (resistance - support) / close * 100
        if range_pct < 0.5:  # 太窄，视为neutral
            return PositionState.NEUTRAL

        position_pct = (close - support) / (resistance - support)

        if position_pct > 0.9:
            return PositionState.ABOVE_EXTREME
        elif position_pct > 0.7:
            return PositionState.ABOVE
        elif position_pct < 0.1:
            return PositionState.BELOW_EXTREME
        elif position_pct < 0.3:
            return PositionState.BELOW
        elif position_pct > 0.6:
            return PositionState.NEAR_RESISTANCE
        elif position_pct < 0.4:
            return PositionState.NEAR_SUPPORT

        return PositionState.NEUTRAL

    def _position_from_levels(
        self,
        close: float,
        support: float,
        resistance: float,
        prev_support: float,
        prev_resistance: float,
    ) -> PositionState:
        """用预计算 SR 位和视角 close 计算 position。"""
        if pd.isna(support) or pd.isna(resistance):
            return PositionState.NEUTRAL

        if not pd.isna(prev_resistance) and close > prev_resistance:
            return PositionState.BREAK_UP
        if not pd.isna(prev_support) and close < prev_support:
            return PositionState.BREAK_DOWN

        range_pct = (resistance - support) / close * 100
        if range_pct < 0.5:
            return PositionState.NEUTRAL

        position_pct = (close - support) / (resistance - support)

        if position_pct > 0.9:
            return PositionState.ABOVE_EXTREME
        elif position_pct > 0.7:
            return PositionState.ABOVE
        elif position_pct < 0.1:
            return PositionState.BELOW_EXTREME
        elif position_pct < 0.3:
            return PositionState.BELOW
        elif position_pct > 0.6:
            return PositionState.NEAR_RESISTANCE
        elif position_pct < 0.4:
            return PositionState.NEAR_SUPPORT

        return PositionState.NEUTRAL

    def _calculate_volatility(self, df: pd.DataFrame) -> VolatilityState:
        """计算波动状态"""
        if len(df) < self.atr_period + 5:
            return VolatilityState.NEUTRAL

        # ATR percent
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        atr_pct = atr / df['close'] * 100

        current_atr_pct = atr_pct.iloc[-1]
        if pd.isna(current_atr_pct):
            return VolatilityState.NEUTRAL

        # ATR percent 历史分位
        atr_hist = atr_pct.dropna()
        if len(atr_hist) < 20:
            return VolatilityState.NEUTRAL

        atr_rank = (atr_hist < current_atr_pct).mean()

        # 幅动活跃 = ATR percent 处于历史中高位
        if atr_rank > 0.6:
            return VolatilityState.ACTIVE

        return VolatilityState.NEUTRAL

    # ========================================================================
    # State Hex 计算
    # ========================================================================

    def _calculate_d1_hex(self) -> Optional[Tuple[datetime, str]]:
        """计算最新D1的state_hex"""
        if len(self.d1_data) < self.bb_period:
            return None
        components = self._calculate_components(self.d1_data)
        hex_code = self.encoder.encode(components)
        return (self.d1_data[-1].timestamp, hex_code)

    def _calculate_w1_hex(self, for_timestamp: datetime) -> Optional[Tuple[datetime, str]]:
        """计算对应时间戳的W1 state_hex"""
        year, week, _ = for_timestamp.isocalendar()
        w1_key = f"{year}-{week:02d}"

        if w1_key not in self.w1_data:
            return None

        sorted_keys = sorted(self.w1_data.keys())
        current_idx = sorted_keys.index(w1_key)
        available_keys = sorted_keys[:current_idx + 1]

        if len(available_keys) < 3:  # 至少需要3周数据
            return (for_timestamp, "8")

        w1_klines = [self.w1_data[k] for k in available_keys]
        components = self._calculate_components(w1_klines)
        hex_code = self.encoder.encode(components)
        return (for_timestamp, hex_code)

    def _calculate_mn1_hex(self, for_timestamp: datetime) -> Optional[Tuple[datetime, str]]:
        """计算对应时间戳的MN1 state_hex"""
        mn1_key = for_timestamp.strftime("%Y-%m")

        if mn1_key not in self.mn1_data:
            return None

        sorted_keys = sorted(self.mn1_data.keys())
        current_idx = sorted_keys.index(mn1_key)
        available_keys = sorted_keys[:current_idx + 1]

        if len(available_keys) < 3:  # 至少需要3月数据
            return (for_timestamp, "8")

        mn1_klines = [self.mn1_data[k] for k in available_keys]
        components = self._calculate_components(mn1_klines)
        hex_code = self.encoder.encode(components)
        return (for_timestamp, hex_code)

    # ========================================================================
    # 三元组生成
    # ========================================================================

    def compute_triplets(self) -> List[StateHexTriplet]:
        """计算所有时间戳对齐的三元组"""
        self.triplets = []

        for d1 in self.d1_data:
            ts = d1.timestamp

            # D1 state_hex
            d1_components = self._calculate_components(self.d1_data[:self.d1_data.index(d1) + 1])
            d1_hex = self.encoder.encode(d1_components)

            # W1 state_hex
            w1_result = self._calculate_w1_hex(ts)
            w1_hex = w1_result[1] if w1_result else "8"

            # MN1 state_hex
            mn1_result = self._calculate_mn1_hex(ts)
            mn1_hex = mn1_result[1] if mn1_result else "8"

            # 持续时间
            d1_duration = self._calc_duration(self.d1_states, d1_hex)
            w1_duration = self._calc_duration(self.w1_states, w1_hex)
            mn1_duration = self._calc_duration(self.mn1_states, mn1_hex)

            # 记录
            self.d1_states.append((ts, d1_hex))
            if not self.w1_states or self.w1_states[-1][1] != w1_hex:
                self.w1_states.append((ts, w1_hex))
            if not self.mn1_states or self.mn1_states[-1][1] != mn1_hex:
                self.mn1_states.append((ts, mn1_hex))

            triplet = StateHexTriplet(
                timestamp=ts,
                mn1_hex=mn1_hex,
                w1_hex=w1_hex,
                d1_hex=d1_hex,
                mn1_duration=mn1_duration,
                w1_duration=w1_duration,
                d1_duration=d1_duration
            )
            self.triplets.append(triplet)

        logger.info(f"三元组计算完成 | 共{len(self.triplets)}个")
        return self.triplets

    def _calc_duration(self, state_history: List[Tuple[datetime, str]], current: str) -> int:
        """计算状态持续时间"""
        if not state_history:
            return 1
        count = 0
        for _, s in reversed(state_history):
            if s == current:
                count += 1
            else:
                break
        return count + 1

    # ========================================================================
    # H1 视角五元组计算 (MN1, W1, D1, H4, H1)
    # ========================================================================

    def add_mn1_dataframe(self, df: pd.DataFrame):
        """批量添加 MN1 结构周期数据"""
        required = ['timestamp', 'open', 'high', 'low', 'close']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")
        for _, row in df.iterrows():
            ts = row['timestamp']
            if isinstance(ts, str):
                ts = pd.to_datetime(ts)
            self.mn1_independent.append(KLine(ts, row['open'], row['high'],
                                              row['low'], row['close'],
                                              row.get('volume', 0.0)))
        self.mn1_independent.sort(key=lambda k: k.timestamp)

    def add_w1_dataframe(self, df: pd.DataFrame):
        """批量添加 W1 结构周期数据"""
        required = ['timestamp', 'open', 'high', 'low', 'close']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")
        for _, row in df.iterrows():
            ts = row['timestamp']
            if isinstance(ts, str):
                ts = pd.to_datetime(ts)
            self.w1_independent.append(KLine(ts, row['open'], row['high'],
                                             row['low'], row['close'],
                                             row.get('volume', 0.0)))
        self.w1_independent.sort(key=lambda k: k.timestamp)

    def compute_quintuplets(self) -> List[StateHexQuintuplet]:
        """
        计算 H1 视角、H1 时间戳对齐的五元组。

        架构契约：
        - H1 视角是一个独立 Agent。
        - 该 Agent 包含 MN1/W1/D1/H4/H1 五个结构周期状态。
        - base/trend/volatility 来自各结构周期自身。
        - position 应使用 H1 close vs 各结构周期 SR。

        每根 H1 K 线输出一行，包含 5 个结构周期在 H1 视角下的 state_hex。
        """
        if not self.h1_data:
            logger.warning("无 H1 数据，无法计算五元组")
            return []

        self.quintuplets = []

        # 五个结构周期各自提供 OHLCV 结构；它们共同服务于 H1 视角 Agent。
        # 每个 state 的 position 都使用当前 H1 close 作为视角基准价。
        mn1_hex_map = self._compute_states_under_view(
            self.mn1_independent if self.mn1_independent else self._fallback_mn1(),
            self.h1_data,
            "MN1"
        )
        w1_hex_map = self._compute_states_under_view(
            self.w1_independent if self.w1_independent else self._fallback_w1(),
            self.h1_data,
            "W1"
        )
        d1_hex_map = self._compute_states_under_view(self.d1_data, self.h1_data, "D1")
        h4_hex_map = self._compute_states_under_view(self.h4_data, self.h1_data, "H4")
        h1_hex_map = self._compute_states_under_view(self.h1_data, self.h1_data, "H1")

        # 对齐：每根 H1 K线查找其他周期的 state_hex
        h1_state_history: List[Tuple[datetime, str]] = []

        for h1_bar in self.h1_data:
            ts = h1_bar.timestamp

            h1_hex = h1_hex_map.get(ts, "8")
            h4_hex = h4_hex_map.get(ts, "8")
            d1_hex = d1_hex_map.get(ts, "8")
            w1_hex = w1_hex_map.get(ts, "8")
            mn1_hex = mn1_hex_map.get(ts, "8")

            # durations
            h1_dur = self._calc_duration(h1_state_history, h1_hex)
            h1_state_history.append((ts, h1_hex))

            self.quintuplets.append(StateHexQuintuplet(
                timestamp=ts,
                mn1_hex=mn1_hex,
                w1_hex=w1_hex,
                d1_hex=d1_hex,
                h4_hex=h4_hex,
                h1_hex=h1_hex,
                mn1_duration=0,
                w1_duration=0,
                d1_duration=0,
                h4_duration=0,
                h1_duration=h1_dur,
            ))

        logger.info(f"五元组计算完成 | 共{len(self.quintuplets)}个")
        return self.quintuplets

    def _compute_independent_states(
        self, data: List[KLine], label: str
    ) -> Dict[datetime, str]:
        """
        从结构周期 OHLCV 数据生成 state_hex 查找表。

        注意：这是结构周期本地计算 helper。完整的 viewpoint Agent 合规计算
        还需要把 view_tf close 注入 position 计算。
        返回 {timestamp: hex_code}
        """
        result: Dict[datetime, str] = {}
        if not data or len(data) < self.bb_period:
            logger.warning(f"{label} Agent: 数据不足 ({len(data)}条)")
            return result

        for i in range(self.bb_period - 1, len(data)):
            slice_data = data[:i + 1]
            components = self._calculate_components(slice_data)
            hex_code = self.encoder.encode(components)
            result[data[i].timestamp] = hex_code

        logger.info(f"{label} Agent: 计算完成 {len(result)} 个 state_hex")
        return result

    def _compute_states_under_view(
        self,
        structure_data: List[KLine],
        view_data: List[KLine],
        label: str,
    ) -> Dict[datetime, str]:
        """
        计算结构周期在同一视角 Agent 下的 state_hex。

        base/trend/volatility 使用 structure_data；position 使用 view bar close。
        返回 {view_timestamp: hex_code}。
        """
        result: Dict[datetime, str] = {}
        if not structure_data or len(structure_data) < self.bb_period:
            logger.warning(f"{label}@view: 结构数据不足 ({len(structure_data)}条)")
            return result

        structure_data = sorted(structure_data, key=lambda k: k.timestamp)
        prepared = self._prepare_structure_features(structure_data)

        if not prepared:
            return result

        structure_idx = -1
        for view_bar in view_data:
            while (
                structure_idx + 1 < len(prepared)
                and prepared[structure_idx + 1][0] <= view_bar.timestamp
            ):
                structure_idx += 1

            if structure_idx < 0:
                continue
            (
                _,
                compression,
                trend,
                volatility,
                support,
                resistance,
                prev_support,
                prev_resistance,
            ) = prepared[structure_idx]
            position = self._position_from_levels(
                view_bar.close,
                support,
                resistance,
                prev_support,
                prev_resistance,
            )
            components = StateComponents(compression, trend, position, volatility)
            result[view_bar.timestamp] = self.encoder.encode(components)

        logger.info(f"{label}@view: 计算完成 {len(result)} 个 state_hex")
        return result

    def _prepare_structure_features(
        self, data: List[KLine]
    ) -> List[Tuple[datetime, CompressionState, TrendState, VolatilityState, float, float, float, float]]:
        """预计算结构周期自身特征，供不同视角 close 注入 position。"""
        df = pd.DataFrame([
            {'open': k.open, 'high': k.high, 'low': k.low,
             'close': k.close, 'volume': k.volume}
            for k in data
        ])

        close = df['close']
        high = df['high']
        low = df['low']

        # Compression
        bb_mid = close.rolling(self.bb_period).mean()
        bb_std = close.rolling(self.bb_period).std()
        bb_width = ((bb_mid + self.bb_std * bb_std) - (bb_mid - self.bb_std * bb_std)) / bb_mid
        kaufman_width = (high - low) / bb_mid

        # Trend
        high_diff = high.diff()
        low_diff = -low.diff()
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.adx_period).mean()
        plus_di = 100 * plus_dm.rolling(self.adx_period).mean() / atr
        minus_di = 100 * minus_dm.rolling(self.adx_period).mean() / atr
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(self.adx_period).mean()

        # Volatility
        atr_pct = atr / close * 100

        # SR levels
        support = low.rolling(self.pivot_period).min()
        resistance = high.rolling(self.pivot_period).max()
        prev_support = support.shift(1)
        prev_resistance = resistance.shift(1)

        prepared = []
        for i in range(self.bb_period - 1, len(data)):
            compression = CompressionState.NEUTRAL
            current_bb = bb_width.iloc[i]
            current_kaufman = kaufman_width.iloc[i]
            if not pd.isna(current_bb) and not pd.isna(current_kaufman):
                bb_hist = bb_width.iloc[:i + 1].dropna()
                kaufman_hist = kaufman_width.iloc[:i + 1].dropna()
                if len(bb_hist) >= 20:
                    bb_rank = (bb_hist < current_bb).mean()
                    kaufman_rank = (kaufman_hist < current_kaufman).mean()
                    if bb_rank < 0.1 or kaufman_rank < 0.1:
                        compression = CompressionState.CLOSED
                    elif bb_rank < 0.3 or kaufman_rank < 0.3:
                        compression = CompressionState.CONTRACTION
                    elif bb_rank > 0.9 or kaufman_rank > 0.9:
                        compression = CompressionState.STRONG_EXPANSION
                    elif bb_rank > 0.7 or kaufman_rank > 0.7:
                        compression = CompressionState.EXPANSION

            trend = TrendState.NEUTRAL
            current_adx = adx.iloc[i]
            current_plus = plus_di.iloc[i]
            current_minus = minus_di.iloc[i]
            if not pd.isna(current_adx):
                if current_adx < 20:
                    trend = TrendState.CLOSED if current_adx < 15 else TrendState.NEUTRAL
                elif current_plus > current_minus:
                    trend = TrendState.BULL_TREND if current_adx > 30 else TrendState.BULL_START
                else:
                    trend = TrendState.BEAR_TREND if current_adx > 30 else TrendState.BEAR_START

            volatility = VolatilityState.NEUTRAL
            current_atr_pct = atr_pct.iloc[i]
            if not pd.isna(current_atr_pct):
                atr_hist = atr_pct.iloc[:i + 1].dropna()
                if len(atr_hist) >= 20 and (atr_hist < current_atr_pct).mean() > 0.6:
                    volatility = VolatilityState.ACTIVE

            prepared.append((
                data[i].timestamp,
                compression,
                trend,
                volatility,
                support.iloc[i],
                resistance.iloc[i],
                prev_support.iloc[i],
                prev_resistance.iloc[i],
            ))

        return prepared

    def _lookup_higher_tf(
        self, hex_map: Dict[datetime, str], h1_ts: datetime, label: str
    ) -> str:
        """查找包含 h1_ts 的更高周期 state_hex"""
        # 找到 <= h1_ts 的最新一根
        candidates = [ts for ts in hex_map if ts <= h1_ts]
        if not candidates:
            return "8"
        best = max(candidates)
        return hex_map[best]

    def _fallback_mn1(self) -> List[KLine]:
        """如果没有独立 MN1 数据，从 D1 聚合"""
        if not self.d1_data:
            return []
        agg: Dict[str, KLine] = {}
        for bar in self.d1_data:
            key = bar.timestamp.strftime("%Y-%m")
            if key not in agg:
                agg[key] = KLine(bar.timestamp, bar.open, bar.high,
                                 bar.low, bar.close, bar.volume)
            else:
                k = agg[key]
                k.high = max(k.high, bar.high)
                k.low = min(k.low, bar.low)
                k.close = bar.close
                k.volume += bar.volume
        return sorted(agg.values(), key=lambda k: k.timestamp)

    def _fallback_w1(self) -> List[KLine]:
        """如果没有独立 W1 数据，从 D1 聚合"""
        if not self.d1_data:
            return []
        agg: Dict[str, KLine] = {}
        for bar in self.d1_data:
            year, week, _ = bar.timestamp.isocalendar()
            key = f"{year}-{week:02d}"
            if key not in agg:
                agg[key] = KLine(bar.timestamp, bar.open, bar.high,
                                 bar.low, bar.close, bar.volume)
            else:
                k = agg[key]
                k.high = max(k.high, bar.high)
                k.low = min(k.low, bar.low)
                k.close = bar.close
                k.volume += bar.volume
        return sorted(agg.values(), key=lambda k: k.timestamp)

    def to_quintuplet_dataframe(self) -> pd.DataFrame:
        """五元组转 DataFrame"""
        if not self.quintuplets:
            return pd.DataFrame()
        data = []
        for q in self.quintuplets:
            data.append({
                'timestamp': q.timestamp,
                'MN1_hex': q.mn1_hex,
                'W1_hex': q.w1_hex,
                'D1_hex': q.d1_hex,
                'H4_hex': q.h4_hex,
                'H1_hex': q.h1_hex,
                'MN1_dur': q.mn1_duration,
                'W1_dur': q.w1_duration,
                'D1_dur': q.d1_duration,
                'H4_dur': q.h4_duration,
                'H1_dur': q.h1_duration,
            })
        return pd.DataFrame(data)

    # ========================================================================
    # 输出接口
    # ========================================================================

    def get_latest_triplet(self) -> Optional[StateHexTriplet]:
        return self.triplets[-1] if self.triplets else None

    def to_dataframe(self) -> pd.DataFrame:
        if not self.triplets:
            return pd.DataFrame()
        data = []
        for t in self.triplets:
            data.append({
                'timestamp': t.timestamp,
                'MN1_hex': t.mn1_hex,
                'W1_hex': t.w1_hex,
                'D1_hex': t.d1_hex,
                'MN1_duration': t.mn1_duration,
                'W1_duration': t.w1_duration,
                'D1_duration': t.d1_duration,
            })
        return pd.DataFrame(data)

    def get_triplet_summary(self) -> Dict:
        if not self.triplets:
            return {}
        df = self.to_dataframe()
        return {
            'total_days': len(self.triplets),
            'd1_distribution': df['D1_hex'].value_counts().to_dict(),
            'w1_distribution': df['W1_hex'].value_counts().to_dict(),
            'mn1_distribution': df['MN1_hex'].value_counts().to_dict(),
        }


# ============================================================================
# 便捷函数
# ============================================================================

def compute_state_hex_triplets(df: pd.DataFrame) -> pd.DataFrame:
    """从DataFrame一键计算State Hex三元组"""
    engine = StateHexEngine()
    engine.add_d1_dataframe(df)
    engine.compute_triplets()
    return engine.to_dataframe()


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("State Hex Engine Test")
    print("=" * 70)

    np.random.seed(42)
    n_days = 120
    base_price = 1.0850

    trend = np.sin(np.linspace(0, 3*np.pi, n_days)) * 0.015
    noise = np.cumsum(np.random.randn(n_days) * 0.003)
    prices = base_price + trend + noise

    data = []
    start_date = datetime(2025, 1, 1)
    for i in range(n_days):
        date = start_date + timedelta(days=i)
        if date.weekday() >= 5:
            continue
        close = prices[i]
        high = close + abs(np.random.randn()) * 0.008
        low = close - abs(np.random.randn()) * 0.008
        open_p = close + np.random.randn() * 0.003
        data.append({
            'timestamp': date,
            'open': open_p,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.randint(10000, 100000)
        })

    df = pd.DataFrame(data)
    print(f"\nGenerated {len(df)} trading days")

    engine = StateHexEngine()
    engine.add_d1_dataframe(df)
    triplets = engine.compute_triplets()

    print(f"\nTriplets computed: {len(triplets)}")

    print("\n[First 5 Triplets]")
    for t in triplets[:5]:
        print(f"  {t.timestamp.strftime('%Y-%m-%d')} | "
              f"MN1({t.mn1_hex:3s}/{t.mn1_duration:2d}d) | "
              f"W1({t.w1_hex:3s}/{t.w1_duration:2d}d) | "
              f"D1({t.d1_hex:3s}/{t.d1_duration:2d}d)")

    print("\n[Last 5 Triplets]")
    for t in triplets[-5:]:
        print(f"  {t.timestamp.strftime('%Y-%m-%d')} | "
              f"MN1({t.mn1_hex:3s}/{t.mn1_duration:2d}d) | "
              f"W1({t.w1_hex:3s}/{t.w1_duration:2d}d) | "
              f"D1({t.d1_hex:3s}/{t.d1_duration:2d}d)")

    summary = engine.get_triplet_summary()
    print(f"\n[Summary]")
    print(f"  Total days: {summary['total_days']}")
    print(f"  D1 distribution: {summary['d1_distribution']}")
    print(f"  W1 distribution: {summary['w1_distribution']}")
    print(f"  MN1 distribution: {summary['mn1_distribution']}")

    print("\n" + "=" * 70)
    print("Test completed")
    print("=" * 70)
