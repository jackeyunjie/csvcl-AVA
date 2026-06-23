import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from build_h1_state_real import build_with_mt5_api

# 新增股指品种
new_indices = [
    'UK_100','FRANCE_40','EUROPE_50','SWISS_20','ITALY_40','GERMANY_TECH30',
    'CHINA_INTERNET',
]

print("=" * 60)
print(f"开始获取 {len(new_indices)} 只新增股指的H1 State数据")
print("=" * 60)

build_with_mt5_api(symbols=new_indices, days=120)

print("=" * 60)
print("新增股指数据获取完成")
print("=" * 60)
