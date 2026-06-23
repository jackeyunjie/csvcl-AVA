import duckdb
conn = duckdb.connect('data/observation_db.duckdb')
print('Tables:', conn.execute("SHOW TABLES").fetchall())
print('Sessions:', conn.execute('SELECT * FROM observation_sessions').fetchall())
print('Profiles count:', conn.execute('SELECT COUNT(*) FROM daily_contraction_profiles').fetchone()[0])
print('Signatures count:', conn.execute('SELECT COUNT(*) FROM symbol_signatures').fetchone()[0])
print('Key obs count:', conn.execute('SELECT COUNT(*) FROM key_observations').fetchone()[0])
conn.close()
