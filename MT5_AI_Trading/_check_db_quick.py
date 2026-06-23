import duckdb
from pathlib import Path

print("=== H1 DATABASE ===")
conn = duckdb.connect("data/h1_state.duckdb", read_only=True)
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"Tables: {tables}")
for tbl in [t[0] for t in tables]:
    try:
        rows = conn.execute(f"SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp) FROM {tbl} GROUP BY symbol ORDER BY symbol").fetchall()
        print(f"\nTable: {tbl}")
        for r in rows:
            print(f"  {r[0]}: {r[1]} rows, {r[2]} to {r[3]}")
    except Exception as e:
        print(f"  {tbl}: error - {e}")
conn.close()

print("\n=== M15 DATABASE ===")
conn = duckdb.connect("data/m15_state.duckdb", read_only=True)
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"Tables: {tables}")
for tbl in [t[0] for t in tables]:
    try:
        rows = conn.execute(f"SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp) FROM {tbl} GROUP BY symbol ORDER BY symbol").fetchall()
        print(f"\nTable: {tbl}")
        for r in rows:
            print(f"  {r[0]}: {r[1]} rows, {r[2]} to {r[3]}")
    except Exception as e:
        print(f"  {tbl}: error - {e}")
conn.close()
