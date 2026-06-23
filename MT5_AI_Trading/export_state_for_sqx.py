"""
导出 State 数据给 SQX (StrategyQuant X)

将 H1 State 数据导出为：
1. SQX 自定义指标格式（每行 = H1 时间戳 + 各周期 state_hex + SR 位）
2. CSV 格式供 SQX 数据导入
3. 分段文件：按 State 模式分组，每组一个文件

用法:
  python export_state_for_sqx.py --symbol US_30
  python export_state_for_sqx.py --all
  python export_state_for_sqx.py --split-by-state
"""

import sys
import argparse
import logging
from pathlib import Path

import duckdb
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("export_sqx")

DB_STATE = "data/h1_state.duckdb"
SQX_DATA_DIR = Path("D:/SQX136/data/processed")


def decode_hex(hex_val: str) -> dict:
    if not hex_val or hex_val in ("N/A", ""):
        return {"dir": 0, "trend": 0, "breakout": 0, "squeeze": 1, "val": -1}
    is_neg = hex_val.startswith("-")
    clean = hex_val.lstrip("-")
    try:
        val = int(clean, 16)
    except ValueError:
        return {"dir": 0, "trend": 0, "breakout": 0, "squeeze": 1, "val": -1}
    has_trend = (val & 4) != 0
    has_pos = (val & 2) != 0
    is_contraction = (val & 8) == 0
    direction = -1 if is_neg else (1 if (has_trend or has_pos) else 0)
    return {
        "dir": direction,
        "trend": 1 if has_trend else 0,
        "breakout": 1 if has_pos else 0,
        "squeeze": 1 if (is_contraction and not has_trend and not has_pos) else 0,
        "val": val,
    }


def export_sqx_csv(symbol: str, output_dir: Path = None):
    """
    导出单个品种的 State 数据为 SQX 可读的 CSV

    SQX CSV 格式:
    Date,Time,Open,High,Low,Close,Volume,State_D1,State_H4,State_H1,...
    """
    output_dir = output_dir or SQX_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(DB_STATE, read_only=True)
    df = conn.execute("""
        SELECT timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex
        FROM h1_state_snapshot
        WHERE symbol = ?
        ORDER BY timestamp
    """, [symbol]).fetchdf()
    conn.close()

    if df.empty:
        logger.warning(f"{symbol}: 无数据")
        return None

    # 解析每个周期的 state 组件
    sqx_rows = []
    for _, row in df.iterrows():
        ts = pd.to_datetime(row["timestamp"])

        # 各周期解码
        mn1 = decode_hex(row["mn1_hex"])
        w1 = decode_hex(row["w1_hex"])
        d1 = decode_hex(row["d1_hex"])
        h4 = decode_hex(row["h4_hex"])
        h1 = decode_hex(row["h1_hex"])

        sqx_rows.append({
            "Date": ts.strftime("%Y.%m.%d"),
            "Time": ts.strftime("%H:%M"),
            # State 原始 hex 值
            "State_MN1": row["mn1_hex"],
            "State_W1": row["w1_hex"],
            "State_D1": row["d1_hex"],
            "State_H4": row["h4_hex"],
            "State_H1": row["h1_hex"],
            # 解码后的数值（SQX 可用作条件）
            "MN1_dir": mn1["dir"],
            "MN1_trend": mn1["trend"],
            "MN1_squeeze": mn1["squeeze"],
            "W1_dir": w1["dir"],
            "W1_trend": w1["trend"],
            "W1_squeeze": w1["squeeze"],
            "D1_dir": d1["dir"],
            "D1_trend": d1["trend"],
            "D1_squeeze": d1["squeeze"],
            "H4_dir": h4["dir"],
            "H4_trend": h4["trend"],
            "H4_squeeze": h4["squeeze"],
            "H1_dir": h1["dir"],
            "H1_trend": h1["trend"],
            "H1_squeeze": h1["squeeze"],
            # 组合信号
            "Multi_bull": sum([1 for x in [mn1, w1, d1, h4, h1] if x["dir"] == 1]),
            "Multi_bear": sum([1 for x in [mn1, w1, d1, h4, h1] if x["dir"] == -1]),
            "Squeeze_count": sum([mn1["squeeze"], w1["squeeze"], d1["squeeze"],
                                  h4["squeeze"], h1["squeeze"]]),
            "Breakout_up": 1 if h1["trend"] and h1["dir"] == 1 else 0,
            "Breakout_down": 1 if h1["trend"] and h1["dir"] == -1 else 0,
        })

    sqx_df = pd.DataFrame(sqx_rows)

    # 保存
    filename = f"{symbol}_state_sqx.csv"
    filepath = output_dir / filename
    sqx_df.to_csv(filepath, index=False)
    logger.info(f"{symbol}: 导出 {len(sqx_df)} 行 → {filepath}")

    return filepath


