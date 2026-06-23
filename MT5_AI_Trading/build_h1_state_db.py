from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Sequence

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "python"))

from ai_engine.h1_state_view import (  # noqa: E402
    DEFAULT_SYMBOLS,
    H1_VIEW_STRUCTURE_ORDER,
    TIMEFRAME_BAR_LIMITS,
    build_forward_frame,
    build_slice_frame,
    build_view_snapshot_frame,
    compute_feature_series,
    fetch_rates_batched,
)


def build_timeframe_map(mt5_module) -> Dict[str, int]:
    return {
        "MN1": mt5_module.TIMEFRAME_MN1,
        "W1": mt5_module.TIMEFRAME_W1,
        "D1": mt5_module.TIMEFRAME_D1,
        "H4": mt5_module.TIMEFRAME_H4,
        "H1": mt5_module.TIMEFRAME_H1,
    }


def ensure_tables(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS h1_state_snapshots (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            view_tf VARCHAR DEFAULT 'H1',
            mn1_hex VARCHAR,
            w1_hex VARCHAR,
            d1_hex VARCHAR,
            h4_hex VARCHAR,
            h1_hex VARCHAR,
            mn1_score INTEGER,
            w1_score INTEGER,
            d1_score INTEGER,
            h4_score INTEGER,
            h1_score INTEGER,
            ef_count INTEGER,
            h1_close DOUBLE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_h1_state_snapshots_symbol_ts ON h1_state_snapshots(symbol, timestamp)")


def write_frame(conn: duckdb.DuckDBPyConnection, table_name: str, frame: pd.DataFrame) -> int:
    if frame is None or frame.empty:
        return 0
    if table_name == "h1_state_snapshots":
        frame = frame[
            [
                "symbol",
                "timestamp",
                "view_tf",
                "mn1_hex",
                "w1_hex",
                "d1_hex",
                "h4_hex",
                "h1_hex",
                "mn1_score",
                "w1_score",
                "d1_score",
                "h4_score",
                "h1_score",
                "ef_count",
                "h1_close",
            ]
        ]
    conn.register("tmp_frame", frame)
    conn.execute(f"INSERT INTO {table_name} SELECT * FROM tmp_frame")
    return len(frame)


def get_completed_symbols(conn: duckdb.DuckDBPyConnection) -> set[str]:
    rows = conn.execute("SELECT DISTINCT symbol FROM h1_state_snapshots").fetchall()
    return {row[0] for row in rows}


def rebuild_derived_tables(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("DROP TABLE IF EXISTS h1_fwd")
    conn.execute("DROP TABLE IF EXISTS h1_slices")

    conn.execute(
        """
        CREATE TABLE h1_fwd AS
        SELECT
            symbol,
            timestamp,
            view_tf,
            h1_close,
            LEAD(h1_close, 4) OVER (PARTITION BY symbol ORDER BY timestamp) / h1_close - 1.0 AS fwd_4h,
            LEAD(h1_close, 24) OVER (PARTITION BY symbol ORDER BY timestamp) / h1_close - 1.0 AS fwd_24h,
            LEAD(h1_close, 120) OVER (PARTITION BY symbol ORDER BY timestamp) / h1_close - 1.0 AS fwd_120h
        FROM h1_state_snapshots
        WHERE view_tf = 'H1'
        """
    )

    conn.execute(
        """
        CREATE TABLE h1_slices AS
        WITH joined AS (
            SELECT
                s.symbol,
                s.view_tf,
                s.timestamp,
                s.mn1_hex,
                s.w1_hex,
                s.d1_hex,
                s.h4_hex,
                s.h1_hex,
                s.ef_count,
                f.fwd_4h,
                f.fwd_24h,
                f.fwd_120h
            FROM h1_state_snapshots s
            LEFT JOIN h1_fwd f
                ON s.symbol = f.symbol
               AND s.timestamp = f.timestamp
        )
        SELECT
            symbol,
            view_tf,
            mn1_hex || '_' || w1_hex || '_' || d1_hex || '_' || h4_hex || '_' || h1_hex AS pattern,
            mn1_hex,
            w1_hex,
            d1_hex,
            h4_hex,
            h1_hex,
            COUNT(*) AS occurrence_count,
            AVG(ef_count) AS avg_ef_count,
            AVG(fwd_4h) AS avg_fwd_4h,
            AVG(fwd_24h) AS avg_fwd_24h,
            AVG(fwd_120h) AS avg_fwd_120h
        FROM joined
        GROUP BY
            symbol,
            view_tf,
            mn1_hex,
            w1_hex,
            d1_hex,
            h4_hex,
            h1_hex
        """
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_h1_fwd_symbol_ts ON h1_fwd(symbol, timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_h1_slices_symbol_pattern ON h1_slices(symbol, pattern)")


def build_symbol_frames(mt5_module, symbol: str, tf_map: Dict[str, int], batch_size: int) -> Dict[str, pd.DataFrame]:
    frames: Dict[str, pd.DataFrame] = {}
    for tf, bars in TIMEFRAME_BAR_LIMITS.items():
        rates = fetch_rates_batched(mt5_module, symbol, tf_map[tf], bars, batch_size=batch_size)
        frames[tf] = rates
    return frames


def build_symbol_snapshots(mt5_module, symbol: str, tf_map: Dict[str, int], batch_size: int) -> pd.DataFrame:
    frames = build_symbol_frames(mt5_module, symbol, tf_map, batch_size=batch_size)
    structures = {tf: compute_feature_series(frames[tf], tf) for tf in H1_VIEW_STRUCTURE_ORDER}
    snapshot_frame = build_view_snapshot_frame(
        symbol=symbol,
        structure_series=structures,
        view_series=structures["H1"],
        structure_order=H1_VIEW_STRUCTURE_ORDER,
        close_field_name="h1_close",
    )
    return snapshot_frame


def build_database(db_path: Path, terminal_path: str | None, symbols: Sequence[str], batch_size: int) -> None:
    import MetaTrader5 as mt5

    db_path.parent.mkdir(parents=True, exist_ok=True)

    init_kwargs = {"timeout": 60000}
    if terminal_path:
        init_kwargs["path"] = terminal_path
    if not mt5.initialize(**init_kwargs):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    conn = duckdb.connect(str(db_path))
    try:
        ensure_tables(conn)
        tf_map = build_timeframe_map(mt5)
        completed = get_completed_symbols(conn)

        total_rows = 0
        for index, symbol in enumerate(symbols, start=1):
            if symbol in completed:
                existing = conn.execute(
                    "SELECT COUNT(*) FROM h1_state_snapshots WHERE symbol = ?",
                    [symbol],
                ).fetchone()[0]
                print(f"[{index:02d}/{len(symbols):02d}] {symbol:8s} -> skip ({existing:7d} existing rows)")
                continue

            mt5.symbol_select(symbol, True)
            snapshot_frame = build_symbol_snapshots(mt5, symbol, tf_map, batch_size=batch_size)
            inserted = write_frame(conn, "h1_state_snapshots", snapshot_frame)
            total_rows += inserted
            print(f"[{index:02d}/{len(symbols):02d}] {symbol:8s} -> {inserted:7d} rows")
            conn.commit()

        rebuild_derived_tables(conn)

        stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total_rows,
                COUNT(DISTINCT symbol) AS symbols,
                MIN(timestamp) AS first_ts,
                MAX(timestamp) AS last_ts
            FROM h1_state_snapshots
            """
        ).fetchone()
        print(
            f"\nBuilt {total_rows} rows | db_rows={stats[0]} | symbols={stats[1]} | "
            f"{stats[2]} -> {stats[3]}"
        )
    finally:
        conn.close()
        mt5.shutdown()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build H1 viewpoint state DuckDB")
    parser.add_argument("--db", default="data/hermass_h1_state.db", help="output DuckDB path")
    parser.add_argument("--terminal", default=None, help="MT5 terminal path")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS), help="symbols to build")
    parser.add_argument("--batch-size", type=int, default=5000, help="MT5 fetch batch size")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_database(Path(args.db), args.terminal, args.symbols, args.batch_size)


if __name__ == "__main__":
    main()
