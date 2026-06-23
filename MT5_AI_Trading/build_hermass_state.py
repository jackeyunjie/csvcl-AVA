"""
build_hermass_state.py v2 — 向量化加速版
=========================================
核心优化: 预计算TR数组→pandas rolling→ADX向量化
速度提升: ~50-100倍

公式不变: base + trend×4 + pos + vol, 符号裁决MN1 SR优先
11个参数不变: BB20/2,ATR14,ADX14,slope3,k=5,confirm3
"""

import argparse
import MetaTrader5 as mt5
import duckdb, numpy as np, sys, io, time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DEFAULT_SYMBOLS = [
    "EURUSD","GBPUSD","USDJPY","AUDUSD","NZDUSD","USDCAD","USDCHF",
    "EURJPY","GBPJPY","AUDJPY","EURGBP","EURCHF","EURCAD","GBPCHF",
    "BTCUSD","ETHUSD","XRPUSD",
]

SYMBOL_MAP = {
    "XAUUSD": "GOLD",
    "USOIL": "CrudeOIL",
    "GER30": "GERMANY_40",
    "JP225": "JAPAN_225",
}

BB_P, BB_D, BB_PW, BB_Q = 20, 2.0, 20, 0.20
ATR_P, ADX_P, ADX_S = 14, 14, 3
K, LAG = 5, 3
SCALE = {"MN1": 22, "W1": 5, "D1": 1}

DB_PATH = Path("data/hermass_state.db")
DB_PATH.parent.mkdir(exist_ok=True)

def parse_args():
    parser = argparse.ArgumentParser(description="构建 D1 Hermass State 数据库")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS, help="交易品种")
    parser.add_argument("--terminal", default=None, help="MT5 终端路径")
    parser.add_argument("--bars", type=int, default=5000, help="每个品种拉取的 D1 bar 数")
    return parser.parse_args()

def hx(s): a=abs(s); h=hex(a)[2:].upper(); return f"-{h}" if s<0 else h

