import duckdb
from pathlib import Path

print("=== H1 State Database ===")
if Path('data/h1_state.duckdb').exists():
    conn = duckdb.connect('data/h1_state.duckdb', read_only=True)
    try:
        result = conn.execute("""
            SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp) 
            FROM h1_state_snapshot 
            GROUP BY symbol 
            ORDER BY symbol
        """).fetchall()
        for row in result:
            print(f"  {row}")
    except Exception as e:
        print(f"  Error: {e}")
    finally:
        conn.close()
else:
    print("  Database not found")

print("\n=== M15 State Database ===")
if Path('data/m15_state.duckdb').exists():
    conn = duckdb.connect('data/m15_state.duckdb', read_only=True)
    try:
        result = conn.execute("""
            SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp) 
            FROM m15_state_snapshot 
            GROUP BY symbol 
            ORDER BY symbol
        """).fetchall()
        for row in result:
            print(f"  {row}")
    except Exception as e:
        print(f"  Error: {e}")
    finally:
        conn.close()
else:
    print("  Database not found")
