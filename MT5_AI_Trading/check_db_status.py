import duckdb
import sys
sys.path.insert(0, "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\python")

conn = duckdb.connect('data/h1_state.duckdb')
markets = ['US_30','US_500','US_TECH100','EURUSD','GBPUSD','USDJPY','XAUUSD','USOIL','BTCUSD','HK_50','CHINA_A50','GER30','JP225','SILVER','BRENT_OIL','NATURAL_GAS','#APPLE','#MICROSOFT','#NVIDIA','#TESLA']
print('=== H1 State 数据库状态 ===')
for m in markets:
    cnt = conn.execute(f"SELECT COUNT(*) FROM h1_state_snapshot WHERE symbol='{m}'").fetchone()[0]
    latest = conn.execute(f"SELECT MAX(timestamp) FROM h1_state_snapshot WHERE symbol='{m}'").fetchone()[0]
    print(f'{m:15} | {cnt:5}条 | 最新: {latest}')
conn.close()
print('\n数据检查完成！')
