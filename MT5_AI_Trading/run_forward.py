import MetaTrader5 as mt5, duckdb, os
from datetime import datetime

SYMBOLS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","NZDUSD","USDCAD","USDCHF",
           "EURJPY","GBPJPY","AUDJPY","EURGBP","EURCHF","EURCAD","GBPCHF"]

out = open("forward_log.txt", "w", encoding="utf-8")
def p(s=""): out.write(str(s)+"\n"); out.flush()

try:
    p("="*65)
    p("  Hermass State x MT5 = Forward Returns")
    p("="*65)

    if not mt5.initialize():
        p("[FATAL] MT5 fail")
        exit(1)

    db = duckdb.connect("data/hermass_state.db")
    db.execute("DROP TABLE IF EXISTS daily_prices")
    db.execute("CREATE TABLE daily_prices (symbol TEXT, date TEXT, close DOUBLE)")

    price_total = 0
    for sym in SYMBOLS:
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_D1, 0, 5000)
        if rates is None or len(rates) < 50:
            continue
        rows = [(sym, datetime.fromtimestamp(r[0]).strftime("%Y-%m-%d"), float(r[4])) for r in rates]
        for b in range(0, len(rows), 1000):
            db.executemany("INSERT INTO daily_prices VALUES (?,?,?)", rows[b:b+1000])
        price_total += len(rows)

    p(f"[Price] {price_total} rows")

    db.execute("DROP TABLE IF EXISTS fwd")
    db.execute("""
        CREATE TABLE fwd AS
        SELECT symbol, date, close,
               LEAD(close, 5)  OVER (PARTITION BY symbol ORDER BY date) as f5,
               LEAD(close, 10) OVER (PARTITION BY symbol ORDER BY date) as f10,
               LEAD(close, 20) OVER (PARTITION BY symbol ORDER BY date) as f20
        FROM daily_prices
    """)
    db.execute("ALTER TABLE fwd ADD COLUMN r5 DOUBLE")
    db.execute("ALTER TABLE fwd ADD COLUMN r10 DOUBLE")
    db.execute("ALTER TABLE fwd ADD COLUMN r20 DOUBLE")
    db.execute("UPDATE fwd SET r5=(f5-close)/close*100, r10=(f10-close)/close*100, r20=(f20-close)/close*100")

    p("\n--- EF=2 Forward Returns ---")
    ef2 = db.execute("""
        SELECT COUNT(*),
               AVG(f.r5), AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END),
               AVG(f.r10), AVG(CASE WHEN f.r10>0 THEN 1 ELSE 0 END),
               AVG(f.r20), AVG(CASE WHEN f.r20>0 THEN 1 ELSE 0 END)
        FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
        WHERE s.ef_count=2 AND s.perspective='D1' AND f.r5 IS NOT NULL
    """).fetchone()

    if ef2 and ef2[0]:
        p(f"  EF=2: N={ef2[0]}  5d={ef2[1]:+.2f}% WR5={ef2[2]*100:.0f}%  10d={ef2[3]:+.2f}% WR10={ef2[4]*100:.0f}%  20d={ef2[5]:+.2f}% WR20={ef2[6]*100:.0f}%")
    else:
        p("  EF=2: 无数据")

    for e in [1, 0]:
        r = db.execute(f"""
            SELECT COUNT(*), AVG(f.r5), AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END)
            FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
            WHERE s.ef_count={e} AND s.perspective='D1' AND f.r5 IS NOT NULL
        """).fetchone()
        p(f"  EF={e}: N={r[0]}  5d={r[1]:+.2f}% WR={r[2]*100:.0f}%")

    p("\n--- Rule1: MN1=2+W1=A+D1=E/F ---")
    r1 = db.execute("""
        SELECT COUNT(*), AVG(f.r5), AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END),
               AVG(f.r10), AVG(f.r20), AVG(CASE WHEN f.r20>0 THEN 1 ELSE 0 END)
        FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
        WHERE s.mn1_score=2 AND s.w1_score=10 AND s.d1_score IN (14,15)
          AND s.perspective='D1' AND f.r5 IS NOT NULL
    """).fetchone()
    p(f"  Rule1: N={r1[0]}  5d={r1[1]:+.2f}% WR5={r1[2]*100:.0f}%  10d={r1[3]:+.2f}%  20d={r1[4]:+.2f}% WR20={r1[5]*100:.0f}%")

    p("\n--- Rule2: MN1=2+W1=2+D1=E ---")
    r2 = db.execute("""
        SELECT COUNT(*), AVG(f.r5), AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END),
               AVG(f.r10), AVG(f.r20)
        FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
        WHERE s.mn1_score=2 AND s.w1_score=2 AND s.d1_score=14
          AND s.perspective='D1' AND f.r5 IS NOT NULL
    """).fetchone()
    p(f"  Rule2: N={r2[0]}  5d={r2[1]:+.2f}% WR5={r2[2]*100:.0f}%  10d={r2[3]:+.2f}%  20d={r2[4]:+.2f}%")

    p("\n--- TOP10 Patterns (n>=10) ---")
    top = db.execute("""
        SELECT s.mn1_hex||'_'||s.w1_hex||'_'||s.d1_hex pat, COUNT(*) n,
               AVG(f.r5) a5, AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END) w5
        FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
        WHERE s.perspective='D1' AND f.r5 IS NOT NULL
        GROUP BY pat HAVING COUNT(*)>=10 ORDER BY a5 DESC LIMIT 10
    """).fetchall()
    for r in top: p(f"  {r[0]:20s} N={r[1]:3d}  5d={r[2]:+6.2f}%  WR={r[3]*100:5.0f}%")

    p("\n--- Per-symbol EF=2 ---")
    by = db.execute("""
        SELECT s.symbol, COUNT(*) n, AVG(f.r5) a5,
               AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END) w5
        FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
        WHERE s.ef_count=2 AND s.perspective='D1' AND f.r5 IS NOT NULL
        GROUP BY s.symbol HAVING COUNT(*)>=3 ORDER BY w5 DESC
    """).fetchall()
    for r in by: p(f"  {r[0]:8s} EF=2x{r[1]:2d}  WR5={r[3]*100:5.0f}%  5d={r[2]:+6.2f}%")

    db.close()
    mt5.shutdown()
    sz = os.path.getsize("data/hermass_state.db")/1024/1024
    p(f"\nDB: {sz:.1f}MB")
    p("[Done]")

except Exception as e:
    p(f"ERROR: {e}")
    import traceback
    p(traceback.format_exc())

out.close()
