"""
ACD 枢轴收缩检测系统

枢轴定义:
- 1日枢轴: (High + Low + Close) / 3
- 3日枢轴: 最近3日 (H+L+C)/3 的平均
- 6日枢轴: 最近6日 (H+L+C)/3 的平均

收缩判定:
1. 连续4天枢轴范围变小 (当日范围 < 前日范围)
2. 数值处于30天内较低水平 (< 30日 percentile 20%)
3. 多周期同时收缩 = 高概率突破前兆
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class PivotContraction:
    """枢轴收缩检测结果"""
    symbol: str
    pivot_1d: float
    pivot_3d: float
    pivot_6d: float
    range_1d: float
    range_3d: float
    range_6d: float
    contraction_days: int
    is_contracting: bool
    is_30d_low: bool
    squeeze_score: int  # 0-3, 收缩周期数


def calc_pivot(high: float, low: float, close: float) -> float:
    """计算枢轴点 (H + L + C) / 3"""
    return (high + low + close) / 3


def calc_pivot_range(df: pd.DataFrame, window: int = 1) -> pd.Series:
    """
    计算 N 日枢轴范围
    
    Args:
        df: DataFrame with [high, low, close]
        window: 1=1日, 3=3日, 6=6日
    
    Returns:
        Series of pivot ranges (max - min of pivots in window)
    """
    pivots = (df['high'] + df['low'] + df['close']) / 3
    
    if window == 1:
        return pivots
    
    # N日聚合
    return pivots.rolling(window=window).mean()


def detect_contraction(
    df: pd.DataFrame,
    contraction_days: int = 4,
    lookback: int = 30,
    percentile_threshold: float = 0.20
) -> Dict[str, any]:
    """
    检测枢轴收缩
    
    Args:
        df: OHLC DataFrame (至少30天数据)
        contraction_days: 连续收缩天数 (默认4)
        lookback: 历史回看天数 (默认30)
        percentile_threshold: 低位阈值 (默认20%)
    
    Returns:
        {
            'is_contracting': bool,
            'contraction_count': int,  # 连续收缩天数
            'is_30d_low': bool,
            'squeeze_score': int,  # 0-3
            'pivots': {'1d': float, '3d': float, '6d': float},
            'ranges': {'1d': float, '3d': float, '6d': float},
        }
    """
    if len(df) < lookback + contraction_days:
        return {
            'is_contracting': False,
            'contraction_count': 0,
            'is_30d_low': False,
            'squeeze_score': 0,
            'pivots': {},
            'ranges': {},
        }
    
    # 计算各周期枢轴
    pivot_1d = calc_pivot_range(df, 1)
    pivot_3d = calc_pivot_range(df, 3)
    pivot_6d = calc_pivot_range(df, 6)
    
    # 计算枢轴范围 (当日最高枢轴 - 最低枢轴)
    # 简化: 用 high-low 作为范围代理
    range_1d = df['high'] - df['low']
    range_3d = range_1d.rolling(3).mean()
    range_6d = range_1d.rolling(6).mean()
    
    # 检测连续收缩
    def count_contraction(series: pd.Series) -> int:
        """计算连续收缩天数"""
        if len(series) < contraction_days + 1:
            return 0
        
        count = 0
        for i in range(1, contraction_days + 1):
            if series.iloc[-i] < series.iloc[-(i+1)]:
                count += 1
            else:
                break
        return count
    
    c1 = count_contraction(range_1d)
    c3 = count_contraction(range_3d)
    c6 = count_contraction(range_6d)
    
    # 是否处于30日低位
    def is_low(series: pd.Series) -> bool:
        if len(series) < lookback:
            return False
        current = series.iloc[-1]
        hist = series.iloc[-lookback:]
        return current <= np.percentile(hist, percentile_threshold * 100)
    
    low_1d = is_low(range_1d)
    low_3d = is_low(range_3d)
    low_6d = is_low(range_6d)
    
    # 综合评分
    squeeze_score = sum([
        c1 >= contraction_days and low_1d,
        c3 >= contraction_days and low_3d,
        c6 >= contraction_days and low_6d,
    ])
    
    is_contracting = squeeze_score >= 1
    
    return {
        'is_contracting': is_contracting,
        'contraction_count': max(c1, c3, c6),
        'is_30d_low': low_1d or low_3d or low_6d,
        'squeeze_score': squeeze_score,
        'pivots': {
            '1d': pivot_1d.iloc[-1] if len(pivot_1d) > 0 else 0,
            '3d': pivot_3d.iloc[-1] if len(pivot_3d) > 0 else 0,
            '6d': pivot_6d.iloc[-1] if len(pivot_6d) > 0 else 0,
        },
        'ranges': {
            '1d': range_1d.iloc[-1] if len(range_1d) > 0 else 0,
            '3d': range_3d.iloc[-1] if len(range_3d) > 0 else 0,
            '6d': range_6d.iloc[-1] if len(range_6d) > 0 else 0,
        },
        'details': {
            '1d': {'contracting': c1 >= contraction_days, 'low': low_1d},
            '3d': {'contracting': c3 >= contraction_days, 'low': low_3d},
            '6d': {'contracting': c6 >= contraction_days, 'low': low_6d},
        }
    }


def detect_breakout(
    df: pd.DataFrame,
    contraction: Dict,
    lookback: int = 30,
) -> Dict:
    """
    突破确认：检测价格是否突破收缩区间

    逻辑：
    1. 计算收缩期间的阻力位（最高高点）和支撑位（最低低点）
    2. 当前收盘价突破阻力 → 向上突破
    3. 当前收盘价跌破支撑 → 向下突破
    4. 突破必须伴随成交量放大（如果有volume列）

    Returns:
        {
            'breakout': 'up' / 'down' / 'none',
            'resistance': float,
            'support': float,
            'close': float,
            'breakout_pct': float,  # 突破幅度百分比
        }
    """
    if len(df) < lookback or not contraction.get('is_contracting'):
        return {'breakout': 'none', 'resistance': 0, 'support': 0,
                'close': 0, 'breakout_pct': 0}

    # 收缩期间的高低点
    recent = df.iloc[-lookback:]
    resistance = recent['high'].max()
    support = recent['low'].min()
    current_close = df['close'].iloc[-1]

    # 突破幅度
    range_size = resistance - support
    if range_size <= 0:
        return {'breakout': 'none', 'resistance': resistance, 'support': support,
                'close': current_close, 'breakout_pct': 0}

    # 向上突破：收盘价 > 阻力位
    if current_close > resistance:
        pct = (current_close - resistance) / range_size * 100
        return {'breakout': 'up', 'resistance': resistance, 'support': support,
                'close': current_close, 'breakout_pct': pct}

    # 向下突破：收盘价 < 支撑位
    if current_close < support:
        pct = (support - current_close) / range_size * 100
        return {'breakout': 'down', 'resistance': resistance, 'support': support,
                'close': current_close, 'breakout_pct': pct}

    return {'breakout': 'none', 'resistance': resistance, 'support': support,
            'close': current_close, 'breakout_pct': 0}


def pivot_to_signal(contraction: Dict, fundamental_signal: str = "HOLD",
                    breakout: Dict = None) -> Tuple[str, float, str]:
    """
    将枢轴收缩 + 突破确认转换为交易信号

    三阶段逻辑：
    1. 无收缩 → HOLD
    2. 有收缩 + 无突破 → 观望（等待方向）
    3. 有收缩 + 有突破 → 确认信号

    Returns:
        (signal, confidence, reason)
    """
    squeeze = contraction['squeeze_score']
    is_contracting = contraction['is_contracting']
    breakout_dir = breakout.get('breakout', 'none') if breakout else 'none'
    breakout_pct = breakout.get('breakout_pct', 0) if breakout else 0

    if not is_contracting:
        return "HOLD", 0.50, "无枢轴收缩"

    # 收缩强度
    if squeeze >= 3:
        strength = "强"
        base_conf = 0.75
    elif squeeze == 2:
        strength = "中"
        base_conf = 0.65
    else:
        strength = "弱"
        base_conf = 0.55

    # 阶段2：有收缩 + 无突破 → 等待
    if breakout_dir == 'none':
        if squeeze >= 2 and fundamental_signal in ("BUY", "SELL"):
            return "准备", base_conf, f"{strength}收缩 + 基本面{fundamental_signal} + 等待突破"
        return "观望", base_conf, f"{strength}收缩(大波动即将到来，方向待确认)"

    # 阶段3：有收缩 + 有突破 → 确认
    # 突破置信度加成
    breakout_bonus = min(0.15, breakout_pct * 0.01)  # 突破越远越确认

    if breakout_dir == 'up':
        if fundamental_signal in ("BUY", "HOLD"):
            return "强BUY", min(0.95, base_conf + 0.15 + breakout_bonus), \
                   f"{strength}收缩 + 向上突破{breakout_pct:.1f}% + 基本面{fundamental_signal}"
        else:
            # 基本面差但向上突破 → 观望
            return "观望", base_conf, \
                   f"向上突破但基本面{fundamental_signal}，不追涨"

    elif breakout_dir == 'down':
        if fundamental_signal in ("SELL", "REDUCE"):
            return "强SELL", min(0.95, base_conf + 0.15 + breakout_bonus), \
                   f"{strength}收缩 + 向下突破{breakout_pct:.1f}% + 基本面{fundamental_signal}"
        else:
            return "观望", base_conf, \
                   f"向下突破但基本面{fundamental_signal}，不追空"

    return "观望", base_conf, "信号不明确"


if __name__ == "__main__":
    # 测试
    np.random.seed(42)
    
    # 生成模拟数据: 前20天波动大，后10天波动收缩
    n = 40
    trend = np.cumsum(np.random.randn(n) * 0.5)
    
    # 波动率: 前20天高，后20天低
    vol = np.concatenate([
        np.ones(20) * 2.0,
        np.linspace(2.0, 0.3, 10),  # 收缩
        np.ones(10) * 0.3
    ])
    
    close = 100 + trend
    high = close + np.abs(np.random.randn(n)) * vol
    low = close - np.abs(np.random.randn(n)) * vol
    
    df = pd.DataFrame({
        'high': high,
        'low': low,
        'close': close,
    })
    
    result = detect_contraction(df)
    
    print("=== ACD 枢轴收缩检测 ===")
    print(f"收缩中: {result['is_contracting']}")
    print(f"连续收缩天数: {result['contraction_count']}")
    print(f"30日低位: {result['is_30d_low']}")
    print(f"Squeeze Score: {result['squeeze_score']}/3")
    print(f"\n枢轴点:")
    for k, v in result['pivots'].items():
        print(f"  {k}: {v:.2f}")
    print(f"\n范围:")
    for k, v in result['ranges'].items():
        print(f"  {k}: {v:.2f}")
    
    sig, conf, reason = pivot_to_signal(result, "BUY")
    print(f"\n信号: {sig} (置信度{conf:.0%})")
    print(f"原因: {reason}")
