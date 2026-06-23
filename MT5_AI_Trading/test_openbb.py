from openbb import obb
import json

# 测试股票基本面
symbol = "AAPL"

print("=== OpenBB 数据拉取测试 ===")
print(f"\n测试股票: {symbol}")

try:
    # 获取公司信息
    print("\n1. 公司信息...")
    info = obb.equity.profile(symbol)
    print(f"   成功: {info}")
except Exception as e:
    print(f"   失败: {e}")

try:
    # 获取财务报表
    print("\n2. 收入报表...")
    income = obb.equity.fundamental.income(symbol, period="quarter")
    print(f"   成功: {income}")
except Exception as e:
    print(f"   失败: {e}")

try:
    # 获取资产负债表
    print("\n3. 资产负债表...")
    balance = obb.equity.fundamental.balance(symbol, period="quarter")
    print(f"   成功: {balance}")
except Exception as e:
    print(f"   失败: {e}")

try:
    # 获取估值指标
    print("\n4. 财务比率...")
    ratios = obb.equity.fundamental.ratios(symbol)
    print(f"   成功: {ratios}")
except Exception as e:
    print(f"   失败: {e}")

try:
    # 获取价格数据
    print("\n5. 价格数据...")
    price = obb.equity.price.historical(symbol, start_date="2024-01-01")
    print(f"   成功: {price.tail()}")
except Exception as e:
    print(f"   失败: {e}")

print("\n=== 测试完成 ===")