def split_by_state_pattern(symbol: str, output_dir: Path = None):
    """
    按 State 模式分段导出

    每个 D1+H4+H1 组合模式一个文件，供 SQX 分别回测
    """
    output_dir = output_dir or SQX_DATA_DIR / "state_segments"
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(DB_STATE, read_only=True)
    df = conn.execute("""
        SELECT timestamp, d1_hex, h4_hex, h1_hex
        FROM h1_state_snapshot
        WHERE symbol = ?
        ORDER BY timestamp
    """, [symbol]).fetchdf()
    conn.close()

    if df.empty:
        return

    # 按 D1+H4+H1 模式分组
    df["pattern"] = df["d1_hex"] + "_" + df["h4_hex"] + "_" + df["h1_hex"]

    patterns = df["pattern"].value_counts()
    logger.info(f"{symbol}: {len(patterns)} 种模式")

    # 只导出出现次数 >= 20 的模式
    valid_patterns = patterns[patterns >= 20]
    logger.info(f"  有效模式 (>=20次): {len(valid_patterns)}")

    for pattern, count in valid_patterns.items():
        segment = df[df["pattern"] == pattern][["timestamp"]].copy()
        segment["Date"] = pd.to_datetime(segment["timestamp"]).dt.strftime("%Y.%m.%d")
        segment["Time"] = pd.to_datetime(segment["timestamp"]).dt.strftime("%H:%M")

        filename = f"{symbol}_{pattern}_{count}bars.csv"
        filepath = output_dir / filename
        segment[["Date", "Time"]].to_csv(filepath, index=False)

    logger.info(f"  已导出 {len(valid_patterns)} 个分段文件到 {output_dir}")


def generate_sqx_strategy_template(symbol: str):
    """
    生成 SQX 策略模板（AlgoWizard 格式）

    这是 SQX 可以直接导入的策略规则模板
    """
    template = f"""
# SQX Strategy Template for {symbol}
# Generated by State System

# === 入场条件 ===
# BUY 条件:
#   1. D1_dir == 1 (日线看涨)
#   2. H1_trend == 1 (H1 有趋势触发)
#   3. H4_dir == 1 OR H4_breakout == 1 (H4 确认)
#   4. RSI(14) > 50 (动量确认)
#   5. Price > EMA(20) (趋势确认)

# SELL 条件:
#   1. D1_dir == -1 (日线看跌)
#   2. H1_trend == 1 (H1 有趋势触发)
#   3. H4_dir == -1 OR H4_breakout == 1 (H4 确认)
#   4. RSI(14) < 50 (动量确认)
#   5. Price < EMA(20) (趋势确认)

# === 过滤条件 ===
# State 过滤:
#   - Squeeze_count >= 2 → 等待突破
#   - Multi_bull >= 3 → 只做多
#   - Multi_bear >= 3 → 只做空

# === 止损止盈 ===
#   SL: ATR(14) * 1.5
#   TP: ATR(14) * 3.0
#   持仓: 12 根 H1 (12小时)
"""
    return template


def main():
    parser = argparse.ArgumentParser(description="导出 State 数据给 SQX")
    parser.add_argument("--symbol", type=str, help="品种名")
    parser.add_argument("--all", action="store_true", help="导出所有品种")
    parser.add_argument("--split-by-state", action="store_true", help="按 State 模式分段")
    parser.add_argument("--output", type=str, help="输出目录")
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else SQX_DATA_DIR

    # 获取所有品种
    conn = duckdb.connect(DB_STATE, read_only=True)
    symbols = conn.execute(
        "SELECT DISTINCT symbol FROM h1_state_snapshot"
    ).fetchdf()["symbol"].tolist()
    conn.close()

    target = symbols if args.all else ([args.symbol] if args.symbol else ["US_30"])

    for sym in target:
        logger.info(f"\n{'='*50}")
        logger.info(f"导出 {sym}")
        logger.info(f"{'='*50}")

        # 导出完整 CSV
        export_sqx_csv(sym, output_dir)

        # 按模式分段
        if args.split_by_state:
            split_by_state_pattern(sym, output_dir)

    # 生成策略模板
    template = generate_sqx_strategy_template(target[0])
    template_path = output_dir / "strategy_template.txt"
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(template)
    logger.info(f"\n策略模板已生成: {template_path}")

    logger.info(f"\n{'='*50}")
    logger.info(f"导出完成！文件位于: {output_dir}")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    main()
