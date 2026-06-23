"""
build_fundamental_db.py v2 — 反限流版
======================================
策略: yfinance批量下载价格 + 分批拉基本面 + FRED宏观
"""

import duckdb, yfinance as yf, pandas as pd, numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys, time, json
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path("data/fundamental_duckdb.db")
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

SYMBOLS = [
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","JPM","V","JNJ",
    "WMT","PG","XOM","BAC","INTC","AMD","NFLX","ADBE","CRM","PYPL",
    "BA","DIS","CAT","GE","WFC","GS","MS","CVX","T","VZ",
]

END_DATE = datetime.now().strftime("%Y-%m-%d")
START_DATE = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")

print("=" * 60)
print("  基本面数据库构建器 v2 (反限流)")
print("=" * 60)

DB_PATH.parent.mkdir(exist_ok=True)
if DB_PATH.exists(): DB_PATH.unlink()
conn = duckdb.connect(str(DB_PATH))

conn.execute("""
CREATE TABLE equity_fundamentals (
    symbol VARCHAR, date DATE, pe DOUBLE, pb DOUBLE, market_cap DOUBLE,
    sector VARCHAR, industry VARCHAR, PRIMARY KEY (symbol, date)
);
CREATE TABLE macro_indicators (
    date DATE PRIMARY KEY, vix DOUBLE, sp500 DOUBLE, us10y DOUBLE,
    us2y DOUBLE, yield_curve DOUBLE
);
CREATE TABLE daily_prices (
    symbol VARCHAR, date DATE, close DOUBLE, volume BIGINT,
    PRIMARY KEY (symbol, date)
);
""")

# ===== Step 1: 批量历史价格 (一次性下载30只=1个HTTP请求) =====
print(f"\n[Step 1] 批量历史价格 {len(SYMBOLS)}只...")
try:
    tickers = yf.Tickers(" ".join(SYMBOLS))
    hist = tickers.history(start=START_DATE, end=END_DATE, progress=False)
    if hist is not None and not hist.empty:
        for sym in SYMBOLS:
            if sym not in hist["Close"].columns:
                continue
            sym_close = hist["Close"][sym].dropna()
            sym_vol = hist["Volume"][sym].dropna()
            rows = [
                {"symbol": sym, "date": d.strftime("%Y-%m-%d"),
                 "close": float(sym_close[d]), "volume": int(sym_vol[d])}
                for d in sym_close.index
            ]
            if rows:
                df = pd.DataFrame(rows)
                conn.register("tmp", df)
                conn.execute("INSERT OR IGNORE INTO daily_prices SELECT * FROM tmp")
                conn.unregister("tmp")
        price_count = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
        print(f"  历史价格: {price_count} 行")
    else:
        print("  批量下载返回空")
except Exception as e:
    print(f"  批量下载失败: {e}")

# ===== Step 2: 基本面数据 (分批, 每批5只+间隔2秒) =====
print(f"\n[Step 2] 分批基本面 {len(SYMBOLS)}只...")
fund_count = 0
batch_size = 5
for batch_start in range(0, len(SYMBOLS), batch_size):
    batch = SYMBOLS[batch_start:batch_start + batch_size]
    for sym in batch:
        try:
            t = yf.Ticker(sym)
            info = t.info
            pe = info.get("trailingPE") or info.get("forwardPE")
            pb = info.get("priceToBook")
            mc = info.get("marketCap")
            sec = info.get("sector", "")
            ind = info.get("industry", "")
            if pe or pb or mc:
                conn.execute(
                    "INSERT OR REPLACE INTO equity_fundamentals VALUES (?,?,?,?,?,?,?)",
                    (sym, END_DATE, pe, pb, mc, sec, ind))
                fund_count += 1
            print(f"  {sym:6s} PE={pe} PB={pb}" + (" OK" if pe or pb else " 无数据"))
        except Exception as e:
            err = str(e)[:60]
            print(f"  {sym:6s} FAILED: {err}")
        time.sleep(1)
    if batch_start + batch_size < len(SYMBOLS):
        time.sleep(2)

print(f"  基本面: {fund_count} 只")

# ===== Step 3: 宏观数据 (VIX+SP500+10Y) =====
print(f"\n[Step 3] 宏观数据...")
try:
    macro = yf.download("^VIX ^GSPC ^TNX ^FVX", start=START_DATE, end=END_DATE, progress=False)
    macro_count = 0
    if macro is not None and not macro.empty:
        for idx in macro.index:
            vals = {}
            if "^VIX" in macro["Close"].columns:
                vals["vix"] = float(macro["Close"]["^VIX"][idx]) if not pd.isna(macro["Close"]["^VIX"][idx]) else None
            if "^GSPC" in macro["Close"].columns:
                vals["sp500"] = float(macro["Close"]["^GSPC"][idx]) if not pd.isna(macro["Close"]["^GSPC"][idx]) else None
            if "^TNX" in macro["Close"].columns:
                vals["us10y"] = float(macro["Close"]["^TNX"][idx]) if not pd.isna(macro["Close"]["^TNX"][idx]) else None
            if "^FVX" in macro["Close"].columns:
                vals["us2y"] = float(macro["Close"]["^FVX"][idx]) if not pd.isna(macro["Close"]["^FVX"][idx]) else None

            if vals:
                yc = None
                if vals.get("us10y") and vals.get("us2y"):
                    yc = vals["us10y"] - vals["us2y"]
                conn.execute(
                    "INSERT OR REPLACE INTO macro_indicators VALUES (?,?,?,?,?,?)",
                    (idx.strftime("%Y-%m-%d"), vals.get("vix"), vals.get("sp500"),
                     vals.get("us10y"), vals.get("us2y"), yc))
                macro_count += 1
        print(f"  宏观: {macro_count} 天")
    else:
        print("  宏观下载为空")
except Exception as e:
    print(f"  宏观失败: {e}")

# ===== 报告 =====
print("\n" + "=" * 60)
for tbl in ["daily_prices", "equity_fundamentals", "macro_indicators"]:
    cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"  {tbl}: {cnt} 条")

conn.close()
sz_mb = DB_PATH.stat().st_size / 1024 / 1024
print(f"\n[Done] {DB_PATH} ({sz_mb:.1f} MB)")
print("运行: python state_fundamental_fusion.py 查看分析结果")
