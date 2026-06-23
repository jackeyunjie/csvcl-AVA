"""
数据层 (Data Layer)

职责: 负责所有数据的获取、清洗、存储和对齐。

模块:
- MT5DataBridge: 从MT5提取历史数据（Python API / ZeroMQ）
- DataStore: DuckDB本地缓存，支持增量更新
- MultiTimeframeAligner: MN1/W1/D1多周期数据对齐

核心原则:
- 三元组(MN1, W1, D1)为最小分析单元，数据必须对齐
- 禁止单独分析日线D1
- 数据质量检查前置，脏数据不入库
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

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


# ============================================================================
# 数据质量报告
# ============================================================================

@dataclass
class DataQualityReport:
    """数据质量报告"""
    symbol: str
    timeframe: str
    total_rows: int
    missing_values: int
    gap_days: int
    duplicate_rows: int
    price_anomalies: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_valid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "total_rows": self.total_rows,
            "missing_values": self.missing_values,
            "gap_days": self.gap_days,
            "duplicate_rows": self.duplicate_rows,
            "price_anomalies": self.price_anomalies,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_valid": self.is_valid,
        }


# ============================================================================
# MT5 数据桥接器
# ============================================================================

class MT5DataBridge:
    """
    MT5 数据桥接器

    通过 MetaTrader5 Python API 从 MT5 提取历史数据。
    支持多周期数据一次性提取。

    使用方式:
        bridge = MT5DataBridge()
        if bridge.connect():
            df = bridge.fetch_ohlcv("EURUSD", "D1", start, end)
            multi = bridge.fetch_multi_timeframe("EURUSD", ["MN1","W1","D1"], start, end)
            bridge.disconnect()
    """

    TIMEFRAME_MAP = {
        "MN1": 49153,    # 月线图
        "W1": 32769,     # 周线图
        "D1": 16408,     # 日线图
        "H4": 16388,     # 4小时图
        "H1": 16385,     # 1小时图
        "M30": 30,       # 30分钟图
        "M15": 15,       # 15分钟图
        "M5": 5,         # 5分钟图
        "M1": 1,         # 1分钟图
    }

    def __init__(self, terminal_path: Optional[str] = None):
        self.terminal_path = terminal_path
        self._mt5 = None
        self._connected = False

    @staticmethod
    def _to_local_timestamp(series: pd.Series) -> pd.Series:
        """Convert MT5 epoch seconds to local naive timestamps.

        MetaTrader5 returns epoch seconds. `pd.to_datetime(..., unit='s')`
        interprets them as UTC-naive values, which shifts Asia/Shanghai bars
        eight hours behind the MT5 terminal view. Use `datetime.fromtimestamp`
        to match the local terminal clock used by existing reports.
        """
        return series.apply(lambda value: datetime.fromtimestamp(int(value)))

    def _import_mt5(self):
        """延迟导入MT5模块"""
        if self._mt5 is None:
            try:
                import MetaTrader5 as mt5
                self._mt5 = mt5
            except ImportError as exc:
                logger.warning(
                    "MetaTrader5 package未安装，MT5数据提取将不可用。"
                    "如需使用，请运行: pip install MetaTrader5"
                )
                raise ImportError(
                    "MetaTrader5 package is not installed. Run: pip install MetaTrader5"
                ) from exc
        return self._mt5

    def connect(self) -> bool:
        """连接MT5终端"""
        try:
            mt5 = self._import_mt5()
            kwargs = {"timeout": 60000}
            if self.terminal_path:
                kwargs["path"] = self.terminal_path

            if not mt5.initialize(**kwargs):
                logger.error(f"MT5初始化失败: {mt5.last_error()}")
                return False

            account = mt5.account_info()
            if account is None:
                logger.error(f"MT5账户信息获取失败: {mt5.last_error()}")
                mt5.shutdown()
                return False

            self._connected = True
            logger.info(f"MT5数据桥接器连接成功 | 账户: {account.login}")
            return True

        except ImportError:
            logger.warning("MT5模块不可用，将使用CSV回退路径")
            return False
        except Exception as e:
            logger.error(f"MT5连接异常: {e}")
            return False

    def disconnect(self):
        """断开MT5连接"""
        if self._mt5 and self._connected:
            self._mt5.shutdown()
            self._connected = False
            logger.info("MT5数据桥接器已断开")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """
        获取OHLCV历史数据

        Args:
            symbol: 交易品种，如 "EURUSD"
            timeframe: 周期，如 "D1", "W1", "MN1", "H4", "H1"
            start: 开始时间
            end: 结束时间

        Returns:
            DataFrame，列: timestamp, open, high, low, close, volume
        """
        if not self._connected:
            raise RuntimeError("MT5未连接，请先调用connect()")

        mt5 = self._mt5
        tf_code = self.TIMEFRAME_MAP.get(timeframe)
        if tf_code is None:
            raise ValueError(f"不支持的周期: {timeframe}，支持的: {list(self.TIMEFRAME_MAP.keys())}")

        # 确保品种可见
        info = mt5.symbol_info(symbol)
        if info is None:
            raise ValueError(f"MT5中找不到品种: {symbol}")
        if not info.visible:
            mt5.symbol_select(symbol, True)

        # 获取数据
        rates = mt5.copy_rates_range(symbol, tf_code, start, end)
        if rates is None or len(rates) == 0:
            logger.warning(f"未获取到数据: {symbol} {timeframe} {start}~{end}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['timestamp'] = self._to_local_timestamp(df['time'])
        df = df.rename(columns={'tick_volume': 'volume'})

        # 标准化列名
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

        logger.info(f"获取数据: {symbol} {timeframe} | {len(df)}条 | {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
        return df

    def fetch_ohlcv_from_pos(
        self,
        symbol: str,
        timeframe: str,
        count: int,
    ) -> pd.DataFrame:
        """
        从当前位置往前获取N条数据

        Args:
            symbol: 交易品种
            timeframe: 周期
            count: 条数

        Returns:
            DataFrame
        """
        if not self._connected:
            raise RuntimeError("MT5未连接")

        mt5 = self._mt5
        tf_code = self.TIMEFRAME_MAP.get(timeframe)
        if tf_code is None:
            raise ValueError(f"不支持的周期: {timeframe}")

        rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, count)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['timestamp'] = self._to_local_timestamp(df['time'])
        df = df.rename(columns={'tick_volume': 'volume'})
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    def fetch_multi_timeframe(
        self,
        symbol: str,
        timeframes: List[str],
        start: datetime,
        end: datetime,
    ) -> Dict[str, pd.DataFrame]:
        """
        一次性获取多周期数据

        Args:
            symbol: 交易品种
            timeframes: 周期列表，如 ["MN1", "W1", "D1"]
            start: 开始时间
            end: 结束时间

        Returns:
            Dict[timeframe, DataFrame]
        """
        result = {}
        for tf in timeframes:
            try:
                df = self.fetch_ohlcv(symbol, tf, start, end)
                result[tf] = df
            except Exception as e:
                logger.error(f"获取 {symbol} {tf} 数据失败: {e}")
                result[tf] = pd.DataFrame()
        return result

    def fetch_tick_data(
        self,
        symbol: str,
        date: datetime,
    ) -> pd.DataFrame:
        """
        获取指定日期的tick数据

        Args:
            symbol: 交易品种
            date: 日期

        Returns:
            DataFrame，列: timestamp, bid, ask, last, volume
        """
        if not self._connected:
            raise RuntimeError("MT5未连接")

        mt5 = self._mt5
        start = datetime.combine(date.date(), datetime.min.time())
        end = start + timedelta(days=1)

        ticks = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(ticks)
        df['timestamp'] = self._to_local_timestamp(df['time'])
        return df[['timestamp', 'bid', 'ask', 'last', 'volume']]

    def get_available_symbols(self) -> List[str]:
        """获取MT5中可用的品种列表"""
        if not self._connected:
            return []

        mt5 = self._mt5
        symbols = mt5.symbols_get()
        if symbols is None:
            return []
        return [s.name for s in symbols]

    @property
    def is_connected(self) -> bool:
        return self._connected


# ============================================================================
# DuckDB 数据存储
# ============================================================================

class DataStore:
    """
    数据缓存层

    使用 DuckDB 作为本地缓存，支持:
    - 按品种+周期分区存储
    - 自动去重和增量更新
    - 数据质量元数据记录
    - SQL查询接口

    数据库结构:
    - ohlcv_data: 主表，存储所有OHLCV数据
    - data_quality: 数据质量记录表
    - data_metadata: 数据元信息表（最后更新时间等）

    使用方式:
        store = DataStore("data/cache.duckdb")
        store.save_ohlcv("EURUSD", "D1", df)
        df = store.load_ohlcv("EURUSD", "D1", start, end)
        report = store.get_data_quality_report("EURUSD", "D1")
    """

    def __init__(self, db_path: str = "data/cache.duckdb"):
        self.db_path = db_path
        self._conn = None
        # 延迟初始化，首次使用时创建连接

    def _get_connection(self):
        """获取DuckDB连接（延迟初始化）"""
        if self._conn is None:
            try:
                import duckdb
                # 确保目录存在
                os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
                self._conn = duckdb.connect(self.db_path)
                self._create_tables()
            except ImportError:
                logger.warning("DuckDB未安装，将使用SQLite回退。运行: pip install duckdb")
                import sqlite3
                os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
                self._conn = sqlite3.connect(self.db_path.replace(".duckdb", ".sqlite"))
                self._create_tables_sqlite()
        return self._conn

    def _create_tables(self):
        """创建数据表（DuckDB语法）"""
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_data (
                symbol VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_quality (
                symbol VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_rows INTEGER,
                missing_values INTEGER,
                gap_days INTEGER,
                duplicate_rows INTEGER,
                price_anomalies INTEGER,
                is_valid BOOLEAN,
                PRIMARY KEY (symbol, timeframe, check_date)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_metadata (
                symbol VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                last_update TIMESTAMP,
                row_count INTEGER,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                source VARCHAR,
                PRIMARY KEY (symbol, timeframe)
            )
        """)
        conn.commit()

    def _create_tables_sqlite(self):
        """创建数据表（SQLite语法）"""
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_data (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_quality (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                check_date TEXT DEFAULT CURRENT_TIMESTAMP,
                total_rows INTEGER,
                missing_values INTEGER,
                gap_days INTEGER,
                duplicate_rows INTEGER,
                price_anomalies INTEGER,
                is_valid INTEGER,
                PRIMARY KEY (symbol, timeframe, check_date)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_metadata (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                last_update TEXT,
                row_count INTEGER,
                start_date TEXT,
                end_date TEXT,
                source TEXT,
                PRIMARY KEY (symbol, timeframe)
            )
        """)
        conn.commit()

    def save_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
        source: str = "mt5",
    ) -> bool:
        """
        保存OHLCV数据，自动处理重复

        Args:
            symbol: 品种
            timeframe: 周期
            df: DataFrame，必须包含 timestamp, open, high, low, close, volume
            source: 数据来源

        Returns:
            是否成功
        """
        if df.empty:
            logger.warning(f"保存空数据: {symbol} {timeframe}")
            return False

        required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")

        conn = self._get_connection()

        # 准备数据
        save_df = df[required].copy()
        save_df['symbol'] = symbol
        save_df['timeframe'] = timeframe
        save_df['timestamp'] = pd.to_datetime(save_df['timestamp'])

        try:
            # 使用UPSERT语义：插入或替换
            # DuckDB支持INSERT OR REPLACE，SQLite也支持
            conn.execute("BEGIN TRANSACTION")

            # 先删除重叠的数据
            start_ts = save_df['timestamp'].min()
            end_ts = save_df['timestamp'].max()
            conn.execute(
                "DELETE FROM ohlcv_data WHERE symbol = ? AND timeframe = ? AND timestamp BETWEEN ? AND ?",
                (symbol, timeframe, start_ts, end_ts)
            )

            # 插入新数据
            for _, row in save_df.iterrows():
                conn.execute(
                    """INSERT INTO ohlcv_data
                       (symbol, timeframe, timestamp, open, high, low, close, volume)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (symbol, timeframe, row['timestamp'], row['open'], row['high'],
                     row['low'], row['close'], row['volume'])
                )

            # 更新元数据
            conn.execute(
                """INSERT OR REPLACE INTO data_metadata
                   (symbol, timeframe, last_update, row_count, start_date, end_date, source)
                   VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)""",
                (symbol, timeframe, len(save_df), start_ts, end_ts, source)
            )

            conn.execute("COMMIT")
            logger.info(f"数据保存成功: {symbol} {timeframe} | {len(save_df)}条")
            return True

        except Exception as e:
            conn.execute("ROLLBACK")
            logger.error(f"数据保存失败: {e}")
            return False

    def load_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        读取OHLCV数据

        Args:
            symbol: 品种
            timeframe: 周期
            start: 开始时间（可选）
            end: 结束时间（可选）

        Returns:
            DataFrame
        """
        conn = self._get_connection()

        query = "SELECT timestamp, open, high, low, close, volume FROM ohlcv_data WHERE symbol = ? AND timeframe = ?"
        params = [symbol, timeframe]

        if start is not None:
            query += " AND timestamp >= ?"
            params.append(start)
        if end is not None:
            query += " AND timestamp <= ?"
            params.append(end)

        query += " ORDER BY timestamp ASC"

        try:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            logger.info(f"数据读取: {symbol} {timeframe} | {len(df)}条")
            return df
        except Exception as e:
            logger.error(f"数据读取失败: {e}")
            return pd.DataFrame()

    def get_data_quality_report(
        self,
        symbol: str,
        timeframe: str,
    ) -> DataQualityReport:
        """
        获取数据质量报告

        检查项:
        - 缺失值
        - 时间跳空
        - 重复行
        - 价格异常（如high < low, close > high等）
        """
        df = self.load_ohlcv(symbol, timeframe)

        if df.empty:
            return DataQualityReport(
                symbol=symbol, timeframe=timeframe,
                total_rows=0, missing_values=0, gap_days=0,
                duplicate_rows=0, price_anomalies=0, is_valid=False
            )

        # 缺失值
        missing = df.isnull().sum().sum()

        # 重复行
        dups = df.duplicated(subset=['timestamp']).sum()

        # 时间跳空（按交易日计算， Forex周末正常跳空）
        df_sorted = df.sort_values('timestamp')
        expected_days = (df_sorted['timestamp'].max() - df_sorted['timestamp'].min()).days + 1
        actual_days = len(df_sorted)
        gap_days = max(0, expected_days - actual_days)

        # 价格异常
        anomalies = 0
        anomalies += (df['high'] < df['low']).sum()
        anomalies += (df['close'] > df['high']).sum()
        anomalies += (df['close'] < df['low']).sum()
        anomalies += (df['open'] > df['high']).sum()
        anomalies += (df['open'] < df['low']).sum()

        is_valid = (
            len(df) >= 50 and      # 至少50条
            missing == 0 and       # 无缺失值
            anomalies == 0 and     # 无价格异常
            dups == 0              # 无重复
        )

        report = DataQualityReport(
            symbol=symbol,
            timeframe=timeframe,
            total_rows=len(df),
            missing_values=int(missing),
            gap_days=gap_days,
            duplicate_rows=int(dups),
            price_anomalies=int(anomalies),
            start_date=df['timestamp'].min(),
            end_date=df['timestamp'].max(),
            is_valid=is_valid,
        )

        # 保存质量报告
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO data_quality
                   (symbol, timeframe, check_date, total_rows, missing_values,
                    gap_days, duplicate_rows, price_anomalies, is_valid)
                   VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)""",
                (symbol, timeframe, report.total_rows, report.missing_values,
                 report.gap_days, report.duplicate_rows, report.price_anomalies,
                 report.is_valid)
            )
            conn.commit()
        except Exception as e:
            logger.debug(f"保存质量报告失败: {e}")

        return report

    def list_available_data(self) -> pd.DataFrame:
        """列出所有可用的数据"""
        conn = self._get_connection()
        try:
            df = pd.read_sql_query(
                "SELECT * FROM data_metadata ORDER BY symbol, timeframe",
                conn
            )
            return df
        except Exception as e:
            logger.error(f"查询可用数据失败: {e}")
            return pd.DataFrame()

    def delete_data(self, symbol: str, timeframe: str) -> bool:
        """删除指定数据"""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM ohlcv_data WHERE symbol = ? AND timeframe = ?", (symbol, timeframe))
            conn.execute("DELETE FROM data_metadata WHERE symbol = ? AND timeframe = ?", (symbol, timeframe))
            conn.commit()
            logger.info(f"数据已删除: {symbol} {timeframe}")
            return True
        except Exception as e:
            logger.error(f"删除数据失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# 多周期数据对齐器
# ============================================================================

class MultiTimeframeAligner:
    """
    多周期数据对齐器

    核心职责: 确保MN1/W1/D1数据在同一时间戳上对齐，
    为三元组计算提供干净的数据输入。

    对齐规则:
    - D1数据: 每日一根，作为基准
    - W1数据: 周五收盘值对齐到当周所有D1
    - MN1数据: 月末收盘值对齐到当月所有D1

    输出: 每行D1数据附加W1和MN1的OHLCV
    """

    def align(
        self,
        d1_df: pd.DataFrame,
        w1_df: pd.DataFrame,
        mn1_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        将W1和MN1数据对齐到D1时间轴

        Args:
            d1_df: D1数据，列: timestamp, open, high, low, close, volume
            w1_df: W1数据，列: timestamp, open, high, low, close, volume
            mn1_df: MN1数据，列: timestamp, open, high, low, close, volume

        Returns:
            对齐后的DataFrame，每行包含D1 + W1 + MN1数据
        """
        if d1_df.empty:
            raise ValueError("D1数据不能为空")

        # 确保timestamp为datetime
        d1 = d1_df.copy()
        d1['timestamp'] = pd.to_datetime(d1['timestamp'])
        d1 = d1.sort_values('timestamp').reset_index(drop=True)

        # 添加日期列用于对齐
        d1['date'] = d1['timestamp'].dt.date

        # 对齐W1数据
        if not w1_df.empty:
            w1 = w1_df.copy()
            w1['timestamp'] = pd.to_datetime(w1['timestamp'])
            w1 = w1.sort_values('timestamp')

            # 为每个D1行找到对应的W1
            # W1时间戳通常是周五，对齐到当周所有D1
            d1['w1_key'] = d1['timestamp'].apply(self._get_week_key)
            w1['w1_key'] = w1['timestamp'].apply(self._get_week_key)

            # 重命名W1列
            w1_renamed = w1.rename(columns={
                'open': 'w1_open',
                'high': 'w1_high',
                'low': 'w1_low',
                'close': 'w1_close',
                'volume': 'w1_volume',
            })[['w1_key', 'w1_open', 'w1_high', 'w1_low', 'w1_close', 'w1_volume']]

            d1 = d1.merge(w1_renamed, on='w1_key', how='left')
            d1 = d1.drop(columns=['w1_key'])
        else:
            # W1数据缺失，用D1聚合生成
            logger.warning("W1数据缺失，将用D1聚合生成")
            d1 = self._aggregate_w1_from_d1(d1)

        # 对齐MN1数据
        if not mn1_df.empty:
            mn1 = mn1_df.copy()
            mn1['timestamp'] = pd.to_datetime(mn1['timestamp'])
            mn1 = mn1.sort_values('timestamp')

            # MN1时间戳通常是月末，对齐到当月所有D1
            d1['mn1_key'] = d1['timestamp'].dt.to_period('M').astype(str)
            mn1['mn1_key'] = mn1['timestamp'].dt.to_period('M').astype(str)

            mn1_renamed = mn1.rename(columns={
                'open': 'mn1_open',
                'high': 'mn1_high',
                'low': 'mn1_low',
                'close': 'mn1_close',
                'volume': 'mn1_volume',
            })[['mn1_key', 'mn1_open', 'mn1_high', 'mn1_low', 'mn1_close', 'mn1_volume']]

            d1 = d1.merge(mn1_renamed, on='mn1_key', how='left')
            d1 = d1.drop(columns=['mn1_key'])
        else:
            # MN1数据缺失，用D1聚合生成
            logger.warning("MN1数据缺失，将用D1聚合生成")
            d1 = self._aggregate_mn1_from_d1(d1)

        # 清理临时列
        if 'date' in d1.columns:
            d1 = d1.drop(columns=['date'])

        # 验证对齐结果
        self._validate_alignment(d1)

        logger.info(f"多周期对齐完成: D1={len(d1_df)}条 | 输出={len(d1)}行 | 列={list(d1.columns)}")
        return d1

    def _get_week_key(self, ts: datetime) -> str:
        """获取周键值 (年-周号)"""
        year, week, _ = ts.isocalendar()
        return f"{year}-{week:02d}"

    def _aggregate_w1_from_d1(self, d1_df: pd.DataFrame) -> pd.DataFrame:
        """从D1数据聚合W1数据"""
        d1 = d1_df.copy()
        d1['w1_key'] = d1['timestamp'].apply(self._get_week_key)

        # 按周聚合
        w1_agg = d1.groupby('w1_key').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
        }).reset_index()
        w1_agg.columns = ['w1_key', 'w1_open', 'w1_high', 'w1_low', 'w1_close', 'w1_volume']

        d1 = d1.merge(w1_agg, on='w1_key', how='left')
        d1 = d1.drop(columns=['w1_key'])
        return d1

    def _aggregate_mn1_from_d1(self, d1_df: pd.DataFrame) -> pd.DataFrame:
        """从D1数据聚合MN1数据"""
        d1 = d1_df.copy()
        d1['mn1_key'] = d1['timestamp'].dt.to_period('M').astype(str)

        # 按月聚合
        mn1_agg = d1.groupby('mn1_key').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
        }).reset_index()
        mn1_agg.columns = ['mn1_key', 'mn1_open', 'mn1_high', 'mn1_low', 'mn1_close', 'mn1_volume']

        d1 = d1.merge(mn1_agg, on='mn1_key', how='left')
        d1 = d1.drop(columns=['mn1_key'])
        return d1

    def _validate_alignment(self, aligned_df: pd.DataFrame):
        """验证对齐结果"""
        required_w1 = ['w1_open', 'w1_high', 'w1_low', 'w1_close']
        required_mn1 = ['mn1_open', 'mn1_high', 'mn1_low', 'mn1_close']

        missing = []
        for col in required_w1 + required_mn1:
            if col not in aligned_df.columns:
                missing.append(col)

        if missing:
            logger.warning(f"对齐结果缺少列: {missing}")

        # 检查NaN比例
        for col in required_w1 + required_mn1:
            if col in aligned_df.columns:
                nan_ratio = aligned_df[col].isna().mean()
                if nan_ratio > 0.1:
                    logger.warning(f"{col} NaN比例过高: {nan_ratio:.1%}")


# ============================================================================
# 便捷函数
# ============================================================================

def fetch_and_store_mt5_data(
    symbol: str,
    timeframes: List[str],
    start: datetime,
    end: datetime,
    store_path: str = "data/cache.duckdb",
    terminal_path: Optional[str] = None,
) -> Dict[str, bool]:
    """
    一站式函数: 从MT5获取数据并存储到本地

    Args:
        symbol: 品种
        timeframes: 周期列表
        start: 开始时间
        end: 结束时间
        store_path: 本地存储路径
        terminal_path: MT5终端路径

    Returns:
        Dict[timeframe, 是否成功]
    """
    results = {}

    bridge = MT5DataBridge(terminal_path=terminal_path)
    if not bridge.connect():
        logger.error("MT5连接失败，无法获取数据")
        return {tf: False for tf in timeframes}

    try:
        store = DataStore(store_path)

        for tf in timeframes:
            try:
                df = bridge.fetch_ohlcv(symbol, tf, start, end)
                if not df.empty:
                    success = store.save_ohlcv(symbol, tf, df, source="mt5")
                    results[tf] = success

                    # 生成质量报告
                    if success:
                        report = store.get_data_quality_report(symbol, tf)
                        logger.info(f"数据质量: {symbol} {tf} | 有效={report.is_valid} | 行数={report.total_rows}")
                else:
                    results[tf] = False
            except Exception as e:
                logger.error(f"获取 {tf} 数据失败: {e}")
                results[tf] = False

        store.close()
    finally:
        bridge.disconnect()

    return results


def load_aligned_data(
    symbol: str,
    store_path: str = "data/cache.duckdb",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    从本地存储加载对齐后的多周期数据

    Args:
        symbol: 品种
        store_path: 存储路径
        start: 开始时间
        end: 结束时间

    Returns:
        对齐后的DataFrame
    """
    store = DataStore(store_path)

    d1_df = store.load_ohlcv(symbol, "D1", start, end)
    w1_df = store.load_ohlcv(symbol, "W1", start, end)
    mn1_df = store.load_ohlcv(symbol, "MN1", start, end)

    store.close()

    if d1_df.empty:
        raise ValueError(f"本地无 {symbol} D1 数据，请先获取")

    aligner = MultiTimeframeAligner()
    return aligner.align(d1_df, w1_df, mn1_df)


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Data Layer Test")
    print("=" * 70)

    # 1. 测试 DataStore（使用内存数据库）
    print("\n[1] DataStore 测试")
    store = DataStore(":memory:")

    # 生成测试数据
    np.random.seed(42)
    n_days = 100
    base_price = 1.0850
    dates = pd.date_range(start="2025-01-01", periods=n_days, freq="B")
    prices = base_price + np.cumsum(np.random.randn(n_days) * 0.003)

    test_df = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.randn(n_days) * 0.001,
        'high': prices + abs(np.random.randn(n_days)) * 0.005,
        'low': prices - abs(np.random.randn(n_days)) * 0.005,
        'close': prices,
        'volume': np.random.randint(10000, 100000, n_days),
    })

    success = store.save_ohlcv("EURUSD", "D1", test_df)
    print(f"  保存数据: {'成功' if success else '失败'}")

    loaded = store.load_ohlcv("EURUSD", "D1")
    print(f"  读取数据: {len(loaded)}条")

    report = store.get_data_quality_report("EURUSD", "D1")
    print(f"  数据质量: 有效={report.is_valid} | 行数={report.total_rows} | 异常={report.price_anomalies}")

    store.close()

    # 2. 测试 MultiTimeframeAligner
    print("\n[2] MultiTimeframeAligner 测试")

    # D1数据
    d1 = test_df.copy()

    # W1数据（从D1聚合）
    d1['week'] = d1['timestamp'].apply(lambda x: f"{x.isocalendar()[0]}-{x.isocalendar()[1]:02d}")
    w1 = d1.groupby('week').agg({
        'timestamp': 'last',
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
    }).reset_index(drop=True)

    # MN1数据（从D1聚合）
    d1['month'] = d1['timestamp'].dt.to_period('M').astype(str)
    mn1 = d1.groupby('month').agg({
        'timestamp': 'last',
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
    }).reset_index(drop=True)

    aligner = MultiTimeframeAligner()
    aligned = aligner.align(d1[['timestamp', 'open', 'high', 'low', 'close', 'volume']], w1, mn1)

    print(f"  D1行数: {len(d1)}")
    print(f"  W1行数: {len(w1)}")
    print(f"  MN1行数: {len(mn1)}")
    print(f"  对齐后行数: {len(aligned)}")
    print(f"  对齐后列: {list(aligned.columns)}")
    print(f"  W1 close NaN比例: {aligned['w1_close'].isna().mean():.1%}")
    print(f"  MN1 close NaN比例: {aligned['mn1_close'].isna().mean():.1%}")

    print("\n[3] 对齐结果预览")
    print(aligned[['timestamp', 'close', 'w1_close', 'mn1_close']].tail(10).to_string(index=False))

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
