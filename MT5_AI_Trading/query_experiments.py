"""
实验查询工具

用法:
  python query_experiments.py --top 20
  python query_experiments.py --pattern "D1=8"
  python query_experiments.py --quality 70
  python query_experiments.py --compare
  python query_experiments.py --matrix
  python query_experiments.py --report
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_DUCKDB = ROOT / "data" / "experiments.duckdb"
DEFAULT_SQLITE = ROOT / "data" / "experiments.db"
DEFAULT_STATE_DB = ROOT / "data" / "h1_state.duckdb"
DEFAULT_MATRIX_CSV = ROOT / "data" / "strategy_state_matrix.csv"
DEFAULT_MATRIX_SVG = ROOT / "data" / "strategy_state_heatmap.svg"
DEFAULT_REPORT = ROOT / "data" / "strategy_report.md"


@dataclass
class Experiment:
    experiment_id: str
    pattern: str
    direction: str
    hold_bars: int | None
    stop_loss_pct: float | None
    take_profit_pct: float | None
    symbols: str
    total_trades: int
    win_rate: float
    avg_pnl: float
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    avg_hold_bars: float
    sample_per_symbol: float
    year_stability: float
    symbol_stability: float
    quality_score: float
    created_at: str
    status: str = ""

    @property
    def param_key(self) -> str:
        hold = self.hold_bars if self.hold_bars is not None else "NA"
        sl = fmt_num(self.stop_loss_pct)
        tp = fmt_num(self.take_profit_pct)
        return f"hold={hold}/sl={sl}/tp={tp}"


@dataclass
class Trade:
    experiment_id: str
    symbol: str
    direction: str
    entry_time: str
    exit_time: str
    hold_bars: int
    pnl_pct: float
    exit_reason: str


class ExperimentStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.kind = self._detect_kind(db_path)
        self.conn: Any | None = None

    def __enter__(self) -> "ExperimentStore":
        if self.kind == "duckdb":
            import duckdb

            self.conn = duckdb.connect(str(self.db_path), read_only=True)
        else:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.conn is not None:
            self.conn.close()

    @staticmethod
    def _detect_kind(db_path: Path) -> str:
        if db_path.suffix.lower() == ".duckdb":
            return "duckdb"
        return "sqlite"

    def count_experiments(self) -> int:
        return int(self._scalar("SELECT COUNT(*) FROM experiments") or 0)

    def count_trades(self) -> int:
        if self.kind != "duckdb" or not self.table_exists("experiment_trades"):
            return 0
        return int(self._scalar("SELECT COUNT(*) FROM experiment_trades") or 0)

    def table_exists(self, table_name: str) -> bool:
        if self.kind == "duckdb":
            rows = self.conn.execute("SHOW TABLES").fetchall()
            return table_name in {row[0] for row in rows}
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchall()
        return bool(rows)

    def _scalar(self, sql: str, params: Iterable[Any] = ()) -> Any:
        return self.conn.execute(sql, list(params) if self.kind == "duckdb" else tuple(params)).fetchone()[0]

    def query_experiments(
        self,
        *,
        limit: int | None = None,
        pattern: str | None = None,
        min_quality: float | None = None,
        direction: str | None = None,
        symbol: str | None = None,
        distinct_pattern: bool = False,
    ) -> list[Experiment]:
        if self.kind == "duckdb":
            return self._query_duckdb(limit, pattern, min_quality, direction, symbol, distinct_pattern)
        return self._query_sqlite(limit, pattern, min_quality, direction, symbol, distinct_pattern)

    def _query_duckdb(
        self,
        limit: int | None,
        pattern: str | None,
        min_quality: float | None,
        direction: str | None,
        symbol: str | None,
        distinct_pattern: bool,
    ) -> list[Experiment]:
        where = ["COALESCE(quality_score, 0) >= 0"]
        params: list[Any] = []
        if pattern:
            where.append("pattern LIKE ?")
            params.append(f"%{pattern}%")
        if min_quality is not None:
            where.append("quality_score >= ?")
            params.append(min_quality)
        if direction:
            where.append("direction = ?")
            params.append(direction.lower())
        if symbol:
            where.append("symbols LIKE ?")
            params.append(f"%{symbol}%")

        where_sql = " AND ".join(where)
        if distinct_pattern:
            sql = f"""
                WITH ranked AS (
                    SELECT *,
                           ROW_NUMBER() OVER (
                               PARTITION BY pattern
                               ORDER BY quality_score DESC, total_trades DESC, created_at DESC
                           ) AS rn
                    FROM experiments
                    WHERE {where_sql}
                )
                SELECT * FROM ranked
                WHERE rn = 1
                ORDER BY quality_score DESC, total_trades DESC, pattern
            """
        else:
            sql = f"""
                SELECT * FROM experiments
                WHERE {where_sql}
                ORDER BY quality_score DESC, total_trades DESC, created_at DESC
            """
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        rows = self.conn.execute(sql, params).fetchall()
        columns = [col[0] for col in self.conn.description]
        return [experiment_from_mapping(dict(zip(columns, row))) for row in rows]

    def _query_sqlite(
        self,
        limit: int | None,
        pattern: str | None,
        min_quality: float | None,
        direction: str | None,
        symbol: str | None,
        distinct_pattern: bool,
    ) -> list[Experiment]:
        where = ["1=1"]
        params: list[Any] = []
        if pattern:
            where.append("e.state_pattern LIKE ?")
            params.append(f"%{pattern}%")
        if min_quality is not None:
            where.append("COALESCE(r.score, 0) >= ?")
            params.append(min_quality)
        if direction:
            where.append("LOWER(e.direction) = ?")
            params.append(direction.lower())
        if symbol:
            where.append("e.markets LIKE ?")
            params.append(f"%{symbol}%")

        sql = f"""
            SELECT
                e.id AS experiment_id,
                e.name,
                e.state_pattern,
                e.direction AS experiment_direction,
                e.hold_bars AS experiment_hold_bars,
                e.markets,
                e.config_json,
                r.id AS result_id,
                r.total_samples,
                r.win_count,
                r.loss_count,
                r.win_rate,
                r.avg_return,
                r.profit_factor,
                r.sharpe_ratio,
                r.max_drawdown,
                r.score,
                r.is_valid,
                r.result_json,
                r.created_at
            FROM experiments e
            JOIN experiment_results r ON e.id = r.experiment_id
            WHERE {" AND ".join(where)}
            ORDER BY COALESCE(r.score, 0) DESC, r.total_samples DESC, r.created_at DESC
        """
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        rows = [dict(row) for row in self.conn.execute(sql, params).fetchall()]
        experiments = [experiment_from_sqlite_row(row) for row in rows]
        if not distinct_pattern:
            return experiments

        best_by_pattern: dict[str, Experiment] = {}
        for exp in experiments:
            current = best_by_pattern.get(exp.pattern)
            if current is None or (exp.quality_score, exp.total_trades) > (
                current.quality_score,
                current.total_trades,
            ):
                best_by_pattern[exp.pattern] = exp
        return sorted(best_by_pattern.values(), key=lambda exp: (-exp.quality_score, -exp.total_trades))

    def fetch_trades(self, experiment_id: str) -> list[Trade]:
        if self.kind != "duckdb" or not self.table_exists("experiment_trades"):
            return []
        rows = self.conn.execute(
            """
            SELECT experiment_id, symbol, direction, entry_time, exit_time,
                   hold_bars, pnl_pct, exit_reason
            FROM experiment_trades
            WHERE experiment_id = ?
            ORDER BY entry_time, symbol
            """,
            [experiment_id],
        ).fetchall()
        return [
            Trade(
                experiment_id=str(row[0]),
                symbol=str(row[1]),
                direction=str(row[2]),
                entry_time=str(row[3]),
                exit_time=str(row[4]),
                hold_bars=int(row[5] or 0),
                pnl_pct=float(row[6] or 0),
                exit_reason=str(row[7]),
            )
            for row in rows
        ]

    def matrix_rows(self) -> list[Experiment]:
        return self.query_experiments(limit=None, distinct_pattern=False)


class StateBenchmark:
    """Long-only buy-and-hold proxy based on the same H1 state return model used by strategy_miner."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.rows_by_symbol: dict[str, list[tuple[str, float]]] = {}

    def available(self) -> bool:
        return self.db_path.exists()

    def load(self, symbols: Iterable[str]) -> None:
        if not self.available():
            return

        import duckdb

        symbols = sorted({s for s in symbols if s})
        if not symbols:
            return

        conn = duckdb.connect(str(self.db_path), read_only=True)
        try:
            placeholders = ",".join("?" for _ in symbols)
            rows = conn.execute(
                f"""
                SELECT symbol, timestamp, h1_hex
                FROM h1_state_snapshot
                WHERE symbol IN ({placeholders})
                ORDER BY symbol, timestamp
                """,
                symbols,
            ).fetchall()
        finally:
            conn.close()

        grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for symbol, timestamp, h1_hex in rows:
            grouped[str(symbol)].append((str(timestamp), state_long_step(str(h1_hex))))
        self.rows_by_symbol = dict(grouped)

    def return_between(self, symbol: str, entry_time: str, exit_time: str) -> float:
        total = 0.0
        for timestamp, step in self.rows_by_symbol.get(symbol, []):
            if entry_time < timestamp <= exit_time:
                total += step
        return round(total, 3)


