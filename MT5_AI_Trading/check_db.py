import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))
from data.h1_state_db import H1StateDB

db = H1StateDB("data/h1_state.duckdb")
conn = db._get_conn()
df = conn.execute("SELECT symbol, COUNT(*) as cnt, MAX(timestamp) as latest FROM h1_state_snapshot GROUP BY symbol ORDER BY symbol").fetchdf()
print(df.to_string(index=False))
