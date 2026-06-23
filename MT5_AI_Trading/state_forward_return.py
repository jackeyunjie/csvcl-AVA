"""
state_forward_return.py — Hermass State × MT5价格 = 向前收益率
=============================================================
从MT5拉14个外汇品种的D1收盘价 → JOIN hermass_state → 算5/10/20日收益率
输出: 每种State模式的历史胜率和均收益
"""
import MetaTrader5 as mt5
import duckdb, numpy as np, sys, io
from datetime import datetime
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SYMBOLS = [
    "EURUSD","GBPUSD","USDJPY","AUDUSD","NZDUSD","USDCAD","USDCHF",
    "EURJPY","GBPJPY","AUDJPY","EURGBP","EURCHF","EURCAD","GBPCHF",
]

print("=" * 65)
print("  Hermass State × MT5价格 = 向前收益率")
print("=" * 65)

if not mt5.initialize():
    print("[FATAL] MT5未运行"); exit(1)

# Step 1: 从MT5拉价格 + 存入DuckDB
db = duckdb.connect("data/hermass_state.db")
db.execute("DROP TABLE IF EXISTS daily_prices")
db.execute("CREATE TABLE daily_prices (symbol VARCHAR, date DATE, close DOUBLE)")

price_total = 0
for sym in SYMBOLS:
    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_D1, 0, 5000)
    if rates is None or len(rates) < 50:
        continue
    rows = [(sym, datetime.fromtimestamp(r[0]).strftime("%Y-%m-%d"), float(r[4]))
            for r in rates]
    for b in range(0, len(rows), 1000):
        db.executemany("INSERT INTO daily_prices VALUES (?,?,?)", rows[b:b+1000])
    price_total += len(rows)

print(f"\n[Price] {price_total} 条 ({len(SYMBOLS)}品种)")

# Step 2: JOIN → 向前收益率
print("\n[Forward Returns] 计算中...")

# 预计算各品种的forward returns
db.execute("DROP TABLE IF EXISTS forward_returns")
db.execute("""
    CREATE TABLE forward_returns AS
    WITH prices AS (
        SELECT symbol, date, close,
               LEAD(close, 5)  OVER w as fwd_5,
               LEAD(close, 10) OVER w as fwd_10,
               LEAD(close, 20) OVER w as fwd_20
        FROM daily_prices
        WINDOW w AS (PARTITION BY symbol ORDER BY date)
    )
    SELECT p.*,
           (fwd_5  - close) / close * 100 as ret_5d_pct,
           (fwd_10 - close) / close * 100 as ret_10d_pct,
           (fwd_20 - close) / close * 100 as ret_20d_pct
    FROM prices p
""")

# Step 3: State × Forward Returns
print("\n" + "-" * 50)
print("  [EF=2信号] 向前收益率统计")

ef2 = db.execute("""
    SELECT
        COUNT(*) as n,
        ROUND(AVG(ret_5d_pct), 3) as avg_5d,
        ROUND(AVG(CASE WHEN ret_5d_pct > 0 THEN 1 ELSE 0 END) * 100, 1) as wr_5d,
        ROUND(AVG(ret_10d_pct), 3) as avg_10d,
        ROUND(AVG(CASE WHEN ret_10d_pct > 0 THEN 1 ELSE 0 END) * 100, 1) as wr_10d,
        ROUND(AVG(ret_20d_pct), 3) as avg_20d,
        ROUND(AVG(CASE WHEN ret_20d_pct > 0 THEN 1 ELSE 0 END) * 100, 1) as wr_20d
    FROM state_snapshots s
    JOIN forward_returns f
        ON s.symbol = f.symbol AND s.date = f.date
    WHERE s.ef_count = 2 AND s.perspective = 'D1'
      AND f.ret_5d_pct IS NOT NULL
""").fetchone()

print(f"  EF=2 信号: {ef2[0]}次")
print(f"    5日: 均收益={ef2[1]:+.2f}%  胜率={ef2[2]}%")
print(f"   10日: 均收益={ef2[3]:+.2f}%  胜率={ef2[4]}%")
print(f"   20日: 均收益={ef2[5]:+.2f}%  胜率={ef2[6]}%")

# Step 4: EF=1 vs EF=0 对照组
print("\n" + "-" * 50)
print("  [对照组] EF=1 vs EF=0")

for ef_val in [1, 0]:
    r = db.execute(f"""
        SELECT COUNT(*),
               ROUND(AVG(ret_5d_pct), 3),
               ROUND(AVG(CASE WHEN ret_5d_pct>0 THEN 1 ELSE 0 END)*100,1)
        FROM state_snapshots s
        JOIN forward_returns f ON s.symbol=f.symbol AND s.date=f.date
        WHERE s.ef_count={ef_val} AND s.perspective='D1' AND f.ret_5d_pct IS NOT NULL
    """).fetchone()
    print(f"  EF={ef_val}: {r[0]:5d}次  5日均收益={r[1]:+.2f}%  胜率={r[2]}%")