def experiment_from_mapping(row: dict[str, Any]) -> Experiment:
    return Experiment(
        experiment_id=str(row.get("experiment_id", "")),
        pattern=str(row.get("pattern", "")),
        direction=str(row.get("direction", "")),
        hold_bars=to_int(row.get("hold_bars")),
        stop_loss_pct=to_float(row.get("stop_loss_pct")),
        take_profit_pct=to_float(row.get("take_profit_pct")),
        symbols=str(row.get("symbols") or ""),
        total_trades=to_int(row.get("total_trades")) or 0,
        win_rate=to_float(row.get("win_rate")) or 0.0,
        avg_pnl=to_float(row.get("avg_pnl")) or 0.0,
        total_pnl=to_float(row.get("total_pnl")) or 0.0,
        sharpe_ratio=to_float(row.get("sharpe_ratio")) or 0.0,
        max_drawdown=to_float(row.get("max_drawdown")) or 0.0,
        profit_factor=to_float(row.get("profit_factor")) or 0.0,
        avg_hold_bars=to_float(row.get("avg_hold_bars")) or 0.0,
        sample_per_symbol=to_float(row.get("sample_per_symbol")) or 0.0,
        year_stability=to_float(row.get("year_stability")) or 0.0,
        symbol_stability=to_float(row.get("symbol_stability")) or 0.0,
        quality_score=to_float(row.get("quality_score")) or 0.0,
        created_at=str(row.get("created_at") or ""),
        status=str(row.get("status") or ""),
    )


