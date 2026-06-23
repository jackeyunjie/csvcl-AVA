"""
build_state_hermass_duckdb.py
=============================
State historical backfill - Hermass Schema + DuckDB + D1 data window scaling
Optimized: incremental computation, O(n) per symbol instead of O(n^2)

Principle:
- No dependency on multi-timeframe K-lines, all computed from D1 data
- Avoids MN1/W1 data shortage issues
- Schema fully aligned with Hermass for unified querying

D1 perspective:
  MN1 State: D1_BB(20*22~440), D1_ADX(14*22), D1_SR(k=5*22), position via D1 close
  W1 State:  D1_BB(20*5~100), D1_ADX(14*5), D1_SR(k=5*5), position via D1 close
  D1 State:  D1_BB(20), D1_ADX(14), D1_SR(k=5), position via D1 close

Schema (Hermass):
  symbol VARCHAR, perspective VARCHAR, date DATE,
  mn1_hex VARCHAR, w1_hex VARCHAR, d1_hex VARCHAR,
  mn1_score INTEGER, w1_score INTEGER, d1_score INTEGER,
  ef_count INTEGER, raw_json VARCHAR, source VARCHAR
"""

import MetaTrader5 as mt5
import duckdb
import numpy as np
import json
import sys
import io
from datetime import datetime
from pathlib import Path
from collections import deque

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ========== Config ==========
FOCUS_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF",
    "EURJPY", "GBPJPY", "AUDJPY", "EURGBP", "EURCHF", "EURCAD", "GBPCHF",
    "BTCUSD", "ETHUSD", "XRPUSD",
    "US_30", "GERMANY_40", "UK_100", "AUS_200", "FRANCE_40",
    "GOLD", "SILVER", "CrudeOIL",
]

BB_PERIOD = 20
BB_STDDEV = 2.0
BB_PERCENTILE_WINDOW = 20
BB_COMPRESSION_Q = 0.20
ATR_PERIOD = 14
ADX_PERIOD = 14
ADX_SLOPE = 3
FRACTAL_K = 5
FRACTAL_LAG = 3

SCALE = {"MN1": 22, "W1": 5, "D1": 1}

DB_PATH = Path(__file__).parent / "data" / "state_hermass.duckdb"


def _score_to_hex(score: int) -> str:
    s = abs(score)
    h = f"{s:X}"
    return f"-{h}" if score < 0 else h


