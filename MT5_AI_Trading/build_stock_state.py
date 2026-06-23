"""build_stock_state.py v3 — full State + stock-specific metrics"""
import MetaTrader5 as mt5, duckdb, numpy as np, sys, io, time
from datetime import datetime
from collections import defaultdict
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')

STOCK_SYMBOLS = [
    "#AMAZON","#MICROSOFT","#NVIDIA","#META","#TESLA",
    "#GOOGLE","#AMD","#INTEL","#NETFLIX","#ADOBE","#ALIBABA",
    "#WELLSFARGO","#CITIGROUP","#PFIZER","#MERCK","#ABBVIE",
    "#COSTCO","#HOMEDEPOT","#NIKE","#STARBUCKS","#MCDONALDS",
    "#PEPSICO","#EXXONMOBIL","#CHEVRON","#CONOCOPHILLIPS",
    "#BOEING","#CATERPILLAR","#GENERALELECTRIC","#HONEYWELL",
    "#AT&T","#VERIZON","#COMCAST",
    "#VISA","#MASTERCARD","#SALESFORCE",
    "#UBER","#AIRBNB","#SNAP","#PALANTIR",
]
MAX_BARS = 500

BB_P,BB_D,BB_PW,BB_Q=20,2.0,20,0.20
ATR_P,ADX_P,ADX_S=14,14,3
K,LAG=5,3
SCALE={"MN1":22,"W1":5,"D1":1}

def hx(s):a=abs(s);h=hex(a)[2:].upper();return f"-{h}"if s<0 else h
def calc_tr(h,l,c):
    n=len(c);tr=np.zeros(n);tr[0]=h[0]-l[0]
    for i in range(1,n):tr[i]=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1]))
    return tr
def calc_adx_vec(tr,h,l,period,sw):
    n=len(tr)
    if n<period+sw+3:return np.zeros(n,dtype=int)
    pdm=np.zeros(n);mdm=np.zeros(n)
    for i in range(1,n):up=h[i]-h[i-1];dn=l[i-1]-l[i];pdm[i]=up if up>dn and up>0 else 0;mdm[i]=dn if dn>up and dn>0 else 0
    ar=np.convolve(tr,np.ones(period),mode='valid')/period
    pr=np.convolve(pdm,np.ones(period),mode='valid')/period
    mr=np.convolve(mdm,np.ones(period),mode='valid')/period
    nv=len(ar);dx=np.zeros(nv)
    for i in range(nv):
        if ar[i]>0:p=pr[i]/ar[i]*100;m=mr[i]/ar[i]*100;dx[i]=abs(p-m)/(p+m)*100 if(p+m)>0 else 0
    adx=np.zeros(nv)
    if nv>0:adx[0]=dx[0]
    for i in range(1,nv):adx[i]=(adx[i-1]*(period-1)+dx[i])/period
    result=np.zeros(n,dtype=int);off=n-nv
    for i in range(off+sw,n):
        idx=i-off
        if idx>=sw and idx<nv:c1=adx[idx];c2=adx[idx-sw]
        if c1>=25 and c1>c2:result[i]=1
        elif c1>20:result[i]=1
        elif c1<=13 and c1<c2:result[i]=0
    return result
def calc_base_vec(c,period,pw):
    n=len(c)
    if n<period+pw:return np.zeros(n,dtype=int)
    nm=n-period+1;bbw=np.zeros(nm)
    for i in range(nm):seg=c[i:i+period];m=np.mean(seg);s=np.std(seg,ddof=0);bbw[i]=(m+BB_D*s-(m-BB_D*s))/m if m>0 else 0
    result=np.zeros(n,dtype=int)
    for i in range(period+pw-1,n):hist=bbw[i-period-pw+1:i-period+1];cur=bbw[i-period];q=np.percentile(hist,BB_Q*100);result[i]=0 if cur<q else 8
    return result

print("="*65)
print("  Stock State DB v3")
print("="*65)
if not mt5.initialize(): print("[FATAL]");exit(1)

db=duckdb.connect("data/stock_state.db")
db.execute("DROP TABLE IF EXISTS state_snapshots")
db.execute("""CREATE TABLE state_snapshots (symbol VARCHAR,perspective VARCHAR,date DATE,mn1_hex VARCHAR,w1_hex VARCHAR,d1_hex VARCHAR,mn1_score INT,w1_score INT,d1_score INT,ef_count INT,sector VARCHAR)""")

