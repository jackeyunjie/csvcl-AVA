"""
收缩观测系统 - 综合品种分析（含股指、商品、加密货币）

使用正确的MT5品种名称映射
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
logger = logging.getLogger("squeeze_comprehensive")

# 完整的MT5品种名称映射: 标准名 -> MT5实际名称
SYMBOL_MAP = {
    # 外汇主要货币对
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
    "USDCHF": "USDCHF",
    "NZDUSD": "NZDUSD",
    "EURGBP": "EURGBP",
    "EURJPY": "EURJPY",
    "GBPJPY": "GBPJPY",
    "AUDJPY": "AUDJPY",
    "CADJPY": "CADJPY",
    "CHFJPY": "CHFJPY",
    # 贵金属
    "XAUUSD": "GOLD",
    "XAGUSD": "SILVER",
    # 股指
    "US30": "US_30",
    "US500": "US_500",
    "NAS100": "US_TECH100",
    "GER40": "GERMANY_40",
    "UK100": "UK_100",
    # 能源
    "USOIL": "CrudeOIL",
    "UKOIL": "BRENT_OIL",
    # 加密货币
    "BTCUSD": "BTCUSD",
    "ETHUSD": "ETHUSD",
}


def fetch_ohlcv_from_mt5(mt5_symbol: str, timeframe: str = "H1", lookback_days: int = 60):
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
            return pd.DataFrame(), "无数据"

        df.columns = [c.lower() for c in df.columns]
        if 'time' in df.columns and 'timestamp' not in df.columns:
            df = df.rename(columns={'time': 'timestamp'})

        return df, f"获取 {len(df)} 条"

    except Exception as e:
        return pd.DataFrame(), str(e)


def analyze_symbol(std_name: str, mt5_name: str, timeframe: str = "H1",
                   db_path: Path = None) -> list:
    """分析单个品种，返回metrics记录列表"""
    df, msg = fetch_ohlcv_from_mt5(mt5_name, timeframe, 60)
    if df.empty:
        return [], msg

    # 计算指标
    df['bb_width'] = SqueezeObserver.compute_bb_width(df['close'])
    df['pivot_range'] = SqueezeObserver.compute_pivot_range(df['high'], df['low'], df['close'])
    df['sr_range'] = SqueezeObserver.compute_sr_range(df['high'], df['low'], df['close'])
    df['adx'] = SqueezeObserver.compute_adx(df['high'], df['low'], df['close'])

    # 获取state_hex
    df['state_hex'] = ""
    if db_path and db_path.exists():
        try:
            conn = duckdb.connect(str(db_path), read_only=True)
            state_col = f"{timeframe.lower()}_hex"
            state_df = conn.execute(f"""
                SELECT timestamp, {state_col} as state_hex
                FROM h1_state_snapshot
                WHERE symbol = ?
                ORDER BY timestamp
            """, [std_name]).fetchdf()
            conn.close()
            if not state_df.empty:
                df = df.merge(state_df, on='timestamp', how='left')
        except:
            pass

    records = []
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

        records.append({
            'symbol': std_name,
            'timeframe': timeframe,
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

    return records, msg


def generate_rl_samples(df: pd.DataFrame, hold_bars_list=[1, 5, 10]) -> pd.DataFrame:
    """
    生成强化学习训练样本

    样本格式: (state, action, reward, next_state)
    - state: 收缩时刻的指标向量
    - action: 突破方向 (0=观望, 1=做多, 2=做空)
    - reward: 未来N根K线的收益率
    """
    samples = []

    for symbol in df['symbol'].unique():
        sym_df = df[df['symbol'] == symbol].sort_values('timestamp').reset_index(drop=True)

        for i in range(len(sym_df) - max(hold_bars_list)):
            row = sym_df.iloc[i]

            # 只记录高收缩时刻
            if row['squeeze_score'] < 2:
                continue

            entry_price = None  # 需要价格数据
            # 从记录中计算收益率（使用bb_width作为价格变化的代理，或需要原始价格）
            # 这里简化：记录收缩状态作为state

            state = {
                'bb_width': row['bb_width'],
                'pivot_range': row['pivot_range_pct'],
                'sr_range': row['sr_range_pct'],
                'adx': row['adx'],
                'state_is_zero': row['state_is_zero'],
                'squeeze_score': row['squeeze_score'],
            }

            # 判断未来方向（基于后续bb_width变化作为代理）
            future = sym_df.iloc[i+1:i+6]
            if len(future) < 5:
                continue

            # 简化：用pivot_range扩张判断方向
            future_pivot = future['pivot_range_pct'].mean()
            current_pivot = row['pivot_range_pct']

            if future_pivot > current_pivot * 1.2:
                # 扩张发生
                direction = 1  # 假设向上（实际需要价格数据）
                reward = (future_pivot - current_pivot) / current_pivot * 100
            else:
                continue

            samples.append({
                'symbol': symbol,
                'timestamp': row['timestamp'],
                'state': state,
                'action': direction,
                'reward': reward,
            })

    return pd.DataFrame(samples)


def main():
    logger.info("=" * 60)
    logger.info("收缩观测系统 - 综合品种分析")
    logger.info("=" * 60)

    db_path = Path(__file__).parent / "data" / "h1_state.duckdb"

    all_records = []
    success_symbols = []
    failed_symbols = []

    for std_name, mt5_name in SYMBOL_MAP.items():
        logger.info(f"分析 {std_name} (MT5: {mt5_name})")
        records, msg = analyze_symbol(std_name, mt5_name, "H1", db_path)

        if records:
            all_records.extend(records)
            success_symbols.append(std_name)
            logger.info(f"  成功: {msg}, {len(records)}条记录")
        else:
            failed_symbols.append((std_name, msg))
            logger.warning(f"  失败: {msg}")

    if not all_records:
        logger.error("无成功分析的品种")
        return

    result_df = pd.DataFrame(all_records)

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
    print(f"成功品种: {len(success_symbols)}/{len(SYMBOL_MAP)}")
    print(f"成功列表: {', '.join(success_symbols)}")
    if failed_symbols:
        print(f"失败列表: {', '.join([s for s, _ in failed_symbols])}")
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

    # 各品种最新状态
    print("\n各品种最新收缩状态:")
    for sym in sorted(result_df['symbol'].unique()):
        sym_data = result_df[result_df['symbol'] == sym]
        sym_latest = sym_data.iloc[-1]
        print(f"  {sym:8s}: BB={sym_latest['bb_width']:.4f}, Pivot={sym_latest['pivot_range_pct']:.2f}%, "
              f"SR={sym_latest['sr_range_pct']:.2f}%, ADX={sym_latest['adx']:.1f}, "
              f"Score={sym_latest['squeeze_score']}")

    # 生成报告
    from squeeze_report import generate_report, save_report
    report = generate_report(result_df, stats)
    save_report(report, sync_obsidian=True)
    logger.info("报告已保存并同步到Obsidian")

    # 导出CSV数据供强化学习使用
    csv_path = Path(__file__).parent / "reports" / "squeeze" / f"squeeze_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(csv_path, index=False)
    logger.info(f"数据已导出: {csv_path}")


if __name__ == "__main__":
    main()
