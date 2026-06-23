"""
Smoke test for the official MetaTrader5 Python API connection.
"""

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "python"))

from core.mt5_python_api import MT5PythonAPIBridge


def main() -> int:
    parser = argparse.ArgumentParser(description="Test MT5 Python API connection without trading.")
    parser.add_argument("--terminal-path", default=os.getenv("MT5_TERMINAL_PATH", ""))
    parser.add_argument("--login", type=int, default=int(os.getenv("MT5_LOGIN", "0")) or None)
    parser.add_argument("--server", default=os.getenv("MT5_SERVER", ""))
    parser.add_argument("--password-env", default="MT5_PASSWORD")
    parser.add_argument("--symbol", default=os.getenv("MT5_SYMBOL", "EURUSD"))
    args = parser.parse_args()

    bridge = MT5PythonAPIBridge(
        terminal_path=args.terminal_path or None,
        login=args.login,
        server=args.server or None,
        password_env=args.password_env,
        symbols=[args.symbol],
        poll_interval=9999,
    )

    if not bridge.connect():
        return 1
    try:
        account = bridge.get_account_info()
        tick = bridge._read_tick(args.symbol)
        print(f"account={account.get('login')} server={account.get('server')} equity={account.get('equity')}")
        if tick:
            print(f"tick={tick.symbol} bid={tick.bid} ask={tick.ask} spread={tick.spread}")
        return 0
    finally:
        bridge.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())

