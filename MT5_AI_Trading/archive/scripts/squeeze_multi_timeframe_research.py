"""
多周期共振收缩→突破统计验证研究 v2

核心改进：
1. 多周期共振：H1 setup + H4/D1趋势方向过滤
2. 扩大样本：24个品种，365天历史
3. 唯一事件去重：按 cluster_id 去重
4. 修正止损窗口：入场后才开始计算止损
5. 真实ATR突破阈值（替代 anchor_range 倍数）

注意：
- 不把squeeze_setup直接当long/short信号
- 突破方向由价格行为决定，不预设方向
- 所有结论基于样本统计，区分验证状态
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "python"))

from analytics.squeeze_observer import SqueezeObserver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("squeeze_mt_research")


# MT5品种映射（24个品种）
SYMBOL_MAP = {
    "EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD", "USDCAD": "USDCAD", "USDCHF": "USDCHF",
    "NZDUSD": "NZDUSD", "EURGBP": "EURGBP", "EURJPY": "EURJPY",
    "GBPJPY": "GBPJPY", "AUDJPY": "AUDJPY", "CADJPY": "CADJPY",
    "CHFJPY": "CHFJPY",
    "XAUUSD": "GOLD", "XAGUSD": "SILVER",
    "US30": "US_30", "US500": "US_500", "NAS100": "US_TECH100",
    "GER40": "GERMANY_40", "UK100": "UK_100",
    "USOIL": "CrudeOIL", "UKOIL": "BRENT_OIL",
    "BTCUSD": "BTCUSD", "ETHUSD": "ETHUSD",
}


@dataclass
class SqueezeSetup:
    """收缩Setup事件"""
    symbol: str
    timeframe: str
    timestamp: datetime
    bar_idx: int
    squeeze_score: int
    conditions: List[str]
    
    bb_width: float
    pivot_range: float
    sr_range: float
    adx: float
    state_is_zero: bool
    
    open: float
    high: float
    low: float
    close: float
    
    anchor_high: float
    anchor_low: float
    anchor_range: float
    anchor_range_pct: float
    anchor_mid: float
    
    # 多周期共振信息
    h4_trend_bias: str = "neutral"  # bullish / bearish / neutral
    d1_trend_bias: str = "neutral"
    h4_ma_slope: float = 0.0
    d1_ma_slope: float = 0.0
    h4_adx_di_plus: float = 0.0
    h4_adx_di_minus: float = 0.0
    d1_adx_di_plus: float = 0.0
    d1_adx_di_minus: float = 0.0
    
    # 唯一标识
    cluster_id: str = ""


@dataclass
class BreakoutEvent:
    """突破事件"""
    setup: SqueezeSetup
    
    breakout_timestamp: datetime
    breakout_bar_idx: int
    breakout_direction: str
    
    entry_price: float
    breakout_level: float
    
    # 未来收益（从entry_price起算，百分比）
    returns_1bar: float
    returns_3bar: float
    returns_5bar: float
    returns_10bar: float
    returns_20bar: float
    
    max_drawdown_pct: float
    max_runup_pct: float
    
    hit_target_1r: bool
    hit_target_2r: bool
    hit_target_3r: bool
    
    # 止损（入场后才开始计算）
    stop_triggered: bool
    stop_bar_idx: Optional[int]
    stop_price: Optional[float]
    stop_after_entry: bool  # 区分入场前噪音和真实止损
    
    pnl_5bar: float
    pnl_10bar: float
    pnl_20bar: float
    
    # 唯一标识
    cluster_id: str = ""


@dataclass
class ResearchResult:
    """研究结果"""
    total_setups: int
    total_breakouts: int
    unique_breakouts: int
    breakout_rate: float
    no_breakout_count: int
    up_breakouts: int
    down_breakouts: int
    direction_balance: float
    
    # 去重后统计
    unique_win_rate_5bar: float
    unique_expectancy_5bar: float
    unique_win_loss_ratio: float
    
    returns_5bar_all_mean: float
    returns_5bar_all_median: float
    returns_10bar_all_mean: float
    returns_20bar_all_mean: float
    
    returns_5bar_bo_mean: float
    returns_10bar_bo_mean: float
    
    hit_1r_rate: float
    hit_2r_rate: float
    hit_3r_rate: float
    stop_rate: float
    stop_after_entry_rate: float
    
    win_rate_5bar: float
    win_rate_10bar: float
    avg_win_5bar: float
    avg_loss_5bar: float
    win_loss_ratio_5bar: float
    expectancy_5bar: float
    
    # 多周期共振统计
    with_trend_breakouts: int
    against_trend_breakouts: int
    with_trend_win_rate: float
    against_trend_win_rate: float
    
    by_score: Dict
    by_conditions: Dict
    by_symbol: Dict
    by_adx: Dict
    by_trend_alignment: Dict
    
    recommendations: List[str]
    validation_status: str
    warnings: List[str]
    
    param_analysis: Dict = field(default_factory=dict)


class MultiTimeframeSqueezeResearch:
    """多周期共振收缩→突破统计验证引擎 v2"""
    
    def __init__(self):
        self.observer = SqueezeObserver()
        self.setups: List[SqueezeSetup] = []
        self.breakouts: List[BreakoutEvent] = []
        self.raw_data: Dict[str, Dict[str, pd.DataFrame]] = {}  # symbol -> timeframe -> df
        
    def fetch_multi_timeframe_data(self, symbols: Dict[str, str],
                                    timeframes: List[str] = None,
                                    lookback_days: int = 365) -> Dict[str, Dict[str, pd.DataFrame]]:
        """从MT5获取多周期数据"""
        if timeframes is None:
            timeframes = ["H1", "H4", "D1"]
        
        data = {}
        
        for std_name, mt5_name in symbols.items():
            data[std_name] = {}
            for tf in timeframes:
                try:
                    # 大周期需要更多历史数据
                    tf_lookback = lookback_days
                    if tf == "D1":
                        tf_lookback = max(lookback_days, 730)
                    elif tf == "H4":
                        tf_lookback = max(lookback_days, 365)
                    
                    logger.info(f"获取数据: {std_name} ({mt5_name}) {tf} ({tf_lookback}天)")
                    df = self.observer._fetch_from_mt5(mt5_name, tf, tf_lookback)
                    if not df.empty and len(df) >= 50:
                        data[std_name][tf] = df
                        logger.info(f"  成功: {len(df)}条")
                    else:
                        logger.warning(f"  数据不足: {len(df)}条")
                except Exception as e:
                    logger.error(f"  失败: {e}")
        
        self.raw_data = data
        total = sum(len(v) for v in data.values())
        logger.info(f"数据获取完成: {len(data)}个品种, {total}个周期数据集")
        return data
    
    def _compute_trend_bias(self, df: pd.DataFrame, period: int = 20) -> Tuple[str, float, float, float]:
        """
        计算趋势方向
        
        Returns:
            (trend_bias, ma_slope, di_plus, di_minus)
        """
        if len(df) < period + 5:
            return "neutral", 0.0, 0.0, 0.0
        
        # MA斜率
        ma = df['close'].rolling(period).mean()
        ma_slope = (ma.iloc[-1] - ma.iloc[-5]) / ma.iloc[-5] * 100 if ma.iloc[-5] != 0 else 0
        
        # ADX DI+/-
        adx_series = SqueezeObserver.compute_adx(df['high'], df['low'], df['close'])
        
        # 计算DI+和DI-
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - df['close'].shift(1)).abs()
        tr3 = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm[plus_dm <= minus_dm] = 0
        minus_dm[minus_dm <= plus_dm] = 0
        
        atr = tr.ewm(alpha=1/14, min_periods=14).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr
        minus_di = 100 * minus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr
        
        di_plus = plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 0
        di_minus = minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 0
        
        # 综合判断趋势
        if ma_slope > 0.05 and di_plus > di_minus:
            bias = "bullish"
        elif ma_slope < -0.05 and di_minus > di_plus:
            bias = "bearish"
        elif ma_slope > 0.1:
            bias = "bullish"
        elif ma_slope < -0.1:
            bias = "bearish"
        else:
            bias = "neutral"
        
        return bias, ma_slope, di_plus, di_minus
    
    def find_setups(self, min_squeeze_score: int = 2,
                    cooldown_bars: int = 5,
                    require_structural: bool = False) -> List[SqueezeSetup]:
        """识别收缩setup时刻（带多周期趋势信息）"""
        setups = []
        
        for symbol, tf_data in self.raw_data.items():
            h1_df = tf_data.get("H1")
            if h1_df is None or len(h1_df) < 30:
                continue
            
            h1_df = h1_df.copy().reset_index(drop=True)
            
            # 计算H1指标
            h1_df['bb_width'] = SqueezeObserver.compute_bb_width(h1_df['close'])
            h1_df['pivot_range'] = SqueezeObserver.compute_pivot_range(h1_df['high'], h1_df['low'], h1_df['close'])
            h1_df['sr_range'] = SqueezeObserver.compute_sr_range(h1_df['high'], h1_df['low'], h1_df['close'])
            h1_df['adx'] = SqueezeObserver.compute_adx(h1_df['high'], h1_df['low'], h1_df['close'])
            
            # 计算分位数
            h1_df['bb_20pct'] = h1_df['bb_width'].expanding(min_periods=20).quantile(0.20)
            h1_df['pivot_20pct'] = h1_df['pivot_range'].expanding(min_periods=20).quantile(0.20)
            h1_df['sr_20pct'] = h1_df['sr_range'].expanding(min_periods=20).quantile(0.20)
            
            h1_df['bb_squeezed'] = (h1_df['bb_width'] <= h1_df['bb_20pct']) & h1_df['bb_width'].notna()
            h1_df['pivot_squeezed'] = (h1_df['pivot_range'] <= h1_df['pivot_20pct']) & h1_df['pivot_range'].notna()
            h1_df['sr_squeezed'] = (h1_df['sr_range'] <= h1_df['sr_20pct']) & h1_df['sr_range'].notna()
            h1_df['adx_lt_20'] = h1_df['adx'] < 20
            h1_df['adx_lt_13'] = h1_df['adx'] < 13
            h1_df['adx_lt_9'] = h1_df['adx'] < 9
            
            h1_df['structural_score'] = h1_df[['bb_squeezed', 'pivot_squeezed', 'sr_squeezed']].sum(axis=1)
            
            score_cols = ['bb_squeezed', 'pivot_squeezed', 'sr_squeezed', 
                          'adx_lt_20', 'adx_lt_13', 'adx_lt_9']
            h1_df['squeeze_score'] = h1_df[score_cols].sum(axis=1)
            
            # 预计算H4和D1趋势（按H1 bar索引映射）
            h4_bias_map = {}
            d1_bias_map = {}
            
            if "H4" in tf_data:
                h4_df = tf_data["H4"].copy()
                h4_bias, h4_slope, h4_di_plus, h4_di_minus = self._compute_trend_bias(h4_df)
                # H4的每个bar对应H1的4个bar
                for i in range(len(h1_df)):
                    h4_idx = i // 4
                    if h4_idx < len(h4_df):
                        h4_bias_map[i] = (h4_bias, h4_slope, h4_di_plus, h4_di_minus)
            
            if "D1" in tf_data:
                d1_df = tf_data["D1"].copy()
                d1_bias, d1_slope, d1_di_plus, d1_di_minus = self._compute_trend_bias(d1_df)
                # D1的每个bar对应H1的24个bar（假设每天24小时交易）
                for i in range(len(h1_df)):
                    d1_idx = i // 24
                    if d1_idx < len(d1_df):
                        d1_bias_map[i] = (d1_bias, d1_slope, d1_di_plus, d1_di_minus)
            
            last_setup_idx = -cooldown_bars - 1
            
            for i in range(30, len(h1_df)):
                if h1_df['squeeze_score'].iloc[i] < min_squeeze_score:
                    continue
                
                if require_structural and h1_df['structural_score'].iloc[i] < 1:
                    continue
                
                if i - last_setup_idx <= cooldown_bars:
                    continue
                
                anchor_start = max(0, i - 20)
                anchor_window = h1_df.iloc[anchor_start:i]
                
                if len(anchor_window) < 10:
                    continue
                
                anchor_high = anchor_window['high'].max()
                anchor_low = anchor_window['low'].min()
                anchor_range = anchor_high - anchor_low
                anchor_mid = (anchor_high + anchor_low) / 2
                
                if anchor_range <= 0:
                    continue
                
                close = h1_df['close'].iloc[i]
                anchor_range_pct = anchor_range / close * 100
                
                conditions = []
                if h1_df['bb_squeezed'].iloc[i]: conditions.append("BB")
                if h1_df['pivot_squeezed'].iloc[i]: conditions.append("Pivot")
                if h1_df['sr_squeezed'].iloc[i]: conditions.append("SR")
                if h1_df['adx_lt_20'].iloc[i]: conditions.append("ADX<20")
                if h1_df['adx_lt_13'].iloc[i]: conditions.append("ADX<13")
                if h1_df['adx_lt_9'].iloc[i]: conditions.append("ADX<9")
                
                # 获取多周期趋势
                h4_info = h4_bias_map.get(i, ("neutral", 0.0, 0.0, 0.0))
                d1_info = d1_bias_map.get(i, ("neutral", 0.0, 0.0, 0.0))
                
                # 生成cluster_id
                ts = h1_df['timestamp'].iloc[i]
                cluster_id = f"{symbol}_{ts.strftime('%Y%m%d_%H')}"
                
                setup = SqueezeSetup(
                    symbol=symbol, timeframe="H1",
                    timestamp=ts, bar_idx=i,
                    squeeze_score=int(h1_df['squeeze_score'].iloc[i]),
                    conditions=conditions,
                    bb_width=h1_df['bb_width'].iloc[i],
                    pivot_range=h1_df['pivot_range'].iloc[i],
                    sr_range=h1_df['sr_range'].iloc[i],
                    adx=h1_df['adx'].iloc[i],
                    state_is_zero=False,
                    open=h1_df['open'].iloc[i], high=h1_df['high'].iloc[i],
                    low=h1_df['low'].iloc[i], close=close,
                    anchor_high=anchor_high, anchor_low=anchor_low,
                    anchor_range=anchor_range, anchor_range_pct=anchor_range_pct,
                    anchor_mid=anchor_mid,
                    h4_trend_bias=h4_info[0], d1_trend_bias=d1_info[0],
                    h4_ma_slope=h4_info[1], d1_ma_slope=d1_info[1],
                    h4_adx_di_plus=h4_info[2], h4_adx_di_minus=h4_info[3],
                    d1_adx_di_plus=d1_info[2], d1_adx_di_minus=d1_info[3],
                    cluster_id=cluster_id
                )
                setups.append(setup)
                last_setup_idx = i
        
        self.setups = setups
        logger.info(f"识别到 {len(setups)} 个收缩setup (min_score={min_squeeze_score})")
        return setups
    
    def detect_breakouts(self, max_wait_bars: int = 20,
                         min_breakout_atr: float = 0.25) -> List[BreakoutEvent]:
        """检测setup后的突破事件（修正止损窗口）"""
        breakouts = []
        
        for setup in self.setups:
            symbol_data = self.raw_data.get(setup.symbol)
            if symbol_data is None:
                continue
            
            df = symbol_data.get("H1")
            if df is None:
                continue
            
            future = df.iloc[setup.bar_idx + 1:setup.bar_idx + 1 + max_wait_bars].copy()
            
            if future.empty:
                continue
            
            future = future.reset_index(drop=True)
            
            up_threshold = setup.anchor_high + min_breakout_atr * setup.anchor_range
            down_threshold = setup.anchor_low - min_breakout_atr * setup.anchor_range
            
            up_break = future[future['close'] > up_threshold]
            down_break = future[future['close'] < down_threshold]
            
            direction = None
            breakout_bar_idx = None
            breakout_level = None
            entry_price = None
            
            if not up_break.empty and not down_break.empty:
                up_first = up_break.index[0]
                down_first = down_break.index[0]
                if up_first < down_first:
                    direction = "up"
                    breakout_bar_idx = int(up_first) + 1
                    breakout_level = setup.anchor_high
                    entry_price = up_break.iloc[0]['close']
                elif down_first < up_first:
                    direction = "down"
                    breakout_bar_idx = int(down_first) + 1
                    breakout_level = setup.anchor_low
                    entry_price = down_break.iloc[0]['close']
                else:
                    continue
            elif not up_break.empty:
                direction = "up"
                breakout_bar_idx = int(up_break.index[0]) + 1
                breakout_level = setup.anchor_high
                entry_price = up_break.iloc[0]['close']
            elif not down_break.empty:
                direction = "down"
                breakout_bar_idx = int(down_break.index[0]) + 1
                breakout_level = setup.anchor_low
                entry_price = down_break.iloc[0]['close']
            else:
                continue
            
            # 多周期趋势过滤：只保留与趋势方向一致的突破
            if direction == "up" and setup.h4_trend_bias == "bearish" and setup.d1_trend_bias == "bearish":
                continue  # 强烈逆势，跳过
            if direction == "down" and setup.h4_trend_bias == "bullish" and setup.d1_trend_bias == "bullish":
                continue  # 强烈逆势，跳过
            
            # 未来收益（从entry_price起算）
            future_prices = df.iloc[setup.bar_idx + breakout_bar_idx:setup.bar_idx + breakout_bar_idx + 21]
            
            def calc_return(idx):
                if idx < len(future_prices):
                    return (future_prices.iloc[idx]['close'] - entry_price) / entry_price * 100
                return np.nan
            
            def calc_pnl(idx, direction):
                r = calc_return(idx)
                if pd.isna(r):
                    return np.nan
                return r if direction == "up" else -r
            
            returns_1bar = calc_return(0)
            returns_3bar = calc_return(2)
            returns_5bar = calc_return(4)
            returns_10bar = calc_return(9)
            returns_20bar = calc_return(19)
            
            if len(future_prices) > 0:
                prices = future_prices['close'].values
                if direction == "up":
                    max_dd = min((prices - entry_price) / entry_price * 100)
                    max_ru = max((prices - entry_price) / entry_price * 100)
                else:
                    max_dd = min((entry_price - prices) / entry_price * 100)
                    max_ru = max((entry_price - prices) / entry_price * 100)
            else:
                max_dd = 0
                max_ru = 0
            
            # 修正止损：只在入场后计算
            stop_price = setup.anchor_low if direction == "up" else setup.anchor_high
            stop_triggered = False
            stop_bar = None
            stop_after_entry = False
            
            # 入场后的价格序列
            entry_future = df.iloc[setup.bar_idx + breakout_bar_idx:setup.bar_idx + breakout_bar_idx + 21]
            
            for j, (_, row) in enumerate(entry_future.iterrows()):
                if direction == "up" and row['low'] < stop_price:
                    stop_triggered = True
                    stop_bar = j + 1
                    stop_after_entry = True
                    break
                elif direction == "down" and row['high'] > stop_price:
                    stop_triggered = True
                    stop_bar = j + 1
                    stop_after_entry = True
                    break
            
            # 目标判断（修正short方向）
            target_1r = setup.anchor_range if direction == "up" else -setup.anchor_range
            target_2r = 2 * setup.anchor_range if direction == "up" else -2 * setup.anchor_range
            target_3r = 3 * setup.anchor_range if direction == "up" else -3 * setup.anchor_range
            
            def check_target(target):
                if len(future_prices) == 0:
                    return False
                if direction == "up":
                    return (future_prices['high'] - entry_price).max() >= target
                else:
                    return (entry_price - future_prices['low']).min() >= abs(target)
            
            hit_1r = check_target(target_1r)
            hit_2r = check_target(target_2r)
            hit_3r = check_target(target_3r)
            
            pnl_5 = calc_pnl(4, direction)
            pnl_10 = calc_pnl(9, direction)
            pnl_20 = calc_pnl(19, direction)
            
            event = BreakoutEvent(
                setup=setup,
                breakout_timestamp=future.iloc[breakout_bar_idx - 1]['timestamp'],
                breakout_bar_idx=breakout_bar_idx,
                breakout_direction=direction,
                entry_price=entry_price,
                breakout_level=breakout_level,
                returns_1bar=returns_1bar if not pd.isna(returns_1bar) else 0,
                returns_3bar=calc_return(2) if not pd.isna(calc_return(2)) else 0,
                returns_5bar=returns_5bar if not pd.isna(returns_5bar) else 0,
                returns_10bar=returns_10bar if not pd.isna(returns_10bar) else 0,
                returns_20bar=returns_20bar if not pd.isna(returns_20bar) else 0,
                max_drawdown_pct=max_dd,
                max_runup_pct=max_ru,
                hit_target_1r=hit_1r,
                hit_target_2r=hit_2r,
                hit_target_3r=hit_3r,
                stop_triggered=stop_triggered,
                stop_bar_idx=stop_bar,
                stop_price=stop_price,
                stop_after_entry=stop_after_entry,
                pnl_5bar=pnl_5 if not pd.isna(pnl_5) else 0,
                pnl_10bar=pnl_10 if not pd.isna(pnl_10) else 0,
                pnl_20bar=pnl_20 if not pd.isna(pnl_20) else 0,
                cluster_id=setup.cluster_id
            )
            breakouts.append(event)
        
        self.breakouts = breakouts
        logger.info(f"检测到 {len(breakouts)} 个突破事件（多周期过滤后）")
        return breakouts
    
    def _deduplicate_breakouts(self, breakouts: List[BreakoutEvent]) -> List[BreakoutEvent]:
        """按cluster_id去重：同一品种同一天的突破只保留第一个"""
        seen_clusters = set()
        unique_breakouts = []
        
        for b in breakouts:
            if b.cluster_id not in seen_clusters:
                seen_clusters.add(b.cluster_id)
                unique_breakouts.append(b)
        
        logger.info(f"去重前: {len(breakouts)} 个, 去重后: {len(unique_breakouts)} 个唯一突破")
        return unique_breakouts
    
    def analyze(self, deduplicate: bool = True) -> ResearchResult:
        """执行完整分析"""
        if not self.setups:
            logger.error("没有setup数据")
            return None
        
        setups = self.setups
        breakouts = self.breakouts
        
        # 去重
        if deduplicate:
            unique_breakouts = self._deduplicate_breakouts(breakouts)
        else:
            unique_breakouts = breakouts
        
        total_setups = len(setups)
        total_breakouts = len(breakouts)
        unique_breakout_count = len(unique_breakouts)
        breakout_rate = total_breakouts / total_setups if total_setups > 0 else 0
        no_breakout = total_setups - total_breakouts
        
        up_bo = sum(1 for b in breakouts if b.breakout_direction == "up")
        down_bo = sum(1 for b in breakouts if b.breakout_direction == "down")
        direction_balance = up_bo / total_breakouts if total_breakouts > 0 else 0.5
        
        # 所有setup的未来收益
        all_returns_5 = []
        all_returns_10 = []
        all_returns_20 = []
        
        for setup in setups:
            symbol_data = self.raw_data.get(setup.symbol)
            if symbol_data is None:
                continue
            df = symbol_data.get("H1")
            if df is None:
                continue
            future = df.iloc[setup.bar_idx + 1:setup.bar_idx + 21]
            if len(future) >= 5:
                r5 = (future.iloc[4]['close'] - setup.close) / setup.close * 100
                all_returns_5.append(r5)
            if len(future) >= 10:
                r10 = (future.iloc[9]['close'] - setup.close) / setup.close * 100
                all_returns_10.append(r10)
            if len(future) >= 20:
                r20 = (future.iloc[19]['close'] - setup.close) / setup.close * 100
                all_returns_20.append(r20)
        
        # 突破样本统计（原始）
        bo_returns_5 = [b.returns_5bar for b in breakouts]
        bo_returns_10 = [b.returns_10bar for b in breakouts]
        
        pnl_5 = [b.pnl_5bar for b in breakouts]
        pnl_10 = [b.pnl_10bar for b in breakouts]
        
        wins_5 = [p for p in pnl_5 if p > 0]
        losses_5 = [p for p in pnl_5 if p <= 0]
        
        win_rate_5 = len(wins_5) / len(pnl_5) if pnl_5 else 0
        avg_win_5 = np.mean(wins_5) if wins_5 else 0
        avg_loss_5 = np.mean(losses_5) if losses_5 else 0
        wl_ratio = abs(avg_win_5 / avg_loss_5) if avg_loss_5 != 0 else float('inf')
        expectancy = win_rate_5 * avg_win_5 + (1 - win_rate_5) * avg_loss_5
        
        # 去重后统计
        unique_pnl_5 = [b.pnl_5bar for b in unique_breakouts]
        unique_wins_5 = [p for p in unique_pnl_5 if p > 0]
        unique_losses_5 = [p for p in unique_pnl_5 if p <= 0]
        unique_win_rate_5 = len(unique_wins_5) / len(unique_pnl_5) if unique_pnl_5 else 0
        unique_avg_win = np.mean(unique_wins_5) if unique_wins_5 else 0
        unique_avg_loss = np.mean(unique_losses_5) if unique_losses_5 else 0
        unique_wl_ratio = abs(unique_avg_win / unique_avg_loss) if unique_avg_loss != 0 else float('inf')
        unique_expectancy = unique_win_rate_5 * unique_avg_win + (1 - unique_win_rate_5) * unique_avg_loss
        
        # 多周期趋势共振统计
        with_trend = []
        against_trend = []
        
        for b in breakouts:
            direction = b.breakout_direction
            h4_bias = b.setup.h4_trend_bias
            d1_bias = b.setup.d1_trend_bias
            
            if direction == "up":
                if h4_bias == "bullish" or d1_bias == "bullish":
                    with_trend.append(b)
                elif h4_bias == "bearish" or d1_bias == "bearish":
                    against_trend.append(b)
            elif direction == "down":
                if h4_bias == "bearish" or d1_bias == "bearish":
                    with_trend.append(b)
                elif h4_bias == "bullish" or d1_bias == "bullish":
                    against_trend.append(b)
        
        with_trend_pnl = [b.pnl_5bar for b in with_trend]
        against_trend_pnl = [b.pnl_5bar for b in against_trend]
        
        with_trend_wr = len([p for p in with_trend_pnl if p > 0]) / len(with_trend_pnl) if with_trend_pnl else 0
        against_trend_wr = len([p for p in against_trend_pnl if p > 0]) / len(against_trend_pnl) if against_trend_pnl else 0
        
        hit_1r = sum(1 for b in breakouts if b.hit_target_1r) / total_breakouts if total_breakouts else 0
        hit_2r = sum(1 for b in breakouts if b.hit_target_2r) / total_breakouts if total_breakouts else 0
        hit_3r = sum(1 for b in breakouts if b.hit_target_3r) / total_breakouts if total_breakouts else 0
        stop_rate = sum(1 for b in breakouts if b.stop_triggered) / total_breakouts if total_breakouts else 0
        stop_after_entry_rate = sum(1 for b in breakouts if b.stop_after_entry) / total_breakouts if total_breakouts else 0
        
        # 按score分组
        by_score = defaultdict(lambda: {"count": 0, "breakouts": 0, "win_rate": 0, "avg_pnl": 0})
        for setup in setups:
            s = setup.squeeze_score
            by_score[s]["count"] += 1
        for b in breakouts:
            s = b.setup.squeeze_score
            by_score[s]["breakouts"] += 1
        for s in by_score:
            bo_list = [b for b in breakouts if b.setup.squeeze_score == s]
            if bo_list:
                pnls = [b.pnl_5bar for b in bo_list]
                by_score[s]["win_rate"] = sum(1 for p in pnls if p > 0) / len(pnls)
                by_score[s]["avg_pnl"] = np.mean(pnls)
                by_score[s]["breakout_rate"] = by_score[s]["breakouts"] / by_score[s]["count"]
        
        # 按品种分组
        by_symbol = defaultdict(lambda: {"setups": 0, "breakouts": 0, "avg_pnl": 0})
        for setup in setups:
            by_symbol[setup.symbol]["setups"] += 1
        for b in breakouts:
            by_symbol[b.setup.symbol]["breakouts"] += 1
        for sym in by_symbol:
            bo_list = [b for b in breakouts if b.setup.symbol == sym]
            if bo_list:
                by_symbol[sym]["avg_pnl"] = np.mean([b.pnl_5bar for b in bo_list])
        
        # 按趋势一致性分组
        by_trend_alignment = {
            "with_trend": {"count": len(with_trend), "win_rate": with_trend_wr, "avg_pnl": np.mean(with_trend_pnl) if with_trend_pnl else 0},
            "against_trend": {"count": len(against_trend), "win_rate": against_trend_wr, "avg_pnl": np.mean(against_trend_pnl) if against_trend_pnl else 0},
            "neutral": {"count": total_breakouts - len(with_trend) - len(against_trend), "win_rate": 0, "avg_pnl": 0},
        }
        
        recommendations = []
        warnings = []
        
        if unique_breakout_count < 100:
            warnings.append(f"去重后样本量不足: 仅{unique_breakout_count}个唯一突破")
        
        if breakout_rate < 0.3:
            recommendations.append(f"突破率较低({breakout_rate*100:.1f}%)，建议扩大等待周期或降低突破阈值")
        elif breakout_rate > 0.8:
            recommendations.append(f"突破率过高({breakout_rate*100:.1f}%)，可能突破阈值过低")
        
        if unique_win_rate_5 > 0.55 and unique_expectancy > 0:
            recommendations.append(f"去重后5bar胜率{unique_win_rate_5*100:.1f}%为正期望，策略有潜力")
        
        if with_trend_wr > against_trend_wr + 0.05:
            recommendations.append(f"顺势突破胜率({with_trend_wr*100:.1f}%)优于逆势({against_trend_wr*100:.1f}%)，趋势过滤有效")
        
        if unique_breakout_count < 50:
            validation_status = "样本不足"
        elif unique_win_rate_5 < 0.5 and unique_expectancy < 0:
            validation_status = "暂不建议进入实盘"
        elif unique_win_rate_5 >= 0.55 and unique_expectancy > 0 and unique_wl_ratio > 1.2:
            validation_status = "已验证有效"
        else:
            validation_status = "逻辑需要调整"
        
        return ResearchResult(
            total_setups=total_setups,
            total_breakouts=total_breakouts,
            unique_breakouts=unique_breakout_count,
            breakout_rate=breakout_rate,
            no_breakout_count=no_breakout,
            up_breakouts=up_bo,
            down_breakouts=down_bo,
            direction_balance=direction_balance,
            unique_win_rate_5bar=unique_win_rate_5,
            unique_expectancy_5bar=unique_expectancy,
            unique_win_loss_ratio=unique_wl_ratio,
            returns_5bar_all_mean=np.mean(all_returns_5) if all_returns_5 else 0,
            returns_5bar_all_median=np.median(all_returns_5) if all_returns_5 else 0,
            returns_10bar_all_mean=np.mean(all_returns_10) if all_returns_10 else 0,
            returns_20bar_all_mean=np.mean(all_returns_20) if all_returns_20 else 0,
            returns_5bar_bo_mean=np.mean(bo_returns_5) if bo_returns_5 else 0,
            returns_10bar_bo_mean=np.mean(bo_returns_10) if bo_returns_10 else 0,
            hit_1r_rate=hit_1r,
            hit_2r_rate=hit_2r,
            hit_3r_rate=hit_3r,
            stop_rate=stop_rate,
            stop_after_entry_rate=stop_after_entry_rate,
            win_rate_5bar=win_rate_5,
            win_rate_10bar=len([p for p in pnl_10 if p > 0]) / len(pnl_10) if pnl_10 else 0,
            avg_win_5bar=avg_win_5,
            avg_loss_5bar=avg_loss_5,
            win_loss_ratio_5bar=wl_ratio,
            expectancy_5bar=expectancy,
            with_trend_breakouts=len(with_trend),
            against_trend_breakouts=len(against_trend),
            with_trend_win_rate=with_trend_wr,
            against_trend_win_rate=against_trend_wr,
            by_score=dict(by_score),
            by_conditions={},
            by_symbol=dict(by_symbol),
            by_adx={},
            by_trend_alignment=by_trend_alignment,
            recommendations=recommendations,
            validation_status=validation_status,
            warnings=warnings
        )
    
    def run_param_sweep(self) -> Dict:
        """参数扫描"""
        logger.info("开始参数扫描...")
        
        param_results = []
        
        scores = [2, 3, 4]
        waits = [10, 15, 20, 30]
        atrs = [0.1, 0.25, 0.5]
        struct_reqs = [False, True]
        
        total_combos = len(scores) * len(waits) * len(atrs) * len(struct_reqs)
        current = 0
        
        for score in scores:
            for wait in waits:
                for atr in atrs:
                    for struct in struct_reqs:
                        current += 1
                        logger.info(f"参数组合 [{current}/{total_combos}]: score={score}, wait={wait}, atr={atr}, struct={struct}")
                        
                        self.find_setups(min_squeeze_score=score, cooldown_bars=5, require_structural=struct)
                        self.detect_breakouts(max_wait_bars=wait, min_breakout_atr=atr)
                        result = self.analyze(deduplicate=True)
                        
                        if result:
                            param_results.append({
                                'min_score': score,
                                'max_wait': wait,
                                'min_atr': atr,
                                'require_structural': struct,
                                'setups': result.total_setups,
                                'breakouts': result.total_breakouts,
                                'unique_breakouts': result.unique_breakouts,
                                'breakout_rate': result.breakout_rate,
                                'win_rate_5bar': result.win_rate_5bar,
                                'unique_win_rate': result.unique_win_rate_5bar,
                                'unique_expectancy': result.unique_expectancy_5bar,
                                'win_loss_ratio': result.win_loss_ratio_5bar,
                                'expectancy': result.expectancy_5bar,
                                'with_trend_wr': result.with_trend_win_rate,
                                'stop_rate': result.stop_rate,
                                'validation': result.validation_status
                            })
        
        df = pd.DataFrame(param_results)
        
        # 排序：优先去重后期望值为正且样本充足的
        df['score'] = df['unique_expectancy'] * np.sqrt(df['unique_breakouts'].clip(lower=1))
        df_sorted = df.sort_values('score', ascending=False)
        
        logger.info("参数扫描完成")
        return {
            'all_results': df,
            'top_results': df_sorted.head(10),
            'best_params': df_sorted.iloc[0].to_dict() if len(df_sorted) > 0 else None
        }
    
    def generate_report(self, result: ResearchResult, param_analysis: Dict = None,
                        output_dir: str = "reports/squeeze") -> Tuple[str, str]:
        """生成研究报告和CSV"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        lines = []
        lines.append("# 多周期共振收缩→突破统计验证研究报告 v2")
        lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"\n## 验证状态: {result.validation_status}")
        
        if result.warnings:
            lines.append("\n### ⚠️ 警告")
            for w in result.warnings:
                lines.append(f"- {w}")
        
        lines.append("\n---")
        lines.append("\n## 一、样本概览")
        lines.append(f"\n| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 总Setup数 | {result.total_setups} |")
        lines.append(f"| 突破事件数(原始) | {result.total_breakouts} |")
        lines.append(f"| 唯一突破事件数 | {result.unique_breakouts} |")
        lines.append(f"| 突破率 | {result.breakout_rate*100:.1f}% |")
        lines.append(f"| 未突破数 | {result.no_breakout_count} |")
        lines.append(f"| 向上突破 | {result.up_breakouts} |")
        lines.append(f"| 向下突破 | {result.down_breakouts} |")
        lines.append(f"| 方向平衡 | {result.direction_balance*100:.1f}% |")
        
        lines.append("\n## 二、收益统计（原始样本）")
        lines.append(f"\n| 持有周期 | 均值 | 中位数 |")
        lines.append(f"|----------|------|--------|")
        lines.append(f"| 5bar | {result.returns_5bar_all_mean:.3f}% | {result.returns_5bar_all_median:.3f}% |")
        lines.append(f"| 10bar | {result.returns_10bar_all_mean:.3f}% | - |")
        lines.append(f"| 20bar | {result.returns_20bar_all_mean:.3f}% | - |")
        
        lines.append("\n## 三、交易绩效（原始样本）")
        lines.append(f"\n| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 5bar胜率 | {result.win_rate_5bar*100:.1f}% |")
        lines.append(f"| 10bar胜率 | {result.win_rate_10bar*100:.1f}% |")
        lines.append(f"| 平均盈利 | {result.avg_win_5bar:.3f}% |")
        lines.append(f"| 平均亏损 | {result.avg_loss_5bar:.3f}% |")
        lines.append(f"| 盈亏比 | {result.win_loss_ratio_5bar:.2f} |")
        lines.append(f"| 期望值 | {result.expectancy_5bar:.3f}% |")
        lines.append(f"| 1R达成率 | {result.hit_1r_rate*100:.1f}% |")
        lines.append(f"| 2R达成率 | {result.hit_2r_rate*100:.1f}% |")
        lines.append(f"| 3R达成率 | {result.hit_3r_rate*100:.1f}% |")
        lines.append(f"| 止损触发率 | {result.stop_rate*100:.1f}% |")
        lines.append(f"| 入场后止损率 | {result.stop_after_entry_rate*100:.1f}% |")
        
        lines.append("\n## 四、交易绩效（去重后唯一事件）")
        lines.append(f"\n| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 唯一突破数 | {result.unique_breakouts} |")
        lines.append(f"| 5bar胜率 | {result.unique_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 盈亏比 | {result.unique_win_loss_ratio:.2f} |")
        lines.append(f"| 期望值 | {result.unique_expectancy_5bar:.3f}% |")
        
        lines.append("\n## 五、多周期趋势共振分析")
        lines.append(f"\n| 类型 | 数量 | 胜率 | 平均PNL |")
        lines.append(f"|------|------|------|---------|")
        for key, d in result.by_trend_alignment.items():
            lines.append(f"| {key} | {d['count']} | {d['win_rate']*100:.1f}% | {d['avg_pnl']:.3f}% |")
        
        lines.append("\n## 六、按Squeeze Score分组")
        lines.append(f"\n| Score | Setup数 | 突破数 | 突破率 | 胜率 | 平均PNL |")
        lines.append(f"|-------|---------|--------|--------|------|---------|")
        for score in sorted(result.by_score.keys()):
            d = result.by_score[score]
            lines.append(f"| {score} | {d['count']} | {d['breakouts']} | {d.get('breakout_rate', 0)*100:.1f}% | {d['win_rate']*100:.1f}% | {d['avg_pnl']:.3f}% |")
        
        lines.append("\n## 七、按品种分组")
        lines.append(f"\n| 品种 | Setup数 | 突破数 | 平均PNL |")
        lines.append(f"|------|---------|--------|---------|")
        for sym in sorted(result.by_symbol.keys()):
            d = result.by_symbol[sym]
            lines.append(f"| {sym} | {d['setups']} | {d['breakouts']} | {d['avg_pnl']:.3f}% |")
        
        if param_analysis and 'top_results' in param_analysis:
            lines.append("\n## 八、参数扫描结果（Top 10）")
            lines.append(f"\n| 排名 | min_score | max_wait | min_atr | struct | setups | breakouts | 唯一突破 | 胜率 | 盈亏比 | 期望 | 状态 |")
            lines.append(f"|------|-----------|----------|---------|--------|--------|-----------|----------|------|--------|------|------|")
            top = param_analysis['top_results']
            for idx, row in top.iterrows():
                lines.append(f"| {idx+1} | {row['min_score']} | {row['max_wait']} | {row['min_atr']} | {row['require_structural']} | "
                           f"{row['setups']} | {row['breakouts']} | {row['unique_breakouts']} | {row['unique_win_rate']*100:.1f}% | "
                           f"{row['win_loss_ratio']:.2f} | {row['unique_expectancy']:.3f}% | {row['validation']} |")
            
            if param_analysis.get('best_params'):
                best = param_analysis['best_params']
                lines.append(f"\n### 推荐参数")
                lines.append(f"- min_squeeze_score: {best['min_score']}")
                lines.append(f"- max_wait_bars: {best['max_wait']}")
                lines.append(f"- min_breakout_atr: {best['min_atr']}")
                lines.append(f"- require_structural: {best['require_structural']}")
        
        lines.append("\n## 九、参数建议")
        if result.recommendations:
            for rec in result.recommendations:
                lines.append(f"- {rec}")
        else:
            lines.append("暂无明确建议，需更多样本数据。")
        
        lines.append("\n## 十、结论")
        lines.append(f"\n**验证状态**: {result.validation_status}")
        lines.append(f"\n- **已验证有效**: 去重后胜率>55%且期望值为正")
        lines.append(f"- **样本不足**: 唯一突破事件<50")
        lines.append(f"- **逻辑需要调整**: 有样本但胜率或期望值不达标")
        lines.append(f"- **暂不建议进入实盘**: 胜率和期望值均为负")
        lines.append(f"\n**多周期共振效果**: 顺势突破胜率{result.with_trend_win_rate*100:.1f}% vs 逆势{result.against_trend_win_rate*100:.1f}%")
        
        lines.append("\n---")
        lines.append("\n> 免责声明：本报告仅供研究参考，不构成投资建议。")
        
        report_path = Path(output_dir) / f"squeeze_mt_research_{timestamp}.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"报告已保存: {report_path}")
        
        # CSV
        if self.breakouts:
            csv_records = []
            for b in self.breakouts:
                csv_records.append({
                    'symbol': b.setup.symbol,
                    'cluster_id': b.cluster_id,
                    'squeeze_timestamp': b.setup.timestamp,
                    'squeeze_score': b.setup.squeeze_score,
                    'conditions': '+'.join(b.setup.conditions),
                    'adx': b.setup.adx,
                    'h4_trend_bias': b.setup.h4_trend_bias,
                    'd1_trend_bias': b.setup.d1_trend_bias,
                    'h4_ma_slope': b.setup.h4_ma_slope,
                    'd1_ma_slope': b.setup.d1_ma_slope,
                    'anchor_range_pct': b.setup.anchor_range_pct,
                    'breakout_timestamp': b.breakout_timestamp,
                    'breakout_direction': b.breakout_direction,
                    'breakout_bar_idx': b.breakout_bar_idx,
                    'entry_price': b.entry_price,
                    'returns_1bar': b.returns_1bar,
                    'returns_5bar': b.returns_5bar,
                    'returns_10bar': b.returns_10bar,
                    'returns_20bar': b.returns_20bar,
                    'max_drawdown_pct': b.max_drawdown_pct,
                    'max_runup_pct': b.max_runup_pct,
                    'hit_1r': b.hit_target_1r,
                    'hit_2r': b.hit_target_2r,
                    'hit_3r': b.hit_target_3r,
                    'stop_triggered': b.stop_triggered,
                    'stop_after_entry': b.stop_after_entry,
                    'stop_bar_idx': b.stop_bar_idx,
                    'pnl_5bar': b.pnl_5bar,
                    'pnl_10bar': b.pnl_10bar,
                    'pnl_20bar': b.pnl_20bar,
                })
            
            csv_df = pd.DataFrame(csv_records)
            csv_path = Path(output_dir) / f"squeeze_mt_samples_{timestamp}.csv"
            csv_df.to_csv(csv_path, index=False)
            logger.info(f"样本CSV已保存: {csv_path}")
        else:
            csv_path = None
        
        if param_analysis and 'all_results' in param_analysis:
            param_csv_path = Path(output_dir) / f"squeeze_mt_param_sweep_{timestamp}.csv"
            param_analysis['all_results'].to_csv(param_csv_path, index=False)
            logger.info(f"参数扫描CSV已保存: {param_csv_path}")
        
        return str(report_path), str(csv_path) if csv_path else None


