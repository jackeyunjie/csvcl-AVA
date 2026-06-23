"""
H1 State 数据库 - H1 视角 Agent 快照

每行 = 1 根 H1 K 线，包含本周期及以上结构周期在 H1 视角下的 state_hex：
  timestamp(H1) | MN1@H1 | W1@H1 | D1@H1 | H4@H1 | H1@H1 | durations

架构契约：
  - 周期(structure_tf)和视角(view_tf)是正交维度。
  - H1 视角 Agent 使用 H1 timestamp/H1 close 作为观察基准。
  - base/trend/volatility 来自各结构周期自身。
  - position 必须使用 H1 close vs 各结构周期 SR。

注意：不能把 MN1/W1/D1/H4/H1 各自原生视角 state 简单拼接后称为 H1 视角。
详见 docs/STATE_VIEWPOINT_AGENT_CONTRACT.md。
"""

import logging
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_engine.state_hex_engine import StateHexEngine, StateHexQuintuplet

logger = logging.getLogger("h1_state_db")

# 所有需要的周期
ALL_TIMEFRAMES = ["MN1", "W1", "D1", "H4", "H1", "M15"]

# 扩展品种支持
EXTENDED_SYMBOLS = [
    "US_30", "US_500", "US_TECH100",
    "HK_50", "CHINA_A50",
    "XAUUSD", "USOIL", "BTCUSD",
    "EURUSD",
]


