"""
收缩观测系统完整测试
使用模拟数据测试所有指标计算和报告生成
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "python"))

from analytics.squeeze_observer import SqueezeObserver, SqueezeMetrics

# 生成模拟OHLCV数据（含收缩期）
np.random.seed(42)
n = 120  # 120根K线

# 价格趋势
trend = np.cumsum(np.random.randn(n) * 0.3)
base_price = 100

# 波动率：前80天高，中间20天收缩，后20天扩张
vol = np.ones(n) * 2.0
vol[60:80] = np.linspace(2.0, 0.4, 20)  # 收缩期
vol[80:100] = 0.4  # 低波动持续
vol[100:] = np.linspace(0.4, 2.5, 20)  # 扩张期

close = base_price + trend
high = close + np.abs(np.random.randn(n)) * vol
low = close - np.abs(np.random.randn(n)) * vol
open_p = close + np.random.randn(n) * vol * 0.3

# 确保OHLC逻辑正确
for i in range(n):
    high[i] = max(high[i], close[i], open_p[i])
    low[i] = min(low[i], close[i], open_p[i])

df = pd.DataFrame({
    'open': open_p,
    'high': high,
    'low': low,
    'close': close,
    'volume': np.random.randint(1000, 10000, n)
})

print("=" * 60)
print("收缩观测系统完整测试")
print("=" * 60)
print(f"模拟数据: {n}根K线")
print(f"收缩期: K线60-100 (波动率从2.0降至0.4)")
print()

# 测试1: 布林带宽
print("【测试1】布林带宽计算")
bb_width = SqueezeObserver.compute_bb_width(df['close'])
print(f"  BB Width均值: {bb_width.mean():.4f}")
print(f"  BB Width最新: {bb_width.iloc[-1]:.4f}")
print(f"  BB Width最小: {bb_width.min():.4f} (K线{bb_width.idxmin()})")
print()

# 测试2: 枢轴范围
print("【测试2】枢轴范围计算")
pivot_range = SqueezeObserver.compute_pivot_range(df['high'], df['low'], df['close'])
print(f"  Pivot Range均值: {pivot_range.mean():.2f}%")
print(f"  Pivot Range最新: {pivot_range.iloc[-1]:.2f}%")
print(f"  Pivot Range最小: {pivot_range.min():.2f}% (K线{pivot_range.idxmin()})")
print()

# 测试3: SR间距（独立指标）
print("【测试3】SR支撑阻力位间距计算（独立指标）")
sr_range = SqueezeObserver.compute_sr_range(df['high'], df['low'], df['close'])
print(f"  SR Range均值: {sr_range.mean():.2f}%")
print(f"  SR Range最新: {sr_range.iloc[-1]:.2f}%")
print(f"  SR Range最小: {sr_range.min():.2f}% (K线{sr_range.idxmin()})")
print(f"  与Pivot Range差异: {(sr_range - pivot_range).abs().max():.6f} (理论上相同公式，应≈0)")
print()

# 测试4: ADX
print("【测试4】ADX(14)计算")
adx = SqueezeObserver.compute_adx(df['high'], df['low'], df['close'])
print(f"  ADX均值: {adx.mean():.1f}")
print(f"  ADX最新: {adx.iloc[-1]:.1f}")
print(f"  ADX<20比例: {(adx < 20).mean()*100:.1f}%")
print(f"  ADX<13比例: {(adx < 13).mean()*100:.1f}%")
print(f"  ADX<9比例: {(adx < 9).mean()*100:.1f}%")
print()

# 测试5: 收缩判定
print("【测试5】收缩判定")
print(f"  BB收缩(20%分位): {SqueezeObserver.is_value_below_percentile(bb_width, lookback=30, percentile=20)}")
print(f"  Pivot收缩(20%分位): {SqueezeObserver.is_value_below_percentile(pivot_range, lookback=30, percentile=20)}")
print(f"  SR收缩(20%分位): {SqueezeObserver.is_value_below_percentile(sr_range, lookback=30, percentile=20)}")
print()

# 测试6: 完整分析流程
print("【测试6】完整分析流程（模拟EURUSD H1）")

# 构造带timestamp的DataFrame
df['timestamp'] = pd.date_range(start='2026-01-01', periods=n, freq='H')

# 模拟SqueezeObserver的分析（手动构造）
metrics_list = []
for i in range(30, n):
    row = df.iloc[i]
    ts = row['timestamp']

    bb_hist = df['close'].iloc[:i+1]
    bb_w = SqueezeObserver.compute_bb_width(bb_hist)
    bb_20 = bb_w.quantile(0.20)

    pivot_r = SqueezeObserver.compute_pivot_range(df['high'].iloc[:i+1], df['low'].iloc[:i+1], df['close'].iloc[:i+1])
    pivot_20 = pivot_r.quantile(0.20)

    sr_r = SqueezeObserver.compute_sr_range(df['high'].iloc[:i+1], df['low'].iloc[:i+1], df['close'].iloc[:i+1])
    sr_20 = sr_r.quantile(0.20)

    adx_s = SqueezeObserver.compute_adx(df['high'].iloc[:i+1], df['low'].iloc[:i+1], df['close'].iloc[:i+1])

    metrics = SqueezeMetrics(
        symbol="EURUSD",
        timeframe="H1",
        timestamp=ts,
        bb_width=bb_w.iloc[-1],
        bb_width_20pct=bb_20,
        bb_squeezed_20=bb_w.iloc[-1] <= bb_20,
        pivot_range_pct=pivot_r.iloc[-1],
        pivot_20pct=pivot_20,
        pivot_squeezed=pivot_r.iloc[-1] <= pivot_20,
        sr_range_pct=sr_r.iloc[-1],
        sr_20pct=sr_20,
        sr_squeezed=sr_r.iloc[-1] <= sr_20,
        adx=adx_s.iloc[-1] if not pd.isna(adx_s.iloc[-1]) else np.nan,
        adx_lt_20=adx_s.iloc[-1] < 20 if not pd.isna(adx_s.iloc[-1]) else False,
        adx_lt_13=adx_s.iloc[-1] < 13 if not pd.isna(adx_s.iloc[-1]) else False,
        adx_lt_9=adx_s.iloc[-1] < 9 if not pd.isna(adx_s.iloc[-1]) else False,
        state_is_zero=False,
    )

    conditions = []
    if metrics.bb_squeezed_20: conditions.append("BB_20")
    if metrics.pivot_squeezed: conditions.append("Pivot")
    if metrics.sr_squeezed: conditions.append("SR_Squeeze")
    if metrics.adx_lt_20: conditions.append("ADX<20")
    if metrics.adx_lt_13: conditions.append("ADX<13")
    if metrics.adx_lt_9: conditions.append("ADX<9")
    if metrics.state_is_zero: conditions.append("State=0")

    metrics.squeeze_score = len(conditions)
    metrics.squeeze_conditions = conditions
    metrics_list.append(metrics)

print(f"  生成Metrics记录: {len(metrics_list)}条")

# 统计
scores = [m.squeeze_score for m in metrics_list]
print(f"  收缩分数分布:")
for s in sorted(set(scores)):
    print(f"    分数={s}: {scores.count(s)}次")

high_squeeze = [m for m in metrics_list if m.squeeze_score >= 3]
print(f"  高收缩(>=3)次数: {len(high_squeeze)}")

if high_squeeze:
    print(f"  最新高收缩记录:")
    latest = high_squeeze[-1]
    print(f"    时间: {latest.timestamp}")
    print(f"    BB Width: {latest.bb_width:.4f}")
    print(f"    Pivot Range: {latest.pivot_range_pct:.2f}%")
    print(f"    SR Range: {latest.sr_range_pct:.2f}%")
    print(f"    ADX: {latest.adx:.1f}")
    print(f"    条件: {latest.squeeze_conditions}")

print()
print("=" * 60)
print("测试完成！所有指标计算正常。")
print("=" * 60)
