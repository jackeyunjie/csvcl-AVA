"""快速分析 State 数据"""
import duckdb
conn = duckdb.connect('data/h1_state.duckdb', read_only=True)

# 只查几条
rows = conn.execute("SELECT DISTINCT symbol FROM h1_state_snapshot LIMIT 5").fetchall()
print("Symbols:", [r[0] for r in rows])

rows = conn.execute("SELECT DISTINCT h1_hex FROM h1_state_snapshot WHERE h1_hex != 'N/A' LIMIT 20").fetchall()
print("H1 Hex samples:", [r[0] for r in rows])

# 统计格式
rows = conn.execute("""
    SELECT 
        CASE WHEN h1_hex LIKE '%+%' OR h1_hex LIKE '%=%' THEN 'old'
             WHEN h1_hex REGEXP '^-?[0-9A-Fa-f]+$' THEN 'real'
             ELSE 'other' END as fmt,
        COUNT(*) as cnt
    FROM h1_state_snapshot
    GROUP BY fmt
""").fetchall()
print("Format distribution:")
for fmt, cnt in rows:
    print(f"  {fmt}: {cnt}")

conn.close()
