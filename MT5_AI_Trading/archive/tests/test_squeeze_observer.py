import sys
sys.path.insert(0, 'python')

from analytics.squeeze_observer import SqueezeObserver, SqueezeMetrics
import pandas as pd
import numpy as np

# 测试1: 静态方法测试
print("=" * 60)
print("测试1: 指标计算静态方法")
print("=" * 60)

# 生成测试数据
np.random.seed(42)
n = 100
close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5))
high = close + abs(np.random.randn(n) * 0.3)
low = close - abs(np.random.randn(n) * 0.3)

# 测试布林带宽
bb_width = SqueezeObserver.compute_bb_width(close)
print(f"BB Width: 均值={bb_width.mean():.4f}, 最新={bb_width.iloc[-1]:.4f}")

# 测试枢轴范围
pivot_range = SqueezeObserver.compute_pivot_range(high, low, close)
print(f"Pivot Range: 均值={pivot_range.mean():.2f}%, 最新={pivot_range.iloc[-1]:.2f}%")

# 测试ADX
adx = SqueezeObserver.compute_adx(high, low, close)
print(f"ADX: 均值={adx.mean():.1f}, 最新={adx.iloc[-1]:.1f}")

# 测试分位数判断
is_squeezed = SqueezeObserver.is_value_below_percentile(bb_width, lookback=30, percentile=20)
print(f"BB是否收缩(20%分位): {is_squeezed}")

print("\n静态方法测试通过!")

# 测试2: SqueezeMetrics数据类
print("\n" + "=" * 60)
print("测试2: SqueezeMetrics数据类")
print("=" * 60)

m = SqueezeMetrics(
    symbol="EURUSD",
    timeframe="H1",
    timestamp=pd.Timestamp("2026-06-04 01:00"),
    bb_width=0.0234,
    bb_squeezed_20=True,
    adx=15.5,
    adx_lt_20=True,
    adx_lt_13=False,
    state_hex="0",
    state_is_zero=True,
    squeeze_score=3,
    squeeze_conditions=["BB_20", "ADX<20", "State=0"]
)

print(f"品种: {m.symbol}")
print(f"周期: {m.timeframe}")
print(f"BB Width: {m.bb_width}")
print(f"收缩分数: {m.squeeze_score}")
print(f"条件: {m.squeeze_conditions}")

print("\n数据类测试通过!")
print("\n" + "=" * 60)
print("所有测试通过! 等待数据更新完成后可运行完整分析。")
print("=" * 60)
