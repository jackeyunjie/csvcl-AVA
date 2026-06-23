"""
State数据库构建 - DuckDB版本
优势:
- 比SQLite快10-100倍分析查询
- 原生支持Pandas DataFrame互操作
- 可以直接查询Parquet/CSV
- 适合量化分析的大数据集
"""
import duckdb
import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

print("="*60)
print("State数据库构建 - DuckDB版")
print("="*60)

# 初始化MT5
if not mt5.initialize():
    print("MT5初始化失败")
    exit(1)
print("MT5已连接\n")

SYMBOLS = [
    "EURUSD","GBPUSD","USDJPY","AUDUSD","NZDUSD","USDCAD","USDCHF",
    "EURJPY","GBPJPY","AUDJPY","EURGBP","EURCHF","EURCAD","GBPCHF",
    "BTCUSD","ETHUSD","XRPUSD",
]

DB_PATH = Path("data/state_duckdb.db")
DB_PATH.parent.mkdir(exist_ok=True)
if DB_PATH.exists():
    DB_PATH.unlink()
    print("已删除旧数据库")

# 创建DuckDB连接
conn = duckdb.connect(str(DB_PATH))

# 创建表
conn.execute('''
CREATE TABLE state_snapshots (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR,
    perspective VARCHAR,
    timestamp DATE,
    state_hex VARCHAR,
    state_desc VARCHAR,
    ef_count INTEGER,
    bits VARCHAR,
    source VARCHAR,
    created_at TIMESTAMP
)
''')

def calc_state(closes):
    """计算State编码"""
    n = len(closes)
    if n < 35:
        return "C=L", 0
    
    # 布林带位置
    sma20 = np.mean(closes[-20:])
    std20 = np.std(closes[-20:])
    price = closes[-1]
    
    if std20 == 0:
        pos = "C"
    elif price > sma20 + 2*std20:
        pos = "A"
    elif price > sma20 + 0.5*std20:
        pos = "B"
    elif price > sma20 - 0.5*std20:
        pos = "C"
    elif price > sma20 - 2*std20:
        pos = "D"
    else:
        pos = "E"
    
    # 趋势
    ema10 = np.mean(closes[-10:])
    ema30 = np.mean(closes[-30:])
    if ema10 > ema30 * 1.001:
        trend = "+"
    elif ema10 < ema30 * 0.999:
        trend = "-"
    else:
        trend = "="
    
    # 波动率
    recent = closes[-16:]
    changes = np.diff(recent) / recent[:-1]
    vol = np.std(changes)
    if vol > 0.015:
        vol_state = "H"
    elif vol > 0.008:
        vol_state = "M"
    else:
        vol_state = "L"
    
    state = f"{pos}{trend}{vol_state}"
    
    # EF信号
    ef = 0
    if pos in ["D", "E"] and trend == "-":
        ef += 1
    if pos in ["A", "B"] and trend == "+":
        ef += 1
    if vol_state == "H":
        ef += 1
    
    return state, ef

# 收集所有数据
all_data = []

for idx, symbol in enumerate(SYMBOLS, 1):
    print(f"[{idx:2d}/{len(SYMBOLS)}] {symbol}...", end=" ")
    
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 99999)
    if rates is None or len(rates) == 0:
        print("无数据")
        continue
    
    closes = rates['close']
    times = rates['time']
    n = len(rates)
    
    count = 0
    for i in range(200, n, 5):
        window = closes[:i+1]
        state, ef = calc_state(window)
        dt = datetime.fromtimestamp(times[i]).date()
        
        all_data.append({
            'symbol': symbol,
            'perspective': 'D1',
            'timestamp': dt,
            'state_hex': state,
            'state_desc': state,
            'ef_count': ef,
            'bits': state,
            'source': 'MT5',
            'created_at': datetime.now()
        })
        count += 1
    
    print(f"{count} 快照")

# 批量插入DuckDB
if all_data:
    df = pd.DataFrame(all_data)
    conn.register('df', df)
    conn.execute('INSERT INTO state_snapshots SELECT * FROM df')
    conn.commit()
    print(f"\n已插入 {len(all_data)} 条记录")

# 分析查询
print("\n" + "="*60)
print("DuckDB分析查询示例")
print("="*60)

# 1. 基本统计
result = conn.execute('''
    SELECT 
        COUNT(*) as total,
        COUNT(DISTINCT symbol) as symbols,
        MIN(timestamp) as start_date,
        MAX(timestamp) as end_date
    FROM state_snapshots
''').fetchone()
print(f"\n总记录: {result[0]}")
print(f"品种数: {result[1]}")
print(f"日期范围: {result[2]} ~ {result[3]}")

# 2. EF分布 (DuckDB窗口函数)
print("\nEF分布:")
for row in conn.execute('''
    SELECT 
        ef_count,
        COUNT(*) as cnt,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct
    FROM state_snapshots
    GROUP BY ef_count
    ORDER BY ef_count
''').fetchall():
    print(f"  EF={row[0]}: {row[1]} ({row[2]}%)")

# 3. 各品种State统计
print("\n各品种快照数:")
for row in conn.execute('''
    SELECT symbol, COUNT(*) as cnt
    FROM state_snapshots
    GROUP BY symbol
    ORDER BY cnt DESC
''').fetchall():
    print(f"  {row[0]}: {row[1]}")

# 4. 高EF信号历史 (DuckDB快速过滤)
print("\n高EF信号 (ef>=2) 最近10条:")
for row in conn.execute('''
    SELECT timestamp, symbol, state_hex, ef_count
    FROM state_snapshots
    WHERE ef_count >= 2
    ORDER BY timestamp DESC
    LIMIT 10
''').fetchall():
    print(f"  {row[0]} {row[1]} {row[2]} EF={row[3]}")

# 5. State转换分析 (DuckDB LAG窗口函数)
print("\nEURUSD State转换频率:")
for row in conn.execute('''
    SELECT 
        state_hex,
        COUNT(*) as freq,
        ROUND(AVG(ef_count), 2) as avg_ef
    FROM state_snapshots
    WHERE symbol = 'EURUSD'
    GROUP BY state_hex
    ORDER BY freq DESC
    LIMIT 10
''').fetchall():
    print(f"  {row[0]}: {row[1]}次 (平均EF={row[2]})")

# 导出为Parquet (DuckDB原生支持)
parquet_path = Path("data/state_snapshots.parquet")
conn.execute(f"COPY state_snapshots TO '{parquet_path}' (FORMAT PARQUET)")
print(f"\n已导出Parquet: {parquet_path} ({parquet_path.stat().st_size / 1024:.1f} KB)")

# 关闭连接
conn.close()
mt5.shutdown()

print("\n" + "="*60)
print("DuckDB数据库构建完成!")
print(f"数据库: {DB_PATH} ({DB_PATH.stat().st_size / 1024:.1f} KB)")
print("="*60)
