"""
模拟 MT5 EA 接收端 - 验证信号格式
在没有 MT5 运行时测试 Python → EA 通信
"""

import zmq
import json
import time
import threading

MOCK_PORT = 5556  # 与 MT5 EA 相同端口


class MockMT5EA:
    """模拟 MT5 EA 的 REP Socket"""

    def __init__(self, port: int = MOCK_PORT):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.received_signals = []
        self.running = False

    def start(self):
        """启动模拟 EA"""
        self.socket.bind(f"tcp://*:{self.port}")
        self.running = True
        print(f"[MockEA] 启动，监听端口 {self.port}")

        while self.running:
            try:
                if self.socket.poll(1000):  # 1秒超时
                    msg = self.socket.recv_string(zmq.NOBLOCK)
                    print(f"\n[MockEA] 收到: {msg[:200]}")

                    # 解析信号
                    try:
                        data = json.loads(msg)
                        self.received_signals.append(data)
                        cmd_type = data.get("type", "unknown")
                        print(f"[MockEA] 类型: {cmd_type}")

                        if cmd_type == "fundamental_signal":
                            print(f"[MockEA] 基本面信号:")
                            print(f"  股票: {data.get('symbol')}")
                            print(f"  信号: {data.get('signal')}")
                            print(f"  评分: {data.get('score')}")
                            print(f"  原因: {data.get('reason')}")
                    except json.JSONDecodeError:
                        print(f"[MockEA] JSON解析失败")

                    # 发送响应
                    response = json.dumps({
                        "type": "ack",
                        "success": True,
                        "time": int(time.time() * 1000)
                    })
                    self.socket.send_string(response)

            except zmq.Again:
                continue
            except Exception as e:
                print(f"[MockEA] 错误: {e}")

    def stop(self):
        self.running = False
        self.socket.close()
        self.context.term()
        print(f"[MockEA] 停止")

    def get_signals(self):
        return self.received_signals


def test_signal_format():
    """测试信号格式"""
    print("=" * 50)
    print("模拟 MT5 EA 信号测试")
    print("=" * 50)

    # 启动模拟 EA
    mock_ea = MockMT5EA()

    # 在后台线程运行
    ea_thread = threading.Thread(target=mock_ea.start, daemon=True)
    ea_thread.start()
    time.sleep(0.5)  # 等待启动

    # 发送测试信号
    print("\n[发送方] 发送测试信号...")

    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://localhost:{MOCK_PORT}")

    # 测试1: 基本面信号
    signal = {
        "type": "fundamental_signal",
        "symbol": "GOOGL",
        "signal": "BUY",
        "score": 95,
        "reason": "低PE(24.3); PB(7.1); 低负债; 大盘股",
        "pe": 24.3,
        "pb": 7.1,
    }

    print(f"[发送方] 信号: {json.dumps(signal, ensure_ascii=False)}")
    socket.send_string(json.dumps(signal))

    # 等待响应
    if socket.poll(3000):
        response = socket.recv_string()
        print(f"[发送方] 响应: {response}")
    else:
        print("[发送方] 超时，无响应")

    # 测试2: 订单信号
    order = {
        "type": "order",
        "symbol": "AAPL",
        "action": "BUY",
        "volume": 0.01,
        "comment": "Fundamental|score=55",
    }

    print(f"\n[发送方] 订单: {json.dumps(order, ensure_ascii=False)}")
    socket.send_string(json.dumps(order))

    if socket.poll(3000):
        response = socket.recv_string()
        print(f"[发送方] 响应: {response}")

    # 关闭
    socket.close()
    context.term()

    # 输出结果
    print(f"\n{'='*50}")
    print(f"测试结果:")
    print(f"  接收信号数: {len(mock_ea.get_signals())}")

    for i, sig in enumerate(mock_ea.get_signals()):
        print(f"\n  信号 {i+1}:")
        print(f"    类型: {sig.get('type')}")
        if sig.get('type') == 'fundamental_signal':
            print(f"    股票: {sig.get('symbol')}")
            print(f"    信号: {sig.get('signal')}")
            print(f"    评分: {sig.get('score')}")

    mock_ea.stop()

    # 验证
    if len(mock_ea.get_signals()) >= 2:
        print("\n[OK] 信号格式验证通过！")
        return True
    else:
        print("\n[FAIL] 信号接收不完整")
        return False


if __name__ == "__main__":
    test_signal_format()
