"""
Dry-Run 安全测试 - 验证默认配置下不会发送真实订单
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from ai_engine.trading_strategy import TradingSignal, SignalType


class TestDryRunSafety(unittest.TestCase):
    """
    测试安全机制：
    1. live_trading=false 时不应调用 send_order
    2. dry_run=true 时只记录日志不发送订单
    3. 手数超限应拒绝订单
    4. 冷却期内应跳过交易
    """
    
    def setUp(self):
        """设置测试环境"""
        # 模拟配置（默认安全）
        self.mock_config = {
            'trading': {
                'symbol': 'EURUSD',
                'live_trading': False,      # 默认关闭
                'dry_run': True,            # 默认模拟
                'max_lot_size': 0.1,
                'signal_cooldown_seconds': 300,
                'min_confidence': 0.6
            },
            'risk': {
                'hard_max_lot_size': 0.1,
                'require_live_trading': True
            },
            'mt5': {
                'host': 'localhost',
                'pub_port': 5555,
                'req_port': 5556
            },
            'monitoring': {
                'alert_cooldown': 300,
                'risk_check_interval': 60
            }
        }
    
    @patch('core.main_controller.MT5Bridge')
    @patch('core.main_controller.TradingStrategy')
    @patch('core.main_controller.TradingMonitor')
    def test_live_trading_false_blocks_order(self, mock_monitor, mock_strategy, mock_bridge):
        """测试: live_trading=false 时不调用 send_order"""
        from core.main_controller import TradingSystem
        
        # 创建系统实例
        with patch.object(TradingSystem, '_load_config', return_value=self.mock_config):
            system = TradingSystem()
            system.bridge = Mock()
            system.bridge.send_order = Mock()
            system.monitor = Mock()
            
            # 创建模拟信号
            signal = TradingSignal(
                signal_type=SignalType.BUY,
                symbol='EURUSD',
                confidence=0.8,
                entry_price=1.0850,
                stop_loss=1.0800,
                take_profit=1.0900,
                position_size=0.05,
                reasoning='测试信号',
                timestamp=datetime.now().isoformat()
            )
            
            # 执行信号
            system._execute_signal(signal)
            
            # 验证: send_order 不应被调用
            system.bridge.send_order.assert_not_called()
            print("[PASS] live_trading=false 时未调用 send_order")
    
    @patch('core.main_controller.MT5Bridge')
    @patch('core.main_controller.TradingStrategy')
    @patch('core.main_controller.TradingMonitor')
    def test_dry_run_blocks_order(self, mock_monitor, mock_strategy, mock_bridge):
        """测试: dry_run=true 时只记录日志不发送订单"""
        from core.main_controller import TradingSystem
        
        # 修改配置: live_trading=true 但 dry_run=true
        config = self.mock_config.copy()
        config['trading'] = self.mock_config['trading'].copy()
        config['trading']['live_trading'] = True
        config['trading']['dry_run'] = True
        
        with patch.object(TradingSystem, '_load_config', return_value=config):
            system = TradingSystem()
            system.bridge = Mock()
            system.bridge.send_order = Mock()
            system.monitor = Mock()
            
            signal = TradingSignal(
                signal_type=SignalType.BUY,
                symbol='EURUSD',
                confidence=0.8,
                entry_price=1.0850,
                stop_loss=1.0800,
                take_profit=1.0900,
                position_size=0.05,
                reasoning='测试信号',
                timestamp=datetime.now().isoformat()
            )
            
            system._execute_signal(signal)
            
            # 验证: send_order 不应被调用
            system.bridge.send_order.assert_not_called()
            print("[PASS] dry_run=true 时未调用 send_order")
    
    @patch('core.main_controller.MT5Bridge')
    @patch('core.main_controller.TradingStrategy')
    @patch('core.main_controller.TradingMonitor')
    def test_max_lot_size_rejects_order(self, mock_monitor, mock_strategy, mock_bridge):
        """测试: 手数超限应拒绝订单"""
        from core.main_controller import TradingSystem
        
        # 修改配置: 允许交易但手数限制为0.01
        config = self.mock_config.copy()
        config['trading'] = self.mock_config['trading'].copy()
        config['trading']['live_trading'] = True
        config['trading']['dry_run'] = False
        config['trading']['max_lot_size'] = 0.01
        
        with patch.object(TradingSystem, '_load_config', return_value=config):
            system = TradingSystem()
            system.bridge = Mock()
            system.bridge.send_order = Mock()
            system.monitor = Mock()
            
            # 创建超手数信号 (0.05 > 0.01)
            signal = TradingSignal(
                signal_type=SignalType.BUY,
                symbol='EURUSD',
                confidence=0.8,
                entry_price=1.0850,
                stop_loss=1.0800,
                take_profit=1.0900,
                position_size=0.05,  # 超过限制
                reasoning='测试信号',
                timestamp=datetime.now().isoformat()
            )
            
            system._execute_signal(signal)
            
            # 验证: send_order 不应被调用
            system.bridge.send_order.assert_not_called()
            print("[PASS] 手数超限时拒绝订单")
    
    @patch('core.main_controller.MT5Bridge')
    @patch('core.main_controller.TradingStrategy')
    @patch('core.main_controller.TradingMonitor')
    def test_cooldown_blocks_order(self, mock_monitor, mock_strategy, mock_bridge):
        """测试: 冷却期内应跳过交易"""
        from core.main_controller import TradingSystem
        import time
        
        # 修改配置: 允许交易
        config = self.mock_config.copy()
        config['trading'] = self.mock_config['trading'].copy()
        config['trading']['live_trading'] = True
        config['trading']['dry_run'] = False
        config['trading']['signal_cooldown_seconds'] = 60  # 60秒冷却
        
        with patch.object(TradingSystem, '_load_config', return_value=config):
            system = TradingSystem()
            system.bridge = Mock()
            system.bridge.is_connected = True
            system.bridge.send_order = Mock(
                return_value=Mock(
                    success=True,
                    ticket=12345,
                    symbol='EURUSD',
                    action='BUY',
                    volume=0.05,
                    price=1.0850
                )
            )
            system.bridge.get_account_info = Mock(return_value={'equity': 10000, 'balance': 10000})
            system.monitor = Mock()
            system._is_trading_hours = Mock(return_value=True)
            
            signal = TradingSignal(
                signal_type=SignalType.BUY,
                symbol='EURUSD',
                confidence=0.8,
                entry_price=1.0850,
                stop_loss=1.0800,
                take_profit=1.0900,
                position_size=0.05,
                reasoning='测试信号',
                timestamp=datetime.now().isoformat()
            )
            
            # 第一次交易
            system._execute_signal(signal)
            self.assertEqual(system.bridge.send_order.call_count, 1)
            
            # 立即第二次交易（应在冷却期内）
            system._execute_signal(signal)
            # 仍然只调用一次
            self.assertEqual(system.bridge.send_order.call_count, 1)
            print("[PASS] 冷却期内阻止重复交易")


class TestDefaultConfigSafety(unittest.TestCase):
    """测试默认配置的安全性"""
    
    def test_default_config_has_safety(self):
        """测试: 默认配置包含安全开关"""
        from core.main_controller import TradingSystem
        
        system = TradingSystem()
        config = system.config
        
        # 检查必要配置项
        self.assertIn('live_trading', config.get('trading', {}))
        self.assertIn('dry_run', config.get('trading', {}))
        self.assertIn('max_lot_size', config.get('trading', {}))
        self.assertIn('signal_cooldown_seconds', config.get('trading', {}))
        
        # 检查默认值是否安全
        self.assertFalse(config['trading']['live_trading'])
        self.assertTrue(config['trading']['dry_run'])
        
        print("[PASS] 默认配置包含安全开关且默认安全")


if __name__ == '__main__':
    print("="*60)
    print("Dry-Run 安全测试")
    print("="*60)
    print()
    
    # 运行测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDryRunSafety))
    suite.addTests(loader.loadTestsFromTestCase(TestDefaultConfigSafety))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("="*60)
    if result.wasSuccessful():
        print("所有安全测试通过!")
    else:
        print(f"测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
    print("="*60)
