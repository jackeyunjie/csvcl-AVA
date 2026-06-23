"""
State Hex 编码系统 - Hermass / 弘运系统统一状态编码

编码规则（基于 P107_STATE_HEX_ENCODING_RULES_20260517）：
- base: 0=收缩底座(contraction/closed), 8=非收缩底座(non-contraction)
- +1: volatility 幅动活跃
- +2: position 关键位/突破位置触发
- +4: trend 趋势触发
- 方向: 正号=多向/非空向语境, 负号=空向语境

常见编码:
0 = 收缩底座, 无额外组件
1 = 收缩底座 + 幅动活跃
2 = 收缩底座 + 位置触发
3 = 收缩底座 + 幅动活跃 + 位置触发
4 = 收缩底座 + 趋势触发
5 = 收缩底座 + 幅动活跃 + 趋势触发
6 = 收缩底座 + 位置触发 + 趋势触发
7 = 收缩底座 + 幅动活跃 + 位置触发 + 趋势触发
8 = 非收缩底座, 无额外组件
9 = 非收缩底座 + 幅动活跃
A = 非收缩底座 + 位置触发
B = 非收缩底座 + 幅动活跃 + 位置触发
C = 非收缩底座 + 趋势触发
D = 非收缩底座 + 幅动活跃 + 趋势触发
E = 非收缩底座 + 位置触发 + 趋势触发
F = 非收缩底座 + 幅动活跃 + 位置触发 + 趋势触发
-F = 空向语境下的 F
"""

import logging
from enum import Enum, auto
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CompressionState(Enum):
    """压缩/收缩状态"""
    CLOSED = "closed"           # 闭藏/收缩
    CONTRACTION = "contraction" # 收缩中
    EXPANSION_START = "expansion_start"
    EXPANSION = "expansion"
    STRONG_EXPANSION = "strong_expansion"
    NEUTRAL = "neutral"


class TrendState(Enum):
    """趋势状态"""
    BULL_START = "bull_start"
    BULL_TREND = "bull_trend"
    BULL_HIDDEN = "bull_hidden"
    BEAR_START = "bear_start"
    BEAR_TREND = "bear_trend"
    BEAR_HIDDEN = "bear_hidden"
    CLOSED = "closed"
    FLAT_HIDDEN = "flat_hidden"
    CONTRACTION = "contraction"
    NEUTRAL = "neutral"


class PositionState(Enum):
    """位置状态"""
    ABOVE_EXTREME = "above_extreme"
    ABOVE = "above"
    BREAK_UP = "break_up"
    BELOW_EXTREME = "below_extreme"
    BELOW = "below"
    BREAK_DOWN = "break_down"
    NEAR_RESISTANCE = "near_resistance"
    NEAR_SUPPORT = "near_support"
    NEUTRAL = "neutral"


class VolatilityState(Enum):
    """波动状态"""
    ACTIVE = "active"           # 幅动活跃
    NEUTRAL = "neutral"         # 中性


@dataclass(frozen=True)
class StateComponents:
    """状态组件（用于计算 state_score）"""
    compression: CompressionState = CompressionState.NEUTRAL
    trend: TrendState = TrendState.NEUTRAL
    position: PositionState = PositionState.NEUTRAL
    volatility: VolatilityState = VolatilityState.NEUTRAL


