"""
收缩→突破统计验证研究

目标：基于MT5原始OHLCV数据，验证"收缩带来扩张"假设的有效性

研究步骤：
1. 从MT5获取多品种多周期OHLCV数据
2. 计算收缩指标，识别收缩setup时刻
3. 检测收缩后的突破事件（价格突破收缩锚定区间）
4. 统计突破成功率、收益分布、最大回撤
5. 分析不同收缩条件组合的效果差异
6. 给出参数建议（基于样本统计）

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

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "python"))

from analytics.squeeze_observer import SqueezeObserver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("squeeze_research")


# MT5品种映射
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
    
    # 收缩时刻指标
    bb_width: float
    pivot_range: float
    sr_range: float
    adx: float
    state_is_zero: bool
    
    # 收缩时刻价格
    open: float
    high: float
    low: float
    close: float
    
    # 锚定区间（收缩前20根K线）
    anchor_high: float
    anchor_low: float
    anchor_range: float
    anchor_range_pct: float
    anchor_mid: float


@dataclass
class BreakoutEvent:
    """突破事件"""
    setup: SqueezeSetup
    
    # 突破信息
    breakout_timestamp: datetime
    breakout_bar_idx: int
    breakout_direction: str
    
    # 突破确认价格
    entry_price: float
    breakout_level: float
    
    # 未来收益（从entry_price起算，百分比）
    returns_1bar: float
    returns_3bar: float
    returns_5bar: float
    returns_10bar: float
    returns_20bar: float
    
    # 风险指标
    max_drawdown_pct: float
    max_runup_pct: float
    
    # 是否达到目标收益
    hit_target_1r: bool
    hit_target_2r: bool
    hit_target_3r: bool
    
    # 止损
    stop_triggered: bool
    stop_bar_idx: Optional[int]
    stop_price: Optional[float]
    
    # 实际盈亏
    pnl_5bar: float
    pnl_10bar: float
    pnl_20bar: float


@dataclass
class ResearchResult:
    """研究结果"""
    total_setups: int
    total_breakouts: int
    breakout_rate: float
    no_breakout_count: int
    up_breakouts: int
    down_breakouts: int
    direction_balance: float
    
    returns_5bar_all_mean: float
    returns_5bar_all_median: float
    returns_10bar_all_mean: float
    returns_10bar_all_median: float
    returns_20bar_all_mean: float
    returns_20bar_all_median: float
    
    returns_5bar_bo_mean: float
    returns_5bar_bo_median: float
    returns_10bar_bo_mean: float
    returns_10bar_bo_median: float
    
    hit_1r_rate: float
    hit_2r_rate: float
    hit_3r_rate: float
    stop_rate: float
    
    win_rate_5bar: float
    win_rate_10bar: float
    avg_win_5bar: float
    avg_loss_5bar: float
    win_loss_ratio_5bar: float
    expectancy_5bar: float
    
    by_score: Dict
    by_conditions: Dict
    by_symbol: Dict
    by_adx: Dict
    
    recommendations: List[str]
    validation_status: str
    warnings: List[str]
    
    # 新增：按参数组合分析
    param_analysis: Dict = field(default_factory=dict)


class SqueezeBreakoutResearch:
    """收缩→突破统计验证引擎"""
    
    def __init__(self):
        self.observer = SqueezeObserver()
        self.setups: List[SqueezeSetup] = []
        self.breakouts: List[BreakoutEvent] = []
        self.raw_data: Dict[str, pd.DataFrame] = {}
        
    def fetch_data(self, symbols: Dict[str, str], timeframe: str = "H1",
                   lookback_days: int = 180) -> Dict[str, pd.DataFrame]:
        """从MT5获取数据"""
        data = {}
        for std_name, mt5_name in symbols.items():
            try:
                logger.info(f"获取数据: {std_name} ({mt5_name}) {timeframe}")
                df = self.observer._fetch_from_mt5(mt5_name, timeframe, lookback_days)
                if not df.empty and len(df) >= 50:
                    data[std_name] = df
                    logger.info(f"  成功: {len(df)}条")
                else:
                    logger.warning(f"  数据不足: {len(df)}条")
            except Exception as e:
                logger.error(f"  失败: {e}")
        self.raw_data = data
        logger.info(f"数据获取完成: {len(data)}个品种")
        return data
    
    def find_setups(self, min_squeeze_score: int = 2,
                    cooldown_bars: int = 5,
                    require_structural: bool = False) -> List[SqueezeSetup]:
        """
        识别收缩setup时刻
        
        Args:
            min_squeeze_score: 最小收缩分数
            cooldown_bars: 去重间隔
            require_structural: 是否要求至少包含结构收缩（BB/Pivot/SR）
        """
        setups = []
        
        for symbol, df in self.raw_data.items():
            if len(df) < 30:
                continue
            
            df = df.copy().reset_index(drop=True)
            
            # 计算指标
            df['bb_width'] = SqueezeObserver.compute_bb_width(df['close'])
            df['pivot_range'] = SqueezeObserver.compute_pivot_range(df['high'], df['low'], df['close'])
            df['sr_range'] = SqueezeObserver.compute_sr_range(df['high'], df['low'], df['close'])
            df['adx'] = SqueezeObserver.compute_adx(df['high'], df['low'], df['close'])
            
            # 计算分位数
            df['bb_20pct'] = df['bb_width'].expanding(min_periods=20).quantile(0.20)
            df['pivot_20pct'] = df['pivot_range'].expanding(min_periods=20).quantile(0.20)
            df['sr_20pct'] = df['sr_range'].expanding(min_periods=20).quantile(0.20)
            
            df['bb_squeezed'] = (df['bb_width'] <= df['bb_20pct']) & df['bb_width'].notna()
            df['pivot_squeezed'] = (df['pivot_range'] <= df['pivot_20pct']) & df['pivot_range'].notna()
            df['sr_squeezed'] = (df['sr_range'] <= df['sr_20pct']) & df['sr_range'].notna()
            df['adx_lt_20'] = df['adx'] < 20
            df['adx_lt_13'] = df['adx'] < 13
            df['adx_lt_9'] = df['adx'] < 9
            
            # 结构收缩分数（BB+Pivot+SR）
            df['structural_score'] = df[['bb_squeezed', 'pivot_squeezed', 'sr_squeezed']].sum(axis=1)
            
            # 总分数
            score_cols = ['bb_squeezed', 'pivot_squeezed', 'sr_squeezed', 
                          'adx_lt_20', 'adx_lt_13', 'adx_lt_9']
            df['squeeze_score'] = df[score_cols].sum(axis=1)
            
            last_setup_idx = -cooldown_bars - 1
            
            for i in range(30, len(df)):
                if df['squeeze_score'].iloc[i] < min_squeeze_score:
                    continue
                
                # 要求结构收缩
                if require_structural and df['structural_score'].iloc[i] < 1:
                    continue
                
                if i - last_setup_idx <= cooldown_bars:
                    continue
                
                anchor_start = max(0, i - 20)
                anchor_window = df.iloc[anchor_start:i]
                
                if len(anchor_window) < 10:
                    continue
                
                anchor_high = anchor_window['high'].max()
                anchor_low = anchor_window['low'].min()
                anchor_range = anchor_high - anchor_low
                anchor_mid = (anchor_high + anchor_low) / 2
                
                if anchor_range <= 0:
                    continue
                
                close = df['close'].iloc[i]
                anchor_range_pct = anchor_range / close * 100
                
                conditions = []
                if df['bb_squeezed'].iloc[i]: conditions.append("BB")
                if df['pivot_squeezed'].iloc[i]: conditions.append("Pivot")
                if df['sr_squeezed'].iloc[i]: conditions.append("SR")
                if df['adx_lt_20'].iloc[i]: conditions.append("ADX<20")
                if df['adx_lt_13'].iloc[i]: conditions.append("ADX<13")
                if df['adx_lt_9'].iloc[i]: conditions.append("ADX<9")
                
                setup = SqueezeSetup(
                    symbol=symbol, timeframe="H1",
                    timestamp=df['timestamp'].iloc[i], bar_idx=i,
                    squeeze_score=int(df['squeeze_score'].iloc[i]),
                    conditions=conditions,
                    bb_width=df['bb_width'].iloc[i],
                    pivot_range=df['pivot_range'].iloc[i],
                    sr_range=df['sr_range'].iloc[i],
                    adx=df['adx'].iloc[i],
                    state_is_zero=False,
                    open=df['open'].iloc[i], high=df['high'].iloc[i],
                    low=df['low'].iloc[i], close=close,
                    anchor_high=anchor_high, anchor_low=anchor_low,
                    anchor_range=anchor_range, anchor_range_pct=anchor_range_pct,
                    anchor_mid=anchor_mid
                )
                setups.append(setup)
                last_setup_idx = i
        
        self.setups = setups
        logger.info(f"识别到 {len(setups)} 个收缩setup (min_score={min_squeeze_score}, structural={require_structural})")
        return setups
    
    def detect_breakouts(self, max_wait_bars: int = 20,
                         min_breakout_atr: float = 0.25) -> List[BreakoutEvent]:
        """检测setup后的突破事件"""
        breakouts = []
        
        for setup in self.setups:
            df = self.raw_data.get(setup.symbol)
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
            
            stop_price = setup.anchor_low if direction == "up" else setup.anchor_high
            stop_triggered = False
            stop_bar = None
            
            for j, (_, row) in enumerate(future.iterrows()):
                if direction == "up" and row['low'] < stop_price:
                    stop_triggered = True
                    stop_bar = j + 1
                    break
                elif direction == "down" and row['high'] > stop_price:
                    stop_triggered = True
                    stop_bar = j + 1
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
                pnl_5bar=pnl_5 if not pd.isna(pnl_5) else 0,
                pnl_10bar=pnl_10 if not pd.isna(pnl_10) else 0,
                pnl_20bar=pnl_20 if not pd.isna(pnl_20) else 0
            )
            breakouts.append(event)
        
        self.breakouts = breakouts
        logger.info(f"检测到 {len(breakouts)} 个突破事件")
        return breakouts
    
    def analyze(self) -> ResearchResult:
        """执行完整分析"""
        if not self.setups:
            logger.error("没有setup数据")
            return None
        
        setups = self.setups
        breakouts = self.breakouts
        
        total_setups = len(setups)
        total_breakouts = len(breakouts)
        breakout_rate = total_breakouts / total_setups if total_setups > 0 else 0
        no_breakout = total_setups - total_breakouts
        
        up_bo = sum(1 for b in breakouts if b.breakout_direction == "up")
        down_bo = sum(1 for b in breakouts if b.breakout_direction == "down")
        direction_balance = up_bo / total_breakouts if total_breakouts > 0 else 0.5
        
        all_returns_5 = []
        all_returns_10 = []
        all_returns_20 = []
        
        for setup in setups:
            df = self.raw_data.get(setup.symbol)
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
        
        hit_1r = sum(1 for b in breakouts if b.hit_target_1r) / total_breakouts if total_breakouts else 0
        hit_2r = sum(1 for b in breakouts if b.hit_target_2r) / total_breakouts if total_breakouts else 0
        hit_3r = sum(1 for b in breakouts if b.hit_target_3r) / total_breakouts if total_breakouts else 0
        stop_rate = sum(1 for b in breakouts if b.stop_triggered) / total_breakouts if total_breakouts else 0
        
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
        
        by_conditions = defaultdict(lambda: {"count": 0, "breakouts": 0, "avg_pnl": 0})
        for setup in setups:
            key = "+".join(sorted(setup.conditions))
            by_conditions[key]["count"] += 1
        for b in breakouts:
            key = "+".join(sorted(b.setup.conditions))
            by_conditions[key]["breakouts"] += 1
        for key in by_conditions:
            bo_list = [b for b in breakouts if "+".join(sorted(b.setup.conditions)) == key]
            if bo_list:
                by_conditions[key]["avg_pnl"] = np.mean([b.pnl_5bar for b in bo_list])
        
        by_symbol = defaultdict(lambda: {"setups": 0, "breakouts": 0, "avg_pnl": 0})
        for setup in setups:
            by_symbol[setup.symbol]["setups"] += 1
        for b in breakouts:
            by_symbol[b.setup.symbol]["breakouts"] += 1
        for sym in by_symbol:
            bo_list = [b for b in breakouts if b.setup.symbol == sym]
            if bo_list:
                by_symbol[sym]["avg_pnl"] = np.mean([b.pnl_5bar for b in bo_list])
        
        by_adx = {
            "ADX<9": {"count": 0, "avg_pnl": 0},
            "ADX<13": {"count": 0, "avg_pnl": 0},
            "ADX<20": {"count": 0, "avg_pnl": 0},
            "ADX>=20": {"count": 0, "avg_pnl": 0},
        }
        for b in breakouts:
            adx = b.setup.adx
            if adx < 9:
                key = "ADX<9"
            elif adx < 13:
                key = "ADX<13"
            elif adx < 20:
                key = "ADX<20"
            else:
                key = "ADX>=20"
            by_adx[key]["count"] += 1
        for key in by_adx:
            bo_list = [b for b in breakouts if 
                       (key == "ADX<9" and b.setup.adx < 9) or
                       (key == "ADX<13" and 9 <= b.setup.adx < 13) or
                       (key == "ADX<20" and 13 <= b.setup.adx < 20) or
                       (key == "ADX>=20" and b.setup.adx >= 20)]
            if bo_list:
                by_adx[key]["avg_pnl"] = np.mean([b.pnl_5bar for b in bo_list])
        
        recommendations = []
        warnings = []
        
        if total_setups < 50:
            warnings.append(f"样本量不足: 仅{total_setups}个setup")
        
        if breakout_rate < 0.3:
            recommendations.append(f"突破率较低({breakout_rate*100:.1f}%)，建议扩大等待周期或降低突破阈值")
        elif breakout_rate > 0.8:
            recommendations.append(f"突破率过高({breakout_rate*100:.1f}%)，可能突破阈值过低")
        
        if win_rate_5 > 0.55 and expectancy > 0:
            recommendations.append(f"5bar胜率{win_rate_5*100:.1f}%为正期望，策略有潜力")
        
        if wl_ratio > 1.5:
            recommendations.append(f"盈亏比{wl_ratio:.2f}良好")
        
        if total_setups < 30:
            validation_status = "样本不足"
        elif win_rate_5 < 0.5 and expectancy < 0:
            validation_status = "暂不建议进入实盘"
        elif win_rate_5 >= 0.55 and expectancy > 0 and wl_ratio > 1.2:
            validation_status = "已验证有效"
        else:
            validation_status = "逻辑需要调整"
        
        return ResearchResult(
            total_setups=total_setups, total_breakouts=total_breakouts,
            breakout_rate=breakout_rate, no_breakout_count=no_breakout,
            up_breakouts=up_bo, down_breakouts=down_bo,
            direction_balance=direction_balance,
            returns_5bar_all_mean=np.mean(all_returns_5) if all_returns_5 else 0,
            returns_5bar_all_median=np.median(all_returns_5) if all_returns_5 else 0,
            returns_10bar_all_mean=np.mean(all_returns_10) if all_returns_10 else 0,
            returns_10bar_all_median=np.median(all_returns_10) if all_returns_10 else 0,
            returns_20bar_all_mean=np.mean(all_returns_20) if all_returns_20 else 0,
            returns_20bar_all_median=np.median(all_returns_20) if all_returns_20 else 0,
            returns_5bar_bo_mean=np.mean(bo_returns_5) if bo_returns_5 else 0,
            returns_5bar_bo_median=np.median(bo_returns_5) if bo_returns_5 else 0,
            returns_10bar_bo_mean=np.mean(bo_returns_10) if bo_returns_10 else 0,
            returns_10bar_bo_median=np.median(bo_returns_10) if bo_returns_10 else 0,
            hit_1r_rate=hit_1r, hit_2r_rate=hit_2r, hit_3r_rate=hit_3r, stop_rate=stop_rate,
            win_rate_5bar=win_rate_5, win_rate_10bar=len([p for p in pnl_10 if p > 0]) / len(pnl_10) if pnl_10 else 0,
            avg_win_5bar=avg_win_5, avg_loss_5bar=avg_loss_5,
            win_loss_ratio_5bar=wl_ratio, expectancy_5bar=expectancy,
            by_score=dict(by_score), by_conditions=dict(by_conditions),
            by_symbol=dict(by_symbol), by_adx=by_adx,
            recommendations=recommendations, validation_status=validation_status,
            warnings=warnings
        )
    
    def run_param_sweep(self) -> Dict:
        """
        参数扫描：测试不同参数组合的效果
        
        扫描参数：
        - min_squeeze_score: 2, 3, 4, 5
        - max_wait_bars: 10, 15, 20, 30
        - min_breakout_atr: 0.1, 0.25, 0.5
        - require_structural: True, False
        """
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
                        
                        # 重新识别setup和突破
                        self.find_setups(min_squeeze_score=score, cooldown_bars=5, require_structural=struct)
                        self.detect_breakouts(max_wait_bars=wait, min_breakout_atr=atr)
                        result = self.analyze()
                        
                        if result:
                            param_results.append({
                                'min_score': score,
                                'max_wait': wait,
                                'min_atr': atr,
                                'require_structural': struct,
                                'setups': result.total_setups,
                                'breakouts': result.total_breakouts,
                                'breakout_rate': result.breakout_rate,
                                'win_rate_5bar': result.win_rate_5bar,
                                'win_loss_ratio': result.win_loss_ratio_5bar,
                                'expectancy': result.expectancy_5bar,
                                'hit_1r': result.hit_1r_rate,
                                'stop_rate': result.stop_rate,
                                'validation': result.validation_status
                            })
        
        df = pd.DataFrame(param_results)
        
        # 排序：优先期望值为正且样本充足的
        df['score'] = df['expectancy'] * np.sqrt(df['setups'].clip(lower=1))  # 样本加权期望
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
        lines.append("# 收缩→突破统计验证研究报告")
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
        lines.append(f"| 突破事件数 | {result.total_breakouts} |")
        lines.append(f"| 突破率 | {result.breakout_rate*100:.1f}% |")
        lines.append(f"| 未突破数 | {result.no_breakout_count} |")
        lines.append(f"| 向上突破 | {result.up_breakouts} |")
        lines.append(f"| 向下突破 | {result.down_breakouts} |")
        lines.append(f"| 方向平衡 | {result.direction_balance*100:.1f}% |")
        
        lines.append("\n## 二、收益统计")
        lines.append("\n### 所有Setup（包括未突破）")
        lines.append(f"\n| 持有周期 | 均值 | 中位数 |")
        lines.append(f"|----------|------|--------|")
        lines.append(f"| 5bar | {result.returns_5bar_all_mean:.3f}% | {result.returns_5bar_all_median:.3f}% |")
        lines.append(f"| 10bar | {result.returns_10bar_all_mean:.3f}% | {result.returns_10bar_all_median:.3f}% |")
        lines.append(f"| 20bar | {result.returns_20bar_all_mean:.3f}% | {result.returns_20bar_all_median:.3f}% |")
        
        lines.append("\n### 仅突破Setup")
        lines.append(f"\n| 持有周期 | 均值 | 中位数 |")
        lines.append(f"|----------|------|--------|")
        lines.append(f"| 5bar | {result.returns_5bar_bo_mean:.3f}% | {result.returns_5bar_bo_median:.3f}% |")
        lines.append(f"| 10bar | {result.returns_10bar_bo_mean:.3f}% | {result.returns_10bar_bo_median:.3f}% |")
        
        lines.append("\n## 三、交易绩效（基于突破方向交易）")
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
        
        lines.append("\n## 四、按Squeeze Score分组")
        lines.append(f"\n| Score | Setup数 | 突破数 | 突破率 | 胜率 | 平均PNL |")
        lines.append(f"|-------|---------|--------|--------|------|---------|")
        for score in sorted(result.by_score.keys()):
            d = result.by_score[score]
            lines.append(f"| {score} | {d['count']} | {d['breakouts']} | {d.get('breakout_rate', 0)*100:.1f}% | {d['win_rate']*100:.1f}% | {d['avg_pnl']:.3f}% |")
        
        lines.append("\n## 五、按ADX分组")
        lines.append(f"\n| ADX区间 | 突破数 | 平均PNL |")
        lines.append(f"|---------|--------|---------|")
        for key in ["ADX<9", "ADX<13", "ADX<20", "ADX>=20"]:
            d = result.by_adx.get(key, {"count": 0, "avg_pnl": 0})
            lines.append(f"| {key} | {d['count']} | {d['avg_pnl']:.3f}% |")
        
        lines.append("\n## 六、按品种分组")
        lines.append(f"\n| 品种 | Setup数 | 突破数 | 平均PNL |")
        lines.append(f"|------|---------|--------|---------|")
        for sym in sorted(result.by_symbol.keys()):
            d = result.by_symbol[sym]
            lines.append(f"| {sym} | {d['setups']} | {d['breakouts']} | {d['avg_pnl']:.3f}% |")
        
        # 参数扫描结果
        if param_analysis and 'top_results' in param_analysis:
            lines.append("\n## 七、参数扫描结果（Top 10）")
            lines.append(f"\n| 排名 | min_score | max_wait | min_atr | struct | setups | breakouts | 胜率 | 盈亏比 | 期望 | 状态 |")
            lines.append(f"|------|-----------|----------|---------|--------|--------|-----------|------|--------|------|------|")
            top = param_analysis['top_results']
            for idx, row in top.iterrows():
                lines.append(f"| {idx+1} | {row['min_score']} | {row['max_wait']} | {row['min_atr']} | {row['require_structural']} | "
                           f"{row['setups']} | {row['breakouts']} | {row['win_rate_5bar']*100:.1f}% | {row['win_loss_ratio']:.2f} | "
                           f"{row['expectancy']:.3f}% | {row['validation']} |")
            
            if param_analysis.get('best_params'):
                best = param_analysis['best_params']
                lines.append(f"\n### 推荐参数")
                lines.append(f"- min_squeeze_score: {best['min_score']}")
                lines.append(f"- max_wait_bars: {best['max_wait']}")
                lines.append(f"- min_breakout_atr: {best['min_atr']}")
                lines.append(f"- require_structural: {best['require_structural']}")
        
        lines.append("\n## 八、参数建议")
        if result.recommendations:
            for rec in result.recommendations:
                lines.append(f"- {rec}")
        else:
            lines.append("暂无明确建议，需更多样本数据。")
        
        lines.append("\n## 九、结论")
        lines.append(f"\n**验证状态**: {result.validation_status}")
        lines.append(f"\n- **已验证有效**: 胜率>55%且期望值为正")
        lines.append(f"- **样本不足**: setup总数<30")
        lines.append(f"- **逻辑需要调整**: 有样本但胜率或期望值不达标")
        lines.append(f"- **暂不建议进入实盘**: 胜率和期望值均为负")
        
        lines.append("\n---")
        lines.append("\n> 免责声明：本报告仅供研究参考，不构成投资建议。")
        
        report_path = Path(output_dir) / f"squeeze_breakout_research_{timestamp}.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"报告已保存: {report_path}")
        
        # CSV
        if self.breakouts:
            csv_records = []
            for b in self.breakouts:
                csv_records.append({
                    'symbol': b.setup.symbol,
                    'timeframe': b.setup.timeframe,
                    'squeeze_timestamp': b.setup.timestamp,
                    'squeeze_score': b.setup.squeeze_score,
                    'conditions': '+'.join(b.setup.conditions),
                    'adx': b.setup.adx,
                    'bb_width': b.setup.bb_width,
                    'pivot_range': b.setup.pivot_range,
                    'sr_range': b.setup.sr_range,
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
                    'stop_bar_idx': b.stop_bar_idx,
                    'pnl_5bar': b.pnl_5bar,
                    'pnl_10bar': b.pnl_10bar,
                    'pnl_20bar': b.pnl_20bar,
                })
            
            csv_df = pd.DataFrame(csv_records)
            csv_path = Path(output_dir) / f"squeeze_breakout_samples_{timestamp}.csv"
            csv_df.to_csv(csv_path, index=False)
            logger.info(f"样本CSV已保存: {csv_path}")
        else:
            csv_path = None
        
        # 参数扫描CSV
        if param_analysis and 'all_results' in param_analysis:
            param_csv_path = Path(output_dir) / f"squeeze_param_sweep_{timestamp}.csv"
            param_analysis['all_results'].to_csv(param_csv_path, index=False)
            logger.info(f"参数扫描CSV已保存: {param_csv_path}")
        
        return str(report_path), str(csv_path) if csv_path else None


def main():
    """主函数"""
    print("=" * 70)
    print("收缩→突破统计验证研究")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    research = SqueezeBreakoutResearch()
    
    priority_symbols = {
        "EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY",
        "AUDUSD": "AUDUSD", "USDCAD": "USDCAD", "XAUUSD": "GOLD",
        "US30": "US_30", "US500": "US_500", "NAS100": "US_TECH100",
        "GER40": "GERMANY_40", "BTCUSD": "BTCUSD",
    }
    
    # 获取数据
    research.fetch_data(priority_symbols, timeframe="H1", lookback_days=180)
    
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
    
    result = research.analyze()
    
    if result:
        print(f"\n{'='*60}")
        print("分析结果摘要")
        print(f"{'='*60}")
        print(f"Setup总数: {result.total_setups}")
        print(f"突破事件: {result.total_breakouts}")
        print(f"突破率: {result.breakout_rate*100:.1f}%")
        print(f"5bar胜率: {result.win_rate_5bar*100:.1f}%")
        print(f"盈亏比: {result.win_loss_ratio_5bar:.2f}")
        print(f"期望值: {result.expectancy_5bar:.3f}%")
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
