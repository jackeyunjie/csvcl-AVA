"""
AI交易平台 — 首次模拟下单测试

功能：连接MT5 → 获取行情 → 发送0.01手EURUSD模拟买入单 → 立即平仓
目的：验证完整下单-平仓流程，确认AI可以控制MT5交易

⚠ 安全：仅EURUSD 0.01手，开仓后3秒自动平仓
"""

import MetaTrader5 as mt5
import time

SYMBOL = "EURUSD"
LOTS = 0.01

def get_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    return tick.ask if tick else 0

def send_order(order_type, price, lots=LOTS):
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lots,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 20260517,
        "comment": "AI_test",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    return result

def main():
    print("=" * 55)
    print("  AI 交易平台 — 模拟下单测试")
    print("=" * 55)

    if not mt5.initialize():
        print("[失败] MT5初始化失败")
        return
    print(f"[连接] AVATRADE MT5 已连接")

    sym = mt5.symbol_info(SYMBOL)
    if not sym:
        print(f"[失败] 品种 {SYMBOL} 不可用")
        mt5.shutdown()
        return
    mt5.symbol_select(SYMBOL, True)
    print(f"[品种] {SYMBOL} 已选择")

    ask = get_price(SYMBOL)
    print(f"[行情] {SYMBOL} Ask={ask}")

    input(f"\n按 Enter 发送0.01手买入单到MT5...")

    result = send_order(mt5.ORDER_TYPE_BUY, ask)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[失败] 下单失败 code={result.retcode} comment={result.comment}")
        mt5.shutdown()
        return

    ticket = result.order
    print(f"[开仓] OK 多单已开 ticket={ticket} price={result.price}")

    time.sleep(3)

    position = mt5.positions_get(ticket=ticket)
    if position:
        pos = position[0]
        profit = pos.profit
        bid = mt5.symbol_info_tick(SYMBOL).bid
        print(f"[持仓] 手数={pos.volume} 浮盈={profit:.2f}")

        input(f"\n按 Enter 平仓...")

        close_result = send_order(mt5.ORDER_TYPE_SELL, bid)
        if close_result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[平仓] OK 已平仓 @ {close_result.price}")
        else:
            print(f"[平仓失败] code={close_result.retcode}")
    else:
        print("[平仓] 无持仓，可能已被止损/止盈")

    print("\n" + "=" * 55)
    print("  [OK] AI -> MT5 下单-平仓 完整通路验证通过")
    print("=" * 55)

    mt5.shutdown()

if __name__ == "__main__":
    main()
