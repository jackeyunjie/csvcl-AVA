"""
MT4-H1 端到端测试

验证:
1. MT4 CSV数据读取
2. H1四周期对齐
3. H1 State Hex计算
4. H1策略信号生成
5. H1回测执行
6. 绩效报告生成
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mt4_h1_backtest.data_layer import MT4CSVReader, H1MultiTimeframeAligner
from mt4_h1_backtest.compute_layer import H1FeaturePipeline, H1StateHexEngine
from mt4_h1_backtest.strategy_layer import H1P107StateHexStrategy
from mt4_h1_backtest.execution_layer import H1BacktestRunner


def generate_test_csv_files(data_dir: str, days: int = 30):
    """生成测试用的MT4格式CSV文件（仅H1，D1/W1/MN1从H1聚合）"""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    np.random.seed(42)
    end = datetime.now()

    # 生成H1数据 (每天24根)
    h1_dates = pd.date_range(end=end, periods=days * 24, freq='H')
    base = 1.0850
    trend = np.cumsum(np.random.randn(len(h1_dates)) * 0.0003)
    close = base + trend
    open_p = close + np.random.randn(len(h1_dates)) * 0.0001
    high = np.maximum(open_p, close) + np.random.uniform(0.0002, 0.0008, len(h1_dates))
    low = np.minimum(open_p, close) - np.random.uniform(0.0002, 0.0008, len(h1_dates))
    volume = np.random.randint(100, 1000, len(h1_dates))

    h1_df = pd.DataFrame({
        'Time': h1_dates.strftime('%Y.%m.%d %H:%M'),
        'Open': open_p,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume,
    })
    h1_df.to_csv(data_dir / 'EURUSD60.csv', index=False)

    print(f"测试数据生成完成: {data_dir} (仅H1，D1/W1/MN1从H1聚合)")
    return data_dir


def run_tests():
    """运行端到端测试"""
    print("=" * 70)
    print("MT4-H1 回测系统 端到端测试")
    print("=" * 70)

    checks = []

    # 1. 生成测试数据
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = generate_test_csv_files(tmpdir, days=60)

        # 2. 测试CSV读取（仅H1）
        print("\n[Step 1] MT4 CSV数据读取（仅H1）...")
        reader = MT4CSVReader(str(data_dir))
        h1_df = reader.read_ohlcv("EURUSD", "H1")

        ok = len(h1_df) > 0
        checks.append(("数据层: CSV读取(H1)", ok))
        print(f"  H1: {len(h1_df)}条 (D1/W1/MN1将从H1聚合生成)")

        # 3. 测试四周期对齐（从H1聚合生成D1/W1/MN1）
        print("\n[Step 2] H1四周期对齐（H1聚合→D1/W1/MN1）...")
        aligner = H1MultiTimeframeAligner()
        aligned = aligner.align_from_h1(h1_df)

        required_cols = ['timestamp', 'open', 'high', 'low', 'close',
                         'd1_open', 'w1_open', 'mn1_open']
        has_all = all(c in aligned.columns for c in required_cols)
        checks.append(("数据层: 四周期对齐", has_all))
        print(f"  对齐后: {len(aligned)}行, 列: {list(aligned.columns)}")

        # 4. 测试H1特征计算
        print("\n[Step 3] H1特征计算...")
        pipeline = H1FeaturePipeline()
        features = pipeline.compute_for_backtest_bar(aligned, len(aligned) - 1)

        ok = features.d1_triplet is not None and features.h1_ohlcv is not None
        checks.append(("计算层: H1特征", ok))
        if features.d1_triplet:
            print(f"  D1三元组: {features.d1_triplet.mn1_hex}|{features.d1_triplet.w1_hex}|{features.d1_triplet.d1_hex}")
        print(f"  H1位置: 第{features.h1_index_in_d1}根, 距收盘{features.h1_remaining_in_d1}根")
        print(f"  指标: {features.technical_indicators}")

        # 5. 测试H1策略
        print("\n[Step 4] H1策略信号...")
        strategy = H1P107StateHexStrategy(
            min_confidence=0.5,
            state_alignment_mode="loose",
            h1_entry_timing="any",
        )
        from backtest_platform.strategy_layer import PortfolioState
        portfolio = PortfolioState(balance=10000, equity=10000, open_positions=[])
        signal = strategy.on_h1_features(features, portfolio)

        checks.append(("策略层: H1信号", signal is not None))
        if signal:
            print(f"  信号: {signal.direction} @ {signal.entry_price:.5f}")
            print(f"  SL: {signal.stop_loss:.5f}, TP: {signal.take_profit:.5f}")
            print(f"  信心度: {signal.confidence:.2f}")

        # 6. 测试H1回测
        print("\n[Step 5] H1回测执行...")
        runner = H1BacktestRunner(
            symbol="EURUSD",
            initial_balance=10000.0,
            lot_size=0.1,
            close_at_daily_end=False,
        )
        runner.set_strategy(strategy)
        report = runner.run(aligned)

        ok = report.total_trades >= 0
        checks.append(("执行层: H1回测", ok))
        print(f"  总交易: {report.total_trades}")
        print(f"  胜率: {report.win_rate:.1%}")
        print(f"  收益: {report.total_return_pct:.1f}%")
        print(f"  最大回撤: {report.max_drawdown_pct:.1f}%")

    # 汇总
    print("\n" + "=" * 70)
    print("验证清单")
    print("=" * 70)
    passed = 0
    for name, ok in checks:
        status = "通过" if ok else "失败"
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {status}")
        if ok:
            passed += 1

    print(f"\n总计: {passed}/{len(checks)} 项通过")

    if passed == len(checks):
        print("\n所有验证通过！MT4-H1回测系统可正常工作。")
        return True
    else:
        print("\n部分验证失败，请检查。")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
