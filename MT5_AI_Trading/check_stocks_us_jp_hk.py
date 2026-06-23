import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))

import MetaTrader5 as mt5

mt5.initialize()

# 候选美股（科技、金融、医疗、消费等）
us_stocks = [
    # 科技
    "#ORACLE", "#INTEL", "#CISCO", "#QUALCOMM", "#BROADCOM", "#TEXASINSTRUMENTS",
    "#APPLIEDMATERIALS", "#MICRON", "#SERVICENOW", "#INTUIT", "#AUTODESK",
    # 金融
    "#BANKOFAMERICA", "#WELLSFARGO", "#CITIGROUP", "#GOLDMANSACHS", "#MORGANSTANLEY",
    "#AMERICANEXPRESS", "#VISA", "#MASTERCARD", "#PAYPAL", "#SQUARE",
    # 医疗
    "#PFIZER", "#MERCK", "#ABBVIE", "#LILLY", "#THERMOFISHER",
    # 消费/零售
    "#COSTCO", "#HOMEDEPOT", "#LOWES", "#TARGET", "#PROCTER",
    # 能源/工业
    "#CHEVRON", "#SCHLUMBERGER", "#BOEING", "#CATERPILLAR", "#GENERALELECTRIC",
    # 通信/媒体
    "#VERIZON", "#ATT", "#COMCAST", "#CHARTER", "#SPOTIFY",
]

# 候选日股
jp_stocks = [
    "#TOYOTAMOTOR", "#SONY", "#SOFTBANK", "#NINTENDO", "#HONDA",
    "#CANON", "#PANASONIC", "#HITACHI", "#MITSUBISHI", "#FUJITSU",
    "#SHARP", "#NISSAN", "#MAZDA", "#SUBARU", "#KONAMI",
]

# 候选港股
hk_stocks = [
    "#TENCENT", "#ALIBABA", "#MEITUAN", "#XIAOMI", "#PINDUODUO",
    "#JD", "#BIDU", "#NETEASE", "#BYD", "#LI_AUTO",
    "#NIO", "#XPENG", "#BILIBILI", "#KUAISHOU", "#WUXI",
]

print("=" * 70)
print("MT5 美股/日股/港股 可用性检查")
print("=" * 70)

print("\n【美股】")
us_available = []
for sym in us_stocks:
    info = mt5.symbol_info(sym)
    if info is not None:
        us_available.append(sym)
        print(f"  [OK] {sym}")
    else:
        print(f"  [NO] {sym}")

print(f"\n可用美股: {len(us_available)} 只")

print("\n【日股】")
jp_available = []
for sym in jp_stocks:
    info = mt5.symbol_info(sym)
    if info is not None:
        jp_available.append(sym)
        print(f"  [OK] {sym}")
    else:
        print(f"  [NO] {sym}")

print(f"\n可用日股: {len(jp_available)} 只")

print("\n【港股/中概股】")
hk_available = []
for sym in hk_stocks:
    info = mt5.symbol_info(sym)
    if info is not None:
        hk_available.append(sym)
        print(f"  [OK] {sym}")
    else:
        print(f"  [NO] {sym}")

print(f"\n可用港股/中概股: {len(hk_available)} 只")

print("\n" + "=" * 70)
print("汇总")
print("=" * 70)
print(f"美股: {us_available}")
print(f"日股: {jp_available}")
print(f"港股: {hk_available}")

mt5.shutdown()
