"""
State数据库构建 v3 - 健壮版
支持断点续建，逐个品种处理
"""
import MetaTrader5 as mt5
import sqlite3
import numpy as np
from datetime import datetime
from pathlib import Path
import time

# 初始化MT5
print("正在连接MT5...")
if not mt5.initialize():
    print("MT5初始化失败")
    exit(1)

print(f"MT5已连接")

SYMBOLS = [
    "EURUSD","GBPUSD","USDJPY","AUDUSD","NZDUSD","USDCAD","USDCHF",
    "EURJPY","GBPJPY","AUDJPY","EURGBP","EURCHF","EURCAD","GBPCHF",
    "BTCUSD","ETHUSD","XRPUSD",
]

DB_PATH = Path("data/state_db.sqlite")
DB_PATH.parent.mkdir(exist_ok=True)

# 连接数据库（保留已有数据）
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 检查表是否存在
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='state_snapshots'")
if not c.fetchone():
    c.execute('''CREATE TABLE state_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, perspective TEXT, timestamp TEXT,
        state_hex TEXT, state_desc TEXT,
        ef_count INTEGER, bits TEXT,
        source TEXT, created_at TEXT
    )''')
    conn.commit()
    print("创建新数据库")
else:
    # 检查已完成的品种
    c.execute("SELECT DISTINCT symbol FROM state_snapshots")
    done = set(row[0] for row in c.fetchall())
    print(f"已有数据，已完成: {len(done)} 个品种")
    SYMBOLS = [s for s in SYMBOLS if s not in done]

def calc_state(closes):
    """简化State计算"""
    if len(closes) < 21:
        return "C=L", 0
    
    # 布林带位置
    sma = np.mean(closes[-20:])
    std = np.std(closes[-20:])
    price = closes[-1]
    
    if std == 0:
        pos = "C"
    elif price > sma + 2*std:
        pos = "A"
    elif price > sma + 0.5*std:
        pos = "B"
    elif price > sma - 0.5*std:
        pos = "C"
    elif price > sma - 2*std:
        pos = "D"
    else:
        pos = "E"
    
    # 趋势
    if len(closes) >= 35:
        ema_fast = np.mean(closes[-10:])
        ema_slow = np.mean(closes[-30:])
        if ema_fast > ema_slow * 1.001:
            trend = "+"
        elif ema_fast < ema_slow * 0.999:
            trend = "-"
        else:
            trend = "="
    else:
        trend = "="
    
    # 波动率
    if len(closes) >= 16:
        recent = closes[-16:]
        returns = np.diff(recent) / recent[:-1]
        vol = np.std(returns)
        if vol > 0.015:
            vol_state = "H"
        elif vol > 0.008:
            vol_state = "M"
        else:
            vol_state = "L"
    else:
        vol_state = "L"
    
    state = f"{pos}{trend}{vol_state}"
    
    # EF计数
    ef = 0
    if pos in ["D", "E"] and trend == "-":
        ef += 1
    if pos in ["A", "B"] and trend == "+":
        ef += 1
    if vol_state == "H":
        ef += 1
    
    return state, ef

# 主循环
print(f"\n待处理品种: {len(SYMBOLS)}")
total = 0

for idx, symbol in enumerate(SYMBOLS, 1):
    print(f"\n[{idx}/{len(SYMBOLS)}] 处理 {symbol}...")
    
    try:
        # 获取数据（带重试）
        for attempt in range(3):
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 99999)
            if rates is not None and len(rates) > 0:
                break
            time.sleep(2)
        
        if rates is None or len(rates) == 0:
            print(f"  ⚠️ 无数据，跳过")
            continue
        
        closes = rates['close']
        times = rates['time']
        print(f"  历史: {len(rates)} 根 ({datetime.fromtimestamp(times[0]).date()} ~ {datetime.fromtimestamp(times[-1]).date()})")
        
        # 生成State（每5天采样）
        count = 0
        batch = []
        for i in range(200, len(rates), 5):
            window = closes[:i+1]
            state, ef = calc_state(window)
            dt = datetime.fromtimestamp(times[i]).strftime('%Y-%m-%d')
            
            batch.append((symbol, "D1", dt, state, state, ef, state, "MT5", datetime.now().isoformat()))
            
            if len(batch) >= 100:
                c.executemany('''INSERT INTO state_snapshots 
                    (symbol, perspective, timestamp, state_hex, state_desc, 
                     ef_count, bits, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', batch)
                conn.commit()
                batch = []
            
            count += 1
        
        # 剩余批次
        if batch:
            c.executemany('''INSERT INTO state_snapshots 
                (symbol, perspective, timestamp, state_hex, state_desc, 
                 ef_count, bits, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', batch)
            conn.commit()
        
        print(f"  ✅ 生成 {count} 个快照")
        total += count
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        continue

# 统计
print("\n" + "="*50)
print("构建完成!")
print("="*50)

c.execute("SELECT COUNT(*) FROM state_snapshots")
snapshots = c.fetchone()[0]

c.execute("SELECT COUNT(DISTINCT symbol) FROM state_snapshots")
symbols = c.fetchone()[0]

print(f"总快照: {snapshots}")
print(f"品种: {symbols}")

# EF分布
c.execute("SELECT ef_count, COUNT(*) FROM state_snapshots GROUP BY ef_count")
print("\nEF分布:")
for ef, count in c.fetchall():
    print(f"  EF={ef}: {count} ({count/snapshots*100:.1f}%)")

conn.close()
mt5.shutdown()

print(f"\n数据库: {DB_PATH} ({DB_PATH.stat().st_size / 1024:.1f} KB)")
