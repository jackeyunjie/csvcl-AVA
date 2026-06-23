"""
AI交易平台 — 快速连通性测试脚本

运行前：确保MT5已启动并登录，AVATRADE或KVB均可。
执行后应输出：账号余额 / BTCUSD行情 / 连接成功提示。
"""

import MetaTrader5 as mt5
import time

def test_connect():
    print("=" * 55)
    print("  AI 交易平台 — 连通性测试")
    print("=" * 55)

    if not mt5.initialize():
        print("[错误] 初始化失败。请确保MT5已启动并登录。")
        return False

    info = mt5.terminal_info()
    account = mt5.account_info()

    if not info or not account:
        print("[错误] 无法获取终端/账户信息。")
        mt5.shutdown()
        return False

    print(f"\n--- 终端: {info.name}")
    print(f"   路径: {info.path}")
    print(f"   版本: {info.build}")
    print(f"\n--- 账号: {account.login}")
    print(f"   余额: ${account.balance:.2f}")
    print(f"   净值: ${account.equity:.2f}")
    print(f"   服务器: {account.server}")
    trade_mode = "模拟" if account.trade_mode == 0 else "实盘"
    print(f"   模式: {trade_mode}")

    for sym in ["BTCUSD", "XAUUSD", "EURUSD", "USDJPY"]:
        tick = mt5.symbol_info_tick(sym)
        if tick:
            print(f"\n--- {sym} 实时报价")
            print(f"   Bid: {tick.bid}  Ask: {tick.ask}  点差: {tick.ask - tick.bid:.5f}")
            break
    else:
        print("\n[警告] 未找到行情")

    print("\n" + "=" * 55)
    print("  [OK] 连接测试通过 - AI现在可以看到市场了")
    print("=" * 55)
    mt5.shutdown()
    return True

if __name__ == "__main__":
    test_connect()