def experiment_from_sqlite_row(row: dict[str, Any]) -> Experiment:
    config = parse_json(row.get("config_json"))
    result = parse_json(row.get("result_json"))
    result_config = result.get("config", {}) if isinstance(result.get("config"), dict) else {}
    merged_config = {**config, **result_config}
    result_suffix = row.get("result_id")
    experiment_id = str(row.get("experiment_id") or "")
    if result_suffix is not None:
        experiment_id = f"{experiment_id}#{result_suffix}"

    return Experiment(
        experiment_id=experiment_id,
        pattern=str(merged_config.get("state_pattern") or row.get("state_pattern") or ""),
        direction=str(merged_config.get("direction") or row.get("experiment_direction") or ""),
        hold_bars=to_int(merged_config.get("hold_bars") or row.get("experiment_hold_bars")),
        stop_loss_pct=to_float(merged_config.get("stop_loss_pct")),
        take_profit_pct=to_float(merged_config.get("take_profit_pct")),
        symbols=json.dumps(merged_config.get("markets") or parse_json(row.get("markets")) or [], ensure_ascii=False),
        total_trades=to_int(row.get("total_samples")) or 0,
        win_rate=to_float(row.get("win_rate")) or 0.0,
        avg_pnl=to_float(row.get("avg_return")) or 0.0,
        total_pnl=(to_float(row.get("avg_return")) or 0.0) * (to_int(row.get("total_samples")) or 0),
        sharpe_ratio=to_float(row.get("sharpe_ratio")) or 0.0,
        max_drawdown=to_float(row.get("max_drawdown")) or 0.0,
        profit_factor=to_float(row.get("profit_factor")) or 0.0,
        avg_hold_bars=to_float(merged_config.get("hold_bars")) or 0.0,
        sample_per_symbol=0.0,
        year_stability=0.0,
        symbol_stability=0.0,
        quality_score=to_float(row.get("score")) or 0.0,
        created_at=str(row.get("created_at") or ""),
        status="valid" if row.get("is_valid") else "candidate",
    )


def parse_json(value: Any) -> Any:
    if value is None:
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return {}


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_db_path(value: str | None) -> Path:
    if value:
        path = Path(value)
        return path if path.is_absolute() else (ROOT / path).resolve()
    if DEFAULT_DUCKDB.exists():
        return DEFAULT_DUCKDB
    return DEFAULT_SQLITE


def fmt_num(value: Any, digits: int = 1) -> str:
    number = to_float(value)
    if number is None:
        return "NA"
    if abs(number - int(number)) < 1e-9:
        return str(int(number))
    return f"{number:.{digits}f}"


def fmt_pct(value: Any) -> str:
    number = to_float(value) or 0.0
    return f"{number * 100:.1f}%"


def fmt_score(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return ""
    return f"{number:.1f}"


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def state_long_step(hex_val: str) -> float:
    direction = decode_hex(hex_val).get("dir")
    if direction == "bull":
        return 0.12
    if direction == "bear":
        return -0.18
    return 0.0


def decode_hex(hex_val: str) -> dict[str, Any]:
    if not hex_val or hex_val in ("N/A", ""):
        return {"dir": "neutral", "trend": False, "breakout": False, "squeeze": True, "val": -1}
    is_neg = hex_val.startswith("-")
    clean = hex_val.lstrip("-")
    try:
        val = int(clean, 16)
    except ValueError:
        return {"dir": "neutral", "trend": False, "breakout": False, "squeeze": True, "val": -1}
    has_trend = (val & 4) != 0
    has_pos = (val & 2) != 0
    is_contraction = (val & 8) == 0
    if is_neg:
        direction = "bear"
    elif has_trend or has_pos:
        direction = "bull"
    else:
        direction = "neutral"
    return {
        "dir": direction,
        "trend": has_trend,
        "breakout": has_pos,
        "squeeze": is_contraction and not has_trend and not has_pos,
        "val": val,
    }


def print_experiments(experiments: list[Experiment]) -> None:
    headers = [
        "rank",
        "experiment_id",
        "pattern",
        "direction",
        "hold",
        "sl",
        "tp",
        "trades",
        "win_rate",
        "sharpe",
        "pf",
        "max_dd",
        "quality",
    ]
    rows = []
    for index, exp in enumerate(experiments, start=1):
        rows.append(
            [
                str(index),
                exp.experiment_id,
                exp.pattern,
                exp.direction,
                str(exp.hold_bars or ""),
                fmt_num(exp.stop_loss_pct),
                fmt_num(exp.take_profit_pct),
                str(exp.total_trades),
                fmt_pct(exp.win_rate),
                f"{exp.sharpe_ratio:.2f}",
                f"{exp.profit_factor:.2f}",
                f"{exp.max_drawdown:.2f}",
                fmt_score(exp.quality_score),
            ]
        )
    print_table(headers, rows)


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    if not rows:
        print("No rows.")
        return
    widths = [
        max(len(str(headers[i])), *(len(str(row[i])) for row in rows))
        for i in range(len(headers))
    ]
    print("  ".join(str(headers[i]).ljust(widths[i]) for i in range(len(headers))))
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  ".join(str(row[i]).ljust(widths[i]) for i in range(len(headers))))


def generate_matrix(experiments: list[Experiment], csv_path: Path, svg_path: Path) -> tuple[Path, Path]:
    best: dict[tuple[str, str], Experiment] = {}
    param_sort: dict[str, tuple[int, float, float]] = {}
    patterns: set[str] = set()

    for exp in experiments:
        if exp.quality_score <= 0 or exp.hold_bars is None:
            continue
        key = (exp.pattern, exp.param_key)
        current = best.get(key)
        if current is None or exp.quality_score > current.quality_score:
            best[key] = exp
        patterns.add(exp.pattern)
        param_sort[exp.param_key] = (
            exp.hold_bars or 0,
            exp.stop_loss_pct if exp.stop_loss_pct is not None else 999.0,
            exp.take_profit_pct if exp.take_profit_pct is not None else 999.0,
        )

    sorted_patterns = sorted(
        patterns,
        key=lambda pattern: max(
            (exp.quality_score for (p, _), exp in best.items() if p == pattern),
            default=0,
        ),
        reverse=True,
    )
    sorted_params = sorted(param_sort, key=lambda param: param_sort[param])

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["state_pattern", *sorted_params])
        for pattern in sorted_patterns:
            row = [pattern]
            for param in sorted_params:
                exp = best.get((pattern, param))
                row.append("" if exp is None else f"{exp.quality_score:.1f}")
            writer.writerow(row)

    write_heatmap_svg(sorted_patterns, sorted_params, best, svg_path)
    return csv_path, svg_path


