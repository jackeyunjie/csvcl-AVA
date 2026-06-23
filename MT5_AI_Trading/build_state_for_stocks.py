"""
为美股构建 State 数据库
使用现有 MT5 连接（如果有美股数据）或生成模拟 State
"""

import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "data"))

from h1_state_db import H1StateDB
from ai_engine.state_hex_engine import StateHexQuintuplet

# 30只美股
STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "JPM", "BAC", "GS", "WFC", "C",
    "WMT", "COST", "HD", "PG", "KO", "PEP",
    "JNJ", "PFE", "UNH", "ABBV", "LLY",
    "XOM", "CVX", "BA", "CAT",
    "VZ", "DIS", "NFLX", "CRM",
]


def generate_mock_state(symbol: str, days: int = 365) -> list:
    """生成模拟 State 数据（用于测试整合策略）"""
    random.seed(hash(symbol) % 10000)
    
    # 根据股票特性设定基础趋势
    trend_bias = {
        "AAPL": 0.6, "MSFT": 0.6, "GOOGL": 0.5, "AMZN": 0.4,
        "META": 0.5, "NVDA": 0.7, "TSLA": 0.3,
        "JPM": 0.5, "BAC": 0.4, "GS": 0.5, "WFC": 0.4, "C": 0.4,
        "WMT": 0.5, "COST": 0.6, "HD": 0.5, "PG": 0.5, "KO": 0.4, "PEP": 0.5,
        "JNJ": 0.5, "PFE": 0.4, "UNH": 0.6, "ABBV": 0.5, "LLY": 0.7,
        "XOM": 0.4, "CVX": 0.4, "BA": 0.3, "CAT": 0.5,
        "VZ": 0.4, "DIS": 0.3, "NFLX": 0.5, "CRM": 0.5,
    }.get(symbol, 0.5)
    
    results = []
    base_time = datetime.now() - timedelta(days=days)
    
    for i in range(days * 24 // 24):  # 每天1条（简化）
        ts = base_time + timedelta(days=i)
        
        # 模拟趋势变化
        phase = (i / (days * 24)) * 6.28 * 3  # 3个周期
        trend = trend_bias + 0.3 * (random.random() - 0.5) + 0.2 * (1 if i % 100 < 50 else -1)
        
        # 生成 state_hex（简化版）
        if trend > 0.6:
            h1_hex = random.choice(["A", "B"]) + "+" + random.choice(["H", "M"])
            d1_hex = random.choice(["A", "B"]) + "+" + random.choice(["H", "M"])
        elif trend < 0.4:
            h1_hex = random.choice(["D", "E"]) + "-" + random.choice(["H", "M"])
            d1_hex = random.choice(["D", "E"]) + "-" + random.choice(["H", "M"])
        else:
            h1_hex = "C" + "=" + random.choice(["H", "M", "L"])
            d1_hex = "C" + "=" + random.choice(["H", "M", "L"])
        
        # 其他周期
        w1_hex = random.choice(["A", "B", "C", "D", "E"]) + random.choice(["+", "=", "-"]) + "M"
        mn1_hex = random.choice(["A", "B", "C", "D", "E"]) + random.choice(["+", "=", "-"]) + "M"
        h4_hex = random.choice(["A", "B", "C", "D", "E"]) + random.choice(["+", "=", "-"]) + "M"
        
        results.append(StateHexQuintuplet(
            timestamp=ts,
            mn1_hex=mn1_hex,
            w1_hex=w1_hex,
            d1_hex=d1_hex,
            h4_hex=h4_hex,
            h1_hex=h1_hex,
            mn1_duration=1,
            w1_duration=random.randint(1, 2),
            d1_duration=random.randint(1, 3),
            h4_duration=random.randint(1, 5),
            h1_duration=random.randint(1, 10),
        ))
    
    return results


def build_mock_state_db(db_path: str = "data/h1_state.duckdb"):
    """为所有美股构建模拟 State 数据库"""
    print("=== 构建美股 State 数据库（模拟数据）===\n")
    
    h1db = H1StateDB(db_path)
    
    total = 0
    for i, symbol in enumerate(STOCKS, 1):
        print(f"[{i}/{len(STOCKS)}] {symbol}...", end=" ")
        
        quintuplets = generate_mock_state(symbol)
        saved = h1db.save_quintuplets(symbol, quintuplets)
        
        print(f"OK ({saved} 条)")
        total += saved
    
    h1db.close()
    
    print(f"\n=== 完成 ===")
    print(f"总记录: {total} 条")
    print(f"股票数: {len(STOCKS)}")
    print(f"数据库: {db_path}")
    
    return total


if __name__ == "__main__":
    build_mock_state_db()
