"""
多品种策略管理器与信号评分系统测试
Phase 2 完整测试覆盖
"""

import sys
import os
import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from ai_engine.multi_symbol_manager import (
    MultiSymbolStrategyManager, SymbolConfig, AggregatedSignal,
    load_symbol_configs_from_dict
)
from ai_engine.signal_scorer import (
    SignalScorer, SignalRecord, SignalOutcome, PerformanceMetrics
)
from ai_engine.trading_strategy import TradingSignal, SignalType, RiskParameters


class TestSymbolConfigLoading(unittest.TestCase):
    """测试品种配置加载"""

    def test_load_from_dict(self):
        """测试从字典加载配置"""
        config_list = [
            {"symbol": "EURUSD", "timeframe": "H1", "weight": 1.0, "enabled": True},
            {"symbol": "GBPUSD", "timeframe": "H4", "weight": 0.8, "enabled": False},
            {"symbol": "USDJPY", "weight": 0.5},
        ]
        configs = load_symbol_configs_from_dict(config_list)

        self.assertEqual(len(configs), 3)
        self.assertEqual(configs[0].symbol, "EURUSD")
        self.assertEqual(configs[0].timeframe, "H1")
        self.assertEqual(configs[0].weight, 1.0)
        self.assertTrue(configs[0].enabled)

        self.assertEqual(configs[1].symbol, "GBPUSD")
        self.assertFalse(configs[1].enabled)

        self.assertEqual(configs[2].symbol, "USDJPY")
        self.assertEqual(configs[2].min_confidence, 0.6)  # 默认值
        print("[PASS] 配置加载正确")

    def test_load_empty_list(self):
        """测试空列表"""
        configs = load_symbol_configs_from_dict([])
        self.assertEqual(len(configs), 0)
        print("[PASS] 空列表处理正确")


