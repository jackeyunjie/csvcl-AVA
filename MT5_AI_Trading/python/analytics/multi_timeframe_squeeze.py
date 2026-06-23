"""
多周期收缩观测系统 - Multi-Timeframe Squeeze Observer

架构设计：
1. 每个周期（MN1/W1/D1/H4/H1）是独立的观测Agent
2. 各Agent只关注自己周期的收缩指标
3. 上层DebateAgent收集各周期观点，进行跨周期辩论
4. 最终输出：多周期共振的交易策略

核心原则：
- 周期独立：每个Agent独立计算自己周期的指标
- 视角隔离：Agent之间不共享内部计算过程
- 上层聚合：只有DebateAgent能看到多周期全貌
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

import pandas as pd
import numpy as np

try:
    from analytics.squeeze_observer import SqueezeObserver
except ImportError:
    from squeeze_observer import SqueezeObserver

logger = logging.getLogger(__name__)


TIMEFRAME_PRIORITY = ["MN1", "W1", "D1", "H4", "H1"]
RECENT_SQUEEZE_BARS = {
    "MN1": 3,
    "W1": 4,
    "D1": 5,
    "H4": 8,
    "H1": 12,
}
MIN_TIMEFRAME_LOOKBACK_DAYS = {
    "MN1": 3600,
    "W1": 900,
    "D1": 240,
    "H4": 180,
    "H1": 120,
}


class Timeframe(Enum):
    """支持的分析周期"""
    MN1 = "MN1"
    W1 = "W1"
    D1 = "D1"
    H4 = "H4"
    H1 = "H1"


@dataclass
class TimeframeOpinion:
    """单个周期Agent的观测观点"""
    timeframe: str
    symbol: str
    timestamp: datetime

    # 收缩状态
    is_squeezing: bool = False
    squeeze_score: int = 0
    squeeze_conditions: List[str] = field(default_factory=list)

    # 关键指标
    bb_width: float = np.nan
    bb_squeezed: bool = False
    pivot_range: float = np.nan
    pivot_squeezed: bool = False
    sr_range: float = np.nan
    sr_squeezed: bool = False
    adx: float = np.nan
    adx_lt_20: bool = False
    adx_lt_13: bool = False
    adx_lt_9: bool = False
    state_is_zero: bool = False
    current_close: float = np.nan

    # 趋势方向（基于ADX DI+/-或价格位置）
    trend_bias: str = "neutral"  # "bullish" / "bearish" / "neutral"

    # 收缩后的突破状态
    recent_squeeze: bool = False
    recent_squeeze_score: int = 0
    recent_squeeze_bars: int = 0
    last_squeeze_bars_ago: Optional[int] = None
    breakout_confirmed: bool = False
    breakout_direction: str = "none"  # "up" / "down" / "none"
    breakout_strength: float = 0.0
    breakout_level: Optional[float] = None
    breakout_stop: Optional[float] = None
    breakout_target: Optional[float] = None
    breakout_conditions: List[str] = field(default_factory=list)

    # Agent的"信心"（基于数据质量和指标清晰度）
    confidence: float = 0.5  # 0-1

    # Agent的"观点陈述"（自然语言描述）
    statement: str = ""

    def to_dict(self) -> dict:
        return {
            'timeframe': self.timeframe,
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'is_squeezing': self.is_squeezing,
            'squeeze_score': self.squeeze_score,
            'squeeze_conditions': self.squeeze_conditions,
            'bb_width': self.bb_width,
            'bb_squeezed': self.bb_squeezed,
            'pivot_range': self.pivot_range,
            'pivot_squeezed': self.pivot_squeezed,
            'sr_range': self.sr_range,
            'sr_squeezed': self.sr_squeezed,
            'adx': self.adx,
            'adx_lt_20': self.adx_lt_20,
            'adx_lt_13': self.adx_lt_13,
            'adx_lt_9': self.adx_lt_9,
            'state_is_zero': self.state_is_zero,
            'current_close': self.current_close,
            'trend_bias': self.trend_bias,
            'recent_squeeze': self.recent_squeeze,
            'recent_squeeze_score': self.recent_squeeze_score,
            'recent_squeeze_bars': self.recent_squeeze_bars,
            'last_squeeze_bars_ago': self.last_squeeze_bars_ago,
            'breakout_confirmed': self.breakout_confirmed,
            'breakout_direction': self.breakout_direction,
            'breakout_strength': self.breakout_strength,
            'breakout_level': self.breakout_level,
            'breakout_stop': self.breakout_stop,
            'breakout_target': self.breakout_target,
            'breakout_conditions': self.breakout_conditions,
            'confidence': self.confidence,
            'statement': self.statement,
        }


@dataclass
class CrossTimeframeSignal:
    """跨周期辩论后的交易信号"""
    symbol: str
    timestamp: datetime

    # 各周期观点
    opinions: Dict[str, TimeframeOpinion] = field(default_factory=dict)

    # 辩论结果
    consensus_direction: str = "hold"  # "long" / "short" / "hold"
    consensus_confidence: float = 0.0
    debate_summary: str = ""

    # 多周期共振度
    resonance_score: int = 0  # 同时收缩的周期数
    resonance_timeframes: List[str] = field(default_factory=list)
    setup_resonance_score: int = 0  # 当前或近期收缩的周期数
    setup_resonance_timeframes: List[str] = field(default_factory=list)

    # 共振突破：这是最高优先级交易机会
    breakout_resonance_score: int = 0
    breakout_resonance_timeframes: List[str] = field(default_factory=list)
    breakout_direction: str = "none"  # "up" / "down" / "none" / "mixed"
    opportunity_stage: str = "none"  # none / squeeze_setup / leading_breakout / resonant_breakout / conflicted_breakout
    opportunity_grade: str = "D"
    action_note: str = ""
    audit_warnings: List[str] = field(default_factory=list)

    # 策略建议
    suggested_entry: Optional[float] = None
    suggested_stop: Optional[float] = None
    suggested_target: Optional[float] = None
    risk_reward: float = 0.0


class TimeframeAgent:
    """
    单周期收缩观测Agent

    职责：
    1. 只关注自己周期的数据
    2. 独立计算收缩指标
    3. 形成自己的观点（statement）
    4. 不与其他周期Agent直接通信
    """

    def __init__(self, timeframe: Timeframe, observer: SqueezeObserver):
        self.timeframe = timeframe
        self.observer = observer
        self.name = f"{timeframe.value}Agent"

    @staticmethod
    def _clean_number(value) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return np.nan
        return value if np.isfinite(value) else np.nan

    def _build_squeeze_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add per-bar squeeze conditions without leaking other timeframe data."""
        bb_hist = df['bb_width'].expanding(min_periods=20).quantile(0.20)
        pivot_hist = df['pivot_range'].expanding(min_periods=20).quantile(0.20)
        sr_hist = df['sr_range'].expanding(min_periods=20).quantile(0.20)

        df['bb_squeezed'] = df['bb_width'].le(bb_hist) & df['bb_width'].notna()
        df['pivot_squeezed'] = df['pivot_range'].le(pivot_hist) & df['pivot_range'].notna()
        df['sr_squeezed'] = df['sr_range'].le(sr_hist) & df['sr_range'].notna()
        df['adx_lt_20'] = df['adx'].lt(20) & df['adx'].notna()
        df['adx_lt_13'] = df['adx'].lt(13) & df['adx'].notna()
        df['adx_lt_9'] = df['adx'].lt(9) & df['adx'].notna()
        df['squeeze_score'] = (
            df[['bb_squeezed', 'pivot_squeezed', 'sr_squeezed', 'adx_lt_20', 'adx_lt_13', 'adx_lt_9']]
            .sum(axis=1)
            .astype(int)
        )
        df['structural_squeeze_score'] = (
            df[['bb_squeezed', 'pivot_squeezed', 'sr_squeezed']]
            .sum(axis=1)
            .astype(int)
        )
        df['is_squeezing'] = df['squeeze_score'] >= 2
        return df

    def _detect_breakout(self, df: pd.DataFrame) -> dict:
        """
        Detect a breakout only if this timeframe had a squeeze recently.

        The Agent still uses only its own OHLCV series. DebateAgent later aggregates
        these public facts across timeframes.
        """
        recent_window = RECENT_SQUEEZE_BARS.get(self.timeframe.value, 8)
        recent = df.tail(recent_window + 1).copy()
        squeeze_recent = recent[recent['is_squeezing']]

        if squeeze_recent.empty:
            return {
                'recent_squeeze': False,
                'recent_squeeze_score': 0,
                'recent_squeeze_bars': recent_window,
                'last_squeeze_bars_ago': None,
                'breakout_confirmed': False,
                'breakout_direction': 'none',
                'breakout_strength': 0.0,
                'breakout_level': None,
                'breakout_stop': None,
                'breakout_target': None,
                'breakout_conditions': [],
            }

        latest = df.iloc[-1]
        structural_recent = recent[recent['structural_squeeze_score'] > 0]
        anchor_recent = structural_recent if not structural_recent.empty else squeeze_recent
        last_squeeze_pos = int(anchor_recent.index[-1])
        latest_pos = int(df.index[-1])
        last_any_squeeze_pos = int(squeeze_recent.index[-1])
        last_squeeze_bars_ago = latest_pos - last_any_squeeze_pos
        squeeze_anchor = df.loc[last_squeeze_pos]

        range_start = max(0, last_squeeze_pos - 19)
        breakout_range = df.iloc[range_start:last_squeeze_pos + 1]
        resistance = self._clean_number(breakout_range['high'].max())
        support = self._clean_number(breakout_range['low'].min())
        close = self._clean_number(latest['close'])
        atr = self._clean_number((df['high'] - df['low']).rolling(14).mean().iloc[-1])
        if pd.isna(atr) or atr <= 0:
            atr = self._clean_number((breakout_range['high'] - breakout_range['low']).mean())
        if pd.isna(atr) or atr <= 0 or pd.isna(close):
            atr = 0.0

        direction = 'none'
        level = None
        strength = 0.0
        conditions = []
        if not pd.isna(resistance) and close > resistance:
            direction = 'up'
            level = resistance
            strength = (close - resistance) / atr if atr > 0 else 0.0
            conditions.append('Close>RecentResistance')
        elif not pd.isna(support) and close < support:
            direction = 'down'
            level = support
            strength = (support - close) / atr if atr > 0 else 0.0
            conditions.append('Close<RecentSupport')

        if direction != 'none':
            prior_close = self._clean_number(df['close'].iloc[-2]) if len(df) >= 2 else np.nan
            if direction == 'up' and not pd.isna(prior_close) and prior_close <= level:
                conditions.append('FreshBreakout')
            elif direction == 'down' and not pd.isna(prior_close) and prior_close >= level:
                conditions.append('FreshBreakout')

            squeeze_released = (
                not bool(latest['is_squeezing'])
                or int(latest['squeeze_score']) < int(squeeze_anchor['squeeze_score'])
            )
            if squeeze_released:
                conditions.append('SqueezeReleased')

        confirmed = direction != 'none' and strength >= 0.25 and 'SqueezeReleased' in conditions
        stop = support if direction == 'up' else resistance if direction == 'down' else None
        target = None
        if confirmed and stop is not None and not pd.isna(stop):
            risk = abs(close - stop)
            if risk > 0:
                target = close + risk * 2 if direction == 'up' else close - risk * 2

        return {
            'recent_squeeze': True,
            'recent_squeeze_score': int(squeeze_recent['squeeze_score'].max()),
            'recent_squeeze_bars': recent_window,
            'last_squeeze_bars_ago': last_squeeze_bars_ago,
            'breakout_confirmed': confirmed,
            'breakout_direction': direction,
            'breakout_strength': float(strength) if np.isfinite(strength) else 0.0,
            'breakout_level': level,
            'breakout_stop': stop,
            'breakout_target': target,
            'breakout_conditions': conditions,
        }

    def observe(self, symbol: str, df: pd.DataFrame) -> TimeframeOpinion:
        """
        观测指定品种在当前周期的收缩状态

        Args:
            symbol: 品种代码
            df: OHLCV DataFrame（已包含该周期数据）

        Returns:
            TimeframeOpinion: 该Agent的观点
        """
        if len(df) < 30:
            return TimeframeOpinion(
                timeframe=self.timeframe.value,
                symbol=symbol,
                timestamp=datetime.now(),
                statement=f"{self.name}: 数据不足，无法形成观点"
            )

        # 计算指标（只用自己的数据）
        df = df.copy()
        df['bb_width'] = SqueezeObserver.compute_bb_width(df['close'])
        df['pivot_range'] = SqueezeObserver.compute_pivot_range(df['high'], df['low'], df['close'])
        df['sr_range'] = SqueezeObserver.compute_sr_range(df['high'], df['low'], df['close'])
        df['adx'] = SqueezeObserver.compute_adx(df['high'], df['low'], df['close'])
        df = self._build_squeeze_columns(df.reset_index(drop=True))

        # 取最新数据
        latest = df.iloc[-1]
        ts = latest['timestamp'] if 'timestamp' in latest else datetime.now()

        # 计算分位数（基于历史）
        bb_hist = df['bb_width'].dropna()
        bb_20 = bb_hist.quantile(0.20) if len(bb_hist) >= 20 else np.nan

        pivot_hist = df['pivot_range'].dropna()
        pivot_20 = pivot_hist.quantile(0.20) if len(pivot_hist) >= 20 else np.nan

        sr_hist = df['sr_range'].dropna()
        sr_20 = sr_hist.quantile(0.20) if len(sr_hist) >= 20 else np.nan

        # 判定
        bb_squeezed = bool(latest['bb_squeezed'])
        pivot_squeezed = bool(latest['pivot_squeezed'])
        sr_squeezed = bool(latest['sr_squeezed'])
        adx_val = latest['adx'] if not pd.isna(latest['adx']) else np.nan
        adx_lt_20 = bool(latest['adx_lt_20'])
        adx_lt_13 = bool(latest['adx_lt_13'])
        adx_lt_9 = bool(latest['adx_lt_9'])

        # 趋势偏向（简化：基于价格相对于20周期均线的位置）
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        trend_bias = "bullish" if latest['close'] > ma20 else "bearish" if latest['close'] < ma20 else "neutral"

        # 收缩条件
        conditions = []
        if bb_squeezed: conditions.append("BB")
        if pivot_squeezed: conditions.append("Pivot")
        if sr_squeezed: conditions.append("SR")
        if adx_lt_20: conditions.append("ADX<20")
        if adx_lt_13: conditions.append("ADX<13")
        if adx_lt_9: conditions.append("ADX<9")

        squeeze_score = len(conditions)
        is_squeezing = squeeze_score >= 2
        breakout = self._detect_breakout(df)

        # 信心度（基于数据量和指标清晰度）
        confidence = min(1.0, len(df) / 100) * (0.5 + 0.1 * max(squeeze_score, breakout['recent_squeeze_score']))
        if breakout['breakout_confirmed']:
            confidence = min(1.0, confidence + 0.15 + min(0.15, breakout['breakout_strength'] * 0.03))

        # 生成观点陈述
        if breakout['breakout_confirmed']:
            action = '向上突破' if breakout['breakout_direction'] == 'up' else '向下突破'
            statement = (f"【{self.name}】{symbol} 收缩后{action} | "
                        f"近期收缩分={breakout['recent_squeeze_score']} | "
                        f"突破强度={breakout['breakout_strength']:.2f}ATR | "
                        f"级别={breakout['breakout_level']:.5g} | "
                        f"趋势偏向={trend_bias} | 条件={breakout['breakout_conditions']}")
        elif is_squeezing:
            statement = (f"【{self.name}】{symbol} 处于收缩状态 | "
                        f"分数={squeeze_score} | 条件={conditions} | "
                        f"趋势偏向={trend_bias} | ADX={adx_val:.1f} | "
                        f"BB={latest['bb_width']:.4f} | SR={latest['sr_range']:.2f}%")
        elif breakout['recent_squeeze']:
            statement = (f"【{self.name}】{symbol} 近期有收缩但未确认突破 | "
                        f"最高分={breakout['recent_squeeze_score']} | "
                        f"距上次收缩={breakout['last_squeeze_bars_ago']}根 | "
                        f"候选方向={breakout['breakout_direction']} | "
                        f"强度={breakout['breakout_strength']:.2f}ATR | "
                        f"趋势偏向={trend_bias}")
        else:
            statement = (f"【{self.name}】{symbol} 未收缩 | "
                        f"分数={squeeze_score} | ADX={adx_val:.1f} | "
                        f"趋势偏向={trend_bias}")

        return TimeframeOpinion(
            timeframe=self.timeframe.value,
            symbol=symbol,
            timestamp=ts,
            is_squeezing=is_squeezing,
            squeeze_score=squeeze_score,
            squeeze_conditions=conditions,
            bb_width=latest['bb_width'],
            bb_squeezed=bb_squeezed,
            pivot_range=latest['pivot_range'],
            pivot_squeezed=pivot_squeezed,
            sr_range=latest['sr_range'],
            sr_squeezed=sr_squeezed,
            adx=adx_val,
            adx_lt_20=adx_lt_20,
            adx_lt_13=adx_lt_13,
            adx_lt_9=adx_lt_9,
            current_close=latest['close'],
            trend_bias=trend_bias,
            recent_squeeze=breakout['recent_squeeze'],
            recent_squeeze_score=breakout['recent_squeeze_score'],
            recent_squeeze_bars=breakout['recent_squeeze_bars'],
            last_squeeze_bars_ago=breakout['last_squeeze_bars_ago'],
            breakout_confirmed=breakout['breakout_confirmed'],
            breakout_direction=breakout['breakout_direction'],
            breakout_strength=breakout['breakout_strength'],
            breakout_level=breakout['breakout_level'],
            breakout_stop=breakout['breakout_stop'],
            breakout_target=breakout['breakout_target'],
            breakout_conditions=breakout['breakout_conditions'],
            confidence=confidence,
            statement=statement,
        )


