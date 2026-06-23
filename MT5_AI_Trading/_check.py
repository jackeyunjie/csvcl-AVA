import duckdb,os;db='data/fundamental_duckdb.db'
c=duckdb.connect(db)
for t in c.execute('SHOW TABLES').fetchall():
    n=c.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
    print(f'{t[0]}: {n}')
c.close()
print(f'Size: {os.path.getsize(db)/1024:.0f}KB')