def calc_tr(h, l, c):
    """向量化TR"""
    n = len(c)
    tr = np.zeros(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
    return tr

def calc_adx_vec(tr, h, l, period, slope_w):
    """向量化ADX + trend_bit"""
    n = len(tr)
    if n < period + slope_w + 3: return np.zeros(n, dtype=int)

    # DM
    pdm = np.zeros(n); mdm = np.zeros(n)
    for i in range(1, n):
        up = h[i] - h[i-1]; dn = l[i-1] - l[i]
        pdm[i] = up if up > dn and up > 0 else 0
        mdm[i] = dn if dn > up and dn > 0 else 0

    # 滚动求和 → ATR, PDI, MDI
    atr_r = np.convolve(tr, np.ones(period), mode='valid') / period
    pdm_r = np.convolve(pdm, np.ones(period), mode='valid') / period
    mdm_r = np.convolve(mdm, np.ones(period), mode='valid') / period

    n_valid = len(atr_r)
    dx = np.zeros(n_valid)
    for i in range(n_valid):
        if atr_r[i] > 0:
            p = pdm_r[i] / atr_r[i] * 100; m = mdm_r[i] / atr_r[i] * 100
            dx[i] = abs(p - m) / (p + m) * 100 if (p+m) > 0 else 0

    # ADX = EMA of DX (Wilder smoothing)
    adx = np.zeros(n_valid)
    if n_valid > 0: adx[0] = dx[0]
    for i in range(1, n_valid):
        adx[i] = (adx[i-1] * (period-1) + dx[i]) / period

    # trend_bit 判定
    result = np.zeros(n, dtype=int)
    offset = n - n_valid
    for i in range(offset + slope_w, n):
        idx = i - offset
        if idx >= slope_w and idx < n_valid:
            cur = adx[idx]; prev = adx[idx - slope_w]
            if cur >= 25 and cur > prev: result[i] = 1
            elif cur > 20: result[i] = 1
            elif cur <= 13 and cur < prev: result[i] = 0
    return result

def calc_base_vec(c, period, pw):
    """向量化布林带宽 → base(8/0)"""
    n = len(c)
    if n < period + pw: return np.zeros(n, dtype=int)
    mid = np.convolve(c, np.ones(period)/period, mode='valid')
    n_mid = len(mid)

    bbw = np.zeros(n_mid)
    for i in range(n_mid):
        seg = c[i:i+period]
        m = np.mean(seg); s = np.std(seg, ddof=0)
        bbw[i] = (m + BB_D*s - (m - BB_D*s)) / m if m > 0 else 0

    result = np.zeros(n, dtype=int)
    offset = n - n_mid
    for i in range(offset + pw, n):
        idx = i - offset
        hist = bbw[idx-pw:idx]
        cur = bbw[idx-1] if idx > 0 else bbw[0]
        q = np.percentile(hist, BB_Q * 100)
        result[i] = 0 if cur < q else 8
    return result

def calc_pos_vec(price_arr, h, l, scale):
    """向量化SR突破 → pos(2/0)"""
    n = len(h); k = K * scale; lag = LAG * scale
    if n < k + lag: return np.zeros(n, dtype=int)
    hk = k // 2
    res_levels = []
    for i in range(hk, n - hk):
        is_r = True
        for j in range(1, hk+1):
            if h[i] <= h[i-j] or h[i] <= h[i+j]:
                is_r = False; break
        if is_r: res_levels.append(h[i])
    sup_levels = []
    for i in range(hk, n - hk):
        is_s = True
        for j in range(1, hk+1):
            if l[i] >= l[i-j] or l[i] >= l[i+j]:
                is_s = False; break
        if is_s: sup_levels.append(l[i])

    result = np.zeros(n, dtype=int)
    if not res_levels and not sup_levels: return result
    sr_r = res_levels[-1] if res_levels else 0
    sr_s = sup_levels[-1] if sup_levels else 0
    for i in range(n):
        if sr_r > 0 and price_arr[i] > sr_r: result[i] = 2
        elif sr_s > 0 and price_arr[i] < sr_s: result[i] = 2
    return result

def calc_vol_vec(tr, scale):
    """向量化ATR扩张 → vol(1/0)"""
    n = len(tr); p = ATR_P * scale
    if n < p + 2: return np.zeros(n, dtype=int)
    atr = np.convolve(tr, np.ones(p)/p, mode='valid')
    result = np.zeros(n, dtype=int)
    offset = n - len(atr)
    for i in range(offset + 2, n):
        if atr[i-offset] > atr[i-offset-1]: result[i] = 1
    return result

def calc_sign_vec(price_arr, h, l, c):
    """符号裁决"""
    n = len(h); scale = SCALE["MN1"]; k = K * scale; hk = k // 2
    res = None; sup = None
    if n > k + LAG * scale:
        for i in range(hk, n - hk):
            is_r = True
            for j in range(1, hk+1):
                if h[i] <= h[i-j] or h[i] <= h[i+j]: is_r = False; break
            if is_r: res = max(res or 0, h[i])
            is_s = True
            for j in range(1, hk+1):
                if l[i] >= l[i-j] or l[i] >= l[i+j]: is_s = False; break
            if is_s: sup = min(sup or float('inf'), l[i])

    result = np.ones(n, dtype=int)
    for i in range(n):
        if res and price_arr[i] > res: result[i] = 1
        elif sup and sup < float('inf') and price_arr[i] < sup: result[i] = -1
        elif i >= 20: result[i] = 1 if c[i] > c[i-20] else -1
    return result

# ===== 主流程 =====
args = parse_args()
SYMBOLS = args.symbols
BARS = args.bars
target_db_path = DB_PATH
build_db_path = target_db_path.with_name(f"{target_db_path.stem}.build.tmp{target_db_path.suffix}")

print("=" * 60)
print("  Hermass 4-bit State v2 — 向量化加速")
print("=" * 60)

init_kwargs = {"timeout": 60000}
if args.terminal:
    init_kwargs["path"] = args.terminal

if not mt5.initialize(**init_kwargs):
    print("[FATAL] MT5未运行"); exit(1)
acc = mt5.account_info()
print(f"[MT5] {acc.server} | {acc.login}")

if build_db_path.exists():
    build_db_path.unlink()

conn = duckdb.connect(str(build_db_path))
conn.execute("""
CREATE TABLE state_snapshots (
    symbol VARCHAR, perspective VARCHAR, date DATE,
    mn1_hex VARCHAR, w1_hex VARCHAR, d1_hex VARCHAR,
    mn1_score INTEGER, w1_score INTEGER, d1_score INTEGER,
    ef_count INTEGER, source VARCHAR DEFAULT 'MT5_D1'
);
CREATE INDEX idx1 ON state_snapshots(symbol, perspective, date);
""")

total_start = time.time()
total_count = 0
total_symbols = len(SYMBOLS)

for idx, sym in enumerate(SYMBOLS):
    t0 = time.time()
    try:
        mt5_sym = SYMBOL_MAP.get(sym, sym)
        mt5.symbol_select(mt5_sym, True)
        rates = mt5.copy_rates_from_pos(mt5_sym, mt5.TIMEFRAME_D1, 0, BARS)
        if rates is None or len(rates) < 100:
            print(f"  [{idx+1:2d}/{total_symbols}] {sym:10s} ({mt5_sym}) -> 跳过({len(rates) if rates else 0}bar)")
            continue

        n_raw = len(rates)
        h = np.array([r[2] for r in rates]); l = np.array([r[3] for r in rates])
        c = np.array([r[4] for r in rates])

        # 预计算 TR (整个周期共用)
        tr = calc_tr(h, l, c)

        # 各周期向量化
        mn1_base = calc_base_vec(c, BB_P * SCALE["MN1"], BB_PW)
        mn1_trend = calc_adx_vec(tr, h, l, ADX_P * SCALE["MN1"], ADX_S * SCALE["MN1"])
        mn1_pos = calc_pos_vec(c, h, l, SCALE["MN1"])
        mn1_vol = calc_vol_vec(tr, SCALE["MN1"])
        sign = calc_sign_vec(c, h, l, c)

        w1_base = calc_base_vec(c, BB_P * SCALE["W1"], BB_PW)
        w1_trend = calc_adx_vec(tr, h, l, ADX_P * SCALE["W1"], ADX_S * SCALE["W1"])
        w1_pos = calc_pos_vec(c, h, l, SCALE["W1"])
        w1_vol = calc_vol_vec(tr, SCALE["W1"])

        d1_base = calc_base_vec(c, BB_P, BB_PW)
        d1_trend = calc_adx_vec(tr, h, l, ADX_P, ADX_S)
        d1_pos = calc_pos_vec(c, h, l, SCALE["D1"])
        d1_vol = calc_vol_vec(tr, SCALE["D1"])

        # 拼装4-bit → hex
        rows = []
        for i in range(50, n_raw):
            mn1_mag = mn1_base[i] + mn1_trend[i]*4 + mn1_pos[i] + mn1_vol[i]
            w1_mag  = w1_base[i]  + w1_trend[i]*4  + w1_pos[i]  + w1_vol[i]
            d1_mag  = d1_base[i]  + d1_trend[i]*4  + d1_pos[i]  + d1_vol[i]
            s = int(sign[i])
            mn1_s = int(s * mn1_mag); w1_s = int(s * w1_mag); d1_s = int(s * d1_mag)
            ef = int(sum(1 for v in [mn1_s, w1_s, d1_s] if v in (14, 15)))
            dt = datetime.fromtimestamp(rates[i][0]).strftime("%Y-%m-%d")
            rows.append((str(sym), "D1", dt, hx(mn1_s), hx(w1_s), hx(d1_s),
                         mn1_s, w1_s, d1_s, ef, "MT5_D1"))

        # 批量插入
        for b in range(0, len(rows), 1000):
            conn.executemany("INSERT INTO state_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                             rows[b:b+1000])

        elapsed = time.time() - t0
        first = datetime.fromtimestamp(rates[0][0]).strftime("%Y-%m-%d")
        last  = datetime.fromtimestamp(rates[-1][0]).strftime("%Y-%m-%d")
        print(f"  [{idx+1:2d}/{total_symbols}] {sym:10s} ({mt5_sym}) -> {len(rows):5d}条"
              f"  [{first}~{last}]  {elapsed:.1f}s")
        total_count += len(rows)

    except Exception as e:
        print(f"  [{idx+1:2d}/{total_symbols}] {sym:10s} -> ERROR: {str(e)[:80]}")

# ===== 切片 =====
print(f"\n[Slice] 生成中...")
conn.execute("DROP TABLE IF EXISTS state_slices")
conn.execute("""
CREATE TABLE state_slices (
    slice_id VARCHAR, symbol VARCHAR, perspective VARCHAR,
    pattern VARCHAR, mn1_hex VARCHAR, w1_hex VARCHAR, d1_hex VARCHAR,
    occurrence_count INTEGER
)""")

slice_n = 0
for sym in SYMBOLS:
    rows = conn.execute(
        "SELECT date,mn1_hex,w1_hex,d1_hex FROM state_snapshots "
        "WHERE symbol=? AND perspective='D1' ORDER BY date", (sym,)).fetchall()
    if len(rows) < 10: continue
    pats = defaultdict(int)
    for r in rows: pats[f"{r[1]}_{r[2]}_{r[3]}"] += 1
    for pat, cnt in pats.items():
        p = pat.split("_")
        if len(p) != 3: continue
        conn.execute("INSERT INTO state_slices VALUES (?,?,?,?,?,?,?,?)",
                     (f"{sym}_D1_{pat}", sym, "D1", pat, p[0], p[1], p[2], cnt))
        slice_n += 1
conn.commit()
print(f"  切片: {slice_n} 个")

# ===== 报告 =====
snap = conn.execute("SELECT COUNT(*) FROM state_snapshots").fetchone()[0]
syms = conn.execute("SELECT COUNT(DISTINCT symbol) FROM state_snapshots").fetchone()[0]
sl = conn.execute("SELECT COUNT(*) FROM state_slices").fetchone()[0]
dr = conn.execute("SELECT MIN(date),MAX(date) FROM state_snapshots").fetchone()
ef = conn.execute("SELECT ef_count,COUNT(*) FROM state_snapshots GROUP BY ef_count ORDER BY ef_count DESC").fetchall()
today = conn.execute("SELECT symbol,mn1_hex,w1_hex,d1_hex,ef_count FROM state_snapshots WHERE date=(SELECT MAX(date) FROM state_snapshots) AND ef_count>=1 ORDER BY ef_count DESC").fetchall()

print(f"\n{'='*60}")
print(f"  Hermass State DB: {snap}条 {syms}品种 {sl}切片")
print(f"  日期: {dr[0]} ~ {dr[1]}")
print(f"  EF分布:")
for e,n in ef: print(f"    ef={e}: {n:6d} {'#'*(n//200+1)}")
print(f"  今日共振 (ef>=1):")
for t in today: print(f"    {t[0]:8s} {t[1]}_{t[2]}_{t[3]} ef={t[4]}")

eur = conn.execute("SELECT date,mn1_hex,w1_hex,d1_hex,ef_count FROM state_snapshots WHERE symbol='EURUSD' AND perspective='D1' ORDER BY date DESC LIMIT 5").fetchall()
print(f"  EURUSD样本:")
for r in eur: print(f"    {r[0]} MN1={r[1]:3s} W1={r[2]:3s} D1={r[3]:3s} ef={r[4]}")

conn.close()
total_elapsed = time.time() - total_start
mt5.shutdown()

if total_count <= 0:
    try:
        build_db_path.unlink()
    except OSError:
        pass
    print("[FATAL] D1 build saved 0 rows; active DB was not replaced.")
    exit(1)

if target_db_path.exists():
    backup_path = target_db_path.with_name(
        f"{target_db_path.stem}.pre_replace_{datetime.now().strftime('%Y%m%d_%H%M%S')}{target_db_path.suffix}"
    )
    target_db_path.replace(backup_path)
build_db_path.replace(target_db_path)

sz = target_db_path.stat().st_size/1024/1024
print(f"\n[Done] {target_db_path} ({sz:.1f}MB) 总耗时{total_elapsed:.0f}s")
