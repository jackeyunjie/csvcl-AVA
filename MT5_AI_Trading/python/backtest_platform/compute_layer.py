"""
计算层 (Compute Layer)

职责: 所有状态计算、特征工程、MISS融合。

模块:
- StateHexComputeEngine: 封装现有StateHexEngine，提供统一计算接口
- MISSEngine: Market Information State Segmentation (4维25子状态)
- FeaturePipeline: 原始数据 → 状态特征 → 策略可用特征
- StateEvolutionTracker: 状态演化追踪

核心原则:
- 最小分析单元: 三元组(MN1, W1, D1)
- State Hex为主裁决，MISS为环境修饰
- 资金流仅做二级确认
- Walk-Forward: 严格只用今天及之前的数据
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque

import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_engine.state_hex_encoding import StateHexEncoder
from ai_engine.state_hex_engine import StateHexEngine, StateHexTriplet
from ai_engine.moneyflow_energy_layer import MoneyflowEnergyLayer, EnergyLabel

logger = logging.getLogger(__name__)


# ============================================================================
# 核心数据类
# ============================================================================

@dataclass
class OHLCVBar:
    """标准化K线数据"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class MISSSnapshot:
    """MISS 快照 (Market Information State Segmentation)

    4个正交维度 × 25个子状态
    """
    timestamp: datetime

    # 维度1: Price (价格状态)
    price_state: str = "unknown"           # trend/oscillation/reversal/breakout/neutral
    price_state_confidence: float = 0.0

    # 维度2: Volume (成交量状态)
    volume_state: str = "unknown"          # expanding/shrinking/average/anomaly/neutral
    volume_state_confidence: float = 0.0

    # 维度3: Liquidity (流动性状态)
    liquidity_state: str = "unknown"       # ample/tight/dry/recovering/neutral
    liquidity_state_confidence: float = 0.0

    # 维度4: Information (信息状态)
    info_state: str = "unknown"            # calm/expectation/release/digestion/neutral
    info_state_confidence: float = 0.0

    # 综合评分
    overall_alignment: float = 0.0         # 与State Hex方向的一致性


@dataclass
class FusedState:
    """融合后的状态 (State Hex + MISS)"""
    timestamp: datetime
    triplet: StateHexTriplet
    miss_snapshot: Optional[MISSSnapshot]

    # 融合后信心度
    fused_confidence: float = 0.0

    # 融合标签
    fused_tags: List[str] = field(default_factory=list)

    # 解释
    explanation: str = ""


@dataclass
class DailyFeatures:
    """每日特征包（计算层输出，策略层输入）"""
    timestamp: datetime
    triplet: StateHexTriplet
    miss_snapshot: Optional[MISSSnapshot]
    fused_state: Optional[FusedState]
    ohlcv: OHLCVBar
    technical_indicators: Dict[str, float] = field(default_factory=dict)
    state_transitions: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# State Hex 计算引擎
# ============================================================================

