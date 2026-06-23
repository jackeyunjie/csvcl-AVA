"""
MT4-H1 计算层

职责: H1级别的State Hex计算、四周期特征融合。

核心设计:
- 复用现有StateHexEncoder（编码规则不变）
- H1数据用于计算D1状态（从H1聚合）
- 四元组概念: (MN1, W1, D1, H1)
  - MN1/W1/D1: 定义市场气候（复用现有逻辑）
  - H1: 在气候内部提供交易时机

关键原则:
- 三元组(MN1,W1,D1)仍是气候定义的最小单元
- H1是执行层面的细化，不改变气候判断
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest_platform.compute_layer import (
    StateHexComputeEngine, MISSEngine, FeaturePipeline,
    DailyFeatures, OHLCVBar, FusedState, MISSSnapshot,
)
from ai_engine.state_hex_engine import StateHexTriplet

logger = logging.getLogger(__name__)


# ============================================================================
# H1 特征数据类
# ============================================================================

@dataclass
class H1Features:
    """H1级别特征（扩展DailyFeatures）"""
    timestamp: datetime
    h1_ohlcv: OHLCVBar
    d1_triplet: Optional[StateHexTriplet] = None  # D1三元组（气候）
    h1_state_hex: Optional[str] = None  # H1的State Hex（时机）
    miss_snapshot: Optional[MISSSnapshot] = None
    fused_state: Optional[FusedState] = None
    technical_indicators: Dict[str, float] = field(default_factory=dict)
    # H1特有: 当前H1在D1中的位置（开盘第几根）
    h1_index_in_d1: int = 0
    # H1特有: 距D1收盘还有几根
    h1_remaining_in_d1: int = 0


# ============================================================================
# H1 State Hex 计算引擎
# ============================================================================

class H1StateHexEngine:
    """
    H1 State Hex 计算引擎

    从H1数据计算D1/W1/MN1状态，同时生成H1级别的状态。

    工作流程:
    1. 从H1聚合生成D1 OHLCV
    2. 用聚合后的D1计算三元组(MN1,W1,D1) -> 气候
    3. 计算当前H1在D1内部的相对位置 -> 时机
    """

    def __init__(self):
        self.state_engine = StateHexComputeEngine()
        self.miss_engine = MISSEngine()

    def compute_h1_features(
        self,
        aligned_h1_df: pd.DataFrame,
        h1_index: int,
    ) -> H1Features:
        """
        计算指定H1位置的特征

        Args:
            aligned_h1_df: 四周期对齐后的H1数据
            h1_index: 当前H1在数据中的索引

        Returns:
            H1Features
        """
        if aligned_h1_df.empty or h1_index < 0 or h1_index >= len(aligned_h1_df):
            raise ValueError("无效的H1索引")

        # 只取到当前H1的数据（Walk-Forward）
        data_up_to_now = aligned_h1_df.iloc[:h1_index + 1].copy()
        current_row = aligned_h1_df.iloc[h1_index]
        timestamp = pd.to_datetime(current_row['timestamp'])

        # 1. 从H1聚合生成D1数据（用于计算三元组）
        d1_df = self._aggregate_h1_to_d1(data_up_to_now)

        # 2. 计算D1三元组（气候）
        triplet_series = self.state_engine.compute_triplet_series(d1_df)
        triplet = self.state_engine.get_triplet_at(timestamp) if not triplet_series.empty else None

        # 3. 计算H1在D1中的位置
        h1_in_d1, remaining = self._calc_h1_position_in_d1(data_up_to_now, timestamp)

        # 4. 计算MISS（基于最近H1数据）
        miss = self.miss_engine.compute_miss_snapshot(data_up_to_now, lookback=24)

        # 5. 融合
        fused = None
        if triplet is not None:
            fused = self.miss_engine.fuse_with_state_hex(miss, triplet)

        # 6. 构建H1 OHLCV
        h1_ohlcv = OHLCVBar(
            timestamp=timestamp,
            open=float(current_row['open']),
            high=float(current_row['high']),
            low=float(current_row['low']),
            close=float(current_row['close']),
            volume=float(current_row.get('volume', 0)),
        )

        # 7. H1技术指标
        tech = self._calc_h1_indicators(data_up_to_now)

        return H1Features(
            timestamp=timestamp,
            h1_ohlcv=h1_ohlcv,
            d1_triplet=triplet,
            miss_snapshot=miss,
            fused_state=fused,
            technical_indicators=tech,
            h1_index_in_d1=h1_in_d1,
            h1_remaining_in_d1=remaining,
        )

    def _aggregate_h1_to_d1(self, h1_df: pd.DataFrame) -> pd.DataFrame:
        """从H1聚合生成D1数据"""
        if h1_df.empty:
            return pd.DataFrame()

        df = h1_df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date

        d1 = df.groupby('date').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
        }).reset_index()

        d1['timestamp'] = pd.to_datetime(d1['date'])
        d1 = d1[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        return d1

    def _calc_h1_position_in_d1(
        self,
        h1_df: pd.DataFrame,
        current_ts: datetime,
    ) -> Tuple[int, int]:
        """
        计算当前H1在D1中的位置

        Returns:
            (当前是D1第几根H1, 距收盘还有几根)
        """
        current_date = current_ts.date()
        day_h1 = h1_df[h1_df['timestamp'].dt.date == current_date]

        if day_h1.empty:
            return 0, 0

        # 当前是第几根（0-based）
        h1_in_d1 = len(day_h1) - 1

        # 假设每天24根H1（外汇市场）
        remaining = max(0, 24 - h1_in_d1 - 1)

        return h1_in_d1, remaining

    def _calc_h1_indicators(self, h1_df: pd.DataFrame) -> Dict[str, float]:
        """计算H1级别技术指标"""
        indicators = {}
        if len(h1_df) < 24:
            return indicators

        closes = h1_df['close'].values
        highs = h1_df['high'].values
        lows = h1_df['low'].values

        # H1 ATR (14根)
        tr1 = highs[-14:] - lows[-14:]
        tr2 = np.abs(highs[-14:] - np.roll(closes, 1)[-14:])
        tr3 = np.abs(lows[-14:] - np.roll(closes, 1)[-14:])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        indicators['atr_14'] = float(np.mean(tr))

        # H1 RSI
        if len(closes) >= 14:
            deltas = np.diff(closes[-15:])
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                indicators['rsi'] = 100 - (100 / (1 + rs))

        # 当前H1在D1高低点中的位置（0-1）
        current_date = pd.to_datetime(h1_df['timestamp'].iloc[-1]).date()
        day_h1 = h1_df[h1_df['timestamp'].dt.date == current_date]
        if not day_h1.empty:
            day_high = day_h1['high'].max()
            day_low = day_h1['low'].min()
            current_close = closes[-1]
            if day_high > day_low:
                indicators['position_in_d1_range'] = (current_close - day_low) / (day_high - day_low)

        return indicators


# ============================================================================
# H1 特征管线
# ============================================================================

class H1FeaturePipeline:
    """
    H1特征管线

    将H1原始数据 → H1特征 → 策略可用特征
    支持Walk-Forward回测
    """

    def __init__(self):
        self.h1_engine = H1StateHexEngine()
        self._cached_features: Optional[H1Features] = None
        self._cached_index: int = -1

    def compute_for_backtest_bar(
        self,
        aligned_h1_df: pd.DataFrame,
        current_idx: int,
    ) -> H1Features:
        """
        回测专用: 逐H1计算特征

        Args:
            aligned_h1_df: 四周期对齐后的完整H1数据
            current_idx: 当前H1索引

        Returns:
            H1Features
        """
        # 简单缓存：如果索引连续递增，复用部分计算
        if self._cached_index == current_idx and self._cached_features is not None:
            return self._cached_features

        features = self.h1_engine.compute_h1_features(aligned_h1_df, current_idx)
        self._cached_features = features
        self._cached_index = current_idx
        return features
