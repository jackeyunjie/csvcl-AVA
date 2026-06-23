"""
从 MT5 拉取真实 OHLCV 数据，构建 H1 State 数据库

用法:
  python build_h1_state_real.py                    # 默认 EURUSD, 90天
  python build_h1_state_real.py --symbol GBPUSD    # 指定品种
  python build_h1_state_real.py --days 180         # 180天数据
  python build_h1_state_real.py --symbols EURUSD GBPUSD USDJPY  # 多品种
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
logger = logging.getLogger("build_h1_state")

# 品种名称映射 (AVATRADE 平台实际名称)
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
    # 欧洲股指 (6只)
    "UK_100": "UK_100",
    "FRANCE_40": "FRANCE_40",
    "EUROPE_50": "EUROPE_50",
    "SWISS_20": "SWISS_20",
    "ITALY_40": "ITALY_40",
    "GERMANY_TECH30": "GERMANY_TECH30",
    # 亚太/中国股指 (2只)
    "CHINA_INTERNET": "CHINA_INTERNET",
    "SILVER": "SILVER",
    "BRENT_OIL": "BRENT_OIL",
    "NATURAL_GAS": "NATURAL_GAS",
    "#APPLE": "#APPLE",
    "#MICROSOFT": "#MICROSOFT",
    "#NVIDIA": "#NVIDIA",
    "#TESLA": "#TESLA",
    "#AMAZON": "#AMAZON",
    "#GOOGLE": "#GOOGLE",
    "#META": "#META",
    "#NETFLIX": "#NETFLIX",
    "#AMD": "#AMD",
    "#JPMORGAN": "#JPMORGAN",
    "#BERKSHIRE": "#BERKSHIRE",
    "#JOHNSON": "#JOHNSON",
    "#EXXON": "#EXXON",
    "#WALMART": "#WALMART",
    # 美国大型科技股/金融 (8只)
    "#ALIBABA": "#ALIBABA",
    "#ADOBE": "#ADOBE",
    "#SALESFORCE": "#SALESFORCE",
    "#ZOOM": "#ZOOM",
    "#UBER": "#UBER",
    "#AIRBNB": "#AIRBNB",
    "#SNAPCHAT": "#SNAPCHAT",
    "#COINBASE": "#COINBASE",
    # 美国传统行业 (5只)
    "#PEPSICO": "#PEPSICO",
    "#MCDONALDS": "#MCDONALDS",
    "#STARBUCKS": "#STARBUCKS",
    "#NIKE": "#NIKE",
    "#DISNEY": "#DISNEY",
    # 日本/亚太 (3只)
    "#SONY": "#SONY",
    "#TAIWANSEMI": "#TAIWANSEMI",
    "#PINDUODUO": "#PINDUODUO",
    # === 第三批：美股/中概 新增20只 ===
    # 科技/半导体 (5只)
    "#ORACLE": "#ORACLE",
    "#INTEL": "#INTEL",
    "#CISCO": "#CISCO",
    "#QUALCOMM": "#QUALCOMM",
    "#BROADCOM": "#BROADCOM",
    # 金融/支付 (4只)
    "#VISA": "#VISA",
    "#MASTERCARD": "#MASTERCARD",
    "#BLACKROCK": "#BLACKROCK",
    "#CITIGROUP": "#CITIGROUP",
    # 医疗/制药 (4只)
    "#PFIZER": "#PFIZER",
    "#MERCK": "#MERCK",
    "#ABBVIE": "#ABBVIE",
    "#THERMOFISHER": "#THERMOFISHER",
    # 消费/零售 (3只)
    "#COSTCO": "#COSTCO",
    "#HOMEDEPOT": "#HOMEDEPOT",
    "#TARGET": "#TARGET",
    # 能源/工业/通信 (3只)
    "#CHEVRON": "#CHEVRON",
    "#BOEING": "#BOEING",
    "#VERIZON": "#VERIZON",
    # 中概股 (1只)
    "#BAIDU": "#BAIDU",
}


def check_mt5_available() -> bool:
    """检查 MT5 Python API 是否可用"""
    try:
        import MetaTrader5 as mt5
        return True
    except ImportError:
        return False


def build_with_mt5_api(symbols: list, days: int, terminal_path: str = None):
    """使用 MT5 Python API 拉取数据"""
    from backtest_platform.data_layer import MT5DataBridge
    from ai_engine.state_hex_engine import StateHexEngine
    from data.h1_state_db import H1StateDB

    bridge = MT5DataBridge(terminal_path=terminal_path)
    if not bridge.connect():
        logger.error("MT5 连接失败！请确认:")
        logger.error("  1. MT5 终端已启动")
        logger.error("  2. 已登录账户")
        logger.error("  3. MetaTrader5 包已安装 (pip install MetaTrader5)")
        raise RuntimeError("MT5 connection failed")

    start = datetime.now() - timedelta(days=days)
    end = datetime.now()
    timeframes = ["MN1", "W1", "D1", "H4", "H1"]

    h1db = H1StateDB("data/h1_state.duckdb")
    total_saved = 0

    try:
        for symbol in symbols:
            logger.info(f"\n{'='*50}")
            logger.info(f"处理 {symbol} ({days}天)")
            logger.info(f"{'='*50}")

            # 拉取多周期数据（用 count 方式，更可靠）
            multi = {}
            bar_counts = {"MN1": 60, "W1": 260, "D1": days, "H4": days * 6, "H1": days * 24}
            mt5_symbol = SYMBOL_MAP.get(symbol, symbol)

            for tf in timeframes:
                try:
                    multi[tf] = bridge.fetch_ohlcv_from_pos(mt5_symbol, tf, bar_counts.get(tf, 500))
                except Exception as e:
                    logger.warning(f"  {tf} 拉取失败: {e}")
                    multi[tf] = None

            for tf in timeframes:
                df = multi.get(tf)
                logger.info(f"  {tf}: {len(df) if df is not None and not df.empty else 0} 条")

            # 初始化引擎
            engine = StateHexEngine()

            d1_df = multi.get("D1")
            w1_df = multi.get("W1")
            mn1_df = multi.get("MN1")
            h4_df = multi.get("H4")
            h1_df = multi.get("H1")

            if d1_df is None or d1_df.empty:
                logger.warning(f"  {symbol}: D1 数据为空，跳过")
                continue
            if h1_df is None or h1_df.empty:
                logger.warning(f"  {symbol}: H1 数据为空，跳过")
                continue

            # 加载 5 个结构周期数据，共同服务于 H1 视角 Agent
            engine.add_d1_dataframe(d1_df)
            if w1_df is not None and not w1_df.empty:
                engine.add_w1_dataframe(w1_df)
            if mn1_df is not None and not mn1_df.empty:
                engine.add_mn1_dataframe(mn1_df)
            if h4_df is not None and not h4_df.empty:
                engine.add_h4_dataframe(h4_df)
            engine.add_h1_dataframe(h1_df)

            # 计算五元组
            quintuplets = engine.compute_quintuplets()
            logger.info(f"  五元组: {len(quintuplets)} 条")

            # 存入数据库
            saved = h1db.save_quintuplets(symbol, quintuplets)
            total_saved += saved
            logger.info(f"  已保存: {saved} 条")
    finally:
        h1db.close()
        bridge.disconnect()

    logger.info("\n构建完成！")
    return total_saved


def build_with_csv_fallback(symbols: list, days: int):
    """无 MT5 时的备用方案：用种子数据构建"""
    logger.warning("MT5 Python API 不可用，使用种子数据构建")

    from ai_engine.state_hex_engine import StateHexEngine
    from data.h1_state_db import H1StateDB
    import numpy as np
    import pandas as pd

    np.random.seed(42)
    h1db = H1StateDB("data/h1_state.duckdb")

    for symbol in symbols:
        logger.info(f"构建 {symbol} 种子数据...")

        # 生成模拟 OHLCV
        n_h1 = days * 24
        base = 1.0850 if "USD" in symbol else 100.0
        vol = 0.0005 if "USD" in symbol else 0.5

        start = datetime.now() - timedelta(days=days)

        def gen_ohlcv(n, freq_hours, base_price, volatility):
            data = []
            price = base_price
            for i in range(n):
                ts = start + timedelta(hours=i * freq_hours)
                price += np.random.randn() * volatility
                h = price + abs(np.random.randn()) * volatility * 0.5
                l = price - abs(np.random.randn()) * volatility * 0.5
                data.append({'timestamp': ts, 'open': price + np.random.randn() * volatility * 0.2,
                             'high': h, 'low': l, 'close': price, 'volume': np.random.randint(1000, 10000)})
            return pd.DataFrame(data)

        engine = StateHexEngine()
        engine.add_mn1_dataframe(gen_ohlcv(max(12, days // 30), 24 * 30, base, vol * 3))
        engine.add_w1_dataframe(gen_ohlcv(max(52, days // 7), 24 * 7, base, vol * 2))
        engine.add_d1_dataframe(gen_ohlcv(days, 24, base, vol * 1.5))
        engine.add_h4_dataframe(gen_ohlcv(days * 6, 4, base, vol))
        engine.add_h1_dataframe(gen_ohlcv(n_h1, 1, base, vol))

        quintuplets = engine.compute_quintuplets()
        saved = h1db.save_quintuplets(symbol, quintuplets)
        logger.info(f"  {symbol}: {saved} 条种子数据")

    h1db.close()
    logger.info("\n种子数据构建完成！")


def show_summary(symbols: list):
    """显示数据库摘要"""
    from data.h1_state_db import H1StateDB
    import json

    h1db = H1StateDB("data/h1_state.duckdb")
    for symbol in symbols:
        summary = h1db.get_summary(symbol)
        print(f"\n{'='*50}")
        print(f"{symbol} State 数据库摘要:")
        print(json.dumps(summary, indent=2, default=str))
    h1db.close()


def main():
    parser = argparse.ArgumentParser(description="构建 H1 State 数据库")
    parser.add_argument("--symbols", nargs="+", default=["EURUSD"], help="交易品种")
    parser.add_argument("--days", type=int, default=90, help="拉取天数")
    parser.add_argument("--terminal", default=None, help="MT5 终端路径")
    parser.add_argument("--summary", action="store_true", help="显示摘要")
    args = parser.parse_args()

    if args.summary:
        show_summary(args.symbols)
        return

    if not check_mt5_available():
        logger.error("MetaTrader5 包不可用；生产任务禁止使用 CSV/seed fallback。")
        raise SystemExit(2)

    try:
        saved = build_with_mt5_api(args.symbols, args.days, args.terminal)
    except Exception as exc:
        logger.error(f"H1 构建失败: {exc}")
        raise SystemExit(1) from exc
    if saved <= 0:
        logger.error("H1 构建未保存任何数据")
        raise SystemExit(1)

    show_summary(args.symbols)


if __name__ == "__main__":
    main()
