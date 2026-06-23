"""
测试脚本：验证 Python 策略信号 → MT5 EA 接收
发送 fundamental_signal 指令，检查 EA 是否正确记录
"""

import sys
import json
import time
from pathlib import Path

# 添加项目路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "python" / "core"))

from mt5_bridge import MT5Bridge

# 测试信号
TEST_SIGNALS = [
    {
        "symbol": "GOOGL",
        "signal": "BUY",
        "score": 95,
        "reason": "PE=24.3 < 行业中位数30, 低负债, 大盘股",
        "pe": 24.3,
        "pb": 7.1,
        "source": "fundamental"
    },
    {
        "symbol": "META", 
        "signal": "BUY",
        "score": 85,
        "reason": "PE=23.8合理, 营收增长22%, 盈利增长35%",
        "pe": 23.8,
        "pb": 8.2,
        "source": "fundamental"
    },
    {
        "symbol": "NVDA",
        "signal": "REDUCE",
        "score": 50,
        "reason": "PE=62.5过高, PB=42.0过高",
        "pe": 62.5,
        "pb": 42.0,
        "source": "fundamental"
    }
]

def test_fundamental_signal():
    """测试发送基本面信号到 MT5 EA"""
    print("=== MT5 EA 信号接收测试 ===\n")
    
    # 连接 MT5 (AVATRADE 研发环境)
    print("[1] 连接 MT5 AVATRADE (端口 5565/5566)...")
    bridge = MT5Bridge(mt5_host="localhost", pub_port=5565, req_port=5566)
    
    if not bridge.connect():
        print("[ERROR] 连接失败，请确保 MT5 EA 已加载运行")
        return False
    
    print("[OK] 连接成功\n")
    
    # 发送测试信号
    print("[2] 发送测试信号...")
    for i, signal in enumerate(TEST_SIGNALS, 1):
        print(f"\n  信号 {i}/{len(TEST_SIGNALS)}: {signal['symbol']} -> {signal['signal']}")
        
        # 构建指令
        cmd = {
            "type": "fundamental_signal",
            **signal
        }
        
        # 发送
        try:
            response = bridge.send_command(cmd)
            print(f"  [OK] 发送成功")
            print(f"  响应: {response}")
        except Exception as e:
            print(f"  [ERROR] 发送失败: {e}")
    
    # 断开连接
    bridge.disconnect()
    print("\n[3] 断开连接")
    
    print("\n=== 测试完成 ===")
    print("请检查 MT5 EA 的日志文件，确认信号已记录")
    print("日志路径: MQL5/Files/FundamentalSignals_*.csv")
    
    return True

if __name__ == "__main__":
    test_fundamental_signal()
