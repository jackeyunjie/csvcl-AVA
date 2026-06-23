#!/usr/bin/env python3
"""检查数据更新进度"""
import duckdb
import sys

try:
    con = duckdb.connect('data/h1_state.duckdb', read_only=True)
    result = con.execute('''
        SELECT 
            COUNT(DISTINCT symbol) as symbol_cnt,
            MAX(timestamp) as latest_ts,
            COUNT(*) as total_rows
        FROM h1_state_snapshot
    ''').fetchone()
    print(f"Symbols: {result[0]}/73")
    print(f"Latest: {result[1]}")
    print(f"Total rows: {result[2]}")
    
    # List symbols
    symbols = con.execute('SELECT DISTINCT symbol FROM h1_state_snapshot ORDER BY symbol').fetchall()
    print(f"\nSymbols in DB ({len(symbols)}):")
    for s in symbols:
        print(f"  {s[0]}")
    con.close()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
