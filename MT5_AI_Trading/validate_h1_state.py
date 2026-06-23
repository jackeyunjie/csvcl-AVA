from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Sequence

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "python"))

from ai_engine.h1_state_view import (  # noqa: E402
    DEFAULT_SYMBOLS,
    D1_VIEW_STRUCTURE_ORDER,
    H1_VIEW_STRUCTURE_ORDER,
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


def print_db_stats(conn: duckdb.DuckDBPyConnection) -> None:
    snapshot_count, symbol_count, first_ts, last_ts = conn.execute(
        """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT symbol) AS symbols,
            MIN(timestamp) AS first_ts,
            MAX(timestamp) AS last_ts
        FROM h1_state_snapshots
        """
    ).fetchone()

    dup_count = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT symbol, timestamp, COUNT(*) AS c
            FROM h1_state_snapshots
            GROUP BY symbol, timestamp
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    print(f"rows={snapshot_count} symbols={symbol_count} range={first_ts} -> {last_ts}")
    print(f"duplicates={dup_count}")

    ef_dist = conn.execute(
        """
        SELECT ef_count, COUNT(*) AS cnt
        FROM h1_state_snapshots
        GROUP BY ef_count
        ORDER BY ef_count
        """
    ).fetchdf()
    print("\nef distribution:")
    print(ef_dist.to_string(index=False))

    fwd_count = conn.execute("SELECT COUNT(*) FROM h1_fwd").fetchone()[0]
    slice_count = conn.execute("SELECT COUNT(*) FROM h1_slices").fetchone()[0]
    print(f"\nfwd_rows={fwd_count} slice_rows={slice_count}")

    null_check = conn.execute(
        """
        SELECT
            SUM(CASE WHEN h1_close IS NULL THEN 1 ELSE 0 END) AS null_close,
            SUM(CASE WHEN view_tf <> 'H1' THEN 1 ELSE 0 END) AS non_h1_rows
        FROM h1_state_snapshots
        """
    ).fetchone()
    print(f"null_close={null_check[0]} non_h1_rows={null_check[1]}")


def validate_sample_alignment(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    terminal_path: str | None,
    batch_size: int,
) -> None:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("\nMT5 package not installed; skipping live alignment check.")
        return

    init_kwargs = {"timeout": 60000}
    if terminal_path:
        init_kwargs["path"] = terminal_path
    if not mt5.initialize(**init_kwargs):
        print(f"\nMT5 initialize failed; skipping live alignment check: {mt5.last_error()}")
        return

    try:
        tf_map = build_timeframe_map(mt5)
        mt5.symbol_select(symbol, True)

        frames = {}
        for tf in H1_VIEW_STRUCTURE_ORDER:
            frames[tf] = fetch_rates_batched(mt5, symbol, tf_map[tf], 5000 if tf != "H1" else 120000, batch_size=batch_size)

        structures = {tf: compute_feature_series(frames[tf], tf) for tf in H1_VIEW_STRUCTURE_ORDER}
        h1_view = build_view_snapshot_frame(
            symbol=symbol,
            structure_series=structures,
            view_series=structures["H1"],
            structure_order=H1_VIEW_STRUCTURE_ORDER,
            close_field_name="view_close",
        )
        d1_view = build_view_snapshot_frame(
            symbol=symbol,
            structure_series={k: structures[k] for k in D1_VIEW_STRUCTURE_ORDER},
            view_series=structures["D1"],
            structure_order=D1_VIEW_STRUCTURE_ORDER,
            close_field_name="view_close",
        )

        h1_db = conn.execute(
            """
            SELECT timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex, h1_close
            FROM h1_state_snapshots
            WHERE symbol = ?
            ORDER BY timestamp
            """,
            [symbol],
        ).fetchdf()

        if h1_db.empty or d1_view.empty:
            print(f"\nNo data available for sample symbol {symbol}; skipping alignment check.")
            return

        h1_db["timestamp"] = pd.to_datetime(h1_db["timestamp"])
        h1_view["timestamp"] = pd.to_datetime(h1_view["timestamp"])
        d1_view["timestamp"] = pd.to_datetime(d1_view["timestamp"])
        frames["D1"]["timestamp"] = pd.to_datetime(frames["D1"]["timestamp"])
        frames["H1"]["timestamp"] = pd.to_datetime(frames["H1"]["timestamp"])

        aligned = pd.merge(
            d1_view[["timestamp", "mn1_hex", "w1_hex", "d1_hex", "view_close"]],
            h1_db[["timestamp", "mn1_hex", "w1_hex", "d1_hex", "h1_close"]],
            on="timestamp",
            how="inner",
            suffixes=("_d1", "_h1"),
        )

        if aligned.empty:
            print(f"\nNo aligned D1 timestamps for {symbol}; skipping state equality check.")
            return

        match_mask = (
            (aligned["mn1_hex_d1"] == aligned["mn1_hex_h1"])
            & (aligned["w1_hex_d1"] == aligned["w1_hex_h1"])
            & (aligned["d1_hex_d1"] == aligned["d1_hex_h1"])
        )
        close_mask = (aligned["view_close"] - aligned["h1_close"]).abs() < 1e-9

        print(f"\nSample alignment for {symbol}:")
        print(f"  aligned_rows={len(aligned)}")
        print(f"  hex_match_rows={int(match_mask.sum())}")
        print(f"  close_match_rows={int(close_mask.sum())}")
        print("  latest aligned rows:")
        print(
            aligned.tail(5)[
                [
                    "timestamp",
                    "mn1_hex_d1",
                    "w1_hex_d1",
                    "d1_hex_d1",
                    "mn1_hex_h1",
                    "w1_hex_h1",
                    "d1_hex_h1",
                ]
            ].to_string(index=False)
        )
    finally:
        mt5.shutdown()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate H1 viewpoint state database")
    parser.add_argument("--db", default="data/hermass_h1_state.db", help="DuckDB path")
    parser.add_argument("--symbol", default="EURUSD", help="sample symbol for live alignment check")
    parser.add_argument("--terminal", default=None, help="MT5 terminal path")
    parser.add_argument("--batch-size", type=int, default=5000, help="MT5 fetch batch size")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    conn = duckdb.connect(str(Path(args.db)), read_only=True)
    try:
        print_db_stats(conn)
        validate_sample_alignment(conn, args.symbol, args.terminal, args.batch_size)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
