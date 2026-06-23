"""
MT5 ZeroMQ Bridge - Python端
功能：
1. 订阅行情数据（PUB/SUB）
2. 发送交易指令（REQ/REP）
3. 心跳检测与自动重连
4. 异步事件处理
"""

import zmq
import json
import time
import threading
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
try:
    from ai_engine.d1_risk_officer import D1RiskOfficer, latest_d1_hex_from_duckdb
except ImportError:
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep + "ai_engine")
    from d1_risk_officer import D1RiskOfficer, latest_d1_hex_from_duckdb

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TickData:
    """行情数据结构"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    time: int
    time_msc: int
    spread: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


@dataclass
class OrderResult:
    """订单结果"""
    success: bool
    ticket: int
    volume: float
    price: float
    symbol: str
    action: str
    comment: str
    error: str = None


class MT5Bridge:
    """
    MT5 ZeroMQ 桥接器 (AVATRADE 单账户)
    
    双通道架构：
    - PUB/SUB: 接收实时行情
    - REQ/REP: 发送交易指令
    
    默认端口 (AVATRADE):
    - pub_port: 5565
    - req_port: 5566
    """
    
    def __init__(
        self,
        mt5_host: str = "localhost",
        pub_port: int = 5565,
        req_port: int = 5566,
        heartbeat_interval: int = 5,
        auto_reconnect: bool = True
    ):
        self.mt5_host = mt5_host
        self.pub_port = pub_port
        self.req_port = req_port
        self.heartbeat_interval = heartbeat_interval
        self.auto_reconnect = auto_reconnect
        
        self.context = zmq.Context()
        self.sub_socket: Optional[zmq.Socket] = None
        self.req_socket: Optional[zmq.Socket] = None
        
        self._connected = False
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None
        
        # 回调函数
        self.on_tick: Optional[Callable[[TickData], None]] = None
        self.on_heartbeat: Optional[Callable[[Dict], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
        
        # 最新行情缓存
        self._latest_tick: Optional[TickData] = None
        self._tick_lock = threading.Lock()
        
        logger.info(f"MT5Bridge初始化完成 | 主机: {mt5_host}")
    
    def connect(self) -> bool:
        """连接MT5终端"""
        try:
            # 创建SUB socket接收行情
            self.sub_socket = self.context.socket(zmq.SUB)
            sub_addr = f"tcp://{self.mt5_host}:{self.pub_port}"
            self.sub_socket.connect(sub_addr)
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            self.sub_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1秒超时
            logger.info(f"SUB socket连接成功: {sub_addr}")
            
            # 创建REQ socket发送指令
            self.req_socket = self.context.socket(zmq.REQ)
            req_addr = f"tcp://{self.mt5_host}:{self.req_port}"
            self.req_socket.connect(req_addr)
            self.req_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5秒超时
            self.req_socket.setsockopt(zmq.SNDTIMEO, 5000)
            logger.info(f"REQ socket连接成功: {req_addr}")
            
            self._connected = True
            self._running = True
            
            # 启动心跳线程
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._heartbeat_thread.start()
            
            # 启动接收线程
            self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._receive_thread.start()
            
            # 测试连接
            if self._test_connection():
                logger.info("MT5连接成功，通信正常")
                return True
            else:
                logger.warning("MT5连接成功，但通信测试失败")
                return False
                
        except Exception as e:
            logger.error(f"连接MT5失败: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        self._running = False
        self._connected = False
        
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2)
        if self._receive_thread:
            self._receive_thread.join(timeout=2)
        
        if self.sub_socket:
            self.sub_socket.close()
        if self.req_socket:
            self.req_socket.close()
        
        logger.info("MT5连接已断开")
    
    def _test_connection(self) -> bool:
        """测试连接"""
        try:
            response = self.send_command({"type": "ping"})
            return response.get("type") == "pong"
        except:
            return False
    
    def _heartbeat_loop(self):
        """心跳检测循环"""
        last_heartbeat = time.time()
        
        while self._running:
            try:
                if time.time() - last_heartbeat >= self.heartbeat_interval:
                    response = self.send_command({"type": "ping"})
                    if response.get("type") == "pong":
                        last_heartbeat = time.time()
                        if self.on_heartbeat:
                            self.on_heartbeat(response)
                    else:
                        logger.warning("心跳检测失败")
                        if self.auto_reconnect:
                            self._try_reconnect()
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"心跳检测异常: {e}")
                if self.auto_reconnect:
                    self._try_reconnect()
    
    def _receive_loop(self):
        """行情接收循环"""
        while self._running:
            try:
                if self.sub_socket and self._connected:
                    msg = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                    data = json.loads(msg)
                    
                    if data.get("type") == "tick":
                        tick = TickData(
                            symbol=data["symbol"],
                            bid=data["bid"],
                            ask=data["ask"],
                            last=data.get("last", 0),
                            volume=data.get("volume", 0),
                            time=data["time"],
                            time_msc=data.get("time_msc", 0),
                            spread=data.get("spread", 0)
                        )
                        
                        with self._tick_lock:
                            self._latest_tick = tick
                        
                        if self.on_tick:
                            self.on_tick(tick)
                    
                    elif data.get("type") == "heartbeat":
                        if self.on_heartbeat:
                            self.on_heartbeat(data)
                            
            except zmq.Again:
                time.sleep(0.001)  # 1ms避免CPU占用过高
            except Exception as e:
                logger.error(f"接收行情异常: {e}")
                time.sleep(1)
    
    def _try_reconnect(self):
        """尝试重连"""
        logger.info("尝试重新连接MT5...")
        self._connected = False
        
        try:
            if self.sub_socket:
                self.sub_socket.close()
            if self.req_socket:
                self.req_socket.close()
            
            time.sleep(2)
            self.connect()
        except Exception as e:
            logger.error(f"重连失败: {e}")
    
    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """发送指令并等待响应"""
        if not self._connected or not self.req_socket:
            raise ConnectionError("未连接到MT5")
        
        try:
            self.req_socket.send_string(json.dumps(command))
            response = self.req_socket.recv_string()
            return json.loads(response)
        except zmq.Again:
            raise TimeoutError("指令响应超时")
        except Exception as e:
            raise ConnectionError(f"指令发送失败: {e}")
    
    def send_order(
        self,
        action: str,
        symbol: str,
        volume: float,
        sl: float = 0,
        tp: float = 0,
        comment: str = "AI_Trading"
    ) -> OrderResult:
        """
        发送交易订单
        
        Args:
            action: BUY 或 SELL
            symbol: 交易品种
            volume: 手数
            sl: 止损价格
            tp: 止盈价格
            comment: 订单注释
        """
        if isinstance(action, dict):
            payload = action
            action = payload.get("action", "")
            symbol = payload.get("symbol", symbol)
            volume = payload.get("volume", volume)
            sl = payload.get("sl", sl)
            tp = payload.get("tp", tp)
            comment = payload.get("comment", comment)

        d1_hex = latest_d1_hex_from_duckdb(symbol)
        d1_decision = D1RiskOfficer().assess(d1_hex, action, lower_timeframe="H1")
        if not d1_decision.allowed:
            return OrderResult(
                success=False,
                ticket=0,
                volume=0,
                price=0,
                symbol=symbol,
                action=action,
                comment=comment,
                error=f"D1RiskOfficer blocked: {d1_decision.reason} (d1_hex={d1_decision.d1_hex or 'N/A'})"
            )

        command = {
            "type": "order",
            "action": action,
            "symbol": symbol,
            "volume": volume,
            "sl": sl,
            "tp": tp,
            "comment": comment
        }
        
        try:
            response = self.send_command(command)
            
            if response.get("success"):
                return OrderResult(
                    success=True,
                    ticket=response["ticket"],
                    volume=response["volume"],
                    price=response["price"],
                    symbol=response["symbol"],
                    action=response["action"],
                    comment=response.get("comment", "")
                )
            else:
                return OrderResult(
                    success=False,
                    ticket=0,
                    volume=0,
                    price=0,
                    symbol=symbol,
                    action=action,
                    comment=comment,
                    error=response.get("error", "未知错误")
                )
        except Exception as e:
            return OrderResult(
                success=False,
                ticket=0,
                volume=0,
                price=0,
                symbol=symbol,
                action=action,
                comment=comment,
                error=str(e)
            )
    
    def close_position(self, ticket: int) -> Dict[str, Any]:
        """平仓"""
        return self.send_command({
            "type": "close",
            "ticket": ticket
        })
    
    def modify_position(self, ticket: int, sl: float = 0, tp: float = 0) -> Dict[str, Any]:
        """修改持仓SL/TP"""
        return self.send_command({
            "type": "modify",
            "ticket": ticket,
            "sl": sl,
            "tp": tp
        })
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        return self.send_command({"type": "info"})
    
    def get_positions(self) -> Dict[str, Any]:
        """获取持仓列表"""
        return self.send_command({"type": "positions"})
    
    def get_latest_tick(self) -> Optional[TickData]:
        """获取最新行情"""
        with self._tick_lock:
            return self._latest_tick
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


if __name__ == "__main__":
    # 测试代码
    bridge = MT5Bridge()
    
    def on_tick(tick: TickData):
        print(f"[{tick.symbol}] Bid: {tick.bid:.5f} | Ask: {tick.ask:.5f} | Spread: {tick.spread:.5f}")
    
    bridge.on_tick = on_tick
    
    if bridge.connect():
        print("连接成功，等待行情数据...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n用户中断")
        finally:
            bridge.disconnect()
    else:
        print("连接失败")
