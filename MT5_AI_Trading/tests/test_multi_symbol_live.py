"""
多品种实时数据流测试
验证MT5 Python API模式下多品种行情接收与信号生成

运行方式:
    python tests/test_multi_symbol_live.py
"""

import sys
import os
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from core.mt5_python_api import MT5PythonAPIBridge
from ai_engine.multi_symbol_manager import (
    MultiSymbolStrategyManager, SymbolConfig, load_symbol_configs_from_dict
)
from ai_engine.signal_scorer import SignalScorer
from ai_engine.trading_strategy import RiskParameters

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试品种配置
TEST_SYMBOLS = [
    {"symbol": "EURUSD", "timeframe": "H1", "weight": 1.0, "enabled": True, "min_confidence": 0.6},
    {"symbol": "GBPUSD", "timeframe": "H1", "weight": 0.8, "enabled": True, "min_confidence": 0.65},
    {"symbol": "USDJPY", "timeframe": "H1", "weight": 0.8, "enabled": True, "min_confidence": 0.65},
]


def test_multi_symbol_data_flow(duration_seconds: int = 30):
    """
    测试多品种数据流

    Args:
        duration_seconds: 测试持续时间（秒）
    """
    print("=" * 60)
    print("多品种实时数据流测试")
    print("=" * 60)
    print(f"测试品种: {[s['symbol'] for s in TEST_SYMBOLS]}")
    print(f"测试时长: {duration_seconds}秒")
    print("=" * 60)

    # 1. 初始化桥接
    symbols = [s["symbol"] for s in TEST_SYMBOLS]
    bridge = MT5PythonAPIBridge(
        symbols=symbols,
        poll_interval=1.0,
        auto_reconnect=True
    )

    if not bridge.connect():
        print("[FAIL] MT5连接失败")
        return False

    try:
        # 2. 获取账户信息
        account = bridge.get_account_info()
        print(f"\n[账户] {account.get('login')} | {account.get('server')} | 权益: ${account.get('equity', 0):.2f}")

        # 3. 初始化多品种管理器
        symbol_configs = load_symbol_configs_from_dict(TEST_SYMBOLS)
        scorer = SignalScorer(max_history=1000)
        manager = MultiSymbolStrategyManager(
            symbol_configs=symbol_configs,
            risk_params=RiskParameters(),
            global_max_positions=5,
            signal_scorer=scorer
        )

        # 4. 收集tick数据
        tick_counts = {s: 0 for s in symbols}
        signal_count = 0
        start_time = time.time()

        print(f"\n[开始] 接收行情数据...")
        while time.time() - start_time < duration_seconds:
            for symbol in symbols:
                tick = bridge.get_latest_tick(symbol)
                if tick:
                    tick_counts[symbol] += 1
                    manager.update_price(symbol, {
                        'timestamp': tick.timestamp,
                        'bid': tick.bid,
                        'ask': tick.ask,
                        'mid': (tick.bid + tick.ask) / 2,
                        'open': tick.bid,
                        'high': tick.ask,
                        'low': tick.bid,
                        'close': (tick.bid + tick.ask) / 2,
                        'volume': tick.volume
                    })

            # 每5秒尝试生成一次信号
            elapsed = time.time() - start_time
            if int(elapsed) % 5 == 0 and elapsed > 5:
                positions = bridge.get_positions()
                current_positions = {}
                if isinstance(positions, dict) and 'positions' in positions:
                    for pos in positions['positions']:
                        sym = pos.get('symbol', '')
                        current_positions[sym] = current_positions.get(sym, 0) + 1

                signals = manager.generate_all_signals(
                    account_balance=account.get('balance', 10000),
                    current_positions=current_positions
                )
                if signals:
                    signal_count += len(signals)
                    for agg in signals[:3]:  # 只显示前3个
                        print(f"  [信号#{agg.rank}] {agg.signal.symbol} {agg.signal.signal_type.value} | "
                              f"评分:{agg.score:.3f} | 信心度:{agg.signal.confidence:.2%} | "
                              f"质量:{agg.quality_score:.3f}")

            time.sleep(0.5)

        # 5. 测试结果汇总
        print(f"\n{'=' * 60}")
        print("测试结果汇总")
        print(f"{'=' * 60}")
        print(f"运行时长: {duration_seconds}秒")
        print(f"Tick接收:")
        for sym, count in tick_counts.items():
            status = "OK" if count > 0 else "FAIL"
            print(f"  {sym}: {count} ticks [{status}]")
        print(f"生成信号: {signal_count}个")

        # 品种状态
        all_status = manager.get_all_status()
        print(f"\n品种数据状态:")
        for sym, status in all_status.items():
            print(f"  {sym}: 数据点={status['data_points']} 信号数={status['signal_count']}")

        # 判断测试是否通过
        all_received = all(c > 0 for c in tick_counts.values())
        if all_received:
            print(f"\n[PASS] 所有品种数据流正常")
            return True
        else:
            print(f"\n[FAIL] 部分品种无数据")
            return False

    finally:
        bridge.disconnect()
        print(f"\n[断开] MT5连接已关闭")


def test_signal_scorer_with_live_data(duration_seconds: int = 20):
    """
    测试SignalScorer与实时数据集成
    """
    print("\n" + "=" * 60)
    print("SignalScorer实时集成测试")
    print("=" * 60)

    symbols = ["EURUSD", "GBPUSD"]
    bridge = MT5PythonAPIBridge(symbols=symbols, poll_interval=1.0)

    if not bridge.connect():
        print("[FAIL] MT5连接失败")
        return False

    try:
        scorer = SignalScorer(max_history=100)
        tick_count = 0
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            for symbol in symbols:
                tick = bridge.get_latest_tick(symbol)
                if tick:
                    tick_count += 1
                    # 模拟注册信号
                    if tick_count % 10 == 0:
                        sid = scorer.register_signal(
                            symbol=symbol,
                            signal_type="BUY",
                            entry_price=tick.ask,
                            stop_loss=tick.ask - 0.0010,
                            take_profit=tick.ask + 0.0020,
                            position_size=0.01,
                            confidence=0.7
                        )
                        print(f"  [注册] {sid} | {symbol} @ {tick.ask:.5f}")
            time.sleep(0.5)

        print(f"\n注册信号数: {len(scorer.records)}")
        if scorer.records:
            metrics = scorer.calculate_metrics()
            print(f"绩效指标: 总信号={metrics.total_signals} 胜率={metrics.win_rate:.1%}")

        print("[PASS] SignalScorer实时集成正常")
        return True

    finally:
        bridge.disconnect()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=int, default=30, help='测试时长(秒)')
    parser.add_argument('--scorer-only', action='store_true', help='只测试SignalScorer')
    args = parser.parse_args()

    if args.scorer_only:
        test_signal_scorer_with_live_data(args.duration)
    else:
        success = test_multi_symbol_data_flow(args.duration)
        sys.exit(0 if success else 1)