class StateHexEncoder:
    """
    State Hex 编码器

    核心公式:
    state_score = base(0 or 8) + volatility(1) + position(2) + trend(4)
    state_hex = signed_hex(state_score)
    """

    # 正向支持值（多头策略语境）
    POSITIVE_VALUES = {2, 3, 6, 7, 10, 11, 14, 15}
    # 阻断值（多头策略语境下的空头信号）
    VETO_VALUES = {-2, -3, -6, -7, -10, -11, -14, -15}

    def __init__(self):
        logger.info("StateHexEncoder初始化完成")

    def encode(self, components: StateComponents) -> str:
        """
        将状态组件编码为 state_hex

        Args:
            components: 状态组件 (compression, trend, position, volatility)

        Returns:
            state_hex 字符串，如 "F", "-F", "8", "0"
        """
        # 1. 计算 base (0 or 8)
        is_contraction = (
            components.compression in (CompressionState.CLOSED, CompressionState.CONTRACTION)
            or components.trend == TrendState.CLOSED
        )
        base = 0 if is_contraction else 8

        # 2. 计算组件位
        volatility_bit = 1 if components.volatility == VolatilityState.ACTIVE else 0
        position_bit = 2 if self._is_position_triggered(components.position) else 0
        trend_bit = 4 if self._is_trend_triggered(components.trend) else 0

        # 3. 计算绝对值
        magnitude = base + volatility_bit + position_bit + trend_bit

        # 4. 判断方向
        bull_context = self._is_bull_context(components.trend, components.position)
        bear_context = self._is_bear_context(components.trend, components.position)

        if bear_context and not bull_context:
            state_score = -magnitude
        else:
            state_score = magnitude

        # 5. 转为十六进制
        return self._to_signed_hex(state_score)

    def decode(self, state_hex: str) -> Tuple[int, bool, bool, bool, bool]:
        """
        解码 state_hex

        Returns:
            (state_score, is_contraction, has_volatility, has_position, has_trend)
        """
        state_score = self._from_signed_hex(state_hex)
        abs_score = abs(state_score)

        is_contraction = abs_score < 8
        base = 0 if is_contraction else 8
        remainder = abs_score - base

        has_volatility = bool(remainder & 0b0001)
        has_position = bool(remainder & 0b0010)
        has_trend = bool(remainder & 0b0100)

        return state_score, is_contraction, has_volatility, has_position, has_trend

    def describe(self, state_hex: str) -> str:
        """获取 state_hex 的文字描述"""
        state_score, is_contraction, has_vol, has_pos, has_trend = self.decode(state_hex)

        direction = "空向" if state_score < 0 else "多向/非空向"
        base = "收缩底座" if is_contraction else "非收缩底座"

        parts = [base]
        if has_vol:
            parts.append("幅动活跃")
        if has_pos:
            parts.append("位置触发")
        if has_trend:
            parts.append("趋势触发")

        return f"{state_hex}({state_score}) = {direction} | {' + '.join(parts)}"

    def is_positive_for_long(self, state_hex: str) -> bool:
        """判断是否为多头策略支持状态"""
        state_score = self._from_signed_hex(state_hex)
        return state_score in self.POSITIVE_VALUES

    def is_veto_for_long(self, state_hex: str) -> bool:
        """判断是否为多头策略阻断状态"""
        state_score = self._from_signed_hex(state_hex)
        return state_score in self.VETO_VALUES

    # -------------------------------------------------------------------------
    # 内部辅助
    # -------------------------------------------------------------------------

    @staticmethod
    def _is_position_triggered(position: PositionState) -> bool:
        """位置是否明确触发"""
        return position in {
            PositionState.ABOVE_EXTREME, PositionState.ABOVE,
            PositionState.BREAK_UP, PositionState.BELOW_EXTREME,
            PositionState.BELOW, PositionState.BREAK_DOWN
        }

    @staticmethod
    def _is_trend_triggered(trend: TrendState) -> bool:
        """趋势是否包含 bull/bear"""
        return trend in {
            TrendState.BULL_START, TrendState.BULL_TREND, TrendState.BULL_HIDDEN,
            TrendState.BEAR_START, TrendState.BEAR_TREND, TrendState.BEAR_HIDDEN
        }

    @staticmethod
    def _is_bull_context(trend: TrendState, position: PositionState) -> bool:
        """判断是否多向语境"""
        trend_bull = trend in {TrendState.BULL_START, TrendState.BULL_TREND, TrendState.BULL_HIDDEN}
        position_bull = position in {PositionState.ABOVE_EXTREME, PositionState.ABOVE, PositionState.BREAK_UP}
        return trend_bull or position_bull

    @staticmethod
    def _is_bear_context(trend: TrendState, position: PositionState) -> bool:
        """判断是否空向语境"""
        trend_bear = trend in {TrendState.BEAR_START, TrendState.BEAR_TREND, TrendState.BEAR_HIDDEN}
        position_bear = position in {PositionState.BELOW_EXTREME, PositionState.BELOW, PositionState.BREAK_DOWN}
        return trend_bear or position_bear

    @staticmethod
    def _to_signed_hex(value: int) -> str:
        """带符号的十六进制转换"""
        if value < 0:
            return f"-{format(abs(value), 'X')}"
        return format(value, 'X')

    @staticmethod
    def _from_signed_hex(hex_str: str) -> int:
        """带符号的十六进制解析"""
        hex_str = hex_str.strip().upper()
        if hex_str.startswith('-'):
            return -int(hex_str[1:], 16)
        return int(hex_str, 16)