def write_heatmap_svg(
    patterns: list[str],
    params: list[str],
    best: dict[tuple[str, str], Experiment],
    svg_path: Path,
) -> None:
    cell_w = 78
    cell_h = 34
    left = 220
    top = 165
    right = 30
    bottom = 40
    width = left + len(params) * cell_w + right
    height = top + len(patterns) * cell_h + bottom

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Arial,'Microsoft YaHei',sans-serif;font-size:12px;fill:#1f2937}",
        ".small{font-size:10px}.title{font-size:18px;font-weight:700}.label{font-weight:600}",
        "</style>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        '<text x="20" y="32" class="title">Strategy-State 适配矩阵</text>',
        '<text x="20" y="54" class="small">行: State 模式 / 列: hold-sl-tp 参数 / 值: 最优质量分</text>',
    ]

    for col, param in enumerate(params):
        x = left + col * cell_w + cell_w / 2
        y = top - 12
        safe_param = xml_escape(param)
        lines.append(f'<g transform="translate({x:.1f},{y:.1f}) rotate(-50)">')
        lines.append(f'<text class="small" text-anchor="start">{safe_param}</text>')
        lines.append("</g>")

    for row, pattern in enumerate(patterns):
        y = top + row * cell_h
        lines.append(
            f'<text x="{left - 12}" y="{y + 22}" class="label" text-anchor="end">{xml_escape(pattern)}</text>'
        )
        for col, param in enumerate(params):
            x = left + col * cell_w
            exp = best.get((pattern, param))
            value = exp.quality_score if exp is not None else None
            fill = heatmap_color(value)
            stroke = "#e5e7eb"
            lines.append(
                f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" fill="{fill}" stroke="{stroke}"/>'
            )
            if value is not None:
                text_fill = "#ffffff" if value >= 58 else "#111827"
                title = (
                    f"{pattern} | {param} | {exp.direction} | "
                    f"{exp.experiment_id} | Q={value:.1f}"
                )
                lines.append(f"<title>{xml_escape(title)}</title>")
                lines.append(
                    f'<text x="{x + cell_w / 2:.1f}" y="{y + 22}" fill="{text_fill}" '
                    f'text-anchor="middle">{value:.1f}</text>'
                )

    lines.append("</svg>")
    svg_path.write_text("\n".join(lines), encoding="utf-8")