class IncrementalStateCalculator:
    """Incremental state calculator - computes state for each new bar without reprocessing history"""

    def __init__(self, highs, lows, closes, scale=1):
        self.highs = highs
        self.lows = lows
        self.closes = closes
        self.scale = scale
        self.n = 0

        # Parameters scaled
        self.bb_per = BB_PERIOD * scale
        self.bb_pw = BB_PERCENTILE_WINDOW
        self.adx_per = ADX_PERIOD * scale
        self.adx_slope_w = ADX_SLOPE * scale
        self.fractal_k = FRACTAL_K * scale
        self.fractal_lag = FRACTAL_LAG * scale
        self.atr_per = ATR_PERIOD * scale

        # Buffers for incremental ADX
        self.tr_buffer = deque(maxlen=self.adx_per)
        self.pdm_buffer = deque(maxlen=self.adx_per)
        self.mdm_buffer = deque(maxlen=self.adx_per)
        self.adx_history = []

        # BB width history
        self.bbw_history = deque(maxlen=self.bb_pw + 1)

        # Fractal levels
        self.res_levels = []
        self.sup_levels = []
        self.fractal_half = self.fractal_k // 2

        # ATR buffer
        self.atr_buffer = deque(maxlen=self.atr_per + 2)

    def _calc_bb_width(self, i):
        """Calculate Bollinger Band width at index i"""
        start = i - self.bb_per + 1
        if start < 0:
            return None
        seg = self.closes[start:i + 1]
        mid = np.mean(seg)
        std = np.std(seg, ddof=0)
        up = mid + BB_STDDEV * std
        lo = mid - BB_STDDEV * std
        return (up - lo) / mid if mid > 0 else 0

    def _update_adx(self, i):
        """Update ADX calculation incrementally"""
        if i < 1:
            return None

        tr = max(
            self.highs[i] - self.lows[i],
            abs(self.highs[i] - self.closes[i - 1]),
            abs(self.lows[i] - self.closes[i - 1]),
        )
        pdm = (
            self.highs[i] - self.highs[i - 1]
            if self.highs[i] > self.highs[i - 1]
            and self.highs[i] - self.highs[i - 1] > self.lows[i - 1] - self.lows[i]
            else 0
        )
        mdm = (
            self.lows[i - 1] - self.lows[i]
            if self.lows[i - 1] > self.lows[i]
            and self.lows[i - 1] - self.lows[i] > self.highs[i] - self.highs[i - 1]
            else 0
        )

        self.tr_buffer.append(tr)
        self.pdm_buffer.append(pdm)
        self.mdm_buffer.append(mdm)

        if len(self.tr_buffer) < self.adx_per:
            return None

        atr = sum(self.tr_buffer) / self.adx_per
        pdi = sum(self.pdm_buffer) / self.adx_per / atr * 100 if atr > 0 else 0
        mdi = sum(self.mdm_buffer) / self.adx_per / atr * 100 if atr > 0 else 0
        dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0
        self.adx_history.append(dx)

        if len(self.adx_history) < self.adx_slope_w + 1:
            return None

        cur = self.adx_history[-1]
        prev = self.adx_history[-1 - self.adx_slope_w]
        slope = cur - prev

        if cur >= 25 and slope > 0:
            return 1
        if cur > 20:
            return 1
        if cur <= 13 and slope < 0:
            return 0
        return 0

    def _update_fractals(self, i):
        """Update fractal SR levels incrementally"""
        half = self.fractal_half
        if i < half * 2 + self.fractal_lag:
            return

        # Check if index (i - half - self.fractal_lag) forms a fractal
        check_idx = i - half - self.fractal_lag
        if check_idx < half:
            return

        is_r = True
        is_s = True
        for j in range(1, half + 1):
            if self.highs[check_idx] <= self.highs[check_idx - j] or self.highs[check_idx] <= self.highs[check_idx + j]:
                is_r = False
            if self.lows[check_idx] >= self.lows[check_idx - j] or self.lows[check_idx] >= self.lows[check_idx + j]:
                is_s = False

        if is_r:
            self.res_levels.append(self.highs[check_idx])
        if is_s:
            self.sup_levels.append(self.lows[check_idx])

    def _calc_position(self, price):
        """Check if price breaks latest SR levels"""
        sr_r = self.res_levels[-1] if self.res_levels else 0
        sr_s = self.sup_levels[-1] if self.sup_levels else 0
        if sr_r > 0 and price > sr_r:
            return 2
        if sr_s > 0 and price < sr_s:
            return 2
        return 0

    def _calc_volatility(self, i):
        """Calculate ATR-based volatility"""
        if i < 2:
            return 0
        tr1 = max(
            self.highs[i] - self.lows[i],
            abs(self.highs[i] - self.closes[i - 1]),
            abs(self.lows[i] - self.closes[i - 1]),
        )
        tr2 = max(
            self.highs[i - 1] - self.lows[i - 1],
            abs(self.highs[i - 1] - self.closes[i - 2]),
            abs(self.lows[i - 1] - self.closes[i - 2]),
        )
        return 1 if tr1 > tr2 else 0

    def _calc_base(self, i):
        """Calculate BB width base"""
        bbw = self._calc_bb_width(i)
        if bbw is None:
            return 0

        self.bbw_history.append(bbw)
        if len(self.bbw_history) < 2:
            return 0

        cur = self.bbw_history[-1]
        hist = list(self.bbw_history)[:-1]
        q20 = np.percentile(hist, BB_COMPRESSION_Q * 100)
        return 0 if cur < q20 else 8

    def compute_all(self):
        """Compute states for all bars incrementally"""
        states = []
        n = len(self.closes)

        for i in range(n):
            # Update incremental components
            trend = self._update_adx(i)
            self._update_fractals(i)

            # Need minimum data to compute state
            if i < max(self.bb_per + self.bb_pw, self.adx_per + self.adx_slope_w + 2,
                       self.fractal_k + self.fractal_lag, self.atr_per + 2):
                continue

            base = self._calc_base(i)
            if trend is None:
                trend = 0
            pos = self._calc_position(self.closes[i])
            vol = self._calc_volatility(i)

            magnitude = base + trend * 4 + pos + vol
            states.append((i, magnitude, base, trend, pos, vol))

        return states


