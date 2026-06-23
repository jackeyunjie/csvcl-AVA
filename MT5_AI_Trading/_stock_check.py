import duckdb,os
c=duckdb.connect('data/stock_state.db')
snap=c.execute('SELECT COUNT(*) FROM state_snapshots').fetchone()[0]
syms=c.execute('SELECT COUNT(DISTINCT symbol) FROM state_snapshots').fetchone()[0]
tbls=[t[0] for t in c.execute('SHOW TABLES').fetchall()]
print(f'Stock: {snap}条 {syms}品种 表:{tbls}')
if snap>0:
    ef=c.execute('SELECT ef_count,COUNT(*) FROM state_snapshots GROUP BY ef_count ORDER BY ef_count DESC').fetchall()
    for r in ef: print(f'  EF={r[0]}: {r[1]}')
    ok=c.execute('SELECT DISTINCT symbol FROM state_snapshots ORDER BY symbol').fetchall()
    print(f'Working: {[r[0] for r in ok]}')
c.close()
