import duckdb

conn = duckdb.connect('data/h1_state.duckdb')

# 获取最新数据时间
latest = conn.execute('SELECT MAX(timestamp) FROM h1_state_snapshot').fetchone()[0]
print('最新数据时间:', latest)
print()

# 获取所有品种的最新五元组状态
rows = conn.execute("""
    SELECT symbol, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex, timestamp
    FROM h1_state_snapshot
    WHERE timestamp = (SELECT MAX(timestamp) FROM h1_state_snapshot)
    ORDER BY symbol
""").fetchall()

print(f'共 {len(rows)} 个品种的最新State:')
print()
print(f'{"品种":<20} | {"MN1":>4} | {"W1":>4} | {"D1":>4} | {"H4":>4} | {"H1":>4}')
print('-' * 70)
for r in rows:
    print(f'{r[0]:<20} | {r[1]:>4} | {r[2]:>4} | {r[3]:>4} | {r[4]:>4} | {r[5]:>4}')

conn.close()
