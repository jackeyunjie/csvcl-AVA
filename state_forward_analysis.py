"""
state_forward_analysis.py
=========================
基于 Hermass State DuckDB 的前向收益分析

功能:
1. 读取 state_hermass.duckdb 中的 state_snapshots (MN1/W1/D1 state_hex)
2. 从 MT5 补全对应品种日线的 close 价格
3. 对每个品种的每一天计算:
   - FORWARD_RETURN_1D = (close[t+1] - close[t]) / close[t]
   - FORWARD_RETURN_5D = (close[t+5] - close[t]) / close[t]
   - FORWARD_RETURN_20D = (close[t+20] - close[t]) / close[t]
4. 按 State 维度统计前向收益分布 (单周期 / 组合 / EF共振 / 状态池)
5. 结果写回 DuckDB 并导出 CSV/JSON 报告

作者: AI Assistant
日期: 2026-05-26
"""

import json
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import duckdb

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
    print("[WARN] MetaTrader5 未安装，将无法从MT5获取价格数据")


# =====================================================================
# 配置区
# =====================================================================
DB_PATH = Path("MT5_AI_Trading/data/state_hermass.duckdb")
OUTPUT_DIR = Path("MT5_AI_Trading/data")
OUTPUT_DB_PATH = OUTPUT_DIR / "state_forward_analysis.duckdb"

# 前向收益周期
FORWARD_PERIODS = {
    "1d": 1,
    "5d": 5,
    "20d": 20,
}

# =====================================================================
# 1. 数据加载: 从 DuckDB 读取 State 快照
# =====================================================================
def load_state_snapshots(db_path: Path) -> pd.DataFrame:
    """读取 Hermass State 快照，返回 DataFrame"""
    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在: {db_path}")

    conn = duckdb.connect(str(db_path), read_only=True)
    df = conn.execute("""
        SELECT
            symbol,
            perspective,
            date,
            mn1_hex,
            w1_hex,
            d1_hex,
            mn1_score,
            w1_score,
            d1_score,
            ef_count
        FROM state_snapshots
        ORDER BY symbol, date
    """).fetchdf()
    conn.close()

    df["date"] = pd.to_datetime(df["date"]).dt.date
    print(f"[DB] 加载 {len(df)} 条 State 记录, {df['symbol'].nunique()} 个品种")
    return df


# =====================================================================
# 2. 价格补全: 从 MT5 获取日线 close
# =====================================================================
def fetch_close_prices(symbols: List[str], dates_map: Dict[str, set]) -> pd.DataFrame:
    """
    从 MT5 获取指定品种的日线 close 价格
    参数:
        symbols: 品种列表
        dates_map: {symbol: {date, ...}} 需要补全的日期集合
    返回:
        DataFrame[symbol, date, close]
    """
    if mt5 is None:
        raise RuntimeError("MetaTrader5 未安装，无法获取价格数据")

    if not mt5.initialize():
        raise RuntimeError("MT5 初始化失败，请确认 MT5 已运行")

    all_price_rows: List[dict] = []

    for sym in symbols:
        needed_dates = dates_map.get(sym, set())
        if not needed_dates:
            continue

        min_date = min(needed_dates)
        max_date = max(needed_dates)
        # 多取一点数据，确保能算 forward return
        max_date = max_date + timedelta(days=max(FORWARD_PERIODS.values()) + 5)

        # MT5 copy_rates_range 需要 datetime
        rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_D1,
                                     datetime.combine(min_date, datetime.min.time()),
                                     datetime.combine(max_date, datetime.min.time()))
        if rates is None or len(rates) == 0:
            print(f"  [WARN] {sym}: MT5 无数据")
            continue

        for r in rates:
            bar_date = datetime.fromtimestamp(r[0]).date()
            all_price_rows.append({
                "symbol": sym,
                "date": bar_date,
                "close": float(r[4]),
            })

    mt5.shutdown()
    df = pd.DataFrame(all_price_rows)
    df = df.drop_duplicates(subset=["symbol", "date"], keep="first")
    print(f"[MT5] 加载 {len(df)} 条价格记录")
    return df


