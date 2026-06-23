import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))

import MetaTrader5 as mt5
from data.h1_state_db import H1StateDB

mt5.initialize()

print("=" * 60)
print("GER30 / JP225 做空权限与最新数据查询")
print("=" * 60)

for sym in ['GERMANY_40', 'JAPAN_225']:
    info = mt5.symbol_info(sym)
    if info:
        print(f"\n=== {sym} ===")
        print(f"  可做空 (trade_mode=4 表示可双向): {info.trade_mode}")
        print(f"  买入价 (ask): {info.ask}")
        print(f"  卖出价 (bid): {info.bid}")
        print(f"  点差 (spread): {info.spread}")
        print(f"  最小手数: {info.volume_min}")
        print(f"  最大手数: {info.volume_max}")
        print(f"  合约大小: {info.trade_contract_size}")
    else:
        print(f"\n{sym}: 无法获取信息")

mt5.shutdown()

print("\n" + "=" * 60)
print("最新 H1 State")
print("=" * 60)

db = H1StateDB("data/h1_state.duckdb")
for s in ['GER30', 'JP225']:
    latest = db.get_latest(s)
    print(f"\n=== {s} ===")
    if latest:
        print(f"  时间: {latest.get('timestamp')}")
        print(f"  MN1: {latest.get('mn1_hex')}")
        print(f"  W1:  {latest.get('w1_hex')}")
        print(f"  D1:  {latest.get('d1_hex')}")
        print(f"  H4:  {latest.get('h4_hex')}")
        print(f"  H1:  {latest.get('h1_hex')}")
    else:
        print("  无数据")

db.close()
