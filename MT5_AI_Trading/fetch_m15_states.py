"""
M15 State 数据下载与计算

独立系统，使用 m15_state.duckdb
支持7周期：MN1/W1/D1/H4/H1/M30/M15

用法:
    python fetch_m15_states.py --symbols EURUSD XAUUSD
    python fetch_m15_states.py --all
"""

import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "ai_engine"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python"))

from backtest_platform.data_layer import MT5DataBridge
from m15_state_db import M15StateEngine, M15_TIMEFRAMES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 品种映射（AVATRADE 实际符号）
SYMBOL_MAP = {
    "EURUSD": "EURUSD",
    "XAUUSD": "XAUUSD",
    "USOIL": "USOIL",
    "BTCUSD": "BTCUSD",
    "US_30": "US_30",
    "US_500": "US_500",
    "US_TECH100": "US_TECH100",
    "HK_50": "HK_50",
    "CHINA_A50": "CHINA_A50",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
}


def download_m15_states(symbols: list, days: int = 30, terminal_path: str = None):
    """下载M15 State数据 (使用 MT5 Python API)"""
    bridge = MT5DataBridge(terminal_path=terminal_path)
    engine = M15StateEngine()

    if not bridge.connect():
        logger.error("MT5连接失败，请确认终端已启动")
        return

    # 用 count 方式拉取（更可靠）
    bar_counts = {
        "MN1": 60, "W1": 260, "D1": days,
        "H4": days * 6, "H1": days * 24,
        "M30": days * 48, "M15": days * 96,
    }

    total = 0
    for symbol in symbols:
        mt5_symbol = SYMBOL_MAP.get(symbol, symbol)
        logger.info(f"\n{'='*60}")
        logger.info(f"下载 M15 State: {symbol} ({mt5_symbol})")
        logger.info(f"{'='*60}")

        try:
            # 拉取7周期数据
            multi_data = {}
            for tf in M15_TIMEFRAMES:
                count = bar_counts.get(tf, 500)
                df = bridge.fetch_ohlcv_from_pos(mt5_symbol, tf, count)
                multi_data[tf] = df
                if df is not None and not df.empty:
                    logger.info(f"  {tf}: {len(df)} 条")
                else:
                    logger.warning(f"  {tf}: 无数据")

            if multi_data.get("M15") is None or multi_data["M15"].empty:
                logger.warning(f"{symbol} 无M15数据")
                continue

            # 计算并保存M15 State
            count = engine.process_symbol(symbol, multi_data)
            total += count
            logger.info(f"{symbol} 完成: {count} 条M15 State")

        except Exception as e:
            logger.error(f"{symbol} 失败: {e}")
            import traceback
            traceback.print_exc()

    bridge.disconnect()
    logger.info(f"\n{'='*60}")
    logger.info(f"总计: {total} 条M15 State")
    logger.info(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["US_30", "US_500", "US_TECH100"],
                        help="品种列表")
    parser.add_argument("--all", action="store_true",
                        help="下载所有品种")
    parser.add_argument("--days", type=int, default=30,
                        help="下载天数 (默认30)")
    parser.add_argument("--terminal", default=r"D:\Program Files\Ava Trade MT5 Terminal\terminal64.exe",
                        help="MT5 终端路径")
    args = parser.parse_args()

    symbols = list(SYMBOL_MAP.keys()) if args.all else args.symbols

    logger.info("="*60)
    logger.info("M15 State 数据下载")
    logger.info("="*60)
    logger.info(f"品种: {symbols}")
    logger.info(f"周期: {M15_TIMEFRAMES}")
    logger.info(f"天数: {args.days}")

    download_m15_states(symbols, args.days, args.terminal)


if __name__ == "__main__":
    main()
