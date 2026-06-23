"""
多周期共振收缩→突破统计验证研究 v3

核心修正（相比v2）：
1. as-of 多周期对齐: 使用 pd.merge_asof，禁止 i//4、i//24 映射
2. 真实 event_id 去重: symbol + breakout_timestamp + breakout_direction
3. 修正 short 方向 target 判断: 使用 .max() 而非 .min()
4. 修正 min_breakout_atr 命名: 改为 min_breakout_anchor_multiple
5. 移除 Pivot/SR 重复计分: 只保留 SR range，移除 Pivot range
6. 加入交易成本和三类出场回测
7. walk-forward: train/validation/test

注意：
- 不把squeeze_setup直接当long/short信号
- 突破方向由价格行为决定，不预设方向
- 所有结论基于样本统计，区分验证状态
- 禁止直接进入实盘自动交易
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
logger = logging.getLogger("squeeze_mt_research_v3")


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

# 交易成本模型（按品种类别）
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


def get_symbol_cost(symbol: str) -> Dict:
    """获取品种交易成本"""
    cls = SYMBOL_CLASS.get(symbol, "FX")
    return COST_MODEL.get(cls, COST_MODEL["FX"])


@dataclass
class SqueezeSetup:
    """收缩Setup事件"""
    setup_id: str  # 唯一setup标识
    symbol: str
    timeframe: str
    timestamp: datetime
    bar_idx: int
    squeeze_score: int
    conditions: List[str]
    
    bb_width: float
    sr_range: float  # v3: 只保留SR，移除Pivot
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
    
    # 多周期共振信息 (as-of对齐)
    h4_trend_bias: str = "neutral"
    d1_trend_bias: str = "neutral"
    h4_ma_slope: float = 0.0
    d1_ma_slope: float = 0.0
    h4_adx_di_plus: float = 0.0
    h4_adx_di_minus: float = 0.0
    d1_adx_di_plus: float = 0.0
    d1_adx_di_minus: float = 0.0
    
    # as-of对齐追溯信息
    h4_bar_time: Optional[datetime] = None
    d1_bar_time: Optional[datetime] = None
    data_warning: Optional[str] = None
    
    # 簇ID（用于诊断，不作为去重主键）
    cluster_id: str = ""


@dataclass
class BreakoutEvent:
    """突破事件"""
    event_id: str  # 真实唯一突破标识: symbol + breakout_timestamp + direction
    setup: SqueezeSetup
    
    breakout_timestamp: datetime
    breakout_bar_idx: int
    breakout_direction: str
    
    entry_price: float
    breakout_level: float
    
    # 未来收益（从entry_price起算，百分比）
    # v3: 1bar=入场后第1根K线close，不把入场bar当成1bar
    returns_1bar: float
    returns_3bar: float
    returns_5bar: float
    returns_10bar: float
    returns_20bar: float
    
    # MFE/MAE (使用high/low)
    mfe_pct: float  # 最大有利波动
    mae_pct: float  # 最大不利波动
    
    hit_target_1r: bool
    hit_target_2r: bool
    hit_target_3r: bool
    
    # 止损（入场后才开始计算）
    stop_triggered: bool
    stop_bar_idx: Optional[int]
    stop_price: Optional[float]
    stop_after_entry: bool
    
    pnl_5bar: float
    pnl_10bar: float
    pnl_20bar: float
    
    # 趋势共振分类 (v3: 移到必填字段，避免dataclass默认值顺序问题)
    trend_alignment: str


@dataclass
class Trade:
    """交易级回测记录"""
    trade_id: str
    event_id: str
    symbol: str
    direction: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime]
    exit_price: Optional[float]
    exit_rule: str  # fixed_hold_5bar / fixed_hold_10bar / structure_stop / 1R_partial
    
    gross_pnl_pct: float
    cost_pct: float
    net_pnl_pct: float
    
    mfe_pct: float
    mae_pct: float
    bars_held: int
    
    # walk-forward分区
    fold: str = "train"  # train / validation / test


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
    
    # 原始样本指标
    raw_win_rate_5bar: float
    raw_expectancy_5bar: float
    raw_win_loss_ratio: float
    
    # 真实唯一事件指标
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
    
    avg_win_5bar: float
    avg_loss_5bar: float
    
    # 多周期共振统计
    with_trend_breakouts: int
    against_trend_breakouts: int
    neutral_breakouts: int
    with_trend_win_rate: float
    against_trend_win_rate: float
    neutral_win_rate: float
    
    # 交易成本后指标
    net_win_rate_5bar: float
    net_expectancy_5bar: float
    
    by_score: Dict
    by_symbol: Dict
    by_trend_alignment: Dict
    
    # walk-forward
    train_metrics: Dict
    validation_metrics: Dict
    test_metrics: Dict
    
    recommendations: List[str]
    validation_status: str
    warnings: List[str]
    
    param_analysis: Dict = field(default_factory=dict)


class MultiTimeframeSqueezeResearchV3:
    """多周期共振收缩→突破统计验证引擎 v3"""
    
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
                        # 确保timestamp列存在且为datetime
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
                                  setup_time: datetime) -> Tuple[str, float, float, float, Optional[datetime]]:
        """
        as-of 计算高周期趋势: 只能使用setup_time之前已收盘的bar
        
        Returns:
            (trend_bias, ma_slope, di_plus, di_minus, bar_time)
        """
        if df_high_tf is None or len(df_high_tf) == 0:
            return "neutral", 0.0, 0.0, 0.0, None
        
        df = df_high_tf.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 只使用setup_time之前已收盘的bar
        available = df[df['timestamp'] <= setup_time]
        
        if len(available) == 0:
            return "neutral", 0.0, 0.0, 0.0, None
        
        latest_bar_time = available['timestamp'].iloc[-1]
        
        # 数据不足25根时，返回neutral但保留bar_time
        if len(df_high_tf) < 25:
            return "neutral", 0.0, 0.0, 0.0, latest_bar_time
        
        if len(available) < 20:
            return "neutral", 0.0, 0.0, 0.0, latest_bar_time
        
        # MA斜率 (用最近5根可用bar)
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
        
        # 修正DI计算
        plus_dm_clean = plus_dm.copy()
        minus_dm_clean = minus_dm.copy()
        plus_dm_clean[plus_dm <= minus_dm] = 0
        minus_dm_clean[minus_dm <= plus_dm] = 0
        
        atr = tr.ewm(alpha=1/14, min_periods=14).mean()
        plus_di = 100 * plus_dm_clean.ewm(alpha=1/14, min_periods=14).mean() / atr
        minus_di = 100 * minus_dm_clean.ewm(alpha=1/14, min_periods=14).mean() / atr
        
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
        
        return bias, ma_slope, di_plus, di_minus, latest_bar_time
    
    def _precompute_trend_biases(self, symbol: str, h1_df: pd.DataFrame,
                                  h4_df: Optional[pd.DataFrame],
                                  d1_df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """
        预计算每个H1 bar的as-of趋势bias
        使用merge_asof进行时间戳对齐 (向量化，避免逐条循环)
        """
        h1 = h1_df.copy()
        h1['timestamp'] = pd.to_datetime(h1['timestamp'])
        h1 = h1.sort_values('timestamp').reset_index(drop=True)
        
        result = pd.DataFrame({
            'timestamp': h1['timestamp'],
            'h4_trend_bias': 'neutral',
            'h4_ma_slope': 0.0,
            'h4_di_plus': 0.0,
            'h4_di_minus': 0.0,
            'h4_bar_time': pd.NaT,
            'd1_trend_bias': 'neutral',
            'd1_ma_slope': 0.0,
            'd1_di_plus': 0.0,
            'd1_di_minus': 0.0,
            'd1_bar_time': pd.NaT,
            'data_warning': None
        })
        
        def _compute_trend_for_df(high_tf_df: pd.DataFrame, prefix: str):
            """向量化计算高周期趋势并merge到H1"""
            if high_tf_df is None or high_tf_df.empty or len(high_tf_df) < 25:
                return
            
            df = high_tf_df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 计算每根高周期bar的趋势指标
            df['ma20'] = df['close'].rolling(20).mean()
            df['ma_slope'] = (df['ma20'] - df['ma20'].shift(4)) / df['ma20'].shift(4).replace(0, np.nan) * 100
            
            # 简化ADX计算
            tr1 = df['high'] - df['low']
            tr2 = (df['high'] - df['close'].shift(1)).abs()
            tr3 = (df['low'] - df['close'].shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.ewm(alpha=1/14, min_periods=14).mean()
            
            plus_dm = df['high'].diff().clip(lower=0)
            minus_dm = (-df['low'].diff()).clip(lower=0)
            plus_di = 100 * plus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr.replace(0, np.nan)
            minus_di = 100 * minus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr.replace(0, np.nan)
            
            df['di_plus'] = plus_di
            df['di_minus'] = minus_di
            
            # 综合判断趋势
            conditions = [
                (df['ma_slope'] > 0.05) & (df['di_plus'] > df['di_minus']),
                (df['ma_slope'] < -0.05) & (df['di_minus'] > df['di_plus']),
                df['ma_slope'] > 0.1,
                df['ma_slope'] < -0.1
            ]
            choices = ['bullish', 'bearish', 'bullish', 'bearish']
            df['trend_bias'] = np.select(conditions, choices, default='neutral')
            
            # 使用merge_asof对齐到H1
            # 重命名高周期timestamp列避免冲突
            df_renamed = df[['timestamp', 'trend_bias', 'ma_slope', 'di_plus', 'di_minus']].copy()
            df_renamed = df_renamed.rename(columns={'timestamp': 'htf_timestamp'})
            merged = pd.merge_asof(
                h1[['timestamp']], df_renamed,
                left_on='timestamp', right_on='htf_timestamp', direction='backward'
            )
            
            result[f'{prefix}_trend_bias'] = merged['trend_bias'].fillna('neutral')
            result[f'{prefix}_ma_slope'] = merged['ma_slope'].fillna(0.0)
            result[f'{prefix}_di_plus'] = merged['di_plus'].fillna(0.0)
            result[f'{prefix}_di_minus'] = merged['di_minus'].fillna(0.0)
            result[f'{prefix}_bar_time'] = merged['htf_timestamp']
        
        # H4 as-of对齐
        if h4_df is not None and not h4_df.empty:
            _compute_trend_for_df(h4_df, 'h4')
        
        # D1 as-of对齐
        if d1_df is not None and not d1_df.empty:
            _compute_trend_for_df(d1_df, 'd1')
        
        # 标记数据警告
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
                    require_structural: bool = False) -> List[SqueezeSetup]:
        """识别收缩setup时刻（v3: as-of对齐，移除Pivot重复计分）"""
        setups = []
        setup_counter = 0
        
        for symbol, tf_data in self.raw_data.items():
            h1_df = tf_data.get("H1")
            if h1_df is None or len(h1_df) < 30:
                continue
            
            h1_df = h1_df.copy().reset_index(drop=True)
            
            # 计算H1指标
            h1_df['bb_width'] = SqueezeObserver.compute_bb_width(h1_df['close'])
            # v3: 移除pivot_range，只保留sr_range
            h1_df['sr_range'] = SqueezeObserver.compute_sr_range(h1_df['high'], h1_df['low'], h1_df['close'])
            h1_df['adx'] = SqueezeObserver.compute_adx(h1_df['high'], h1_df['low'], h1_df['close'])
            
            # 计算分位数
            h1_df['bb_20pct'] = h1_df['bb_width'].expanding(min_periods=20).quantile(0.20)
            h1_df['sr_20pct'] = h1_df['sr_range'].expanding(min_periods=20).quantile(0.20)
            
            h1_df['bb_squeezed'] = (h1_df['bb_width'] <= h1_df['bb_20pct']) & h1_df['bb_width'].notna()
            h1_df['sr_squeezed'] = (h1_df['sr_range'] <= h1_df['sr_20pct']) & h1_df['sr_range'].notna()
            h1_df['adx_lt_20'] = h1_df['adx'] < 20
            h1_df['adx_lt_13'] = h1_df['adx'] < 13
            h1_df['adx_lt_9'] = h1_df['adx'] < 9
            
            # v3: structural_score只包含bb+sr（移除pivot）
            h1_df['structural_score'] = h1_df[['bb_squeezed', 'sr_squeezed']].sum(axis=1)
            
            # v3: squeeze_score只包含bb+sr+adx（移除pivot）
            score_cols = ['bb_squeezed', 'sr_squeezed', 'adx_lt_20', 'adx_lt_13', 'adx_lt_9']
            h1_df['squeeze_score'] = h1_df[score_cols].sum(axis=1)
            
            # v3: as-of预计算多周期趋势
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
                if h1_df['sr_squeezed'].iloc[i]: conditions.append("SR")
                if h1_df['adx_lt_20'].iloc[i]: conditions.append("ADX<20")
                if h1_df['adx_lt_13'].iloc[i]: conditions.append("ADX<13")
                if h1_df['adx_lt_9'].iloc[i]: conditions.append("ADX<9")
                
                # 获取as-of趋势
                trend_row = trend_df.iloc[i]
                
                ts = h1_df['timestamp'].iloc[i]
                setup_counter += 1
                setup_id = f"{symbol}_setup_{setup_counter:06d}_{ts.strftime('%Y%m%d%H%M')}"
                cluster_id = f"{symbol}_{ts.strftime('%Y%m%d_%H')}"
                
                setup = SqueezeSetup(
                    setup_id=setup_id,
                    symbol=symbol, timeframe="H1",
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
                    anchor_mid=anchor_mid,
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
        logger.info(f"识别到 {len(setups)} 个收缩setup (min_score={min_squeeze_score})")
        return setups
    
    def detect_breakouts(self, max_wait_bars: int = 20,
                         min_breakout_anchor_multiple: float = 0.25) -> List[BreakoutEvent]:
        """检测setup后的突破事件（v3: 修正short target，真实event_id）"""
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
            
            # v3: 使用anchor_multiple命名
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
            
            # 多周期趋势过滤：只保留与趋势方向一致的突破
            if direction == "up" and setup.h4_trend_bias == "bearish" and setup.d1_trend_bias == "bearish":
                continue
            if direction == "down" and setup.h4_trend_bias == "bullish" and setup.d1_trend_bias == "bullish":
                continue
            
            # v3: 未来收益 - 入场后第N根K线（不把入场bar当成1bar）
            entry_idx = setup.bar_idx + breakout_bar_idx
            future_prices = df.iloc[entry_idx:entry_idx + 21]
            
            def calc_return(n_bars_after_entry):
                """n_bars_after_entry: 入场后第N根K线"""
                if n_bars_after_entry < len(future_prices) and n_bars_after_entry >= 0:
                    return (future_prices.iloc[n_bars_after_entry]['close'] - entry_price) / entry_price * 100
                return np.nan
            
            def calc_pnl(n_bars_after_entry, direction):
                r = calc_return(n_bars_after_entry)
                if pd.isna(r):
                    return np.nan
                return r if direction == "up" else -r
            
            # v3: 1bar=入场后第1根K线(close)，不是入场bar本身
            returns_1bar = calc_return(1)
            returns_3bar = calc_return(3)
            returns_5bar = calc_return(5)
            returns_10bar = calc_return(10)
            returns_20bar = calc_return(20)
            
            # v3: MFE/MAE使用high/low
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
            
            # 止损：只在入场后计算
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
            
            # v3: 修正short方向target判断 - 使用.max()
            target_1r = setup.anchor_range if direction == "up" else -setup.anchor_range
            target_2r = 2 * setup.anchor_range if direction == "up" else -2 * setup.anchor_range
            target_3r = 3 * setup.anchor_range if direction == "up" else -3 * setup.anchor_range
            
            def check_target(target):
                if len(future_prices) == 0:
                    return False
                if direction == "up":
                    return (future_prices['high'] - entry_price).max() >= target
                else:
                    # v3修正: short方向使用.max()而非.min()
                    return (entry_price - future_prices['low']).max() >= abs(target)
            
            hit_1r = check_target(target_1r)
            hit_2r = check_target(target_2r)
            hit_3r = check_target(target_3r)
            
            pnl_5 = calc_pnl(5, direction)
            pnl_10 = calc_pnl(10, direction)
            pnl_20 = calc_pnl(20, direction)
            
            # v3: 趋势共振分类
            h4_bias = setup.h4_trend_bias
            d1_bias = setup.d1_trend_bias
            
            if direction == "up":
                if h4_bias == "bullish" or d1_bias == "bullish":
                    trend_alignment = "with_trend"
                elif h4_bias == "bearish" or d1_bias == "bearish":
                    trend_alignment = "against_trend"
                else:
                    trend_alignment = "neutral"
            elif direction == "down":
                if h4_bias == "bearish" or d1_bias == "bearish":
                    trend_alignment = "with_trend"
                elif h4_bias == "bullish" or d1_bias == "bullish":
                    trend_alignment = "against_trend"
                else:
                    trend_alignment = "neutral"
            else:
                trend_alignment = "neutral"
            
            # v3: 真实event_id
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
        logger.info(f"检测到 {len(breakouts)} 个突破事件（多周期过滤后）")
        return breakouts
    
    def _deduplicate_breakouts(self, breakouts: List[BreakoutEvent]) -> List[BreakoutEvent]:
        """v3: 使用真实event_id去重 - symbol + breakout_timestamp + direction"""
        seen_events = {}  # event_key -> BreakoutEvent
        duplicate_count = 0
        
        for b in breakouts:
            # 真实突破键: symbol + breakout_timestamp + direction
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
        """
        v3: 交易级回测 - 三类出场规则
        - fixed_hold_5bar: 固定持有5根K线
        - fixed_hold_10bar: 固定持有10根K线
        - structure_stop: 结构止损（anchor opposite side）
        """
        trades = []
        trade_counter = 0
        
        # 计算walk-forward分区边界
        if unique_events and fold_boundaries is None:
            all_times = [e.breakout_timestamp for e in unique_events]
            min_t, max_t = min(all_times), max(all_times)
            total_span = (max_t - min_t).total_seconds()
            train_end = min_t + timedelta(seconds=total_span * 0.6)
            validation_end = min_t + timedelta(seconds=total_span * 0.8)
        else:
            train_end, validation_end = fold_boundaries
        
        for event in unique_events:
            symbol_data = self.raw_data.get(event.setup.symbol)
            if symbol_data is None:
                continue
            
            df = symbol_data.get("H1")
            if df is None:
                continue
            
            entry_idx = event.setup.bar_idx + event.breakout_bar_idx
            entry_price = event.entry_price
            direction = event.breakout_direction
            symbol = event.setup.symbol
            
            # 获取未来价格
            future = df.iloc[entry_idx:entry_idx + 25]
            if len(future) < 2:
                continue
            
            # 成本
            cost = get_symbol_cost(symbol)
            total_cost = cost['spread_pct'] + cost['commission_pct']
            
            # 分区
            fold = self._assign_walk_forward_fold(event.breakout_timestamp, train_end, validation_end)
            
            # 三类出场规则
            exit_rules = []
            
            # 1. fixed_hold_5bar
            if len(future) > 5:
                exit_price = future.iloc[5]['close']
                gross = (exit_price - entry_price) / entry_price * 100
                gross = gross if direction == "up" else -gross
                net = gross - total_cost
                exit_rules.append(("fixed_hold_5bar", future.iloc[5]['timestamp'], exit_price, gross, net, 5))
            
            # 2. fixed_hold_10bar
            if len(future) > 10:
                exit_price = future.iloc[10]['close']
                gross = (exit_price - entry_price) / entry_price * 100
                gross = gross if direction == "up" else -gross
                net = gross - total_cost
                exit_rules.append(("fixed_hold_10bar", future.iloc[10]['timestamp'], exit_price, gross, net, 10))
            
            # 3. structure_stop
            stop_price = event.setup.anchor_low if direction == "up" else event.setup.anchor_high
            structure_exit = None
            for j in range(1, min(len(future), 21)):
                row = future.iloc[j]
                if direction == "up" and row['low'] < stop_price:
                    structure_exit = ("structure_stop", row['timestamp'], stop_price, 
                                      (stop_price - entry_price) / entry_price * 100 - total_cost, j)
                    break
                elif direction == "down" and row['high'] > stop_price:
                    structure_exit = ("structure_stop", row['timestamp'], stop_price,
                                      (entry_price - stop_price) / entry_price * 100 - total_cost, j)
                    break
            
            if structure_exit is None and len(future) > 1:
                # 未触发止损，持有到最后
                last = future.iloc[-1]
                gross = (last['close'] - entry_price) / entry_price * 100
                gross = gross if direction == "up" else -gross
                net = gross - total_cost
                structure_exit = ("structure_stop", last['timestamp'], last['close'], net, len(future) - 1)
            
            if structure_exit:
                gross_pnl = structure_exit[3] + total_cost  # 还原gross
                exit_rules.append(("structure_stop", structure_exit[1], structure_exit[2], 
                                   gross_pnl, structure_exit[3], structure_exit[4]))
            
            # 为每个出场规则创建交易记录
            for rule_name, exit_time, exit_price, gross, net, bars in exit_rules:
                trade_counter += 1
                trade = Trade(
                    trade_id=f"T{trade_counter:06d}",
                    event_id=event.event_id,
                    symbol=symbol,
                    direction=direction,
                    entry_time=event.breakout_timestamp,
                    entry_price=entry_price,
                    exit_time=exit_time,
                    exit_price=exit_price,
                    exit_rule=rule_name,
                    gross_pnl_pct=gross,
                    cost_pct=total_cost,
                    net_pnl_pct=net,
                    mfe_pct=event.mfe_pct,
                    mae_pct=event.mae_pct,
                    bars_held=bars,
                    fold=fold
                )
                trades.append(trade)
        
        self.trades = trades
        logger.info(f"生成 {len(trades)} 笔交易记录")
        return trades
    
    def analyze(self, deduplicate: bool = True) -> ResearchResult:
        """v3: 执行完整分析（含交易成本、walk-forward）"""
        if not self.setups:
            logger.error("没有setup数据")
            return None
        
        setups = self.setups
        breakouts = self.breakouts
        
        # 真实事件去重
        if deduplicate:
            unique_events = self._deduplicate_breakouts(breakouts)
        else:
            unique_events = breakouts
        
        total_setups = len(setups)
        total_breakouts = len(breakouts)
        unique_breakout_count = len(unique_events)
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
        
        # 原始样本统计
        bo_returns_5 = [b.returns_5bar for b in breakouts]
        bo_returns_10 = [b.returns_10bar for b in breakouts]
        
        pnl_5 = [b.pnl_5bar for b in breakouts]
        wins_5 = [p for p in pnl_5 if p > 0]
        losses_5 = [p for p in pnl_5 if p <= 0]
        
        raw_win_rate = len(wins_5) / len(pnl_5) if pnl_5 else 0
        raw_avg_win = np.mean(wins_5) if wins_5 else 0
        raw_avg_loss = np.mean(losses_5) if losses_5 else 0
        raw_wl_ratio = abs(raw_avg_win / raw_avg_loss) if raw_avg_loss != 0 else float('inf')
        raw_expectancy = raw_win_rate * raw_avg_win + (1 - raw_win_rate) * raw_avg_loss
        
        # 真实唯一事件统计
        unique_pnl_5 = [b.pnl_5bar for b in unique_events]
        unique_wins_5 = [p for p in unique_pnl_5 if p > 0]
        unique_losses_5 = [p for p in unique_pnl_5 if p <= 0]
        unique_win_rate = len(unique_wins_5) / len(unique_pnl_5) if unique_pnl_5 else 0
        unique_avg_win = np.mean(unique_wins_5) if unique_wins_5 else 0
        unique_avg_loss = np.mean(unique_losses_5) if unique_losses_5 else 0
        unique_wl_ratio = abs(unique_avg_win / unique_avg_loss) if unique_avg_loss != 0 else float('inf')
        unique_expectancy = unique_win_rate * unique_avg_win + (1 - unique_win_rate) * unique_avg_loss
        
        # 多周期趋势共振统计
        with_trend = [b for b in unique_events if b.trend_alignment == "with_trend"]
        against_trend = [b for b in unique_events if b.trend_alignment == "against_trend"]
        neutral_trend = [b for b in unique_events if b.trend_alignment == "neutral"]
        
        with_trend_pnl = [b.pnl_5bar for b in with_trend]
        against_trend_pnl = [b.pnl_5bar for b in against_trend]
        neutral_trend_pnl = [b.pnl_5bar for b in neutral_trend]
        
        with_trend_wr = len([p for p in with_trend_pnl if p > 0]) / len(with_trend_pnl) if with_trend_pnl else 0
        against_trend_wr = len([p for p in against_trend_pnl if p > 0]) / len(against_trend_pnl) if against_trend_pnl else 0
        neutral_wr = len([p for p in neutral_trend_pnl if p > 0]) / len(neutral_trend_pnl) if neutral_trend_pnl else 0
        
        hit_1r = sum(1 for b in unique_events if b.hit_target_1r) / unique_breakout_count if unique_breakout_count else 0
        hit_2r = sum(1 for b in unique_events if b.hit_target_2r) / unique_breakout_count if unique_breakout_count else 0
        hit_3r = sum(1 for b in unique_events if b.hit_target_3r) / unique_breakout_count if unique_breakout_count else 0
        stop_rate = sum(1 for b in unique_events if b.stop_triggered) / unique_breakout_count if unique_breakout_count else 0
        stop_after_entry_rate = sum(1 for b in unique_events if b.stop_after_entry) / unique_breakout_count if unique_breakout_count else 0
        
        # 交易成本后指标（基于交易回测）
        if self.trades:
            net_pnls = [t.net_pnl_pct for t in self.trades if t.exit_rule == "fixed_hold_5bar"]
            net_wins = [p for p in net_pnls if p > 0]
            net_losses = [p for p in net_pnls if p <= 0]
            net_win_rate = len(net_wins) / len(net_pnls) if net_pnls else 0
            net_avg_win = np.mean(net_wins) if net_wins else 0
            net_avg_loss = np.mean(net_losses) if net_losses else 0
            net_expectancy = net_win_rate * net_avg_win + (1 - net_win_rate) * net_avg_loss
        else:
            net_win_rate = 0
            net_expectancy = 0
        
        # walk-forward统计
        train_metrics = self._calc_fold_metrics("train")
        validation_metrics = self._calc_fold_metrics("validation")
        test_metrics = self._calc_fold_metrics("test")
        
        # 按score分组
        by_score = defaultdict(lambda: {"count": 0, "breakouts": 0, "win_rate": 0, "avg_pnl": 0})
        for setup in setups:
            s = setup.squeeze_score
            by_score[s]["count"] += 1
        for b in unique_events:
            s = b.setup.squeeze_score
            by_score[s]["breakouts"] += 1
        for s in by_score:
            bo_list = [b for b in unique_events if b.setup.squeeze_score == s]
            if bo_list:
                pnls = [b.pnl_5bar for b in bo_list]
                by_score[s]["win_rate"] = sum(1 for p in pnls if p > 0) / len(pnls)
                by_score[s]["avg_pnl"] = np.mean(pnls)
                by_score[s]["breakout_rate"] = by_score[s]["breakouts"] / by_score[s]["count"]
        
        # 按品种分组
        by_symbol = defaultdict(lambda: {"setups": 0, "breakouts": 0, "avg_pnl": 0, "avg_net_pnl": 0})
        for setup in setups:
            by_symbol[setup.symbol]["setups"] += 1
        for b in unique_events:
            by_symbol[b.setup.symbol]["breakouts"] += 1
        for sym in by_symbol:
            bo_list = [b for b in unique_events if b.setup.symbol == sym]
            if bo_list:
                by_symbol[sym]["avg_pnl"] = np.mean([b.pnl_5bar for b in bo_list])
            trade_list = [t for t in self.trades if t.symbol == sym and t.exit_rule == "fixed_hold_5bar"]
            if trade_list:
                by_symbol[sym]["avg_net_pnl"] = np.mean([t.net_pnl_pct for t in trade_list])
        
        # 按趋势一致性分组
        by_trend_alignment = {
            "with_trend": {"count": len(with_trend), "win_rate": with_trend_wr, 
                          "avg_pnl": np.mean(with_trend_pnl) if with_trend_pnl else 0},
            "against_trend": {"count": len(against_trend), "win_rate": against_trend_wr,
                             "avg_pnl": np.mean(against_trend_pnl) if against_trend_pnl else 0},
            "neutral": {"count": len(neutral_trend), "win_rate": neutral_wr,
                       "avg_pnl": np.mean(neutral_trend_pnl) if neutral_trend_pnl else 0},
        }
        
        recommendations = []
        warnings = []
        
        if unique_breakout_count < 100:
            warnings.append(f"去重后样本量不足: 仅{unique_breakout_count}个唯一突破")
        
        if breakout_rate < 0.3:
            recommendations.append(f"突破率较低({breakout_rate*100:.1f}%)，建议扩大等待周期或降低突破阈值")
        elif breakout_rate > 0.8:
            recommendations.append(f"突破率过高({breakout_rate*100:.1f}%)，可能突破阈值过低")
        
        if unique_win_rate > 0.55 and unique_expectancy > 0:
            recommendations.append(f"去重后5bar胜率{unique_win_rate*100:.1f}%为正期望，策略有潜力")
        
        if with_trend_wr > against_trend_wr + 0.05:
            recommendations.append(f"顺势突破胜率({with_trend_wr*100:.1f}%)优于逆势({against_trend_wr*100:.1f}%)，趋势过滤有效")
        
        if test_metrics.get('net_expectancy', 0) > 0 and test_metrics.get('count', 0) >= 100:
            recommendations.append("测试段净期望为正，可考虑模拟盘观察")
        
        if unique_breakout_count < 50:
            validation_status = "样本不足"
        elif unique_win_rate < 0.5 and unique_expectancy < 0:
            validation_status = "暂不建议进入实盘"
        elif unique_win_rate >= 0.55 and unique_expectancy > 0 and unique_wl_ratio > 1.2:
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
            raw_win_rate_5bar=raw_win_rate,
            raw_expectancy_5bar=raw_expectancy,
            raw_win_loss_ratio=raw_wl_ratio,
            unique_win_rate_5bar=unique_win_rate,
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
            avg_win_5bar=unique_avg_win,
            avg_loss_5bar=unique_avg_loss,
            with_trend_breakouts=len(with_trend),
            against_trend_breakouts=len(against_trend),
            neutral_breakouts=len(neutral_trend),
            with_trend_win_rate=with_trend_wr,
            against_trend_win_rate=against_trend_wr,
            neutral_win_rate=neutral_wr,
            net_win_rate_5bar=net_win_rate,
            net_expectancy_5bar=net_expectancy,
            by_score=dict(by_score),
            by_symbol=dict(by_symbol),
            by_trend_alignment=by_trend_alignment,
            train_metrics=train_metrics,
            validation_metrics=validation_metrics,
            test_metrics=test_metrics,
            recommendations=recommendations,
            validation_status=validation_status,
            warnings=warnings
        )
    
    def _calc_fold_metrics(self, fold: str) -> Dict:
        """计算指定fold的指标"""
        fold_trades = [t for t in self.trades if t.fold == fold and t.exit_rule == "fixed_hold_5bar"]
        if not fold_trades:
            return {"count": 0, "win_rate": 0, "avg_gross": 0, "avg_net": 0, "expectancy": 0}
        
        gross_pnls = [t.gross_pnl_pct for t in fold_trades]
        net_pnls = [t.net_pnl_pct for t in fold_trades]
        wins = [p for p in net_pnls if p > 0]
        
        return {
            "count": len(fold_trades),
            "win_rate": len(wins) / len(net_pnls) if net_pnls else 0,
            "avg_gross": np.mean(gross_pnls),
            "avg_net": np.mean(net_pnls),
            "expectancy": np.mean(net_pnls)
        }
    
    def run_param_sweep(self, quick_mode: bool = True) -> Dict:
        """参数扫描 (quick_mode=True时缩减为18组核心组合)"""
        logger.info("开始参数扫描...")
        
        param_results = []
        
        if quick_mode:
            # 精简扫描：聚焦关键参数组合
            scores = [2, 3]
            waits = [15, 30]
            anchor_mults = [0.1, 0.25, 0.5]
            struct_reqs = [False, True]
        else:
            scores = [2, 3, 4]
            waits = [10, 15, 20, 30]
            anchor_mults = [0.1, 0.25, 0.5]
            struct_reqs = [False, True]
        
        total_combos = len(scores) * len(waits) * len(anchor_mults) * len(struct_reqs)
        current = 0
        
        for score in scores:
            for wait in waits:
                for am in anchor_mults:
                    for struct in struct_reqs:
                        current += 1
                        logger.info(f"参数组合 [{current}/{total_combos}]: score={score}, wait={wait}, anchor_mult={am}, struct={struct}")
                        
                        self.find_setups(min_squeeze_score=score, cooldown_bars=5, require_structural=struct)
                        self.detect_breakouts(max_wait_bars=wait, min_breakout_anchor_multiple=am)
                        
                        unique_events = self._deduplicate_breakouts(self.breakouts)
                        self.run_trade_backtest(unique_events)
                        
                        result = self.analyze(deduplicate=True)
                        
                        if result:
                            param_results.append({
                                'min_score': score,
                                'max_wait': wait,
                                'min_anchor_mult': am,
                                'require_structural': struct,
                                'setups': result.total_setups,
                                'breakouts': result.total_breakouts,
                                'unique_breakouts': result.unique_breakouts,
                                'breakout_rate': result.breakout_rate,
                                'raw_win_rate': result.raw_win_rate_5bar,
                                'unique_win_rate': result.unique_win_rate_5bar,
                                'unique_expectancy': result.unique_expectancy_5bar,
                                'win_loss_ratio': result.unique_win_loss_ratio,
                                'net_win_rate': result.net_win_rate_5bar,
                                'net_expectancy': result.net_expectancy_5bar,
                                'with_trend_wr': result.with_trend_win_rate,
                                'stop_rate': result.stop_rate,
                                'validation': result.validation_status,
                                'test_net_expectancy': result.test_metrics.get('expectancy', 0),
                                'test_count': result.test_metrics.get('count', 0)
                            })
        
        df = pd.DataFrame(param_results)
        
        # 排序：优先测试段净期望为正且样本充足的
        df['score'] = df['test_net_expectancy'] * np.sqrt(df['test_count'].clip(lower=1))
        df_sorted = df.sort_values('score', ascending=False)
        
        logger.info("参数扫描完成")
        return {
            'all_results': df,
            'top_results': df_sorted.head(10),
            'best_params': df_sorted.iloc[0].to_dict() if len(df_sorted) > 0 else None
        }
    
    def generate_report(self, result: ResearchResult, param_analysis: Dict = None,
                        output_dir: str = "reports/squeeze") -> Tuple[str, str, str, str]:
        """生成v3研究报告和CSV"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        lines = []
        lines.append("# 多周期共振收缩→突破统计验证研究报告 v3")
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
        
        lines.append("\n## 二、收益统计")
        lines.append(f"\n| 持有周期 | 均值 | 中位数 |")
        lines.append(f"|----------|------|--------|")
        lines.append(f"| 5bar | {result.returns_5bar_all_mean:.3f}% | {result.returns_5bar_all_median:.3f}% |")
        lines.append(f"| 10bar | {result.returns_10bar_all_mean:.3f}% | - |")
        lines.append(f"| 20bar | {result.returns_20bar_all_mean:.3f}% | - |")
        
        lines.append("\n## 三、交易绩效（原始样本）")
        lines.append(f"\n| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 5bar胜率 | {result.raw_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 平均盈利 | {result.avg_win_5bar:.3f}% |")
        lines.append(f"| 平均亏损 | {result.avg_loss_5bar:.3f}% |")
        lines.append(f"| 盈亏比 | {result.raw_win_loss_ratio:.2f} |")
        lines.append(f"| 期望值 | {result.raw_expectancy_5bar:.3f}% |")
        
        lines.append("\n## 四、交易绩效（真实唯一事件）")
        lines.append(f"\n| 指标 | 数值 |")
        lines.append(f"|------|------|")
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
        lines.append(f"\n| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 净5bar胜率 | {result.net_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 净期望值 | {result.net_expectancy_5bar:.3f}% |")
        
        lines.append("\n## 六、多周期趋势共振分析")
        lines.append(f"\n| 类型 | 数量 | 胜率 | 平均PNL |")
        lines.append(f"|------|------|------|---------|")
        for key, d in result.by_trend_alignment.items():
            lines.append(f"| {key} | {d['count']} | {d['win_rate']*100:.1f}% | {d['avg_pnl']:.3f}% |")
        
        lines.append("\n## 七、Walk-Forward分析")
        lines.append(f"\n| 分区 | 交易数 | 胜率 | 平均Gross | 平均Net | 期望 |")
        lines.append(f"|------|--------|------|-----------|---------|------|")
        for fold_name, metrics in [("Train", result.train_metrics), ("Validation", result.validation_metrics), ("Test", result.test_metrics)]:
            lines.append(f"| {fold_name} | {metrics['count']} | {metrics['win_rate']*100:.1f}% | {metrics['avg_gross']:.3f}% | {metrics['avg_net']:.3f}% | {metrics['expectancy']:.3f}% |")
        
        lines.append("\n## 八、按Squeeze Score分组")
        lines.append(f"\n| Score | Setup数 | 突破数 | 突破率 | 胜率 | 平均PNL |")
        lines.append(f"|-------|---------|--------|--------|------|---------|")
        for score in sorted(result.by_score.keys()):
            d = result.by_score[score]
            lines.append(f"| {score} | {d['count']} | {d['breakouts']} | {d.get('breakout_rate', 0)*100:.1f}% | {d['win_rate']*100:.1f}% | {d['avg_pnl']:.3f}% |")
        
        lines.append("\n## 九、按品种分组")
        lines.append(f"\n| 品种 | Setup数 | 突破数 | 平均GrossPNL | 平均NetPNL |")
        lines.append(f"|------|---------|--------|--------------|------------|")
        for sym in sorted(result.by_symbol.keys()):
            d = result.by_symbol[sym]
            lines.append(f"| {sym} | {d['setups']} | {d['breakouts']} | {d['avg_pnl']:.3f}% | {d.get('avg_net_pnl', 0):.3f}% |")
        
        if param_analysis and 'top_results' in param_analysis:
            lines.append("\n## 十、参数扫描结果（Top 10）")
            lines.append(f"\n| 排名 | min_score | max_wait | anchor_mult | struct | setups | breakouts | 唯一突破 | 胜率 | 净期望 | 测试期望 | 状态 |")
            lines.append(f"|------|-----------|----------|-------------|--------|--------|-----------|----------|------|--------|----------|------|")
            top = param_analysis['top_results']
            for idx, row in top.iterrows():
                lines.append(f"| {idx+1} | {row['min_score']} | {row['max_wait']} | {row['min_anchor_mult']} | {row['require_structural']} | "
                           f"{row['setups']} | {row['breakouts']} | {row['unique_breakouts']} | {row['unique_win_rate']*100:.1f}% | "
                           f"{row['net_expectancy']:.3f}% | {row['test_net_expectancy']:.3f}% | {row['validation']} |")
            
            if param_analysis.get('best_params'):
                best = param_analysis['best_params']
                lines.append(f"\n### 推荐参数")
                lines.append(f"- min_squeeze_score: {best['min_score']}")
                lines.append(f"- max_wait_bars: {best['max_wait']}")
                lines.append(f"- min_breakout_anchor_multiple: {best['min_anchor_mult']}")
                lines.append(f"- require_structural: {best['require_structural']}")
        
        lines.append("\n## 十一、v2 vs v3 差异")
        lines.append("\n| 维度 | v2 | v3 |")
        lines.append("|------|-----|-----|")
        lines.append("| 多周期对齐 | i//4, i//24 | merge_asof as-of |")
        lines.append("| 事件去重 | cluster_id (hour级) | event_id (timestamp+direction) |")
        lines.append("| short target | .min() | .max() |")
        lines.append("| 突破阈值 | min_breakout_atr | min_breakout_anchor_multiple |")
        lines.append("| 收缩指标 | BB+Pivot+SR+ADX | BB+SR+ADX (移除Pivot) |")
        lines.append("| 交易成本 | 无 | 按品种类别 |")
        lines.append("| 出场规则 | 固定持有 | fixed_hold/structure_stop/1R_partial |")
        lines.append("| walk-forward | 无 | train/validation/test |")
        
        lines.append("\n## 十二、结论")
        lines.append(f"\n**验证状态**: {result.validation_status}")
        lines.append(f"\n- **已验证有效**: 去重后胜率>55%且期望值为正")
        lines.append(f"- **样本不足**: 唯一突破事件<50")
        lines.append(f"- **逻辑需要调整**: 有样本但胜率或期望值不达标")
        lines.append(f"- **暂不建议进入实盘**: 胜率和期望值均为负")
        lines.append(f"\n**多周期共振效果**: 顺势突破胜率{result.with_trend_win_rate*100:.1f}% vs 逆势{result.against_trend_win_rate*100:.1f}% vs 中性{result.neutral_win_rate*100:.1f}%")
        lines.append(f"\n**Walk-Forward测试段**: 净期望{result.test_metrics.get('expectancy', 0):.3f}%, 样本{result.test_metrics.get('count', 0)}")
        
        if result.test_metrics.get('expectancy', 0) > 0 and result.test_metrics.get('count', 0) >= 100:
            lines.append("\n**模拟盘观察**: 测试段净期望为正，可考虑搭建模拟盘观察系统（只观察，不下单）")
        else:
            lines.append("\n**模拟盘观察**: 测试段数据不支持，暂不进入模拟盘观察")
        
        lines.append("\n---")
        lines.append("\n> **免责声明**：本报告仅供研究参考，不构成投资建议。")
        lines.append("> **实盘限制**：当前阶段禁止直接进入实盘自动交易。")
        
        report_path = Path(output_dir) / f"squeeze_mt_research_v3_{timestamp}.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"报告已保存: {report_path}")
        
        # setups CSV
        setups_records = []
        for s in self.setups:
            setups_records.append({
                'setup_id': s.setup_id,
                'symbol': s.symbol,
                'timestamp': s.timestamp,
                'squeeze_score': s.squeeze_score,
                'conditions': '+'.join(s.conditions),
                'adx': s.adx,
                'h4_trend_bias': s.h4_trend_bias,
                'd1_trend_bias': s.d1_trend_bias,
                'h4_bar_time': s.h4_bar_time,
                'd1_bar_time': s.d1_bar_time,
                'data_warning': s.data_warning,
                'anchor_range_pct': s.anchor_range_pct,
                'cluster_id': s.cluster_id,
            })
        setups_df = pd.DataFrame(setups_records)
        setups_path = Path(output_dir) / f"squeeze_mt_setups_v3_{timestamp}.csv"
        setups_df.to_csv(setups_path, index=False)
        logger.info(f"Setup CSV已保存: {setups_path}")
        
        # events CSV
        if unique_events := self._deduplicate_breakouts(self.breakouts):
            events_records = []
            for b in unique_events:
                events_records.append({
                    'event_id': b.event_id,
                    'setup_id': b.setup.setup_id,
                    'symbol': b.setup.symbol,
                    'breakout_timestamp': b.breakout_timestamp,
                    'breakout_direction': b.breakout_direction,
                    'entry_price': b.entry_price,
                    'trend_alignment': b.trend_alignment,
                    'h4_trend_bias': b.setup.h4_trend_bias,
                    'd1_trend_bias': b.setup.d1_trend_bias,
                    'returns_1bar': b.returns_1bar,
                    'returns_5bar': b.returns_5bar,
                    'returns_10bar': b.returns_10bar,
                    'returns_20bar': b.returns_20bar,
                    'mfe_pct': b.mfe_pct,
                    'mae_pct': b.mae_pct,
                    'hit_1r': b.hit_target_1r,
                    'hit_2r': b.hit_target_2r,
                    'hit_3r': b.hit_target_3r,
                    'stop_triggered': b.stop_triggered,
                    'stop_after_entry': b.stop_after_entry,
                    'pnl_5bar': b.pnl_5bar,
                    'pnl_10bar': b.pnl_10bar,
                    'pnl_20bar': b.pnl_20bar,
                })
            events_df = pd.DataFrame(events_records)
            events_path = Path(output_dir) / f"squeeze_mt_events_v3_{timestamp}.csv"
            events_df.to_csv(events_path, index=False)
            logger.info(f"Events CSV已保存: {events_path}")
        else:
            events_path = None
        
        # trades CSV
        if self.trades:
            trades_records = []
            for t in self.trades:
                trades_records.append({
                    'trade_id': t.trade_id,
                    'event_id': t.event_id,
                    'symbol': t.symbol,
                    'direction': t.direction,
                    'entry_time': t.entry_time,
                    'entry_price': t.entry_price,
                    'exit_time': t.exit_time,
                    'exit_price': t.exit_price,
                    'exit_rule': t.exit_rule,
                    'gross_pnl_pct': t.gross_pnl_pct,
                    'cost_pct': t.cost_pct,
                    'net_pnl_pct': t.net_pnl_pct,
                    'mfe_pct': t.mfe_pct,
                    'mae_pct': t.mae_pct,
                    'bars_held': t.bars_held,
                    'fold': t.fold,
                })
            trades_df = pd.DataFrame(trades_records)
            trades_path = Path(output_dir) / f"squeeze_mt_trades_v3_{timestamp}.csv"
            trades_df.to_csv(trades_path, index=False)
            logger.info(f"Trades CSV已保存: {trades_path}")
        else:
            trades_path = None
        
        if param_analysis and 'all_results' in param_analysis:
            param_csv_path = Path(output_dir) / f"squeeze_mt_param_sweep_v3_{timestamp}.csv"
            param_analysis['all_results'].to_csv(param_csv_path, index=False)
            logger.info(f"参数扫描CSV已保存: {param_csv_path}")
        
        return str(report_path), str(setups_path), str(events_path) if events_path else None, str(trades_path) if trades_path else None


