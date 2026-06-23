from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Sequence

import duckdb
import numpy as np
import pandas as pd


DEFAULT_SYMBOLS: tuple[str, ...] = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "EURJPY",
    "GBPJPY",
    "AUDJPY",
    "EURGBP",
    "EURCHF",
    "EURCAD",
    "GBPCHF",
)


def parse_hex_score(hex_value: str | None) -> dict[str, int]:
    raw = "" if hex_value is None else str(hex_value).strip().upper()
    if not raw:
        score = 0
    elif raw.startswith("-"):
        score = -int(raw[1:], 16)
    else:
        score = int(raw, 16)

    magnitude = abs(score)
    return {
        "score": score,
        "sign": 1 if score >= 0 else -1,
        "base_expand": 1 if (magnitude & 8) else 0,
        "trend": 1 if (magnitude & 4) else 0,
        "position": 1 if (magnitude & 2) else 0,
        "vol": 1 if (magnitude & 1) else 0,
    }


def add_state_decode_columns(frame: pd.DataFrame, tf: str) -> None:
    col = f"{tf.lower()}_hex"
    decoded = {value: parse_hex_score(value) for value in frame[col].astype(str).unique()}
    for field in ("score", "sign", "base_expand", "trend", "position", "vol"):
        frame[f"{tf.lower()}_{field}"] = frame[col].map(lambda value: decoded[str(value)][field]).astype(np.int16)


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)

    avg_gain = gains.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = losses.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def ensure_forward_columns(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.sort_values(["symbol", "timestamp"]).copy()
    grouped = ordered.groupby("symbol", sort=False)["h1_close"]

    if "fwd_4h" not in ordered.columns:
        ordered["fwd_4h"] = grouped.shift(-4) / ordered["h1_close"] - 1.0
    if "fwd_24h" not in ordered.columns:
        ordered["fwd_24h"] = grouped.shift(-24) / ordered["h1_close"] - 1.0
    if "fwd_120h" not in ordered.columns:
        ordered["fwd_120h"] = grouped.shift(-120) / ordered["h1_close"] - 1.0

    return ordered


def load_dataset(db_path: Path, symbols: Sequence[str]) -> pd.DataFrame:
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        if "h1_state_snapshots" not in tables:
            raise RuntimeError(
                f"{db_path} does not contain h1_state_snapshots. "
                "Run python build_h1_state_db.py --db data/hermass_h1_state.db first."
            )

        has_fwd = "h1_fwd" in tables
        symbol_filter = ", ".join(f"'{symbol}'" for symbol in symbols)

        if has_fwd:
            query = f"""
                SELECT
                    s.symbol,
                    s.timestamp,
                    s.mn1_hex,
                    s.w1_hex,
                    s.d1_hex,
                    s.h4_hex,
                    s.h1_hex,
                    s.h1_close,
                    f.fwd_4h,
                    f.fwd_24h,
                    f.fwd_120h
                FROM h1_state_snapshots s
                LEFT JOIN h1_fwd f
                    ON s.symbol = f.symbol
                   AND s.timestamp = f.timestamp
                WHERE s.symbol IN ({symbol_filter})
                ORDER BY s.symbol, s.timestamp
            """
        else:
            query = f"""
                SELECT
                    symbol,
                    timestamp,
                    mn1_hex,
                    w1_hex,
                    d1_hex,
                    h4_hex,
                    h1_hex,
                    h1_close
                FROM h1_state_snapshots
                WHERE symbol IN ({symbol_filter})
                ORDER BY symbol, timestamp
            """

        frame = conn.execute(query).fetchdf()
    finally:
        conn.close()

    if frame.empty:
        raise RuntimeError("No snapshot rows found for the requested symbols.")

    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame = ensure_forward_columns(frame)
    frame["bar_index"] = frame.groupby("symbol", sort=False).cumcount()
    frame["month_key"] = frame["timestamp"].dt.to_period("M").astype(str)
    frame["week_key"] = frame["timestamp"].dt.to_period("W").astype(str)
    frame["rsi14"] = frame.groupby("symbol", sort=False)["h1_close"].transform(compute_rsi)

    for tf in ("mn1", "w1", "d1", "h4", "h1"):
        add_state_decode_columns(frame, tf.upper())

    frame["regime_id"] = "MN1:" + frame["mn1_hex"].astype(str) + "|W1:" + frame["w1_hex"].astype(str)
    frame["regime_sign_aligned"] = frame["mn1_sign"] == frame["w1_sign"]
    frame["mn1_score"] = frame["mn1_sign"] * (frame["mn1_base_expand"] * 8 + frame["mn1_trend"] * 4 + frame["mn1_position"] * 2 + frame["mn1_vol"])
    frame["w1_score"] = frame["w1_sign"] * (frame["w1_base_expand"] * 8 + frame["w1_trend"] * 4 + frame["w1_position"] * 2 + frame["w1_vol"])
    return frame


@dataclass(frozen=True)
class StrategyTemplate:
    name: str
    description: str
    direction: str
    mask_builder: Callable[[pd.DataFrame, int], pd.Series]
    sqx_entry: str


@dataclass
class CandidateResult:
    regime_id: str
    template: str
    description: str
    direction: str
    horizon_bars: int
    rsi_threshold: int
    total_trades: int
    unique_symbols: int
    sample_months: int
    avg_return: float
    median_return: float
    win_rate: float
    sharpe_like: float
    positive_folds: int
    quality_score: float
    sqx_recipe: str


def build_templates() -> list[StrategyTemplate]:
    return [
        StrategyTemplate(
            name="monthly_breakout_rsi",
            description="Monthly breakout confirmed by weekly alignment and H1 RSI.",
            direction="long",
            mask_builder=lambda df, rsi: (
                (df["mn1_sign"] > 0)
                & (df["w1_sign"] > 0)
                & (df["mn1_position"] == 1)
                & (df["rsi14"] >= rsi)
            ),
            sqx_entry="SqSrMTF(43200) upside breakout AND RSI(14) > threshold",
        ),
        StrategyTemplate(
            name="weekly_breakout_rsi",
            description="Weekly breakout inside a bullish monthly regime with RSI support.",
            direction="long",
            mask_builder=lambda df, rsi: (
                (df["mn1_sign"] > 0)
                & (df["w1_sign"] > 0)
                & (df["w1_position"] == 1)
                & (df["w1_trend"] == 1)
                & (df["rsi14"] >= rsi)
            ),
            sqx_entry="SqSrMTF(10080) upside breakout AND RSI(14) > threshold",
        ),
        StrategyTemplate(
            name="mn1_w1_h4_h1_alignment",
            description="Monthly and weekly regime aligned, then H4 and H1 trigger in the same direction.",
            direction="long",
            mask_builder=lambda df, rsi: (
                (df["mn1_sign"] > 0)
                & (df["w1_sign"] > 0)
                & ((df["h4_trend"] == 1) | (df["h4_position"] == 1))
                & ((df["h1_trend"] == 1) | (df["h1_position"] == 1))
                & (df["rsi14"] >= rsi)
            ),
            sqx_entry="H4/H1 alignment AND RSI(14) > threshold",
        ),
        StrategyTemplate(
            name="monthly_breakout_rsi",
            description="Monthly downside breakout confirmed by weekly alignment and H1 RSI.",
            direction="short",
            mask_builder=lambda df, rsi: (
                (df["mn1_sign"] < 0)
                & (df["w1_sign"] < 0)
                & (df["mn1_position"] == 1)
                & (df["rsi14"] <= (100 - rsi))
            ),
            sqx_entry="SqSrMTF(43200) downside breakout AND RSI(14) < threshold",
        ),
        StrategyTemplate(
            name="weekly_breakout_rsi",
            description="Weekly downside breakout inside a bearish monthly regime with RSI support.",
            direction="short",
            mask_builder=lambda df, rsi: (
                (df["mn1_sign"] < 0)
                & (df["w1_sign"] < 0)
                & (df["w1_position"] == 1)
                & (df["w1_trend"] == 1)
                & (df["rsi14"] <= (100 - rsi))
            ),
            sqx_entry="SqSrMTF(10080) downside breakout AND RSI(14) < threshold",
        ),
        StrategyTemplate(
            name="mn1_w1_h4_h1_alignment",
            description="Monthly and weekly regime aligned, then H4 and H1 trigger in the same bearish direction.",
            direction="short",
            mask_builder=lambda df, rsi: (
                (df["mn1_sign"] < 0)
                & (df["w1_sign"] < 0)
                & ((df["h4_trend"] == 1) | (df["h4_position"] == 1))
                & ((df["h1_trend"] == 1) | (df["h1_position"] == 1))
                & (df["rsi14"] <= (100 - rsi))
            ),
            sqx_entry="H4/H1 bearish alignment AND RSI(14) < threshold",
        ),
    ]


def summarize_regimes(frame: pd.DataFrame, min_rows: int, direction: str | None = None) -> pd.DataFrame:
    summary = (
        frame.groupby(["regime_id", "mn1_hex", "w1_hex"], as_index=False)
        .agg(
            rows=("symbol", "size"),
            symbols=("symbol", "nunique"),
            months=("month_key", "nunique"),
            avg_fwd_4h=("fwd_4h", "mean"),
            avg_fwd_24h=("fwd_24h", "mean"),
            avg_fwd_120h=("fwd_120h", "mean"),
            aligned=("regime_sign_aligned", "max"),
            mn1_score=("mn1_score", "first"),
            w1_score=("w1_score", "first"),
        )
    )

    if direction == "short":
        # Bearish regime: MN1 and W1 both negative
        summary = summary[
            (summary["rows"] >= min_rows)
            & (summary["mn1_score"] < 0)
            & (summary["w1_score"] < 0)
        ]
    elif direction == "long":
        summary = summary[
            (summary["rows"] >= min_rows)
            & (summary["mn1_score"] > 0)
            & (summary["w1_score"] > 0)
        ]
    else:
        summary = summary[(summary["rows"] >= min_rows) & (summary["aligned"])]

    return summary.sort_values(["rows", "symbols", "months"], ascending=[False, False, False]).reset_index(drop=True)


def select_non_overlapping(signals: pd.DataFrame, horizon_bars: int) -> pd.DataFrame:
    kept_rows: list[int] = []
    for _, group in signals.groupby("symbol", sort=False):
        next_allowed = -1
        for index, row in group.iterrows():
            bar_index = int(row["bar_index"])
            if bar_index >= next_allowed:
                kept_rows.append(index)
                next_allowed = bar_index + horizon_bars
    return signals.loc[kept_rows].sort_values(["symbol", "timestamp"]).reset_index(drop=True)


def compute_positive_folds(returns: pd.Series, timestamps: pd.Series, min_fold_trades: int = 5) -> int:
    if len(returns) < min_fold_trades * 2:
        return 0

    ordered = pd.DataFrame({"ret": returns.to_numpy(), "ts": timestamps.to_numpy()}).sort_values("ts")
    ordered["fold"] = pd.qcut(np.arange(len(ordered)), q=min(4, len(ordered)), labels=False, duplicates="drop")
    fold_means = ordered.groupby("fold")["ret"].mean()
    fold_counts = ordered.groupby("fold")["ret"].size()
    return int(((fold_counts >= min_fold_trades) & (fold_means > 0)).sum())


def quality_score(
    returns: pd.Series,
    unique_symbols: int,
    sample_months: int,
    positive_folds: int,
    min_trades: int,
) -> float:
    trade_count = len(returns)
    if trade_count < min_trades:
        return 0.0

    avg_return = float(returns.mean())
    win_rate = float((returns > 0).mean())
    std = float(returns.std(ddof=1)) if trade_count > 1 else 0.0
    sharpe_like = (avg_return / std) * np.sqrt(trade_count) if std > 0 else 0.0

    score = 0.0
    score += min(35.0, max(0.0, sharpe_like * 4.0))
    score += min(20.0, max(0.0, (win_rate - 0.50) * 100.0))
    score += min(20.0, max(0.0, avg_return * 10000.0 / 4.0))
    score += min(15.0, unique_symbols * 1.5)
    score += min(10.0, sample_months / 2.0)
    score += min(10.0, positive_folds * 2.5)
    return round(min(100.0, score), 2)


def build_sqx_recipe(candidate: CandidateResult) -> str:
    regime = candidate.regime_id
    if candidate.direction == "long":
        direction_filter = "bullish"
        exit_direction = "sell"
        rsi_clause = f"RSI(14) > {candidate.rsi_threshold}"
    else:
        direction_filter = "bearish"
        exit_direction = "buy-to-cover"
        rsi_clause = f"RSI(14) < {100 - candidate.rsi_threshold}"

    return (
        f"Chart=H1 | Regime={regime} ({direction_filter}) | "
        f"Entry={candidate.template} -> {rsi_clause} | "
        f"Hold={candidate.horizon_bars} H1 bars | Exit={exit_direction} on bar timeout"
    )


def evaluate_candidates(
    frame: pd.DataFrame,
    regime_summary: pd.DataFrame,
    templates: Iterable[StrategyTemplate],
    rsi_thresholds: Sequence[int],
    horizons: Sequence[int],
    min_trades: int,
    top_regimes: int,
    direction_filter: str | None = None,
) -> list[CandidateResult]:
    results: list[CandidateResult] = []
    horizon_columns = {4: "fwd_4h", 24: "fwd_24h", 120: "fwd_120h"}

    for _, regime_row in regime_summary.head(top_regimes).iterrows():
        regime_id = regime_row["regime_id"]
        regime_slice = frame[frame["regime_id"] == regime_id].copy()
        if regime_slice.empty:
            continue

        for template in templates:
            if direction_filter and template.direction != direction_filter:
                continue
            for rsi_threshold in rsi_thresholds:
                template_mask = template.mask_builder(regime_slice, rsi_threshold)
                if not template_mask.any():
                    continue

                raw_signals = regime_slice.loc[template_mask].sort_values(["symbol", "timestamp"])

                for horizon in horizons:
                    horizon_col = horizon_columns[horizon]
                    signals = select_non_overlapping(raw_signals, horizon)
                    signals = signals.dropna(subset=[horizon_col])
                    if signals.empty:
                        continue

                    direction_multiplier = 1.0 if template.direction == "long" else -1.0
                    returns = signals[horizon_col] * direction_multiplier
                    trade_count = len(returns)
                    if trade_count < min_trades:
                        continue

                    unique_symbols = int(signals["symbol"].nunique())
                    sample_months = int(signals["month_key"].nunique())
                    avg_return = float(returns.mean())
                    median_return = float(returns.median())
                    win_rate = float((returns > 0).mean())
                    std = float(returns.std(ddof=1)) if trade_count > 1 else 0.0
                    sharpe_like = (avg_return / std) * np.sqrt(trade_count) if std > 0 else 0.0
                    positive_folds = compute_positive_folds(returns, signals["timestamp"])
                    score = quality_score(returns, unique_symbols, sample_months, positive_folds, min_trades)

                    candidate = CandidateResult(
                        regime_id=regime_id,
                        template=template.name,
                        description=template.description,
                        direction=template.direction,
                        horizon_bars=horizon,
                        rsi_threshold=rsi_threshold,
                        total_trades=trade_count,
                        unique_symbols=unique_symbols,
                        sample_months=sample_months,
                        avg_return=round(avg_return, 6),
                        median_return=round(median_return, 6),
                        win_rate=round(win_rate, 4),
                        sharpe_like=round(sharpe_like, 4),
                        positive_folds=positive_folds,
                        quality_score=score,
                        sqx_recipe="",
                    )
                    candidate.sqx_recipe = build_sqx_recipe(candidate)
                    results.append(candidate)

    results.sort(
        key=lambda row: (
            row.quality_score,
            row.avg_return,
            row.win_rate,
            row.total_trades,
        ),
        reverse=True,
    )
    return results


def write_outputs(
    out_prefix: Path,
    regime_summary: pd.DataFrame,
    candidates: Sequence[CandidateResult],
    top_n: int,
) -> dict[str, str]:
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    regime_path = out_prefix.with_name(out_prefix.name + "_regimes.csv")
    candidates_path = out_prefix.with_name(out_prefix.name + "_candidates.csv")
    report_path = out_prefix.with_name(out_prefix.name + "_report.md")
    playbook_path = out_prefix.with_name(out_prefix.name + "_sqx_playbook.json")

    regime_summary.to_csv(regime_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(asdict(candidate) for candidate in candidates).to_csv(
        candidates_path,
        index=False,
        encoding="utf-8-sig",
    )

    top_candidates = list(candidates[:top_n])
    playbook = [asdict(candidate) for candidate in top_candidates]
    with open(playbook_path, "w", encoding="utf-8") as handle:
        json.dump(playbook, handle, ensure_ascii=False, indent=2)

    lines = [
        "# H1 Regime Strategy Report",
        "",
        "## Monthly/Weekly Regimes",
        "",
        "| Regime | Rows | Symbols | Months | Avg4h | Avg24h | Avg120h |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in regime_summary.head(top_n).iterrows():
        lines.append(
            f"| {row['regime_id']} | {int(row['rows'])} | {int(row['symbols'])} | {int(row['months'])} | "
            f"{row['avg_fwd_4h']:.5f} | {row['avg_fwd_24h']:.5f} | {row['avg_fwd_120h']:.5f} |"
        )

    lines.extend(
        [
            "",
            "## Top H1 Triggers",
            "",
            "| Rank | Regime | Template | Dir | Hold | RSI | Trades | WinRate | AvgRet | Score | SQX Rule |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )

    for index, candidate in enumerate(top_candidates, start=1):
        lines.append(
            f"| {index} | {candidate.regime_id} | {candidate.template} | {candidate.direction} | "
            f"{candidate.horizon_bars} | {candidate.rsi_threshold} | {candidate.total_trades} | "
            f"{candidate.win_rate:.2%} | {candidate.avg_return:.5f} | {candidate.quality_score:.2f} | "
            f"{candidate.sqx_recipe} |"
        )

    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return {
        "regimes": str(regime_path),
        "candidates": str(candidates_path),
        "report": str(report_path),
        "playbook": str(playbook_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mine H1-view regime strategies for SQX")
    parser.add_argument("--db", default="data/hermass_h1_state.db", help="H1 viewpoint DuckDB path")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS), help="symbols to include")
    parser.add_argument("--top-regimes", type=int, default=20, help="number of monthly/weekly regimes to inspect")
    parser.add_argument("--top-candidates", type=int, default=30, help="number of top candidates to write to the report")
    parser.add_argument("--min-regime-rows", type=int, default=150, help="minimum rows for a regime slice")
    parser.add_argument("--min-trades", type=int, default=25, help="minimum non-overlapping trades per candidate")
    parser.add_argument("--rsi-thresholds", nargs="+", type=int, default=[50, 55, 60], help="RSI thresholds to test")
    parser.add_argument("--horizons", nargs="+", type=int, default=[4, 24, 120], help="forward horizons in H1 bars")
    parser.add_argument("--out-prefix", default="data/h1_regime_strategy", help="output file prefix")
    parser.add_argument("--direction", choices=["long", "short", None], default=None, help="filter templates by direction")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    dataset = load_dataset(db_path, args.symbols)

    direction = args.direction
    regime_summary = summarize_regimes(dataset, min_rows=args.min_regime_rows, direction=direction)
    templates = build_templates()
    candidates = evaluate_candidates(
        frame=dataset,
        regime_summary=regime_summary,
        templates=templates,
        rsi_thresholds=args.rsi_thresholds,
        horizons=args.horizons,
        min_trades=args.min_trades,
        top_regimes=args.top_regimes,
        direction_filter=direction,
    )

    outputs = write_outputs(
        out_prefix=Path(args.out_prefix),
        regime_summary=regime_summary,
        candidates=candidates,
        top_n=args.top_candidates,
    )

    print(f"rows={len(dataset)} regimes={len(regime_summary)} candidates={len(candidates)}")
    for key, value in outputs.items():
        print(f"{key}={value}")

    for index, candidate in enumerate(candidates[:10], start=1):
        print(
            f"{index:02d}. {candidate.regime_id} | {candidate.template} | {candidate.direction} | "
            f"hold={candidate.horizon_bars} | rsi={candidate.rsi_threshold} | "
            f"trades={candidate.total_trades} | win={candidate.win_rate:.2%} | "
            f"avg={candidate.avg_return:.5f} | score={candidate.quality_score:.2f}"
        )


if __name__ == "__main__":
    main()
