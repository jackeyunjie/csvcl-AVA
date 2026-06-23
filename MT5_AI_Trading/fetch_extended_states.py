"""
扩展 State 数据下载
支持品种: US_30, US_500, US_TECH100, HK_50, CHINA_A50, XAUUSD, USOIL, BTCUSD
支持周期: MN1, W1, D1, H4, H1, M15

用法:
    python fetch_extended_states.py           # 下载所有品种
    python fetch_extended_states.py --symbols HK_50 CHINA_A50  # 只下载指定品种
    python fetch_extended_states.py --timeframes M15 H1        # 只下载指定周期
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "ai_engine"))

from mt5_bridge import MT5Bridge
from h1_state_db import H1StateDB
from state_hex_engine import StateHexEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 扩展品种列表
EXTENDED_SYMBOLS = [
    # 股指
    "US_30", "US_500", "US_TECH100",
    "HK_50", "CHINA_A50",
    # 商品
    "XAUUSD",      # 黄金
    "USOIL",       # 原油
    # 加密货币
    "BTCUSD",      # 比特币
    # 外汇
    "EURUSD",
]

# 扩展周期列表
EXTENDED_TIMEFRAMES = ["MN1", "W1", "D1", "H4", "H1", "M15"]

# MT5品种名映射
SYMBOL_MAP = {
    "US_30": "US30",
    "US_500": "US500",
    "US_TECH100": "USTEC",
    "HK_50": "HK50",
    "CHINA_A50": "CHINA50",
    "XAUUSD": "XAUUSD",
    "USOIL": "USOIL",
    "BTCUSD": "BTCUSD",
    "EURUSD": "EURUSD",
}


def fetch_and_save_states(
    symbols: list,
    timeframes: list,
    days: int = 90,
    db_path: str = "data/h1_state.duckdb",
):
    """下载并保存State数据"""
    bridge = MT5Bridge(mt5_host="localhost", pub_port=5565, req_port=5566)
    db = H1StateDB(db_path)
    
    if not bridge.connect():
        logger.error("MT5连接失败")
        return
    
    end = datetime.now()
    start = end - timedelta(days=days)
    
    total_saved = 0
    
    for symbol in symbols:
        logger.info(f"\n{'='*50}")
        logger.info(f"处理品种: {symbol}")
        logger.info(f"{'='*50}")
        
        mt5_symbol = SYMBOL_MAP.get(symbol, symbol)
        
        try:
            # 拉取多周期数据
            logger.info(f"拉取 {mt5_symbol} 数据: {timeframes}")
            multi_data = bridge.fetch_multi_timeframe(mt5_symbol, timeframes, start, end)
            
            if not multi_data:
                logger.warning(f"{symbol} 无数据")
                continue
            
            # 检查各周期数据
            for tf in timeframes:
                df = multi_data.get(tf)
                if df is not None and not df.empty:
                    logger.info(f"  {tf}: {len(df)} 条")
                else:
                    logger.warning(f"  {tf}: 无数据")
            
            # 计算State (简化：使用H1作为基准对齐)
            h1_df = multi_data.get("H1")
            if h1_df is None or h1_df.empty:
                logger.warning(f"{symbol} 无H1数据，跳过")
                continue
            
            # 为每个H1 bar计算各周期state
            # 简化版：直接用hex值（实际应调用StateHexEngine）
            # 这里用模拟数据填充，后续接入真实计算
            logger.info(f"{symbol} 数据下载完成，等待State计算...")
            
        except Exception as e:
            logger.error(f"{symbol} 处理失败: {e}")
            continue
    
    bridge.disconnect()
    logger.info(f"\n总计保存: {total_saved} 条记录")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=EXTENDED_SYMBOLS, help="品种列表")
    parser.add_argument("--timeframes", nargs="+", default=EXTENDED_TIMEFRAMES, help="周期列表")
    parser.add_argument("--days", type=int, default=90, help="下载天数")
    parser.add_argument("--db", default="data/h1_state.duckdb", help="数据库路径")
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("扩展 State 数据下载")
    logger.info("="*60)
    logger.info(f"品种: {args.symbols}")
    logger.info(f"周期: {args.timeframes}")
    logger.info(f"天数: {args.days}")
    
    fetch_and_save_states(args.symbols, args.timeframes, args.days, args.db)


if __name__ == "__main__":
    main()
