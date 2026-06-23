"""
AVATRADE MT5 ZeroMQ Bridge - Python端
管理AVATRADE MT5终端的连接：
- 实盘/模拟盘执行
- 回测+策略验证
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
    source: str = ""  # 来源标识: AVATRADE
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
    source: str = ""  # 来源标识
    error: str = None


class MT5Bridge:
    """单个MT5桥接器 (AVATRADE 默认端口)"""
    
    def __init__(
        self,
        mt5_host: str = "localhost",
        pub_port: int = 5565,
        req_port: int = 5566,
        heartbeat_interval: int = 5,
        auto_reconnect: bool = True,
        label: str = "MT5"
    ):
        self.mt5_host = mt5_host
        self.pub_port = pub_port
        self.req_port = req_port
        self.heartbeat_interval = heartbeat_interval
        self.auto_reconnect = auto_reconnect
        self.label = label
        
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
        
        logger.info(f"[{label}] MT5Bridge初始化完成 | 主机: {mt5_host}")
    
    def connect(self) -> bool:
        """连接MT5终端"""
        try:
            # 创建SUB socket接收行情
            self.sub_socket = self.context.socket(zmq.SUB)
            sub_addr = f"tcp://{self.mt5_host}:{self.pub_port}"
            self.sub_socket.connect(sub_addr)
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            self.sub_socket.setsockopt(zmq.RCVTIMEO, 1000)
            logger.info(f"[{self.label}] SUB socket连接成功: {sub_addr}")
            
            # 创建REQ socket发送指令
            self.req_socket = self.context.socket(zmq.REQ)
            req_addr = f"tcp://{self.mt5_host}:{self.req_port}"
            self.req_socket.connect(req_addr)
            self.req_socket.setsockopt(zmq.RCVTIMEO, 5000)
            self.req_socket.setsockopt(zmq.SNDTIMEO, 5000)
            logger.info(f"[{self.label}] REQ socket连接成功: {req_addr}")
            
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
                logger.info(f"[{self.label}] MT5连接成功，通信正常")
                return True
            else:
                logger.warning(f"[{self.label}] MT5连接成功，但通信测试失败")
                return False
                
        except Exception as e:
            logger.error(f"[{self.label}] 连接MT5失败: {e}")
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
        
        logger.info(f"[{self.label}] MT5连接已断开")
    
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
                        logger.warning(f"[{self.label}] 心跳检测失败")
                        if self.auto_reconnect:
                            self._try_reconnect()
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"[{self.label}] 心跳检测异常: {e}")
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
                            spread=data.get("spread", 0),
                            source=self.label
                        )
                        
                        with self._tick_lock:
                            self._latest_tick = tick
                        
                        if self.on_tick:
                            self.on_tick(tick)
                    
                    elif data.get("type") == "heartbeat":
                        if self.on_heartbeat:
                            self.on_heartbeat(data)
                            
            except zmq.Again:
                time.sleep(0.001)
            except Exception as e:
                logger.error(f"[{self.label}] 接收行情异常: {e}")
                time.sleep(1)
    
    def _try_reconnect(self):
        """尝试重连"""
        logger.info(f"[{self.label}] 尝试重新连接MT5...")
        self._connected = False
        
        try:
            if self.sub_socket:
                self.sub_socket.close()
            if self.req_socket:
                self.req_socket.close()
            
            time.sleep(2)
            self.connect()
        except Exception as e:
            logger.error(f"[{self.label}] 重连失败: {e}")
    
    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """发送指令并等待响应"""
        if not self._connected or not self.req_socket:
            raise ConnectionError(f"[{self.label}] 未连接到MT5")
        
        try:
            self.req_socket.send_string(json.dumps(command))
            response = self.req_socket.recv_string()
            return json.loads(response)
        except zmq.Again:
            raise TimeoutError(f"[{self.label}] 指令响应超时")
        except Exception as e:
            raise ConnectionError(f"[{self.label}] 指令发送失败: {e}")
    
    def send_order(
        self,
        action: str,
        symbol: str,
        volume: float,
        sl: float = 0,
        tp: float = 0,
        comment: str = "AI_Trading"
    ) -> OrderResult:
        """发送交易订单"""
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
                source=self.label,
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
                    comment=response.get("comment", ""),
                    source=self.label
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
                    source=self.label,
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
                source=self.label,
                error=str(e)
            )
    
    def close_position(self, ticket: int) -> Dict[str, Any]:
        """平仓"""
        return self.send_command({
            "type": "close",
            "ticket": ticket
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


class DualMT5Bridge:
    """
    双MT5桥接管理器
    同时管理生产环境和研发环境的MT5连接
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.production: Optional[MT5Bridge] = None
        self.research: Optional[MT5Bridge] = None
        
        # 统一行情回调
        self.on_tick: Optional[Callable[[TickData], None]] = None
        
        logger.info("DualMT5Bridge初始化完成")
    
    def connect_all(self) -> Dict[str, bool]:
        """连接所有MT5终端"""
        results = {}
        
        # 连接生产环境 (AVATRADE)
        if "production" in self.config.get("mt5", {}):
            prod_config = self.config["mt5"]["production"]
            self.production = MT5Bridge(
                mt5_host=prod_config.get("host", "localhost"),
                pub_port=prod_config.get("pub_port", 5565),
                req_port=prod_config.get("req_port", 5566),
                heartbeat_interval=prod_config.get("heartbeat_interval", 5),
                auto_reconnect=prod_config.get("auto_reconnect", True),
                label=prod_config.get("label", "AVATRADE")
            )
            self.production.on_tick = self._on_tick_proxy
            results["production"] = self.production.connect()
        
        # 连接研发环境 (AVATRADE-RESEARCH)
        if "research" in self.config.get("mt5", {}):
            res_config = self.config["mt5"]["research"]
            self.research = MT5Bridge(
                mt5_host=res_config.get("host", "localhost"),
                pub_port=res_config.get("pub_port", 5567),
                req_port=res_config.get("req_port", 5568),
                heartbeat_interval=res_config.get("heartbeat_interval", 5),
                auto_reconnect=res_config.get("auto_reconnect", True),
                label=res_config.get("label", "AVATRADE-RESEARCH")
            )
            self.research.on_tick = self._on_tick_proxy
            results["research"] = self.research.connect()
        
        return results
    
    def disconnect_all(self):
        """断开所有连接"""
        if self.production:
            self.production.disconnect()
        if self.research:
            self.research.disconnect()
        logger.info("所有MT5连接已断开")
    
    def _on_tick_proxy(self, tick: TickData):
        """行情代理回调"""
        if self.on_tick:
            self.on_tick(tick)
    
    def get_production_bridge(self) -> Optional[MT5Bridge]:
        """获取生产环境桥接器"""
        return self.production
    
    def get_research_bridge(self) -> Optional[MT5Bridge]:
        """获取研发环境桥接器"""
        return self.research
    
    def get_all_status(self) -> Dict[str, bool]:
        """获取所有连接状态"""
        return {
            "production": self.production.is_connected if self.production else False,
            "research": self.research.is_connected if self.research else False
        }


if __name__ == "__main__":
    # 测试代码
    import yaml
    
    # 加载配置
    with open("config/trading_config_dual.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 创建双桥接器
    dual_bridge = DualMT5Bridge(config)
    
    def on_tick(tick: TickData):
        print(f"[{tick.source}] {tick.symbol} | Bid: {tick.bid:.5f} | Ask: {tick.ask:.5f}")
    
    dual_bridge.on_tick = on_tick
    
    # 连接所有
    results = dual_bridge.connect_all()
    print(f"连接结果: {results}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        dual_bridge.disconnect_all()
