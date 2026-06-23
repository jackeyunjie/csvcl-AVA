#!/usr/bin/env python3
"""检查新增股票品种数据状态"""

import duckdb

conn = duckdb.connect('data/h1_state.duckdb')

# 查询所有股票品种
print("=" * 70)
print("美股品种数据状态")
print("=" * 70)

df = conn.execute("""
    SELECT 
        symbol, 
        COUNT(*) as cnt, 
        MIN(timestamp) as earliest, 
        MAX(timestamp) as latest 
    FROM h1_state_snapshot 
    WHERE symbol LIKE '#%' 
    GROUP BY symbol 
    ORDER BY symbol
""").fetchdf()

print(df.to_string(index=False))

# 总品种数统计
print("\n" + "=" * 70)
total = conn.execute("SELECT COUNT(DISTINCT symbol) FROM h1_state_snapshot").fetchone()[0]
stock_count = conn.execute("SELECT COUNT(DISTINCT symbol) FROM h1_state_snapshot WHERE symbol LIKE '#' || '%' ").fetchone()[0]
print(f"数据库总品种数: {total}")
print(f"美股品种数: {stock_count}")
print("=" * 70)

conn.close()
