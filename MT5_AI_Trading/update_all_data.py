import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from build_h1_state_real import build_with_mt5_api

# 所有73个品种
all_symbols = [
    # 股指 (13只)
    'US_30','US_500','US_TECH100','HK_50','CHINA_A50','GER30','JP225',
    'UK_100','FRANCE_40','EUROPE_50','SWISS_20','ITALY_40','GERMANY_TECH30',
    'CHINA_INTERNET',
    # 外汇 (3对)
    'EURUSD','GBPUSD','USDJPY',
    # 大宗商品 (4个)
    'XAUUSD','USOIL','SILVER','BRENT_OIL','NATURAL_GAS',
    # 加密货币 (1个)
    'BTCUSD',
    # 个股 - 第一批 (10只)
    '#APPLE','#MICROSOFT','#NVIDIA','#TESLA','#AMAZON',
    '#GOOGLE','#META','#NETFLIX','#AMD','#JPMORGAN',
    '#BERKSHIRE','#JOHNSON','#EXXON','#WALMART',
    # 第二批 (16只)
    '#ALIBABA','#ADOBE','#SALESFORCE','#ZOOM','#UBER',
    '#AIRBNB','#SNAPCHAT','#COINBASE','#PEPSICO','#MCDONALDS',
    '#STARBUCKS','#NIKE','#DISNEY','#SONY','#TAIWANSEMI','#PINDUODUO',
    # 第三批 (20只)
    '#ORACLE','#INTEL','#CISCO','#QUALCOMM','#BROADCOM',
    '#VISA','#MASTERCARD','#BLACKROCK','#CITIGROUP',
    '#PFIZER','#MERCK','#ABBVIE','#THERMOFISHER',
    '#COSTCO','#HOMEDEPOT','#TARGET',
    '#CHEVRON','#BOEING','#VERIZON',
    '#BAIDU',
]

print("=" * 60)
print(f"开始更新 {len(all_symbols)} 个品种的最新H1 State数据")
print("=" * 60)

build_with_mt5_api(symbols=all_symbols, days=120)

print("=" * 60)
print("所有品种数据更新完成")
print("=" * 60)