def heatmap_color(value: float | None) -> str:
    if value is None:
        return "#f9fafb"
    low = (254, 243, 199)
    high = (15, 118, 110)
    ratio = max(0.0, min(1.0, value / 80.0))
    rgb = tuple(round(low[i] + (high[i] - low[i]) * ratio) for i in range(3))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def xml_escape(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _extract_h1(pattern: str) -> str:
    for part in pattern.split(","):
        if part.strip().upper().startswith("H1="):
            return part.strip().split("=")[1]
    return ""


def compare_experiments(experiments: list[Experiment]) -> None:
    best_by_pattern: dict[str, Experiment] = {}
    for exp in experiments:
        current = best_by_pattern.get(exp.pattern)
        if current is None or exp.quality_score > current.quality_score:
            best_by_pattern[exp.pattern] = exp

    print("\nBest strategy by State pattern")
    print_experiments(sorted(best_by_pattern.values(), key=lambda exp: -exp.quality_score))

    # H1 vs M30 对比（若数据中存在 M30 则对比，否则对比 H1 内部 hex 分组）
    has_m30 = any("M30=" in exp.pattern for exp in experiments)
    print(f"\nTimeframe comparison ({'M30 vs H1' if has_m30 else 'H1 hex groups (M30 not present)' })")
    group_key = (lambda e: "M30" if "M30=" in e.pattern else "H1") if has_m30 else (lambda e: _extract_h1(e.pattern) or "Other")
    groups: dict[str, list[Experiment]] = defaultdict(list)
    for exp in experiments:
        groups[group_key(exp)].append(exp)

    rows = []
    for grp, items in sorted(groups.items()):
        rows.append(
            [
                grp,
                str(len(items)),
                fmt_pct(sum(exp.win_rate for exp in items) / len(items)),
                f"{sum(exp.quality_score for exp in items) / len(items):.1f}",
                f"{max(exp.quality_score for exp in items):.1f}",
                f"{sum(exp.total_trades for exp in items)}",
            ]
        )
    print_table(["group", "experiments", "avg_win_rate", "avg_quality", "max_quality", "total_trades"], rows)

    buckets: dict[tuple[int | None, float | None, float | None], list[Experiment]] = defaultdict(list)
    for exp in experiments:
        buckets[(exp.hold_bars, exp.stop_loss_pct, exp.take_profit_pct)].append(exp)

    rows = []
    for (hold, sl, tp), items in sorted(
        buckets.items(),
        key=lambda item: (item[0][0] or 0, item[0][1] or 0, item[0][2] or 0),
    ):
        rows.append(
            [
                str(hold or ""),
                fmt_num(sl),
                fmt_num(tp),
                str(len(items)),
                f"{sum(exp.quality_score for exp in items) / len(items):.1f}",
                f"{max(exp.quality_score for exp in items):.1f}",
                fmt_pct(sum(exp.win_rate for exp in items) / len(items)),
            ]
        )

    print("\nParameter sensitivity")
    print_table(["hold", "sl", "tp", "experiments", "avg_quality", "max_quality", "avg_win_rate"], rows)


def export_experiments(experiments: list[Experiment], fmt: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "experiment_id", "pattern", "direction", "hold_bars", "stop_loss_pct",
                "take_profit_pct", "symbols", "total_trades", "win_rate", "avg_pnl",
                "total_pnl", "sharpe_ratio", "max_drawdown", "profit_factor",
                "quality_score", "year_stability", "symbol_stability", "status", "created_at"
            ])
            for exp in experiments:
                writer.writerow([
                    exp.experiment_id, exp.pattern, exp.direction, exp.hold_bars,
                    exp.stop_loss_pct, exp.take_profit_pct, exp.symbols, exp.total_trades,
                    exp.win_rate, exp.avg_pnl, exp.total_pnl, exp.sharpe_ratio,
                    exp.max_drawdown, exp.profit_factor, exp.quality_score,
                    exp.year_stability, exp.symbol_stability, exp.status, exp.created_at
                ])
    elif fmt == "md":
        lines = [
            "# 实验查询结果",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"记录数: {len(experiments)}",
            "",
            "| 排名 | 实验ID | 模式 | 方向 | 持仓 | SL | TP | 交易数 | 胜率 | Sharpe | 盈亏比 | 最大回撤 | 质量分 |",
            "|------|--------|------|------|------|----|----|--------|------|--------|--------|----------|--------|",
        ]
        for index, exp in enumerate(experiments, start=1):
            lines.append(
                f"| {index} | `{exp.experiment_id}` | {md_escape(exp.pattern)} | {exp.direction} | "
                f"{exp.hold_bars}h | {fmt_num(exp.stop_loss_pct)} | {fmt_num(exp.take_profit_pct)} | "
                f"{exp.total_trades} | {fmt_pct(exp.win_rate)} | {exp.sharpe_ratio:.2f} | "
                f"{exp.profit_factor:.2f} | {exp.max_drawdown:.2f} | {exp.quality_score:.1f} |"
            )
        path.write_text("\n".join(lines), encoding="utf-8")
    else:
        raise SystemExit(f"Unsupported export format: {fmt}")
    return path


def summarize_by_symbol(trades: list[Trade]) -> list[list[str]]:
    grouped: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        grouped[trade.symbol].append(trade)
    rows = []
    for symbol, items in sorted(grouped.items()):
        wins = [trade for trade in items if trade.pnl_pct > 0]
        total_pnl = sum(trade.pnl_pct for trade in items)
        rows.append(
            [
                symbol,
                str(len(items)),
                str(len(wins)),
                fmt_pct(len(wins) / len(items) if items else 0),
                f"{total_pnl:.2f}",
                f"{(total_pnl / len(items)) if items else 0:.3f}",
            ]
        )
    return rows


def summarize_by_month(trades: list[Trade]) -> list[list[str]]:
    grouped: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        grouped[trade.entry_time[:7]].append(trade)
    rows = []
    for month, items in sorted(grouped.items()):
        wins = [trade for trade in items if trade.pnl_pct > 0]
        pnls = [trade.pnl_pct for trade in items]
        total_pnl = sum(pnls)
        rows.append(
            [
                month,
                str(len(items)),
                str(len(wins)),
                fmt_pct(len(wins) / len(items) if items else 0),
                f"{total_pnl:.2f}",
                f"{(total_pnl / len(items)) if items else 0:.3f}",
                f"{max(pnls):.3f}" if pnls else "0.000",
                f"{min(pnls):.3f}" if pnls else "0.000",
            ]
        )
    return rows


