"""
快速构建 State 数据库 - 小数据量测试
"""

import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

import duckdb

# 路径
DB_PATH = "data/h1_state.duckdb"

# 股票列表
STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "JPM", "BAC", "GS", "WFC", "C",
    "WMT", "COST", "HD", "PG", "KO", "PEP",
    "JNJ", "PFE", "UNH", "ABBV", "LLY",
    "XOM", "CVX", "BA", "CAT",
    "VZ", "DIS", "NFLX", "CRM",
]

# 趋势偏好（影响 state_hex）
TREND_BIAS = {
    "AAPL": 0.6, "MSFT": 0.6, "GOOGL": 0.5, "AMZN": 0.4,
    "META": 0.5, "NVDA": 0.7, "TSLA": 0.3,
    "JPM": 0.5, "BAC": 0.4, "GS": 0.5, "WFC": 0.4, "C": 0.4,
    "WMT": 0.5, "COST": 0.6, "HD": 0.5, "PG": 0.5, "KO": 0.4, "PEP": 0.5,
    "JNJ": 0.5, "PFE": 0.4, "UNH": 0.6, "ABBV": 0.5, "LLY": 0.7,
    "XOM": 0.4, "CVX": 0.4, "BA": 0.3, "CAT": 0.5,
    "VZ": 0.4, "DIS": 0.3, "NFLX": 0.5, "CRM": 0.5,
}


def generate_state_for_stock(symbol: str, days: int = 30):
    """生成单只股票的 State 数据（30天）"""
    random.seed(hash(symbol) % 10000)
    bias = TREND_BIAS.get(symbol, 0.5)
    
    rows = []
    base = datetime.now() - timedelta(days=days)
    
    for i in range(days):
        ts = base + timedelta(days=i)
        
        # 根据趋势偏好生成 state
        t = bias + 0.2 * (random.random() - 0.5)
        
        if t > 0.6:
            h1 = random.choice(["A", "B"]) + "+" + random.choice(["H", "M"])
            d1 = random.choice(["A", "B"]) + "+" + random.choice(["H", "M"])
        elif t < 0.4:
            h1 = random.choice(["D", "E"]) + "-" + random.choice(["H", "M"])
            d1 = random.choice(["D", "E"]) + "-" + random.choice(["H", "M"])
        else:
            h1 = "C" + "=" + random.choice(["H", "M", "L"])
            d1 = "C" + "=" + random.choice(["H", "M", "L"])
        
        rows.append((
            symbol, ts,
            "C=M", "C=M", d1, "C=M", h1,  # mn1, w1, d1, h4, h1
            1, 1, 1, 1, 1  # durations
        ))
    
    return rows


def main():
    print("=== 快速构建 State 数据库 ===\n")
    
    # 连接数据库
    conn = duckdb.connect(DB_PATH)
    
    # 确保表存在
    conn.execute("""
        CREATE TABLE IF NOT EXISTS h1_state_snapshot (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            mn1_hex VARCHAR,
            w1_hex VARCHAR,
            d1_hex VARCHAR,
            h4_hex VARCHAR,
            h1_hex VARCHAR,
            mn1_duration INTEGER,
            w1_duration INTEGER,
            d1_duration INTEGER,
            h4_duration INTEGER,
            h1_duration INTEGER
        )
    """)
    
    total = 0
    for i, symbol in enumerate(STOCKS, 1):
        rows = generate_state_for_stock(symbol)
        
        conn.executemany("""
            INSERT INTO h1_state_snapshot
            (symbol, timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex,
             mn1_duration, w1_duration, d1_duration, h4_duration, h1_duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        
        print(f"[{i:2d}/{len(STOCKS)}] {symbol}: {len(rows)} 条")
        total += len(rows)
    
    conn.commit()
    conn.close()
    
    print(f"\n=== 完成 ===")
    print(f"总记录: {total} 条")
    print(f"数据库: {DB_PATH}")


if __name__ == "__main__":
    main()
