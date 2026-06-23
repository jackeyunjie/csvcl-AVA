import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))

import MetaTrader5 as mt5

mt5.initialize()

# 更多候选 - 尝试不同命名
more_stocks = [
    # 日股 - 其他可能命名
    "#TOYOTA", "#HONDA_MOTOR", "#PANASONIC_CORP", "#MITSUBISHI_UFJ",
    # 更多美股
    "#LOCKHEED", "#NORTHROP", "#RAYTHEON", "#GENERAL_DYNAMICS",
    "#PHILIPMORRIS", "#ALTRIA", "#BRISTOL", "#BRISTOLMYERS",
    "#GILEAD", "#AMGEN", "#REGENERON", "#VERTEX",
    "#STARBUCKS", "#MCDONALDS", "#CHIPOTLE", "#DOMINOS",
    "#FEDEX", "#UPS", "#CSX", "#NORFOLK",
    "#BLACKROCK", "#BLACKSTONE", "#KKR", "#CARLYLE",
    "#SALESFORCE", "#WORKDAY", "#DATADOG", "#SNOWFLAKE",
    "#AIRBNB", "#UBER", "#LYFT", "#DOORDASH",
    "#ZOOM", "#SLACK", "#TWILIO", "#SHOPIFY",
    # 更多中概/港股
    "#BAIDU", "#JD_COM", "#XIAOMI_CORP", "#MEITUAN_DIANPING",
    "#KUAISHOU_TECH", "#WUXI_BIO", "#ENN_ENERGY", "#CHINA_MOBILE",
]

print("=" * 70)
print("MT5 更多股票可用性检查")
print("=" * 70)

available = []
for sym in more_stocks:
    info = mt5.symbol_info(sym)
    if info is not None:
        available.append(sym)
        print(f"  [OK] {sym}")
    else:
        print(f"  [NO] {sym}")

print(f"\n可用: {len(available)} 只")
print(available)

# 也尝试列出所有 # 开头的symbol看看命名规律
print("\n" + "=" * 70)
print("MT5中所有 # 开头的品种（前100个）")
print("=" * 70)

all_symbols = mt5.symbols_get()
hash_symbols = [s.name for s in all_symbols if s.name.startswith('#')]
hash_symbols.sort()
print(f"共 {len(hash_symbols)} 个 # 开头品种")
for s in hash_symbols[:100]:
    print(f"  {s}")

if len(hash_symbols) > 100:
    print(f"  ... 还有 {len(hash_symbols)-100} 个")

mt5.shutdown()