total=0
for idx,sym in enumerate(STOCK_SYMBOLS):
    rates=mt5.copy_rates_from_pos(sym,mt5.TIMEFRAME_D1,0,MAX_BARS)
    if rates is None or len(rates)<100: continue
    h=np.array([r[2] for r in rates]);l=np.array([r[3] for r in rates]);c=np.array([r[4] for r in rates])
    tr=calc_tr(h,l,c)
    db_c=calc_base_vec(c,BB_P*SCALE["D1"],BB_PW)
    dt_c=calc_adx_vec(tr,h,l,ADX_P*SCALE["D1"],ADX_S*SCALE["D1"])
    rows=[]
    for i in range(50,len(c)):
        mag=db_c[i]+dt_c[i]*4
        sgn=1 if i<20 or c[i]>c[i-20] else -1
        ds=int(sgn*mag)
        ef=1 if ds in(14,15)else 0
        dt=datetime.fromtimestamp(rates[i][0]).strftime("%Y-%m-%d")
        rows.append((sym,"D1",dt,"","",hx(ds),0,0,ds,ef,"stock"))
    db.executemany("INSERT INTO state_snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?)",rows)
    total+=len(rows)
    if idx<3 or (idx+1)%8==0:print(f"  [{idx+1:2d}] {sym:25s} {len(rows):4d}")

# Slice
db.execute("DROP TABLE IF EXISTS state_slices")
db.execute("CREATE TABLE state_slices (slice_id TEXT,symbol TEXT,perspective TEXT,pattern TEXT,mn1_hex TEXT,w1_hex TEXT,d1_hex TEXT,occurrence_count INT)")
slice_n=0
for sym in STOCK_SYMBOLS:
    rs=db.execute("SELECT date,mn1_hex,w1_hex,d1_hex FROM state_snapshots WHERE symbol=? ORDER BY date",(sym,)).fetchall()
    if len(rs)<10:continue
    pats=defaultdict(int)
    for r in rs:pats[f"{r[1]}_{r[2]}_{r[3]}"]+=1
    for pat,cnt in pats.items():
        p=pat.split("_")
        if len(p)!=3:continue
        db.execute("INSERT INTO state_slices VALUES(?,?,?,?,?,?,?,?)",(f"{sym}_D1_{pat}",sym,"D1",pat,p[0],p[1],p[2],cnt))
        slice_n+=1

snap=db.execute("SELECT COUNT(*) FROM state_snapshots").fetchone()[0]
syms=db.execute("SELECT COUNT(DISTINCT symbol) FROM state_snapshots").fetchone()[0]
slc=db.execute("SELECT COUNT(*) FROM state_slices").fetchone()[0]
ef=db.execute("SELECT ef_count,COUNT(*),ROUND(COUNT(*)*100.0/MAX(1,SUM(COUNT(*))OVER()),1) FROM state_snapshots GROUP BY ef_count ORDER BY ef_count DESC").fetchall()

print(f"\nStock State: {snap}条 {syms}品种 {slc}切片")
print("EF分布(STD):")
for e,n,p in ef:print(f"  EF={e}: {n:4d} ({p}%)")
# Stock signal: abs(score)>=12
sig=db.execute("SELECT CASE WHEN abs(d1_score)>=12 THEN '>=12' ELSE '<12' END grp,COUNT(*),ROUND(COUNT(*)*100.0/MAX(1,SUM(COUNT(*))OVER()),1) FROM state_snapshots GROUP BY grp").fetchall()
print("Stock信号 (|score|>=12):")
for g,n,p in sig:print(f"  {g}: {n} ({p}%)")
# By stock
top=db.execute("SELECT symbol,COUNT(*) n,ROUND(AVG(abs(d1_score*1.0)),1) avg_score,ROUND(AVG(CASE WHEN abs(d1_score)>=12 THEN 1 ELSE 0 END)*100,1) sig_pct FROM state_snapshots GROUP BY symbol ORDER BY sig_pct DESC LIMIT 12").fetchall()
print("高信号占比Top12:")
for r in top:print(f"  {r[0]:25s} N={r[1]:3d} avg=|{r[2]}| sig={r[3]}%")

# Slice patterns  
top_pat=db.execute("SELECT pattern,SUM(occurrence_count)n FROM state_slices GROUP BY pattern ORDER BY n DESC LIMIT 10").fetchall()
print("\nTop10 D1模式:")
for r in top_pat:print(f"  {r[0]:20s} x{r[1]:4d}")

db.close()
import os
print(f"\nDone: {os.path.getsize('data/stock_state.db')/1024:.0f}KB")
