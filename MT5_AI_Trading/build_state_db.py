"""
State历史回填 — 全部用D1数据 + 窗口缩放
=======================================
核心原理: 不依赖各周期K线, 全部用D1数据计算, 避免MN1/W1数据不足问题

D1视角下:
  MN1 State: D1_BB(20*22≈440), D1_ADX(14*22), D1_SR(k=5*22), position用D1 close
  W1 State:  D1_BB(20*5≈100), D1_ADX(14*5), D1_SR(k=5*5), position用D1 close
  D1 State:  D1_BB(20), D1_ADX(14), D1_SR(k=5), position用D1 close
"""

import MetaTrader5 as mt5
import sqlite3, json, sys, io
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CORE_DIR = Path(__file__).parent / "python" / "core"
sys.path.insert(0, str(CORE_DIR))
from state_database import StateDatabase, StateSnapshot

FOCUS_SYMBOLS = [
    "EURUSD","GBPUSD","USDJPY","AUDUSD","NZDUSD","USDCAD","USDCHF",
    "EURJPY","GBPJPY","AUDJPY","EURGBP","EURCHF","EURCAD","GBPCHF",
    "BTCUSD","ETHUSD","XRPUSD",
]

BB_PERIOD = 20; BB_STDDEV = 2.0
BB_PERCENTILE_WINDOW = 20; BB_COMPRESSION_Q = 0.20
ATR_PERIOD = 14; ADX_PERIOD = 14; ADX_SLOPE = 3
FRACTAL_K = 5; FRACTAL_LAG = 3

# 周期缩放系数 (D1基础)
SCALE = {"MN1": 22, "W1": 5, "D1": 1}

def _score_to_hex(score: int) -> str:
    s = abs(score); h = f"{s:X}"
    return f"-{h}" if score < 0 else h

def calc_adx(highs, lows, closes, scale=1):
    """计算ADX趋势bit (1=有趋势,0=无趋势)"""
    per = ADX_PERIOD * scale
    slope_w = ADX_SLOPE * scale
    n = len(closes)
    if n < per + slope_w + 2:
        return 0

    adx_vals = []
    for i in range(per, n):
        tr_sum = 0; plus_dm_sum = 0; minus_dm_sum = 0
        for j in range(i - per, i):
            tr = max(highs[j] - lows[j],
                     abs(highs[j] - closes[j-1]),
                     abs(lows[j] - closes[j-1]))
            tr_sum += tr
            pdm = highs[j] - highs[j-1] if highs[j] > highs[j-1] and highs[j] - highs[j-1] > lows[j-1] - lows[j] else 0
            mdm = lows[j-1] - lows[j] if lows[j-1] > lows[j] and lows[j-1] - lows[j] > highs[j] - highs[j-1] else 0
            plus_dm_sum += pdm; minus_dm_sum += mdm
        atr = tr_sum / per
        pdi = plus_dm_sum / per / atr * 100 if atr > 0 else 0
        mdi = minus_dm_sum / per / atr * 100 if atr > 0 else 0
        dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0
        adx_vals.append(dx)

    if len(adx_vals) < slope_w + 1:
        return 0
    cur = adx_vals[-1]; prev = adx_vals[-1 - slope_w]
    slope = cur - prev
    if cur >= 25 and slope > 0: return 1
    if cur > 20: return 1
    if cur <= 13 and slope < 0: return 0
    return 0

def calc_base(closes, scale=1):
    """计算布林带宽base (8=扩张,0=收缩)"""
    per = BB_PERIOD * scale
    pw = BB_PERCENTILE_WINDOW
    n = len(closes)
    if n < per + pw:
        return 0

    bbw_list = []
    for i in range(n - per - pw, n - per + 1):
        seg = closes[i:i + per]
        if len(seg) < per: continue
        mid = np.mean(seg); std = np.std(seg, ddof=0)
        up = mid + BB_STDDEV * std; lo = mid - BB_STDDEV * std
        bbw_list.append((up - lo) / mid if mid > 0 else 0)

    if len(bbw_list) < 2: return 0
    cur = bbw_list[-1]; hist = bbw_list[:-1]
    q20 = np.percentile(hist, BB_COMPRESSION_Q * 100)
    return 0 if cur < q20 else 8

def calc_position(price, highs, lows, scale=1):
    """计算SR突破position (2=突破,0=未突破)"""
    k = FRACTAL_K * scale; lag = FRACTAL_LAG * scale
    n = len(highs)
    if n < k + lag: return 0

    half = k // 2
    res_levels = []; sup_levels = []
    for i in range(half, n - half - lag):
        is_r = True; is_s = True
        for j in range(1, half + 1):
            if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]: is_r = False
            if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]: is_s = False
        if is_r: res_levels.append(highs[i])
        if is_s: sup_levels.append(lows[i])

    sr_r = res_levels[-1] if res_levels else 0
    sr_s = sup_levels[-1] if sup_levels else 0
    if sr_r > 0 and price > sr_r: return 2
    if sr_s > 0 and price < sr_s: return 2
    return 0

def calc_volatility(highs, lows, closes, scale=1):
    """计算ATR波动volatility (1=扩张,0=稳定)"""
    per = ATR_PERIOD * scale
    n = len(closes)
    if n < per + 2: return 0
    tr1 = max(highs[-1] - lows[-1], abs(highs[-1] - closes[-2]), abs(lows[-1] - closes[-2]))
    tr2 = max(highs[-2] - lows[-2], abs(highs[-2] - closes[-3]), abs(lows[-2] - closes[-3]))
    return 1 if tr1 > tr2 else 0

