import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from build_h1_state_real import build_with_mt5_api

# 第三批新增20只股票
new_stocks = [
    # 科技/半导体 (5只)
    '#ORACLE','#INTEL','#CISCO','#QUALCOMM','#BROADCOM',
    # 金融/支付 (4只)
    '#VISA','#MASTERCARD','#BLACKROCK','#CITIGROUP',
    # 医疗/制药 (4只)
    '#PFIZER','#MERCK','#ABBVIE','#THERMOFISHER',
    # 消费/零售 (3只)
    '#COSTCO','#HOMEDEPOT','#TARGET',
    # 能源/工业/通信 (3只)
    '#CHEVRON','#BOEING','#VERIZON',
    # 中概股 (1只)
    '#BAIDU',
]

print("=" * 60)
print(f"开始获取 {len(new_stocks)} 只新增股票的H1 State数据")
print("=" * 60)

build_with_mt5_api(symbols=new_stocks, days=120)

print("=" * 60)
print("第三批新增股票数据获取完成")
print("=" * 60)
