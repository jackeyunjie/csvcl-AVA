"""快速测试: EURUSD历史State回填"""
import MetaTrader5 as mt5, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
mt5.initialize()
r = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_D1, 0, 99999)
print(f"EURUSD D1: {len(r) if r is not None else 0} 根")
if r is not None:
    from datetime import datetime
    print(f"范围: {datetime.fromtimestamp(r[0][0]).date()} ~ {datetime.fromtimestamp(r[-1][0]).date()}")
    print(f"最新收盘: {r[-1][4]}")
mt5.shutdown()