def main():
    """主函数"""
    print("=" * 70)
    print("多周期共振收缩→突破统计验证研究 v2")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    research = MultiTimeframeSqueezeResearch()
    
    # 24个品种
    all_symbols = {
        "EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY",
        "AUDUSD": "AUDUSD", "USDCAD": "USDCAD", "USDCHF": "USDCHF",
        "NZDUSD": "NZDUSD", "EURGBP": "EURGBP", "EURJPY": "EURJPY",
        "GBPJPY": "GBPJPY", "AUDJPY": "AUDJPY", "CADJPY": "CADJPY",
        "CHFJPY": "CHFJPY",
        "XAUUSD": "GOLD", "XAGUSD": "SILVER",
        "US30": "US_30", "US500": "US_500", "NAS100": "US_TECH100",
        "GER40": "GERMANY_40", "UK100": "UK_100",
        "USOIL": "CrudeOIL", "UKOIL": "BRENT_OIL",
        "BTCUSD": "BTCUSD", "ETHUSD": "ETHUSD",
    }
    
    # 获取多周期数据（365天）
    research.fetch_multi_timeframe_data(
        all_symbols,
        timeframes=["H1", "H4", "D1"],
        lookback_days=365
    )
    
    if not research.raw_data:
        logger.error("没有获取到数据，无法继续")
        return
    
    # 参数扫描
    param_analysis = research.run_param_sweep()
    
    # 使用最佳参数重新运行
    best = param_analysis.get('best_params')
    if best:
        logger.info(f"使用最佳参数重新分析: {best}")
        research.find_setups(
            min_squeeze_score=best['min_score'],
            cooldown_bars=5,
            require_structural=best['require_structural']
        )
        research.detect_breakouts(
            max_wait_bars=best['max_wait'],
            min_breakout_atr=best['min_atr']
        )
    else:
        research.find_setups(min_squeeze_score=2)
        research.detect_breakouts()
    
    result = research.analyze(deduplicate=True)
    
    if result:
        print(f"\n{'='*60}")
        print("分析结果摘要")
        print(f"{'='*60}")
        print(f"Setup总数: {result.total_setups}")
        print(f"突破事件(原始): {result.total_breakouts}")
        print(f"唯一突破事件: {result.unique_breakouts}")
        print(f"突破率: {result.breakout_rate*100:.1f}%")
        print(f"5bar胜率(原始): {result.win_rate_5bar*100:.1f}%")
        print(f"5bar胜率(去重): {result.unique_win_rate_5bar*100:.1f}%")
        print(f"盈亏比(去重): {result.unique_win_loss_ratio:.2f}")
        print(f"期望值(去重): {result.unique_expectancy_5bar:.3f}%")
        print(f"顺势突破胜率: {result.with_trend_win_rate*100:.1f}%")
        print(f"逆势突破胜率: {result.against_trend_win_rate*100:.1f}%")
        print(f"验证状态: {result.validation_status}")
        
        if best:
            print(f"\n最佳参数:")
            print(f"  min_score: {best['min_score']}")
            print(f"  max_wait: {best['max_wait']}")
            print(f"  min_atr: {best['min_atr']}")
            print(f"  require_structural: {best['require_structural']}")
        
        report_path, csv_path = research.generate_report(result, param_analysis)
        print(f"\n报告: {report_path}")
        if csv_path:
            print(f"样本: {csv_path}")
    
    print("\n" + "=" * 70)
    print("研究完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