class H1StateDB:
    """H1 State 数据库管理器"""

    def __init__(self, db_path: str = "data/h1_state.duckdb"):
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
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS h1_state_snapshot (
                symbol VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                mn1_hex VARCHAR,
                w1_hex VARCHAR,
                d1_hex VARCHAR,
                h4_hex VARCHAR,
                h1_hex VARCHAR,
                mn1_duration INTEGER DEFAULT 0,
                w1_duration INTEGER DEFAULT 0,
                d1_duration INTEGER DEFAULT 0,
                h4_duration INTEGER DEFAULT 0,
                h1_duration INTEGER DEFAULT 0,
                PRIMARY KEY (symbol, timestamp)
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_h1_state_ts
            ON h1_state_snapshot(symbol, timestamp)
        """)
        logger.info("h1_state_snapshot 表初始化完成")

    def save_quintuplets(
        self, symbol: str, quintuplets: List[StateHexQuintuplet]
    ) -> int:
        """保存五元组到数据库"""
        if not quintuplets:
            return 0

        conn = self._get_conn()

        # 删除旧数据（相同 symbol + 时间范围）
        min_ts = quintuplets[0].timestamp
        max_ts = quintuplets[-1].timestamp

        # 批量插入
        rows = []
        for q in quintuplets:
            rows.append((
                symbol, q.timestamp,
                q.mn1_hex, q.w1_hex, q.d1_hex, q.h4_hex, q.h1_hex,
                q.mn1_duration, q.w1_duration, q.d1_duration,
                q.h4_duration, q.h1_duration,
            ))

        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "DELETE FROM h1_state_snapshot WHERE symbol = ? AND timestamp BETWEEN ? AND ?",
                [symbol, min_ts, max_ts]
            )
            conn.executemany(
                """INSERT INTO h1_state_snapshot
                   (symbol, timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex,
                    mn1_duration, w1_duration, d1_duration, h4_duration, h1_duration)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        logger.info(f"[{symbol}] 保存 {len(rows)} 条五元组")
        return len(rows)

    def query(
        self, symbol: str, start: Optional[str] = None, end: Optional[str] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """查询五元组"""
        conn = self._get_conn()
        sql = "SELECT * FROM h1_state_snapshot WHERE symbol = ?"
        params = [symbol]

        if start:
            sql += " AND timestamp >= ?"
            params.append(start)
        if end:
            sql += " AND timestamp <= ?"
            params.append(end)

        sql += f" ORDER BY timestamp DESC LIMIT {limit}"
        return conn.execute(sql, params).fetchdf()

    def get_latest(self, symbol: str) -> Optional[Dict]:
        """获取最新一条五元组"""
        df = self.query(symbol, limit=1)
        if df.empty:
            return None
        return df.iloc[0].to_dict()

    def get_summary(self, symbol: str) -> Dict:
        """获取统计摘要"""
        conn = self._get_conn()
        result = conn.execute(
            """SELECT COUNT(*) as total,
                      MIN(timestamp) as earliest,
                      MAX(timestamp) as latest
               FROM h1_state_snapshot WHERE symbol = ?""",
            [symbol]
        ).fetchone()

        # 各周期 hex 分布
        hex_dist = {}
        for tf in ["mn1_hex", "w1_hex", "d1_hex", "h4_hex", "h1_hex"]:
            dist = conn.execute(
                f"SELECT {tf}, COUNT(*) as cnt FROM h1_state_snapshot WHERE symbol = ? GROUP BY {tf} ORDER BY cnt DESC",
                [symbol]
            ).fetchdf()
            hex_dist[tf] = dict(zip(dist[tf], dist["cnt"]))

        return {
            "symbol": symbol,
            "total_rows": result[0],
            "earliest": str(result[1]) if result[1] else None,
            "latest": str(result[2]) if result[2] else None,
            "hex_distributions": hex_dist,
        }

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


def build_h1_state_from_mt5(
    symbol: str = "EURUSD",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    terminal_path: Optional[str] = None,
    db_path: str = "data/h1_state.duckdb",
) -> Dict:
    """
    从 MT5 拉取数据，计算五元组，存入数据库

    Args:
        symbol: 交易品种
        start: 开始时间（默认 1 年前）
        end: 结束时间（默认当前）
        terminal_path: MT5 终端路径
        db_path: 数据库路径

    Returns:
        {"symbol": ..., "rows": ..., "status": ...}
    """
    from backtest_platform.data_layer import MT5DataBridge

    if start is None:
        start = datetime.now() - timedelta(days=365)
    if end is None:
        end = datetime.now()

    # 连接 MT5
    bridge = MT5DataBridge(terminal_path=terminal_path)
    if not bridge.connect():
        return {"symbol": symbol, "rows": 0, "status": "MT5连接失败"}

    try:
        # 拉取 5 个周期的 OHLCV
        logger.info(f"拉取 {symbol} 多周期数据: {ALL_TIMEFRAMES}")
        multi_data = bridge.fetch_multi_timeframe(symbol, ALL_TIMEFRAMES, start, end)

        for tf in ALL_TIMEFRAMES:
            df = multi_data.get(tf, pd.DataFrame())
            logger.info(f"  {tf}: {len(df)} 条")

        # 初始化引擎
        engine = StateHexEngine()

        # 每个结构周期独立加载 OHLCV；它们共同服务于 H1 视角 Agent。
        # 合规的 H1 视角计算必须在 position 计算时使用 H1 close。
        d1_df = multi_data.get("D1", pd.DataFrame())
        w1_df = multi_data.get("W1", pd.DataFrame())
        mn1_df = multi_data.get("MN1", pd.DataFrame())
        h4_df = multi_data.get("H4", pd.DataFrame())
        h1_df = multi_data.get("H1", pd.DataFrame())

        if d1_df.empty:
            return {"symbol": symbol, "rows": 0, "status": "D1数据为空"}

        # D1 Agent
        engine.add_d1_dataframe(d1_df)

        # W1 Agent（独立数据）
        if not w1_df.empty:
            engine.add_w1_dataframe(w1_df)
        # MN1 Agent（独立数据）
        if not mn1_df.empty:
            engine.add_mn1_dataframe(mn1_df)
        # H4 Agent
        if not h4_df.empty:
            engine.add_h4_dataframe(h4_df)
        # H1 Agent
        if h1_df.empty:
            return {"symbol": symbol, "rows": 0, "status": "H1数据为空"}
        engine.add_h1_dataframe(h1_df)

        # 计算五元组
        quintuplets = engine.compute_quintuplets()
        logger.info(f"计算完成: {len(quintuplets)} 个五元组")

        # 存入数据库
        h1db = H1StateDB(db_path)
        saved = h1db.save_quintuplets(symbol, quintuplets)
        h1db.close()

        return {
            "symbol": symbol,
            "rows": saved,
            "status": "成功",
            "d1_rows": len(d1_df),
            "w1_rows": len(w1_df),
            "mn1_rows": len(mn1_df),
            "h4_rows": len(h4_df),
            "h1_rows": len(h1_df),
        }

    finally:
        bridge.disconnect()


# CLI
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    parser = argparse.ArgumentParser(description="H1 State 数据库")
    parser.add_argument("--symbol", default="EURUSD", help="交易品种")
    parser.add_argument("--days", type=int, default=365, help="拉取天数")
    parser.add_argument("--query", action="store_true", help="查询最新数据")
    parser.add_argument("--summary", action="store_true", help="显示统计摘要")
    parser.add_argument("--db", default="data/h1_state.duckdb", help="数据库路径")
    args = parser.parse_args()

    if args.query:
        h1db = H1StateDB(args.db)
        df = h1db.query(args.symbol, limit=20)
        if df.empty:
            print("无数据")
        else:
            print(df.to_string(index=False))
        h1db.close()

    elif args.summary:
        h1db = H1StateDB(args.db)
        summary = h1db.get_summary(args.symbol)
        import json
        print(json.dumps(summary, indent=2, default=str))
        h1db.close()

    else:
        start = datetime.now() - timedelta(days=args.days)
        result = build_h1_state_from_mt5(
            symbol=args.symbol,
            start=start,
            db_path=args.db,
        )
        print(f"\n结果: {result}")
