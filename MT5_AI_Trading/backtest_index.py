"""
股指回测：D1+H1+H4 State 规则

规则:
  BUY:  D1 看涨(+4/+6/+E/+F) + H1 趋势触发(+4/+6) + H4 确认(+2/+4/+6)
  SELL: D1 看跌(-4/-6/-E/-F) + H1 趋势触发(-4/-6) + H4 确认(-2/-4/-6)

回测逻辑:
  - 每根 H1 K线检查入场条件
  - 入场后持有 N 根 H1 K线后平仓
  - 统计胜率、平均收益、最大回撤
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import duckdb
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "python" / "ai_engine"))

DB_PATH = "data/h1_state.duckdb"


def decode_hex(hex_val: str) -> Dict:
    if not hex_val or hex_val == "N/A":
        return {"dir": "neutral", "trend": False, "breakout": False, "squeeze": True}
    is_neg = hex_val.startswith("-")
    clean = hex_val.lstrip("-")
    try:
        val = int(clean, 16)
    except ValueError:
        return {"dir": "neutral", "trend": False, "breakout": False, "squeeze": True}
    has_trend = (val & 4) != 0
    has_pos = (val & 2) != 0
    is_contraction = (val & 8) == 0
    if is_neg:
        direction = "bear"
    elif has_trend or has_pos:
        direction = "bull"
    else:
        direction = "neutral"
    return {
        "dir": direction,
        "trend": has_trend,
        "breakout": has_pos,
        "squeeze": is_contraction and not has_trend and not has_pos,
    }


def check_buy_signal(d1_hex: str, h1_hex: str, h4_hex: str) -> bool:
    """BUY: D1看涨 + H1趋势触发(多) + H4确认(多)"""
    d1 = decode_hex(d1_hex)
    h1 = decode_hex(h1_hex)
    h4 = decode_hex(h4_hex)
    return (d1["dir"] == "bull" and
            h1["trend"] and h1["dir"] == "bull" and
            (h4["dir"] == "bull" or h4["breakout"]))


def check_sell_signal(d1_hex: str, h1_hex: str, h4_hex: str) -> bool:
    """SELL: D1看跌 + H1趋势触发(空) + H4确认(空)"""
    d1 = decode_hex(d1_hex)
    h1 = decode_hex(h1_hex)
    h4 = decode_hex(h4_hex)
    return (d1["dir"] == "bear" and
            h1["trend"] and h1["dir"] == "bear" and
            (h4["dir"] == "bear" or h4["breakout"]))


@dataclass
class Trade:
    symbol: str
    direction: str  # BUY / SELL
    entry_time: datetime
    entry_idx: int
    exit_time: Optional[datetime] = None
    exit_idx: Optional[int] = None
    hold_bars: int = 0
    pnl_pct: float = 0.0
    exit_reason: str = ""


def backtest(
    symbol: str,
    hold_bars: int = 24,
    stop_loss_pct: float = 2.0,
    take_profit_pct: float = 3.0,
) -> Dict:
    """
    回测单个品种

    Args:
        symbol: 品种名
        hold_bars: 持仓 H1 K线数（默认24 = 1天）
        stop_loss_pct: 止损百分比
        take_profit_pct: 止盈百分比
    """
    conn = duckdb.connect(DB_PATH, read_only=True)
    df = conn.execute("""
        SELECT timestamp, d1_hex, h4_hex, h1_hex
        FROM h1_state_snapshot
        WHERE symbol = ?
        ORDER BY timestamp
    """, [symbol]).fetchdf()
    conn.close()

    if df.empty:
        return {"symbol": symbol, "error": "无数据"}

    trades: List[Trade] = []
    in_trade = False
    current_trade: Optional[Trade] = None

    for i in range(len(df)):
        row = df.iloc[i]

        if in_trade:
            current_trade.hold_bars += 1

            # 模拟收益：用 state_hex 方向作为收益代理
            # 真实回测需要接入实际价格
            h1_dir = decode_hex(row["h1_hex"])["dir"]

            # 简化收益模型：
            # - 入场后每根 H1，如果方向一致 +0.1%，不一致 -0.1%
            if current_trade.direction == "BUY":
                if h1_dir == "bull":
                    current_trade.pnl_pct += 0.1
                elif h1_dir == "bear":
                    current_trade.pnl_pct -= 0.15
            else:  # SELL
                if h1_dir == "bear":
                    current_trade.pnl_pct += 0.1
                elif h1_dir == "bull":
                    current_trade.pnl_pct -= 0.15

            # 平仓条件
            exit_reason = ""
            if current_trade.pnl_pct <= -stop_loss_pct:
                exit_reason = "止损"
            elif current_trade.pnl_pct >= take_profit_pct:
                exit_reason = "止盈"
            elif current_trade.hold_bars >= hold_bars:
                exit_reason = "到期"

            if exit_reason:
                current_trade.exit_time = row["timestamp"]
                current_trade.exit_idx = i
                current_trade.exit_reason = exit_reason
                trades.append(current_trade)
                in_trade = False
                current_trade = None

        else:
            # 检查入场信号
            d1_hex = row["d1_hex"]
            h1_hex = row["h1_hex"]
            h4_hex = row["h4_hex"]

            if check_buy_signal(d1_hex, h1_hex, h4_hex):
                current_trade = Trade(
                    symbol=symbol, direction="BUY",
                    entry_time=row["timestamp"], entry_idx=i
                )
                in_trade = True
            elif check_sell_signal(d1_hex, h1_hex, h4_hex):
                current_trade = Trade(
                    symbol=symbol, direction="SELL",
                    entry_time=row["timestamp"], entry_idx=i
                )
                in_trade = True

    # 统计
    if not trades:
        return {"symbol": symbol, "trades": 0, "error": "无交易信号"}

    wins = [t for t in trades if t.pnl_pct > 0]
    losses = [t for t in trades if t.pnl_pct <= 0]
    buy_trades = [t for t in trades if t.direction == "BUY"]
    sell_trades = [t for t in trades if t.direction == "SELL"]

    total_pnl = sum(t.pnl_pct for t in trades)
    avg_pnl = total_pnl / len(trades)
    win_rate = len(wins) / len(trades) * 100

    avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
    avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0
    profit_factor = abs(avg_win * len(wins)) / abs(avg_loss * len(losses)) if losses and avg_loss != 0 else float('inf')

    # 最大回撤
    cumulative = np.cumsum([t.pnl_pct for t in trades])
    peak = np.maximum.accumulate(cumulative)
    drawdown = peak - cumulative
    max_dd = np.max(drawdown) if len(drawdown) > 0 else 0

    return {
        "symbol": symbol,
        "total_trades": len(trades),
        "buy_trades": len(buy_trades),
        "sell_trades": len(sell_trades),
        "win_rate": f"{win_rate:.1f}%",
        "total_pnl": f"{total_pnl:.2f}%",
        "avg_pnl_per_trade": f"{avg_pnl:.3f}%",
        "avg_win": f"{avg_win:.3f}%",
        "avg_loss": f"{avg_loss:.3f}%",
        "profit_factor": f"{profit_factor:.2f}",
        "max_drawdown": f"{max_dd:.2f}%",
        "exit_reasons": {
            "止盈": len([t for t in trades if t.exit_reason == "止盈"]),
            "止损": len([t for t in trades if t.exit_reason == "止损"]),
            "到期": len([t for t in trades if t.exit_reason == "到期"]),
        },
        "avg_hold_bars": f"{np.mean([t.hold_bars for t in trades]):.1f}",
        "trades_detail": [
            {
                "dir": t.direction,
                "entry": str(t.entry_time),
                "hold": t.hold_bars,
                "pnl": f"{t.pnl_pct:.2f}%",
                "exit": t.exit_reason,
            }
            for t in trades[:20]  # 只显示前20笔
        ],
    }


def main():
    print("=" * 60)
    print("股指回测：D1+H1+H4 State 规则")
    print("=" * 60)

    symbols = ["US_30", "US_500", "US_TECH100"]

    for hold in [12, 24, 48]:
        print(f"\n{'='*60}")
        print(f"持仓时间: {hold} 根 H1 ({hold}小时)")
        print(f"{'='*60}")

        for symbol in symbols:
            result = backtest(symbol, hold_bars=hold)

            if "error" in result:
                print(f"\n  {symbol}: {result['error']}")
                continue

            print(f"\n  {symbol}:")
            print(f"    交易次数: {result['total_trades']} (BUY={result['buy_trades']}, SELL={result['sell_trades']})")
            print(f"    胜率: {result['win_rate']}")
            print(f"    总收益: {result['total_pnl']}")
            print(f"    平均收益: {result['avg_pnl_per_trade']}")
            print(f"    盈亏比: {result['profit_factor']}")
            print(f"    最大回撤: {result['max_drawdown']}")
            print(f"    平均持仓: {result['avg_hold_bars']} 根")
            print(f"    平仓原因: {result['exit_reasons']}")

    # 详细交易记录
    print(f"\n{'='*60}")
    print("US_30 详细交易记录 (持仓24小时)")
    print(f"{'='*60}")

    result = backtest("US_30", hold_bars=24)
    if "trades_detail" in result:
        print(f"\n{'方向':<6} {'入场时间':<22} {'持仓':>4} {'收益':>8} {'平仓'}")
        print("-" * 55)
        for t in result["trades_detail"]:
            print(f"{t['dir']:<6} {t['entry']:<22} {t['hold']:>4} {t['pnl']:>8} {t['exit']}")

    print(f"\n{'='*60}")
    print("回测完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
