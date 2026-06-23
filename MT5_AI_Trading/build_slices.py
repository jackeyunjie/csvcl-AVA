"""生成State切片库 — 对现有hermass_state.db补充state_slices表"""
import duckdb
from collections import defaultdict

DB = "data/hermass_state.db"
c = duckdb.connect(DB)

# 删旧建新
c.execute("DROP TABLE IF EXISTS state_slices")
c.execute("""
    CREATE TABLE state_slices (
        slice_id VARCHAR, symbol VARCHAR, perspective VARCHAR,
        pattern VARCHAR, mn1_hex VARCHAR, w1_hex VARCHAR, d1_hex VARCHAR,
        occurrence_count INTEGER
    )
""")

syms = [r[0] for r in c.execute("SELECT DISTINCT symbol FROM state_snapshots").fetchall()]
total = 0

for sym in syms:
    rows = c.execute("""
        SELECT mn1_hex, w1_hex, d1_hex
        FROM state_snapshots
        WHERE symbol=? AND perspective='D1'
        ORDER BY date
    """, (sym,)).fetchall()

    if len(rows) < 10:
        continue

    pats = defaultdict(int)
    for r in rows:
        pats[f"{r[0]}_{r[1]}_{r[2]}"] += 1

    for pat, cnt in pats.items():
        p = pat.split("_")
        if len(p) != 3:
            continue
        c.execute("""
            INSERT INTO state_slices VALUES (?,?,?,?,?,?,?,?)
        """, (f"{sym}_D1_{pat}", sym, "D1", pat, p[0], p[1], p[2], cnt))
        total += 1

print(f"Slices: {total} ({len(syms)}品种)")

# 验证
top = c.execute("""
    SELECT pattern, SUM(occurrence_count) n
    FROM state_slices
    GROUP BY pattern
    ORDER BY n DESC LIMIT 10
""").fetchall()
print("\nTop10 State模式(全品种):")
for r in top:
    print(f"  {r[0]:20s} x{r[1]:5d}")

c.close()
import os
print(f"\nDB: {os.path.getsize(DB)/1024:.0f}KB")
