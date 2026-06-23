"""
通信测试脚本 - 验证 ZMQ 通信格式和端口
无需启动 MT5，模拟 EA 和 Python 之间的通信
"""

import sys
import os
import json
import time
import zmq
import threading
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from core.mt5_bridge import MT5Bridge, TickData


class MockMT5Server:
    """
    模拟 MT5 EA 的 ZMQ 服务端
    
    功能：
    1. PUB 端口发布模拟 Tick 数据
    2. REP 端口接收并响应交易指令
    """
    
    def __init__(self, pub_port=5555, req_port=5556):
        self.pub_port = pub_port
        self.req_port = req_port
        self.context = zmq.Context()
        self.pub_socket = None
        self.rep_socket = None
        self.running = False
        self.received_commands = []
        
    def start(self):
        """启动模拟服务器"""
        # PUB socket - 发布行情
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{self.pub_port}")
        
        # REP socket - 接收指令
        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(f"tcp://*:{self.req_port}")
        
        self.running = True
        print(f"[MockMT5] 服务器启动")
        print(f"[MockMT5] PUB端口: {self.pub_port} | REP端口: {self.req_port}")
        
        # 启动行情发布线程
        tick_thread = threading.Thread(target=self._publish_ticks, daemon=True)
        tick_thread.start()
        
        # 启动指令接收线程
        cmd_thread = threading.Thread(target=self._receive_commands, daemon=True)
        cmd_thread.start()
        
    def stop(self):
        """停止服务器"""
        self.running = False
        if self.pub_socket:
            self.pub_socket.close()
        if self.rep_socket:
            self.rep_socket.close()
        self.context.term()
        print("[MockMT5] 服务器已停止")
        
    def _publish_ticks(self):
        """发布模拟 Tick 数据"""
        base_price = 1.08500
        tick_count = 0
        
        while self.running and tick_count < 100:
            # 模拟价格波动
            price_change = (tick_count % 10 - 5) * 0.0001
            bid = base_price + price_change
            ask = bid + 0.0002
            
            tick = {
                "type": "tick",
                "symbol": "EURUSD",
                "bid": round(bid, 5),
                "ask": round(ask, 5),
                "last": round(bid, 5),
                "volume": 100 + tick_count,
                "time": int(time.time()),
                "time_msc": 0,
                "spread": 0.0002
            }
            
            self.pub_socket.send_string(json.dumps(tick))
            tick_count += 1
            time.sleep(0.1)  # 100ms 一个tick
            
    def _receive_commands(self):
        """接收并响应交易指令"""
        while self.running:
            try:
                self.rep_socket.setsockopt(zmq.RCVTIMEO, 1000)
                msg = self.rep_socket.recv_string()
                command = json.loads(msg)
                self.received_commands.append(command)
                
                print(f"[MockMT5] 收到指令: {command}")
                
                # 根据指令类型响应
                cmd_type = command.get('type', '')
                
                if cmd_type == 'ping':
                    response = {"type": "pong", "time": int(time.time())}
                elif cmd_type == 'order':
                    # 模拟订单执行（dry-run模式下不应收到）
                    response = {
                        "type": "order_result",
                        "success": True,
                        "ticket": 12345,
                        "volume": command.get('volume', 0),
                        "price": 1.08500,
                        "symbol": command.get('symbol', ''),
                        "action": command.get('action', ''),
                        "comment": command.get('comment', '')
                    }
                elif cmd_type == 'info':
                    response = {
                        "type": "account_info",
                        "balance": 10000.00,
                        "equity": 10000.00,
                        "margin": 0.00,
                        "free_margin": 10000.00,
                        "margin_level": 0.00,
                        "profit": 0.00,
                        "currency": "USD"
                    }
                elif cmd_type == 'positions':
                    response = {
                        "type": "positions",
                        "count": 0,
                        "positions": []
                    }
                else:
                    response = {"type": "error", "success": False, "error": "未知指令"}
                
                self.rep_socket.send_string(json.dumps(response))
                
            except zmq.Again:
                continue
            except Exception as e:
                print(f"[MockMT5] 处理指令异常: {e}")
                

def test_zmq_ports():
    """测试 ZMQ 端口是否可用"""
    print("="*60)
    print("测试1: ZMQ 端口可用性")
    print("="*60)
    
    try:
        context = zmq.Context()
        
        # 测试 PUB 端口
        pub_test = context.socket(zmq.PUB)
        pub_test.bind("tcp://*:5555")
        print("[OK] PUB端口 5555 可用")
        pub_test.close()
        
        # 测试 REP 端口
        rep_test = context.socket(zmq.REP)
        rep_test.bind("tcp://*:5556")
        print("[OK] REP端口 5556 可用")
        rep_test.close()
        
        context.term()
        return True
        
    except Exception as e:
        print(f"[FAIL] 端口测试失败: {e}")
        return False


