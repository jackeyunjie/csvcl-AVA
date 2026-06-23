import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))

import MetaTrader5 as mt5

mt5.initialize()

# 常见全球股指列表
check_symbols = [
    # 欧洲
    "UK_100", "FRANCE_40", "EUROPE_50", "SPAIN_35", "SWISS_20", "ITALY_40",
    # 亚太
    "AUSTRALIA_200", "INDIA_50", "SINGAPORE_25", "SOUTH_AFRICA_40",
    # 其他
    "US_30", "US_500", "US_TECH100", "HK_50", "CHINA_A50", "GER30", "JP225",
]

print("=" * 60)
print("MT5 全球股指可用性检查")
print("=" * 60)

available = []
for sym in check_symbols:
    info = mt5.symbol_info(sym)
    if info is not None:
        available.append(sym)
        print(f"  [OK] {sym}")
    else:
        print(f"  [NO] {sym}")

print("=" * 60)
print(f"可用股指: {len(available)} 个")
print(available)

# 也尝试搜索所有包含index/指数的symbol
print("\n" + "=" * 60)
print("搜索MT5中所有指数类品种...")
print("=" * 60)

all_symbols = mt5.symbols_get()
indices = []
for s in all_symbols:
    name = s.name
    # 常见股指命名模式
    if any(x in name for x in ['_30','_500','_100','_225','_50','GER','HK','CHINA','JAPAN','UK','FRANCE','EUROPE','AUSTRALIA','INDIA','SINGAPORE','SWISS','SPAIN','ITALY','SOUTH_AFRICA']):
        if name not in indices:
            indices.append(name)

indices.sort()
print(f"找到 {len(indices)} 个指数类品种:")
for i in indices:
    print(f"  {i}")

mt5.shutdown()