def compute_states_for_symbol(highs, lows, closes, scale):
    """Compute all states for a symbol using incremental calculator"""
    calc = IncrementalStateCalculator(highs, lows, closes, scale)
    return calc.compute_all()


def determine_sign(price, highs, lows, closes):
    """Determine sign based on MN1-level SR"""
    mn1_scale = SCALE["MN1"]
    mn1_k = FRACTAL_K * mn1_scale
    mn1_lag = FRACTAL_LAG * mn1_scale
    mn1_half = mn1_k // 2
    n = len(highs)

    mn1_res = None
    mn1_sup = None

    if n > mn1_k + mn1_lag:
        for i in range(mn1_half, n - mn1_half - mn1_lag):
            is_r = True
            is_s = True
            for j in range(1, mn1_half + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                    is_r = False
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                    is_s = False
            if is_r:
                mn1_res = max(mn1_res or 0, highs[i])
            if is_s:
                mn1_sup = min(mn1_sup or float('inf'), lows[i])

    if mn1_res and price > mn1_res:
        return 1
    elif mn1_sup and price < mn1_sup:
        return -1
    elif len(closes) >= 20:
        return 1 if closes[-1] > closes[-20] else -1
    return 1


# ========== Main ==========
if __name__ == "__main__":
    print("=" * 60)
    print("  State Hermass DuckDB Builder - D1 Historical Backfill")
    print("  Optimized: Incremental O(n) computation")
    print("=" * 60)

    if not mt5.initialize():
        print("[FATAL] MT5 not running")
        sys.exit(1)

    acc = mt5.account_info()
    print(f"[MT5] {acc.server} | {acc.login}\n")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"[DB] Removed old database: {DB_PATH}")

    conn = duckdb.connect(str(DB_PATH))

    conn.execute("""
        CREATE TABLE state_snapshots (
            symbol VARCHAR,
            perspective VARCHAR,
            date DATE,
            mn1_hex VARCHAR,
            w1_hex VARCHAR,
            d1_hex VARCHAR,
            mn1_score INTEGER,
            w1_score INTEGER,
            d1_score INTEGER,
            ef_count INTEGER,
            raw_json VARCHAR,
            source VARCHAR
        )
    """)
    print("[DB] Created state_snapshots table (Hermass Schema)")

    total_count = 0
    all_rows = []

    for sym in FOCUS_SYMBOLS:
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_D1, 0, 99999)
        if rates is None or len(rates) < 100:
            print(f"  {sym:12s} -> insufficient data ({len(rates) if rates else 0} bars)")
            continue

        highs = np.array([r[2] for r in rates])
        lows = np.array([r[3] for r in rates])
        closes = np.array([r[4] for r in rates])

        # Compute all states incrementally for each scale
        mn1_states = compute_states_for_symbol(highs, lows, closes, SCALE["MN1"])
        w1_states = compute_states_for_symbol(highs, lows, closes, SCALE["W1"])
        d1_states = compute_states_for_symbol(highs, lows, closes, SCALE["D1"])

        # Build lookup by bar index
        mn1_map = {idx: mag for idx, mag, _, _, _, _ in mn1_states}
        w1_map = {idx: mag for idx, mag, _, _, _, _ in w1_states}
        d1_map = {idx: mag for idx, mag, _, _, _, _ in d1_states}

        # Determine sign once per bar using full history up to that bar
        sym_count = 0
        valid_indices = sorted(set(mn1_map.keys()) & set(w1_map.keys()) & set(d1_map.keys()))

        for idx in valid_indices:
            bar_time = datetime.fromtimestamp(rates[idx][0])
            dt = bar_time.date()
            price = closes[idx]

            sign = determine_sign(price, highs[:idx + 1], lows[:idx + 1], closes[:idx + 1])

            mn1_s = sign * mn1_map[idx]
            w1_s = sign * w1_map[idx]
            d1_s = sign * d1_map[idx]

            mn1_h = _score_to_hex(mn1_s)
            w1_h = _score_to_hex(w1_s)
            d1_h = _score_to_hex(d1_s)

            ef = sum(1 for s in [mn1_s, w1_s, d1_s] if s in (14, 15))

            raw_json = json.dumps({
                "bar_index": idx,
                "timestamp": bar_time.isoformat(),
                "close": float(price),
            })

            all_rows.append({
                "symbol": sym,
                "perspective": "D1",
                "date": dt,
                "mn1_hex": mn1_h,
                "w1_hex": w1_h,
                "d1_hex": d1_h,
                "mn1_score": mn1_s,
                "w1_score": w1_s,
                "d1_score": d1_s,
                "ef_count": ef,
                "raw_json": raw_json,
                "source": "MT5",
            })
            sym_count += 1

        total_count += sym_count
        first_d = datetime.fromtimestamp(rates[0][0]).strftime("%Y-%m-%d")
        last_d = datetime.fromtimestamp(rates[-1][0]).strftime("%Y-%m-%d")
        print(f"  {sym:12s} -> {sym_count:5d} bars [{first_d} ~ {last_d}]")

    if all_rows:
        import pandas as pd
        df = pd.DataFrame(all_rows)
        conn.register("df", df)
        conn.execute("INSERT INTO state_snapshots SELECT * FROM df")
        conn.commit()
        print(f"\n[DB] Inserted {len(all_rows)} records")

    print("\n" + "=" * 60)
    print("  Statistics Report")
    print("=" * 60)

    result = conn.execute("""
        SELECT COUNT(*) as total, COUNT(DISTINCT symbol) as symbols,
               MIN(date) as start_date, MAX(date) as end_date
        FROM state_snapshots
    """).fetchone()
    print(f"\nTotal records: {result[0]}")
    print(f"Symbols: {result[1]}")
    print(f"Date range: {result[2]} ~ {result[3]}")

    print("\nRecords per symbol:")
    for row in conn.execute("""
        SELECT symbol, COUNT(*) as cnt, MIN(date) as d0, MAX(date) as d1
        FROM state_snapshots GROUP BY symbol ORDER BY cnt DESC
    """).fetchall():
        print(f"  {row[0]:12s}: {row[1]:5d} bars [{row[2]} ~ {row[3]}]")

    print("\nEF distribution:")
    for row in conn.execute("""
        SELECT ef_count, COUNT(*) as cnt,
               ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct
        FROM state_snapshots GROUP BY ef_count ORDER BY ef_count
    """).fetchall():
        print(f"  EF={row[0]}: {row[1]} ({row[2]}%)")

    parquet_path = DB_PATH.parent / "state_hermass.parquet"
    conn.execute(f"COPY state_snapshots TO '{parquet_path}' (FORMAT PARQUET)")
    print(f"\n[Export] Parquet: {parquet_path} ({parquet_path.stat().st_size / 1024:.1f} KB)")

    conn.close()
    mt5.shutdown()

    print("\n" + "=" * 60)
    print(f"[Done] {DB_PATH} ({DB_PATH.stat().st_size / 1024:.1f} KB)")
    print("=" * 60)
