"""
M15 State 数据库 - M15 视角 Agent 快照

每行 = 1 根 M15 K 线，包含本周期及以上结构周期在 M15 视角下的 state_hex：
  timestamp(M15) | MN1@M15 | W1@M15 | D1@M15 | H4@M15 | H1@M15 | M30@M15 | M15@M15

关键差异：
- 时间基准：M15（不是 H1）
- 周期覆盖：MN1/W1/D1/H4/H1/M30/M15（7 个结构周期）
- SR突破判断：M15 close vs 各结构周期支撑阻力位
- 独立 Agent：M15 是一套完整视角系统，不是给 H1 系统多加一列

架构契约：
  - base/trend/volatility 来自各结构周期自身。
  - position 必须使用 M15 close vs 各结构周期 SR。

详见 docs/STATE_VIEWPOINT_AGENT_CONTRACT.md。
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger("m15_state_db")

# M15系统所有周期
M15_TIMEFRAMES = ["MN1", "W1", "D1", "H4", "H1", "M30", "M15"]


@dataclass
class SRLevel:
    """支撑阻力位"""
    timeframe: str      # 来自哪个周期
    level_type: str     # "support" | "resistance" | "pivot"
    price: float
    strength: int       # 1-5，基于触及次数
    touches: int        # 触及次数
    last_touch: datetime


@dataclass
class M15StateHex:
    """M15 视角下的多结构周期 State Hex 值"""
    timestamp: datetime
    mn1_hex: str
    w1_hex: str
    d1_hex: str
    h4_hex: str
    h1_hex: str
    m30_hex: str
    m15_hex: str
    # SR突破信息
    sr_breakout: bool      # 是否有SR突破
    breakout_direction: str  # "up" | "down" | "none"
    breakout_tf: str       # 突破发生在哪个周期
    # 各周期SR位
    sr_levels: List[SRLevel]


class M15StateDB:
    """M15 State 数据库管理器"""

    def __init__(self, db_path: str = "data/m15_state.duckdb"):
        self.db_path = db_path
        self._conn = None

    def _get_conn(self):
        if self._conn is None:
            import duckdb
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            self._conn = duckdb.connect(self.db_path)
            self._create_tables()
        return self._conn

    def _create_tables(self):
        """创建M15 State表"""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS m15_state_snapshot (
                symbol VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                mn1_hex VARCHAR,
                w1_hex VARCHAR,
                d1_hex VARCHAR,
                h4_hex VARCHAR,
                h1_hex VARCHAR,
                m30_hex VARCHAR,
                m15_hex VARCHAR,
                -- SR突破信息
                sr_breakout BOOLEAN DEFAULT FALSE,
                breakout_direction VARCHAR,
                breakout_tf VARCHAR,
                -- 持续时间
                mn1_duration INTEGER DEFAULT 0,
                w1_duration INTEGER DEFAULT 0,
                d1_duration INTEGER DEFAULT 0,
                h4_duration INTEGER DEFAULT 0,
                h1_duration INTEGER DEFAULT 0,
                m30_duration INTEGER DEFAULT 0,
                m15_duration INTEGER DEFAULT 0,
                PRIMARY KEY (symbol, timestamp)
            )
        """)

        # SR水平表（单独存储，一对多）
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS m15_sr_levels (
                id INTEGER,
                symbol VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                timeframe VARCHAR,
                level_type VARCHAR,
                price DOUBLE,
                strength INTEGER,
                touches INTEGER
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_m15_state_ts
            ON m15_state_snapshot(symbol, timestamp)
        """)
        logger.info("m15_state_snapshot 表初始化完成")

    def calc_sr_levels(self, df: pd.DataFrame, timeframe: str) -> List[SRLevel]:
        """
        计算支撑阻力位

        方法：
        1. 枢轴点: (High + Low + Close) / 3
        2. 支撑/阻力: 近期高低点
        3. 强度: 触及次数
        """
        if df.empty or len(df) < 20:
            return []

        sr_levels = []
        recent = df.tail(20)  # 最近20根K线

        # 枢轴点
        pivot = (recent['high'].iloc[-1] + recent['low'].iloc[-1] + recent['close'].iloc[-1]) / 3
        sr_levels.append(SRLevel(
            timeframe=timeframe,
            level_type="pivot",
            price=pivot,
            strength=3,
            touches=1,
            last_touch=pd.Timestamp(recent.index[-1]) if hasattr(recent.index[-1], 'to_pydatetime') else datetime.now()
        ))

        # 近期高点 = 阻力
        resistance = recent['high'].max()
        res_touches = (recent['high'] >= resistance * 0.999).sum()
        sr_levels.append(SRLevel(
            timeframe=timeframe,
            level_type="resistance",
            price=resistance,
            strength=min(5, max(1, res_touches)),
            touches=res_touches,
            last_touch=datetime.now()
        ))

        # 近期低点 = 支撑
        support = recent['low'].min()
        sup_touches = (recent['low'] <= support * 1.001).sum()
        sr_levels.append(SRLevel(
            timeframe=timeframe,
            level_type="support",
            price=support,
            strength=min(5, max(1, sup_touches)),
            touches=sup_touches,
            last_touch=datetime.now()
        ))

        return sr_levels

    def check_sr_breakout(self, m15_close: float, sr_levels: List[SRLevel]) -> Tuple[bool, str, str]:
        """
        检查M15收盘价是否突破SR位

        返回: (是否突破, 方向, 突破周期)
        """
        if not sr_levels:
            return False, "none", ""

        # 找最近的SR位
        nearest_dist = float('inf')
        nearest_level = None

        for level in sr_levels:
            dist = abs(m15_close - level.price) / level.price
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_level = level

        if nearest_level is None:
            return False, "none", ""

        # 突破阈值：0.1%
        threshold = 0.001

        if nearest_dist < threshold:
            # 接近SR位，检查方向
            if m15_close > nearest_level.price and nearest_level.level_type == "resistance":
                return True, "up", nearest_level.timeframe
            elif m15_close < nearest_level.price and nearest_level.level_type == "support":
                return True, "down", nearest_level.timeframe

        return False, "none", ""

    def calc_state_hex(
        self,
        ohlc_df: pd.DataFrame,
        timeframe: str,
        viewpoint_close: Optional[float] = None,
    ) -> str:
        """
        计算单个周期的state_hex

        编码（与H1系统一致）：
        - bit 0 (+1): volatility 波动活跃
        - bit 1 (+2): breakout 关键位突破
        - bit 2 (+4): trend 趋势触发
        - bit 3 (+8): base 非收缩状态
        - 正号: 看涨，负号: 看跌
        """
        if ohlc_df.empty or len(ohlc_df) < 5:
            return "0"

        df = ohlc_df.copy()

        # 计算指标
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values

        # 1. 布林带宽 (base)
        bb_period = min(20, len(df))
        sma = np.mean(close[-bb_period:])
        std = np.std(close[-bb_period:])
        bb_width = (2 * std) / sma if sma > 0 else 0

        # 2. 波动率 (volatility)
        atr = np.mean(high[-5:] - low[-5:])
        atr_pct = atr / close[-1] if close[-1] > 0 else 0
        is_volatile = atr_pct > 0.001  # 0.1%

        view_close = close[-1] if viewpoint_close is None else viewpoint_close

        # 3. 趋势 (trend)
        if len(close) >= 10:
            slope = (close[-1] - close[-10]) / close[-10] if close[-10] > 0 else 0
            has_trend = abs(slope) > 0.005  # 0.5%
            is_bull = slope > 0
        else:
            has_trend = False
            is_bull = True

        # 4. 突破 (breakout) - 视角收盘价 vs 结构周期近期高低点
        is_breakout = view_close > high[-5:].max() or view_close < low[-5:].min()

        # 组合hex值
        val = 0
        if is_volatile:
            val += 1
        if is_breakout:
            val += 2
        if has_trend:
            val += 4
        if bb_width > 0.01:  # 非收缩
            val += 8

        # 方向
        sign = "" if is_bull else "-"
        return f"{sign}{val:X}"

    def save_m15_states(self, symbol: str, states: List[M15StateHex]) -> int:
        """保存M15 State到数据库"""
        if not states:
            return 0

        conn = self._get_conn()
        saved = 0
        min_ts = min(state.timestamp for state in states)
        max_ts = max(state.timestamp for state in states)

        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "DELETE FROM m15_sr_levels WHERE symbol = ? AND timestamp BETWEEN ? AND ?",
                [symbol, min_ts, max_ts],
            )
            next_sr_id = conn.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM m15_sr_levels"
            ).fetchone()[0]

            for state in states:
                conn.execute("""
                    INSERT OR REPLACE INTO m15_state_snapshot
                    (symbol, timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex, m30_hex, m15_hex,
                     sr_breakout, breakout_direction, breakout_tf)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, state.timestamp, state.mn1_hex, state.w1_hex,
                    state.d1_hex, state.h4_hex, state.h1_hex, state.m30_hex,
                    state.m15_hex, state.sr_breakout, state.breakout_direction,
                    state.breakout_tf
                ))

                for sr in state.sr_levels:
                    conn.execute("""
                        INSERT INTO m15_sr_levels
                        (id, symbol, timestamp, timeframe, level_type, price, strength, touches)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        int(next_sr_id),
                        str(symbol),
                        state.timestamp,
                        str(sr.timeframe),
                        str(sr.level_type),
                        float(sr.price),
                        int(sr.strength),
                        int(sr.touches),
                    ))
                    next_sr_id += 1

                saved += 1
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        logger.info(f"{symbol} 保存 {saved} 条M15 State")
        return saved

    def get_latest(self, symbol: str) -> Optional[Dict]:
        """获取最新M15 State"""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT * FROM m15_state_snapshot
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, [symbol]).fetchone()

        if not row:
            return None

        cols = [desc[0] for desc in conn.description]
        return dict(zip(cols, row))

    def get_sr_levels(self, symbol: str, timestamp: datetime) -> List[SRLevel]:
        """获取指定时间的SR位"""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT timeframe, level_type, price, strength, touches
            FROM m15_sr_levels
            WHERE symbol = ? AND timestamp = ?
        """, [symbol, timestamp]).fetchall()

        return [
            SRLevel(
                timeframe=r[0],
                level_type=r[1],
                price=r[2],
                strength=r[3],
                touches=r[4],
                last_touch=timestamp,
            )
            for r in rows
        ]

    def get_summary(self, symbol: str) -> Dict:
        """获取品种数据摘要"""
        conn = self._get_conn()
        result = conn.execute(
            "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM m15_state_snapshot WHERE symbol = ?",
            [symbol]
        ).fetchone()
        return {
            "symbol": symbol,
            "total_rows": result[0],
            "earliest": str(result[1]) if result[1] else None,
            "latest": str(result[2]) if result[2] else None,
        }

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("M15StateDB 连接已关闭")


