"""
检查 State 数据库内容
"""
import duckdb

conn = duckdb.connect('data/h1_state.duckdb')

print("=== Tables ===")
print(conn.execute("SHOW TABLES").fetchall())

print("\n=== Count ===")
print(conn.execute("SELECT COUNT(*) FROM h1_state_snapshot").fetchone())

print("\n=== Symbols ===")
rows = conn.execute("SELECT DISTINCT symbol FROM h1_state_snapshot ORDER BY symbol").fetchall()
print([r[0] for r in rows])

print("\n=== Sample ===")
rows = conn.execute("SELECT symbol, h1_hex, h4_hex, d1_hex, timestamp FROM h1_state_snapshot LIMIT 10").fetchall()
for r in rows:
    print(r)

print("\n=== Hex Distribution (H1) ===")
rows = conn.execute("""
    SELECT h1_hex, COUNT(*) as cnt 
    FROM h1_state_snapshot 
    GROUP BY h1_hex 
    ORDER BY cnt DESC 
    LIMIT 10
""").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]}")

print("\n=== Hex Distribution (H4) ===")
rows = conn.execute("""
    SELECT h4_hex, COUNT(*) as cnt 
    FROM h1_state_snapshot 
    GROUP BY h4_hex 
    ORDER BY cnt DESC 
    LIMIT 10
""").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]}")

conn.close()