def load_prices_from_csv_fallback(symbols: List[str], data_dir: Path = Path("MT5_AI_Trading/data")) -> pd.DataFrame:
    """
    如果没有 MT5，尝试从本地 CSV/Parquet 加载价格数据
    期望文件名格式: {symbol}_D1.csv 或 prices.parquet
    """
    all_rows = []
    for sym in symbols:
        # 尝试多种可能的文件名
        candidates = [
            data_dir / f"{sym}_D1.csv",
            data_dir / f"{sym}.csv",
            data_dir / "prices.parquet",
        ]
        for cand in candidates:
            if not cand.exists():
                continue
            try:
                if cand.suffix == ".parquet":
                    df = pd.read_parquet(cand)
                    df = df[df["symbol"] == sym]
                else:
                    df = pd.read_csv(cand)
                    if "symbol" not in df.columns:
                        df["symbol"] = sym
                if "close" in df.columns and "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"]).dt.date
                    all_rows.append(df[["symbol", "date", "close"]])
                    break
            except Exception:
                continue
    if not all_rows:
        return pd.DataFrame(columns=["symbol", "date", "close"])
    return pd.concat(all_rows, ignore_index=True).drop_duplicates(subset=["symbol", "date"])


# =====================================================================
# 3. 核心计算: Forward Return
# =====================================================================
def compute_forward_returns(df_state: pd.DataFrame, df_price: pd.DataFrame) -> pd.DataFrame:
    """
    将 State 与价格合并，计算各周期 forward return
    """
    # 合并
    df = pd.merge(df_state, df_price, on=["symbol", "date"], how="inner")
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # 计算 forward return
    for label, shift in FORWARD_PERIODS.items():
        col = f"forward_return_{label}"
        # 使用 groupby + shift 确保跨品种不串位
        df[col] = df.groupby("symbol")["close"].shift(-shift)
        df[col] = (df[col] - df["close"]) / df["close"]

    # 删除末尾无法计算 forward return 的行
    df = df.dropna(subset=[f"forward_return_{list(FORWARD_PERIODS.keys())[0]}"])
    return df


# =====================================================================
# 4. 统计分析
# =====================================================================
def analyze_by_single_state(df: pd.DataFrame, state_col: str, state_name: str) -> pd.DataFrame:
    """按单周期 state_hex 统计前向收益"""
    agg_exprs = {
        "n": (state_col, "size"),
        "avg_ret_1d_pct": (f"forward_return_1d", lambda x: round(x.mean() * 100, 4)),
        "avg_ret_5d_pct": (f"forward_return_5d", lambda x: round(x.mean() * 100, 4)),
        "avg_ret_20d_pct": (f"forward_return_20d", lambda x: round(x.mean() * 100, 4)),
        "win_rate_1d": (f"forward_return_1d", lambda x: round((x > 0).mean() * 100, 2)),
        "win_rate_5d": (f"forward_return_5d", lambda x: round((x > 0).mean() * 100, 2)),
        "win_rate_20d": (f"forward_return_20d", lambda x: round((x > 0).mean() * 100, 2)),
        "vol_5d_pct": (f"forward_return_5d", lambda x: round(x.std() * 100, 4)),
        "sharpe_5d": (f"forward_return_5d", lambda x: round(x.mean() / x.std() if x.std() > 0 else 0, 4)),
    }
    result = df.groupby(state_col).agg(**{k: pd.NamedAgg(column=v[0], aggfunc=v[1]) for k, v in agg_exprs.items()})
    result = result.reset_index().rename(columns={state_col: "state_hex"})
    result["state_type"] = state_name
    result = result.sort_values("avg_ret_5d_pct", ascending=False)
    return result


