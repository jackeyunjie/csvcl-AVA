"""
基本面数据收集 - yfinance + FRED
使用缓存避免重复请求，支持增量更新
"""
import duckdb
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
import json

print("="*70)
print("基本面数据收集")
print("="*70)

STOCKS = [
    "BABA", "GOOGL", "AMZN", "BA", "AMD", "AAPL", "MMM", "CLX",
    "KO", "DIS", "META", "GS", "FDX", "INTC", "JPM", "MA",
    "MCD", "MRK", "NFLX", "NKE", "PEP", "QCOM", "SBUX", "TSLA",
    "VZ", "ZM", "IBM", "MSFT", "XOM", "LMT"
]

DB_PATH = Path("data/fundamental_duckdb.db")
CACHE_PATH = Path("data/fundamental_cache.json")
DB_PATH.parent.mkdir(exist_ok=True)

conn = duckdb.connect(str(DB_PATH))

# 创建表
conn.execute('''
    CREATE TABLE IF NOT EXISTS equity_fundamentals (
        symbol VARCHAR, date DATE, pe_ratio DOUBLE, pb_ratio DOUBLE,
        ps_ratio DOUBLE, market_cap BIGINT, revenue_growth DOUBLE,
        earnings_growth DOUBLE, debt_to_equity DOUBLE, current_ratio DOUBLE,
        insider_buying DOUBLE, institutional_ownership DOUBLE, updated_at TIMESTAMP
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS macro_indicators (
        date DATE, us10y DOUBLE, us2y DOUBLE, cpi_yoy DOUBLE,
        core_pce DOUBLE, unemployment DOUBLE, initial_claims DOUBLE,
        vix DOUBLE, updated_at TIMESTAMP
    )
''')

# =====================================================================
# 1. 收集个股基本面 (逐个，带重试)
# =====================================================================
print("\n[1/2] 收集个股基本面...")

fundamentals_data = []
cache = {}

# 加载缓存
if CACHE_PATH.exists():
    try:
        with open(CACHE_PATH, 'r') as f:
            cache = json.load(f)
        print(f"  加载缓存: {len(cache)} 条")
    except:
        cache = {}

for idx, symbol in enumerate(STOCKS, 1):
    # 检查缓存是否新鲜 (24小时内)
    if symbol in cache:
        cached_time = datetime.fromisoformat(cache[symbol].get('cached_at', '2000-01-01'))
        if (datetime.now() - cached_time).hours < 24:
            print(f"  [{idx:2d}/{len(STOCKS)}] {symbol}... CACHE")
            fundamentals_data.append(cache[symbol]['data'])
            continue
    
    try:
        print(f"  [{idx:2d}/{len(STOCKS)}] {symbol}...", end=" ")
        time.sleep(3)  # 避免限流
        
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        data = {
            'symbol': symbol,
            'date': datetime.now().date(),
            'pe_ratio': info.get('trailingPE'),
            'pb_ratio': info.get('priceToBook'),
            'ps_ratio': info.get('priceToSalesTrailing12Months'),
            'market_cap': info.get('marketCap'),
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth'),
            'debt_to_equity': info.get('debtToEquity'),
            'current_ratio': info.get('currentRatio'),
            'insider_buying': info.get('heldPercentInsiders'),
            'institutional_ownership': info.get('heldPercentInstitutions'),
            'updated_at': datetime.now()
        }
        
        fundamentals_data.append(data)
        cache[symbol] = {
            'cached_at': datetime.now().isoformat(),
            'data': data
        }
        print("OK")
        
    except Exception as e:
        print(f"SKIP")

# 保存缓存
with open(CACHE_PATH, 'w') as f:
    json.dump(cache, f, default=str)

# 插入数据
if fundamentals_data:
    df = pd.DataFrame(fundamentals_data)
    conn.register('fund', df)
    conn.execute('''
        INSERT INTO equity_fundamentals 
        SELECT symbol, date, pe_ratio, pb_ratio, ps_ratio, market_cap,
               revenue_growth, earnings_growth, debt_to_equity, current_ratio,
               insider_buying, institutional_ownership, updated_at
        FROM fund
    ''')
    conn.commit()
    print(f"\n  已插入 {len(fundamentals_data)} 条")

