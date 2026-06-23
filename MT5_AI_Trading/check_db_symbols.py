import duckdb

conn = duckdb.connect('data/h1_state.duckdb', read_only=True)

# 查看有哪些symbol
symbols = conn.execute("SELECT DISTINCT symbol FROM h1_state_snapshot ORDER BY symbol").fetchdf()
print('数据库中的品种:')
print(symbols.to_string())

# 查找包含GER的品种
ger = conn.execute("SELECT DISTINCT symbol FROM h1_state_snapshot WHERE symbol LIKE '%GER%' ORDER BY symbol").fetchdf()
print('\n包含GER的品种:')
print(ger.to_string())

# 查找GER30
ger30 = conn.execute("SELECT COUNT(*) as cnt FROM h1_state_snapshot WHERE symbol = 'GER30'").fetchdf()
print('\nGER30数据量:')
print(ger30.to_string())

# 查找GERMANY_40
g40 = conn.execute("SELECT COUNT(*) as cnt FROM h1_state_snapshot WHERE symbol = 'GERMANY_40'").fetchdf()
print('\nGERMANY_40数据量:')
print(g40.to_string())

conn.close()