class M15StateEngine:
    """M15 视角 State 计算引擎"""

    def __init__(self):
        self.db = M15StateDB()

    @staticmethod
    def _slice_to_timestamp(df: pd.DataFrame, ts) -> pd.DataFrame:
        """Return rows whose timestamp is known at or before the view timestamp."""
        if df is None or df.empty:
            return pd.DataFrame()

        if 'timestamp' in df.columns:
            result = df.copy()
            result['timestamp'] = pd.to_datetime(result['timestamp'])
            return result[result['timestamp'] <= pd.to_datetime(ts)].sort_values('timestamp')

        if isinstance(df.index, pd.DatetimeIndex):
            return df.loc[df.index <= pd.to_datetime(ts)].sort_index()

        return df

    def process_symbol(self, symbol: str, multi_tf_data: Dict[str, pd.DataFrame]) -> int:
        """
        处理单个品种的M15 State计算

        multi_tf_data: {
            "MN1": df, "W1": df, "D1": df, "H4": df,
            "H1": df, "M30": df, "M15": df
        }
        """
        m15_df = multi_tf_data.get("M15")
        if m15_df is None or m15_df.empty:
            logger.warning(f"{symbol} 无M15数据")
            return 0

        states = []

        for idx in range(len(m15_df)):
            if 'timestamp' in m15_df.columns:
                ts = pd.to_datetime(m15_df['timestamp'].iloc[idx])
            else:
                ts = m15_df.index[idx] if hasattr(m15_df.index[idx], 'to_pydatetime') else idx

            # 计算各结构周期在 M15 视角下的 state_hex。
            # 合规实现中，position 使用当前 M15 close vs 结构周期 SR。
            hex_values = {}
            for tf in M15_TIMEFRAMES:
                df = multi_tf_data.get(tf)
                if df is not None and not df.empty:
                    tf_data = self._slice_to_timestamp(df, ts)
                    if tf_data.empty:
                        hex_values[tf.lower() + '_hex'] = "N/A"
                    else:
                        hex_values[tf.lower() + '_hex'] = self.db.calc_state_hex(
                            tf_data, tf, viewpoint_close=m15_df['close'].iloc[idx]
                        )
                else:
                    hex_values[tf.lower() + '_hex'] = "N/A"

            # 计算SR位（基于所有周期）
            all_sr = []
            for tf in ["MN1", "W1", "D1", "H4", "H1", "M30"]:
                df = multi_tf_data.get(tf)
                if df is not None and not df.empty:
                    tf_data = self._slice_to_timestamp(df, ts)
                    sr_list = self.db.calc_sr_levels(tf_data, tf)
                    all_sr.extend(sr_list)

            # 检查SR突破
            m15_close = m15_df['close'].iloc[idx]
            is_breakout, direction, breakout_tf = self.db.check_sr_breakout(m15_close, all_sr)

            state = M15StateHex(
                timestamp=ts,
                mn1_hex=hex_values.get('mn1_hex', 'N/A'),
                w1_hex=hex_values.get('w1_hex', 'N/A'),
                d1_hex=hex_values.get('d1_hex', 'N/A'),
                h4_hex=hex_values.get('h4_hex', 'N/A'),
                h1_hex=hex_values.get('h1_hex', 'N/A'),
                m30_hex=hex_values.get('m30_hex', 'N/A'),
                m15_hex=hex_values.get('m15_hex', 'N/A'),
                sr_breakout=is_breakout,
                breakout_direction=direction,
                breakout_tf=breakout_tf,
                sr_levels=all_sr,
            )
            states.append(state)

        return self.db.save_m15_states(symbol, states)


if __name__ == "__main__":
    # 测试
    db = M15StateDB()
    print("M15 State DB 初始化完成")
    print(f"数据库路径: {db.db_path}")