# =====================================================================
# 2. 宏观数据
# =====================================================================
print("\n[2/2] 收集宏观数据...")

macro = {'date': datetime.now().date(), 'core_pce': None, 'updated_at': datetime.now()}

# 尝试获取VIX和国债 (使用history避免info限流)
try:
    vix = yf.Ticker("^VIX").history(period="1d", auto_adjust=False)
    if not vix.empty:
        macro['vix'] = float(vix['Close'].iloc[-1])
        print(f"  VIX: {macro['vix']}")
except Exception as e:
    print(f"  VIX SKIP")

try:
    tnx = yf.Ticker("^TNX").history(period="1d", auto_adjust=False)
    if not tnx.empty:
        macro['us10y'] = float(tnx['Close'].iloc[-1])
        print(f"  US10Y: {macro['us10y']}")
except:
    print(f"  US10Y SKIP")

try:
    fvx = yf.Ticker("^FVX").history(period="1d", auto_adjust=False)
    if not fvx.empty:
        macro['us2y'] = float(fvx['Close'].iloc[-1])
        print(f"  US2Y: {macro['us2y']}")
except:
    print(f"  US2Y SKIP")

# FRED数据
try:
    from pandas_datareader import data as pdr
    
    cpi = pdr.get_data_fred('CPIAUCSL', start=datetime.now()-timedelta(days=400))
    if len(cpi) >= 13:
        macro['cpi_yoy'] = float((cpi.iloc[-1] / cpi.iloc[-13] - 1) * 100)
        print(f"  CPI YoY: {macro['cpi_yoy']:.2f}%")
except:
    print(f"  CPI SKIP")

try:
    un = pdr.get_data_fred('UNRATE', start=datetime.now()-timedelta(days=60))
    macro['unemployment'] = float(un.iloc[-1].iloc[0])
    print(f"  Unemployment: {macro['unemployment']}%")
except:
    print(f"  Unemployment SKIP")

try:
    ic = pdr.get_data_fred('ICSA', start=datetime.now()-timedelta(days=30))
    macro['initial_claims'] = float(ic.iloc[-1].iloc[0])
    print(f"  Initial Claims: {macro['initial_claims']}")
except:
    print(f"  Claims SKIP")

# 插入宏观数据
conn.execute('''
    INSERT INTO macro_indicators (date, us10y, us2y, cpi_yoy, core_pce, unemployment, initial_claims, vix, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (macro['date'], macro.get('us10y'), macro.get('us2y'), macro.get('cpi_yoy'),
      macro.get('core_pce'), macro.get('unemployment'), macro.get('initial_claims'),
      macro.get('vix'), macro['updated_at']))
conn.commit()
print("\n  已插入宏观数据")

# =====================================================================
# 验证
# =====================================================================
print("\n" + "="*70)
print("数据验证")
print("="*70)

fund_count = conn.execute("SELECT COUNT(*) FROM equity_fundamentals").fetchone()[0]
macro_count = conn.execute("SELECT COUNT(*) FROM macro_indicators").fetchone()[0]
print(f"\n  总记录: 基本面={fund_count}, 宏观={macro_count}")

if fund_count > 0:
    print("\n  基本面数据 (最近5条):")
    for row in conn.execute('''
        SELECT symbol, pe_ratio, pb_ratio, market_cap/1e9 
        FROM equity_fundamentals ORDER BY updated_at DESC LIMIT 5
    ''').fetchall():
        print(f"    {row[0]}: PE={row[1]}, PB={row[2]}, Cap=${row[3]:.1f}B" if row[3] else f"    {row[0]}: PE={row[1]}, PB={row[2]}")

if macro_count > 0:
    print("\n  宏观数据 (最近3条):")
    for row in conn.execute('''
        SELECT date, us10y, cpi_yoy, unemployment, vix 
        FROM macro_indicators ORDER BY date DESC LIMIT 3
    ''').fetchall():
        print(f"    {row[0]}: 10Y={row[1]}, CPI={row[2]}, Unemp={row[3]}, VIX={row[4]}")

conn.close()
print(f"\n{'='*70}")
print(f"已保存: {DB_PATH}")
print(f"缓存: {CACHE_PATH}")
print(f"{'='*70}")
