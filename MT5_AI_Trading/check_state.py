import sqlite3,os
db='data/state_db.sqlite'
if os.path.exists(db):
    c=sqlite3.connect(db)
    total=c.execute('SELECT COUNT(*) FROM state_snapshots').fetchone()[0]
    syms=c.execute('SELECT COUNT(DISTINCT symbol) FROM state_snapshots').fetchone()[0]
    cols=[r[1] for r in c.execute('PRAGMA table_info(state_snapshots)').fetchall()]
    has_hermass='mn1_hex' in cols and 'd1_score' in cols
    print(f'SQLite: {total}条 {syms}品种 Hermass格式={has_hermass}')
    if has_hermass:
        ef2=c.execute("SELECT COUNT(*) FROM state_snapshots WHERE ef_count>=2").fetchone()[0]
        print(f'EF>=2: {ef2}')
    else:
        print(f'字段: {cols[:12]}')
    c.close()
else:
    print('not found')