# ============================================================================
# 便捷函数
# ============================================================================

def encode_state(compression: str, trend: str, position: str, volatility: str) -> str:
    """一键编码状态"""
    encoder = StateHexEncoder()
    comp = CompressionState(compression) if compression else CompressionState.NEUTRAL
    tr = TrendState(trend) if trend else TrendState.NEUTRAL
    pos = PositionState(position) if position else PositionState.NEUTRAL
    vol = VolatilityState(volatility) if volatility else VolatilityState.NEUTRAL
    return encoder.encode(StateComponents(comp, tr, pos, vol))


def describe_state(state_hex: str) -> str:
    """一键描述状态"""
    return StateHexEncoder().describe(state_hex)


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("State Hex 编码系统测试")
    print("=" * 70)

    encoder = StateHexEncoder()

    # 测试所有常见编码
    test_cases = [
        # (compression, trend, position, volatility, expected_hex)
        ("closed", "neutral", "neutral", "neutral", "0"),
        ("closed", "neutral", "neutral", "active", "1"),
        ("closed", "neutral", "break_up", "neutral", "2"),
        ("closed", "neutral", "break_up", "active", "3"),
        ("closed", "bull_trend", "neutral", "neutral", "4"),
        ("closed", "bull_trend", "neutral", "active", "5"),
        ("closed", "bull_trend", "break_up", "neutral", "6"),
        ("closed", "bull_trend", "break_up", "active", "7"),
        ("neutral", "neutral", "neutral", "neutral", "8"),
        ("neutral", "neutral", "neutral", "active", "9"),
        ("neutral", "neutral", "break_up", "neutral", "A"),
        ("neutral", "neutral", "break_up", "active", "B"),
        ("neutral", "bull_trend", "neutral", "neutral", "C"),
        ("neutral", "bull_trend", "neutral", "active", "D"),
        ("neutral", "bull_trend", "break_up", "neutral", "E"),
        ("neutral", "bull_trend", "break_up", "active", "F"),
        # 空向语境
        ("neutral", "bear_trend", "break_down", "active", "-F"),
        ("closed", "bear_trend", "break_down", "active", "-7"),
    ]

    print("\n[编码测试]")
    for comp, trend, pos, vol, expected in test_cases:
        result = encode_state(comp, trend, pos, vol)
        status = "OK" if result == expected else "NG"
        print(f"  {status} {comp:12s} + {trend:12s} + {pos:12s} + {vol:7s} → {result:3s} (期望 {expected})")

    # 测试解码
    print("\n[解码测试]")
    for hex_code in ["0", "7", "8", "F", "-F", "-7", "A", "3"]:
        desc = encoder.describe(hex_code)
        is_pos = encoder.is_positive_for_long(hex_code)
        is_veto = encoder.is_veto_for_long(hex_code)
        print(f"  {desc:60s} | 多头支持:{is_pos} | 多头阻断:{is_veto}")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
