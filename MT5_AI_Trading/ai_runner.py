"""
AI 策略引擎 — 持续运行主控制器

架构：MT5 Python API(行情+下单) + State编码引擎(信号) + LLM分析
频率：每K线收盘触发一次State计算 (H1周期)
安全：默认dry_run=True，只记录不真下单

启动:  python ai_runner.py
"""

import MetaTrader5 as mt5
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AI_Runner")

DRY_RUN = True
SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "XAUUSD"]
TIMEFRAME = mt5.TIMEFRAME_H1

class AITrader:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.last_bar_times = {}
        if not mt5.initialize():
            raise RuntimeError("MT5初始化失败")
        acc = mt5.account_info()
        logger.info(f"[连接] AVATRADE | 账号: {acc.login} | 余额: ${acc.balance:.2f}")

        for s in SYMBOLS:
            mt5.symbol_select(s, True)
        logger.info(f"[品种] {SYMBOLS} 已就绪")
        logger.info(f"[模式] {'模拟(DryRun)' if self.dry_run else '实盘Live'}")

    def get_ohlcv(self, symbol, count=200):
        rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, count)
        if rates is None:
            return None
        return rates

    def calc_state(self, rates):
        """简化版State计算(布林带ADX+位置) 占位"""
        if rates is None or len(rates) < 50:
            return 0
        last = rates[-1]
        # 布林带位置
        closes = [r[4] for r in rates]
        bb_mid = sum(closes[-20:]) / 20
        bb_std = (sum((c - bb_mid) ** 2 for c in closes[-20:]) / 20) ** 0.5
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        bb_width = (bb_upper - bb_lower) / bb_mid if bb_mid != 0 else 0
        base = 8 if bb_width > 0.02 else 0
        # 趋势（简化）
        trend = 4 if closes[-1] > closes[-10] else 0
        # 位置
        pos = 2 if last[4] > bb_upper else (-2 if last[4] < bb_lower else 0)
        score = base + trend + pos
        return score

    def llm_analyze(self, symbol, state_data):
        """
        LLM分析市场状态
        此处为占位，实际应调用OpenAI API将State编码+行情数据发给GPT分析
        """
        scores = state_data
        ef_count = sum(1 for s in scores.values() if s >= 14)

        analysis = f"{symbol} H1 | 当前价格突破布林上轨 | "
        if ef_count >= 2:
            analysis += "多周期共振E/F信号→趋势策略偏多"
        elif scores.get(symbol, 0) >= 12:
            analysis += "扩张+趋势→可考虑入场"
        else:
            analysis += "收缩/无方向→观望"
        return analysis

    def place_order(self, symbol, order_type, lots=0.01):
        if self.dry_run:
            logger.info(f"[DRY_RUN] {symbol} {'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL'} {lots}手")
            return True

        tick = mt5.symbol_info_tick(symbol)
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lots,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 20260517,
            "comment": "AI_runner",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"[下单] {symbol} ticket={result.order} price={result.price}")
            return True
        logger.error(f"[下单失败] {symbol} code={result.retcode}")
        return False

    def run_once(self):
        now = datetime.now()
        for symbol in SYMBOLS:
            rates = self.get_ohlcv(symbol)
            if rates is None:
                continue

            bar_time = datetime.fromtimestamp(rates[-1][0])
            if symbol in self.last_bar_times:
                if bar_time <= self.last_bar_times[symbol]:
                    continue
            self.last_bar_times[symbol] = bar_time

            state = self.calc_state(rates)
            analysis = self.llm_analyze(symbol, {symbol: state})

            # 示例：State≥12 + 区间在 08:00-22:00(北京时间=GMT+8)时发模拟单
            hour = now.hour
            if state >= 12 and 8 <= hour <= 22:
                logger.info(f"[信号] {symbol} State={state} | {analysis}")
                self.place_order(symbol, mt5.ORDER_TYPE_BUY, 0.01)

    def loop(self):
        logger.info(f"[运行] AI策略引擎启动  {'(DryRun模式，不下真实单)' if self.dry_run else '(实盘)'}")
        try:
            while True:
                self.run_once()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("[退出] 收到停止信号")

if __name__ == "__main__":
    trader = AITrader(dry_run=True)
    trader.loop()
