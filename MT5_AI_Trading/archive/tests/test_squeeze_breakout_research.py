"""
收缩→突破研究模块测试

测试内容：
1. SqueezeSetup数据类创建
2. BreakoutEvent数据类创建
3. SqueezeBreakoutResearch核心逻辑（使用模拟数据）
4. 参数扫描功能验证
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import fields

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "python"))

from squeeze_breakout_research import (
    SqueezeSetup, BreakoutEvent, ResearchResult,
    SqueezeBreakoutResearch
)


class TestDataClasses(unittest.TestCase):
    """测试数据类"""
    
    def test_squeeze_setup_creation(self):
        """测试SqueezeSetup创建"""
        setup = SqueezeSetup(
            symbol="EURUSD",
            timeframe="H1",
            timestamp=datetime(2026, 1, 1, 10, 0),
            bar_idx=100,
            squeeze_score=3,
            conditions=["BB", "Pivot", "ADX<20"],
            bb_width=0.002,
            pivot_range=0.3,
            sr_range=0.3,
            adx=15.0,
            state_is_zero=False,
            open=1.1000,
            high=1.1010,
            low=1.0990,
            close=1.1005,
            anchor_high=1.1020,
            anchor_low=1.0980,
            anchor_range=0.004,
            anchor_range_pct=0.36,
            anchor_mid=1.1000
        )
        self.assertEqual(setup.symbol, "EURUSD")
        self.assertEqual(setup.squeeze_score, 3)
        self.assertEqual(len(setup.conditions), 3)
        self.assertEqual(setup.anchor_range, 0.004)
    
    def test_breakout_event_creation(self):
        """测试BreakoutEvent创建"""
        setup = SqueezeSetup(
            symbol="EURUSD", timeframe="H1",
            timestamp=datetime(2026, 1, 1, 10, 0),
            bar_idx=100, squeeze_score=3,
            conditions=["BB", "Pivot"],
            bb_width=0.002, pivot_range=0.3, sr_range=0.3,
            adx=15.0, state_is_zero=False,
            open=1.1, high=1.101, low=1.099, close=1.1005,
            anchor_high=1.102, anchor_low=1.098,
            anchor_range=0.004, anchor_range_pct=0.36,
            anchor_mid=1.100
        )
        event = BreakoutEvent(
            setup=setup,
            breakout_timestamp=datetime(2026, 1, 1, 11, 0),
            breakout_bar_idx=1,
            breakout_direction="up",
            entry_price=1.1025,
            breakout_level=1.102,
            returns_1bar=0.05,
            returns_3bar=0.10,
            returns_5bar=0.15,
            returns_10bar=0.20,
            returns_20bar=0.25,
            max_drawdown_pct=-0.02,
            max_runup_pct=0.30,
            hit_target_1r=True,
            hit_target_2r=False,
            hit_target_3r=False,
            stop_triggered=False,
            stop_bar_idx=None,
            stop_price=1.098,
            pnl_5bar=0.15,
            pnl_10bar=0.20,
            pnl_20bar=0.25
        )
        self.assertEqual(event.breakout_direction, "up")
        self.assertTrue(event.hit_target_1r)
        self.assertFalse(event.stop_triggered)
        self.assertEqual(event.pnl_5bar, 0.15)


class TestSqueezeBreakoutResearch(unittest.TestCase):
    """测试SqueezeBreakoutResearch核心逻辑"""
    
    def setUp(self):
        """创建模拟数据"""
        np.random.seed(42)
        n = 200
        
        # 生成模拟OHLCV数据
        close = 1.1000 + np.cumsum(np.random.randn(n) * 0.001)
        high = close + np.abs(np.random.randn(n)) * 0.0015
        low = close - np.abs(np.random.randn(n)) * 0.0015
        open_p = close + np.random.randn(n) * 0.0005
        
        for i in range(n):
            high[i] = max(high[i], close[i], open_p[i])
            low[i] = min(low[i], close[i], open_p[i])
        
        self.df = pd.DataFrame({
            'timestamp': pd.date_range(start='2026-01-01', periods=n, freq='h'),
            'open': open_p,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.randint(1000, 10000, n),
        })
        
        self.research = SqueezeBreakoutResearch()
        self.research.raw_data = {"EURUSD": self.df}
    
    def test_find_setups(self):
        """测试setup识别"""
        setups = self.research.find_setups(min_squeeze_score=2, cooldown_bars=5)
        
        # 应该识别到一些setup
        self.assertIsInstance(setups, list)
        self.assertGreater(len(setups), 0, "应该识别到至少一个setup")
        
        # 检查setup属性
        for setup in setups:
            self.assertIsInstance(setup, SqueezeSetup)
            self.assertEqual(setup.symbol, "EURUSD")
            self.assertGreaterEqual(setup.squeeze_score, 2)
            self.assertGreater(setup.anchor_range, 0)
            self.assertIsInstance(setup.conditions, list)
    
    def test_detect_breakouts(self):
        """测试突破检测"""
        # 先识别setup
        self.research.find_setups(min_squeeze_score=2)
        
        # 检测突破
        breakouts = self.research.detect_breakouts(max_wait_bars=20, min_breakout_atr=0.25)
        
        # breakouts可以是空列表（模拟数据可能不突破）
        self.assertIsInstance(breakouts, list)
        
        # 如果有突破，检查属性
        for bo in breakouts:
            self.assertIsInstance(bo, BreakoutEvent)
            self.assertIn(bo.breakout_direction, ["up", "down"])
            self.assertGreater(bo.breakout_bar_idx, 0)
            self.assertIsNotNone(bo.entry_price)
    
    def test_analyze(self):
        """测试分析功能"""
        self.research.find_setups(min_squeeze_score=2)
        self.research.detect_breakouts()
        
        result = self.research.analyze()
        
        if result is not None:
            self.assertIsInstance(result, ResearchResult)
            self.assertGreaterEqual(result.total_setups, 0)
            self.assertGreaterEqual(result.total_breakouts, 0)
            self.assertGreaterEqual(result.breakout_rate, 0)
            self.assertLessEqual(result.breakout_rate, 1)
            self.assertIn(result.validation_status, 
                         ["已验证有效", "样本不足", "逻辑需要调整", "暂不建议进入实盘"])
    
    def test_setup_anchor_range(self):
        """测试锚定区间计算"""
        setups = self.research.find_setups(min_squeeze_score=2)
        
        for setup in setups:
            # anchor_high >= anchor_low
            self.assertGreaterEqual(setup.anchor_high, setup.anchor_low)
            # anchor_range = high - low
            expected_range = setup.anchor_high - setup.anchor_low
            self.assertAlmostEqual(setup.anchor_range, expected_range, places=10)
            # anchor_mid = (high + low) / 2
            expected_mid = (setup.anchor_high + setup.anchor_low) / 2
            self.assertAlmostEqual(setup.anchor_mid, expected_mid, places=10)
    
    def test_breakout_direction_consistency(self):
        """测试突破方向一致性"""
        self.research.find_setups(min_squeeze_score=2)
        breakouts = self.research.detect_breakouts()
        
        for bo in breakouts:
            # 向上突破时，entry_price应高于breakout_level
            if bo.breakout_direction == "up":
                self.assertGreaterEqual(bo.entry_price, bo.breakout_level)
            # 向下突破时，entry_price应低于breakout_level
            elif bo.breakout_direction == "down":
                self.assertLessEqual(bo.entry_price, bo.breakout_level)
    
    def test_pnl_calculation(self):
        """测试PNL计算"""
        self.research.find_setups(min_squeeze_score=2)
        breakouts = self.research.detect_breakouts()
        
        for bo in breakouts:
            # PNL应与returns一致（考虑方向）
            if bo.breakout_direction == "up":
                self.assertAlmostEqual(bo.pnl_5bar, bo.returns_5bar, places=10)
            else:
                self.assertAlmostEqual(bo.pnl_5bar, -bo.returns_5bar, places=10)


class TestEdgeCases(unittest.TestCase):
    """测试边界情况"""
    
    def test_empty_data(self):
        """测试空数据"""
        research = SqueezeBreakoutResearch()
        research.raw_data = {}
        
        setups = research.find_setups()
        self.assertEqual(len(setups), 0)
    
    def test_insufficient_data(self):
        """测试数据不足"""
        research = SqueezeBreakoutResearch()
        # 只有20条数据，不足以计算指标
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2026-01-01', periods=20, freq='h'),
            'open': np.ones(20),
            'high': np.ones(20) * 1.001,
            'low': np.ones(20) * 0.999,
            'close': np.ones(20),
            'volume': np.ones(20) * 1000,
        })
        research.raw_data = {"EURUSD": df}
        
        setups = research.find_setups()
        self.assertEqual(len(setups), 0)
    
    def test_no_breakout(self):
        """测试无突破情况"""
        # 生成几乎没有波动的数据
        research = SqueezeBreakoutResearch()
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2026-01-01', periods=100, freq='h'),
            'open': np.ones(100) * 1.1,
            'high': np.ones(100) * 1.1001,
            'low': np.ones(100) * 1.0999,
            'close': np.ones(100) * 1.1,
            'volume': np.ones(100) * 1000,
        })
        research.raw_data = {"EURUSD": df}
        
        research.find_setups(min_squeeze_score=2)
        breakouts = research.detect_breakouts(max_wait_bars=5, min_breakout_atr=0.5)
        
        # 突破阈值很高，应该没有突破
        self.assertEqual(len(breakouts), 0)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDataClasses))
    suite.addTests(loader.loadTestsFromTestCase(TestSqueezeBreakoutResearch))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
