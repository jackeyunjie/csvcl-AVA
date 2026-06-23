"""
策略引擎测试 - 验证信号生成逻辑
"""

import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from ai_engine.trading_strategy import TradingStrategy, RiskParameters


def generate_test_data(n=200, trend='up'):
    """生成测试数据"""
    np.random.seed(42)
    
    if trend == 'up':
        prices = 1.0850 + np.cumsum(np.random.randn(n) * 0.001 + 0.0005)
    elif trend == 'down':
        prices = 1.0850 + np.cumsum(np.random.randn(n) * 0.001 - 0.0005)
    else:
        prices = 1.0850 + np.cumsum(np.random.randn(n) * 0.001)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(n) * 0.0003,
        'high': prices + abs(np.random.randn(n)) * 0.0008,
        'low': prices - abs(np.random.randn(n)) * 0.0008,
        'close': prices,
        'volume': np.random.randint(1000, 10000, n)
    })
    
    return df


def test_strategy_signals():
    """测试策略信号生成"""
    print("="*50)
    print("策略引擎测试")
    print("="*50)
    
    strategy = TradingStrategy(min_confidence=0.5)
    
    # 测试1: 上升趋势
    print("\n[测试1] 上升趋势数据...")
    df_up = generate_test_data(200, 'up')
    signal = strategy.generate_signal(df_up, "EURUSD", df_up['close'].iloc[-1], 10000)
    if signal:
        print(f"  信号: {signal.signal_type.value} | 信心度: {signal.confidence:.2%}")
        print(f"  入场: {signal.entry_price:.5f} | 止损: {signal.stop_loss:.5f} | 止盈: {signal.take_profit:.5f}")
    else:
        print("  无信号")
    
    # 测试2: 下降趋势
    print("\n[测试2] 下降趋势数据...")
    df_down = generate_test_data(200, 'down')
    signal = strategy.generate_signal(df_down, "EURUSD", df_down['close'].iloc[-1], 10000)
    if signal:
        print(f"  信号: {signal.signal_type.value} | 信心度: {signal.confidence:.2%}")
    else:
        print("  无信号")
    
    # 测试3: 风险参数
    print("\n[测试3] 风险控制...")
    risk_params = RiskParameters(
        max_risk_per_trade=0.02,
        max_positions=2,
        min_risk_reward=2.0
    )
    strategy_risk = TradingStrategy(risk_params=risk_params, min_confidence=0.5)
    
    # 超过持仓限制
    signal = strategy_risk.generate_signal(df_up, "EURUSD", df_up['close'].iloc[-1], 10000, existing_positions=3)
    if signal is None:
        print("  [OK] 持仓限制生效")
    else:
        print("  [FAIL] 持仓限制未生效")
    
    # 测试4: 指标计算
    print("\n[测试4] 技术指标计算...")
    df_with_indicators = strategy.calculate_indicators(df_up)
    required_cols = ['EMA_10', 'EMA_20', 'RSI', 'MACD', 'ATR', 'BB_Upper', 'Stoch_K']
    missing = [col for col in required_cols if col not in df_with_indicators.columns]
    if not missing:
        print(f"  [OK] 所有指标计算成功")
    else:
        print(f"  [FAIL] 缺少指标: {missing}")
    
    # 测试5: 市场状态检测
    print("\n[测试5] 市场状态检测...")
    state = strategy.detect_market_state(df_with_indicators)
    print(f"  检测到的市场状态: {state.value}")
    
    print("\n" + "="*50)
    print("策略引擎测试完成")
    print("="*50)


if __name__ == "__main__":
    test_strategy_signals()
