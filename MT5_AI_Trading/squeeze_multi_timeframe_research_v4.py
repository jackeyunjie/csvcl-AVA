"""
多周期共振收缩→突破统计验证研究 v4

基于v3 + Phase 1诊断发现的改进:
1. 突破后1bar确认机制 (最强发现: 胜率差+29%)
2. ADX<12强收缩筛选 (扩展ADX<10以平衡样本量)
3. 大range收缩偏好 (Q4期望5.5% vs Q1的-0.15%)
4. 品种白名单 (16个正期望品种)
5. 趋势强度重定义 (ADX>25+DI方向 = strong_trend)
6. 保持v3所有修正: as-of对齐, 真实event_id, 交易成本, walk-forward

注意：不把squeeze_setup直接当long/short信号
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
logger = logging.getLogger("squeeze_mt_research_v4")


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

# 交易成本模型
COST_MODEL = {
    "FX": {"spread_pct": 0.015, "commission_pct": 0.0, "swap_pct": 0.005},
    "metal": {"spread_pct": 0.03, "commission_pct": 0.0, "swap_pct": 0.01},
    "index": {"spread_pct": 0.02, "commission_pct": 0.0, "swap_pct": 0.008},
    "oil": {"spread_pct": 0.025, "commission_pct": 0.0, "swap_pct": 0.01},
    "crypto": {"spread_pct": 0.05, "commission_pct": 0.0, "swap_pct": 0.02},
}

SYMBOL_CLASS = {
    "EURUSD": "FX", "GBPUSD": "FX", "USDJPY": "FX",
    "AUDUSD": "FX", "USDCAD": "FX", "USDCHF": "FX",
    "NZDUSD": "FX", "EURGBP": "FX", "EURJPY": "FX",
    "GBPJPY": "FX", "AUDJPY": "FX", "CADJPY": "FX",
    "CHFJPY": "FX",
    "XAUUSD": "metal", "XAGUSD": "metal",
    "US30": "index", "US500": "index", "NAS100": "index",
    "GER40": "index", "UK100": "index",
    "USOIL": "oil", "UKOIL": "oil",
    "BTCUSD": "crypto", "ETHUSD": "crypto",
}

# v4: 品种白名单 (Phase 1诊断出的正期望品种)
SYMBOL_WHITELIST = {
    "XAGUSD", "UKOIL", "USOIL", "US30", "ETHUSD", "XAUUSD", 
    "UK100", "EURUSD", "AUDUSD", "EURGBP", "US500", "GBPUSD",
    "USDJPY", "CADJPY", "GER40", "CHFJPY"
}


def get_symbol_cost(symbol: str) -> Dict:
    cls = SYMBOL_CLASS.get(symbol, "FX")
    return COST_MODEL.get(cls, COST_MODEL["FX"])


# 复用v3的数据类
from squeeze_multi_timeframe_research_v3 import (
    SqueezeSetup, BreakoutEvent, Trade, ResearchResult
)


class MultiTimeframeSqueezeResearchV4:
    """多周期共振收缩→突破统计验证引擎 v4"""
    
    def __init__(self):
        self.observer = SqueezeObserver()
        self.setups: List[SqueezeSetup] = []
        self.breakouts: List[BreakoutEvent] = []
        self.trades: List[Trade] = []
        self.raw_data: Dict[str, Dict[str, pd.DataFrame]] = {}
        
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
                    tf_lookback = lookback_days
                    if tf == "D1":
                        tf_lookback = max(lookback_days, 730)
                    elif tf == "H4":
                        tf_lookback = max(lookback_days, 365)
                    
                    logger.info(f"获取数据: {std_name} ({mt5_name}) {tf} ({tf_lookback}天)")
                    df = self.observer._fetch_from_mt5(mt5_name, tf, tf_lookback)
                    if not df.empty and len(df) >= 50:
                        if 'timestamp' not in df.columns:
                            logger.warning(f"  {std_name}@{tf} 缺少timestamp列")
                            continue
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
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
    
    def _compute_trend_bias_asof(self, df_high_tf: pd.DataFrame, 
                                  setup_time: datetime) -> Tuple[str, float, float, float, Optional[datetime], float]:
        """
        v4: 返回趋势强度信息 (新增adx_value)
        Returns: (trend_bias, ma_slope, di_plus, di_minus, bar_time, adx_value)
        """
        if df_high_tf is None or len(df_high_tf) == 0:
            return "neutral", 0.0, 0.0, 0.0, None, 0.0
        
        df = df_high_tf.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        available = df[df['timestamp'] <= setup_time]
        
        if len(available) == 0:
            return "neutral", 0.0, 0.0, 0.0, None, 0.0
        
        latest_bar_time = available['timestamp'].iloc[-1]
        
        if len(df_high_tf) < 25:
            return "neutral", 0.0, 0.0, 0.0, latest_bar_time, 0.0
        
        if len(available) < 20:
            return "neutral", 0.0, 0.0, 0.0, latest_bar_time, 0.0
        
        # MA斜率
        ma = available['close'].rolling(20).mean()
        if len(ma) >= 5 and not pd.isna(ma.iloc[-1]) and not pd.isna(ma.iloc[-5]) and ma.iloc[-5] != 0:
            ma_slope = (ma.iloc[-1] - ma.iloc[-5]) / ma.iloc[-5] * 100
        else:
            ma_slope = 0.0
        
        # ADX DI+/-
        tr1 = available['high'] - available['low']
        tr2 = (available['high'] - available['close'].shift(1)).abs()
        tr3 = (available['low'] - available['close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        plus_dm = available['high'].diff()
        minus_dm = -available['low'].diff()
        plus_dm = plus_dm.clip(lower=0)
        minus_dm = minus_dm.clip(lower=0)
        
        plus_dm_clean = plus_dm.copy()
        minus_dm_clean = minus_dm.copy()
        plus_dm_clean[plus_dm <= minus_dm] = 0
        minus_dm_clean[minus_dm <= plus_dm] = 0
        
        atr = tr.ewm(alpha=1/14, min_periods=14).mean()
        plus_di = 100 * plus_dm_clean.ewm(alpha=1/14, min_periods=14).mean() / atr
        minus_di = 100 * minus_dm_clean.ewm(alpha=1/14, min_periods=14).mean() / atr
        
        # v4: 计算ADX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(alpha=1/14, min_periods=14).mean()
        
        di_plus = plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 0
        di_minus = minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 0
        adx_value = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
        
        # v4: 趋势强度分类
        if adx_value > 25:
            if di_plus > di_minus:
                bias = "strong_bullish"
            elif di_minus > di_plus:
                bias = "strong_bearish"
            else:
                bias = "neutral"
        elif ma_slope > 0.05 and di_plus > di_minus:
            bias = "weak_bullish"
        elif ma_slope < -0.05 and di_minus > di_plus:
            bias = "weak_bearish"
        elif ma_slope > 0.1:
            bias = "weak_bullish"
        elif ma_slope < -0.1:
            bias = "weak_bearish"
        else:
            bias = "neutral"
        
        return bias, ma_slope, di_plus, di_minus, latest_bar_time, adx_value
    
    def _precompute_trend_biases(self, symbol: str, h1_df: pd.DataFrame,
                                  h4_df: Optional[pd.DataFrame],
                                  d1_df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """v4: 预计算趋势bias + ADX强度"""
        h1 = h1_df.copy()
        h1['timestamp'] = pd.to_datetime(h1['timestamp'])
        h1 = h1.sort_values('timestamp').reset_index(drop=True)
        
        result = pd.DataFrame({
            'timestamp': h1['timestamp'],
            'h4_trend_bias': 'neutral',
            'h4_ma_slope': 0.0,
            'h4_di_plus': 0.0,
            'h4_di_minus': 0.0,
            'h4_adx': 0.0,
            'h4_bar_time': pd.NaT,
            'd1_trend_bias': 'neutral',
            'd1_ma_slope': 0.0,
            'd1_di_plus': 0.0,
            'd1_di_minus': 0.0,
            'd1_adx': 0.0,
            'd1_bar_time': pd.NaT,
            'data_warning': None
        })
        
        def _compute_trend_for_df(high_tf_df: pd.DataFrame, prefix: str):
            if high_tf_df is None or high_tf_df.empty or len(high_tf_df) < 25:
                return
            
            df = high_tf_df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 计算MA斜率
            df['ma'] = df['close'].rolling(20).mean()
            df['ma_slope'] = df['ma'].diff(4) / df['ma'].shift(4) * 100
            
            # 计算DI和ADX
            tr1 = df['high'] - df['low']
            tr2 = (df['high'] - df['close'].shift(1)).abs()
            tr3 = (df['low'] - df['close'].shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            plus_dm = df['high'].diff().clip(lower=0)
            minus_dm = (-df['low'].diff()).clip(lower=0)
            
            atr = tr.ewm(alpha=1/14, min_periods=14).mean()
            plus_di = 100 * plus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr.replace(0, np.nan)
            minus_di = 100 * minus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr.replace(0, np.nan)
            
            dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
            adx = dx.ewm(alpha=1/14, min_periods=14).mean()
            
            df['di_plus'] = plus_di
            df['di_minus'] = minus_di
            df['adx'] = adx
            
            # v4: 趋势强度分类
            conditions = [
                (df['adx'] > 25) & (df['di_plus'] > df['di_minus']),
                (df['adx'] > 25) & (df['di_minus'] > df['di_plus']),
                (df['ma_slope'] > 0.05) & (df['di_plus'] > df['di_minus']),
                (df['ma_slope'] < -0.05) & (df['di_minus'] > df['di_plus']),
                df['ma_slope'] > 0.1,
                df['ma_slope'] < -0.1
            ]
            choices = ['strong_bullish', 'strong_bearish', 'weak_bullish', 'weak_bearish', 'weak_bullish', 'weak_bearish']
            df['trend_bias'] = np.select(conditions, choices, default='neutral')
            
            df_renamed = df[['timestamp', 'trend_bias', 'ma_slope', 'di_plus', 'di_minus', 'adx']].copy()
            df_renamed = df_renamed.rename(columns={'timestamp': 'htf_timestamp'})
            merged = pd.merge_asof(
                h1[['timestamp']], df_renamed,
                left_on='timestamp', right_on='htf_timestamp', direction='backward'
            )
            
            result[f'{prefix}_trend_bias'] = merged['trend_bias'].fillna('neutral')
            result[f'{prefix}_ma_slope'] = merged['ma_slope'].fillna(0.0)
            result[f'{prefix}_di_plus'] = merged['di_plus'].fillna(0.0)
            result[f'{prefix}_di_minus'] = merged['di_minus'].fillna(0.0)
            result[f'{prefix}_adx'] = merged['adx'].fillna(0.0)
            result[f'{prefix}_bar_time'] = merged['htf_timestamp']
        
        if h4_df is not None and not h4_df.empty:
            _compute_trend_for_df(h4_df, 'h4')
        
        if d1_df is not None and not d1_df.empty:
            _compute_trend_for_df(d1_df, 'd1')
        
        warnings_list = []
        for idx, row in result.iterrows():
            warnings = []
            if h4_df is not None and pd.isna(row['h4_bar_time']):
                warnings.append("H4数据缺失")
            if d1_df is not None and pd.isna(row['d1_bar_time']):
                warnings.append("D1数据缺失")
            warnings_list.append(";".join(warnings) if warnings else None)
        result['data_warning'] = warnings_list
        
        return result

    def find_setups(self, min_squeeze_score: int = 2,
                    cooldown_bars: int = 5,
                    require_structural: bool = False,
                    use_whitelist: bool = True,
                    max_adx: float = 12.0,
                    min_anchor_range_pct: float = 0.4) -> List[SqueezeSetup]:
        """v4: 识别收缩setup时刻"""
        setups = []
        setup_counter = 0
        
        for symbol, tf_data in self.raw_data.items():
            if use_whitelist and symbol not in SYMBOL_WHITELIST:
                continue
            
            h1_df = tf_data.get("H1")
            if h1_df is None or len(h1_df) < 30:
                continue
            
            h1_df = h1_df.copy().reset_index(drop=True)
            
            h1_df['bb_width'] = SqueezeObserver.compute_bb_width(h1_df['close'])
            h1_df['sr_range'] = SqueezeObserver.compute_sr_range(h1_df['high'], h1_df['low'], h1_df['close'])
            h1_df['adx'] = SqueezeObserver.compute_adx(h1_df['high'], h1_df['low'], h1_df['close'])
            
            h1_df['bb_20pct'] = h1_df['bb_width'].expanding(min_periods=20).quantile(0.20)
            h1_df['sr_20pct'] = h1_df['sr_range'].expanding(min_periods=20).quantile(0.20)
            
            h1_df['bb_squeezed'] = (h1_df['bb_width'] <= h1_df['bb_20pct']) & h1_df['bb_width'].notna()
            h1_df['sr_squeezed'] = (h1_df['sr_range'] <= h1_df['sr_20pct']) & h1_df['sr_range'].notna()
            h1_df['adx_lt_20'] = h1_df['adx'] < 20
            h1_df['adx_lt_13'] = h1_df['adx'] < 13
            h1_df['adx_lt_9'] = h1_df['adx'] < 9
            
            h1_df['structural_score'] = h1_df[['bb_squeezed', 'sr_squeezed']].sum(axis=1)
            score_cols = ['bb_squeezed', 'sr_squeezed', 'adx_lt_20', 'adx_lt_13', 'adx_lt_9']
            h1_df['squeeze_score'] = h1_df[score_cols].sum(axis=1)
            
            h4_df = tf_data.get("H4")
            d1_df = tf_data.get("D1")
            trend_df = self._precompute_trend_biases(symbol, h1_df, h4_df, d1_df)
            
            last_setup_idx = -cooldown_bars - 1
            
            for i in range(30, len(h1_df)):
                if h1_df['squeeze_score'].iloc[i] < min_squeeze_score:
                    continue
                if require_structural and h1_df['structural_score'].iloc[i] < 1:
                    continue
                if i - last_setup_idx <= cooldown_bars:
                    continue
                if h1_df['adx'].iloc[i] > max_adx:
                    continue
                
                anchor_start = max(0, i - 20)
                anchor_window = h1_df.iloc[anchor_start:i]
                if len(anchor_window) < 10:
                    continue
                
                anchor_high = anchor_window['high'].max()
                anchor_low = anchor_window['low'].min()
                anchor_range = anchor_high - anchor_low
                if anchor_range <= 0:
                    continue
                
                close = h1_df['close'].iloc[i]
                anchor_range_pct = anchor_range / close * 100
                if anchor_range_pct < min_anchor_range_pct:
                    continue
                
                conditions = []
                if h1_df['bb_squeezed'].iloc[i]: conditions.append("BB")
                if h1_df['sr_squeezed'].iloc[i]: conditions.append("SR")
                if h1_df['adx_lt_20'].iloc[i]: conditions.append("ADX<20")
                if h1_df['adx_lt_13'].iloc[i]: conditions.append("ADX<13")
                if h1_df['adx_lt_9'].iloc[i]: conditions.append("ADX<9")
                
                trend_row = trend_df.iloc[i]
                ts = h1_df['timestamp'].iloc[i]
                setup_counter += 1
                setup_id = f"{symbol}_setup_{setup_counter:06d}_{ts.strftime('%Y%m%d%H%M')}"
                cluster_id = f"{symbol}_{ts.strftime('%Y%m%d_%H')}"
                
                setup = SqueezeSetup(
                    setup_id=setup_id, symbol=symbol, timeframe="H1",
                    timestamp=ts, bar_idx=i,
                    squeeze_score=int(h1_df['squeeze_score'].iloc[i]),
                    conditions=conditions,
                    bb_width=h1_df['bb_width'].iloc[i],
                    sr_range=h1_df['sr_range'].iloc[i],
                    adx=h1_df['adx'].iloc[i],
                    state_is_zero=False,
                    open=h1_df['open'].iloc[i], high=h1_df['high'].iloc[i],
                    low=h1_df['low'].iloc[i], close=close,
                    anchor_high=anchor_high, anchor_low=anchor_low,
                    anchor_range=anchor_range, anchor_range_pct=anchor_range_pct,
                    anchor_mid=(anchor_high + anchor_low) / 2,
                    h4_trend_bias=trend_row['h4_trend_bias'],
                    d1_trend_bias=trend_row['d1_trend_bias'],
                    h4_ma_slope=trend_row['h4_ma_slope'],
                    d1_ma_slope=trend_row['d1_ma_slope'],
                    h4_adx_di_plus=trend_row['h4_di_plus'],
                    h4_adx_di_minus=trend_row['h4_di_minus'],
                    d1_adx_di_plus=trend_row['d1_di_plus'],
                    d1_adx_di_minus=trend_row['d1_di_minus'],
                    h4_bar_time=trend_row['h4_bar_time'] if not pd.isna(trend_row['h4_bar_time']) else None,
                    d1_bar_time=trend_row['d1_bar_time'] if not pd.isna(trend_row['d1_bar_time']) else None,
                    data_warning=trend_row['data_warning'],
                    cluster_id=cluster_id
                )
                setups.append(setup)
                last_setup_idx = i
        
        self.setups = setups
        logger.info(f"v4识别到 {len(setups)} 个setup")
        return setups

    def detect_breakouts(self, max_wait_bars: int = 20,
                         min_breakout_anchor_multiple: float = 0.25,
                         require_1bar_confirmation: bool = True) -> List[BreakoutEvent]:
        """v4: 检测setup后的突破事件，含1bar确认机制"""
        breakouts = []
        event_counter = 0
        
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
            
            up_threshold = setup.anchor_high + min_breakout_anchor_multiple * setup.anchor_range
            down_threshold = setup.anchor_low - min_breakout_anchor_multiple * setup.anchor_range
            
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
            
            # v4: 1bar确认机制
            if require_1bar_confirmation:
                entry_idx = setup.bar_idx + breakout_bar_idx
                if entry_idx + 1 < len(df):
                    next_bar_close = df.iloc[entry_idx + 1]['close']
                    if direction == "up" and next_bar_close <= entry_price:
                        continue
                    if direction == "down" and next_bar_close >= entry_price:
                        continue
            
            # v4: 趋势强度过滤 (只过滤极端逆势)
            h4_bias = setup.h4_trend_bias
            d1_bias = setup.d1_trend_bias
            h4_dir = "bullish" if "bullish" in h4_bias else ("bearish" if "bearish" in h4_bias else "neutral")
            d1_dir = "bullish" if "bullish" in d1_bias else ("bearish" if "bearish" in d1_bias else "neutral")
            
            if direction == "up" and h4_dir == "bearish" and d1_dir == "bearish":
                continue
            if direction == "down" and h4_dir == "bullish" and d1_dir == "bullish":
                continue
            
            entry_idx = setup.bar_idx + breakout_bar_idx
            future_prices = df.iloc[entry_idx:entry_idx + 21]
            
            def calc_return(n):
                if n < len(future_prices) and n >= 0:
                    return (future_prices.iloc[n]['close'] - entry_price) / entry_price * 100
                return np.nan
            
            def calc_pnl(n, direction):
                r = calc_return(n)
                if pd.isna(r):
                    return np.nan
                return r if direction == "up" else -r
            
            returns_1bar = calc_return(1)
            returns_5bar = calc_return(5)
            returns_10bar = calc_return(10)
            returns_20bar = calc_return(20)
            
            if len(future_prices) > 0:
                if direction == "up":
                    mfe = (future_prices['high'] - entry_price).max() / entry_price * 100
                    mae = (entry_price - future_prices['low']).min() / entry_price * 100
                else:
                    mfe = (entry_price - future_prices['low']).min() / entry_price * 100
                    mae = (future_prices['high'] - entry_price).max() / entry_price * 100
            else:
                mfe = 0
                mae = 0
            
            stop_price = setup.anchor_low if direction == "up" else setup.anchor_high
            stop_triggered = False
            stop_bar = None
            stop_after_entry = False
            
            entry_future = df.iloc[entry_idx:entry_idx + 21]
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
            
            target_1r = setup.anchor_range if direction == "up" else -setup.anchor_range
            target_2r = 2 * setup.anchor_range if direction == "up" else -2 * setup.anchor_range
            target_3r = 3 * setup.anchor_range if direction == "up" else -3 * setup.anchor_range
            
            def check_target(target):
                if len(future_prices) == 0:
                    return False
                if direction == "up":
                    return (future_prices['high'] - entry_price).max() >= target
                else:
                    return (entry_price - future_prices['low']).max() >= abs(target)
            
            hit_1r = check_target(target_1r)
            hit_2r = check_target(target_2r)
            hit_3r = check_target(target_3r)
            
            pnl_5 = calc_pnl(5, direction)
            pnl_10 = calc_pnl(10, direction)
            pnl_20 = calc_pnl(20, direction)
            
            if direction == "up":
                if "bullish" in h4_bias or "bullish" in d1_bias:
                    trend_alignment = "with_trend"
                elif "bearish" in h4_bias or "bearish" in d1_bias:
                    trend_alignment = "against_trend"
                else:
                    trend_alignment = "neutral"
            elif direction == "down":
                if "bearish" in h4_bias or "bearish" in d1_bias:
                    trend_alignment = "with_trend"
                elif "bullish" in h4_bias or "bullish" in d1_bias:
                    trend_alignment = "against_trend"
                else:
                    trend_alignment = "neutral"
            else:
                trend_alignment = "neutral"
            
            event_counter += 1
            bo_ts = future.iloc[breakout_bar_idx - 1]['timestamp']
            event_id = f"{setup.symbol}_{bo_ts.strftime('%Y%m%d%H%M')}_{direction}_{event_counter:06d}"
            
            event = BreakoutEvent(
                event_id=event_id,
                setup=setup,
                breakout_timestamp=bo_ts,
                breakout_bar_idx=breakout_bar_idx,
                breakout_direction=direction,
                entry_price=entry_price,
                breakout_level=breakout_level,
                returns_1bar=returns_1bar if not pd.isna(returns_1bar) else 0,
                returns_3bar=calc_return(3) if not pd.isna(calc_return(3)) else 0,
                returns_5bar=returns_5bar if not pd.isna(returns_5bar) else 0,
                returns_10bar=returns_10bar if not pd.isna(returns_10bar) else 0,
                returns_20bar=returns_20bar if not pd.isna(returns_20bar) else 0,
                mfe_pct=mfe,
                mae_pct=mae,
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
                trend_alignment=trend_alignment
            )
            breakouts.append(event)
        
        self.breakouts = breakouts
        logger.info(f"v4检测到 {len(breakouts)} 个突破事件（含1bar确认）")
        return breakouts

    def _deduplicate_breakouts(self, breakouts: List[BreakoutEvent]) -> List[BreakoutEvent]:
        """v4: 使用真实event_id去重"""
        seen_events = {}
        duplicate_count = 0
        
        for b in breakouts:
            event_key = f"{b.setup.symbol}_{b.breakout_timestamp.strftime('%Y%m%d%H%M')}_{b.breakout_direction}"
            if event_key not in seen_events:
                seen_events[event_key] = b
            else:
                duplicate_count += 1
        
        unique_breakouts = list(seen_events.values())
        logger.info(f"去重前: {len(breakouts)} 个, 去重后: {len(unique_breakouts)} 个唯一突破, 重复: {duplicate_count}")
        return unique_breakouts
    
    def _assign_walk_forward_fold(self, timestamp: datetime, 
                                   train_end: datetime,
                                   validation_end: datetime) -> str:
        """分配walk-forward分区"""
        if timestamp <= train_end:
            return "train"
        elif timestamp <= validation_end:
            return "validation"
        else:
            return "test"
    
    def run_trade_backtest(self, unique_events: List[BreakoutEvent],
                           fold_boundaries: Tuple[datetime, datetime] = None) -> List[Trade]:
        """v4: 交易级回测 - 三类出场规则"""
        trades = []
        trade_counter = 0
        
        if fold_boundaries:
            train_end, validation_end = fold_boundaries
        else:
            all_times = [e.breakout_timestamp for e in unique_events]
            min_ts, max_ts = min(all_times), max(all_times)
            duration = max_ts - min_ts
            train_end = min_ts + duration * 0.6
            validation_end = min_ts + duration * 0.8
        
        for event in unique_events:
            symbol_data = self.raw_data.get(event.setup.symbol)
            if symbol_data is None:
                continue
            
            df = symbol_data.get("H1")
            if df is None:
                continue
            
            entry_idx = event.setup.bar_idx + event.breakout_bar_idx
            if entry_idx >= len(df):
                continue
            
            entry_price = event.entry_price
            entry_time = event.breakout_timestamp
            direction = event.breakout_direction
            
            # 获取未来价格
            future = df.iloc[entry_idx:entry_idx + 25]
            if len(future) < 5:
                continue
            
            cost = get_symbol_cost(event.setup.symbol)
            total_cost = cost['spread_pct'] + cost['commission_pct']
            
            fold = self._assign_walk_forward_fold(entry_time, train_end, validation_end)
            
            # 三类出场规则
            exit_rules = [
                ("fixed_hold_5bar", 5),
                ("fixed_hold_10bar", 10),
                ("structure_stop", None)
            ]
            
            for rule_name, hold_bars in exit_rules:
                if rule_name == "structure_stop":
                    # 结构止损: 触发止损或持有20bar
                    stop_price = event.setup.anchor_low if direction == "up" else event.setup.anchor_high
                    exit_price = None
                    exit_time = None
                    bars_held = 0
                    
                    for j, (_, row) in enumerate(future.iterrows()):
                        if j == 0:
                            continue
                        if direction == "up" and row['low'] < stop_price:
                            exit_price = stop_price
                            exit_time = row['timestamp']
                            bars_held = j
                            break
                        elif direction == "down" and row['high'] > stop_price:
                            exit_price = stop_price
                            exit_time = row['timestamp']
                            bars_held = j
                            break
                        if j >= 20:
                            exit_price = row['close']
                            exit_time = row['timestamp']
                            bars_held = j
                            break
                    
                    if exit_price is None:
                        exit_price = future.iloc[-1]['close']
                        exit_time = future.iloc[-1]['timestamp']
                        bars_held = len(future) - 1
                else:
                    # 固定持有
                    if hold_bars < len(future):
                        exit_price = future.iloc[hold_bars]['close']
                        exit_time = future.iloc[hold_bars]['timestamp']
                        bars_held = hold_bars
                    else:
                        exit_price = future.iloc[-1]['close']
                        exit_time = future.iloc[-1]['timestamp']
                        bars_held = len(future) - 1
                
                if direction == "up":
                    gross_pnl = (exit_price - entry_price) / entry_price * 100
                else:
                    gross_pnl = (entry_price - exit_price) / entry_price * 100
                
                net_pnl = gross_pnl - total_cost
                
                # MFE/MAE
                if direction == "up":
                    mfe = (future['high'] - entry_price).max() / entry_price * 100
                    mae = (entry_price - future['low']).min() / entry_price * 100
                else:
                    mfe = (entry_price - future['low']).min() / entry_price * 100
                    mae = (future['high'] - entry_price).max() / entry_price * 100
                
                trade_counter += 1
                trade = Trade(
                    trade_id=f"T{trade_counter:06d}",
                    event_id=event.event_id,
                    symbol=event.setup.symbol,
                    direction=direction,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=exit_time,
                    exit_price=exit_price,
                    exit_rule=rule_name,
                    gross_pnl_pct=gross_pnl,
                    cost_pct=total_cost,
                    net_pnl_pct=net_pnl,
                    mfe_pct=mfe,
                    mae_pct=mae,
                    bars_held=bars_held,
                    fold=fold
                )
                trades.append(trade)
        
        self.trades = trades
        logger.info(f"生成 {len(trades)} 笔交易记录")
        return trades
    
    def analyze(self, deduplicate: bool = True) -> Optional[ResearchResult]:
        """v4: 分析结果"""
        if not self.breakouts:
            logger.warning("无突破事件可分析")
            return None
        
        events = self._deduplicate_breakouts(self.breakouts) if deduplicate else self.breakouts
        
        total_setups = len(self.setups)
        total_breakouts = len(self.breakouts)
        unique_breakouts = len(events)
        breakout_rate = unique_breakouts / total_setups if total_setups > 0 else 0
        
        up_breakouts = sum(1 for e in events if e.breakout_direction == "up")
        down_breakouts = sum(1 for e in events if e.breakout_direction == "down")
        direction_balance = up_breakouts / unique_breakouts if unique_breakouts > 0 else 0
        
        # 收益统计
        returns_5bar_all = [e.returns_5bar for e in events]
        returns_5bar_bo = [e.returns_5bar for e in events]
        
        raw_win_rate = sum(1 for r in returns_5bar_all if r > 0) / len(returns_5bar_all) if returns_5bar_all else 0
        
        wins = [r for r in returns_5bar_all if r > 0]
        losses = [r for r in returns_5bar_all if r < 0]
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        raw_expectancy = raw_win_rate * avg_win + (1 - raw_win_rate) * avg_loss
        
        # 唯一事件指标
        unique_win_rate = raw_win_rate
        unique_expectancy = raw_expectancy
        
        # 1R/2R/3R
        hit_1r = sum(1 for e in events if e.hit_target_1r) / len(events) if events else 0
        hit_2r = sum(1 for e in events if e.hit_target_2r) / len(events) if events else 0
        hit_3r = sum(1 for e in events if e.hit_target_3r) / len(events) if events else 0
        stop_rate = sum(1 for e in events if e.stop_triggered) / len(events) if events else 0
        stop_after_entry_rate = sum(1 for e in events if e.stop_after_entry) / len(events) if events else 0
        
        # 交易成本后
        if self.trades:
            net_pnls = [t.net_pnl_pct for t in self.trades if t.exit_rule == "fixed_hold_5bar"]
            net_win_rate = sum(1 for p in net_pnls if p > 0) / len(net_pnls) if net_pnls else 0
            net_expectancy = np.mean(net_pnls) if net_pnls else 0
        else:
            net_win_rate = 0
            net_expectancy = 0
        
        # 趋势共振
        by_trend = defaultdict(lambda: {"count": 0, "wins": 0, "pnls": []})
        for e in events:
            ta = e.trend_alignment
            by_trend[ta]["count"] += 1
            by_trend[ta]["pnls"].append(e.returns_5bar)
            if e.returns_5bar > 0:
                by_trend[ta]["wins"] += 1
        
        by_trend_alignment = {}
        for ta, d in by_trend.items():
            by_trend_alignment[ta] = {
                "count": d["count"],
                "win_rate": d["wins"] / d["count"] if d["count"] > 0 else 0,
                "avg_pnl": np.mean(d["pnls"]) if d["pnls"] else 0
            }
        
        # Walk-forward
        def calc_fold_metrics(trades_list):
            pnls = [t.net_pnl_pct for t in trades_list if t.exit_rule == "fixed_hold_5bar"]
            if not pnls:
                return {"count": 0, "win_rate": 0, "avg_gross": 0, "avg_net": 0, "expectancy": 0}
            gross = [t.gross_pnl_pct for t in trades_list if t.exit_rule == "fixed_hold_5bar"]
            return {
                "count": len(pnls),
                "win_rate": sum(1 for p in pnls if p > 0) / len(pnls),
                "avg_gross": np.mean(gross),
                "avg_net": np.mean(pnls),
                "expectancy": np.mean(pnls)
            }
        
        train_trades = [t for t in self.trades if t.fold == "train"]
        val_trades = [t for t in self.trades if t.fold == "validation"]
        test_trades = [t for t in self.trades if t.fold == "test"]
        
        # Score分组
        by_score = {}
        for e in events:
            score = e.setup.squeeze_score
            if score not in by_score:
                by_score[score] = {"count": 0, "breakouts": 0, "wins": 0, "pnls": []}
            by_score[score]["count"] += 1
            by_score[score]["breakouts"] += 1
            by_score[score]["pnls"].append(e.returns_5bar)
            if e.returns_5bar > 0:
                by_score[score]["wins"] += 1
        
        for score in by_score:
            d = by_score[score]
            d["win_rate"] = d["wins"] / d["count"] if d["count"] > 0 else 0
            d["avg_pnl"] = np.mean(d["pnls"]) if d["pnls"] else 0
        
        # 品种分组
        by_symbol = {}
        for e in events:
            sym = e.setup.symbol
            if sym not in by_symbol:
                by_symbol[sym] = {"setups": 0, "breakouts": 0, "pnls": [], "net_pnls": []}
            by_symbol[sym]["breakouts"] += 1
            by_symbol[sym]["pnls"].append(e.returns_5bar)
        
        for s in self.setups:
            sym = s.symbol
            if sym in by_symbol:
                by_symbol[sym]["setups"] += 1
        
        for sym in by_symbol:
            d = by_symbol[sym]
            d["avg_pnl"] = np.mean(d["pnls"]) if d["pnls"] else 0
            sym_net = [t.net_pnl_pct for t in self.trades if t.symbol == sym and t.exit_rule == "fixed_hold_5bar"]
            d["avg_net_pnl"] = np.mean(sym_net) if sym_net else 0
        
        # 验证状态
        if unique_breakouts < 50:
            validation_status = "样本不足"
        elif unique_win_rate > 0.55 and unique_expectancy > 0:
            validation_status = "已验证有效"
        elif net_expectancy > 0:
            validation_status = "逻辑需要调整"
        else:
            validation_status = "暂不建议进入实盘"
        
        warnings = []
        if direction_balance > 0.7 or direction_balance < 0.3:
            warnings.append(f"方向严重失衡: {direction_balance*100:.1f}%向上")
        
        result = ResearchResult(
            total_setups=total_setups,
            total_breakouts=total_breakouts,
            unique_breakouts=unique_breakouts,
            breakout_rate=breakout_rate,
            no_breakout_count=total_setups - unique_breakouts,
            up_breakouts=up_breakouts,
            down_breakouts=down_breakouts,
            direction_balance=direction_balance,
            raw_win_rate_5bar=raw_win_rate,
            raw_expectancy_5bar=raw_expectancy,
            raw_win_loss_ratio=win_loss_ratio,
            unique_win_rate_5bar=unique_win_rate,
            unique_expectancy_5bar=unique_expectancy,
            unique_win_loss_ratio=win_loss_ratio,
            returns_5bar_all_mean=np.mean(returns_5bar_all) if returns_5bar_all else 0,
            returns_5bar_all_median=np.median(returns_5bar_all) if returns_5bar_all else 0,
            returns_10bar_all_mean=np.mean([e.returns_10bar for e in events]) if events else 0,
            returns_20bar_all_mean=np.mean([e.returns_20bar for e in events]) if events else 0,
            returns_5bar_bo_mean=np.mean(returns_5bar_bo) if returns_5bar_bo else 0,
            returns_10bar_bo_mean=np.mean([e.returns_10bar for e in events]) if events else 0,
            hit_1r_rate=hit_1r,
            hit_2r_rate=hit_2r,
            hit_3r_rate=hit_3r,
            stop_rate=stop_rate,
            stop_after_entry_rate=stop_after_entry_rate,
            avg_win_5bar=avg_win,
            avg_loss_5bar=avg_loss,
            with_trend_breakouts=by_trend_alignment.get("with_trend", {}).get("count", 0),
            against_trend_breakouts=by_trend_alignment.get("against_trend", {}).get("count", 0),
            neutral_breakouts=by_trend_alignment.get("neutral", {}).get("count", 0),
            with_trend_win_rate=by_trend_alignment.get("with_trend", {}).get("win_rate", 0),
            against_trend_win_rate=by_trend_alignment.get("against_trend", {}).get("win_rate", 0),
            neutral_win_rate=by_trend_alignment.get("neutral", {}).get("win_rate", 0),
            net_win_rate_5bar=net_win_rate,
            net_expectancy_5bar=net_expectancy,
            by_score=by_score,
            by_symbol=by_symbol,
            by_trend_alignment=by_trend_alignment,
            train_metrics=calc_fold_metrics(train_trades),
            validation_metrics=calc_fold_metrics(val_trades),
            test_metrics=calc_fold_metrics(test_trades),
            recommendations=[],
            validation_status=validation_status,
            warnings=warnings
        )
        
        return result

    def generate_report(self, result: ResearchResult, param_analysis: Dict = None,
                        output_dir: str = "reports/squeeze") -> Tuple[str, str, str, str]:
        """生成v4研究报告和CSV"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        lines = []
        lines.append("# 多周期共振收缩→突破统计验证研究报告 v4")
        lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"\n## 验证状态: {result.validation_status}")
        
        if result.warnings:
            lines.append("\n### 警告")
            for w in result.warnings:
                lines.append(f"- {w}")
        
        lines.append("\n---")
        lines.append("\n## 一、样本概览")
        lines.append("\n| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 总Setup数 | {result.total_setups} |")
        lines.append(f"| 突破事件数(原始) | {result.total_breakouts} |")
        lines.append(f"| 唯一突破事件数 | {result.unique_breakouts} |")
        lines.append(f"| 突破率 | {result.breakout_rate*100:.1f}% |")
        lines.append(f"| 未突破数 | {result.no_breakout_count} |")
        lines.append(f"| 向上突破 | {result.up_breakouts} |")
        lines.append(f"| 向下突破 | {result.down_breakouts} |")
        lines.append(f"| 方向平衡 | {result.direction_balance*100:.1f}% |")
        
        lines.append("\n## 二、收益统计")
        lines.append("\n| 持有周期 | 均值 | 中位数 |")
        lines.append("|----------|------|--------|")
        lines.append(f"| 5bar | {result.returns_5bar_all_mean:.3f}% | {result.returns_5bar_all_median:.3f}% |")
        lines.append(f"| 10bar | {result.returns_10bar_all_mean:.3f}% | - |")
        lines.append(f"| 20bar | {result.returns_20bar_all_mean:.3f}% | - |")
        
        lines.append("\n## 三、交易绩效（原始样本）")
        lines.append("\n| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 5bar胜率 | {result.raw_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 平均盈利 | {result.avg_win_5bar:.3f}% |")
        lines.append(f"| 平均亏损 | {result.avg_loss_5bar:.3f}% |")
        lines.append(f"| 盈亏比 | {result.raw_win_loss_ratio:.2f} |")
        lines.append(f"| 期望值 | {result.raw_expectancy_5bar:.3f}% |")
        
        lines.append("\n## 四、交易绩效（真实唯一事件）")
        lines.append("\n| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 唯一突破数 | {result.unique_breakouts} |")
        lines.append(f"| 5bar胜率 | {result.unique_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 盈亏比 | {result.unique_win_loss_ratio:.2f} |")
        lines.append(f"| 期望值 | {result.unique_expectancy_5bar:.3f}% |")
        lines.append(f"| 1R达成率 | {result.hit_1r_rate*100:.1f}% |")
        lines.append(f"| 2R达成率 | {result.hit_2r_rate*100:.1f}% |")
        lines.append(f"| 3R达成率 | {result.hit_3r_rate*100:.1f}% |")
        lines.append(f"| 止损触发率 | {result.stop_rate*100:.1f}% |")
        lines.append(f"| 入场后止损率 | {result.stop_after_entry_rate*100:.1f}% |")
        
        lines.append("\n## 五、交易成本后指标")
        lines.append("\n| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 净5bar胜率 | {result.net_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 净期望值 | {result.net_expectancy_5bar:.3f}% |")
        
        lines.append("\n## 六、多周期趋势共振分析")
        lines.append("\n| 类型 | 数量 | 胜率 | 平均PNL |")
        lines.append("|------|------|------|---------|")
        for key, d in result.by_trend_alignment.items():
            lines.append(f"| {key} | {d['count']} | {d['win_rate']*100:.1f}% | {d['avg_pnl']:.3f}% |")
        
        lines.append("\n## 七、Walk-Forward分析")
        lines.append("\n| 分区 | 交易数 | 胜率 | 平均Gross | 平均Net | 期望 |")
        lines.append("|------|--------|------|-----------|---------|------|")
        for fold_name, metrics in [("Train", result.train_metrics), ("Validation", result.validation_metrics), ("Test", result.test_metrics)]:
            lines.append(f"| {fold_name} | {metrics['count']} | {metrics['win_rate']*100:.1f}% | {metrics['avg_gross']:.3f}% | {metrics['avg_net']:.3f}% | {metrics['expectancy']:.3f}% |")
        
        lines.append("\n## 八、按Squeeze Score分组")
        lines.append("\n| Score | Setup数 | 突破数 | 胜率 | 平均PNL |")
        lines.append("|-------|---------|--------|------|---------|")
        for score in sorted(result.by_score.keys()):
            d = result.by_score[score]
            lines.append(f"| {score} | {d['count']} | {d['breakouts']} | {d['win_rate']*100:.1f}% | {d['avg_pnl']:.3f}% |")
        
        lines.append("\n## 九、按品种分组")
        lines.append("\n| 品种 | Setup数 | 突破数 | 平均GrossPNL | 平均NetPNL |")
        lines.append("|------|---------|--------|--------------|------------|")
        for sym in sorted(result.by_symbol.keys()):
            d = result.by_symbol[sym]
            lines.append(f"| {sym} | {d['setups']} | {d['breakouts']} | {d['avg_pnl']:.3f}% | {d.get('avg_net_pnl', 0):.3f}% |")
        
        lines.append("\n## 十、v3 vs v4 差异")
        lines.append("\n| 维度 | v3 | v4 |")
        lines.append("|------|-----|-----|")
        lines.append("| 品种过滤 | 24个全部 | 16个白名单 |")
        lines.append("| ADX过滤 | 无 | <12 |")
        lines.append("| Range过滤 | 无 | >0.4% |")
        lines.append("| 突破确认 | 无 | 1bar确认 |")
        lines.append("| 趋势强度 | bullish/bearish | strong/weak/neutral |")
        
        lines.append("\n## 十一、结论")
        lines.append(f"\n**验证状态**: {result.validation_status}")
        lines.append(f"\n**多周期共振效果**: 顺势{result.with_trend_win_rate*100:.1f}% vs 逆势{result.against_trend_win_rate*100:.1f}% vs 中性{result.neutral_win_rate*100:.1f}%")
        lines.append(f"\n**Walk-Forward测试段**: 净期望{result.test_metrics.get('expectancy', 0):.3f}%, 样本{result.test_metrics.get('count', 0)}")
        
        if result.test_metrics.get('expectancy', 0) > 0 and result.test_metrics.get('count', 0) >= 100:
            lines.append("\n**模拟盘观察**: 测试段净期望为正，可考虑搭建模拟盘观察系统（只观察，不下单）")
        else:
            lines.append("\n**模拟盘观察**: 测试段数据不支持，暂不进入模拟盘观察")
        
        lines.append("\n---")
        lines.append("\n> **免责声明**：本报告仅供研究参考，不构成投资建议。")
        lines.append("> **实盘限制**：当前阶段禁止直接进入实盘自动交易。")
        
        report_path = Path(output_dir) / f"squeeze_mt_research_v4_{timestamp}.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"报告已保存: {report_path}")
        
        # setups CSV
        setups_records = []
        for s in self.setups:
            setups_records.append({
                'setup_id': s.setup_id, 'symbol': s.symbol, 'timestamp': s.timestamp,
                'squeeze_score': s.squeeze_score, 'conditions': '+'.join(s.conditions),
                'adx': s.adx, 'h4_trend_bias': s.h4_trend_bias, 'd1_trend_bias': s.d1_trend_bias,
                'h4_bar_time': s.h4_bar_time, 'd1_bar_time': s.d1_bar_time,
                'data_warning': s.data_warning, 'anchor_range_pct': s.anchor_range_pct,
                'cluster_id': s.cluster_id,
            })
        setups_df = pd.DataFrame(setups_records)
        setups_path = Path(output_dir) / f"squeeze_mt_setups_v4_{timestamp}.csv"
        setups_df.to_csv(setups_path, index=False)
        logger.info(f"Setup CSV已保存: {setups_path}")
        
        # events CSV
        unique_events = self._deduplicate_breakouts(self.breakouts)
        events_records = []
        for b in unique_events:
            events_records.append({
                'event_id': b.event_id, 'setup_id': b.setup.setup_id, 'symbol': b.setup.symbol,
                'breakout_timestamp': b.breakout_timestamp, 'breakout_direction': b.breakout_direction,
                'entry_price': b.entry_price, 'trend_alignment': b.trend_alignment,
                'h4_trend_bias': b.setup.h4_trend_bias, 'd1_trend_bias': b.setup.d1_trend_bias,
                'returns_1bar': b.returns_1bar, 'returns_5bar': b.returns_5bar,
                'returns_10bar': b.returns_10bar, 'returns_20bar': b.returns_20bar,
                'mfe_pct': b.mfe_pct, 'mae_pct': b.mae_pct,
                'hit_1r': b.hit_target_1r, 'hit_2r': b.hit_target_2r, 'hit_3r': b.hit_target_3r,
                'stop_triggered': b.stop_triggered, 'stop_after_entry': b.stop_after_entry,
                'pnl_5bar': b.pnl_5bar, 'pnl_10bar': b.pnl_10bar, 'pnl_20bar': b.pnl_20bar,
            })
        events_df = pd.DataFrame(events_records)
        events_path = Path(output_dir) / f"squeeze_mt_events_v4_{timestamp}.csv"
        events_df.to_csv(events_path, index=False)
        logger.info(f"Events CSV已保存: {events_path}")
        
        # trades CSV
        trades_records = []
        for t in self.trades:
            trades_records.append({
                'trade_id': t.trade_id, 'event_id': t.event_id, 'symbol': t.symbol,
                'direction': t.direction, 'entry_time': t.entry_time, 'entry_price': t.entry_price,
                'exit_time': t.exit_time, 'exit_price': t.exit_price, 'exit_rule': t.exit_rule,
                'gross_pnl_pct': t.gross_pnl_pct, 'cost_pct': t.cost_pct, 'net_pnl_pct': t.net_pnl_pct,
                'mfe_pct': t.mfe_pct, 'mae_pct': t.mae_pct, 'bars_held': t.bars_held, 'fold': t.fold,
            })
        trades_df = pd.DataFrame(trades_records)
        trades_path = Path(output_dir) / f"squeeze_mt_trades_v4_{timestamp}.csv"
        trades_df.to_csv(trades_path, index=False)
        logger.info(f"Trades CSV已保存: {trades_path}")
        
        return str(report_path), str(setups_path), str(events_path), str(trades_path)


