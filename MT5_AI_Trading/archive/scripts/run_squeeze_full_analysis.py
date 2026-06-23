"""
收缩观测系统 - 完整品种分析

使用MT5实际品种名称映射，分析更多品种
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
logger = logging.getLogger("squeeze_full")

# 品种名称映射: 标准名 -> MT5实际名称
SYMBOL_MAP = {
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
    "USDCHF": "USDCHF",
    "NZDUSD": "NZDUSD",
    "EURGBP": "EURGBP",
    "XAUUSD": "GOLD",        # MT5中GOLD=XAUUSD
    "US30": "US30",           # 可能需要其他名称
    "US500": "US500",
    "NAS100": "NAS100",
    "GER30": "GER30",
    "JP225": "JP225",
    "UK100": "UK100",
    "USOIL": "USOIL",
    "BTCUSD": "BTCUSD",
    "ETHUSD": "ETHUSD",
    "EURJPY": "EURJPY",
    "GBPJPY": "GBPJPY",
}


def fetch_ohlcv_from_mt5(symbol: str, mt5_symbol: str, timeframe: str = "H1", lookback_days: int = 60):
    """从MT5获取OHLCV数据"""
    try:
        from backtest_platform.data_layer import MT5DataBridge

        bridge = MT5DataBridge()
        if not bridge.connect():
            return pd.DataFrame(), "MT5连接失败"

        end = datetime.now()
        start = end - timedelta(days=lookback_days)
        df = bridge.fetch_ohlcv(mt5_symbol, timeframe, start, end)
        bridge.disconnect()

        if df.empty:
            return pd.DataFrame(), f"无数据"

        df.columns = [c.lower() for c in df.columns]
        if 'time' in df.columns and 'timestamp' not in df.columns:
            df = df.rename(columns={'time': 'timestamp'})

        return df, f"获取 {len(df)} 条"

    except Exception as e:
        return pd.DataFrame(), str(e)


def main():
    logger.info("=" * 60)
    logger.info("收缩观测系统 - 完整品种分析")
    logger.info("=" * 60)

    db_path = Path(__file__).parent / "data" / "h1_state.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    db_symbols = set(r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM h1_state_snapshot"
    ).fetchall())
    conn.close()

    logger.info(f"数据库品种数: {len(db_symbols)}")

    # 测试品种列表（优先分析主要品种）
    test_symbols = [
        ("EURUSD", "EURUSD"),
        ("GBPUSD", "GBPUSD"),
        ("USDJPY", "USDJPY"),
        ("AUDUSD", "AUDUSD"),
        ("USDCAD", "USDCAD"),
        ("USDCHF", "USDCHF"),
        ("NZDUSD", "NZDUSD"),
        ("EURGBP", "EURGBP"),
        ("EURJPY", "EURJPY"),
        ("GBPJPY", "GBPJPY"),
        ("XAUUSD", "GOLD"),
        ("USOIL", "XTIUSD"),
    ]

    all_records = []
    success_count = 0

    for std_name, mt5_name in test_symbols:
        logger.info(f"分析 {std_name} (MT5: {mt5_name})")

        df, msg = fetch_ohlcv_from_mt5(std_name, mt5_name, "H1", 60)

        if df.empty:
            logger.warning(f"  {std_name}: {msg}")
            continue

        success_count += 1
        logger.info(f"  {msg}")

        # 计算指标
        df['bb_width'] = SqueezeObserver.compute_bb_width(df['close'])
        df['pivot_range'] = SqueezeObserver.compute_pivot_range(df['high'], df['low'], df['close'])
        df['sr_range'] = SqueezeObserver.compute_sr_range(df['high'], df['low'], df['close'])
        df['adx'] = SqueezeObserver.compute_adx(df['high'], df['low'], df['close'])

        # 获取state_hex
        state_col = "h1_hex"
        try:
            conn = duckdb.connect(str(db_path), read_only=True)
            state_df = conn.execute(f"""
                SELECT timestamp, {state_col} as state_hex
                FROM h1_state_snapshot
                WHERE symbol = ?
                ORDER BY timestamp
            """, [std_name]).fetchdf()
            conn.close()
            if not state_df.empty:
                df = df.merge(state_df, on='timestamp', how='left')
            else:
                df['state_hex'] = ""
        except:
            df['state_hex'] = ""

        # 逐行计算
        for i in range(30, len(df)):
            row = df.iloc[i]

            bb_hist = df['bb_width'].iloc[:i+1].dropna()
            bb_20 = bb_hist.quantile(0.20) if len(bb_hist) >= 20 else np.nan
            bb_10 = bb_hist.quantile(0.10) if len(bb_hist) >= 20 else np.nan
            bb_5 = bb_hist.quantile(0.05) if len(bb_hist) >= 20 else np.nan

            pivot_hist = df['pivot_range'].iloc[:i+1].dropna()
            pivot_20 = pivot_hist.quantile(0.20) if len(pivot_hist) >= 20 else np.nan

            sr_hist = df['sr_range'].iloc[:i+1].dropna()
            sr_20 = sr_hist.quantile(0.20) if len(sr_hist) >= 20 else np.nan

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
                'symbol': std_name,
                'timeframe': 'H1',
                'timestamp': row['timestamp'],
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
    logger.info(f"分析完成: {success_count}个品种, {len(result_df)}条记录")

    if result_df.empty:
        logger.warning("无分析结果")
        return

    # 统计
    stats = {
        'total_records': len(result_df),
        'total_symbols': result_df['symbol'].nunique(),
        'timeframes': ['H1'],
        'state_zero_count': int(result_df['state_is_zero'].sum()),
        'state_zero_pct': float(result_df['state_is_zero'].mean() * 100),
        'bb_squeezed_20_count': int(result_df['bb_squeezed_20'].sum()),
        'bb_squeezed_20_pct': float(result_df['bb_squeezed_20'].mean() * 100),
        'bb_squeezed_10_count': int(result_df['bb_squeezed_10'].sum()),
        'bb_squeezed_10_pct': float(result_df['bb_squeezed_10'].mean() * 100),
        'bb_squeezed_5_count': int(result_df['bb_squeezed_5'].sum()),
        'bb_squeezed_5_pct': float(result_df['bb_squeezed_5'].mean() * 100),
        'pivot_squeezed_count': int(result_df['pivot_squeezed'].sum()),
        'pivot_squeezed_pct': float(result_df['pivot_squeezed'].mean() * 100),
        'sr_squeezed_count': int(result_df['sr_squeezed'].sum()),
        'sr_squeezed_pct': float(result_df['sr_squeezed'].mean() * 100),
        'adx_lt_20_count': int(result_df['adx_lt_20'].sum()),
        'adx_lt_20_pct': float(result_df['adx_lt_20'].mean() * 100),
        'adx_lt_13_count': int(result_df['adx_lt_13'].sum()),
        'adx_lt_13_pct': float(result_df['adx_lt_13'].mean() * 100),
        'adx_lt_9_count': int(result_df['adx_lt_9'].sum()),
        'adx_lt_9_pct': float(result_df['adx_lt_9'].mean() * 100),
        'squeeze_score_dist': result_df['squeeze_score'].value_counts().to_dict(),
        'high_squeeze_count': int((result_df['squeeze_score'] >= 3).sum()),
        'high_squeeze_pct': float((result_df['squeeze_score'] >= 3).mean() * 100),
    }

    # 打印摘要
    print("\n" + "=" * 60)
    print("收缩观测报告摘要")
    print("=" * 60)
    print(f"成功分析品种: {success_count}")
    print(f"总记录数: {stats['total_records']:,}")
    print(f"State=0占比: {stats['state_zero_pct']:.2f}%")
    print(f"BB收缩(20%)占比: {stats['bb_squeezed_20_pct']:.2f}%")
    print(f"枢轴收缩占比: {stats['pivot_squeezed_pct']:.2f}%")
    print(f"SR间距收缩占比: {stats['sr_squeezed_pct']:.2f}%")
    print(f"ADX<20占比: {stats['adx_lt_20_pct']:.2f}%")
    print(f"ADX<13占比: {stats['adx_lt_13_pct']:.2f}%")
    print(f"ADX<9占比: {stats['adx_lt_9_pct']:.2f}%")
    print(f"高收缩(>=3)占比: {stats['high_squeeze_pct']:.2f}%")
    print("=" * 60)

    # 当前高收缩
    latest_ts = result_df['timestamp'].max()
    latest = result_df[result_df['timestamp'] == latest_ts]
    high_squeeze = latest[latest['squeeze_score'] >= 2].sort_values('squeeze_score', ascending=False)

    if not high_squeeze.empty:
        print("\n当前高收缩品种（分数>=2）:")
        for _, row in high_squeeze.iterrows():
            print(f"  {row['symbol']}: 分数={row['squeeze_score']}, 条件=[{row['squeeze_conditions']}]")
    else:
        print("\n当前无高收缩品种")

    # 各品种最新收缩状态
    print("\n各品种最新收缩状态:")
    for sym in result_df['symbol'].unique():
        sym_latest = result_df[result_df['symbol'] == sym].iloc[-1]
        print(f"  {sym}: BB={sym_latest['bb_width']:.4f}, Pivot={sym_latest['pivot_range_pct']:.2f}%, "
              f"SR={sym_latest['sr_range_pct']:.2f}%, ADX={sym_latest['adx']:.1f}, "
              f"Score={sym_latest['squeeze_score']}")

    # 生成报告
    from squeeze_report import generate_report, save_report
    report = generate_report(result_df, stats)
    save_report(report, sync_obsidian=True)
    logger.info("报告已保存并同步到Obsidian")


if __name__ == "__main__":
    main()
