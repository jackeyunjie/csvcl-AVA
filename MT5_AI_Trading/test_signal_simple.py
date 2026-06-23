"""
简化测试：直接发送信号到 MT5 EA（不检查心跳）
"""

import zmq
import json
import time

# MT5 AVATRADE 配置
MT5_HOST = "localhost"
REQ_PORT = 5566  # 交易指令端口

# 测试信号
TEST_SIGNALS = [
    {
        "type": "fundamental_signal",
        "symbol": "GOOGL",
        "signal": "BUY",
        "score": 95,
        "reason": "PE=24.3 < 行业中位数30, 低负债, 大盘股",
        "pe": 24.3,
        "pb": 7.1,
        "source": "fundamental"
    },
    {
        "type": "fundamental_signal",
        "symbol": "META", 
        "signal": "BUY",
        "score": 85,
        "reason": "PE=23.8合理, 营收增长22%, 盈利增长35%",
        "pe": 23.8,
        "pb": 8.2,
        "source": "fundamental"
    },
    {
        "type": "fundamental_signal",
        "symbol": "NVDA",
        "signal": "REDUCE",
        "score": 50,
        "reason": "PE=62.5过高, PB=42.0过高",
        "pe": 62.5,
        "pb": 42.0,
        "source": "fundamental"
    }
]

def send_signal_direct(signal: dict) -> str:
    """直接通过 ZMQ 发送信号"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{MT5_HOST}:{REQ_PORT}")
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5秒超时
    socket.setsockopt(zmq.SNDTIMEO, 5000)
    
    try:
        # 发送
        socket.send_string(json.dumps(signal))
        
        # 接收响应
        response = socket.recv_string()
        return response
    except zmq.error.Again:
        return "[ERROR] 超时: MT5 EA 未响应"
    except Exception as e:
        return f"[ERROR] {e}"
    finally:
        socket.close()
        context.term()

print("=== MT5 EA 信号接收测试（简化版）===\n")
print(f"目标: tcp://{MT5_HOST}:{REQ_PORT}")
print("请确保 MT5 AVATRADE EA 已加载运行\n")

for i, signal in enumerate(TEST_SIGNALS, 1):
    print(f"[{i}/{len(TEST_SIGNALS)}] 发送 {signal['symbol']} -> {signal['signal']}")
    response = send_signal_direct(signal)
    print(f"  响应: {response}\n")
    time.sleep(1)

print("=== 测试完成 ===")
print("检查 MT5 EA 日志确认信号记录")
