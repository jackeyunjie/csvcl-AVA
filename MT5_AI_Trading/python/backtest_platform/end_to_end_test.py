"""
端到端整合测试

验证五层架构全流程:
数据层 → 计算层 → 策略层 → 执行层 → 报告输出

测试场景:
1. 生成模拟数据
2. 数据层: 存储到DuckDB
3. 计算层: 计算三元组 + MISS融合
4. 策略层: P107 State Hex策略生成信号
5. 执行层: 模拟撮合 + 绩效统计
6. 报告: JSON + SQX导出
"""

import os
import sys
import json
import logging
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest_platform.data_layer import DataStore, MultiTimeframeAligner
from backtest_platform.compute_layer import FeaturePipeline, StateEvolutionTracker
from backtest_platform.strategy_layer import (
    StrategyRegistry, P107StateHexStrategy, PortfolioState
)
from backtest_platform.execution_layer import (
    BacktestRunner, ReportPrinter, PerformanceReport
)
from backtest_platform.presentation_layer import ReportExporter

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def generate_test_data(symbol: str, n_days: int = 200) -> pd.DataFrame:
    """生成测试数据（确保OHLC逻辑合理，通过质量检查）"""
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=n_days, freq="B")
    base_price = 1.0850

    # 趋势 + 噪声
    trend = np.sin(np.linspace(0, 4 * np.pi, n_days)) * 0.02
    noise = np.cumsum(np.random.randn(n_days) * 0.003)
    prices = base_price + trend + noise

    # 生成合理的OHLC：确保 high >= max(open, close) >= min(open, close) >= low
    opens = prices + np.random.randn(n_days) * 0.001
    closes = prices + np.random.randn(n_days) * 0.001
    highs = np.maximum(np.maximum(opens, closes), prices + abs(np.random.randn(n_days)) * 0.005)
    lows = np.minimum(np.minimum(opens, closes), prices - abs(np.random.randn(n_days)) * 0.005)

    df = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': np.random.randint(10000, 100000, n_days),
    })

    return df


