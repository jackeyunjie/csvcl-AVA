import sqlite3
conn = sqlite3.connect(r"d:\qoder\csvcl - AVA\MT5_AI_Trading\data\state_db.sqlite")
print("="*50)
print("State数据库状态")
print("="*50)
print("总行数:", conn.execute("SELECT COUNT(*) FROM state_snapshots").fetchone()[0])
print("品种数:", conn.execute("SELECT COUNT(DISTINCT symbol) FROM state_snapshots").fetchone()[0])

r = conn.execute("SELECT MIN(timestamp),MAX(timestamp) FROM state_snapshots").fetchone()
print(f"日期范围: {r[0]} ~ {r[1]}")

print("\nEF分布:")
for row in conn.execute("SELECT ef_count, COUNT(*) FROM state_snapshots GROUP BY ef_count"):
    print(f"  EF={row[0]}: {row[1]} ({row[1]/conn.execute('SELECT COUNT(*) FROM state_snapshots').fetchone()[0]*100:.1f}%)")

print("\nEURUSD D1 最新10条:")
for row in conn.execute("SELECT timestamp,state_hex,ef_count FROM state_snapshots WHERE symbol='EURUSD' AND perspective='D1' ORDER BY timestamp DESC LIMIT 10"):
    print(f"  {row[0]} {row[1]} ef={row[2]}")

print("\n各品种快照数:")
for row in conn.execute("SELECT symbol, COUNT(*) FROM state_snapshots GROUP BY symbol ORDER BY COUNT(*) DESC"):
    print(f"  {row[0]}: {row[1]}")

conn.close()
print("="*50)
