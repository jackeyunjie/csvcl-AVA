"""
State 数据库系统 v1.0
=====================
四视角 × 三周期 × N品种 = 完整的 State 时序矩阵

数据库表设计:
  state_snapshots    — 每个品种/视角/周期的每日State值
  state_slices       — 多周期State组合切片(如 MN1=E, W1=F, D1=E → "EFE")
  symbols_registry   — 品种元信息
  platform_sources   — 数据源(MT5#1/MT5#2/MT4)

视角定义:
  D1视角  — position用D1 close (默认, 日线交易者视角)
  W1视角  — position用W1 close (周线自身趋势)
  MN1视角 — position用MN1 close (月线宏观)
  H1视角  — position用H1 close (盘中实时)

周期: MN1(月), W1(周), D1(日), H4(4小时), H1(1小时)

State公式: score = base(8/0) + trend_bit*4 + pos_bit(2/0) + vol_bit(1/0)
"""

import sqlite3
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from pathlib import Path
import logging

logger = logging.getLogger("StateDB")

DB_PATH = Path(r"d:\qoder\csvcl - AVA\MT5_AI_Trading\data\state_db.sqlite")

PERSPECTIVES = ["D1", "W1", "MN1", "H1"]
TIMEFRAMES = ["MN1", "W1", "D1", "H4", "H1"]
PERSPECTIVE_PRICE_TF = {"D1": "D1", "W1": "W1", "MN1": "MN1", "H1": "H1"}

FOCUS_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF",
    "EURJPY", "GBPJPY", "AUDJPY", "EURGBP", "EURCHF", "EURCAD", "GBPCHF",
    "BTCUSD", "ETHUSD", "XRPUSD",
]

@dataclass
class StateSnapshot:
    symbol: str
    perspective: str
    date: str
    mn1_hex: str = ""
    w1_hex: str = ""
    d1_hex: str = ""
    h4_hex: str = ""
    h1_hex: str = ""
    mn1_score: int = 0
    w1_score: int = 0
    d1_score: int = 0
    ef_count: int = 0
    raw_json: str = ""

@dataclass
class StateSlice:
    slice_id: str = ""
    pattern: str = ""
    mn1_hex: str = ""
    w1_hex: str = ""
    d1_hex: str = ""
    forward_return_1d: Optional[float] = None
    forward_return_5d: Optional[float] = None
    forward_return_20d: Optional[float] = None
    occurrence_count: int = 0
    win_rate: Optional[float] = None
    avg_return: Optional[float] = None
    tags: List[str] = field(default_factory=list)

class StateDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS state_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    perspective TEXT NOT NULL,
                    date TEXT NOT NULL,
                    platform TEXT DEFAULT 'AVATRADE_MT5',
                    mn1_hex TEXT, w1_hex TEXT, d1_hex TEXT,
                    h4_hex TEXT, h1_hex TEXT,
                    mn1_score INTEGER, w1_score INTEGER, d1_score INTEGER,
                    h4_score INTEGER, h1_score INTEGER,
                    ef_count INTEGER DEFAULT 0,
                    raw_json TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(symbol, perspective, date, platform)
                );
                CREATE INDEX IF NOT EXISTS idx_state_sym_date
                    ON state_snapshots(symbol, perspective, date);
                CREATE INDEX IF NOT EXISTS idx_state_perspective
                    ON state_snapshots(perspective, date);

                CREATE TABLE IF NOT EXISTS state_slices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slice_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    perspective TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    mn1_hex TEXT, w1_hex TEXT, d1_hex TEXT,
                    forward_return_1d REAL,
                    forward_return_5d REAL,
                    forward_return_20d REAL,
                    occurrence_count INTEGER DEFAULT 1,
                    win_rate REAL,
                    avg_return REAL,
                    tags TEXT DEFAULT '[]',
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_slice_pattern
                    ON state_slices(symbol, perspective, pattern);

                CREATE TABLE IF NOT EXISTS symbols_registry (
                    symbol TEXT PRIMARY KEY,
                    category TEXT,
                    spread_avg REAL,
                    min_lot REAL,
                    platform TEXT DEFAULT 'AVATRADE_MT5',
                    is_active INTEGER DEFAULT 1,
                    last_state_date TEXT
                );

                CREATE TABLE IF NOT EXISTS platform_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    type TEXT,
                    connection_info TEXT,
                    is_online INTEGER DEFAULT 0
                );
            """)
        logger.info(f"StateDB ready: {self.db_path}")

    def insert_snapshot(self, snap: StateSnapshot, platform: str = "AVATRADE_MT5"):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO state_snapshots
                (symbol, perspective, date, platform,
                 mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex,
                 mn1_score, w1_score, d1_score, h4_score, h1_score,
                 ef_count, raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (snap.symbol, snap.perspective, snap.date, platform,
                  snap.mn1_hex, snap.w1_hex, snap.d1_hex,
                  snap.h4_hex, snap.h1_hex,
                  snap.mn1_score, snap.w1_score, snap.d1_score,
                  0, 0, snap.ef_count, snap.raw_json))

    def insert_slice(self, sl: StateSlice, symbol: str, perspective: str):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO state_slices
                (slice_id, symbol, perspective, pattern,
                 mn1_hex, w1_hex, d1_hex,
                 forward_return_1d, forward_return_5d, forward_return_20d,
                 occurrence_count, win_rate, avg_return, tags)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (sl.slice_id, symbol, perspective, sl.pattern,
                  sl.mn1_hex, sl.w1_hex, sl.d1_hex,
                  sl.forward_return_1d, sl.forward_return_5d,
                  sl.forward_return_20d,
                  sl.occurrence_count, sl.win_rate, sl.avg_return,
                  json.dumps(sl.tags)))

    def query_slices_by_pattern(self, symbol: str, perspective: str,
                                 mn1: str = None, w1: str = None, d1: str = None
                                 ) -> List[StateSlice]:
        conditions = ["symbol=?", "perspective=?"]
        params = [symbol, perspective]
        if mn1: conditions.append("mn1_hex=?"); params.append(mn1)
        if w1: conditions.append("w1_hex=?"); params.append(w1)
        if d1: conditions.append("d1_hex=?"); params.append(d1)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM state_slices WHERE {' AND '.join(conditions)} ORDER BY occurrence_count DESC",
                params
            ).fetchall()
            return [_row_to_slice(r) for r in rows]

    def query_latest_snapshot(self, symbol: str, perspective: str = "D1"
                              ) -> Optional[StateSnapshot]:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM state_snapshots WHERE symbol=? AND perspective=? ORDER BY date DESC LIMIT 1",
                (symbol, perspective)
            ).fetchone()
            return _row_to_snapshot(row) if row else None

    def query_snapshots(self, symbol: str, perspective: str = "D1",
                        date_from: str = None, date_to: str = None,
                        limit: int = 100) -> List[StateSnapshot]:
        conditions = ["symbol=?", "perspective=?"]
        params = [symbol, perspective]
        if date_from: conditions.append("date>=?"); params.append(date_from)
        if date_to: conditions.append("date<=?"); params.append(date_to)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM state_snapshots WHERE {' AND '.join(conditions)} ORDER BY date DESC LIMIT ?",
                params + [limit]
            ).fetchall()
            return [_row_to_snapshot(r) for r in rows]

    def query_ef_scan(self, perspective: str = "D1", date: str = None,
                      min_ef: int = 2) -> List[Dict]:
        """扫描所有品种的EF状态"""
        conditions = ["perspective=?", "ef_count>=?"]
        params = [perspective, min_ef]
        if date: conditions.append("date=?"); params.append(date)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT symbol, date, mn1_hex, w1_hex, d1_hex, ef_count FROM state_snapshots WHERE {' AND '.join(conditions)} ORDER BY ef_count DESC, symbol",
                params
            ).fetchall()
            return [dict(r) for r in rows]

    def query_pattern_history(self, symbol: str, perspective: str,
                               mn1: str, w1: str, d1: str) -> List[Dict]:
        """查询某个State组合在历史上出现的所有时间"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT date, mn1_hex, w1_hex, d1_hex, ef_count
                   FROM state_snapshots
                   WHERE symbol=? AND perspective=?
                   AND mn1_hex=? AND w1_hex=? AND d1_hex=?
                   ORDER BY date""",
                (symbol, perspective, mn1, w1, d1)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> Dict:
        with sqlite3.connect(str(self.db_path)) as conn:
            snap_count = conn.execute("SELECT COUNT(*) FROM state_snapshots").fetchone()[0]
            slice_count = conn.execute("SELECT COUNT(*) FROM state_slices").fetchone()[0]
            sym_count = conn.execute("SELECT COUNT(DISTINCT symbol) FROM state_snapshots").fetchone()[0]
            latest = conn.execute(
                "SELECT MAX(date) FROM state_snapshots"
            ).fetchone()[0]
            return {
                "total_snapshots": snap_count,
                "total_slices": slice_count,
                "unique_symbols": sym_count,
                "latest_date": latest,
            }

    def register_symbol(self, symbol: str, category: str = "forex",
                         spread: float = 0, min_lot: float = 0.01,
                         platform: str = "AVATRADE_MT5"):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO symbols_registry (symbol,category,spread_avg,min_lot,platform) VALUES (?,?,?,?,?)",
                (symbol, category, spread, min_lot, platform))

    def get_active_symbols(self) -> List[str]:
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT symbol FROM symbols_registry WHERE is_active=1"
            ).fetchall()
            return [r[0] for r in rows]


def _row_to_snapshot(row) -> StateSnapshot:
    return StateSnapshot(
        symbol=row["symbol"], perspective=row["perspective"],
        date=row["date"],
        mn1_hex=row["mn1_hex"] or "", w1_hex=row["w1_hex"] or "",
        d1_hex=row["d1_hex"] or "", h4_hex=row["h4_hex"] or "",
        mn1_score=row["mn1_score"] or 0, w1_score=row["w1_score"] or 0,
        d1_score=row["d1_score"] or 0,
        ef_count=row["ef_count"] or 0, raw_json=row["raw_json"] or "")

def _row_to_slice(row) -> StateSlice:
    tags = json.loads(row["tags"]) if row["tags"] else []
    return StateSlice(
        slice_id=row["slice_id"], pattern=row["pattern"],
        mn1_hex=row["mn1_hex"] or "", w1_hex=row["w1_hex"] or "",
        d1_hex=row["d1_hex"] or "",
        forward_return_1d=row["forward_return_1d"],
        forward_return_5d=row["forward_return_5d"],
        forward_return_20d=row["forward_return_20d"],
        occurrence_count=row["occurrence_count"] or 0,
        win_rate=row["win_rate"], avg_return=row["avg_return"], tags=tags)
