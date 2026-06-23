import duckdb,os
c=duckdb.connect('data/fundamental_duckdb.db')
for t in ['daily_prices','equity_fundamentals','macro_indicators']:
    n=c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f'{t}: {n}')
c.close()
sz=os.path.getsize('data/fundamental_duckdb.db')/1024
print(f'Size: {sz:.0f}KB')