def test_end_to_end():
    """端到端测试"""
    print("=" * 70)
    print("State Hex 自主回测平台 - 端到端整合测试")
    print("=" * 70)

    symbol = "EURUSD"

    # ========================================================================
    # Step 1: 数据层 - 生成并存储数据
    # ========================================================================
    print("\n[Step 1] 数据层: 生成测试数据")
    raw_df = generate_test_data(symbol, n_days=200)
    print(f"  生成数据: {len(raw_df)}条 | {raw_df['timestamp'].iloc[0].date()} ~ {raw_df['timestamp'].iloc[-1].date()}")

    # 存储到内存数据库
    store = DataStore(":memory:")
    store.save_ohlcv(symbol, "D1", raw_df)

    # 读取并验证
    loaded_df = store.load_ohlcv(symbol, "D1")
    print(f"  存储验证: {len(loaded_df)}条 | 质量检查...")

    quality = store.get_data_quality_report(symbol, "D1")
    print(f"  数据质量: 有效={quality.is_valid} | 行数={quality.total_rows} | 异常={quality.price_anomalies}")
    store.close()

    # ========================================================================
    # Step 2: 计算层 - 计算三元组和MISS
    # ========================================================================
    print("\n[Step 2] 计算层: State Hex + MISS融合")

    pipeline = FeaturePipeline()

    # 计算最新日特征
    latest_features = pipeline.compute_daily_features(raw_df)
    print(f"  最新三元组: MN1={latest_features.triplet.mn1_hex} "
          f"W1={latest_features.triplet.w1_hex} D1={latest_features.triplet.d1_hex}")

    if latest_features.fused_state:
        print(f"  融合信心度: {latest_features.fused_state.fused_confidence:.2%}")
        print(f"  融合标签: {', '.join(latest_features.fused_state.fused_tags[:5])}")

    # 状态演化追踪
    tracker = StateEvolutionTracker()
    for i in range(len(raw_df)):
        try:
            features = pipeline.compute_for_backtest_day(raw_df, i)
            if features.triplet:
                tracker.add_triplet(features.triplet)
        except Exception:
            continue

    summary = tracker.get_current_regime_summary()
    print(f"  状态追踪: 历史{summary.get('history_length', 0)}天 | "
          f"当前D1={summary.get('d1_hex')} | 持续{summary.get('d1_duration')}天")

    # ========================================================================
    # Step 3: 策略层 - 注册策略并生成信号
    # ========================================================================
    print("\n[Step 3] 策略层: P107 State Hex策略")

    registry = StrategyRegistry()
    strategies = registry.list_strategies()
    print(f"  已注册策略: {len(strategies)}个")
    for s in strategies:
        print(f"    - {s.name}: {s.description}")

    strategy = registry.create_instance(
        "P107_StateHex_v1",
        min_confidence=0.6,
        state_alignment_mode="loose",
    )
    print(f"  策略参数: {strategy.params}")

    # 生成信号样本
    sample_signals = 0
    for i in range(50, min(100, len(raw_df))):
        features = pipeline.compute_for_backtest_day(raw_df, i)
        portfolio = PortfolioState(balance=10000, equity=10000)
        signal = strategy.on_daily_features(features, portfolio)
        if signal:
            sample_signals += 1

    print(f"  样本信号: {sample_signals}个 (第50-100天)")

    # ========================================================================
    # Step 4: 执行层 - 回测运行
    # ========================================================================
    print("\n[Step 4] 执行层: 回测运行")

    runner = BacktestRunner(
        symbol=symbol,
        initial_balance=10000.0,
        lot_size=0.1,
        spread_pips=1.0,
        commission_per_lot=5.0,
    )
    runner.set_strategy(strategy)

    report = runner.run(raw_df)

    # ========================================================================
    # Step 5: 报告输出
    # ========================================================================
    print("\n[Step 5] 报告输出")

    # 打印报告
    ReportPrinter.print_report(report)

    # JSON导出
    report_dict = ReportPrinter.to_dict(report)
    print(f"\n[JSON导出验证]")
    print(f"  字段数: {len(report_dict)}")
    print(f"  关键字段: total_return={report_dict['total_return_pct']:.2f}%, "
          f"sharpe={report_dict['sharpe_ratio']:.2f}, "
          f"trades={report_dict['total_trades']}")

    # SQX导出
    sqx_dict = ReportPrinter.export_sqx(report)
    print(f"\n[SQX导出验证]")
    print(f"  字段数: {len(sqx_dict)}")
    for key in ['NetProfit', 'ProfitFactor', 'SharpeRatio', 'MaxDrawdown', 'TotalTrades', 'WinPercent']:
        print(f"    {key}: {sqx_dict[key]}")

    # ========================================================================
    # Step 6: 展示层 - HTML报告生成
    # ========================================================================
    print("\n[Step 6] 展示层: HTML报告生成")

    exporter = ReportExporter(output_dir="reports")
    exported_paths = exporter.export_all(report, strategy_name="P107_StateHex_v1")
    for fmt, path in exported_paths.items():
        print(f"  {fmt.upper()}: {path}")

    # ========================================================================
    # 验证清单
    # ========================================================================
    print("\n" + "=" * 70)
    print("验证清单")
    print("=" * 70)

    checks = [
        ("数据层: 数据存储", len(loaded_df) > 0),
        ("数据层: 质量报告", quality.is_valid),
        ("计算层: 三元组计算", latest_features.triplet is not None),
        ("计算层: MISS融合", latest_features.fused_state is not None),
        ("计算层: 状态追踪", summary.get('history_length', 0) > 0),
        ("策略层: 策略注册", len(strategies) > 0),
        ("策略层: 信号生成", sample_signals > 0),
        ("执行层: 回测完成", report.total_trades > 0),
        ("执行层: 绩效指标", report.sharpe_ratio is not None),
        ("执行层: State-Regime", len(report.state_regime_stats) > 0),
        ("报告: JSON导出", len(report_dict) > 0),
        ("报告: SQX导出", len(sqx_dict) > 0),
        ("展示层: HTML报告", 'html' in exported_paths),
    ]

    passed = 0
    for name, result in checks:
        status = "通过" if result else "失败"
        if result:
            passed += 1
        print(f"  [{'OK' if result else 'NG'}] {name}: {status}")

    print(f"\n总计: {passed}/{len(checks)} 项通过")

    if passed == len(checks):
        print("\n所有验证通过！五层架构整合成功。")
    else:
        print(f"\n有 {len(checks) - passed} 项验证失败，请检查。")

    print("=" * 70)

    return passed == len(checks)


if __name__ == "__main__":
    success = test_end_to_end()
    sys.exit(0 if success else 1)
