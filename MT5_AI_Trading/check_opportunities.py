#!/usr/bin/env python3
"""检查当前市场机会 - 基于最新策略报告"""

import duckdb
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "d:/qoder/csvcl - AVA/MT5_AI_Trading/data/h1_state.duckdb"

conn = duckdb.connect(DB_PATH)

# 获取每个品种最新的state
query = """
SELECT 
    symbol,
    timestamp as datetime,
    mn1_hex as mn1_state,
    w1_hex as w1_state,
    d1_hex as d1_state,
    h4_hex as h4_state,
    h1_hex as h1_state
FROM h1_state_snapshot 
WHERE timestamp = (SELECT MAX(timestamp) FROM h1_state_snapshot)
ORDER BY symbol
"""

df = conn.execute(query).fetchdf()
conn.close()

print("=" * 80)
print(f"当前市场状态检查 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 80)
print(f"\n数据库最新时间: {df['datetime'].iloc[0] if len(df) > 0 else 'N/A'}")
print(f"品种数量: {len(df)}")
print()

# 定义高评分策略模式
patterns = {
    "D1=8,H4=8,H1=-F": lambda r: r['d1_state'] == '8' and r['h4_state'] == '8' and r['h1_state'] == '-F',
    "D1=-E,H1=-6": lambda r: r['d1_state'] == '-E' and r['h1_state'] == '-6',
    "H1=-6": lambda r: r['h1_state'] == '-6',
    "H1=-F": lambda r: r['h1_state'] == '-F',
    "D1=-F,H4=-F,H1=-F": lambda r: r['d1_state'] == '-F' and r['h4_state'] == '-F' and r['h1_state'] == '-F',
    "H1=-E": lambda r: r['h1_state'] == '-E',
    "multi_bear(3+)": lambda r: sum([1 for s in [r['mn1_state'], r['w1_state'], r['d1_state'], r['h4_state'], r['h1_state']] if s and s.startswith('-')]) >= 3,
    "H1 trend-": lambda r: r['h1_state'] and r['h1_state'].startswith('-') and r['h1_state'] in ['-2', '-4', '-6', '-8', '-A', '-C', '-E', '-F'],
}

print("当前匹配高评分策略的品种:")
print("-" * 80)

for pattern_name, pattern_fn in patterns.items():
    matches = df[df.apply(pattern_fn, axis=1)]
    if len(matches) > 0:
        print(f"\n【{pattern_name}】")
        for _, row in matches.iterrows():
            print(f"  {row['symbol']:15s} | "
                  f"MN1={row['mn1_state']} W1={row['w1_state']} D1={row['d1_state']} H4={row['h4_state']} H1={row['h1_state']}")

print("\n" + "=" * 80)
print("所有品种最新状态:")
print("-" * 80)
for _, row in df.iterrows():
    print(f"{row['symbol']:15s} | "
          f"MN1={row['mn1_state']:3s} W1={row['w1_state']:3s} D1={row['d1_state']:3s} H4={row['h4_state']:3s} H1={row['h1_state']:3s}")
