import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from data.h1_state_db import H1StateDB

h1db = H1StateDB("data/h1_state.duckdb")
all_symbols = [
    "US_30", "US_500", "US_TECH100", "EURUSD", "XAUUSD", "USOIL", "BTCUSD",
    "HK_50", "CHINA_A50", "GER30", "JP225", "GBPUSD", "USDJPY",
    "SILVER", "BRENT_OIL", "NATURAL_GAS",
    "#APPLE", "#MICROSOFT", "#NVIDIA", "#TESLA"
]

print("=" * 70)
print("H1 State 数据库 - 全品种数据验证")
print("=" * 70)

total_ok = 0
total_empty = 0
for sym in all_symbols:
    s = h1db.get_summary(sym)
    status = "OK" if s["total_rows"] > 0 else "EMPTY"
    if s["total_rows"] > 0:
        total_ok += 1
    else:
        total_empty += 1
    earliest = s.get("earliest", "N/A")
    latest = s.get("latest", "N/A")
    earliest_str = str(earliest)[:10] if earliest else "N/A"
    latest_str = str(latest)[:10] if latest else "N/A"
    print(f"  {sym:12s} {s['total_rows']:>6} rows  {earliest_str} ~ {latest_str}  [{status}]")

print("=" * 70)
print(f"总计: {total_ok} 个品种有数据, {total_empty} 个品种为空")
print("=" * 70)

h1db.close()
