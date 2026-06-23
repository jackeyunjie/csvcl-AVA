"""
收缩观测系统 - 实际数据分析运行器

从MT5获取OHLCV数据，结合数据库中的state_hex，
运行完整收缩观测分析并生成报告。
"""
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent / "python"))

import pandas as pd
import numpy as np
import duckdb

from analytics.squeeze_observer import SqueezeObserver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("squeeze_analysis")


def fetch_ohlcv_from_mt5(symbol: str, timeframe: str = "H1", lookback_days: int = 60):
    """从MT5获取OHLCV数据"""
    try:
        from backtest_platform.data_layer import MT5DataBridge

        bridge = MT5DataBridge()
        if not bridge.connect():
            logger.warning(f"MT5连接失败: {symbol}")
            return pd.DataFrame()

        end = datetime.now()
        start = end - timedelta(days=lookback_days)
        df = bridge.fetch_ohlcv(symbol, timeframe, start, end)
        bridge.disconnect()

        if df.empty:
            logger.warning(f"MT5无数据: {symbol} {timeframe}")
            return pd.DataFrame()

        # 标准化列名
        df.columns = [c.lower() for c in df.columns]
        if 'time' in df.columns and 'timestamp' not in df.columns:
            df = df.rename(columns={'time': 'timestamp'})

        logger.info(f"  {symbol}: 获取 {len(df)} 条 {timeframe} 数据")
        return df

    except Exception as e:
        logger.warning(f"MT5获取失败 {symbol}: {e}")
        return pd.DataFrame()


def analyze_with_mt5_data(observer: SqueezeObserver, symbols: list,
                          timeframes: list = None) -> pd.DataFrame:
    """
    使用MT5数据进行分析

    流程：
    1. 从MT5获取各品种OHLCV
    2. 从数据库获取state_hex
    3. 计算收缩指标
    """
    if timeframes is None:
        timeframes = ["H1"]

    all_records = []
    total = len(symbols) * len(timeframes)
    processed = 0

    for symbol in symbols:
        for tf in timeframes:
            processed += 1
            logger.info(f"[{processed}/{total}] 分析 {symbol} {tf}")

            # 从MT5获取数据
            df = fetch_ohlcv_from_mt5(symbol, tf, lookback_days=60)
            if df.empty or len(df) < 30:
                logger.warning(f"  {symbol} {tf}: 数据不足，跳过")
                continue

            # 计算指标
            df['bb_width'] = SqueezeObserver.compute_bb_width(df['close'])
            df['pivot_range'] = SqueezeObserver.compute_pivot_range(
                df['high'], df['low'], df['close'])
            df['sr_range'] = SqueezeObserver.compute_sr_range(
                df['high'], df['low'], df['close'])
            df['adx'] = SqueezeObserver.compute_adx(
                df['high'], df['low'], df['close'])

            # 从数据库获取state_hex
            state_col = f"{tf.lower()}_hex"
            try:
                state_df = observer.db.execute(f"""
                    SELECT timestamp, {state_col} as state_hex
                    FROM h1_state_snapshot
                    WHERE symbol = ?
                    ORDER BY timestamp
                """, [symbol]).fetchdf()
                if not state_df.empty:
                    df = df.merge(state_df, on='timestamp', how='left')
                else:
                    df['state_hex'] = ""
            except Exception as e:
                logger.warning(f"  获取state_hex失败: {e}")
                df['state_hex'] = ""

            # 逐行计算收缩指标
            for i in range(len(df)):
                if i < 30:
                    continue

                row = df.iloc[i]
                ts = row['timestamp']

                # 分位数计算
                bb_hist = df['bb_width'].iloc[:i+1].dropna()
                bb_20 = bb_hist.quantile(0.20) if len(bb_hist) >= 20 else np.nan
                bb_10 = bb_hist.quantile(0.10) if len(bb_hist) >= 20 else np.nan
                bb_5 = bb_hist.quantile(0.05) if len(bb_hist) >= 20 else np.nan

                pivot_hist = df['pivot_range'].iloc[:i+1].dropna()
                pivot_20 = pivot_hist.quantile(0.20) if len(pivot_hist) >= 20 else np.nan

                sr_hist = df['sr_range'].iloc[:i+1].dropna()
                sr_20 = sr_hist.quantile(0.20) if len(sr_hist) >= 20 else np.nan

                # 判定条件
                bb_s20 = row['bb_width'] <= bb_20 if not pd.isna(row['bb_width']) and not pd.isna(bb_20) else False
                bb_s10 = row['bb_width'] <= bb_10 if not pd.isna(row['bb_width']) and not pd.isna(bb_10) else False
                bb_s5 = row['bb_width'] <= bb_5 if not pd.isna(row['bb_width']) and not pd.isna(bb_5) else False
                pivot_sq = row['pivot_range'] <= pivot_20 if not pd.isna(row['pivot_range']) and not pd.isna(pivot_20) else False
                sr_sq = row['sr_range'] <= sr_20 if not pd.isna(row['sr_range']) and not pd.isna(sr_20) else False
                adx_val = row['adx'] if not pd.isna(row['adx']) else np.nan
                state0 = str(row.get('state_hex', '')) == '0'

                conditions = []
                if bb_s20: conditions.append("BB_20")
                if bb_s10: conditions.append("BB_10")
                if pivot_sq: conditions.append("Pivot")
                if sr_sq: conditions.append("SR_Squeeze")
                if adx_val < 20: conditions.append("ADX<20")
                if adx_val < 13: conditions.append("ADX<13")
                if adx_val < 9: conditions.append("ADX<9")
                if state0: conditions.append("State=0")

                all_records.append({
                    'symbol': symbol,
                    'timeframe': tf,
                    'timestamp': ts,
                    'bb_width': row['bb_width'],
                    'bb_squeezed_20': bb_s20,
                    'bb_squeezed_10': bb_s10,
                    'bb_squeezed_5': bb_s5,
                    'pivot_range_pct': row['pivot_range'],
                    'pivot_squeezed': pivot_sq,
                    'sr_range_pct': row['sr_range'],
                    'sr_squeezed': sr_sq,
                    'adx': adx_val,
                    'adx_lt_20': adx_val < 20 if not pd.isna(adx_val) else False,
                    'adx_lt_13': adx_val < 13 if not pd.isna(adx_val) else False,
                    'adx_lt_9': adx_val < 9 if not pd.isna(adx_val) else False,
                    'state_hex': row.get('state_hex', ''),
                    'state_is_zero': state0,
                    'squeeze_score': len(conditions),
                    'squeeze_conditions': ','.join(conditions),
                })

    result_df = pd.DataFrame(all_records)
    logger.info(f"分析完成: {len(result_df)} 条记录")
    return result_df