class TestMultiSymbolManager(unittest.TestCase):
    """测试多品种策略管理器"""

    def setUp(self):
        """设置测试环境"""
        self.configs = [
            SymbolConfig(symbol="EURUSD", timeframe="H1", weight=1.0, enabled=True),
            SymbolConfig(symbol="GBPUSD", timeframe="H1", weight=0.8, enabled=True),
            SymbolConfig(symbol="USDJPY", timeframe="H1", weight=0.8, enabled=True),
        ]
        self.manager = MultiSymbolStrategyManager(
            symbol_configs=self.configs,
            risk_params=RiskParameters(),
            global_max_positions=5
        )

    def _generate_price_data(self, symbol: str, n: int = 100) -> list:
        """生成模拟价格数据"""
        np.random.seed(42)
        base_price = {"EURUSD": 1.0850, "GBPUSD": 1.2650, "USDJPY": 149.50}.get(symbol, 1.0)
        prices = base_price + np.cumsum(np.random.randn(n) * 0.001)

        data = []
        for i in range(n):
            price = prices[i]
            data.append({
                'timestamp': datetime.now() - timedelta(minutes=n-i),
                'bid': price - 0.0001,
                'ask': price + 0.0001,
                'mid': price,
                'open': price + np.random.randn() * 0.0005,
                'high': price + abs(np.random.randn()) * 0.001,
                'low': price - abs(np.random.randn()) * 0.001,
                'close': price,
                'volume': np.random.randint(1000, 10000)
            })
        return data

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(len(self.manager.strategies), 3)
        self.assertIn("EURUSD", self.manager.strategies)
        self.assertIn("GBPUSD", self.manager.strategies)
        self.assertIn("USDJPY", self.manager.strategies)
        print("[PASS] 多品种管理器初始化正确")

    def test_disabled_symbol_not_initialized(self):
        """测试禁用品种不初始化策略"""
        configs = [
            SymbolConfig(symbol="EURUSD", enabled=True),
            SymbolConfig(symbol="GBPUSD", enabled=False),
        ]
        manager = MultiSymbolStrategyManager(symbol_configs=configs)
        self.assertIn("EURUSD", manager.strategies)
        self.assertNotIn("GBPUSD", manager.strategies)
        print("[PASS] 禁用品种未初始化策略")

    def test_update_price(self):
        """测试价格更新"""
        data = self._generate_price_data("EURUSD", 50)
        for tick in data:
            self.manager.update_price("EURUSD", tick)

        self.assertEqual(len(self.manager.price_history["EURUSD"]), 50)
        print("[PASS] 价格更新正确")

    def test_update_price_ignores_disabled(self):
        """测试禁用品种价格被忽略"""
        manager = MultiSymbolStrategyManager([
            SymbolConfig(symbol="EURUSD", enabled=True),
            SymbolConfig(symbol="GBPUSD", enabled=False),
        ])
        manager.update_price("GBPUSD", {'bid': 1.0, 'ask': 1.01})
        self.assertEqual(len(manager.price_history["GBPUSD"]), 0)
        print("[PASS] 禁用品种价格被忽略")

    def test_generate_signals(self):
        """测试信号生成"""
        for cfg in self.configs:
            data = self._generate_price_data(cfg.symbol, 100)
            for tick in data:
                self.manager.update_price(cfg.symbol, tick)

        signals = self.manager.generate_all_signals(
            account_balance=10000,
            current_positions={}
        )

        self.assertIsInstance(signals, list)
        print(f"[PASS] 信号生成成功 | 生成{len(signals)}个信号")

    def test_global_position_limit(self):
        """测试全局持仓限制"""
        current_positions = {"EURUSD": 2, "GBPUSD": 2, "USDJPY": 1}

        mock_signals = [
            AggregatedSignal(
                signal=TradingSignal(
                    signal_type=SignalType.BUY,
                    symbol="EURUSD",
                    confidence=0.8,
                    entry_price=1.0850,
                    stop_loss=1.0800,
                    take_profit=1.0900,
                    position_size=0.1,
                    reasoning="测试",
                    timestamp=datetime.now().isoformat()
                ),
                symbol_config=self.configs[0],
                score=0.9
            )
        ]

        filtered = self.manager.check_global_position_limit(current_positions, mock_signals)
        self.assertEqual(len(filtered), 0)
        print("[PASS] 全局持仓限制生效")

    def test_global_position_limit_partial(self):
        """测试全局持仓限制部分通过"""
        current_positions = {"EURUSD": 1, "GBPUSD": 1}  # 总持仓2，限制5

        mock_signals = [
            AggregatedSignal(
                signal=TradingSignal(
                    signal_type=SignalType.BUY,
                    symbol="EURUSD",
                    confidence=0.8,
                    entry_price=1.0850,
                    stop_loss=1.0800,
                    take_profit=1.0900,
                    position_size=0.1,
                    reasoning="测试",
                    timestamp=datetime.now().isoformat()
                ),
                symbol_config=self.configs[0],
                score=0.9
            ),
            AggregatedSignal(
                signal=TradingSignal(
                    signal_type=SignalType.BUY,
                    symbol="GBPUSD",
                    confidence=0.7,
                    entry_price=1.2650,
                    stop_loss=1.2600,
                    take_profit=1.2700,
                    position_size=0.1,
                    reasoning="测试2",
                    timestamp=datetime.now().isoformat()
                ),
                symbol_config=self.configs[1],
                score=0.8
            ),
            AggregatedSignal(
                signal=TradingSignal(
                    signal_type=SignalType.BUY,
                    symbol="USDJPY",
                    confidence=0.6,
                    entry_price=149.50,
                    stop_loss=149.00,
                    take_profit=150.00,
                    position_size=0.1,
                    reasoning="测试3",
                    timestamp=datetime.now().isoformat()
                ),
                symbol_config=self.configs[2],
                score=0.7
            )
        ]

        filtered = self.manager.check_global_position_limit(current_positions, mock_signals)
        self.assertEqual(len(filtered), 3)  # 可用3个槽位
        print("[PASS] 全局持仓限制部分通过")

    def test_symbol_weight_applied(self):
        """测试品种权重应用"""
        for cfg in self.configs[:2]:
            data = self._generate_price_data(cfg.symbol, 100)
            for tick in data:
                self.manager.update_price(cfg.symbol, tick)

        signals = self.manager.generate_all_signals(
            account_balance=10000,
            current_positions={}
        )

        for agg in signals:
            if agg.signal.symbol == "EURUSD":
                self.assertGreaterEqual(agg.signal.position_size, 0)
            elif agg.signal.symbol == "GBPUSD":
                self.assertLessEqual(agg.signal.position_size, 0.1 * 0.8 + 0.01)

        print("[PASS] 品种权重已应用")

    def test_signal_scoring_and_ranking(self):
        """测试信号评分与排序"""
        for cfg in self.configs:
            data = self._generate_price_data(cfg.symbol, 100)
            for tick in data:
                self.manager.update_price(cfg.symbol, tick)

        signals = self.manager.generate_all_signals(
            account_balance=10000,
            current_positions={}
        )

        if len(signals) >= 2:
            for i in range(len(signals) - 1):
                self.assertGreaterEqual(signals[i].score, signals[i+1].score)

            for i, agg in enumerate(signals):
                self.assertEqual(agg.rank, i + 1)

        print("[PASS] 信号评分与排序正确")

    def test_signal_scorer_integration(self):
        """测试SignalScorer集成"""
        scorer = SignalScorer(max_history=100)

        # 注册一些历史信号
        for i in range(10):
            sid = scorer.register_signal(
                symbol="EURUSD", signal_type="BUY",
                entry_price=1.0850, stop_loss=1.0800,
                take_profit=1.0900, position_size=0.1,
                confidence=0.75
            )
            outcome = SignalOutcome.WIN if i < 7 else SignalOutcome.LOSS
            profit = 100.0 if outcome == SignalOutcome.WIN else -50.0
            scorer.update_signal_outcome(
                signal_id=sid, outcome=outcome,
                profit_amount=profit
            )

        # 创建带scorer的管理器
        manager = MultiSymbolStrategyManager(
            symbol_configs=self.configs,
            risk_params=RiskParameters(),
            global_max_positions=5,
            signal_scorer=scorer
        )

        for cfg in self.configs:
            data = self._generate_price_data(cfg.symbol, 100)
            for tick in data:
                manager.update_price(cfg.symbol, tick)

        signals = manager.generate_all_signals(
            account_balance=10000,
            current_positions={}
        )

        for agg in signals:
            if agg.signal.symbol == "EURUSD":
                self.assertGreater(agg.quality_score, 0)
                self.assertLessEqual(agg.quality_score, 1.0)

        print("[PASS] SignalScorer集成正确")

    def test_get_status(self):
        """测试状态查询"""
        status = self.manager.get_symbol_status("EURUSD")
        self.assertEqual(status["symbol"], "EURUSD")
        self.assertTrue(status["enabled"])
        self.assertEqual(status["weight"], 1.0)

        all_status = self.manager.get_all_status()
        self.assertEqual(len(all_status), 3)
        print("[PASS] 状态查询正确")

    def test_price_history_limit(self):
        """测试价格历史长度限制"""
        data = self._generate_price_data("EURUSD", 600)
        for tick in data:
            self.manager.update_price("EURUSD", tick)

        self.assertLessEqual(len(self.manager.price_history["EURUSD"]), 500)
        print("[PASS] 价格历史长度限制正确")