class DebateAgent:
    """
    跨周期辩论Agent

    职责：
    1. 收集各周期Agent的观点
    2. 分析多周期共振情况
    3. 进行"辩论"（检查一致性/矛盾）
    4. 输出最终交易信号
    """

    def __init__(self):
        self.name = "DebateAgent"

    @staticmethod
    def _direction_to_signal(direction: str) -> str:
        return "long" if direction == "up" else "short" if direction == "down" else "hold"

    @staticmethod
    def _bias_to_direction(bias: str) -> str:
        return "up" if bias == "bullish" else "down" if bias == "bearish" else "none"

    @staticmethod
    def _cap_confidence(value: float) -> float:
        return max(0.0, min(0.95, value))

    def debate(self, symbol: str, opinions: List[TimeframeOpinion]) -> CrossTimeframeSignal:
        """
        对各周期观点进行辩论，输出交易信号

        辩论逻辑：
        1. 统计当前收缩、近期收缩底座、已确认突破
        2. 检查突破方向是否跨周期同向
        3. 共振突破优先于单纯收缩
        4. 大周期只作为方向过滤和风险提示，不覆盖已确认事实
        """
        signal = CrossTimeframeSignal(
            symbol=symbol,
            timestamp=datetime.now(),
            opinions={op.timeframe: op for op in opinions}
        )

        # 1. 统计收缩周期数
        squeezing_ops = [op for op in opinions if op.is_squeezing]
        signal.resonance_score = len(squeezing_ops)
        signal.resonance_timeframes = [op.timeframe for op in squeezing_ops]
        setup_ops = [op for op in opinions if op.is_squeezing or op.recent_squeeze]
        signal.setup_resonance_score = len(setup_ops)
        signal.setup_resonance_timeframes = [op.timeframe for op in setup_ops]
        breakout_ops = [op for op in opinions if op.breakout_confirmed]

        # 2. 趋势方向一致性检查
        bullish_count = sum(1 for op in opinions if op.trend_bias == "bullish")
        bearish_count = sum(1 for op in opinions if op.trend_bias == "bearish")
        neutral_count = sum(1 for op in opinions if op.trend_bias == "neutral")

        # 3. 辩论：大周期方向优先
        dominant_bias = "neutral"
        for tf in TIMEFRAME_PRIORITY:
            for op in opinions:
                if op.timeframe == tf and op.trend_bias != "neutral":
                    dominant_bias = op.trend_bias
                    break
            if dominant_bias != "neutral":
                break
        dominant_direction = self._bias_to_direction(dominant_bias)

        up_breakouts = [op for op in breakout_ops if op.breakout_direction == "up"]
        down_breakouts = [op for op in breakout_ops if op.breakout_direction == "down"]
        if up_breakouts and down_breakouts:
            signal.breakout_direction = "mixed"
            signal.opportunity_stage = "conflicted_breakout"
            signal.consensus_direction = "hold"
            signal.consensus_confidence = 0.45
            signal.action_note = "同一品种出现上下突破冲突，等待方向重新一致。"
            signal.audit_warnings.append("突破方向冲突：禁止把混合突破当作交易信号。")
        elif up_breakouts or down_breakouts:
            aligned_breakouts = up_breakouts if up_breakouts else down_breakouts
            breakout_direction = "up" if up_breakouts else "down"
            signal.breakout_direction = breakout_direction
            signal.breakout_resonance_score = len(aligned_breakouts)
            signal.breakout_resonance_timeframes = [op.timeframe for op in aligned_breakouts]
            avg_strength = float(np.mean([op.breakout_strength for op in aligned_breakouts]))
            against_dominant = dominant_direction != "none" and dominant_direction != breakout_direction

            entry_source = max(
                aligned_breakouts,
                key=lambda op: (
                    -(TIMEFRAME_PRIORITY.index(op.timeframe) if op.timeframe in TIMEFRAME_PRIORITY else 99),
                    op.breakout_strength,
                )
            )
            signal.suggested_entry = entry_source.current_close
            signal.suggested_stop = entry_source.breakout_stop
            signal.suggested_target = entry_source.breakout_target
            if (
                signal.suggested_entry is not None
                and signal.suggested_stop is not None
                and signal.suggested_target is not None
            ):
                risk = abs(signal.suggested_entry - signal.suggested_stop)
                reward = abs(signal.suggested_target - signal.suggested_entry)
                signal.risk_reward = reward / risk if risk > 0 else 0.0

            if signal.breakout_resonance_score >= 2 and signal.setup_resonance_score >= 2:
                signal.opportunity_stage = "resonant_breakout"
                signal.opportunity_grade = "A" if not against_dominant else "B"
                signal.consensus_direction = self._direction_to_signal(breakout_direction)
                confidence = 0.70 + 0.06 * signal.breakout_resonance_score + 0.03 * signal.setup_resonance_score
                confidence += min(0.08, avg_strength * 0.02)
                if against_dominant:
                    confidence -= 0.12
                    signal.audit_warnings.append("突破方向与大周期主导偏向相反，信心已降级。")
                signal.consensus_confidence = self._cap_confidence(confidence)
                signal.action_note = "最佳机会：多周期收缩后出现同向共振突破。"
            elif signal.setup_resonance_score >= 2:
                signal.opportunity_stage = "leading_breakout"
                signal.opportunity_grade = "B" if not against_dominant else "C"
                signal.consensus_direction = self._direction_to_signal(breakout_direction)
                confidence = 0.58 + 0.03 * signal.setup_resonance_score + min(0.06, avg_strength * 0.02)
                if against_dominant:
                    confidence -= 0.12
                    signal.audit_warnings.append("领先突破与大周期主导偏向相反，只作试探/观察。")
                signal.consensus_confidence = self._cap_confidence(confidence)
                signal.action_note = "领先突破：已有收缩共振，但突破只被一个周期确认，等待第二周期确认更稳。"
            else:
                signal.opportunity_stage = "none"
                signal.opportunity_grade = "C"
                signal.consensus_direction = "hold"
                signal.consensus_confidence = 0.35
                signal.action_note = "有单周期突破，但缺少多周期收缩底座，不纳入最佳机会。"
        elif signal.setup_resonance_score >= 2:
            signal.opportunity_stage = "squeeze_setup"
            signal.opportunity_grade = "B" if signal.setup_resonance_score >= 3 else "C"
            signal.consensus_direction = "hold"
            signal.consensus_confidence = 0.50 + 0.05 * min(3, signal.setup_resonance_score - 2)
            signal.action_note = "多周期收缩共振成立，但尚未突破；等待同向突破确认。"
        else:
            signal.opportunity_stage = "none"
            signal.opportunity_grade = "D"
            signal.consensus_direction = "hold"
            signal.consensus_confidence = 0.30
            signal.action_note = "无多周期收缩共振，也无有效共振突破。"

        # 5. 生成辩论摘要
        debate_lines = []
        debate_lines.append(f"=== 跨周期辩论: {symbol} ===")
        debate_lines.append(f"参与Agent: {len(opinions)}个周期")
        debate_lines.append(f"当前收缩周期: {signal.resonance_score}个 ({', '.join(signal.resonance_timeframes)})")
        debate_lines.append(f"收缩底座周期: {signal.setup_resonance_score}个 ({', '.join(signal.setup_resonance_timeframes)})")
        debate_lines.append(f"突破确认周期: {signal.breakout_resonance_score}个 ({', '.join(signal.breakout_resonance_timeframes)})")
        debate_lines.append(f"趋势统计: 看涨={bullish_count}, 看跌={bearish_count}, 中性={neutral_count}")
        debate_lines.append(f"主导偏向: {dominant_bias}")
        debate_lines.append(f"机会阶段: {signal.opportunity_stage} | 等级={signal.opportunity_grade}")
        debate_lines.append(f"突破方向: {signal.breakout_direction}")
        debate_lines.append(f"共识方向: {signal.consensus_direction} (信心={signal.consensus_confidence:.2f})")
        debate_lines.append(f"行动说明: {signal.action_note}")
        if signal.suggested_entry is not None:
            stop_text = f"{signal.suggested_stop:.5g}" if signal.suggested_stop is not None else "N/A"
            target_text = f"{signal.suggested_target:.5g}" if signal.suggested_target is not None else "N/A"
            debate_lines.append(
                f"交易位: entry={signal.suggested_entry:.5g}, "
                f"stop={stop_text}, "
                f"target={target_text}, "
                f"RR={signal.risk_reward:.2f}"
            )

        # 各Agent陈述
        debate_lines.append("\n--- 各Agent观点 ---")
        for op in sorted(opinions, key=lambda x: TIMEFRAME_PRIORITY.index(x.timeframe) if x.timeframe in TIMEFRAME_PRIORITY else 99):
            debate_lines.append(f"  {op.statement}")

        # 矛盾检测
        debate_lines.append("\n--- 矛盾检测 ---")
        if bullish_count > 0 and bearish_count > 0:
            debate_lines.append("  发现趋势方向矛盾，大周期只作为过滤，不直接替代突破事实。")
        else:
            debate_lines.append("  趋势方向一致")

        if signal.opportunity_stage == "resonant_breakout":
            debate_lines.append("  多周期共振突破成立：这是系统定义的最佳交易机会。")
        elif signal.opportunity_stage == "leading_breakout":
            debate_lines.append("  只有领先突破，未达到最佳机会标准。")
        elif signal.opportunity_stage == "squeeze_setup":
            debate_lines.append("  多周期收缩底座成立，但交易触发需等待突破。")
        elif signal.opportunity_stage == "conflicted_breakout":
            debate_lines.append("  突破方向冲突，保持观望。")
        else:
            debate_lines.append("  无有效收缩共振/突破共振")

        if signal.audit_warnings:
            debate_lines.append("\n--- 审计告警 ---")
            for warning in signal.audit_warnings:
                debate_lines.append(f"  {warning}")

        signal.debate_summary = "\n".join(debate_lines)

        return signal


