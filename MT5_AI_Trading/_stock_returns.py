"""Add prices + forward returns to stock_state.db"""
import MetaTrader5 as mt5, duckdb
from datetime import datetime

SYMS = ['#ABBVIE','#ADOBE','#ALIBABA','#AMAZON','#AMD','#AT&T','#BOEING','#CHEVRON','#CITIGROUP','#CONOCOPHILLIPS','#COSTCO','#EXXONMOBIL','#GOOGLE','#HOMEDEPOT','#HONEYWELL','#INTEL','#MCDONALDS','#MERCK','#META','#MICROSOFT','#NETFLIX','#NIKE','#NVIDIA','#PEPSICO','#PFIZER','#STARBUCKS','#TESLA','#VERIZON','#WELLSFARGO']

mt5.initialize()
db=duckdb.connect("data/stock_state.db")
db.execute("DROP TABLE IF EXISTS daily_prices")
db.execute("CREATE TABLE daily_prices (symbol TEXT, date TEXT, close DOUBLE)")

total=0
for sym in SYMS:
    r=mt5.copy_rates_from_pos(sym,mt5.TIMEFRAME_D1,0,1000)
    if r is None:continue
    rows=[(sym,datetime.fromtimestamp(x[0]).strftime("%Y-%m-%d"),float(x[4])) for x in r]
    db.executemany("INSERT INTO daily_prices VALUES(?,?,?)",rows)
    total+=len(rows)

db.execute("DROP TABLE IF EXISTS fwd")
db.execute("""CREATE TABLE fwd AS SELECT symbol,date,close,LEAD(close,5)OVER(PARTITION BY symbol ORDER BY date)f5,LEAD(close,20)OVER(PARTITION BY symbol ORDER BY date)f20 FROM daily_prices""")
db.execute("ALTER TABLE fwd ADD COLUMN r5 DOUBLE")
db.execute("ALTER TABLE fwd ADD COLUMN r20 DOUBLE")
db.execute("UPDATE fwd SET r5=(f5-close)/close*100, r20=(f20-close)/close*100")

print("Price:",total)

# Stock signal analysis
for label,cond in [
    ("|score|>=12","abs(d1_score)>=12"),
    ("score>=12","d1_score>=12"),
    ("score<=-12","d1_score<=-12"),
    ("score>=8","d1_score>=8"),
]:
    r=db.execute(f"SELECT COUNT(*),AVG(f.r5),AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END),AVG(f.r20),AVG(CASE WHEN f.r20>0 THEN 1 ELSE 0 END) FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date WHERE s.perspective='D1' AND ({cond}) AND f.r5 IS NOT NULL").fetchone()
    print(f"\n{label}: N={r[0]} 5d={r[1]:+.3f}% WR5={r[2]*100:.0f}% 20d={r[3]:+.3f}% WR20={r[4]*100:.0f}%")

# By stock
for sym in SYMS[:8]:
    r=db.execute(f"SELECT COUNT(*),AVG(f.r5),AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END) FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date WHERE s.symbol=? AND s.perspective='D1' AND abs(s.d1_score)>=12 AND f.r5 IS NOT NULL",(sym,)).fetchone()
    if r[0]>3:print(f"  {sym:25s} |s|>=12 x{r[0]:2d} WR5={r[2]*100:.0f}%")

db.close()
mt5.shutdown()
print("Done")