def analyze_by_ef_count(df: pd.DataFrame) -> pd.DataFrame:
    """按 EF 共振数统计"""
    agg_exprs = {
        "n": ("ef_count", "size"),
        "avg_ret_1d_pct": ("forward_return_1d", lambda x: round(x.mean() * 100, 4)),
        "avg_ret_5d_pct": ("forward_return_5d", lambda x: round(x.mean() * 100, 4)),
        "avg_ret_20d_pct": ("forward_return_20d", lambda x: round(x.mean() * 100, 4)),
        "win_rate_1d": ("forward_return_1d", lambda x: round((x > 0).mean() * 100, 2)),
        "win_rate_5d": ("forward_return_5d", lambda x: round((x > 0).mean() * 100, 2)),
        "win_rate_20d": ("forward_return_20d", lambda x: round((x > 0).mean() * 100, 2)),
        "vol_5d_pct": ("forward_return_5d", lambda x: round(x.std() * 100, 4)),
        "sharpe_5d": ("forward_return_5d", lambda x: round(x.mean() / x.std() if x.std() > 0 else 0, 4)),
    }
    result = df.groupby("ef_count").agg(**{k: pd.NamedAgg(column=v[0], aggfunc=v[1]) for k, v in agg_exprs.items()})
    result = result.reset_index()
    result = result.sort_values("ef_count", ascending=False)
    return result