def baseline_summary(trades: list[Trade], benchmark: StateBenchmark) -> dict[str, float]:
    benchmark_returns = [
        benchmark.return_between(trade.symbol, trade.entry_time, trade.exit_time)
        for trade in trades
    ]
    strategy_returns = [trade.pnl_pct for trade in trades]
    total_strategy = sum(strategy_returns)
    total_benchmark = sum(benchmark_returns)
    return {
        "strategy_total": total_strategy,
        "benchmark_total": total_benchmark,
        "excess_total": total_strategy - total_benchmark,
        "strategy_avg": total_strategy / len(strategy_returns) if strategy_returns else 0.0,
        "benchmark_avg": total_benchmark / len(benchmark_returns) if benchmark_returns else 0.0,
        "strategy_win_rate": len([p for p in strategy_returns if p > 0]) / len(strategy_returns)
        if strategy_returns
        else 0.0,
        "benchmark_win_rate": len([p for p in benchmark_returns if p > 0]) / len(benchmark_returns)
        if benchmark_returns
        else 0.0,
    }


def summarize_by_quarter(trades: list[Trade]) -> list[list[str]]:
    grouped: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        ym = trade.entry_time[:7]
        year = ym[:4]
        month = int(ym[5:7])
        quarter = (month - 1) // 3 + 1
        grouped[f"{year}-Q{quarter}"].append(trade)
    rows = []
    for q, items in sorted(grouped.items()):
        wins = [t for t in items if t.pnl_pct > 0]
        pnls = [t.pnl_pct for t in items]
        total_pnl = sum(pnls)
        rows.append([
            q, str(len(items)), str(len(wins)),
            fmt_pct(len(wins) / len(items) if items else 0),
            f"{total_pnl:.2f}", f"{(total_pnl / len(items)) if items else 0:.3f}",
        ])
    return rows


def exit_reason_analysis(trades: list[Trade]) -> list[list[str]]:
    grouped: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        grouped[trade.exit_reason].append(trade)
    rows = []
    for reason, items in sorted(grouped.items(), key=lambda x: -len(x[1])):
        wins = [t for t in items if t.pnl_pct > 0]
        pnls = [t.pnl_pct for t in items]
        total_pnl = sum(pnls)
        rows.append([
            reason, str(len(items)), str(len(wins)),
            fmt_pct(len(wins) / len(items) if items else 0),
            f"{total_pnl:.2f}", f"{(total_pnl / len(items)) if items else 0:.3f}",
        ])
    return rows


def long_short_summary(experiments: list[Experiment]) -> list[list[str]]:
    longs = [e for e in experiments if e.direction == "long"]
    shorts = [e for e in experiments if e.direction == "short"]
    rows = []
    for label, items in [("long", longs), ("short", shorts)]:
        if not items:
            rows.append([label, "0", "0.0%", "0.0", "0.0", "0"])
            continue
        rows.append([
            label, str(len(items)),
            fmt_pct(sum(e.win_rate for e in items) / len(items)),
            f"{sum(e.quality_score for e in items) / len(items):.1f}",
            f"{max(e.quality_score for e in items):.1f}",
            f"{sum(e.total_trades for e in items)}",
        ])
    return rows


def sl_tp_analysis(experiments: list[Experiment]) -> list[list[str]]:
    buckets: dict[tuple[float | None, float | None], list[Experiment]] = defaultdict(list)
    for exp in experiments:
        buckets[(exp.stop_loss_pct, exp.take_profit_pct)].append(exp)
    rows = []
    for (sl, tp), items in sorted(buckets.items(), key=lambda x: (x[0][0] or 0, x[0][1] or 0)):
        rows.append([
            fmt_num(sl), fmt_num(tp), str(len(items)),
            fmt_pct(sum(e.win_rate for e in items) / len(items)),
            f"{sum(e.quality_score for e in items) / len(items):.1f}",
            f"{max(e.quality_score for e in items):.1f}",
            f"{sum(e.total_trades for e in items)}",
        ])
    return rows


