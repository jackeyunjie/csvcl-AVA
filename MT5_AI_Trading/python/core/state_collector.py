"""
State 采集器 v1.0
================
从MT5获取OHLCV → 按hermass规则计算4-bit State编码 → 存入数据库

支持:
  - 4种视角 (D1/W1/MN1/H1)
  - 5种周期 (MN1/W1/D1/H4/H1)
  - 34个重点品种
  - 多平台数据源 (AVATRADE MT5)
"""

import MetaTrader5 as mt5
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path
import logging
import time
import sys, os

sys.path.insert(0, str(Path(__file__).parent))
from state_database import (
    StateDatabase, StateSnapshot, StateSlice,
    PERSPECTIVES, TIMEFRAMES, FOCUS_SYMBOLS, PERSPECTIVE_PRICE_TF
)

logger = logging.getLogger("StateCollector")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ====== 不可变参数 (来自hermass_state_mt5_package) ======
BB_PERIOD = 20
BB_STDDEV = 2.0
BB_PERCENTILE_WINDOW = 20
BB_COMPRESSION_QUANTILE = 0.20
ATR_PERIOD = 14
ADX_PERIOD = 14
ADX_SLOPE_WINDOW = 3
FRACTAL_K = 5
FRACTAL_CONFIRM_LAG = 3

MT5_TF_MAP = {
    "MN1": mt5.TIMEFRAME_MN1, "W1": mt5.TIMEFRAME_W1,
    "D1": mt5.TIMEFRAME_D1, "H4": mt5.TIMEFRAME_H4,
    "H1": mt5.TIMEFRAME_H1,
}