def main():
    logger.info("=" * 60)
    logger.info("收缩观测系统 - 实际数据分析")
    logger.info("=" * 60)

    # 获取品种列表
    db_path = Path(__file__).parent / "data" / "h1_state.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    symbols = [r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM h1_state_snapshot ORDER BY symbol"
    ).fetchall()]
    conn.close()

    logger.info(f"数据库品种数: {len(symbols)}")

    # 选择主要品种进行分析（先测试10个）
    priority_symbols = [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
        "XAUUSD", "US30", "US500", "NAS100", "GER30"
    ]
    # 过滤出数据库中存在的品种
    available_symbols = [s for s in priority_symbols if s in symbols]
    logger.info(f"优先分析品种: {available_symbols}")

    # 运行分析
    with SqueezeObserver(str(db_path)) as observer:
        df = analyze_with_mt5_data(observer, available_symbols, ["H1"])

        if df.empty:
            logger.warning("无分析结果")
            return

        # 统计
        stats = observer.summarize_squeeze_stats(df)

        # 打印摘要
        print("\n" + "=" * 60)
        print("收缩观测报告摘要")
        print("=" * 60)
        print(f"品种数: {stats.get('total_symbols', 0)}")
        print(f"记录数: {stats.get('total_records', 0):,}")
        print(f"State=0占比: {stats.get('state_zero_pct', 0):.2f}%")
        print(f"BB收缩(20%)占比: {stats.get('bb_squeezed_20_pct', 0):.2f}%")
        print(f"枢轴收缩占比: {stats.get('pivot_squeezed_pct', 0):.2f}%")
        print(f"SR间距收缩占比: {stats.get('sr_squeezed_pct', 0):.2f}%")
        print(f"ADX<20占比: {stats.get('adx_lt_20_pct', 0):.2f}%")
        print(f"ADX<13占比: {stats.get('adx_lt_13_pct', 0):.2f}%")
        print(f"ADX<9占比: {stats.get('adx_lt_9_pct', 0):.2f}%")
        print(f"高收缩(>=3)占比: {stats.get('high_squeeze_pct', 0):.2f}%")
        print("=" * 60)

        # 当前高收缩品种
        latest_ts = df['timestamp'].max()
        latest = df[df['timestamp'] == latest_ts]
        high_squeeze = latest[latest['squeeze_score'] >= 2].sort_values('squeeze_score', ascending=False)

        if not high_squeeze.empty:
            print("\n当前高收缩品种（分数>=2）:")
            for _, row in high_squeeze.head(10).iterrows():
                print(f"  {row['symbol']}: 分数={row['squeeze_score']}, 条件=[{row['squeeze_conditions']}]")

        # 生成报告
        from squeeze_report import generate_report, save_report
        report = generate_report(df, stats)
        save_report(report, sync_obsidian=True)
        logger.info("报告已保存并同步到Obsidian")


if __name__ == "__main__":
    main()
