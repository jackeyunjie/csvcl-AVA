import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "python"))

from build_h1_state_real import build_with_mt5_api

# 20只新增全球股票（MT5中实际可用的）
new_stocks = [
    # 美国大型科技股/金融 (8只)
    '#ALIBABA','#ADOBE','#SALESFORCE','#ZOOM','#UBER',
    '#AIRBNB','#SNAPCHAT','#COINBASE',
    # 美国传统行业 (6只)
    '#COCACOLA','#PEPSICO','#MCDONALDS','#STARBUCKS','#NIKE','#DISNEY',
    # 日本/亚太 (4只)
    '#SONY','#TOYOTAMOTOR','#TAIWANSEMI','#PINDUODUO',
    # 欧洲 (2只)
    '#ASMLHOLDING','#SHELL',
]

print("=" * 60)
print("更新20只新增全球股票数据")
print("=" * 60)
print(f"品种: {new_stocks}")
print("=" * 60)

build_with_mt5_api(symbols=new_stocks, days=120)
