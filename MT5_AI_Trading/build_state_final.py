"""
State数据库构建 - 最终简化版
"""
import MetaTrader5 as mt5
import sqlite3
import numpy as np
from datetime import datetime
from pathlib import Path

print("="*50)
print("State数据库构建")
print("="*50)

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

DB_PATH = Path("data/state_db.sqlite")
DB_PATH.parent.mkdir(exist_ok=True)
if DB_PATH.exists():
    DB_PATH.unlink()
    print("已删除旧数据库")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute('''CREATE TABLE state_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT, perspective TEXT, timestamp TEXT,
    state_hex TEXT, state_desc TEXT,
    ef_count INTEGER, bits TEXT,
    source TEXT, created_at TEXT
)''')
conn.commit()

def calc_state(closes):
    """计算State编码"""
    n = len(closes)
    if n < 35:
        return "C=L", 0
    
    # 布林带位置 (20周期)
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
    
    # 趋势 (10 vs 30 EMA)
    ema10 = np.mean(closes[-10:])
    ema30 = np.mean(closes[-30:])
    if ema10 > ema30 * 1.001:
        trend = "+"
    elif ema10 < ema30 * 0.999:
        trend = "-"
    else:
        trend = "="
    
    # 波动率 (15周期收益率标准差)
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
    
    # EF信号计数
    ef = 0
    if pos in ["D", "E"] and trend == "-":
        ef += 1
    if pos in ["A", "B"] and trend == "+":
        ef += 1
    if vol_state == "H":
        ef += 1
    
    return state, ef

# 处理每个品种
total = 0
for idx, symbol in enumerate(SYMBOLS, 1):
    print(f"[{idx:2d}/{len(SYMBOLS)}] {symbol}...", end=" ")
    
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 99999)
    if rates is None or len(rates) == 0:
        print("无数据")
        continue
    
    closes = rates['close']
    times = rates['time']
    n = len(rates)
    
    # 每5天采样一个State
    count = 0
    for i in range(200, n, 5):
        window = closes[:i+1]
        state, ef = calc_state(window)
        dt = datetime.fromtimestamp(times[i]).strftime('%Y-%m-%d')
        
        c.execute('''INSERT INTO state_snapshots 
            (symbol, perspective, timestamp, state_hex, state_desc, 
             ef_count, bits, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (symbol, "D1", dt, state, state, ef, state, "MT5", datetime.now().isoformat()))
        count += 1
    
    conn.commit()
    print(f"{count} 快照 ({n} 根K线)")
    total += count

# 统计
print("\n" + "="*50)
c.execute("SELECT COUNT(*) FROM state_snapshots")
snapshots = c.fetchone()[0]

c.execute("SELECT COUNT(DISTINCT symbol) FROM state_snapshots")
symbols = c.fetchone()[0]

print(f"总快照: {snapshots}")
print(f"品种数: {symbols}")

c.execute("SELECT ef_count, COUNT(*) FROM state_snapshots GROUP BY ef_count")
print("\nEF分布:")
for ef, count in c.fetchall():
    pct = count / snapshots * 100
    print(f"  EF={ef}: {count:6d} ({pct:5.1f}%)")

conn.close()
mt5.shutdown()

size_kb = DB_PATH.stat().st_size / 1024
print(f"\n数据库: {DB_PATH} ({size_kb:.1f} KB)")
print("="*50)
