#!/usr/bin/env python3
"""检查数据库结构"""
import duckdb

con = duckdb.connect('data/h1_state.duckdb', read_only=True)

# Check tables
tables = con.execute("SHOW TABLES").fetchall()
print('Tables:')
for t in tables:
    print(f'  {t[0]}')

# Check h1_state_snapshot columns
print('\nh1_state_snapshot columns:')
cols = con.execute('PRAGMA table_info(h1_state_snapshot)').fetchall()
for c in cols:
    print(f'  {c[1]} ({c[2]})')

# Sample data
print('\nSample row:')
sample = con.execute('SELECT * FROM h1_state_snapshot LIMIT 1').fetchone()
cols_names = [c[1] for c in cols]
for name, val in zip(cols_names, sample):
    print(f'  {name}: {val}')

con.close()