def calc_one_state(highs, lows, closes, price_close, scale=1):
    """基于D1数据计算单个周期的State hex和score"""
    base = calc_base(closes, scale)
    trend = calc_adx(highs, lows, closes, scale)
    pos = calc_position(price_close, highs, lows, scale)
    vol = calc_volatility(highs, lows, closes, scale)

    magnitude = base + trend * 4 + pos + vol

    # 符号裁决: 看MN1级SR
    mn1_res = None; mn1_sup = None
    mn1_scale = SCALE["MN1"]
    mn1_k = FRACTAL_K * mn1_scale; mn1_lag = FRACTAL_LAG * mn1_scale
    mn1_half = mn1_k // 2
    n = len(highs)
    if n > mn1_k + mn1_lag:
        for i in range(mn1_half, n - mn1_half - mn1_lag):
            is_r = True; is_s = True
            for j in range(1, mn1_half + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]: is_r = False
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]: is_s = False
            if is_r: mn1_res = max(mn1_res or 0, highs[i])
            if is_s: mn1_sup = min(mn1_sup or float('inf'), lows[i])

    sign = 1
    if mn1_res and price_close > mn1_res: sign = 1
    elif mn1_sup and price_close < mn1_sup: sign = -1
    elif len(closes) >= 20: sign = 1 if closes[-1] > closes[-20] else -1

    score = sign * magnitude
    return _score_to_hex(score), score

# ========== 主流程 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("  State DB Builder v3.1 — D1历史回填")
    print("=" * 60)

    if not mt5.initialize():
        print("[FATAL] MT5 未运行"); exit(1)

    acc = mt5.account_info()
    print(f"[MT5] {acc.server} | {acc.login}")

    db = StateDatabase()
    db.db_path.parent.mkdir(parents=True, exist_ok=True)

    # 重建
    _conn = sqlite3.connect(str(db.db_path))
    _conn.executescript("DROP TABLE IF EXISTS state_snapshots; DROP TABLE IF EXISTS state_slices; DROP TABLE IF EXISTS symbols_registry; DROP TABLE IF EXISTS platform_sources;")
    _conn.commit(); _conn.close()
    db._init_schema()

    total_count = 0
    for sym in FOCUS_SYMBOLS:
        db.register_symbol(sym, "forex")

        # 拉最大D1数据
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_D1, 0, 99999)
        if rates is None or len(rates) < 100:
            print(f"  {sym:8s} -> 数据不足({len(rates) if rates else 0}条)")
            continue

        highs = np.array([r[2] for r in rates]); lows = np.array([r[3] for r in rates])
        closes = np.array([r[4] for r in rates])

        sym_count = 0
        for i in range(50, len(rates)):
            bar_time = datetime.fromtimestamp(rates[i][0])
            date_str = bar_time.strftime("%Y-%m-%d")
            price = closes[i]

            # 切片: 只用该日期之前的D1数据
            try:
                mn1_h, mn1_s = calc_one_state(highs[:i+1], lows[:i+1], closes[:i+1], price, SCALE["MN1"])
                w1_h, w1_s   = calc_one_state(highs[:i+1], lows[:i+1], closes[:i+1], price, SCALE["W1"])
                d1_h, d1_s   = calc_one_state(highs[:i+1], lows[:i+1], closes[:i+1], price, SCALE["D1"])
                ef = sum(1 for s in [mn1_s, w1_s, d1_s] if s in (14, 15))

                snap = StateSnapshot(symbol=sym, perspective="D1", date=date_str,
                    mn1_hex=mn1_h, w1_hex=w1_h, d1_hex=d1_h,
                    mn1_score=mn1_s, w1_score=w1_s, d1_score=d1_s,
                    ef_count=ef, raw_json="{}")
                db.insert_snapshot(snap)
                sym_count += 1
            except Exception as e:
                if i % 500 == 0:
                    print(f"  {sym} bar={i} error: {e}")

        total_count += sym_count
        first_d = datetime.fromtimestamp(rates[0][0]).strftime("%Y-%m-%d")
        last_d  = datetime.fromtimestamp(rates[-1][0]).strftime("%Y-%m-%d")
        print(f"  {sym:8s} -> {sym_count:5d}条 [{first_d} ~ {last_d}]")

    # 切片
    print(f"\n[切片] 生成中...")
    slice_count = 0
    for sym in FOCUS_SYMBOLS:
        rows = sqlite3.connect(str(db.db_path)).execute(
            "SELECT date,mn1_hex,w1_hex,d1_hex FROM state_snapshots WHERE symbol=? AND perspective='D1' ORDER BY date",
            (sym,)).fetchall()
        if len(rows) < 10: continue
        patterns = defaultdict(lambda: {"count": 0})
        for r in rows:
            patterns[f"{r[1]}_{r[2]}_{r[3]}"]["count"] += 1
        conn = sqlite3.connect(str(db.db_path))
        for pat, data in patterns.items():
            parts = pat.split("_")
            if len(parts) != 3: continue
            conn.execute(
                "INSERT OR REPLACE INTO state_slices(slice_id,symbol,perspective,pattern,mn1_hex,w1_hex,d1_hex,occurrence_count,tags) VALUES(?,?,?,?,?,?,?,?,?)",
                (f"{sym}_D1_{pat}", sym, "D1", pat, parts[0], parts[1], parts[2], data["count"], '["D1"]'))
            slice_count += 1
        conn.commit(); conn.close()

    # 报告
    stats = db.get_stats()
    print(f"\n{'='*60}")
    print(f"  快照: {stats['total_snapshots']} | 切片: {stats['total_slices']} | 品种: {stats['unique_symbols']}")
    print(f"{'='*60}")
    mt5.shutdown()
    print(f"[Done] {db.db_path} ({db.db_path.stat().st_size/1024/1024:.1f}MB)")
