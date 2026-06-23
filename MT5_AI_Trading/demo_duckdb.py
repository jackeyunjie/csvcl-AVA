"""
DuckDB演示 - 直接查询SQLite并展示分析能力
"""
import duckdb

# DuckDB可以直接查询SQLite!
conn = duckdb.connect()
conn.execute("INSTALL sqlite; LOAD sqlite;")
conn.execute("ATTACH 'data/state_db.sqlite' AS sqlite_db (TYPE SQLITE);")

print("="*60)
print("DuckDB查询SQLite数据库")
print("="*60)

# 1. 基本统计
result = conn.execute('''
    SELECT COUNT(*) as total, COUNT(DISTINCT symbol) as symbols
    FROM sqlite_db.state_snapshots
''').fetchone()
print(f"\n总记录: {result[0]}")
print(f"品种数: {result[1]}")

# 2. EF分布 (窗口函数)
print("\nEF分布:")
for row in conn.execute('''
    SELECT ef_count, COUNT(*) as cnt,
           ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
    FROM sqlite_db.state_snapshots
    GROUP BY ef_count
    ORDER BY ef_count
''').fetchall():
    print(f"  EF={row[0]}: {row[1]} ({row[2]}%)")

# 3. 导入DuckDB进行更快分析
conn.execute('''
    CREATE TABLE state_snapshots AS 
    SELECT * FROM sqlite_db.state_snapshots
''')

# 4. State转换分析 (LAG窗口函数)
print("\nEURUSD State转换 (Top 5):")
for row in conn.execute('''
    WITH lagged AS (
        SELECT timestamp, state_hex,
               LAG(state_hex) OVER (ORDER BY timestamp) as prev
        FROM state_snapshots
        WHERE symbol = 'EURUSD'
    )
    SELECT prev || ' -> ' || state_hex as transition, COUNT(*) as freq
    FROM lagged
    WHERE prev IS NOT NULL
    GROUP BY prev, state_hex
    ORDER BY freq DESC
    LIMIT 5
''').fetchall():
    print(f"  {row[0]}: {row[1]}次")

# 5. 导出为Parquet (DuckDB原生支持)
conn.execute("COPY state_snapshots TO 'data/state_snapshots.parquet' (FORMAT PARQUET)")
print("\n已导出Parquet格式")

# 6. 从Parquet读取 (验证)
conn.execute("CREATE TABLE from_parquet AS SELECT * FROM 'data/state_snapshots.parquet'")
count = conn.execute("SELECT COUNT(*) FROM from_parquet").fetchone()[0]
print(f"从Parquet读取: {count} 条记录")

conn.close()
print("\n" + "="*60)
print("DuckDB演示完成!")
print("="*60)