def generate_report(store: ExperimentStore, report_path: Path, matrix_csv: Path, matrix_svg: Path, top_n: int) -> Path:
    top = store.query_experiments(limit=top_n, distinct_pattern=True, min_quality=0.0001)
    all_experiments = store.matrix_rows()
    generate_matrix(all_experiments, matrix_csv, matrix_svg)

    all_symbols: set[str] = set()
    trades_by_exp: dict[str, list[Trade]] = {}
    for exp in top:
        trades = store.fetch_trades(exp.experiment_id)
        trades_by_exp[exp.experiment_id] = trades
        all_symbols.update(trade.symbol for trade in trades)

    benchmark = StateBenchmark(DEFAULT_STATE_DB)
    benchmark.load(all_symbols)

    lines = [
        "# 策略搜索报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 数据概况",
        "",
        f"- 实验库: `{store.db_path.relative_to(ROOT) if store.db_path.is_relative_to(ROOT) else store.db_path}`",
        f"- 实验数: {store.count_experiments()}",
        f"- 交易记录数: {store.count_trades()}",
        f"- Strategy-State 矩阵: `{matrix_csv.relative_to(ROOT)}`",
        f"- Strategy-State 热力图: `{matrix_svg.relative_to(ROOT)}`",
        "",
        f"## Top {len(top)} 策略",
        "",
        "| 排名 | 实验ID | 模式 | 方向 | 持仓 | SL | TP | 交易数 | 胜率 | Sharpe | 盈亏比 | 最大回撤 | 质量分 |",
        "|------|--------|------|------|------|----|----|--------|------|--------|--------|----------|--------|",
    ]

    for index, exp in enumerate(top, start=1):
        lines.append(
            f"| {index} | `{exp.experiment_id}` | {md_escape(exp.pattern)} | {exp.direction} | "
            f"{exp.hold_bars}h | {fmt_num(exp.stop_loss_pct)} | {fmt_num(exp.take_profit_pct)} | "
            f"{exp.total_trades} | {fmt_pct(exp.win_rate)} | {exp.sharpe_ratio:.2f} | "
            f"{exp.profit_factor:.2f} | {exp.max_drawdown:.2f} | {exp.quality_score:.1f} |"
        )

    # 全局做多 vs 做空
    lines.extend([
        "",
        "## 做多 vs 做空 全局统计",
        "",
        "| 方向 | 实验数 | 平均胜率 | 平均质量分 | 最高质量分 | 总交易数 |",
        "|------|--------|----------|------------|------------|----------|",
    ])
    for row in long_short_summary(top):
        lines.append("| " + " | ".join(row) + " |")

    # 止损/止盈参数分析
    lines.extend([
        "",
        "## 止损/止盈参数分析",
        "",
        "| SL | TP | 实验数 | 平均胜率 | 平均质量分 | 最高质量分 | 总交易数 |",
        "|----|----|--------|----------|------------|------------|----------|",
    ])
    for row in sl_tp_analysis(top):
        lines.append("| " + " | ".join(row) + " |")

    lines.extend(
        [
            "",
            "## 与买入持有基准对比",
            "",
            "基准使用与实验一致的 H1 State 收益代理，按每笔交易的 entry/exit 窗口计算 long-only 买入持有收益。",
            "",
            "| 排名 | 实验ID | 模式 | 策略总收益 | 基准总收益 | 超额收益 | 策略均值 | 基准均值 | 策略胜率 | 基准胜率 |",
            "|------|--------|------|------------|------------|----------|----------|----------|----------|----------|",
        ]
    )

    baseline_by_exp: dict[str, dict[str, float]] = {}
    for index, exp in enumerate(top, start=1):
        summary = baseline_summary(trades_by_exp.get(exp.experiment_id, []), benchmark)
        baseline_by_exp[exp.experiment_id] = summary
        lines.append(
            f"| {index} | `{exp.experiment_id}` | {md_escape(exp.pattern)} | "
            f"{summary['strategy_total']:.2f} | {summary['benchmark_total']:.2f} | "
            f"{summary['excess_total']:.2f} | {summary['strategy_avg']:.3f} | "
            f"{summary['benchmark_avg']:.3f} | {fmt_pct(summary['strategy_win_rate'])} | "
            f"{fmt_pct(summary['benchmark_win_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## Top 策略详细追溯",
            "",
        ]
    )

    for index, exp in enumerate(top, start=1):
        trades = trades_by_exp.get(exp.experiment_id, [])
        summary = baseline_by_exp.get(exp.experiment_id, {})
        lines.extend(
            [
                f"### {index}. {exp.pattern} / {exp.direction} / {exp.param_key}",
                "",
                f"- 实验ID: `{exp.experiment_id}`",
                f"- 质量分: {exp.quality_score:.1f}; 胜率: {fmt_pct(exp.win_rate)}; 交易数: {exp.total_trades}",
                f"- 买入持有基准超额: {summary.get('excess_total', 0.0):.2f}",
                "",
                "#### 按品种分解胜率",
                "",
                "| 品种 | 交易数 | 胜笔 | 胜率 | 总收益 | 平均收益 |",
                "|------|--------|------|------|--------|----------|",
            ]
        )
        symbol_rows = summarize_by_symbol(trades)
        if symbol_rows:
            for row in symbol_rows:
                lines.append("| " + " | ".join(row) + " |")
        else:
            lines.append("| N/A | 0 | 0 | 0.0% | 0.00 | 0.000 |")

        lines.extend(
            [
                "",
                "#### 按月份分解稳定性",
                "",
                "| 月份 | 交易数 | 胜笔 | 胜率 | 总收益 | 平均收益 | 最好 | 最差 |",
                "|------|--------|------|------|--------|----------|------|------|",
            ]
        )
        month_rows = summarize_by_month(trades)
        if month_rows:
            for row in month_rows:
                lines.append("| " + " | ".join(row) + " |")
        else:
            lines.append("| N/A | 0 | 0 | 0.0% | 0.00 | 0.000 | 0.000 | 0.000 |")

        lines.extend(
            [
                "",
                "#### 按季度统计胜率稳定性",
                "",
                "| 季度 | 交易数 | 胜笔 | 胜率 | 总收益 | 平均收益 |",
                "|------|--------|------|------|--------|----------|",
            ]
        )
        quarter_rows = summarize_by_quarter(trades)
        if quarter_rows:
            for row in quarter_rows:
                lines.append("| " + " | ".join(row) + " |")
        else:
            lines.append("| N/A | 0 | 0 | 0.0% | 0.00 | 0.000 |")

        lines.extend(
            [
                "",
                "#### 出场原因分析",
                "",
                "| 出场原因 | 交易数 | 胜笔 | 胜率 | 总收益 | 平均收益 |",
                "|----------|--------|------|------|--------|----------|",
            ]
        )
        exit_rows = exit_reason_analysis(trades)
        if exit_rows:
            for row in exit_rows:
                lines.append("| " + " | ".join(row) + " |")
        else:
            lines.append("| N/A | 0 | 0 | 0.0% | 0.00 | 0.000 |")

        lines.extend(
            [
                "",
                "#### 详细交易记录",
                "",
                "| # | 品种 | 方向 | 入场时间 | 出场时间 | 持仓 | 收益 | 出场原因 |",
                "|---|------|------|----------|----------|------|------|----------|",
            ]
        )
        if trades:
            for trade_index, trade in enumerate(trades, start=1):
                lines.append(
                    f"| {trade_index} | {trade.symbol} | {trade.direction} | {trade.entry_time} | "
                    f"{trade.exit_time} | {trade.hold_bars} | {trade.pnl_pct:.3f} | {trade.exit_reason} |"
                )
        else:
            lines.append("| 1 | N/A | N/A | N/A | N/A | 0 | 0.000 | N/A |")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="实验查询工具")
    parser.add_argument("--db", type=str, help="实验库路径，默认优先 data/experiments.duckdb")
    parser.add_argument("--top", type=int, help="显示 Top N 策略")
    parser.add_argument("--pattern", type=str, help="按 State 模式模糊查询，例如 D1=8")
    parser.add_argument("--quality", type=float, help="筛选质量分 >= 指定值")
    parser.add_argument("--direction", type=str, choices=["long", "short"], help="只看做多或做空")
    parser.add_argument("--symbol", type=str, help="按品种模糊查询，例如 US_30")
    parser.add_argument("--compare", action="store_true", help="交叉对比 State 模式和参数表现")
    parser.add_argument("--matrix", action="store_true", help="生成 Strategy-State 矩阵 CSV 和热力图")
    parser.add_argument("--report", action="store_true", help="增强生成 data/strategy_report.md")
    parser.add_argument("--unique-patterns", action="store_true", help="每个 State 模式只显示最佳策略")
    parser.add_argument("--export", type=str, choices=["csv", "md"], help="导出格式: csv 或 md")
    parser.add_argument("--export-path", type=str, help="导出路径 (默认 data/export.<fmt>)")
    parser.add_argument("--matrix-csv", type=str, default=str(DEFAULT_MATRIX_CSV), help="矩阵 CSV 输出路径")
    parser.add_argument("--heatmap", type=str, default=str(DEFAULT_MATRIX_SVG), help="热力图 SVG 输出路径")
    parser.add_argument("--report-path", type=str, default=str(DEFAULT_REPORT), help="报告输出路径")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Experiment DB not found: {db_path}")

    matrix_csv = Path(args.matrix_csv)
    matrix_svg = Path(args.heatmap)
    report_path = Path(args.report_path)
    if not matrix_csv.is_absolute():
        matrix_csv = (ROOT / matrix_csv).resolve()
    if not matrix_svg.is_absolute():
        matrix_svg = (ROOT / matrix_svg).resolve()
    if not report_path.is_absolute():
        report_path = (ROOT / report_path).resolve()

    with ExperimentStore(db_path) as store:
        if args.report:
            top_n = args.top or 10
            path = generate_report(store, report_path, matrix_csv, matrix_svg, top_n)
            print(f"报告已生成: {path}")
            print(f"矩阵 CSV: {matrix_csv}")
            print(f"热力图: {matrix_svg}")
            return 0

        if args.matrix:
            generate_matrix(store.matrix_rows(), matrix_csv, matrix_svg)
            print(f"矩阵 CSV: {matrix_csv}")
            print(f"热力图: {matrix_svg}")

        if args.compare:
            compare_experiments(store.query_experiments(
                min_quality=args.quality,
                direction=args.direction,
                symbol=args.symbol,
            ))

        should_print_query = args.top is not None or args.pattern or args.quality is not None or args.direction or args.symbol
        if should_print_query and not args.compare:
            limit = args.top
            rows = store.query_experiments(
                limit=limit,
                pattern=args.pattern,
                min_quality=args.quality,
                direction=args.direction,
                symbol=args.symbol,
                distinct_pattern=args.unique_patterns,
            )
            if args.export:
                export_path = Path(args.export_path) if args.export_path else ROOT / "data" / f"export.{args.export}"
                export_experiments(rows, args.export, export_path)
                print(f"已导出 {args.export.upper()}: {export_path}")
            else:
                print_experiments(rows)

        if not any([args.top is not None, args.pattern, args.quality is not None, args.direction, args.symbol, args.compare, args.matrix, args.report]):
            rows = store.query_experiments(limit=20, distinct_pattern=args.unique_patterns)
            print_experiments(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