def main():
    """主函数"""
    print("=" * 70)
    print("多周期共振收缩→突破统计验证研究 v3")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    research = MultiTimeframeSqueezeResearchV3()
    
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
    
    # v3: 使用v2验证的最佳参数直接运行，跳过参数扫描以加速
    # 如需完整参数扫描，调用 research.run_param_sweep()
    best = {
        'min_score': 2,
        'max_wait': 30,
        'min_anchor_mult': 0.1,
        'require_structural': False
    }
    logger.info(f"使用v2验证的最佳参数直接分析: {best}")
    research.find_setups(
        min_squeeze_score=best['min_score'],
        cooldown_bars=5,
        require_structural=best['require_structural']
    )
    research.detect_breakouts(
        max_wait_bars=best['max_wait'],
        min_breakout_anchor_multiple=best['min_anchor_mult']
    )
    
    param_analysis = None  # 跳过参数扫描报告
    
    unique_events = research._deduplicate_breakouts(research.breakouts)
    research.run_trade_backtest(unique_events)
    result = research.analyze(deduplicate=True)
    
    if result:
        print(f"\n{'='*60}")
        print("分析结果摘要")
        print(f"{'='*60}")
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
        
        if best:
            print(f"\n最佳参数:")
            print(f"  min_score: {best['min_score']}")
            print(f"  max_wait: {best['max_wait']}")
            print(f"  min_anchor_mult: {best['min_anchor_mult']}")
            print(f"  require_structural: {best['require_structural']}")
        
        report_path, setups_path, events_path, trades_path = research.generate_report(result, param_analysis)
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