class StateHexComputeEngine:
    """
    State Hex 计算引擎

    封装现有的 StateHexEngine + StateHexEncoder，
    提供统一的计算接口供回测平台调用。

    核心功能:
    - 从对齐后的多周期数据计算三元组序列
    - 状态转移矩阵计算
    - 状态演化追踪
    """

    def __init__(self):
        self.encoder = StateHexEncoder()
        self.engine = StateHexEngine()
        # 前缀缓存：避免O(n²)重复计算
        self._max_cached_df: Optional[pd.DataFrame] = None
        self._max_cached_triplets: Optional[pd.DataFrame] = None

    def compute_triplet_series(
        self,
        aligned_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        计算三元组时间序列（带前缀缓存优化，避免O(n²)重复计算）

        Args:
            aligned_df: 来自 MultiTimeframeAligner 的对齐数据
                        必须包含: timestamp, open, high, low, close, volume

        Returns:
            DataFrame，每行包含:
            - timestamp, mn1_hex, w1_hex, d1_hex
            - mn1_duration, w1_duration, d1_duration
            - mn1_desc, w1_desc, d1_desc
        """
        # 提取D1数据用于State引擎
        required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in aligned_df.columns:
                raise ValueError(f"对齐数据缺少必要列: {col}")

        d1_df = aligned_df[required].copy()
        d1_df['timestamp'] = pd.to_datetime(d1_df['timestamp'])

        # 前缀缓存检查：如果请求的数据是已缓存数据的前缀，直接截取
        if self._max_cached_triplets is not None and self._max_cached_df is not None:
            n_req = len(d1_df)
            n_cache = len(self._max_cached_df)
            if n_req <= n_cache:
                # 检查时间戳是否匹配（前缀验证）
                req_ts = d1_df['timestamp'].values
                cache_ts = self._max_cached_df['timestamp'].values[:n_req]
                if np.array_equal(req_ts, cache_ts):
                    # 命中前缀缓存，直接截取
                    result = self._max_cached_triplets.iloc[:n_req].copy()
                    logger.debug(f"前缀缓存命中: {n_req}/{n_cache}行")
                    return result

        # 缓存未命中，重新计算
        self.engine = StateHexEngine()
        self.engine.add_d1_dataframe(d1_df)
        self.engine.compute_triplets()

        if not self.engine.triplets:
            logger.warning("三元组计算结果为空")
            return pd.DataFrame()

        # 构建结果DataFrame
        data = []
        for t in self.engine.triplets:
            data.append({
                'timestamp': t.timestamp,
                'mn1_hex': t.mn1_hex,
                'w1_hex': t.w1_hex,
                'd1_hex': t.d1_hex,
                'mn1_duration': t.mn1_duration,
                'w1_duration': t.w1_duration,
                'd1_duration': t.d1_duration,
                'mn1_desc': self.encoder.describe(t.mn1_hex),
                'w1_desc': self.encoder.describe(t.w1_hex),
                'd1_desc': self.encoder.describe(t.d1_hex),
            })

        result = pd.DataFrame(data)

        # 更新前缀缓存（只保留更大的数据集）
        if self._max_cached_df is None or len(d1_df) >= len(self._max_cached_df):
            self._max_cached_df = d1_df.copy()
            self._max_cached_triplets = result.copy()
            logger.debug(f"前缀缓存更新: {len(d1_df)}行")

        logger.info(f"三元组序列计算完成: {len(result)}行")
        return result

    def compute_state_transitions(
        self,
        triplet_series: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        计算状态转移矩阵

        Args:
            triplet_series: 三元组序列DataFrame

        Returns:
            DataFrame，包含状态转移信息
        """
        if triplet_series.empty or len(triplet_series) < 2:
            return triplet_series.copy()

        df = triplet_series.copy()

        # D1状态转移
        df['d1_prev'] = df['d1_hex'].shift(1)
        df['d1_transition'] = df.apply(
            lambda r: f"{r['d1_prev']}→{r['d1_hex']}" if pd.notna(r['d1_prev']) else "init",
            axis=1
        )

        # W1状态转移
        df['w1_prev'] = df['w1_hex'].shift(1)
        df['w1_transition'] = df.apply(
            lambda r: f"{r['w1_prev']}→{r['w1_hex']}" if pd.notna(r['w1_prev']) else "init",
            axis=1
        )

        # MN1状态转移
        df['mn1_prev'] = df['mn1_hex'].shift(1)
        df['mn1_transition'] = df.apply(
            lambda r: f"{r['mn1_prev']}→{r['mn1_hex']}" if pd.notna(r['mn1_prev']) else "init",
            axis=1
        )

        # 三周期同时变化标记
        df['all_changed'] = (
            (df['d1_hex'] != df['d1_prev'].fillna(df['d1_hex'])) &
            (df['w1_hex'] != df['w1_prev'].fillna(df['w1_hex'])) &
            (df['mn1_hex'] != df['mn1_prev'].fillna(df['mn1_hex']))
        )

        # 方向一致性
        df['direction_consistency'] = df.apply(self._calc_direction_consistency, axis=1)

        logger.info(f"状态转移计算完成: {len(df)}行")
        return df

    def _calc_direction_consistency(self, row: pd.Series) -> float:
        """计算三周期方向一致性"""
        hexes = [row['mn1_hex'], row['w1_hex'], row['d1_hex']]
        scores = [self.encoder._from_signed_hex(h) for h in hexes]

        # 统计正负
        positives = sum(1 for s in scores if s > 0)
        negatives = sum(1 for s in scores if s < 0)
        neutrals = sum(1 for s in scores if s == 0)

        if neutrals == 3:
            return 0.0
        if positives == 3:
            return 1.0
        if negatives == 3:
            return -1.0
        if positives == 2 and neutrals == 1:
            return 0.7
        if negatives == 2 and neutrals == 1:
            return -0.7
        if positives == 2 and negatives == 1:
            return 0.3
        if negatives == 2 and positives == 1:
            return -0.3

        return 0.0

    def get_state_regime_at(
        self,
        timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """获取指定时间点的状态环境"""
        if not self.engine.triplets:
            return None

        # 找到最近的三元组
        closest = None
        min_diff = None
        for t in self.engine.triplets:
            diff = abs((t.timestamp - timestamp).total_seconds())
            if min_diff is None or diff < min_diff:
                min_diff = diff
                closest = t

        if closest is None:
            return None

        return {
            "timestamp": closest.timestamp,
            "mn1_hex": closest.mn1_hex,
            "w1_hex": closest.w1_hex,
            "d1_hex": closest.d1_hex,
            "mn1_desc": self.encoder.describe(closest.mn1_hex),
            "w1_desc": self.encoder.describe(closest.w1_hex),
            "d1_desc": self.encoder.describe(closest.d1_hex),
            "direction_consistency": self._calc_direction_consistency_from_triplet(closest),
        }

    def _calc_direction_consistency_from_triplet(self, triplet: StateHexTriplet) -> float:
        """从三元组计算方向一致性"""
        hexes = [triplet.mn1_hex, triplet.w1_hex, triplet.d1_hex]
        scores = [self.encoder._from_signed_hex(h) for h in hexes]

        positives = sum(1 for s in scores if s > 0)
        negatives = sum(1 for s in scores if s < 0)
        neutrals = sum(1 for s in scores if s == 0)

        if neutrals == 3:
            return 0.0
        if positives == 3:
            return 1.0
        if negatives == 3:
            return -1.0
        if positives == 2 and neutrals == 1:
            return 0.7
        if negatives == 2 and neutrals == 1:
            return -0.7
        if positives == 2 and negatives == 1:
            return 0.3
        if negatives == 2 and positives == 1:
            return -0.3

        return 0.0

    def get_triplet_at(self, timestamp: datetime) -> Optional[StateHexTriplet]:
        """获取指定时间点的三元组"""
        if not self.engine.triplets:
            return None

        for t in self.engine.triplets:
            if t.timestamp.date() == timestamp.date():
                return t
        return None


# ============================================================================
# MISS 融合引擎
# ============================================================================

class MISSEngine:
    """
    MISS 融合引擎 (Market Information State Segmentation)

    4个正交维度 × 25个子状态

    维度:
    1. Price (价格): 趋势/震荡/反转/突破/中性
    2. Volume (成交量): 放量/缩量/均量/异常/中性
    3. Liquidity (流动性): 充裕/紧张/枯竭/恢复/中性
    4. Information (信息): 平静/预期/发布/消化/中性

    与 State Hex 的关系:
    - State Hex 提供"体检码"（当前状态快照）
    - MISS 提供"环境画像"（市场生态描述）
    - 两者融合形成完整的观察环境
    """

    def __init__(self):
        self.price_analyzer = PriceStateAnalyzer()
        self.volume_analyzer = VolumeStateAnalyzer()
        self.liquidity_analyzer = LiquidityStateAnalyzer()
        self.info_analyzer = InformationStateAnalyzer()

    def compute_miss_snapshot(
        self,
        d1_df: pd.DataFrame,
        lookback: int = 20,
    ) -> MISSSnapshot:
        """
        计算MISS快照

        Args:
            d1_df: D1 OHLCV数据
            lookback: 回看周期

        Returns:
            MISSSnapshot
        """
        if len(d1_df) < lookback:
            logger.warning(f"数据不足计算MISS: {len(d1_df)} < {lookback}")
            return MISSSnapshot(timestamp=d1_df['timestamp'].iloc[-1] if not d1_df.empty else datetime.now())

        latest = d1_df.iloc[-1]
        recent = d1_df.tail(lookback)

        # 计算各维度状态
        price_state, price_conf = self.price_analyzer.analyze(recent)
        volume_state, volume_conf = self.volume_analyzer.analyze(recent)
        liquidity_state, liquidity_conf = self.liquidity_analyzer.analyze(recent)
        info_state, info_conf = self.info_analyzer.analyze(recent)

        return MISSSnapshot(
            timestamp=latest['timestamp'],
            price_state=price_state,
            price_state_confidence=price_conf,
            volume_state=volume_state,
            volume_state_confidence=volume_conf,
            liquidity_state=liquidity_state,
            liquidity_state_confidence=liquidity_conf,
            info_state=info_state,
            info_state_confidence=info_conf,
        )

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
        # 基础信心度（从State Hex计算）
        base_confidence = self._calc_base_confidence(triplet)

        # MISS调整
        adjustment = self._calc_miss_adjustment(miss_snapshot, triplet)

        fused_confidence = max(0.0, min(1.0, base_confidence + adjustment))

        # 生成融合标签
        tags = self._generate_fused_tags(triplet, miss_snapshot, adjustment)

        # 构建解释
        explanation = self._build_fusion_explanation(triplet, miss_snapshot, fused_confidence, adjustment)

        return FusedState(
            timestamp=miss_snapshot.timestamp,
            triplet=triplet,
            miss_snapshot=miss_snapshot,
            fused_confidence=fused_confidence,
            fused_tags=tags,
            explanation=explanation,
        )

    def _calc_base_confidence(self, triplet: StateHexTriplet) -> float:
        """从三元组计算基础信心度"""
        mn1_score = StateHexEncoder._from_signed_hex(triplet.mn1_hex)
        w1_score = StateHexEncoder._from_signed_hex(triplet.w1_hex)
        d1_score = StateHexEncoder._from_signed_hex(triplet.d1_hex)

        # 三周期同向 = 高信心度
        if (mn1_score > 0 and w1_score > 0 and d1_score > 0) or \
           (mn1_score < 0 and w1_score < 0 and d1_score < 0):
            base = 0.7
        # 两周期同向 = 中等
        elif (mn1_score > 0 and w1_score > 0) or (w1_score > 0 and d1_score > 0) or \
             (mn1_score < 0 and w1_score < 0) or (w1_score < 0 and d1_score < 0):
            base = 0.5
        else:
            base = 0.3

        # 持续时间加成
        if triplet.d1_duration >= 3:
            base += 0.05
        if triplet.w1_duration >= 2:
            base += 0.05

        return min(base, 1.0)

    def _calc_miss_adjustment(
        self,
        miss: MISSSnapshot,
        triplet: StateHexTriplet,
    ) -> float:
        """计算MISS对信心度的调整值"""
        adjustment = 0.0

        # 获取State Hex方向
        d1_score = StateHexEncoder._from_signed_hex(triplet.d1_hex)
        triplet_direction = "bull" if d1_score > 0 else "bear" if d1_score < 0 else "neutral"

        # 1. Price维度确认
        if triplet_direction == "bull" and miss.price_state in ["trend", "breakout"]:
            adjustment += 0.10
        elif triplet_direction == "bear" and miss.price_state in ["trend", "breakout"]:
            adjustment += 0.10
        elif miss.price_state == "reversal" and triplet_direction != "neutral":
            adjustment -= 0.10  # 反转信号与趋势信号矛盾

        # 2. Volume维度确认
        if miss.volume_state == "expanding":
            adjustment += 0.05
        elif miss.volume_state == "shrinking":
            adjustment -= 0.05

        # 3. Liquidity维度
        if miss.liquidity_state == "tight":
            adjustment -= 0.10
        elif miss.liquidity_state == "dry":
            adjustment -= 0.15

        # 4. Information维度
        if miss.info_state == "release":
            adjustment -= 0.05  # 信息发布期不确定性高

        return adjustment

    def _generate_fused_tags(
        self,
        triplet: StateHexTriplet,
        miss: MISSSnapshot,
        adjustment: float,
    ) -> List[str]:
        """生成融合标签"""
        tags = []

        # State Hex标签
        d1_score = StateHexEncoder._from_signed_hex(triplet.d1_hex)
        if d1_score > 0:
            tags.append("D1多向")
        elif d1_score < 0:
            tags.append("D1空向")

        if triplet.d1_duration >= 3:
            tags.append(f"D1持续{triplet.d1_duration}天")
        if triplet.w1_duration >= 2:
            tags.append(f"W1持续{triplet.w1_duration}周")

        # MISS标签
        if miss.price_state not in ["unknown", "neutral"]:
            tags.append(f"价格:{miss.price_state}")
        if miss.volume_state not in ["unknown", "neutral"]:
            tags.append(f"成交:{miss.volume_state}")
        if miss.liquidity_state not in ["unknown", "neutral"]:
            tags.append(f"流动性:{miss.liquidity_state}")

        # 融合标签
        if adjustment > 0.1:
            tags.append("环境确认")
        elif adjustment < -0.1:
            tags.append("环境警告")

        return tags

    def _build_fusion_explanation(
        self,
        triplet: StateHexTriplet,
        miss: MISSSnapshot,
        fused_confidence: float,
        adjustment: float,
    ) -> str:
        """构建融合解释"""
        parts = []

        # State Hex描述
        encoder = StateHexEncoder()
        parts.append(f"State: D1={encoder.describe(triplet.d1_hex)}")

        # MISS描述
        miss_parts = []
        if miss.price_state not in ["unknown", "neutral"]:
            miss_parts.append(f"价格{miss.price_state}")
        if miss.volume_state not in ["unknown", "neutral"]:
            miss_parts.append(f"成交{miss.volume_state}")
        if miss.liquidity_state not in ["unknown", "neutral"]:
            miss_parts.append(f"流动性{miss.liquidity_state}")

        if miss_parts:
            parts.append(f"MISS: {' | '.join(miss_parts)}")

        # 融合结果
        parts.append(f"融合信心度: {fused_confidence:.1%} (调整{'+' if adjustment >= 0 else ''}{adjustment:.0%})")

        return " | ".join(parts)


# ============================================================================
# MISS 子维度分析器
# ============================================================================

class PriceStateAnalyzer:
    """价格状态分析器"""

    def analyze(self, df: pd.DataFrame) -> Tuple[str, float]:
        """分析价格状态"""
        if len(df) < 10:
            return "unknown", 0.0

        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values

        # 计算趋势强度 (ADX简化版)
        returns = np.diff(closes) / closes[:-1]
        trend_strength = abs(np.mean(returns)) / (np.std(returns) + 1e-10)

        # 计算震荡指标
        price_range = (highs[-5:].max() - lows[-5:].min()) / closes[-1]

        # 判断突破
        recent_high = highs[-10:].max()
        recent_low = lows[-10:].min()
        current_close = closes[-1]

        is_breakout_up = current_close > recent_high * 0.998
        is_breakout_down = current_close < recent_low * 1.002

        # 判定
        if is_breakout_up or is_breakout_down:
            return "breakout", min(0.9, trend_strength * 2)

        if trend_strength > 0.5:
            return "trend", min(0.9, trend_strength)

        if price_range < 0.02:  # 2%以内震荡
            return "oscillation", 0.6

        # 检查反转信号
        if len(returns) >= 3:
            if returns[-1] * returns[-2] < 0 and abs(returns[-1]) > abs(returns[-2]):
                return "reversal", 0.5

        return "neutral", 0.3


class VolumeStateAnalyzer:
    """成交量状态分析器"""

    def analyze(self, df: pd.DataFrame) -> Tuple[str, float]:
        """分析成交量状态"""
        if len(df) < 10 or 'volume' not in df.columns:
            return "unknown", 0.0

        volumes = df['volume'].values
        avg_vol = np.mean(volumes[:-5])  # 前N-5天平均
        recent_vol = np.mean(volumes[-5:])  # 最近5天平均

        if avg_vol <= 0:
            return "unknown", 0.0

        ratio = recent_vol / avg_vol

        if ratio > 2.0:
            return "anomaly", 0.9  # 异常放量
        elif ratio > 1.5:
            return "expanding", 0.7
        elif ratio < 0.5:
            return "shrinking", 0.6
        elif ratio < 0.8:
            return "shrinking", 0.4

        return "average", 0.3


class LiquidityStateAnalyzer:
    """流动性状态分析器"""

    def analyze(self, df: pd.DataFrame) -> Tuple[str, float]:
        """分析流动性状态"""
        if len(df) < 10:
            return "unknown", 0.0

        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        # 用日内波动率作为流动性代理
        daily_ranges = (highs - lows) / closes
        avg_range = np.mean(daily_ranges[:-5])
        recent_range = np.mean(daily_ranges[-5:])

        if avg_range <= 0:
            return "unknown", 0.0

        ratio = recent_range / avg_range

        # 波动率异常高 = 流动性紧张或枯竭
        if ratio > 3.0:
            return "dry", 0.9
        elif ratio > 2.0:
            return "tight", 0.7
        elif ratio < 0.5:
            return "ample", 0.6
        elif ratio < 0.8:
            return "recovering", 0.4

        return "neutral", 0.3


class InformationStateAnalyzer:
    """信息状态分析器（简化版）"""

    def analyze(self, df: pd.DataFrame) -> Tuple[str, float]:
        """分析信息状态

        简化实现：基于价格波动率突变判断信息发布/消化期
        实际应用中可接入新闻日历、财报日期等外部数据
        """
        if len(df) < 10:
            return "unknown", 0.0

        closes = df['close'].values
        returns = np.diff(closes) / closes[:-1]

        # 计算滚动波动率
        if len(returns) < 5:
            return "unknown", 0.0

        recent_vol = np.std(returns[-5:])
        hist_vol = np.std(returns[:-5]) if len(returns) > 5 else recent_vol

        if hist_vol <= 0:
            return "calm", 0.3

        vol_ratio = recent_vol / hist_vol

        # 波动率突然放大 = 信息发布期
        if vol_ratio > 3.0:
            return "release", 0.8
        elif vol_ratio > 2.0:
            return "expectation", 0.6
        elif vol_ratio < 0.5:
            return "calm", 0.5

        return "digestion", 0.4


# ============================================================================
# 特征计算管线
# ============================================================================

class FeaturePipeline:
    """
    特征计算管线

    将原始数据 → 状态特征 → 策略可用特征
    支持增量计算（回测时逐日推进）
    """

    def __init__(self):
        self.state_engine = StateHexComputeEngine()
        self.miss_engine = MISSEngine()
        self.moneyflow_layer: Optional[MoneyflowEnergyLayer] = None
        # 回测缓存
        self._cached_triplet_series: Optional[pd.DataFrame] = None
        self._cached_data_hash: Optional[int] = None

    def compute_daily_features(
        self,
        data_up_to_today: pd.DataFrame,
    ) -> DailyFeatures:
        """
        计算截至今日的所有特征

        关键约束: 严格只用今天及之前的数据
        （Walk-Forward 防前视偏差）
        """
        if data_up_to_today.empty:
            raise ValueError("数据不能为空")

        latest = data_up_to_today.iloc[-1]
        timestamp = pd.to_datetime(latest['timestamp'])

        # 1. 计算State Hex三元组
        triplet_series = self.state_engine.compute_triplet_series(data_up_to_today)
        triplet = self.state_engine.get_triplet_at(timestamp) if not triplet_series.empty else None

        # 2. 计算MISS
        miss = self.miss_engine.compute_miss_snapshot(data_up_to_today)

        # 3. 融合
        fused = None
        if triplet is not None:
            fused = self.miss_engine.fuse_with_state_hex(miss, triplet)

        # 4. 构建OHLCVBar
        ohlcv = OHLCVBar(
            timestamp=timestamp,
            open=float(latest['open']),
            high=float(latest['high']),
            low=float(latest['low']),
            close=float(latest['close']),
            volume=float(latest.get('volume', 0)),
        )

        # 5. 计算技术指标
        tech_indicators = self._calc_technical_indicators(data_up_to_today)

        # 6. 状态转移信息
        transitions = {}
        if not triplet_series.empty:
            transitions = self._get_latest_transitions(triplet_series)

        return DailyFeatures(
            timestamp=timestamp,
            triplet=triplet,
            miss_snapshot=miss,
            fused_state=fused,
            ohlcv=ohlcv,
            technical_indicators=tech_indicators,
            state_transitions=transitions,
        )

    def compute_for_backtest_day(
        self,
        historical_df: pd.DataFrame,
        current_idx: int,
    ) -> DailyFeatures:
        """
        回测专用: 逐日计算特征（带缓存优化，避免O(n²)重复计算）

        Args:
            historical_df: 完整历史数据
            current_idx: 当前回测日索引

        Returns:
            DailyFeatures
        """
        # 只取到当前日的数据（防前视偏差）
        data_up_to_today = historical_df.iloc[:current_idx + 1].copy()

        # 缓存优化：如果数据是增量追加的，复用已计算的三元组
        data_hash = hash(tuple(data_up_to_today['close'].values))
        if self._cached_data_hash == data_hash and self._cached_triplet_series is not None:
            # 使用缓存的三元组序列
            latest = data_up_to_today.iloc[-1]
            timestamp = pd.to_datetime(latest['timestamp'])
            triplet = self.state_engine.get_triplet_at(timestamp)
            triplet_series = self._cached_triplet_series
        else:
            # 重新计算（首次或数据变化）
            triplet_series = self.state_engine.compute_triplet_series(data_up_to_today)
            latest = data_up_to_today.iloc[-1]
            timestamp = pd.to_datetime(latest['timestamp'])
            triplet = self.state_engine.get_triplet_at(timestamp) if not triplet_series.empty else None
            self._cached_triplet_series = triplet_series
            self._cached_data_hash = data_hash

        # 2. 计算MISS
        miss = self.miss_engine.compute_miss_snapshot(data_up_to_today)

        # 3. 融合
        fused = None
        if triplet is not None:
            fused = self.miss_engine.fuse_with_state_hex(miss, triplet)

        # 4. 构建OHLCVBar
        ohlcv = OHLCVBar(
            timestamp=timestamp,
            open=float(latest['open']),
            high=float(latest['high']),
            low=float(latest['low']),
            close=float(latest['close']),
            volume=float(latest.get('volume', 0)),
        )

        # 5. 计算技术指标
        tech_indicators = self._calc_technical_indicators(data_up_to_today)

        # 6. 状态转移信息
        transitions = {}
        if not triplet_series.empty:
            transitions = self._get_latest_transitions(triplet_series)

        return DailyFeatures(
            timestamp=timestamp,
            triplet=triplet,
            miss_snapshot=miss,
            fused_state=fused,
            ohlcv=ohlcv,
            technical_indicators=tech_indicators,
            state_transitions=transitions,
        )

    def _calc_technical_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算技术指标"""
        indicators = {}

        if len(df) < 20:
            return indicators

        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values

        # ATR
        tr1 = highs[-14:] - lows[-14:]
        tr2 = np.abs(highs[-14:] - np.roll(closes, 1)[-14:])
        tr3 = np.abs(lows[-14:] - np.roll(closes, 1)[-14:])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        indicators['atr'] = float(np.mean(tr))

        # RSI (简化版)
        if len(closes) >= 14:
            deltas = np.diff(closes[-15:])
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                indicators['rsi'] = 100 - (100 / (1 + rs))
            else:
                indicators['rsi'] = 100.0

        # 均线
        indicators['sma20'] = float(np.mean(closes[-20:])) if len(closes) >= 20 else closes[-1]
        indicators['sma50'] = float(np.mean(closes[-50:])) if len(closes) >= 50 else closes[-1]

        return indicators

    def _get_latest_transitions(self, triplet_series: pd.DataFrame) -> Dict[str, Any]:
        """获取最新状态转移"""
        if len(triplet_series) < 2:
            return {}

        latest = triplet_series.iloc[-1]
        prev = triplet_series.iloc[-2]

        return {
            "d1_transition": f"{prev['d1_hex']}→{latest['d1_hex']}",
            "w1_transition": f"{prev['w1_hex']}→{latest['w1_hex']}",
            "mn1_transition": f"{prev['mn1_hex']}→{latest['mn1_hex']}",
            "direction_consistency": latest.get('direction_consistency', 0),
        }


# ============================================================================
# 状态演化追踪器
# ============================================================================

class StateEvolutionTracker:
    """
    状态演化追踪器

    追踪三元组随时间的连续演化规律
    记录状态转移路径、持续时间分布等
    """

    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        self.triplet_history: deque = deque(maxlen=max_history)
        self.transition_counts: Dict[str, int] = {}
        self.state_duration_stats: Dict[str, List[int]] = {}

    def add_triplet(self, triplet: StateHexTriplet):
        """添加三元组到历史"""
        self.triplet_history.append(triplet)

        # 更新转移计数
        if len(self.triplet_history) >= 2:
            prev = self.triplet_history[-2]
            transition = f"D1:{prev.d1_hex}→{triplet.d1_hex}"
            self.transition_counts[transition] = self.transition_counts.get(transition, 0) + 1

    def get_transition_matrix(self) -> pd.DataFrame:
        """获取状态转移矩阵"""
        if not self.transition_counts:
            return pd.DataFrame()

        data = []
        for transition, count in self.transition_counts.items():
            data.append({"transition": transition, "count": count})

        df = pd.DataFrame(data)
        df = df.sort_values("count", ascending=False)
        return df

    def get_state_duration_distribution(self, period: str = "D1") -> Dict[str, Any]:
        """获取状态持续时间分布"""
        if not self.triplet_history:
            return {}

        durations = []
        if period == "D1":
            durations = [t.d1_duration for t in self.triplet_history]
        elif period == "W1":
            durations = [t.w1_duration for t in self.triplet_history]
        elif period == "MN1":
            durations = [t.mn1_duration for t in self.triplet_history]

        if not durations:
            return {}

        return {
            "mean": float(np.mean(durations)),
            "median": float(np.median(durations)),
            "max": int(np.max(durations)),
            "min": int(np.min(durations)),
            "std": float(np.std(durations)),
            "distribution": pd.Series(durations).value_counts().to_dict(),
        }

    def get_current_regime_summary(self) -> Dict[str, Any]:
        """获取当前状态环境摘要"""
        if not self.triplet_history:
            return {}

        latest = self.triplet_history[-1]
        encoder = StateHexEncoder()

        return {
            "timestamp": latest.timestamp,
            "mn1_hex": latest.mn1_hex,
            "w1_hex": latest.w1_hex,
            "d1_hex": latest.d1_hex,
            "mn1_desc": encoder.describe(latest.mn1_hex),
            "w1_desc": encoder.describe(latest.w1_hex),
            "d1_desc": encoder.describe(latest.d1_hex),
            "mn1_duration": latest.mn1_duration,
            "w1_duration": latest.w1_duration,
            "d1_duration": latest.d1_duration,
            "history_length": len(self.triplet_history),
        }


# ============================================================================
# 便捷函数
# ============================================================================

def compute_features_for_backtest(
    aligned_df: pd.DataFrame,
    current_idx: int,
) -> DailyFeatures:
    """
    回测便捷函数: 计算指定日期的特征

    Args:
        aligned_df: 对齐后的多周期数据
        current_idx: 当前索引

    Returns:
        DailyFeatures
    """
    pipeline = FeaturePipeline()
    return pipeline.compute_for_backtest_day(aligned_df, current_idx)


def fuse_confidence(
    base_confidence: float,
    miss_snapshot: MISSSnapshot,
    triplet_direction: str,
) -> float:
    """
    融合信心度计算（独立函数）

    Args:
        base_confidence: State Hex基础信心度
        miss_snapshot: MISS快照
        triplet_direction: 三元组方向 ("bull"/"bear"/"neutral")

    Returns:
        调整后的信心度
    """
    adjusted = base_confidence

    # MISS Price确认
    if triplet_direction == "bull" and miss_snapshot.price_state in ["trend", "breakout"]:
        adjusted += 0.10
    elif triplet_direction == "bear" and miss_snapshot.price_state in ["trend", "breakout"]:
        adjusted += 0.10
    elif miss_snapshot.price_state == "reversal":
        adjusted -= 0.10

    # MISS Volume确认
    if miss_snapshot.volume_state == "expanding":
        adjusted += 0.05
    elif miss_snapshot.volume_state == "shrinking":
        adjusted -= 0.05

    # MISS Liquidity
    if miss_snapshot.liquidity_state == "tight":
        adjusted -= 0.10
    elif miss_snapshot.liquidity_state == "dry":
        adjusted -= 0.15

    return max(0.0, min(1.0, adjusted))


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Compute Layer Test")
    print("=" * 70)

    # 生成测试数据
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

    print(f"\n测试数据: {len(test_df)} 个交易日")

    # 1. 测试 StateHexComputeEngine
    print("\n[1] StateHexComputeEngine 测试")
    state_engine = StateHexComputeEngine()
    triplet_series = state_engine.compute_triplet_series(test_df)

    if not triplet_series.empty:
        print(f"  三元组序列: {len(triplet_series)}行")
        print(f"  最新三元组:")
        latest = triplet_series.iloc[-1]
        print(f"    MN1: {latest['mn1_hex']} | W1: {latest['w1_hex']} | D1: {latest['d1_hex']}")
        print(f"    D1描述: {latest['d1_desc']}")

        # 状态转移
        transition_df = state_engine.compute_state_transitions(triplet_series)
        print(f"  方向一致性: {transition_df['direction_consistency'].iloc[-1]:.2f}")

    # 2. 测试 MISSEngine
    print("\n[2] MISSEngine 测试")
    miss_engine = MISSEngine()
    miss = miss_engine.compute_miss_snapshot(test_df)

    print(f"  价格状态: {miss.price_state} (信心度: {miss.price_state_confidence:.2f})")
    print(f"  成交状态: {miss.volume_state} (信心度: {miss.volume_state_confidence:.2f})")
    print(f"  流动性: {miss.liquidity_state} (信心度: {miss.liquidity_state_confidence:.2f})")
    print(f"  信息状态: {miss.info_state} (信心度: {miss.info_state_confidence:.2f})")

    # 3. 测试融合
    print("\n[3] State Hex + MISS 融合测试")
    if not triplet_series.empty:
        triplet = state_engine.get_triplet_at(test_df['timestamp'].iloc[-1])
        if triplet:
            fused = miss_engine.fuse_with_state_hex(miss, triplet)
            print(f"  融合信心度: {fused.fused_confidence:.2%}")
            print(f"  融合标签: {', '.join(fused.fused_tags)}")
            print(f"  融合解释: {fused.explanation}")

    # 4. 测试 FeaturePipeline
    print("\n[4] FeaturePipeline 测试")
    pipeline = FeaturePipeline()
    features = pipeline.compute_daily_features(test_df)

    print(f"  时间戳: {features.timestamp}")
    print(f"  三元组: MN1={features.triplet.mn1_hex if features.triplet else 'N/A'} "
          f"W1={features.triplet.w1_hex if features.triplet else 'N/A'} "
          f"D1={features.triplet.d1_hex if features.triplet else 'N/A'}")
    print(f"  技术指标: {list(features.technical_indicators.keys())}")
    print(f"  状态转移: {features.state_transitions}")

    # 5. 测试 StateEvolutionTracker
    print("\n[5] StateEvolutionTracker 测试")
    tracker = StateEvolutionTracker()
    for _, row in triplet_series.iterrows():
        from ai_engine.state_hex_engine import StateHexTriplet
        t = StateHexTriplet(
            timestamp=row['timestamp'],
            mn1_hex=row['mn1_hex'],
            w1_hex=row['w1_hex'],
            d1_hex=row['d1_hex'],
            mn1_duration=row['mn1_duration'],
            w1_duration=row['w1_duration'],
            d1_duration=row['d1_duration'],
        )
        tracker.add_triplet(t)

    summary = tracker.get_current_regime_summary()
    print(f"  当前状态: D1={summary.get('d1_hex')} | 持续{summary.get('d1_duration')}天")

    duration_dist = tracker.get_state_duration_distribution("D1")
    print(f"  D1持续时间: 均值={duration_dist.get('mean', 0):.1f} 最大={duration_dist.get('max', 0)}")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