class StateCollector:
    def __init__(self, db: StateDatabase, default_perspective: str = "D1"):
        self.db = db
        self.default_perspective = default_perspective

    # ====== 核心入口：对单个品种计算4视角State ======
    def collect_symbol(self, symbol: str, perspective: str = None
                       ) -> Dict[str, StateSnapshot]:
        """计算一个品种在指定视角下的所有周期State"""
        perspectives = [perspective] if perspective else PERSPECTIVES
        results = {}

        for persp in perspectives:
            try:
                snap = self._calc_for_perspective(symbol, persp)
                if snap:
                    results[persp] = snap
                    self.db.insert_snapshot(snap)
            except Exception as e:
                logger.warning(f"{symbol}/{persp} 计算失败: {e}")

        return results

    def _calc_for_perspective(self, symbol: str, perspective: str
                              ) -> Optional[StateSnapshot]:
        """核心计算：给定品种+视角，计算MN1/W1/D1三个周期的State"""
        price_tf = PERSPECTIVE_PRICE_TF[perspective]
        price_close = self._get_latest_close(symbol, price_tf)
        if price_close is None:
            return None

        today = datetime.now().strftime("%Y-%m-%d")

        # 计算每个周期的State
        mn1_state = self._calc_period_state(symbol, "MN1", price_close, price_tf)
        w1_state = self._calc_period_state(symbol, "W1", price_close, price_tf)
        d1_state = self._calc_period_state(symbol, "D1", price_close, price_tf)

        pattern = f"{mn1_state[0]}{w1_state[0]}{d1_state[0]}"
        ef_count = sum(1 for s in [mn1_state[1], w1_state[1], d1_state[1]]
                       if s in (14, 15))

        raw = json.dumps({
            "symbol": symbol, "perspective": perspective,
            "price_close": price_close, "price_tf": price_tf,
            "mn1": {"hex": mn1_state[0], "score": mn1_state[1]},
            "w1": {"hex": w1_state[0], "score": w1_state[1]},
            "d1": {"hex": d1_state[0], "score": d1_state[1]},
        })

        return StateSnapshot(
            symbol=symbol, perspective=perspective, date=today,
            mn1_hex=mn1_state[0], w1_hex=w1_state[0], d1_hex=d1_state[0],
            mn1_score=mn1_state[1], w1_score=w1_state[1], d1_score=d1_state[1],
            ef_count=ef_count, raw_json=raw)

    # ====== 单周期State计算 ======
    def _calc_period_state(self, symbol: str, tf_str: str,
                            perspective_close: float,
                            price_tf: str) -> Tuple[str, int]:
        """计算单个周期(MN1/W1/D1)的State hex和score"""
        tf = MT5_TF_MAP[tf_str]
        rates = self._get_rates(symbol, tf, 100)
        if rates is None or len(rates) < 50:
            return ("0", 0)

        closes = np.array([r[4] for r in rates])
        highs = np.array([r[2] for r in rates])
        lows = np.array([r[3] for r in rates])

        # Base: 布林带宽分位
        base = self._calc_base(closes)

        # Trend: ADX方向
        trend_bit = self._calc_trend(highs, lows, closes)

        # Position: 价格突破SR
        position_bit = self._calc_position(perspective_close, highs, lows, closes)

        # Volatility: ATR扩张
        volatility_bit = self._calc_volatility(highs, lows, closes)

        # 符号裁决
        sign = self._calc_sign(perspective_close, highs, lows, closes)

        magnitude = base + trend_bit * 4 + position_bit + volatility_bit
        score = sign * magnitude

        hex_val = _score_to_hex(score)
        return (hex_val, score)

    # ====== Base ======
    def _calc_base(self, closes: np.ndarray) -> int:
        if len(closes) < BB_PERIOD + BB_PERCENTILE_WINDOW:
            return 0
        bb_mid = np.convolve(closes, np.ones(BB_PERIOD)/BB_PERIOD, mode='valid')
        if len(bb_mid) < BB_PERCENTILE_WINDOW:
            return 0

        bb_std_list = []
        for i in range(len(bb_mid) - BB_PERCENTILE_WINDOW, len(bb_mid)):
            seg = closes[i:i+BB_PERIOD]
            if len(seg) < BB_PERIOD:
                continue
            avg = np.mean(seg)
            std = np.std(seg, ddof=0)
            upper = avg + BB_STDDEV * std
            lower = avg - BB_STDDEV * std
            mid = avg
            bb_std_list.append((upper - lower) / mid if mid > 0 else 0)

        if not bb_std_list:
            return 0

        current_bbw = bb_std_list[-1]
        percentile = np.percentile(bb_std_list[:-1] if len(bb_std_list) > 1 else bb_std_list,
                                    BB_COMPRESSION_QUANTILE * 100)

        return 0 if current_bbw < percentile else 8

    # ====== Trend ======
    def _calc_trend(self, highs: np.ndarray, lows: np.ndarray,
                     closes: np.ndarray) -> int:
        if len(closes) < ADX_PERIOD + ADX_SLOPE_WINDOW:
            return 0

        adx_vals = []
        tr_vals = []
        plus_di_vals = []
        minus_di_vals = []

        for i in range(ADX_PERIOD, len(highs)):
            tr = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i-1]),
                     abs(lows[i] - closes[i-1]))
            tr_vals.append(tr)
            plus_dm = highs[i] - highs[i-1] if highs[i] > highs[i-1] and \
                       highs[i] - highs[i-1] > lows[i-1] - lows[i] else 0
            minus_dm = lows[i-1] - lows[i] if lows[i-1] > lows[i] and \
                        lows[i-1] - lows[i] > highs[i] - highs[i-1] else 0
            plus_di_vals.append(plus_dm)
            minus_di_vals.append(minus_dm)

        if len(tr_vals) < ADX_PERIOD:
            return 0

        atr = sum(tr_vals[-ADX_PERIOD:]) / ADX_PERIOD
        plus_di = sum(plus_di_vals[-ADX_PERIOD:]) / ADX_PERIOD / atr * 100 if atr > 0 else 0
        minus_di = sum(minus_di_vals[-ADX_PERIOD:]) / ADX_PERIOD / atr * 100 if atr > 0 else 0

        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0

        for i in range(ADX_PERIOD, min(len(tr_vals), 2*ADX_PERIOD)):
            atr2 = sum(tr_vals[i-ADX_PERIOD:i]) / ADX_PERIOD
            pd2 = sum(plus_di_vals[i-ADX_PERIOD:i]) / ADX_PERIOD / atr2 * 100 if atr2 > 0 else 0
            md2 = sum(minus_di_vals[i-ADX_PERIOD:i]) / ADX_PERIOD / atr2 * 100 if atr2 > 0 else 0
            dx2 = abs(pd2 - md2) / (pd2 + md2) * 100 if (pd2 + md2) > 0 else 0
            adx_vals.append(dx2)

        if len(adx_vals) < ADX_SLOPE_WINDOW + 1:
            return 0

        current_adx = adx_vals[-1]
        prev_adx = adx_vals[-1 - ADX_SLOPE_WINDOW]
        adx_slope = current_adx - prev_adx
        di_dir = 1 if plus_di > minus_di else -1

        if current_adx >= 25 and adx_slope > 0:
            return 1
        if current_adx > 20 and di_dir > 0:
            return 1
        if current_adx <= 13 and adx_slope < 0:
            return 0
        return 0

    # ====== Position (SR Breakout) ======
    def _calc_position(self, price: float, highs: np.ndarray,
                        lows: np.ndarray, closes: np.ndarray) -> int:
        if len(highs) < FRACTAL_K + FRACTAL_CONFIRM_LAG:
            return 0

        half_k = FRACTAL_K // 2
        resistance_levels = []
        support_levels = []

        for i in range(half_k, len(highs) - half_k - FRACTAL_CONFIRM_LAG):
            is_resistance = True
            is_support = True
            for j in range(1, half_k + 1):
                if highs[i] <= highs[i-j] or highs[i] <= highs[i+j]:
                    is_resistance = False
                if lows[i] >= lows[i-j] or lows[i] >= lows[i+j]:
                    is_support = False
            if is_resistance:
                resistance_levels.append(highs[i])
            if is_support:
                support_levels.append(lows[i])

        sr_resistance = resistance_levels[-1] if resistance_levels else 0
        sr_support = support_levels[-1] if support_levels else 0

        if sr_resistance > 0 and price > sr_resistance:
            return 2
        if sr_support > 0 and price < sr_support:
            return 2
        return 0

    # ====== Volatility ======
    def _calc_volatility(self, highs: np.ndarray, lows: np.ndarray,
                          closes: np.ndarray) -> int:
        if len(closes) < ATR_PERIOD + 1:
            return 0

        tr_current = max(highs[-1] - lows[-1],
                         abs(highs[-1] - closes[-2]),
                         abs(lows[-1] - closes[-2]))
        tr_prev = max(highs[-2] - lows[-2],
                      abs(highs[-2] - closes[-3]),
                      abs(lows[-2] - closes[-3]))

        return 1 if tr_current > tr_prev else 0

    # ====== Sign ======
    def _calc_sign(self, price: float, highs: np.ndarray,
                    lows: np.ndarray, closes: np.ndarray) -> int:
        """符号裁决: 先看MN1 SR, 再看大周期框架方向"""
        half_k = FRACTAL_K // 2
        mn1_resistance = 0
        mn1_support = float('inf')
        for i in range(half_k, len(highs) - half_k - FRACTAL_CONFIRM_LAG):
            is_res = True
            is_sup = True
            for j in range(1, half_k + 1):
                if highs[i] <= highs[i-j] or highs[i] <= highs[i+j]:
                    is_res = False
                if lows[i] >= lows[i-j] or lows[i] >= lows[i+j]:
                    is_sup = False
            if is_res and highs[i] > mn1_resistance:
                mn1_resistance = highs[i]
            if is_sup and lows[i] < mn1_support:
                mn1_support = lows[i]

        if mn1_resistance > 0 and price > mn1_resistance:
            return 1
        if mn1_support < float('inf') and price < mn1_support:
            return -1
        # 在区间内，参考趋势方向
        if len(closes) >= 20:
            return 1 if closes[-1] > closes[-20] else -1
        return 1

    # ====== MT5数据获取 ======
    def _get_rates(self, symbol: str, tf, count: int) -> Optional[np.ndarray]:
        try:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            return rates if rates is not None and len(rates) > 0 else None
        except:
            return None

    def _get_latest_close(self, symbol: str, tf_str: str) -> Optional[float]:
        tf = MT5_TF_MAP.get(tf_str, mt5.TIMEFRAME_D1)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, 1)
        return rates[0][4] if rates is not None and len(rates) > 0 else None

    # ====== 批量采集 ======
    def collect_all(self, symbols: List[str] = None,
                    perspectives: List[str] = None):
        syms = symbols or FOCUS_SYMBOLS
        persps = perspectives or PERSPECTIVES
        total = len(syms) * len(persps)
        done = 0

        logger.info(f"开始采集: {len(syms)}品种 × {len(persps)}视角 = {total}快照")

        for sym in syms:
            for persp in persps:
                try:
                    snap = self._calc_for_perspective(sym, persp)
                    if snap:
                        self.db.insert_snapshot(snap)
                        self.db.register_symbol(sym)
                    done += 1
                    if done % 10 == 0:
                        logger.info(f"进度: {done}/{total}")
                except Exception as e:
                    logger.warning(f"{sym}/{persp}: {e}")
                time.sleep(0.05)

        return done

    # ====== 切片生成 ======
    def build_slices(self, symbol: str, perspective: str = "D1"):
        """为某个品种/视角的所有历史State生成切片库"""
        snaps = self.db.query_snapshots(symbol, perspective, limit=500)
        if len(snaps) < 5:
            return 0

        pattern_counts = defaultdict(lambda: {"count": 0, "returns": []})
        for i in range(2, len(snaps)):
            pattern = f"{snaps[i].mn1_hex}_{snaps[i].w1_hex}_{snaps[i].d1_hex}"
            pattern_counts[pattern]["count"] += 1

        count = 0
        for pattern, data in pattern_counts.items():
            parts = pattern.split("_")
            if len(parts) != 3:
                continue

            sl = StateSlice(
                slice_id=f"{symbol}_{perspective}_{pattern}",
                pattern=pattern,
                mn1_hex=parts[0], w1_hex=parts[1], d1_hex=parts[2],
                occurrence_count=data["count"],
                tags=[perspective, symbol]
            )
            self.db.insert_slice(sl, symbol, perspective)
            count += 1

        return count