class MultiTimeframeSqueezeSystem:
    """
    多周期收缩观测系统主控

    使用方式：
        system = MultiTimeframeSqueezeSystem()

        # 为每个周期准备数据
        data = {
            "H1": df_h1,
            "H4": df_h4,
            "D1": df_d1,
        }

        # 运行分析
        signal = system.analyze("EURUSD", data)
        print(signal.debate_summary)
    """

    def __init__(self, observer: SqueezeObserver = None):
        self.observer = observer or SqueezeObserver()
        self.agents: Dict[str, TimeframeAgent] = {}
        self.debate_agent = DebateAgent()

        # 初始化各周期Agent
        for tf in Timeframe:
            self.agents[tf.value] = TimeframeAgent(tf, self.observer)

    def analyze(self, symbol: str, timeframe_data: Dict[str, pd.DataFrame]) -> CrossTimeframeSignal:
        """
        分析指定品种的多周期收缩状态

        Args:
            symbol: 品种代码
            timeframe_data: {timeframe: df} 各周期数据

        Returns:
            CrossTimeframeSignal: 跨周期交易信号
        """
        logger.info(f"开始多周期分析: {symbol}")

        # 1. 各周期Agent独立观测
        opinions = []
        for tf_name, df in timeframe_data.items():
            if tf_name not in self.agents:
                logger.warning(f"未知周期: {tf_name}")
                continue

            agent = self.agents[tf_name]
            opinion = agent.observe(symbol, df)
            opinions.append(opinion)
            logger.info(f"  {tf_name}Agent: 分数={opinion.squeeze_score}, 收缩={opinion.is_squeezing}")

        # 2. DebateAgent进行跨周期辩论
        signal = self.debate_agent.debate(symbol, opinions)
        logger.info(f"  辩论结果: {signal.consensus_direction} (信心={signal.consensus_confidence:.2f})")

        return signal

    def analyze_from_mt5(self, symbol: str, mt5_symbol: str,
                         timeframes: List[str] = None,
                         lookback_days: int = 120) -> CrossTimeframeSignal:
        """
        从MT5获取多周期数据并分析

        Args:
            symbol: 标准品种名
            mt5_symbol: MT5品种名
            timeframes: 周期列表，默认[H1, H4, D1]
            lookback_days: 回看天数

        Returns:
            CrossTimeframeSignal
        """
        if timeframes is None:
            timeframes = ["MN1", "W1", "D1", "H4", "H1"]

        timeframe_data = {}

        for tf in timeframes:
            # lookback_days is a calendar span, not a bar count. Do not divide it
            # by timeframe length; higher timeframes need longer calendar history.
            tf_lookback = max(lookback_days, MIN_TIMEFRAME_LOOKBACK_DAYS.get(tf, lookback_days))

            df = self._fetch_mt5(mt5_symbol, tf, tf_lookback)
            if not df.empty:
                timeframe_data[tf] = df
                logger.info(f"  {tf}: {len(df)}条数据")

        if not timeframe_data:
            logger.error("无可用数据")
            return None

        return self.analyze(symbol, timeframe_data)

    def _fetch_mt5(self, mt5_symbol: str, timeframe: str, lookback_days: int) -> pd.DataFrame:
        """从MT5获取数据"""
        try:
            from backtest_platform.data_layer import MT5DataBridge
            bridge = MT5DataBridge()
            if not bridge.connect():
                return pd.DataFrame()

            end = datetime.now()
            start = end - timedelta(days=lookback_days)
            df = bridge.fetch_ohlcv(mt5_symbol, timeframe, start, end)
            bridge.disconnect()

            if df.empty:
                return pd.DataFrame()

            df.columns = [c.lower() for c in df.columns]
            if 'time' in df.columns and 'timestamp' not in df.columns:
                df = df.rename(columns={'time': 'timestamp'})

            return df

        except Exception as e:
            logger.warning(f"MT5获取失败 {mt5_symbol} {timeframe}: {e}")
            return pd.DataFrame()