def analyze_by_pool_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    按状态池 pool_id = W1:{w1_hex}|MN1:{mn1_hex} 统计
    """
    df["pool_id"] = "W1:" + df["w1_hex"].astype(str) + "|MN1:" + df["mn1_hex"].astype(str)
    agg_exprs = {
        "n": ("pool_id", "size"),
        "avg_ret_1d_pct": ("forward_return_1d", lambda x: round(x.mean() * 100, 4)),
        "avg_ret_5d_pct": ("forward_return_5d", lambda x: round(x.mean() * 100, 4)),
        "avg_ret_20d_pct": ("forward_return_20d", lambda x: round(x.mean() * 100, 4)),
        "win_rate_1d": ("forward_return_1d", lambda x: round((x > 0).mean() * 100, 2)),
        "win_rate_5d": ("forward_return_5d", lambda x: round((x > 0).mean() * 100, 2)),
        "win_rate_20d": ("forward_return_20d", lambda x: round((x > 0).mean() * 100, 2)),
        "vol_5d_pct": ("forward_return_5d", lambda x: round(x.std() * 100, 4)),
        "sharpe_5d": ("forward_return_5d", lambda x: round(x.mean() / x.std() if x.std() > 0 else 0, 4)),
        "ef_count_avg": ("ef_count", "mean"),
    }
    result = df.groupby("pool_id").agg(**{k: pd.NamedAgg(column=v[0], aggfunc=v[1]) for k, v in agg_exprs.items()})
    result = result.reset_index()
    result = result.sort_values("avg_ret_5d_pct", ascending=False)
    return result


def analyze_by_symbol_state(df: pd.DataFrame) -> pd.DataFrame:
    """按品种 + D1 state 统计"""
    agg_exprs = {
        "n": ("symbol", "size"),
        "avg_ret_1d_pct": ("forward_return_1d", lambda x: round(x.mean() * 100, 4)),
        "avg_ret_5d_pct": ("forward_return_5d", lambda x: round(x.mean() * 100, 4)),
        "win_rate_5d": ("forward_return_5d", lambda x: round((x > 0).mean() * 100, 2)),
    }
    result = df.groupby(["symbol", "d1_hex"]).agg(**{k: pd.NamedAgg(column=v[0], aggfunc=v[1]) for k, v in agg_exprs.items()})
    result = result.reset_index()
    result = result[result["n"] >= 3]  # 至少3个样本
    result = result.sort_values("avg_ret_5d_pct", ascending=False)
    return result


# =====================================================================
# 5. 存储结果
# =====================================================================
def save_results(df_merged: pd.DataFrame,
                 stats_single: pd.DataFrame,
                 stats_ef: pd.DataFrame,
                 stats_pool: pd.DataFrame,
                 stats_symbol_state: pd.DataFrame,
                 output_db: Path) -> None:
    """将结果保存到 DuckDB 和 CSV"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 如果数据库已存在则删除（或连接覆盖）
    if output_db.exists():
        output_db.unlink()

    conn = duckdb.connect(str(output_db))

    # 5.1 主表: 每个品种每天的 state + forward return
    conn.execute("""
        CREATE TABLE state_forward (
            symbol VARCHAR,
            perspective VARCHAR,
            date DATE,
            mn1_hex VARCHAR,
            w1_hex VARCHAR,
            d1_hex VARCHAR,
            mn1_score INTEGER,
            w1_score INTEGER,
            d1_score INTEGER,
            ef_count INTEGER,
            close DOUBLE,
            forward_return_1d DOUBLE,
            forward_return_5d DOUBLE,
            forward_return_20d DOUBLE
        )
    """)
    conn.register("df_merged", df_merged)
    conn.execute("INSERT INTO state_forward SELECT * FROM df_merged")

    # 5.2 单周期统计表
    conn.execute("""
        CREATE TABLE stats_single_state (
            state_hex VARCHAR,
            state_type VARCHAR,
            n INTEGER,
            avg_ret_1d_pct DOUBLE,
            avg_ret_5d_pct DOUBLE,
            avg_ret_20d_pct DOUBLE,
            win_rate_1d DOUBLE,
            win_rate_5d DOUBLE,
            win_rate_20d DOUBLE,
            vol_5d_pct DOUBLE,
            sharpe_5d DOUBLE
        )
    """)
    conn.register("stats_single", stats_single)
    conn.execute("INSERT INTO stats_single_state SELECT * FROM stats_single")

    # 5.3 EF 统计表
    conn.execute("""
        CREATE TABLE stats_ef (
            ef_count INTEGER,
            n INTEGER,
            avg_ret_1d_pct DOUBLE,
            avg_ret_5d_pct DOUBLE,
            avg_ret_20d_pct DOUBLE,
            win_rate_1d DOUBLE,
            win_rate_5d DOUBLE,
            win_rate_20d DOUBLE,
            vol_5d_pct DOUBLE,
            sharpe_5d DOUBLE
        )
    """)
    conn.register("stats_ef", stats_ef)
    conn.execute("INSERT INTO stats_ef SELECT * FROM stats_ef")

    # 5.4 Pool 统计表
    conn.execute("""
        CREATE TABLE stats_pool (
            pool_id VARCHAR,
            n INTEGER,
            avg_ret_1d_pct DOUBLE,
            avg_ret_5d_pct DOUBLE,
            avg_ret_20d_pct DOUBLE,
            win_rate_1d DOUBLE,
            win_rate_5d DOUBLE,
            win_rate_20d DOUBLE,
            vol_5d_pct DOUBLE,
            sharpe_5d DOUBLE,
            ef_count_avg DOUBLE
        )
    """)
    conn.register("stats_pool", stats_pool)
    conn.execute("INSERT INTO stats_pool SELECT * FROM stats_pool")

    # 5.5 品种-State 统计表
    conn.execute("""
        CREATE TABLE stats_symbol_state (
            symbol VARCHAR,
            d1_hex VARCHAR,
            n INTEGER,
            avg_ret_1d_pct DOUBLE,
            avg_ret_5d_pct DOUBLE,
            win_rate_5d DOUBLE
        )
    """)
    conn.register("stats_symbol_state", stats_symbol_state)
    conn.execute("INSERT INTO stats_symbol_state SELECT * FROM stats_symbol_state")

    conn.commit()
    conn.close()

    # 导出 CSV
    df_merged.to_csv(OUTPUT_DIR / "state_forward_merged.csv", index=False, encoding="utf-8-sig")
    stats_single.to_csv(OUTPUT_DIR / "stats_single_state.csv", index=False, encoding="utf-8-sig")
    stats_ef.to_csv(OUTPUT_DIR / "stats_ef.csv", index=False, encoding="utf-8-sig")
    stats_pool.to_csv(OUTPUT_DIR / "stats_pool.csv", index=False, encoding="utf-8-sig")
    stats_symbol_state.to_csv(OUTPUT_DIR / "stats_symbol_state.csv", index=False, encoding="utf-8-sig")

    # 导出 JSON 报告
    report = {
        "generated_at": datetime.now().isoformat(),
        "source_db": str(DB_PATH),
        "total_samples": len(df_merged),
        "symbols": int(df_merged["symbol"].nunique()),
        "date_range": {
            "start": str(df_merged["date"].min()),
            "end": str(df_merged["date"].max()),
        },
        "top_mn1_states": stats_single[stats_single["state_type"] == "MN1"].head(10).to_dict("records"),
        "top_w1_states": stats_single[stats_single["state_type"] == "W1"].head(10).to_dict("records"),
        "top_d1_states": stats_single[stats_single["state_type"] == "D1"].head(10).to_dict("records"),
        "ef_analysis": stats_ef.to_dict("records"),
        "top_pools": stats_pool.head(20).to_dict("records"),
    }
    with open(OUTPUT_DIR / "state_forward_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    print(f"[Save] 结果已保存到 {output_db}")
    print(f"[Save] CSV/JSON 已导出到 {OUTPUT_DIR}")


# =====================================================================
# 6. 主流程
# =====================================================================
def main():
    print("=" * 70)
    print(" State Forward Analysis — Hermass Schema")
    print(" FORWARD_RETURN_1D = (close[t+1] - close[t]) / close[t]")
    print("=" * 70)

    # 6.1 加载 State 数据
    df_state = load_state_snapshots(DB_PATH)
    if df_state.empty:
        print("[FATAL] State 数据为空")
        sys.exit(1)

    # 6.2 准备需要补全的价格日期
    symbols = df_state["symbol"].unique().tolist()
    dates_map: Dict[str, set] = {}
    for sym in symbols:
        dates_map[sym] = set(df_state[df_state["symbol"] == sym]["date"].unique())

    # 6.3 获取价格数据
    print("\n[2/5] 获取价格数据...")
    try:
        df_price = fetch_close_prices(symbols, dates_map)
    except Exception as e:
        print(f"  [WARN] 从 MT5 获取失败: {e}")
        print("  [INFO] 尝试本地 CSV fallback...")
        df_price = load_prices_from_csv_fallback(symbols)

    if df_price.empty:
        print("[FATAL] 无法获取任何价格数据")
        sys.exit(1)

    # 6.4 计算 Forward Return
    print("\n[3/5] 计算 Forward Return...")
    df_merged = compute_forward_returns(df_state, df_price)
    print(f"  合并后样本: {len(df_merged)} 条")
    if len(df_merged) == 0:
        print("[FATAL] State 与价格数据日期无交集，请检查数据一致性")
        sys.exit(1)

    # 6.5 统计分析
    print("\n[4/5] 统计分析...")

    # 单周期分析
    stats_mn1 = analyze_by_single_state(df_merged, "mn1_hex", "MN1")
    stats_w1 = analyze_by_single_state(df_merged, "w1_hex", "W1")
    stats_d1 = analyze_by_single_state(df_merged, "d1_hex", "D1")
    stats_single = pd.concat([stats_mn1, stats_w1, stats_d1], ignore_index=True)

    # EF 共振分析
    stats_ef = analyze_by_ef_count(df_merged)

    # 状态池分析
    stats_pool = analyze_by_pool_id(df_merged)

    # 品种-State 分析
    stats_symbol_state = analyze_by_symbol_state(df_merged)

    # 打印关键结果
    print("\n  【MN1 State TOP10 (by 5d收益)】")
    print(stats_mn1.head(10).to_string(index=False))

    print("\n  【D1 State TOP10 (by 5d收益)】")
    print(stats_d1.head(10).to_string(index=False))

    print("\n  【EF共振分析】")
    print(stats_ef.to_string(index=False))

    print("\n  【TOP10 状态池 (by 5d收益)】")
    print(stats_pool.head(10).to_string(index=False))

    # 6.6 保存结果
    print("\n[5/5] 保存结果...")
    save_results(df_merged, stats_single, stats_ef, stats_pool, stats_symbol_state, OUTPUT_DB_PATH)

    print("\n" + "=" * 70)
    print(" 分析完成!")
    print("=" * 70)


if __name__ == "__main__":
    # 处理 Windows 编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
