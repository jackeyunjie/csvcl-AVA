"""
大数据统计：最优开仓/平仓条件

从真实 H1 State 数据中统计：
1. 哪些状态组合最赚钱？
2. 突破后多久平仓最优？
3. 多周期一致性 vs 单周期突破，哪个更准？
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

import duckdb
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "python" / "ai_engine"))

from state_hex_encoding import StateHexEncoder

DB_PATH = "data/h1_state.duckdb"


def decode_hex(hex_val: str) -> Dict:
    """解析 state_hex 的所有组件"""
    if not hex_val or hex_val == "N/A":
        return {"base": "unknown", "vol": False, "pos": False,
                "trend": False, "dir": "neutral", "squeeze": True}

    is_neg = hex_val.startswith("-")
    clean = hex_val.lstrip("-")
    try:
        val = int(clean, 16)
    except ValueError:
        return {"base": "unknown", "vol": False, "pos": False,
                "trend": False, "dir": "neutral", "squeeze": True}

    has_trend = (val & 4) != 0
    has_pos = (val & 2) != 0
    has_vol = (val & 1) != 0
    is_contraction = (val & 8) == 0

    if is_neg:
        direction = "bear"
    elif has_trend or has_pos:
        direction = "bull"
    else:
        direction = "neutral"

    return {
        "base": "contraction" if is_contraction else "expansion",
        "vol": has_vol,
        "pos": has_pos,
        "trend": has_trend,
        "dir": direction,
        "squeeze": is_contraction and not has_trend and not has_pos,
    }


def load_data(symbols: List[str] = None) -> pd.DataFrame:
    """加载所有 State 数据"""
    conn = duckdb.connect(DB_PATH, read_only=True)

    where = ""
    if symbols:
        syms = "', '".join(symbols)
        where = f"WHERE symbol IN ('{syms}')"

    df = conn.execute(f"""
        SELECT symbol, timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex
        FROM h1_state_snapshot
        {where}
        ORDER BY symbol, timestamp
    """).fetchdf()
    conn.close()

    # 添加下一小时收盘价变化（用 H1 hex 方向作为代理）
    # 注：这里用 state_hex 方向作为未来收益的代理
    return df


def analyze_entry_conditions(df: pd.DataFrame) -> Dict:
    """统计最优入场条件"""
    results = []

    for _, row in df.iterrows():
        h1 = decode_hex(row["h1_hex"])
        h4 = decode_hex(row["h4_hex"])
        d1 = decode_hex(row["d1_hex"])
        w1 = decode_hex(row["w1_hex"])
        mn1 = decode_hex(row["mn1_hex"])

        # 多周期一致性
        trends = [h1["dir"], h4["dir"], d1["dir"], w1["dir"], mn1["dir"]]
        bull_count = trends.count("bull")
        bear_count = trends.count("bear")

        # Squeeze 计数
        squeeze_count = sum([h1["squeeze"], h4["squeeze"], d1["squeeze"],
                            w1["squeeze"], mn1["squeeze"]])

        results.append({
            "symbol": row["symbol"],
            "timestamp": row["timestamp"],
            "h1_dir": h1["dir"],
            "h1_trend": h1["trend"],
            "h1_squeeze": h1["squeeze"],
            "h4_dir": h4["dir"],
            "d1_dir": d1["dir"],
            "bull_count": bull_count,
            "bear_count": bear_count,
            "squeeze_count": squeeze_count,
            "multi_bull": bull_count >= 3,
            "multi_bear": bear_count >= 3,
            "h1_breakout_up": h1["trend"] and h1["dir"] == "bull",
            "h1_breakout_down": h1["trend"] and h1["dir"] == "bear",
            "squeeze_breakout_up": squeeze_count >= 2 and h1["trend"] and h1["dir"] == "bull",
            "squeeze_breakout_down": squeeze_count >= 2 and h1["trend"] and h1["dir"] == "bear",
        })

    stats_df = pd.DataFrame(results)

    # 统计各条件的出现频率
    total = len(stats_df)

    report = {
        "total_bars": total,
        "symbols": stats_df["symbol"].nunique(),
        "conditions": {},
    }

    # 条件统计
    conditions = {
        "H1 趋势触发(多)": stats_df["h1_breakout_up"].sum(),
        "H1 趋势触发(空)": stats_df["h1_breakout_down"].sum(),
        "多周期看涨(3+)": stats_df["multi_bull"].sum(),
        "多周期看跌(3+)": stats_df["multi_bear"].sum(),
        "Squeeze(2+周期)": (stats_df["squeeze_count"] >= 2).sum(),
        "Squeeze+向上突破": stats_df["squeeze_breakout_up"].sum(),
        "Squeeze+向下突破": stats_df["squeeze_breakout_down"].sum(),
        "H1+Squeeze": ((stats_df["h1_trend"]) & (stats_df["squeeze_count"] >= 1)).sum(),
    }

    for name, count in conditions.items():
        report["conditions"][name] = {
            "count": int(count),
            "pct": f"{count/total*100:.1f}%",
        }

    # 组合条件（最佳入场）
    combos = {
        "多周期看涨+H1突破": ((stats_df["multi_bull"]) & (stats_df["h1_breakout_up"])).sum(),
        "多周期看跌+H1突破": ((stats_df["multi_bear"]) & (stats_df["h1_breakout_down"])).sum(),
        "Squeeze+多周期看涨+突破": ((stats_df["squeeze_count"] >= 2) & (stats_df["multi_bull"]) & (stats_df["h1_breakout_up"])).sum(),
        "Squeeze+多周期看跌+突破": ((stats_df["squeeze_count"] >= 2) & (stats_df["multi_bear"]) & (stats_df["h1_breakout_down"])).sum(),
        "D1看涨+H1突破+H4确认": ((stats_df["d1_dir"] == "bull") & (stats_df["h1_breakout_up"]) & (stats_df["h4_dir"] == "bull")).sum(),
        "D1看跌+H1突破+H4确认": ((stats_df["d1_dir"] == "bear") & (stats_df["h1_breakout_down"]) & (stats_df["h4_dir"] == "bear")).sum(),
    }

    report["combo_conditions"] = {}
    for name, count in combos.items():
        report["combo_conditions"][name] = {
            "count": int(count),
            "pct": f"{count/total*100:.2f}%",
        }

    return report


def analyze_state_transitions(df: pd.DataFrame) -> Dict:
    """统计状态转换模式"""
    transitions = defaultdict(lambda: defaultdict(int))

    prev_h1 = None
    for _, row in df.iterrows():
        curr_h1 = row["h1_hex"]
        if prev_h1:
            transitions[prev_h1][curr_h1] += 1
        prev_h1 = curr_h1

    # 找出最常见的转换
    top_transitions = []
    for from_state, to_states in transitions.items():
        for to_state, count in sorted(to_states.items(), key=lambda x: -x[1])[:3]:
            from_decoded = decode_hex(from_state)
            to_decoded = decode_hex(to_state)
            top_transitions.append({
                "from": from_state,
                "to": to_state,
                "count": count,
                "from_desc": f"{'squeeze' if from_decoded['squeeze'] else from_decoded['dir']}",
                "to_desc": f"{'squeeze' if to_decoded['squeeze'] else to_decoded['dir']}",
            })

    top_transitions.sort(key=lambda x: -x["count"])
    return {"top_transitions": top_transitions[:20]}


def main():
    print("=" * 60)
    print("大数据统计：最优开仓/平仓条件")
    print("=" * 60)

    # 加载数据
    df = load_data()
    print(f"\n数据: {len(df)} 条, {df['symbol'].nunique()} 个品种")
    print(f"品种: {df['symbol'].unique().tolist()}")
    print(f"时间: {df['timestamp'].min()} ~ {df['timestamp'].max()}")

    # 1. 入场条件统计
    print(f"\n{'='*60}")
    print("一、入场条件统计")
    print(f"{'='*60}")

    entry = analyze_entry_conditions(df)

    print(f"\n总 Bar 数: {entry['total_bars']}")
    print(f"\n单一条件:")
    for name, info in entry["conditions"].items():
        print(f"  {name}: {info['count']} 次 ({info['pct']})")

    print(f"\n组合条件（最佳入场）:")
    for name, info in entry["combo_conditions"].items():
        print(f"  {name}: {info['count']} 次 ({info['pct']})")

    # 2. 状态转换统计
    print(f"\n{'='*60}")
    print("二、H1 状态转换 Top 20")
    print(f"{'='*60}")

    transitions = analyze_state_transitions(df)
    print(f"\n{'从':<8} {'→':>3} {'到':<8} {'次数':>6} {'描述'}")
    print("-" * 50)
    for t in transitions["top_transitions"]:
        print(f"{t['from']:<8} {'→':>3} {t['to']:<8} {t['count']:>6}   {t['from_desc']} → {t['to_desc']}")

    # 3. 各品种对比
    print(f"\n{'='*60}")
    print("三、各品种对比")
    print(f"{'='*60}")

    for symbol in df["symbol"].unique():
        sym_df = df[df["symbol"] == symbol]
        sym_entry = analyze_entry_conditions(sym_df)
        squeeze_pct = sym_entry["conditions"].get("Squeeze(2+周期)", {}).get("pct", "0%")
        bull_pct = sym_entry["conditions"].get("多周期看涨(3+)", {}).get("pct", "0%")
        bear_pct = sym_entry["conditions"].get("多周期看跌(3+)", {}).get("pct", "0%")
        print(f"\n  {symbol}:")
        print(f"    Squeeze(2+): {squeeze_pct}")
        print(f"    多周期看涨: {bull_pct}")
        print(f"    多周期看跌: {bear_pct}")

    print(f"\n{'='*60}")
    print("统计完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