def test_tick_reception():
    """测试行情数据接收"""
    print("\n" + "="*60)
    print("测试2: 行情数据接收")
    print("="*60)
    
    # 启动模拟服务器
    server = MockMT5Server(pub_port=5555, req_port=5556)
    server.start()
    
    # 给服务器启动时间
    time.sleep(0.5)
    
    # 启动客户端
    bridge = MT5Bridge(mt5_host="localhost", pub_port=5555, req_port=5556)
    
    received_ticks = []
    
    def on_tick(tick):
        received_ticks.append(tick)
        if len(received_ticks) <= 3:
            print(f"[Client] 收到Tick: {tick.symbol} | Bid: {tick.bid:.5f} | Ask: {tick.ask:.5f}")
    
    bridge.on_tick = on_tick
    
    if bridge.connect():
        print("[OK] 客户端连接成功")
        
        # 等待接收一些tick
        time.sleep(2)
        
        print(f"[OK] 共接收 {len(received_ticks)} 个Tick")
        
        if len(received_ticks) > 0:
            print("[PASS] 行情数据接收正常")
        else:
            print("[FAIL] 未收到行情数据")
        
        bridge.disconnect()
    else:
        print("[FAIL] 客户端连接失败")
    
    server.stop()
    return len(received_ticks) > 0


def test_command_format():
    """测试指令格式兼容性"""
    print("\n" + "="*60)
    print("测试3: 指令格式兼容性")
    print("="*60)
    
    server = MockMT5Server(pub_port=5555, req_port=5556)
    server.start()
    time.sleep(0.5)
    
    bridge = MT5Bridge(mt5_host="localhost", pub_port=5555, req_port=5556)
    
    if bridge.connect():
        # 测试 ping
        response = bridge.send_command({"type": "ping"})
        assert response.get("type") == "pong", "ping响应格式错误"
        print("[OK] ping/pong 正常")
        
        # 测试 account_info
        response = bridge.get_account_info()
        assert "balance" in response, "account_info格式错误"
        print("[OK] account_info 正常")
        
        # 测试 positions
        response = bridge.get_positions()
        assert "count" in response, "positions格式错误"
        print("[OK] positions 正常")
        
        # 测试 order（dry-run模式下不应真实发送）
        result = bridge.send_order("BUY", "EURUSD", 0.01, 1.08, 1.09)
        print(f"[OK] send_order 返回: success={result.success}")
        
        bridge.disconnect()
        
        # 检查服务器收到的指令
        if server.received_commands:
            print(f"[OK] 服务器共收到 {len(server.received_commands)} 条指令:")
            for cmd in server.received_commands:
                print(f"       - {cmd['type']}")
        
        print("[PASS] 指令格式兼容性正常")
        success = True
    else:
        print("[FAIL] 连接失败")
        success = False
    
    server.stop()
    return success


def test_dry_run_no_real_orders():
    """测试 dry-run 模式下不会发送真实订单"""
    print("\n" + "="*60)
    print("测试4: Dry-Run 安全验证")
    print("="*60)
    
    server = MockMT5Server(pub_port=5555, req_port=5556)
    server.start()
    time.sleep(0.5)
    
    # 导入主控制器
    from core.main_controller import TradingSystem
    from unittest.mock import patch
    
    # 使用安全配置（dry_run=true）
    config = {
        'trading': {
            'symbol': 'EURUSD',
            'live_trading': False,
            'dry_run': True,
            'max_lot_size': 0.1,
            'signal_cooldown_seconds': 300,
            'min_confidence': 0.6
        },
        'risk': {
            'hard_max_lot_size': 0.1,
            'max_drawdown': 0.10
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
    
    with patch.object(TradingSystem, '_load_config', return_value=config):
        system = TradingSystem()
        system.bridge = bridge = MT5Bridge(mt5_host="localhost", pub_port=5555, req_port=5556)
        
        if bridge.connect():
            print("[OK] 系统连接成功")
            
            # 模拟生成信号并执行
            from ai_engine.trading_strategy import TradingSignal, SignalType
            
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
            
            # 执行信号（dry-run模式下不应发送真实订单）
            system._execute_signal(signal)
            
            # 检查服务器是否收到订单指令
            order_commands = [cmd for cmd in server.received_commands if cmd.get('type') == 'order']
            
            if len(order_commands) == 0:
                print("[PASS] Dry-Run模式下未发送真实订单")
                success = True
            else:
                print(f"[FAIL] Dry-Run模式下收到了 {len(order_commands)} 个订单指令")
                success = False
            
            bridge.disconnect()
        else:
            print("[FAIL] 连接失败")
            success = False
    
    server.stop()
    return success


if __name__ == "__main__":
    print("\n" + "="*60)
    print("MT5 AI 交易系统 - 通信测试")
    print("="*60)
    print("\n注意: 本测试不需要启动 MT5，使用模拟服务器验证通信格式\n")
    
    results = []
    
    # 测试1: 端口可用性
    results.append(("ZMQ端口", test_zmq_ports()))
    
    # 测试2: 行情接收
    results.append(("行情接收", test_tick_reception()))
    
    # 测试3: 指令格式
    results.append(("指令格式", test_command_format()))
    
    # 测试4: Dry-Run安全
    results.append(("Dry-Run安全", test_dry_run_no_real_orders()))
    
    # 汇总
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    
    for name, result in results:
        status = "通过" if result else "失败"
        print(f"  [{status}] {name}")
    
    all_passed = all(r for _, r in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("所有通信测试通过！")
        print("系统可以进入 MT5 编译验证阶段")
    else:
        print("部分测试失败，请检查后再继续")
    print("="*60)
