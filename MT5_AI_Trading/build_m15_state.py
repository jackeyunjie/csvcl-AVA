r"""
从 MT5 拉取真实 OHLCV 数据，构建 M15 State 数据库

用法:
  python build_m15_state.py                    # 默认 EURUSD, 30天
  python build_m15_state.py --symbol US_30     # 指定品种
  python build_m15_state.py --days 30          # 30天数据
  python build_m15_state.py --symbols US_30 US_500 US_TECH100  # 多品种
  python build_m15_state.py --terminal "D:\Program Files\Ava Trade MT5 Terminal\terminal64.exe"
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "python"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("build_m15_state")

# 品种名称映射 (AVATRADE 平台实际名称)
# 从 check_mt5_symbols.py 输出获取
SYMBOL_MAP = {
    "US_30": "US_30",
    "US_500": "US_500",
    "US_TECH100": "US_TECH100",
    "EURUSD": "EURUSD",
    "XAUUSD": "GOLD",
    "USOIL": "CrudeOIL",
    "BTCUSD": "BTCUSD",
    "HK_50": "HK_50",
    "CHINA_A50": "CHINA_A50",
    "GER30": "GERMANY_40",
    "JP225": "JAPAN_225",
}


def check_mt5_available() -> bool:
    """检查 MT5 Python API 是否可用"""
    try:
        import MetaTrader5 as mt5
        return True
    except ImportError:
        return False


def build_with_mt5_api(symbols: list, days: int, terminal_path: str = None):
    """使用 MT5 Python API 拉取数据并构建 M15 State"""
    from backtest_platform.data_layer import MT5DataBridge
    from data.m15_state_db import M15StateEngine, M15_TIMEFRAMES

    bridge = MT5DataBridge(terminal_path=terminal_path)
    if not bridge.connect():
        logger.error("MT5 连接失败！请确认:")
        logger.error("  1. MT5 终端已启动")
        logger.error("  2. 已登录账户")
        logger.error("  3. MetaTrader5 包已安装 (pip install MetaTrader5)")
        raise RuntimeError("MT5 connection failed")

    start = datetime.now() - timedelta(days=days)
    end = datetime.now()

    # M15 周期列表（7个）
    timeframes = M15_TIMEFRAMES

    # 每个周期的 bar 数量估算
    bar_counts = {
        "MN1": max(12, days // 30),
        "W1": max(52, days // 7),
        "D1": days,
        "H4": days * 6,
        "H1": days * 24,
        "M30": days * 48,
        "M15": days * 96,
    }

    engine = M15StateEngine()
    total_saved = 0

    try:
        for symbol in symbols:
            mt5_symbol = SYMBOL_MAP.get(symbol, symbol)
            logger.info(f"\n{'='*60}")
            logger.info(f"处理 M15 State: {symbol} ({mt5_symbol}) | {days}天")
            logger.info(f"{'='*60}")

            # 拉取7周期数据（用日期范围方式）
            multi = {}
            for tf in timeframes:
                try:
                    df = bridge.fetch_ohlcv(mt5_symbol, tf, start, end)
                    multi[tf] = df
                    logger.info(f"  {tf}: {len(df)} 条")
                except Exception as e:
                    logger.warning(f"  {tf} 拉取失败: {e}")
                    multi[tf] = None

            # 检查 M15 数据
            m15_df = multi.get("M15")
            if m15_df is None or m15_df.empty:
                logger.warning(f"  {symbol}: M15 数据为空，跳过")
                continue

            # 计算 M15 State
            saved = engine.process_symbol(symbol, multi)
            total_saved += saved
            logger.info(f"  已保存: {saved} 条 M15 State")
    finally:
        engine.db.close()
        bridge.disconnect()

    logger.info(f"\n{'='*60}")
    logger.info(f"构建完成！总计: {total_saved} 条 M15 State")
    logger.info(f"{'='*60}")
    return total_saved


def build_with_mock_data(symbols: list, days: int):
    """无 MT5 时的备用方案：用模拟数据构建"""
    logger.warning("MT5 Python API 不可用，使用模拟数据构建")

    from data.m15_state_db import M15StateEngine, M15StateDB, M15StateHex, SRLevel
    import numpy as np
    import pandas as pd

    np.random.seed(42)
    db = M15StateDB("data/m15_state.duckdb")

    for symbol in symbols:
        logger.info(f"构建 {symbol} 模拟 M15 数据...")

        n_m15 = days * 96  # M15 bar数量
        base = 1.0850 if "USD" in symbol else 100.0
        vol = 0.0005 if "USD" in symbol else 0.5

        start = datetime.now() - timedelta(days=days)

        def gen_ohlcv(n, freq_minutes, base_price, volatility):
            data = []
            price = base_price
            for i in range(n):
                ts = start + timedelta(minutes=i * freq_minutes)
                price += np.random.randn() * volatility
                h = price + abs(np.random.randn()) * volatility * 0.5
                l = price - abs(np.random.randn()) * volatility * 0.5
                data.append({
                    'timestamp': ts,
                    'open': price + np.random.randn() * volatility * 0.2,
                    'high': h, 'low': l, 'close': price,
                    'volume': np.random.randint(1000, 10000)
                })
            return pd.DataFrame(data)

        # 生成7周期模拟数据
        multi = {
            "MN1": gen_ohlcv(max(12, days // 30), 30 * 24 * 60, base, vol * 3),
            "W1": gen_ohlcv(max(52, days // 7), 7 * 24 * 60, base, vol * 2),
            "D1": gen_ohlcv(days, 24 * 60, base, vol * 1.5),
            "H4": gen_ohlcv(days * 6, 4 * 60, base, vol),
            "H1": gen_ohlcv(days * 24, 60, base, vol * 0.8),
            "M30": gen_ohlcv(days * 48, 30, base, vol * 0.6),
            "M15": gen_ohlcv(n_m15, 15, base, vol * 0.5),
        }

        # 使用 M15StateEngine 处理
        engine = M15StateEngine()
        saved = engine.process_symbol(symbol, multi)
        logger.info(f"  {symbol}: {saved} 条模拟 M15 State")

    engine.db.close()
    logger.info("\n模拟数据构建完成！")


def show_summary(symbols: list):
    """显示数据库摘要"""
    from data.m15_state_db import M15StateDB
    import json

    db = M15StateDB("data/m15_state.duckdb")
    for symbol in symbols:
        summary = db.get_summary(symbol)
        print(f"\n{'='*50}")
        print(f"{symbol} M15 State 数据库摘要:")
        print(json.dumps(summary, indent=2, default=str))

        # 显示最新state
        latest = db.get_latest(symbol)
        if latest:
            print(f"\n  最新记录:")
            print(f"    时间: {latest.get('timestamp')}")
            print(f"    M15={latest.get('m15_hex')}, H1={latest.get('h1_hex')}, D1={latest.get('d1_hex')}")
            print(f"    SR突破={latest.get('sr_breakout')}, 方向={latest.get('breakout_direction')}")

        # SR突破统计
        conn = db._get_conn()
        rows = conn.execute("""
            SELECT breakout_direction, COUNT(*) as cnt
            FROM m15_state_snapshot
            WHERE symbol = ? AND sr_breakout = TRUE
            GROUP BY breakout_direction
        """, [symbol]).fetchall()
        if rows:
            print(f"\n  SR突破统计:")
            for direction, cnt in rows:
                print(f"    {direction}: {cnt} 次")

    db.close()


def main():
    parser = argparse.ArgumentParser(description="构建 M15 State 数据库")
    parser.add_argument("--symbols", nargs="+", default=["EURUSD"], help="交易品种")
    parser.add_argument("--days", type=int, default=30, help="拉取天数")
    parser.add_argument("--terminal", default=None, help="MT5 终端路径")
    parser.add_argument("--summary", action="store_true", help="显示摘要")
    args = parser.parse_args()

    if args.summary:
        show_summary(args.symbols)
        return

    if not check_mt5_available():
        logger.error("MetaTrader5 包不可用；生产任务禁止使用 mock fallback。")
        raise SystemExit(2)

    try:
        saved = build_with_mt5_api(args.symbols, args.days, args.terminal)
    except Exception as exc:
        logger.error(f"M15 构建失败: {exc}")
        raise SystemExit(1) from exc
    if saved <= 0:
        logger.error("M15 构建未保存任何数据")
        raise SystemExit(1)

    show_summary(args.symbols)


if __name__ == "__main__":
    main()
