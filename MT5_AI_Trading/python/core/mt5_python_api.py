"""
MetaTrader 5 official Python API bridge.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from core.mt5_bridge import OrderResult, TickData
from ai_engine.d1_risk_officer import D1RiskOfficer, latest_d1_hex_from_duckdb


logger = logging.getLogger(__name__)


class MT5PythonAPIBridge:
    """Bridge using the official MetaTrader5 Python package."""

    def __init__(
        self,
        terminal_path: Optional[str] = None,
        login: Optional[int] = None,
        password: Optional[str] = None,
        password_env: str = "MT5_PASSWORD",
        server: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        poll_interval: float = 1.0,
        timeout: int = 60000,
        portable: bool = False,
        deviation: int = 20,
        magic: int = 20260517,
        fill_policy: str = "auto",
        auto_reconnect: bool = True,
        **_: Any,
    ):
        self.terminal_path = terminal_path
        self.login = int(login) if login not in (None, "") else None
        self.password = password or os.getenv(password_env)
        self.password_env = password_env
        self.server = server
        self.symbols = symbols or ["EURUSD"]
        self.poll_interval = float(poll_interval)
        self.timeout = int(timeout)
        self.portable = bool(portable)
        self.deviation = int(deviation)
        self.magic = int(magic)
        self.fill_policy = fill_policy
        self.auto_reconnect = auto_reconnect

        self.on_tick: Optional[Callable[[TickData], None]] = None
        self.on_heartbeat: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None

        self._mt5 = None
        self._connected = False
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None
        self._latest_tick: Dict[str, TickData] = {}
        self._tick_lock = threading.Lock()

    def _import_mt5(self):
        if self._mt5 is None:
            try:
                import MetaTrader5 as mt5
            except ImportError as exc:
                raise ImportError(
                    "MetaTrader5 package is not installed. Run: pip install MetaTrader5"
                ) from exc
            self._mt5 = mt5
        return self._mt5

    def connect(self) -> bool:
        mt5 = self._import_mt5()
        kwargs: Dict[str, Any] = {"timeout": self.timeout, "portable": self.portable}
        if self.terminal_path:
            kwargs["path"] = self.terminal_path
        if self.login is not None:
            kwargs["login"] = self.login
        if self.password:
            kwargs["password"] = self.password
        if self.server:
            kwargs["server"] = self.server

        if not mt5.initialize(**kwargs):
            logger.error("MT5 Python API initialize failed: %s", mt5.last_error())
            self._connected = False
            return False

        account = mt5.account_info()
        if account is None:
            logger.error("MT5 account_info failed after initialize: %s", mt5.last_error())
            mt5.shutdown()
            self._connected = False
            return False

        for symbol in self.symbols:
            self._ensure_symbol(symbol)

        self._connected = True
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        logger.info("MT5 Python API connected | account=%s server=%s", account.login, account.server)
        return True

    def disconnect(self):
        self._running = False
        self._connected = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
        if self._mt5:
            self._mt5.shutdown()
        logger.info("MT5 Python API disconnected")

    def _poll_loop(self):
        while self._running:
            try:
                for symbol in self.symbols:
                    tick = self._read_tick(symbol)
                    if tick:
                        with self._tick_lock:
                            self._latest_tick[symbol] = tick
                        if self.on_tick:
                            self.on_tick(tick)
                if self.on_heartbeat:
                    self.on_heartbeat({"type": "heartbeat", "source": "python_api", "time": datetime.now().isoformat()})
                time.sleep(self.poll_interval)
            except Exception as exc:
                logger.error("MT5 Python API polling failed: %s", exc)
                if self.on_disconnect:
                    self.on_disconnect()
                if not self.auto_reconnect:
                    break
                time.sleep(max(2.0, self.poll_interval))

    def _ensure_symbol(self, symbol: str) -> bool:
        mt5 = self._import_mt5()
        info = mt5.symbol_info(symbol)
        if info is None:
            logger.error("Symbol not found in MT5: %s", symbol)
            return False
        if not info.visible and not mt5.symbol_select(symbol, True):
            logger.error("Failed to select symbol %s: %s", symbol, mt5.last_error())
            return False
        return True

    def _read_tick(self, symbol: str) -> Optional[TickData]:
        mt5 = self._import_mt5()
        if not self._ensure_symbol(symbol):
            return None
        raw = mt5.symbol_info_tick(symbol)
        if raw is None:
            logger.warning("symbol_info_tick returned None for %s: %s", symbol, mt5.last_error())
            return None
        bid = float(raw.bid)
        ask = float(raw.ask)
        return TickData(
            symbol=symbol,
            bid=bid,
            ask=ask,
            last=float(getattr(raw, "last", 0) or 0),
            volume=int(getattr(raw, "volume", 0) or 0),
            time=int(getattr(raw, "time", 0) or time.time()),
            time_msc=int(getattr(raw, "time_msc", 0) or 0),
            spread=ask - bid,
            timestamp=datetime.fromtimestamp(raw.time) if getattr(raw, "time", 0) else datetime.now(),
        )

    def get_latest_tick(self, symbol: Optional[str] = None) -> Optional[TickData]:
        symbol = symbol or self.symbols[0]
        with self._tick_lock:
            return self._latest_tick.get(symbol)

    def get_account_info(self) -> Dict[str, Any]:
        mt5 = self._import_mt5()
        info = mt5.account_info()
        if info is None:
            raise RuntimeError(f"account_info failed: {mt5.last_error()}")
        return info._asdict()

    def get_positions(self) -> Dict[str, Any]:
        mt5 = self._import_mt5()
        positions = mt5.positions_get()
        if positions is None:
            raise RuntimeError(f"positions_get failed: {mt5.last_error()}")
        rows = [position._asdict() for position in positions]
        return {"count": len(rows), "positions": rows}

    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        command_type = command.get("type")
        if command_type == "ping":
            return {"type": "pong", "source": "python_api"}
        if command_type == "info":
            return self.get_account_info()
        if command_type == "positions":
            return self.get_positions()
        raise ValueError(f"Unsupported Python API command: {json.dumps(command, ensure_ascii=False)}")

    def send_order(
        self,
        action: str,
        symbol: str,
        volume: float,
        sl: float = 0,
        tp: float = 0,
        comment: str = "AI_Trading",
    ) -> OrderResult:
        mt5 = self._import_mt5()
        if not self._connected:
            return self._failed_order(symbol, action, comment, "MT5 Python API is not connected")
        if not self._ensure_symbol(symbol):
            return self._failed_order(symbol, action, comment, f"Symbol not available: {symbol}")

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return self._failed_order(symbol, action, comment, f"No tick for {symbol}: {mt5.last_error()}")

        action_upper = action.upper()
        d1_hex = latest_d1_hex_from_duckdb(symbol)
        d1_decision = D1RiskOfficer().assess(d1_hex, action_upper, lower_timeframe="H1")
        if not d1_decision.allowed:
            return self._failed_order(
                symbol,
                action,
                comment,
                f"D1RiskOfficer blocked: {d1_decision.reason} (d1_hex={d1_decision.d1_hex or 'N/A'})",
            )

        if action_upper == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = float(tick.ask)
        elif action_upper == "SELL":
            order_type = mt5.ORDER_TYPE_SELL
            price = float(tick.bid)
        else:
            return self._failed_order(symbol, action, comment, f"Unsupported order action: {action}")

        base_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "sl": float(sl or 0),
            "tp": float(tp or 0),
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        last_error = ""
        for filling in self._candidate_fillings():
            request = dict(base_request)
            request["type_filling"] = filling
            check = mt5.order_check(request)
            if check is not None and getattr(check, "retcode", None) not in self._successful_check_retcodes():
                last_error = f"order_check retcode={check.retcode} comment={getattr(check, 'comment', '')}"
                continue

            result = mt5.order_send(request)
            if result is None:
                last_error = f"order_send returned None: {mt5.last_error()}"
                continue
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=True,
                    ticket=int(getattr(result, "order", 0) or getattr(result, "deal", 0) or 0),
                    volume=float(getattr(result, "volume", volume) or volume),
                    price=float(getattr(result, "price", price) or price),
                    symbol=symbol,
                    action=action_upper,
                    comment=str(getattr(result, "comment", comment) or comment),
                )
            last_error = f"order_send retcode={result.retcode} comment={getattr(result, 'comment', '')}"

        return self._failed_order(symbol, action, comment, last_error or "Order was rejected")

    def close_position(self, ticket: int) -> Dict[str, Any]:
        mt5 = self._import_mt5()
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return {"success": False, "error": f"Position not found: {ticket}"}

        position = positions[0]
        symbol = position.symbol
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "error": f"No tick for {symbol}: {mt5.last_error()}"}

        if position.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = float(tick.bid)
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = float(tick.ask)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": int(ticket),
            "symbol": symbol,
            "volume": float(position.volume),
            "type": order_type,
            "price": price,
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": "AI_close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._candidate_fillings()[0],
        }
        result = mt5.order_send(request)
        if result is None:
            return {"success": False, "error": str(mt5.last_error())}
        return {"success": result.retcode == mt5.TRADE_RETCODE_DONE, **result._asdict()}

    def modify_position(self, ticket: int, sl: float = 0, tp: float = 0) -> Dict[str, Any]:
        mt5 = self._import_mt5()
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return {"success": False, "error": f"Position not found: {ticket}"}
        position = positions[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(ticket),
            "symbol": position.symbol,
            "sl": float(sl or 0),
            "tp": float(tp or 0),
        }
        result = mt5.order_send(request)
        if result is None:
            return {"success": False, "error": str(mt5.last_error())}
        return {"success": result.retcode == mt5.TRADE_RETCODE_DONE, **result._asdict()}

    def _candidate_fillings(self) -> List[int]:
        mt5 = self._import_mt5()
        policies = {
            "fok": mt5.ORDER_FILLING_FOK,
            "ioc": mt5.ORDER_FILLING_IOC,
            "return": mt5.ORDER_FILLING_RETURN,
        }
        configured = str(self.fill_policy or "auto").lower()
        if configured in policies:
            return [policies[configured]]
        return [policies["fok"], policies["ioc"], policies["return"]]

    def _successful_check_retcodes(self) -> set:
        mt5 = self._import_mt5()
        return {
            getattr(mt5, "TRADE_RETCODE_DONE", 10009),
            getattr(mt5, "TRADE_RETCODE_PLACED", 10008),
        }

    @staticmethod
    def _failed_order(symbol: str, action: str, comment: str, error: str) -> OrderResult:
        return OrderResult(
            success=False,
            ticket=0,
            volume=0,
            price=0,
            symbol=symbol,
            action=action,
            comment=comment,
            error=error,
        )

    @property
    def is_connected(self) -> bool:
        return self._connected