def demo():
    """演示多周期辩论过程"""
    print("=" * 70)
    print("多周期收缩观测系统 - 演示")
    print("=" * 70)

    # 模拟各周期数据（实际应从MT5获取）
    np.random.seed(42)

    def make_df(n, vol, trend_dir=0):
        """生成模拟数据"""
        trend = np.cumsum(np.random.randn(n) * 0.2 + trend_dir * 0.1)
        close = 100 + trend
        vol_arr = np.ones(n) * vol
        high = close + np.abs(np.random.randn(n)) * vol_arr
        low = close - np.abs(np.random.randn(n)) * vol_arr
        open_p = close + np.random.randn(n) * vol_arr * 0.3
        for i in range(n):
            high[i] = max(high[i], close[i], open_p[i])
            low[i] = min(low[i], close[i], open_p[i])
        return pd.DataFrame({
            'timestamp': pd.date_range(end=datetime.now(), periods=n, freq='h'),
            'open': open_p,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.randint(1000, 10000, n),
        })

    # H1: 收缩中，趋势向上
    df_h1 = make_df(100, 0.5, trend_dir=0.5)
    # H4: 收缩中，趋势向上
    df_h4 = make_df(100, 1.0, trend_dir=0.5)
    # D1: 未收缩，趋势向上
    df_d1 = make_df(100, 2.0, trend_dir=0.5)

    data = {
        "H1": df_h1,
        "H4": df_h4,
        "D1": df_d1,
    }

    # 运行分析
    system = MultiTimeframeSqueezeSystem()
    signal = system.analyze("EURUSD", data)

    # 输出辩论结果
    print("\n" + signal.debate_summary)
    print("\n" + "=" * 70)
    print(f"最终信号: {signal.consensus_direction.upper()}")
    print(f"信心度: {signal.consensus_confidence:.2f}")
    print(f"共振周期: {signal.resonance_score}个")
    print("=" * 70)


if __name__ == "__main__":
    demo()