def _score_to_hex(score: int) -> str:
    """score转16进制字符, 带负号"""
    if score < 0:
        return f"-{(-score):X}"
    return f"{score:X}"


# ====== 命令行入口 ======
if __name__ == "__main__":
    db = StateDatabase()
    collector = StateCollector(db)

    print("=" * 55)
    print("  State 数据库采集器")
    print("=" * 55)

    if not mt5.initialize():
        print("[错误] MT5 未连接")
        exit(1)

    acc = mt5.account_info()
    print(f"[连接] {acc.server} | 账号: {acc.login}")

    # 采集
    collector.collect_all(FOCUS_SYMBOLS, ["D1"])

    # 生成切片
    for sym in FOCUS_SYMBOLS:
        collector.build_slices(sym, "D1")

    stats = db.get_stats()
    print(f"\n[完成] {stats['total_snapshots']}快照 | "
          f"{stats['total_slices']}切片 | "
          f"{stats['unique_symbols']}品种")

    # 展示EF扫描
    ef_list = db.query_ef_scan("D1", min_ef=2)
    print(f"\n[EF扫描] ef_count>=2 的品种:")
    for r in ef_list[:15]:
        print(f"  {r['symbol']:10s} {r['date']} "
              f"MN1={r['mn1_hex']} W1={r['w1_hex']} D1={r['d1_hex']} "
              f"ef={r['ef_count']}")

    mt5.shutdown()
