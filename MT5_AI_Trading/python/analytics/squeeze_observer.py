"""
收缩观测系统 - Squeeze Observer

基于"收缩带来扩张"交易理念的多周期收缩观测系统。
观测指标：
1. 布林带宽收缩 (BB Width)
2. 枢轴收缩 (Pivot Range)
3. ADX极端低值
4. State=0状态
5. SR支撑阻力位间距收缩

分品种、分周期视角进行统计，生成强化学习训练数据。
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SqueezeMetrics:
    """单品种单周期收缩指标"""
    symbol: str
    timeframe: str
    timestamp: datetime
    
    # 布林带宽
    bb_width: float = np.nan
    bb_width_20pct: float = np.nan
    bb_width_10pct: float = np.nan
    bb_width_5pct: float = np.nan
    bb_squeezed_20: bool = False
    bb_squeezed_10: bool = False
    bb_squeezed_5: bool = False
    
    # 枢轴范围
    pivot_range_pct: float = np.nan
    pivot_20pct: float = np.nan
    pivot_squeezed: bool = False
    
    # ADX
    adx: float = np.nan
    adx_lt_20: bool = False
    adx_lt_13: bool = False
    adx_lt_9: bool = False
    
    # State
    state_hex: str = ""
    state_is_zero: bool = False
    
    # SR支撑阻力位间距（独立指标，与枢轴收缩区分）
    sr_range_pct: float = np.nan        # (resistance - support) / close * 100
    sr_20pct: float = np.nan            # 历史20%分位阈值
    sr_squeezed: bool = False           # 是否低于20%分位
    
    # 综合
    squeeze_score: int = 0  # 满足收缩条件的数量
    squeeze_conditions: List[str] = field(default_factory=list)


@dataclass
class BreakoutSample:
    """收缩→突破样本（用于强化学习）"""
    symbol: str
    timeframe: str
    squeeze_timestamp: datetime
    breakout_timestamp: datetime
    breakout_direction: str  # "up" / "down"
    
    # 收缩时刻状态
    squeeze_state: Dict = field(default_factory=dict)
    
    # 突破后收益
    returns_1bar: float = np.nan
    returns_5bar: float = np.nan
    returns_10bar: float = np.nan
    max_drawdown: float = np.nan
    
    # 是否成功（达到目标收益）
    success_1bar: bool = False
    success_5bar: bool = False
    success_10bar: bool = False


class SqueezeObserver:
    """
    收缩观测器
    
    核心功能：
    1. 计算各周期收缩指标
    2. 统计收缩出现频率
    3. 分析收缩→突破的完整过程
    4. 生成强化学习训练样本
    """
    
    def __init__(self, db_path: str = "data/h1_state.duckdb"):
        self.db_path = db_path
        self.db = None
        self._mt5_bridge = None
        self._mt5_connected = False
        
    def _connect(self):
        if self.db is None:
            self.db = duckdb.connect(self.db_path)
            
    def _close(self):
        if self.db is not None:
            self.db.close()
            self.db = None
    
    # ========================================================================
    # 指标计算
    # ========================================================================
    
    @staticmethod
    def compute_bb_width(close: pd.Series, period: int = 20, std: float = 2.0) -> pd.Series:
        """
        布林带宽 = (上轨 - 下轨) / 中轨
        
        Args:
            close: 收盘价序列
            period: 布林带周期
            std: 标准差倍数
            
        Returns:
            布林带宽序列
        """
        mid = close.rolling(period).mean()
        std_dev = close.rolling(period).std()
        upper = mid + std * std_dev
        lower = mid - std * std_dev
        bb_width = (upper - lower) / mid
        return bb_width
    
    @staticmethod
    def compute_pivot_range(high: pd.Series, low: pd.Series, close: pd.Series,
                            period: int = 20) -> pd.Series:
        """
        枢轴范围 = (N周期最高 - N周期最低) / 收盘价 * 100
        反映N周期内价格波动幅度

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 枢轴周期

        Returns:
            枢轴范围百分比序列
        """
        support = low.rolling(period).min()
        resistance = high.rolling(period).max()
        pivot_range = (resistance - support) / close * 100
        return pivot_range

    @staticmethod
    def compute_sr_range(high: pd.Series, low: pd.Series, close: pd.Series,
                         period: int = 20) -> pd.Series:
        """
        SR支撑阻力位间距 = (N周期阻力位 - N周期支撑位) / 收盘价 * 100

        与枢轴收缩的区别：
        - 枢轴收缩：基于(H+L+C)/3枢轴点的范围变化
        - SR间距：基于N周期高低点的绝对间距，反映支撑阻力带的宽度

        当SR间距收缩时，意味着：
        1. 支撑阻力位之间的空间被压缩
        2. 价格在该区间内的波动被限制
        3. 突破后的潜在运行空间更大（弹簧效应）

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: SR计算周期（默认20）

        Returns:
            SR间距百分比序列
        """
        support = low.rolling(period).min()
        resistance = high.rolling(period).max()
        sr_range = (resistance - support) / close * 100
        return sr_range
    
    @staticmethod
    def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, 
                    period: int = 14) -> pd.Series:
        """
        ADX(14) 计算
        
        公式：
        1. TR = max(high-low, |high-prev_close|, |low-prev_close|)
        2. +DM = high - prev_high (if > 0 and > low - prev_low)
        3. -DM = prev_low - low (if > 0 and > high - prev_high)
        4. +DI = 100 * SMA(+DM) / SMA(TR)
        5. -DI = 100 * SMA(-DM) / SMA(TR)
        6. DX = 100 * |+DI - -DI| / (+DI + -DI)
        7. ADX = SMA(DX)
        
        Args:
            high, low, close: OHLC中的HLC
            period: ADX周期
            
        Returns:
            ADX序列
        """
        # True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # +DM, -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm[plus_dm <= minus_dm] = 0
        minus_dm[minus_dm <= plus_dm] = 0
        
        # Smooth TR, +DM, -DM (Wilder's smoothing)
        atr = tr.ewm(alpha=1/period, min_periods=period).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr
        minus_di = 100 * minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr
        
        # DX and ADX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.ewm(alpha=1/period, min_periods=period).mean()
        
        return adx
    
    @staticmethod
    def is_value_below_percentile(series: pd.Series, lookback: int = 30, 
                                   percentile: float = 20) -> bool:
        """
        判断当前值是否低于过去lookback期的指定分位数
        
        Args:
            series: 指标序列
            lookback: 回看周期
            percentile: 分位数 (0-100)
            
        Returns:
            是否低于分位数阈值
        """
        if len(series) < lookback or pd.isna(series.iloc[-1]):
            return False
        threshold = series.iloc[-lookback:].quantile(percentile / 100)
        return series.iloc[-1] <= threshold
    
    # ========================================================================
    # 单品种分析
    # ========================================================================
    
    def _ensure_mt5(self):
        """确保MT5连接已建立"""
        if not self._mt5_connected:
            try:
                import sys
                from pathlib import Path
                project_root = Path(__file__).parent.parent.parent
                sys.path.insert(0, str(project_root))
                from backtest_platform.data_layer import MT5DataBridge
                
                self._mt5_bridge = MT5DataBridge()
                if self._mt5_bridge.connect():
                    self._mt5_connected = True
                    logger.info("MT5连接已建立")
                else:
                    logger.warning("MT5连接失败")
            except Exception as e:
                logger.warning(f"MT5初始化失败: {e}")
    
    def _disconnect_mt5(self):
        """断开MT5连接"""
        if self._mt5_bridge and self._mt5_connected:
            self._mt5_bridge.disconnect()
            self._mt5_connected = False
            self._mt5_bridge = None
            logger.info("MT5连接已断开")
    
    def _fetch_from_mt5(self, symbol: str, timeframe: str, 
                         lookback_days: int = 120) -> pd.DataFrame:
        """从MT5获取OHLCV数据（复用连接）"""
        self._ensure_mt5()
        if not self._mt5_connected or self._mt5_bridge is None:
            return pd.DataFrame()
        
        try:
            end = datetime.now()
            start = end - timedelta(days=lookback_days)
            df = self._mt5_bridge.fetch_ohlcv(symbol, timeframe, start, end)
            return df
        except Exception as e:
            logger.warning(f"从MT5获取数据失败 {symbol} {timeframe}: {e}")
            return pd.DataFrame()
    
    def analyze_symbol_timeframe(self, symbol: str, timeframe: str = "H1",
                                  lookback_days: int = 120) -> List[SqueezeMetrics]:
        """
        分析单个品种单个周期的收缩指标
        
        Args:
            symbol: 品种代码
            timeframe: 周期 (MN1/W1/D1/H4/H1)
            lookback_days: 回看天数
            
        Returns:
            SqueezeMetrics列表（每个时间戳一条记录）
        """
        self._connect()
        
        # 从数据库读取OHLCV数据
        df = pd.DataFrame()
        
        # 先尝试从h1_slices表获取
        try:
            df = self.db.execute("""
                SELECT timestamp, open, high, low, close, volume
                FROM h1_slices
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp
            """, [symbol, timeframe]).fetchdf()
        except:
            pass
        
        # 如果数据库没有，尝试从MT5获取
        if df.empty:
            logger.info(f"{symbol} {timeframe}: 数据库无数据，尝试从MT5获取...")
            df = self._fetch_from_mt5(symbol, timeframe, lookback_days)
        
        if df.empty or len(df) < 30:
            logger.warning(f"{symbol} {timeframe}: 数据不足 ({len(df)}条)")
            return []
        
        # 计算指标
        df['bb_width'] = self.compute_bb_width(df['close'])
        df['pivot_range'] = self.compute_pivot_range(df['high'], df['low'], df['close'])
        df['sr_range'] = self.compute_sr_range(df['high'], df['low'], df['close'])
        df['adx'] = self.compute_adx(df['high'], df['low'], df['close'])
        
        # 获取state_hex
        state_col = f"{timeframe.lower()}_hex"
        try:
            state_df = self.db.execute(f"""
                SELECT timestamp, {state_col} as state_hex
                FROM h1_state_snapshot
                WHERE symbol = ?
                ORDER BY timestamp
            """, [symbol]).fetchdf()
            if not state_df.empty:
                df = df.merge(state_df, on='timestamp', how='left')
            else:
                df['state_hex'] = ""
        except:
            df['state_hex'] = ""
        
        # 逐行计算收缩指标
        metrics_list = []
        for i in range(len(df)):
            if i < 30:  # 需要足够历史数据
                continue
                
            row = df.iloc[i]
            ts = row['timestamp']
            
            # 布林带宽分位数
            bb_hist = df['bb_width'].iloc[:i+1].dropna()
            bb_20 = bb_hist.quantile(0.20) if len(bb_hist) >= 20 else np.nan
            bb_10 = bb_hist.quantile(0.10) if len(bb_hist) >= 20 else np.nan
            bb_5 = bb_hist.quantile(0.05) if len(bb_hist) >= 20 else np.nan
            
            # 枢轴分位数
            pivot_hist = df['pivot_range'].iloc[:i+1].dropna()
            pivot_20 = pivot_hist.quantile(0.20) if len(pivot_hist) >= 20 else np.nan

            # SR间距分位数（独立计算）
            sr_hist = df['sr_range'].iloc[:i+1].dropna()
            sr_20 = sr_hist.quantile(0.20) if len(sr_hist) >= 20 else np.nan

            # 构建指标
            metrics = SqueezeMetrics(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts,
                bb_width=row['bb_width'] if not pd.isna(row['bb_width']) else np.nan,
                bb_width_20pct=bb_20,
                bb_width_10pct=bb_10,
                bb_width_5pct=bb_5,
                bb_squeezed_20=row['bb_width'] <= bb_20 if not pd.isna(row['bb_width']) and not pd.isna(bb_20) else False,
                bb_squeezed_10=row['bb_width'] <= bb_10 if not pd.isna(row['bb_width']) and not pd.isna(bb_10) else False,
                bb_squeezed_5=row['bb_width'] <= bb_5 if not pd.isna(row['bb_width']) and not pd.isna(bb_5) else False,
                pivot_range_pct=row['pivot_range'] if not pd.isna(row['pivot_range']) else np.nan,
                pivot_20pct=pivot_20,
                pivot_squeezed=row['pivot_range'] <= pivot_20 if not pd.isna(row['pivot_range']) and not pd.isna(pivot_20) else False,
                adx=row['adx'] if not pd.isna(row['adx']) else np.nan,
                adx_lt_20=row['adx'] < 20 if not pd.isna(row['adx']) else False,
                adx_lt_13=row['adx'] < 13 if not pd.isna(row['adx']) else False,
                adx_lt_9=row['adx'] < 9 if not pd.isna(row['adx']) else False,
                state_hex=row.get('state_hex', ''),
                state_is_zero=str(row.get('state_hex', '')) == '0',
                sr_range_pct=row['sr_range'] if not pd.isna(row['sr_range']) else np.nan,
                sr_20pct=sr_20,
                sr_squeezed=row['sr_range'] <= sr_20 if not pd.isna(row['sr_range']) and not pd.isna(sr_20) else False,
            )
            
            # 计算综合收缩分数
            conditions = []
            if metrics.bb_squeezed_20:
                conditions.append("BB_20")
            if metrics.bb_squeezed_10:
                conditions.append("BB_10")
            if metrics.pivot_squeezed:
                conditions.append("Pivot")
            if metrics.adx_lt_20:
                conditions.append("ADX<20")
            if metrics.adx_lt_13:
                conditions.append("ADX<13")
            if metrics.adx_lt_9:
                conditions.append("ADX<9")
            if metrics.state_is_zero:
                conditions.append("State=0")
            if metrics.sr_squeezed:
                conditions.append("SR_Squeeze")
            
            metrics.squeeze_score = len(conditions)
            metrics.squeeze_conditions = conditions
            
            metrics_list.append(metrics)
        
        return metrics_list
    
    # ========================================================================
    # 全品种分析
    # ========================================================================
    
    def get_all_symbols(self) -> List[str]:
        """获取数据库中所有品种"""
        self._connect()
        rows = self.db.execute("""
            SELECT DISTINCT symbol FROM h1_state_snapshot ORDER BY symbol
        """).fetchall()
        return [r[0] for r in rows]
    
    def analyze_all(self, symbols: List[str] = None, 
                    timeframes: List[str] = None) -> pd.DataFrame:
        """
        全品种全周期收缩分析
        
        Args:
            symbols: 品种列表，None则全部
            timeframes: 周期列表，None则全部
            
        Returns:
            DataFrame，每行一个(品种, 周期, 时间戳)的收缩指标
        """
        if symbols is None:
            symbols = self.get_all_symbols()
        if timeframes is None:
            timeframes = ["H1"]  # 先从H1开始，其他周期需要原始数据
        
        all_records = []
        total = len(symbols) * len(timeframes)
        processed = 0
        
        for symbol in symbols:
            for tf in timeframes:
                processed += 1
                logger.info(f"[{processed}/{total}] 分析 {symbol} {tf}")
                
                try:
                    metrics_list = self.analyze_symbol_timeframe(symbol, tf)
                    for m in metrics_list:
                        all_records.append({
                            'symbol': m.symbol,
                            'timeframe': m.timeframe,
                            'timestamp': m.timestamp,
                            'bb_width': m.bb_width,
                            'bb_squeezed_20': m.bb_squeezed_20,
                            'bb_squeezed_10': m.bb_squeezed_10,
                            'bb_squeezed_5': m.bb_squeezed_5,
                            'pivot_range_pct': m.pivot_range_pct,
                            'pivot_squeezed': m.pivot_squeezed,
                            'sr_range_pct': m.sr_range_pct,
                            'sr_squeezed': m.sr_squeezed,
                            'adx': m.adx,
                            'adx_lt_20': m.adx_lt_20,
                            'adx_lt_13': m.adx_lt_13,
                            'adx_lt_9': m.adx_lt_9,
                            'state_hex': m.state_hex,
                            'state_is_zero': m.state_is_zero,
                            'squeeze_score': m.squeeze_score,
                            'squeeze_conditions': ','.join(m.squeeze_conditions),
                        })
                except Exception as e:
                    logger.error(f"{symbol} {tf} 分析失败: {e}")
        
        df = pd.DataFrame(all_records)
        logger.info(f"分析完成: {len(df)} 条记录")
        return df
    
    # ========================================================================
    # 强化学习样本生成
    # ========================================================================
    
    def generate_breakout_samples(self, symbol: str, timeframe: str = "H1",
                                   hold_bars: int = 5,
                                   min_squeeze_score: int = 2) -> List[BreakoutSample]:
        """
        生成收缩→突破样本
        
        Args:
            symbol: 品种
            timeframe: 周期
            hold_bars: 持有K线数
            min_squeeze_score: 最小收缩分数
            
        Returns:
            BreakoutSample列表
        """
        metrics_list = self.analyze_symbol_timeframe(symbol, timeframe)
        if not metrics_list:
            return []
        
        # 获取价格数据计算收益
        self._connect()
        df = self.db.execute("""
            SELECT timestamp, close
            FROM h1_slices
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp
        """, [symbol, timeframe]).fetchdf()
        
        if df.empty:
            return []
        
        samples = []
        for i, m in enumerate(metrics_list):
            if m.squeeze_score < min_squeeze_score:
                continue
            
            # 找到对应的价格索引
            price_idx = df[df['timestamp'] == m.timestamp].index
            if len(price_idx) == 0:
                continue
            idx = price_idx[0]
            
            if idx + hold_bars >= len(df):
                continue
            
            entry_price = df['close'].iloc[idx]
            
            # 计算未来N根K线的收益
            future_prices = df['close'].iloc[idx+1:idx+hold_bars+1]
            returns = (future_prices - entry_price) / entry_price * 100
            
            # 判断突破方向（基于未来第一根K线的方向）
            if len(returns) > 0:
                if returns.iloc[0] > 0:
                    direction = "up"
                elif returns.iloc[0] < 0:
                    direction = "down"
                else:
                    continue
            else:
                continue
            
            # 最大回撤
            if direction == "up":
                max_dd = ((future_prices.min() - entry_price) / entry_price * 100)
            else:
                max_dd = ((entry_price - future_prices.max()) / entry_price * 100)
            
            sample = BreakoutSample(
                symbol=symbol,
                timeframe=timeframe,
                squeeze_timestamp=m.timestamp,
                breakout_timestamp=df['timestamp'].iloc[idx+1],
                breakout_direction=direction,
                squeeze_state={
                    'bb_width': m.bb_width,
                    'pivot_range': m.pivot_range_pct,
                    'adx': m.adx,
                    'state_hex': m.state_hex,
                    'squeeze_score': m.squeeze_score,
                },
                returns_1bar=returns.iloc[0] if len(returns) >= 1 else np.nan,
                returns_5bar=returns.iloc[4] if len(returns) >= 5 else np.nan,
                returns_10bar=returns.iloc[9] if len(returns) >= 10 else np.nan,
                max_drawdown=max_dd,
                success_1bar=abs(returns.iloc[0]) > 0.1 if len(returns) >= 1 else False,
                success_5bar=abs(returns.iloc[4]) > 0.3 if len(returns) >= 5 else False,
                success_10bar=abs(returns.iloc[9]) > 0.5 if len(returns) >= 10 else False,
            )
            samples.append(sample)
        
        return samples
    
    # ========================================================================
    # 统计汇总
    # ========================================================================
    
    def summarize_squeeze_stats(self, df: pd.DataFrame) -> Dict:
        """
        汇总收缩统计
        
        Args:
            df: analyze_all返回的DataFrame
            
        Returns:
            统计字典
        """
        if df.empty:
            return {}
        
        stats = {
            'total_records': len(df),
            'total_symbols': df['symbol'].nunique(),
            'timeframes': df['timeframe'].unique().tolist(),
            
            # State=0统计
            'state_zero_count': int(df['state_is_zero'].sum()),
            'state_zero_pct': float(df['state_is_zero'].mean() * 100),
            
            # BB收缩统计
            'bb_squeezed_20_count': int(df['bb_squeezed_20'].sum()),
            'bb_squeezed_20_pct': float(df['bb_squeezed_20'].mean() * 100),
            'bb_squeezed_10_count': int(df['bb_squeezed_10'].sum()),
            'bb_squeezed_10_pct': float(df['bb_squeezed_10'].mean() * 100),
            'bb_squeezed_5_count': int(df['bb_squeezed_5'].sum()),
            'bb_squeezed_5_pct': float(df['bb_squeezed_5'].mean() * 100),
            
            # 枢轴收缩统计
            'pivot_squeezed_count': int(df['pivot_squeezed'].sum()),
            'pivot_squeezed_pct': float(df['pivot_squeezed'].mean() * 100),

            # SR间距收缩统计（独立指标）
            'sr_squeezed_count': int(df['sr_squeezed'].sum()),
            'sr_squeezed_pct': float(df['sr_squeezed'].mean() * 100),

            # ADX统计
            'adx_lt_20_count': int(df['adx_lt_20'].sum()),
            'adx_lt_20_pct': float(df['adx_lt_20'].mean() * 100),
            'adx_lt_13_count': int(df['adx_lt_13'].sum()),
            'adx_lt_13_pct': float(df['adx_lt_13'].mean() * 100),
            'adx_lt_9_count': int(df['adx_lt_9'].sum()),
            'adx_lt_9_pct': float(df['adx_lt_9'].mean() * 100),
            
            # 综合收缩分数分布
            'squeeze_score_dist': df['squeeze_score'].value_counts().to_dict(),
            
            # 多指标共振（>=3个条件）
            'high_squeeze_count': int((df['squeeze_score'] >= 3).sum()),
            'high_squeeze_pct': float((df['squeeze_score'] >= 3).mean() * 100),
        }
        
        return stats
    
    def __enter__(self):
        self._connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._disconnect_mt5()
        self._close()
        return False
