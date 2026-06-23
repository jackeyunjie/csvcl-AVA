"""
MT4-H1 数据层

职责: 从MT4 CSV文件读取数据，H1/D1/W1/MN1四周期对齐。

MT4数据特点:
- 通过"历史中心"导出CSV
- 文件名格式: EURUSD60.csv (H1), EURUSD1440.csv (D1), 等
- 列格式: Time, Open, High, Low, Close, Volume
"""

import os
import sys
import glob
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


# ============================================================================
# MT4 CSV 数据读取器
# ============================================================================

class MT4CSVReader:
    """
    MT4 CSV文件读取器

    支持MT4导出的标准CSV格式:
    - Time, Open, High, Low, Close, Volume
    - Time格式: YYYY.MM.DD HH:MM 或 YYYY-MM-DD HH:MM:SS

    文件命名约定:
    - EURUSD1.csv   = M1
    - EURUSD5.csv   = M5
    - EURUSD15.csv  = M15
    - EURUSD30.csv  = M30
    - EURUSD60.csv  = H1
    - EURUSD240.csv = H4
    - EURUSD1440.csv= D1
    - EURUSD10080.csv = W1
    - EURUSD43200.csv = MN1
    """

    TIMEFRAME_MAP = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
        "M30": 30,
        "H1": 60,
        "H4": 240,
        "D1": 1440,
        "W1": 10080,
        "MN1": 43200,
    }

    def __init__(self, data_dir: str = "data/mt4"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _find_file(self, symbol: str, timeframe: str) -> Optional[Path]:
        """查找CSV文件"""
        minutes = self.TIMEFRAME_MAP.get(timeframe)
        if minutes is None:
            return None

        # 尝试多种命名格式
        patterns = [
            f"{symbol}{minutes}.csv",
            f"{symbol}_{timeframe}.csv",
            f"{symbol}_{timeframe.lower()}.csv",
            f"{symbol}-{timeframe}.csv",
        ]

        for pattern in patterns:
            path = self.data_dir / pattern
            if path.exists():
                return path

        # 模糊匹配
        for f in self.data_dir.glob(f"{symbol}*.csv"):
            if timeframe.lower() in f.name.lower() or str(minutes) in f.name:
                return f

        return None

    def read_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        读取MT4 CSV数据

        Args:
            symbol: 品种，如 "EURUSD"
            timeframe: 周期，如 "H1", "D1"
            start: 开始时间（可选）
            end: 结束时间（可选）

        Returns:
            DataFrame，列: timestamp, open, high, low, close, volume
        """
        file_path = self._find_file(symbol, timeframe)
        if file_path is None:
            logger.warning(f"未找到 {symbol} {timeframe} 的CSV文件")
            return pd.DataFrame()

        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            logger.error(f"读取CSV失败: {file_path}, error={e}")
            return pd.DataFrame()

        # 标准化列名
        df.columns = [c.strip().lower() for c in df.columns]

        # 处理时间列
        if 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'], errors='coerce')
        elif 'datetime' in df.columns:
            df['timestamp'] = pd.to_datetime(df['datetime'], errors='coerce')
        else:
            # 尝试第一列
            df['timestamp'] = pd.to_datetime(df.iloc[:, 0], errors='coerce')

        # 标准化OHLCV列
        col_mapping = {}
        for std_col in ['open', 'high', 'low', 'close', 'volume']:
            for actual_col in df.columns:
                if actual_col.lower() == std_col:
                    col_mapping[actual_col] = std_col
                    break

        df = df.rename(columns=col_mapping)

        # 选择标准列
        required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        available = [c for c in required if c in df.columns]
        df = df[available].copy()

        # 过滤时间范围
        if start is not None:
            df = df[df['timestamp'] >= start]
        if end is not None:
            df = df[df['timestamp'] <= end]

        df = df.dropna(subset=['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        logger.info(f"读取MT4数据: {symbol} {timeframe} | {len(df)}条 | 来源: {file_path.name}")
        return df

    def read_multi_timeframe(
        self,
        symbol: str,
        timeframes: List[str],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, pd.DataFrame]:
        """读取多周期数据"""
        result = {}
        for tf in timeframes:
            df = self.read_ohlcv(symbol, tf, start, end)
            result[tf] = df
        return result

    def list_available_files(self) -> pd.DataFrame:
        """列出所有可用的CSV文件"""
        files = []
        for f in self.data_dir.glob("*.csv"):
            files.append({
                'filename': f.name,
                'size_kb': round(f.stat().st_size / 1024, 1),
                'modified': datetime.fromtimestamp(f.stat().st_mtime),
            })
        return pd.DataFrame(files)


# ============================================================================
# H1 四周期对齐器
# ============================================================================

class H1MultiTimeframeAligner:
    """
    H1四周期对齐器

    核心设计: 只读H1数据，D1/W1/MN1全部从H1聚合生成。
    确保四周期时间戳完全对齐，无外部数据不一致问题。

    对齐规则:
    - H1数据: 每小时一根，作为基准
    - D1数据: 从H1聚合生成（当日H1的open/first, high/max, low/min, close/last）
    - W1数据: 从H1聚合生成（当周H1的open/first, high/max, low/min, close/last）
    - MN1数据: 从H1聚合生成（当月H1的open/first, high/max, low/min, close/last）

    输出: 每行H1数据附加D1/W1/MN1的OHLCV
    """

    def align_from_h1(
        self,
        h1_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        从H1数据生成D1/W1/MN1并对齐到H1时间轴

        Args:
            h1_df: H1数据（唯一输入）

        Returns:
            对齐后的DataFrame
        """
        if h1_df.empty:
            raise ValueError("H1数据不能为空")

        h1 = h1_df.copy()
        h1['timestamp'] = pd.to_datetime(h1['timestamp'])
        h1 = h1.sort_values('timestamp').reset_index(drop=True)

        # 添加对齐键
        h1['date_key'] = h1['timestamp'].dt.date.astype(str)
        h1['week_key'] = h1['timestamp'].apply(self._get_week_key)
        h1['month_key'] = h1['timestamp'].dt.to_period('M').astype(str)

        # 从H1聚合生成D1/W1/MN1
        d1_df = self._aggregate_h1_to_d1(h1)
        w1_df = self._aggregate_h1_to_w1(h1)
        mn1_df = self._aggregate_h1_to_mn1(h1)

        # 对齐D1
        h1 = self._align_d1(h1, d1_df)
        # 对齐W1
        h1 = self._align_w1(h1, w1_df)
        # 对齐MN1
        h1 = self._align_mn1(h1, mn1_df)

        # 清理临时列
        for col in ['date_key', 'week_key', 'month_key']:
            if col in h1.columns:
                h1 = h1.drop(columns=[col])

        logger.info(f"H1四周期对齐完成: H1={len(h1)}行 | 列={list(h1.columns)}")
        return h1

    def _align_d1(self, h1: pd.DataFrame, d1_df: pd.DataFrame) -> pd.DataFrame:
        """对齐D1到H1"""
        d1 = d1_df.copy()
        d1['timestamp'] = pd.to_datetime(d1['timestamp'])
        d1['date_key'] = d1['timestamp'].dt.date.astype(str)

        d1_renamed = d1.rename(columns={
            'open': 'd1_open', 'high': 'd1_high', 'low': 'd1_low',
            'close': 'd1_close', 'volume': 'd1_volume',
        })[['date_key', 'd1_open', 'd1_high', 'd1_low', 'd1_close', 'd1_volume']]

        return h1.merge(d1_renamed, on='date_key', how='left')

    def _align_w1(self, h1: pd.DataFrame, w1_df: pd.DataFrame) -> pd.DataFrame:
        """对齐W1到H1"""
        w1 = w1_df.copy()
        w1['timestamp'] = pd.to_datetime(w1['timestamp'])
        w1['week_key'] = w1['timestamp'].apply(self._get_week_key)

        w1_renamed = w1.rename(columns={
            'open': 'w1_open', 'high': 'w1_high', 'low': 'w1_low',
            'close': 'w1_close', 'volume': 'w1_volume',
        })[['week_key', 'w1_open', 'w1_high', 'w1_low', 'w1_close', 'w1_volume']]

        return h1.merge(w1_renamed, on='week_key', how='left')

    def _align_mn1(self, h1: pd.DataFrame, mn1_df: pd.DataFrame) -> pd.DataFrame:
        """对齐MN1到H1"""
        mn1 = mn1_df.copy()
        mn1['timestamp'] = pd.to_datetime(mn1['timestamp'])
        mn1['month_key'] = mn1['timestamp'].dt.to_period('M').astype(str)

        mn1_renamed = mn1.rename(columns={
            'open': 'mn1_open', 'high': 'mn1_high', 'low': 'mn1_low',
            'close': 'mn1_close', 'volume': 'mn1_volume',
        })[['month_key', 'mn1_open', 'mn1_high', 'mn1_low', 'mn1_close', 'mn1_volume']]

        return h1.merge(mn1_renamed, on='month_key', how='left')

    def _aggregate_h1_to_d1(self, h1: pd.DataFrame) -> pd.DataFrame:
        """从H1聚合生成D1数据

        规则: 当日第一根H1的open作为D1 open,
              当日H1的high最大值作为D1 high,
              当日H1的low最小值作为D1 low,
              当日最后一根H1的close作为D1 close,
              当日H1的volume总和作为D1 volume
        """
        grouped = h1.groupby('date_key', sort=False)

        d1_records = []
        for date_key, group in grouped:
            group = group.sort_values('timestamp')
            d1_records.append({
                'timestamp': pd.Timestamp(date_key),
                'open': group['open'].iloc[0],
                'high': group['high'].max(),
                'low': group['low'].min(),
                'close': group['close'].iloc[-1],
                'volume': group['volume'].sum(),
            })

        d1_df = pd.DataFrame(d1_records)
        d1_df = d1_df.sort_values('timestamp').reset_index(drop=True)
        logger.info(f"H1→D1聚合: {len(d1_df)}根日线")
        return d1_df

    def _aggregate_h1_to_w1(self, h1: pd.DataFrame) -> pd.DataFrame:
        """从H1聚合生成W1数据

        规则: 当周第一根H1的open作为W1 open,
              当周H1的high最大值作为W1 high,
              当周H1的low最小值作为W1 low,
              当周最后一根H1的close作为W1 close,
              当周H1的volume总和作为W1 volume
        """
        grouped = h1.groupby('week_key', sort=False)

        w1_records = []
        for week_key, group in grouped:
            group = group.sort_values('timestamp')
            w1_records.append({
                'timestamp': group['timestamp'].iloc[0],  # 用当周第一根H1的时间
                'open': group['open'].iloc[0],
                'high': group['high'].max(),
                'low': group['low'].min(),
                'close': group['close'].iloc[-1],
                'volume': group['volume'].sum(),
            })

        w1_df = pd.DataFrame(w1_records)
        w1_df = w1_df.sort_values('timestamp').reset_index(drop=True)
        logger.info(f"H1→W1聚合: {len(w1_df)}根周线")
        return w1_df

    def _aggregate_h1_to_mn1(self, h1: pd.DataFrame) -> pd.DataFrame:
        """从H1聚合生成MN1数据

        规则: 当月第一根H1的open作为MN1 open,
              当月H1的high最大值作为MN1 high,
              当月H1的low最小值作为MN1 low,
              当月最后一根H1的close作为MN1 close,
              当月H1的volume总和作为MN1 volume
        """
        grouped = h1.groupby('month_key', sort=False)

        mn1_records = []
        for month_key, group in grouped:
            group = group.sort_values('timestamp')
            mn1_records.append({
                'timestamp': group['timestamp'].iloc[0],  # 用当月第一根H1的时间
                'open': group['open'].iloc[0],
                'high': group['high'].max(),
                'low': group['low'].min(),
                'close': group['close'].iloc[-1],
                'volume': group['volume'].sum(),
            })

        mn1_df = pd.DataFrame(mn1_records)
        mn1_df = mn1_df.sort_values('timestamp').reset_index(drop=True)
        logger.info(f"H1→MN1聚合: {len(mn1_df)}根月线")
        return mn1_df

    def _add_empty_cols(self, df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        """添加空列"""
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[f'{prefix}_{col}'] = np.nan
        return df

    def _get_week_key(self, ts: datetime) -> str:
        """获取周键值"""
        year, week, _ = ts.isocalendar()
        return f"{year}-{week:02d}"


# ============================================================================
# H1 数据存储 (复用DuckDB，但独立数据库)
# ============================================================================

class H1DataStore:
    """
    H1数据存储

    复用DuckDB/SQLite，但使用独立数据库文件，
    避免与MT5-D1系统冲突。
    """

    def __init__(self, db_path: str = "data/mt4_h1_cache.duckdb"):
        self.db_path = db_path
        self._conn = None

    def _get_connection(self):
        """获取数据库连接"""
        if self._conn is None:
            try:
                import duckdb
                os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
                self._conn = duckdb.connect(self.db_path)
                self._create_tables()
            except ImportError:
                import sqlite3
                os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
                self._conn = sqlite3.connect(self.db_path.replace(".duckdb", ".sqlite"))
                self._create_tables_sqlite()
        return self._conn

    def _create_tables(self):
        """创建表结构"""
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_data (
                symbol VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_metadata (
                symbol VARCHAR NOT NULL, timeframe VARCHAR NOT NULL,
                last_update TIMESTAMP, row_count INTEGER,
                start_date TIMESTAMP, end_date TIMESTAMP,
                PRIMARY KEY (symbol, timeframe)
            )
        """)
        conn.commit()

    def _create_tables_sqlite(self):
        """SQLite表结构"""
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_data (
                symbol TEXT NOT NULL, timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL, open REAL, high REAL, low REAL, close REAL, volume REAL,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        """)
        conn.commit()

    def save_ohlcv(self, symbol: str, timeframe: str, df: pd.DataFrame) -> bool:
        """保存OHLCV数据"""
        if df.empty:
            return False
        conn = self._get_connection()
        try:
            save_df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            save_df['symbol'] = symbol
            save_df['timeframe'] = timeframe

            conn.execute("BEGIN")
            conn.execute(f"""
                DELETE FROM ohlcv_data WHERE symbol = '{symbol}' AND timeframe = '{timeframe}'
            """)
            conn.execute("""
                INSERT INTO ohlcv_data (symbol, timeframe, timestamp, open, high, low, close, volume)
                SELECT symbol, timeframe, timestamp, open, high, low, close, volume FROM save_df
            """)
            conn.execute("COMMIT")
            return True
        except Exception as e:
            conn.execute("ROLLBACK")
            logger.error(f"保存失败: {e}")
            return False

    def load_ohlcv(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """读取OHLCV数据"""
        conn = self._get_connection()
        try:
            df = pd.read_sql_query(
                "SELECT timestamp, open, high, low, close, volume FROM ohlcv_data WHERE symbol = ? AND timeframe = ? ORDER BY timestamp",
                conn, params=[symbol, timeframe]
            )
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            logger.error(f"读取失败: {e}")
            return pd.DataFrame()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