# Step 5: 规则1 — MN1=2, W1=A, D1=E/F 
print("\n" + "-" * 50)
print("  [规则1] MN1=2 + W1=A + D1=E/F")

rule1 = db.execute("""
    SELECT
        COUNT(*) n,
        ROUND(AVG(f.ret_5d_pct), 3) avg_5d,
        ROUND(AVG(CASE WHEN f.ret_5d_pct>0 THEN 1 ELSE 0 END)*100,1) wr_5d,
        ROUND(AVG(f.ret_10d_pct), 3) avg_10d,
        ROUND(AVG(f.ret_20d_pct), 3) avg_20d,
        ROUND(AVG(CASE WHEN f.ret_20d_pct>0 THEN 1 ELSE 0 END)*100,1) wr_20d
    FROM state_snapshots s
    JOIN forward_returns f ON s.symbol=f.symbol AND s.date=f.date
    WHERE s.mn1_score=2 AND s.w1_score=10 AND s.d1_score IN (14,15)
      AND s.perspective='D1' AND f.ret_5d_pct IS NOT NULL
""").fetchone()

print(f"  信号次数: {rule1[0]}")
print(f"  5日均收益: {rule1[1]:+.2f}%  胜率: {rule1[2]}%")
print(f"  10日均收益: {rule1[3]:+.2f}%")
print(f"  20日均收益: {rule1[4]:+.2f}%  胜率: {rule1[5]}%")

# Step 6: 规则2 — MN1=2 + W1=2 + D1=E
print("\n" + "-" * 50)
print("  [规则2] MN1=2 + W1=2 + D1=E")

rule2 = db.execute("""
    SELECT
        COUNT(*) n,
        ROUND(AVG(f.ret_5d_pct), 3) avg_5d,
        ROUND(AVG(CASE WHEN f.ret_5d_pct>0 THEN 1 ELSE 0 END)*100,1) wr_5d,
        ROUND(AVG(f.ret_10d_pct), 3) avg_10d,
        ROUND(AVG(f.ret_20d_pct), 3) avg_20d
    FROM state_snapshots s
    JOIN forward_returns f ON s.symbol=f.symbol AND s.date=f.date
    WHERE s.mn1_score=2 AND s.w1_score=2 AND s.d1_score=14
      AND s.perspective='D1' AND f.ret_5d_pct IS NOT NULL
""").fetchone()

print(f"  信号次数: {rule2[0]}")
print(f"  5日均收益: {rule2[1]:+.2f}%  胜率: {rule2[2]}%")
print(f"  10日均收益: {rule2[3]:+.2f}%")
print(f"  20日均收益: {rule2[4]:+.2f}%")

# Step 7: 全State模式收益率排行 TOP15
print("\n" + "-" * 50)
print("  [TOP15高收益State模式] (n>=10)")

top = db.execute("""
    SELECT
        s.mn1_hex||'_'||s.w1_hex||'_'||s.d1_hex as pat,
        COUNT(*) n,
        ROUND(AVG(f.ret_5d_pct), 3) a5,
        ROUND(AVG(CASE WHEN f.ret_5d_pct>0 THEN 1 ELSE 0 END)*100,1) w5
    FROM state_snapshots s
    JOIN forward_returns f ON s.symbol=f.symbol AND s.date=f.date
    WHERE s.perspective='D1' AND f.ret_5d_pct IS NOT NULL
    GROUP BY pat HAVING COUNT(*) >= 10
    ORDER BY a5 DESC LIMIT 15
""").fetchall()

for r in top:
    print(f"  {r[0]:20s} N={r[1]:3d}  5均={r[2]:+6.2f}%  胜率={r[3]:5.1f}%")

# Step 8: 按品种EF=2胜率
print("\n" + "-" * 50)
print("  [分品种EF=2胜率] (n>=5)")

by_sym = db.execute("""
    SELECT s.symbol,
           COUNT(*) n,
           ROUND(AVG(f.ret_5d_pct), 3) a5,
           ROUND(AVG(CASE WHEN f.ret_5d_pct>0 THEN 1 ELSE 0 END)*100,1) w5,
           ROUND(AVG(f.ret_20d_pct), 3) a20
    FROM state_snapshots s
    JOIN forward_returns f ON s.symbol=f.symbol AND s.date=f.date
    WHERE s.ef_count=2 AND s.perspective='D1' AND f.ret_5d_pct IS NOT NULL
    GROUP BY s.symbol HAVING COUNT(*)>=5
    ORDER BY w5 DESC
""").fetchall()

for r in by_sym:
    print(f"  {r[0]:8s} EF=2x{r[1]:2d}  5胜={r[3]:5.1f}%  5均={r[2]:+6.2f}%  20均={r[4]:+6.2f}%")

db.close()
mt5.shutdown()
print(f"\n{'='*65}")
print("  [Done] 数据已写入 hermass_state.db (daily_prices + forward_returns)")
print(f"{'='*65}")
