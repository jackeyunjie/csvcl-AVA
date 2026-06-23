from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


BB_PERIOD = 20
BB_STDDEV = 2.0
BB_PERCENTILE_WINDOW = 20
ATR_PERIOD = 14
ADX_PERIOD = 14
ADX_SLOPE_WINDOW = 3
FRACTAL_K = 5
FRACTAL_CONFIRM_LAG = 3

DEFAULT_SYMBOLS: Tuple[str, ...] = (
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

H1_VIEW_STRUCTURE_ORDER: Tuple[str, ...] = ("MN1", "W1", "D1", "H4", "H1")
D1_VIEW_STRUCTURE_ORDER: Tuple[str, ...] = ("MN1", "W1", "D1")

TIMEFRAME_BAR_LIMITS: Dict[str, int] = {
    "MN1": 240,
    "W1": 800,
    "D1": 5000,
    "H4": 30000,
    "H1": 120000,
}


@dataclass(frozen=True)
class FeatureSeries:
    timeframe: str
    time_s: np.ndarray
    timestamp: pd.Series
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    base_bit: np.ndarray
    trend_bit: np.ndarray
    vol_bit: np.ndarray
    support: np.ndarray
    resistance: np.ndarray
    prev_support: np.ndarray
    prev_resistance: np.ndarray


def score_to_hex(score: int) -> str:
    if score < 0:
        return f"-{abs(int(score)):X}"
    return f"{int(score):X}"


def ensure_rates_frame(rates: pd.DataFrame | np.ndarray) -> pd.DataFrame:
    if rates is None:
        return pd.DataFrame(columns=["time_s", "timestamp", "open", "high", "low", "close", "volume"])

    frame = pd.DataFrame(rates).copy()
    if frame.empty:
        return pd.DataFrame(columns=["time_s", "timestamp", "open", "high", "low", "close", "volume"])

    if "tick_volume" in frame.columns and "volume" not in frame.columns:
        frame = frame.rename(columns={"tick_volume": "volume"})
    if "real_volume" in frame.columns and "volume" not in frame.columns:
        frame = frame.rename(columns={"real_volume": "volume"})

    frame = frame.rename(columns={"time": "time_s"})
    frame["time_s"] = frame["time_s"].astype("int64")
    frame["timestamp"] = pd.to_datetime(frame["time_s"], unit="s")
    if "volume" not in frame.columns:
        frame["volume"] = 0.0

    required = ["time_s", "timestamp", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    frame = frame[required].drop_duplicates(subset=["time_s"]).sort_values("time_s").reset_index(drop=True)
    return frame


def fetch_rates_batched(
    mt5_module,
    symbol: str,
    timeframe_code: int,
    total_bars: int,
    batch_size: int = 5000,
) -> pd.DataFrame:
    chunks: List[pd.DataFrame] = []
    offset = 0

    while offset < total_bars:
        count = min(batch_size, total_bars - offset)
        rates = mt5_module.copy_rates_from_pos(symbol, timeframe_code, offset, count)
        if rates is None or len(rates) == 0:
            break
        chunks.append(pd.DataFrame(rates))
        offset += len(rates)
        if len(rates) < count:
            break

    if not chunks:
        return ensure_rates_frame(pd.DataFrame())

    frame = pd.concat(chunks, ignore_index=True)
    return ensure_rates_frame(frame)


def latest_index(times_s: np.ndarray, view_time_s: int) -> int:
    idx = int(np.searchsorted(times_s, view_time_s, side="right") - 1)
    return idx


def calc_position_bit(view_close: float, support: float, resistance: float) -> int:
    if np.isnan(support) or np.isnan(resistance):
        return 0
    if view_close > resistance:
        return 2
    if view_close < support:
        return 2
    return 0


def calc_sign_from_mn1(view_close: float, mn1: FeatureSeries, mn1_idx: int) -> int:
    if mn1_idx < 0:
        return 1

    res = mn1.resistance[mn1_idx]
    sup = mn1.support[mn1_idx]

    if not np.isnan(res) and view_close > res:
        return 1
    if not np.isnan(sup) and view_close < sup:
        return -1
    if mn1_idx >= 20:
        return 1 if mn1.close[mn1_idx] > mn1.close[mn1_idx - 20] else -1
    return 1


def compute_feature_series(df: pd.DataFrame, timeframe: str) -> FeatureSeries:
    frame = ensure_rates_frame(df)
    if frame.empty:
        raise ValueError(f"{timeframe} frame is empty")

    time_s = frame["time_s"].to_numpy(dtype=np.int64)
    timestamp = frame["timestamp"].reset_index(drop=True)
    open_arr = frame["open"].to_numpy(dtype=float)
    high_arr = frame["high"].to_numpy(dtype=float)
    low_arr = frame["low"].to_numpy(dtype=float)
    close_arr = frame["close"].to_numpy(dtype=float)
    volume_arr = frame["volume"].to_numpy(dtype=float)

    n = len(frame)
    base_bit = np.full(n, 8, dtype=np.int16)
    trend_bit = np.zeros(n, dtype=np.int16)
    vol_bit = np.zeros(n, dtype=np.int16)
    support = np.full(n, np.nan, dtype=float)
    resistance = np.full(n, np.nan, dtype=float)
    prev_support = np.full(n, np.nan, dtype=float)
    prev_resistance = np.full(n, np.nan, dtype=float)

    bb_history: List[float] = []
    tr_buffer: deque[float] = deque(maxlen=ADX_PERIOD)
    pdm_buffer: deque[float] = deque(maxlen=ADX_PERIOD)
    mdm_buffer: deque[float] = deque(maxlen=ADX_PERIOD)
    dx_history: List[float] = []
    adx_history: List[float] = []
    atr_pct_history: List[float] = []
    res_levels: List[float] = []
    sup_levels: List[float] = []
    half = FRACTAL_K // 2

    for i in range(n):
        if i >= BB_PERIOD - 1:
            window = close_arr[i - BB_PERIOD + 1 : i + 1]
            mid = float(window.mean())
            if mid > 0:
                std = float(window.std(ddof=1))
                current_bbw = (2.0 * BB_STDDEV * std) / mid
                if len(bb_history) >= BB_PERCENTILE_WINDOW:
                    q20 = float(np.percentile(bb_history[-BB_PERCENTILE_WINDOW:], 20))
                    base_bit[i] = 0 if current_bbw < q20 else 8
                bb_history.append(current_bbw)

        if i >= 1:
            tr = max(
                high_arr[i] - low_arr[i],
                abs(high_arr[i] - close_arr[i - 1]),
                abs(low_arr[i] - close_arr[i - 1]),
            )
            up_move = high_arr[i] - high_arr[i - 1]
            down_move = low_arr[i - 1] - low_arr[i]
            pdm = up_move if (up_move > down_move and up_move > 0) else 0.0
            mdm = down_move if (down_move > up_move and down_move > 0) else 0.0

            tr_buffer.append(float(tr))
            pdm_buffer.append(float(pdm))
            mdm_buffer.append(float(mdm))

            if len(tr_buffer) == ADX_PERIOD:
                atr = float(np.mean(tr_buffer))
                if atr > 0:
                    pdi = float(np.mean(pdm_buffer) / atr * 100.0)
                    mdi = float(np.mean(mdm_buffer) / atr * 100.0)
                    denom = pdi + mdi
                    dx = abs(pdi - mdi) / denom * 100.0 if denom > 0 else 0.0
                else:
                    dx = 0.0
                dx_history.append(dx)
                if len(dx_history) >= ADX_PERIOD:
                    adx_current = float(np.mean(dx_history[-ADX_PERIOD:]))
                    adx_history.append(adx_current)
                    if len(adx_history) >= ADX_SLOPE_WINDOW + 1:
                        cur = adx_history[-1]
                        prev = adx_history[-1 - ADX_SLOPE_WINDOW]
                        slope = cur - prev
                        if cur >= 25 and slope > 0:
                            trend_bit[i] = 1
                        elif cur > 20:
                            trend_bit[i] = 1
                        elif cur <= 13 and slope < 0:
                            trend_bit[i] = 0

                current_atr_pct = float(atr / close_arr[i] * 100.0) if close_arr[i] else 0.0
                if atr_pct_history:
                    atr_rank = sum(1 for x in atr_pct_history if x < current_atr_pct) / len(atr_pct_history)
                    if atr_rank > 0.6:
                        vol_bit[i] = 1
                atr_pct_history.append(current_atr_pct)

        if i >= half * 2 + FRACTAL_CONFIRM_LAG:
            check_idx = i - half - FRACTAL_CONFIRM_LAG
            if check_idx >= half and check_idx + half < n:
                is_res = True
                is_sup = True
                for j in range(1, half + 1):
                    if high_arr[check_idx] <= high_arr[check_idx - j] or high_arr[check_idx] <= high_arr[check_idx + j]:
                        is_res = False
                    if low_arr[check_idx] >= low_arr[check_idx - j] or low_arr[check_idx] >= low_arr[check_idx + j]:
                        is_sup = False
                if is_res:
                    res_levels.append(float(high_arr[check_idx]))
                if is_sup:
                    sup_levels.append(float(low_arr[check_idx]))

        if res_levels:
            resistance[i] = res_levels[-1]
            if len(res_levels) > 1:
                prev_resistance[i] = res_levels[-2]
        if sup_levels:
            support[i] = sup_levels[-1]
            if len(sup_levels) > 1:
                prev_support[i] = sup_levels[-2]

    return FeatureSeries(
        timeframe=timeframe,
        time_s=time_s,
        timestamp=timestamp,
        open=open_arr,
        high=high_arr,
        low=low_arr,
        close=close_arr,
        volume=volume_arr,
        base_bit=base_bit,
        trend_bit=trend_bit,
        vol_bit=vol_bit,
        support=support,
        resistance=resistance,
        prev_support=prev_support,
        prev_resistance=prev_resistance,
    )


def build_view_snapshot_frame(
    symbol: str,
    structure_series: Mapping[str, FeatureSeries],
    view_series: FeatureSeries,
    structure_order: Sequence[str],
    close_field_name: str = "view_close",
) -> pd.DataFrame:
    if "MN1" not in structure_series:
        raise ValueError("MN1 structure series is required for sign resolution")

    mn1_series = structure_series["MN1"]
    rows: List[Dict[str, object]] = []
    view_times = view_series.time_s
    view_closes = view_series.close

    for i, view_time_s in enumerate(view_times):
        view_close = float(view_closes[i])
        mn1_idx = latest_index(mn1_series.time_s, int(view_time_s))
        sign = calc_sign_from_mn1(view_close, mn1_series, mn1_idx)

        row: Dict[str, object] = {
            "symbol": symbol,
            "timestamp": datetime.fromtimestamp(int(view_time_s)),
            "view_tf": view_series.timeframe,
            close_field_name: view_close,
        }

        ef_count = 0
        for tf in structure_order:
            series = structure_series[tf]
            idx = latest_index(series.time_s, int(view_time_s))
            hex_col = f"{tf.lower()}_hex"
            score_col = f"{tf.lower()}_score"

            if idx < 0:
                score = 8
                hex_code = "8"
            else:
                base = int(series.base_bit[idx])
                trend = int(series.trend_bit[idx])
                position = calc_position_bit(view_close, float(series.support[idx]), float(series.resistance[idx]))
                vol = int(series.vol_bit[idx])
                magnitude = base + trend * 4 + position + vol
                score = int(sign * magnitude)
                hex_code = score_to_hex(score)

            row[hex_col] = hex_code
            row[score_col] = score
            if score in (14, 15):
                ef_count += 1

        row["ef_count"] = ef_count
        rows.append(row)

    return pd.DataFrame(rows)


def build_forward_frame(snapshot_frame: pd.DataFrame) -> pd.DataFrame:
    if snapshot_frame.empty:
        return pd.DataFrame(
            columns=["symbol", "timestamp", "view_tf", "h1_close", "fwd_4h", "fwd_24h", "fwd_120h"]
        )

    frame = snapshot_frame[["symbol", "timestamp", "view_tf", "h1_close"]].copy()
    frame = frame.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    grouped = frame.groupby("symbol", sort=False)["h1_close"]
    frame["fwd_4h"] = grouped.shift(-4) / frame["h1_close"] - 1.0
    frame["fwd_24h"] = grouped.shift(-24) / frame["h1_close"] - 1.0
    frame["fwd_120h"] = grouped.shift(-120) / frame["h1_close"] - 1.0
    return frame


def build_slice_frame(snapshot_frame: pd.DataFrame, forward_frame: pd.DataFrame) -> pd.DataFrame:
    if snapshot_frame.empty:
        return pd.DataFrame(
            columns=[
                "symbol",
                "view_tf",
                "pattern",
                "mn1_hex",
                "w1_hex",
                "d1_hex",
                "h4_hex",
                "h1_hex",
                "occurrence_count",
                "avg_ef_count",
                "avg_fwd_4h",
                "avg_fwd_24h",
                "avg_fwd_120h",
            ]
        )

    merged = snapshot_frame.merge(
        forward_frame[["symbol", "timestamp", "fwd_4h", "fwd_24h", "fwd_120h"]],
        on=["symbol", "timestamp"],
        how="left",
    )
    merged["pattern"] = (
        merged["mn1_hex"].astype(str)
        + "_"
        + merged["w1_hex"].astype(str)
        + "_"
        + merged["d1_hex"].astype(str)
        + "_"
        + merged["h4_hex"].astype(str)
        + "_"
        + merged["h1_hex"].astype(str)
    )

    grouped = (
        merged.groupby(
            [
                "symbol",
                "view_tf",
                "pattern",
                "mn1_hex",
                "w1_hex",
                "d1_hex",
                "h4_hex",
                "h1_hex",
            ],
            as_index=False,
        )
        .agg(
            occurrence_count=("timestamp", "count"),
            avg_ef_count=("ef_count", "mean"),
            avg_fwd_4h=("fwd_4h", "mean"),
            avg_fwd_24h=("fwd_24h", "mean"),
            avg_fwd_120h=("fwd_120h", "mean"),
        )
        .sort_values(["symbol", "occurrence_count", "pattern"], ascending=[True, False, True])
        .reset_index(drop=True)
    )
    return grouped