def main():
    print("=" * 70)
    print("多周期共振收缩→突破统计验证研究 v4")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    research = MultiTimeframeSqueezeResearchV4()
    
    # 获取数据
    data = research.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=365)
    
    if not data:
        print("错误: 未能获取数据")
        return
    
    # v4参数
    research.find_setups(
        min_squeeze_score=2,
        cooldown_bars=5,
        require_structural=False,
        use_whitelist=True,
        max_adx=12.0,
        min_anchor_range_pct=0.4
    )
    
    research.detect_breakouts(
        max_wait_bars=30,
        min_breakout_anchor_multiple=0.1,
        require_1bar_confirmation=True
    )
    
    unique_events = research._deduplicate_breakouts(research.breakouts)
    research.run_trade_backtest(unique_events)
    
    result = research.analyze(deduplicate=True)
    
    if result:
        print("\n" + "=" * 60)
        print("分析结果摘要")
        print("=" * 60)
        print(f"Setup总数: {result.total_setups}")
        print(f"突破事件(原始): {result.total_breakouts}")
        print(f"唯一突破事件: {result.unique_breakouts}")
        print(f"突破率: {result.breakout_rate*100:.1f}%")
        print(f"5bar胜率(原始): {result.raw_win_rate_5bar*100:.1f}%")
        print(f"5bar胜率(唯一事件): {result.unique_win_rate_5bar*100:.1f}%")
        print(f"盈亏比(唯一事件): {result.unique_win_loss_ratio:.2f}")
        print(f"期望值(唯一事件): {result.unique_expectancy_5bar:.3f}%")
        print(f"净5bar胜率: {result.net_win_rate_5bar*100:.1f}%")
        print(f"净期望值: {result.net_expectancy_5bar:.3f}%")
        print(f"顺势突破胜率: {result.with_trend_win_rate*100:.1f}%")
        print(f"逆势突破胜率: {result.against_trend_win_rate*100:.1f}%")
        print(f"验证状态: {result.validation_status}")
        
        print(f"\nWalk-Forward:")
        print(f"  Train: {result.train_metrics['count']}笔, 净期望{result.train_metrics['expectancy']:.3f}%")
        print(f"  Validation: {result.validation_metrics['count']}笔, 净期望{result.validation_metrics['expectancy']:.3f}%")
        print(f"  Test: {result.test_metrics['count']}笔, 净期望{result.test_metrics['expectancy']:.3f}%")
        
        report_path, setups_path, events_path, trades_path = research.generate_report(result)
        print(f"\n报告: {report_path}")
        print(f"Setups: {setups_path}")
        if events_path:
            print(f"Events: {events_path}")
        if trades_path:
            print(f"Trades: {trades_path}")
    
    print("\n" + "=" * 70)
    print("研究完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
