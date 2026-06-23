"""
State数据库构建 v2 - 简化版
直接拉取MT5历史数据，生成State快照
"""
import MetaTrader5 as mt5
import sqlite3
import json
import numpy as np
from datetime import datetime
from pathlib import Path

# 初始化MT5
if not mt5.initialize():
    print("MT5初始化失败")
    exit(1)

print(f"MT5已连接: {mt5.terminal_info().path}")

# 品种列表
SYMBOLS = [
    "EURUSD","GBPUSD","USDJPY","AUDUSD","NZDUSD","USDCAD","USDCHF",
    "EURJPY","GBPJPY","AUDJPY","EURGBP","EURCHF","EURCAD","GBPCHF",
    "BTCUSD","ETHUSD","XRPUSD",
]

PERSPECTIVES = ["MN1", "W1", "D1"]

# 创建数据库
DB_PATH = Path("data/state_db.sqlite")
DB_PATH.parent.mkdir(exist_ok=True)
if DB_PATH.exists():
    DB_PATH.unlink()

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 创建表
c.execute('''CREATE TABLE state_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT, perspective TEXT, timestamp TEXT,
    state_hex TEXT, state_desc TEXT,
    ef_count INTEGER, bits TEXT,
    source TEXT, created_at TEXT
)''')

c.execute('''CREATE TABLE symbols_registry (
    symbol TEXT PRIMARY KEY, name TEXT, category TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS state_slices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT, perspective TEXT,
    s1 TEXT, s2 TEXT, s3 TEXT,
    slice_hash TEXT, count INTEGER,
    ef_count INTEGER, avg_return REAL
)''')

conn.commit()

def calc_bb_position(closes, period=20):
    """计算布林带位置"""
    if len(closes) < period:
        return 0
    sma = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    if std == 0:
        return 0
    bb_upper = sma + 2 * std
    bb_lower = sma - 2 * std
    price = closes[-1]
    if price > bb_upper:
        return 2  # 上轨上方
    elif price > sma:
        return 1  # 中轨上方
    elif price > bb_lower:
        return -1  # 中轨下方
    else:
        return -2  # 下轨下方

def calc_trend(closes, period=14):
    """计算趋势方向"""
    if len(closes) < period + 1:
        return 0
    ema_now = np.mean(closes[-period:])
    ema_prev = np.mean(closes[-(period+1):-1])
    if ema_now > ema_prev * 1.001:
        return 1  # 上升
    elif ema_now < ema_prev * 0.999:
        return -1  # 下降
    return 0  # 横盘

def calc_volatility(closes, period=14):
    """计算波动率状态"""
    if len(closes) < period + 1:
        return 0
    recent = closes[-(period+1):]
    returns = np.diff(recent) / recent[:-1]
    vol = np.std(returns)
    if vol > 0.02:
        return 2  # 高波动
    elif vol > 0.01:
        return 1  # 中波动
    return 0  # 低波动

def build_state(closes):
    """构建State编码"""
    pos = calc_bb_position(closes)
    trend = calc_trend(closes)
    vol = calc_volatility(closes)
    
    # 编码: S1(位置) S2(趋势) S3(波动)
    pos_map = {2: "A", 1: "B", 0: "C", -1: "D", -2: "E"}
    trend_map = {1: "+", 0: "=", -1: "-"}
    vol_map = {2: "H", 1: "M", 0: "L"}
    
    s1 = pos_map.get(pos, "C")
    s2 = trend_map.get(trend, "=")
    s3 = vol_map.get(vol, "L")
    
    # EF计数 (E/F信号)
    ef = 0
    if s1 in ["D", "E"] and s2 == "-":
        ef += 1  # 空头信号
    if s1 in ["A", "B"] and s2 == "+":
        ef += 1  # 多头信号
    if s3 == "H":
        ef += 1  # 高波动确认
    
    return f"{s1}{s2}{s3}", ef

# 主循环
print("\n开始构建State数据库...")
total = 0

for symbol in SYMBOLS:
    print(f"\n处理 {symbol}...")
    
    # 获取D1历史数据
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 99999)
    if rates is None or len(rates) == 0:
        print(f"  跳过: 无数据")
        continue
    
    closes = rates['close']
    times = rates['time']
    
    print(f"  历史数据: {len(rates)} 根")
    
    # 注册品种
    c.execute("INSERT OR REPLACE INTO symbols_registry VALUES (?, ?, ?)",
              (symbol, symbol, "FOREX" if symbol not in ["BTCUSD", "ETHUSD", "XRPUSD"] else "CRYPTO"))
    
    # 为每个时间点生成State (每5天采样，避免数据过多)
    count = 0
    for i in range(200, len(rates), 5):  # 从第200根开始，每5天
        window = closes[:i+1]
        state, ef = build_state(window)
        dt = datetime.fromtimestamp(times[i]).strftime('%Y-%m-%d')
        
        c.execute('''INSERT INTO state_snapshots 
                     (symbol, perspective, timestamp, state_hex, state_desc, 
                      ef_count, bits, source, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (symbol, "D1", dt, state, state, ef, state, "MT5", 
                   datetime.now().isoformat()))
        count += 1
    
    print(f"  生成 {count} 个State快照")
    total += count
    conn.commit()

# 生成切片统计
print("\n生成State切片统计...")
c.execute('''INSERT INTO state_slices (symbol, perspective, s1, s2, s3, 
             slice_hash, count, ef_count, avg_return)
             SELECT symbol, perspective, 
                    substr(state_hex, 1, 1) as s1,
                    substr(state_hex, 2, 1) as s2,
                    substr(state_hex, 3, 1) as s3,
                    state_hex, COUNT(*), ef_count, 0
             FROM state_snapshots
             GROUP BY symbol, perspective, state_hex''')

conn.commit()

# 统计
print("\n" + "="*50)
print("State数据库构建完成!")
print("="*50)

c.execute("SELECT COUNT(*) FROM state_snapshots")
snapshots = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM state_slices")
slices = c.fetchone()[0]

c.execute("SELECT COUNT(DISTINCT symbol) FROM state_snapshots")
symbols = c.fetchone()[0]

print(f"总快照数: {snapshots}")
print(f"切片数: {slices}")
print(f"品种数: {symbols}")

# EF分布
c.execute("SELECT ef_count, COUNT(*) FROM state_snapshots GROUP BY ef_count")
for ef, count in c.fetchall():
    print(f"  EF={ef}: {count} 个")

conn.close()
mt5.shutdown()

print(f"\n数据库: {DB_PATH} ({DB_PATH.stat().st_size / 1024:.1f} KB)")
print("完成!")
