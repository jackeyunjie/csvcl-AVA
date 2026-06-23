"""
模块导入测试 - 验证所有组件可正常加载
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

def test_imports():
    """测试所有核心模块导入"""
    errors = []
    
    # 1. 测试核心模块
    try:
        from core.mt5_bridge import MT5Bridge, TickData
        print("[OK] core.mt5_bridge")
    except Exception as e:
        errors.append(f"core.mt5_bridge: {e}")
        print(f"[FAIL] core.mt5_bridge: {e}")

    try:
        from core.mt5_python_api import MT5PythonAPIBridge
        print("[OK] core.mt5_python_api")
    except Exception as e:
        errors.append(f"core.mt5_python_api: {e}")
        print(f"[FAIL] core.mt5_python_api: {e}")
    
    # 2. 测试策略引擎
    try:
        from ai_engine.trading_strategy import TradingStrategy, RiskParameters
        print("[OK] ai_engine.trading_strategy")
    except Exception as e:
        errors.append(f"ai_engine.trading_strategy: {e}")
        print(f"[FAIL] ai_engine.trading_strategy: {e}")
    
    # 3. 测试LLM分析器（可能缺少API key）
    try:
        from ai_engine.llm_analyzer import LLMAnalyzer
        print("[OK] ai_engine.llm_analyzer")
    except Exception as e:
        print(f"[WARN] ai_engine.llm_analyzer: {e}")
    
    # 4. 测试回测环境
    try:
        from backtest.trading_env import TradingEnv
        print("[OK] backtest.trading_env")
    except Exception as e:
        errors.append(f"backtest.trading_env: {e}")
        print(f"[FAIL] backtest.trading_env: {e}")
    
    # 5. 测试监控系统
    try:
        from monitoring.monitor import TradingMonitor
        print("[OK] monitoring.monitor")
    except Exception as e:
        errors.append(f"monitoring.monitor: {e}")
        print(f"[FAIL] monitoring.monitor: {e}")
    
    # 6. 测试主控制器
    try:
        from core.main_controller import TradingSystem
        print("[OK] core.main_controller")
    except Exception as e:
        errors.append(f"core.main_controller: {e}")
        print(f"[FAIL] core.main_controller: {e}")
    
    print("\n" + "="*50)
    if errors:
        print(f"测试结果: {len(errors)} 个模块导入失败")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("测试结果: 所有核心模块导入成功!")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