class TestSignalScorer(unittest.TestCase):
    """测试信号评分系统"""

    def setUp(self):
        self.scorer = SignalScorer(max_history=1000)

    def test_register_signal(self):
        """测试信号注册"""
        sid = self.scorer.register_signal(
            symbol="EURUSD",
            signal_type="BUY",
            entry_price=1.0850,
            stop_loss=1.0800,
            take_profit=1.0900,
            position_size=0.1,
            confidence=0.75
        )
        self.assertIsNotNone(sid)
        self.assertIn(sid, self.scorer.records)
        print("[PASS] 信号注册成功")

    def test_register_from_trading_signal(self):
        """测试从TradingSignal注册"""
        ts = TradingSignal(
            signal_type=SignalType.SELL,
            symbol="GBPUSD",
            confidence=0.8,
            entry_price=1.2650,
            stop_loss=1.2700,
            take_profit=1.2600,
            position_size=0.15,
            reasoning="测试",
            timestamp=datetime.now().isoformat()
        )
        sid = self.scorer.register_signal_from_trading_signal(ts)
        self.assertIn(sid, self.scorer.records)
        record = self.scorer.records[sid]
        self.assertEqual(record.symbol, "GBPUSD")
        self.assertEqual(record.signal_type, "SELL")
        print("[PASS] TradingSignal注册成功")

    def test_update_outcome(self):
        """测试结果更新"""
        sid = self.scorer.register_signal(
            symbol="EURUSD", signal_type="BUY",
            entry_price=1.0850, stop_loss=1.0800,
            take_profit=1.0900, position_size=0.1, confidence=0.75
        )

        self.scorer.update_signal_outcome(
            signal_id=sid,
            outcome=SignalOutcome.WIN,
            exit_price=1.0900,
            profit_pips=50,
            profit_amount=50.0,
            holding_bars=10
        )

        record = self.scorer.records[sid]
        self.assertEqual(record.outcome, SignalOutcome.WIN)
        self.assertEqual(record.profit_amount, 50.0)
        print("[PASS] 结果更新正确")

    def test_calculate_metrics(self):
        """测试绩效指标计算"""
        outcomes = [
            (SignalOutcome.WIN, 100.0),
            (SignalOutcome.WIN, 80.0),
            (SignalOutcome.LOSS, -50.0),
            (SignalOutcome.WIN, 120.0),
            (SignalOutcome.LOSS, -60.0),
        ]

        for i, (outcome, profit) in enumerate(outcomes):
            sid = self.scorer.register_signal(
                symbol="EURUSD", signal_type="BUY",
                entry_price=1.0850, stop_loss=1.0800,
                take_profit=1.0900, position_size=0.1,
                confidence=0.7 + i * 0.02
            )
            self.scorer.update_signal_outcome(
                signal_id=sid, outcome=outcome,
                profit_amount=profit, holding_bars=5
            )

        metrics = self.scorer.calculate_metrics()
        self.assertEqual(metrics.total_signals, 5)
        self.assertEqual(metrics.winning_trades, 3)
        self.assertEqual(metrics.losing_trades, 2)
        self.assertAlmostEqual(metrics.win_rate, 0.6, places=1)
        self.assertGreater(metrics.profit_factor, 1.0)
        print(f"[PASS] 绩效指标计算正确 | 胜率: {metrics.win_rate:.1%}")

    def test_signal_quality_score(self):
        """测试信号质量评分"""
        for i in range(10):
            sid = self.scorer.register_signal(
                symbol="EURUSD", signal_type="BUY",
                entry_price=1.0850, stop_loss=1.0800,
                take_profit=1.0900, position_size=0.1,
                confidence=0.7
            )
            outcome = SignalOutcome.WIN if i < 7 else SignalOutcome.LOSS
            profit = 100.0 if outcome == SignalOutcome.WIN else -50.0
            self.scorer.update_signal_outcome(
                signal_id=sid, outcome=outcome,
                profit_amount=profit
            )

        score = self.scorer.get_signal_quality_score("EURUSD", "BUY", 0.7)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 1.0)
        print(f"[PASS] 信号质量评分: {score:.3f}")

    def test_attribution_report(self):
        """测试归因报告"""
        symbols = ["EURUSD", "GBPUSD", "EURUSD", "GBPUSD", "EURUSD"]
        for i, sym in enumerate(symbols):
            sid = self.scorer.register_signal(
                symbol=sym, signal_type="BUY",
                entry_price=1.0850, stop_loss=1.0800,
                take_profit=1.0900, position_size=0.1,
                confidence=0.75
            )
            outcome = SignalOutcome.WIN if i % 2 == 0 else SignalOutcome.LOSS
            profit = 100.0 if outcome == SignalOutcome.WIN else -40.0
            self.scorer.update_signal_outcome(
                signal_id=sid, outcome=outcome,
                profit_amount=profit
            )

        report = self.scorer.generate_attribution_report()
        self.assertIn("EURUSD", report.by_symbol)
        self.assertIn("GBPUSD", report.by_symbol)
        self.assertIn("BUY", report.by_signal_type)
        self.assertGreater(report.overall.total_signals, 0)
        print("[PASS] 归因报告生成正确")

    def test_export_report(self):
        """测试报告导出"""
        sid = self.scorer.register_signal(
            symbol="EURUSD", signal_type="BUY",
            entry_price=1.0850, stop_loss=1.0800,
            take_profit=1.0900, position_size=0.1,
            confidence=0.75
        )
        self.scorer.update_signal_outcome(
            signal_id=sid, outcome=SignalOutcome.WIN,
            profit_amount=100.0
        )

        test_path = "test_report.json"
        self.scorer.export_report(test_path)
        self.assertTrue(os.path.exists(test_path))

        os.remove(test_path)
        print("[PASS] 报告导出成功")

    def test_max_history_cleanup(self):
        """测试历史记录清理"""
        scorer = SignalScorer(max_history=5)
        for i in range(10):
            scorer.register_signal(
                symbol="EURUSD", signal_type="BUY",
                entry_price=1.0850 + i * 0.0001, stop_loss=1.0800,
                take_profit=1.0900, position_size=0.1,
                confidence=0.7
            )

        self.assertLessEqual(len(scorer.records), 5)
        print("[PASS] 历史记录清理正确")

    def test_batch_update_from_positions(self):
        """测试批量更新持仓结果"""
        # 注册pending信号
        sid1 = self.scorer.register_signal(
            symbol="EURUSD", signal_type="BUY",
            entry_price=1.0850, stop_loss=1.0800,
            take_profit=1.0900, position_size=0.1,
            confidence=0.75
        )
        sid2 = self.scorer.register_signal(
            symbol="GBPUSD", signal_type="SELL",
            entry_price=1.2650, stop_loss=1.2700,
            take_profit=1.2600, position_size=0.1,
            confidence=0.8
        )

        positions = [
            {"ticket": 1, "symbol": "EURUSD", "profit": 100.0, "price_current": 1.0900},
            {"ticket": 2, "symbol": "GBPUSD", "profit": -50.0, "price_current": 1.2700},
        ]

        updated = self.scorer.batch_update_outcomes_from_positions(positions)
        self.assertEqual(len(updated), 2)

        self.assertEqual(self.scorer.records[sid1].outcome, SignalOutcome.WIN)
        self.assertEqual(self.scorer.records[sid2].outcome, SignalOutcome.LOSS)
        print("[PASS] 批量持仓更新正确")


if __name__ == '__main__':
    print("="*60)
    print("Phase 2 多品种与信号评分系统测试")
    print("="*60)
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestSymbolConfigLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiSymbolManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSignalScorer))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("="*60)
    if result.wasSuccessful():
        print("所有 Phase 2 测试通过!")
    else:
        print(f"测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
    print("="*60)
