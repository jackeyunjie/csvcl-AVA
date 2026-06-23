"""
Walk-forward 验证框架

将数据分为 N 段，每段前 70% 训练、后 30% 测试：
- 训练段搜索最优参数
- 测试段验证 Out-of-Sample (OOS) 表现

用法:
  python walk_forward.py --pattern "D1=8,H4=8,H1=-F"
  python walk_forward.py --pattern "D1=6,H4=6,H1=6" --symbols US_30,US_500
  python walk_forward.py --pattern "D1=8,H4=8,H1=-F" --splits 5 --train-ratio 0.8
"""

import argparse
import math
from itertools import product
from typing import Any, Dict, List, Optional

import duckdb
import numpy as np
import pandas as pd

DB_STATE = "data/h1_state.duckdb"


def resolve_db_state(path: str | None) -> str:
    if path:
        return path
    return DB_STATE


# ============================================================================
# State 解码与模式匹配 (从 strategy_miner.py 复用)
# ============================================================================

def decode_hex(hex_val: str) -> Dict:
    if not hex_val or hex_val in ("N/A", ""):
        return {"dir": "neutral", "trend": False, "breakout": False, "squeeze": True, "val": -1}
    is_neg = hex_val.startswith("-")
    clean = hex_val.lstrip("-")
    try:
        val = int(clean, 16)
    except ValueError:
        return {"dir": "neutral", "trend": False, "breakout": False, "squeeze": True, "val": -1}
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
        "val": val,
    }


def parse_pattern(pattern_str: str) -> Dict:
    parts = {}
    for item in pattern_str.split(","):
        if "=" in item:
            tf, val = item.strip().split("=")
            parts[tf.strip().upper()] = val.strip()
    return parts


def match_pattern(row: pd.Series, pattern: Dict) -> bool:
    for tf, expected_hex in pattern.items():
        col = f"{tf.lower()}_hex"
        if col not in row.index:
            return False
        if str(row[col]) != expected_hex:
            return False
    return True


# ============================================================================
# 回测引擎 (从 strategy_miner.py 复用)
# ============================================================================

def match_pattern_vec(df: pd.DataFrame, pattern: Dict) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for tf, expected_hex in pattern.items():
        col = f"{tf.lower()}_hex"
        if col in df.columns:
            mask &= (df[col].astype(str) == expected_hex)
    return mask


def backtest_pattern(
    df: pd.DataFrame,
    pattern: Dict,
    direction: str,
    hold_bars: int,
    stop_loss_pct: float,
    take_profit_pct: float,
) -> Dict:
    """向量化回测引擎"""
    if len(df) == 0:
        return {"trades": []}

    matches = match_pattern_vec(df, pattern)
    if not matches.any():
        return {"trades": []}

    # 计算每根 K 线的 step return
    h1_dirs = df["h1_hex"].apply(lambda x: decode_hex(str(x))["dir"])
    if direction == "long":
        step_map = {"bull": 0.12, "bear": -0.18, "neutral": 0.0}
    else:
        step_map = {"bear": 0.12, "bull": -0.18, "neutral": 0.0}
    step_returns = h1_dirs.map(step_map).fillna(0.0).values

    # 找到不重叠的 entry 点
    entry_indices = []
    last_exit = -1
    for idx in matches[matches].index:
        if idx > last_exit:
            entry_indices.append(idx)
            last_exit = idx + hold_bars - 1

    trades = []
    for idx in entry_indices:
        max_end = min(idx + hold_bars, len(step_returns))
        future_returns = step_returns[idx:max_end]
        if len(future_returns) == 0:
            continue
        cumulative = np.cumsum(future_returns)

        sl_hit = np.where(cumulative <= -stop_loss_pct)[0]
        tp_hit = np.where(cumulative >= take_profit_pct)[0]

        if len(sl_hit) > 0 and (len(tp_hit) == 0 or sl_hit[0] < tp_hit[0]):
            exit_offset = int(sl_hit[0])
            exit_reason = "stop_loss"
        elif len(tp_hit) > 0:
            exit_offset = int(tp_hit[0])
            exit_reason = "take_profit"
        else:
            exit_offset = len(future_returns) - 1
            exit_reason = "time_exit"

        pnl = round(cumulative[exit_offset], 3)
        trades.append({
            "symbol": df.attrs.get("symbol", "unknown"),
            "direction": direction,
            "entry_time": str(df.iloc[idx].get("timestamp", "")),
            "exit_time": str(df.iloc[min(idx + exit_offset, len(df) - 1)].get("timestamp", "")),
            "hold_bars": exit_offset + 1,
            "pnl_pct": pnl,
            "exit_reason": exit_reason,
        })

    return {"trades": trades}


# ============================================================================
# 质量评估 (从 strategy_miner.py 复用)
# ============================================================================

def evaluate_quality(trades: List[Dict], symbols: List[str]) -> Dict:
    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total = len(trades)
    win_rate = len(wins) / total if total > 0 else 0.0
    avg_pnl = np.mean(pnls) if pnls else 0.0
    total_pnl = sum(pnls)

    if len(pnls) > 1:
        sharpe = np.mean(pnls) / np.std(pnls) if np.std(pnls) > 0 else 0.0
    else:
        sharpe = 0.0

    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdown = peak - cumulative
    max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0

    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = abs(np.mean(losses)) if losses else 1.0
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0.0

    year_stability = 0.0
    if total >= 20:
        quarter_size = max(1, total // 4)
        quarter_wins = []
        for q in range(4):
            start = q * quarter_size
            end = min(start + quarter_size, total)
            q_pnls = pnls[start:end]
            q_wr = len([p for p in q_pnls if p > 0]) / len(q_pnls) if q_pnls else 0
            quarter_wins.append(q_wr)
        year_stability = 1 - np.std(quarter_wins) if len(quarter_wins) > 1 else 0.0

    symbol_stability = 0.0
    if len(symbols) > 1:
        sym_wr = []
        for sym in symbols:
            sym_trades = [t for t in trades if t["symbol"] == sym]
            if sym_trades:
                sym_wr.append(len([t for t in sym_trades if t["pnl_pct"] > 0]) / len(sym_trades))
        symbol_stability = 1 - np.std(sym_wr) if len(sym_wr) > 1 else 0.0

    sample_per_symbol = total / len(symbols) if symbols else total

    quality = 0.0
    if total >= 10:
        quality += min(20, win_rate * 25)
        quality += min(20, sharpe * 5)
        quality += min(15, profit_factor * 5)
        quality += min(15, year_stability * 20)
        quality += min(15, symbol_stability * 20)
        quality += min(15, sample_per_symbol / 5)
        quality = max(0.0, min(100.0, quality))

    return {
        "total_trades": total,
        "win_rate": round(win_rate, 4),
        "avg_pnl": round(avg_pnl, 4),
        "total_pnl": round(total_pnl, 2),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown": round(max_dd, 2),
        "profit_factor": round(profit_factor, 2),
        "year_stability": round(year_stability, 3),
        "symbol_stability": round(symbol_stability, 3),
        "sample_per_symbol": round(sample_per_symbol, 1),
        "quality_score": round(quality, 1),
    }


# ============================================================================
# Walk-forward 验证器
# ============================================================================

class WalkForwardValidator:
    """
    Walk-forward 验证

    将数据按时间分为 n_splits 段：
    - 训练段: 前 train_ratio 数据
    - 测试段: 后 (1 - train_ratio) 数据

    对每个训练段找到最优参数，在测试段验证
    """

    def __init__(self, n_splits: int = 3, train_ratio: float = 0.7, db_path: str = DB_STATE):
        self.n_splits = n_splits
        self.train_ratio = train_ratio
        self.db_path = db_path

    def load_data(self, symbols: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        try:
            conn = duckdb.connect(self.db_path, read_only=True)
        except duckdb.IOException as exc:
            raise RuntimeError(
                f"无法打开 {self.db_path}，可能正在被其他进程占用。"
                f"请关闭占用该数据库的进程后重试。详情: {exc}"
            ) from exc
        if symbols is None:
            symbols = conn.execute(
                "SELECT DISTINCT symbol FROM h1_state_snapshot"
            ).fetchdf()["symbol"].tolist()
        data = {}
        for sym in symbols:
            df = conn.execute("""
                SELECT timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex
                FROM h1_state_snapshot WHERE symbol = ? ORDER BY timestamp
            """, [sym]).fetchdf()
            df.attrs["symbol"] = sym
            data[sym] = df
        conn.close()
        return data

    def split_by_time(
        self, data: Dict[str, pd.DataFrame]
    ) -> List[tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]]:
        """按全局时间戳排序后切分"""
        all_times: set = set()
        for df in data.values():
            all_times.update(df["timestamp"].tolist())
        sorted_times = sorted(all_times)
        n = len(sorted_times)
        if n < self.n_splits * 10:
            raise ValueError(f"时间序列太短: {n} 个时间戳")

        split_size = n // self.n_splits
        splits: List[tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]] = []

        for i in range(self.n_splits):
            start_idx = i * split_size
            end_idx = start_idx + split_size if i < self.n_splits - 1 else n
            split_times = sorted_times[start_idx:end_idx]
            train_cut = int(len(split_times) * self.train_ratio)
            train_times = set(split_times[:train_cut])
            test_times = set(split_times[train_cut:])

            train_data = {}
            test_data = {}
            for sym, df in data.items():
                train_data[sym] = df[df["timestamp"].isin(train_times)].copy()
                test_data[sym] = df[df["timestamp"].isin(test_times)].copy()
            splits.append((train_data, test_data))

        return splits

    def find_best_params(self, train_data: Dict[str, pd.DataFrame], pattern_str: str) -> Optional[Dict]:
        pattern = parse_pattern(pattern_str)
        directions = ["long", "short"]
        hold_options = [6, 12, 24, 48]
        sl_options = [1.0, 2.0, 3.0]
        tp_options = [2.0, 3.0, 5.0]

        best: Optional[Dict] = None
        best_score = -1.0
        symbols = [s for s, df in train_data.items() if len(df) > 0]

        for direction, hold, sl, tp in product(directions, hold_options, sl_options, tp_options):
            all_trades: List[Dict] = []
            for sym, df in train_data.items():
                if len(df) == 0:
                    continue
                df.attrs["symbol"] = sym
                result = backtest_pattern(df, pattern, direction, hold, sl, tp)
                all_trades.extend(result["trades"])
            if len(all_trades) < 5:
                continue
            quality = evaluate_quality(all_trades, symbols)
            if quality["quality_score"] > best_score:
                best_score = quality["quality_score"]
                best = {
                    "direction": direction,
                    "hold_bars": hold,
                    "stop_loss_pct": sl,
                    "take_profit_pct": tp,
                    "train_trades": len(all_trades),
                    "train_quality": quality,
                }
        return best

    def validate_params(
        self, test_data: Dict[str, pd.DataFrame], pattern_str: str, params: Dict
    ) -> Dict:
        pattern = parse_pattern(pattern_str)
        all_trades: List[Dict] = []
        for sym, df in test_data.items():
            if len(df) == 0:
                continue
            df.attrs["symbol"] = sym
            result = backtest_pattern(
                df, pattern,
                params["direction"], params["hold_bars"],
                params["stop_loss_pct"], params["take_profit_pct"],
            )
            all_trades.extend(result["trades"])
        symbols = [s for s, df in test_data.items() if len(df) > 0]
        quality = evaluate_quality(all_trades, symbols)
        return {
            "test_trades": len(all_trades),
            "test_quality": quality,
            "trades": all_trades,
        }

    def validate(self, pattern_str: str, symbols: Optional[List[str]] = None) -> List[Dict]:
        """
        执行 Walk-forward 验证

        Returns:
            各 split 的 OOS 结果列表
        """
        print(f"[WalkForward] 加载数据: pattern={pattern_str}")
        data = self.load_data(symbols)
        if not data:
            raise ValueError("No data loaded")

        total_rows = sum(len(d) for d in data.values())
        print(f"[WalkForward] 品种数: {len(data)}, 总时间戳: {total_rows}")

        splits = self.split_by_time(data)
        results: List[Dict] = []

        for i, (train_data, test_data) in enumerate(splits, 1):
            train_rows = sum(len(d) for d in train_data.values())
            test_rows = sum(len(d) for d in test_data.values())
            print(f"[WalkForward] Split {i}/{self.n_splits} | train_rows={train_rows} test_rows={test_rows}")

            best_params = self.find_best_params(train_data, pattern_str)
            if best_params is None:
                print("  训练段未找到有效参数 (样本不足)")
                continue

            tq = best_params["train_quality"]
            print(
                f"  最优参数: {best_params['direction']} hold={best_params['hold_bars']} "
                f"SL={best_params['stop_loss_pct']} TP={best_params['take_profit_pct']} "
                f"Q={tq['quality_score']:.1f} WR={tq['win_rate']:.1%}"
            )

            oos = self.validate_params(test_data, pattern_str, best_params)
            oq = oos["test_quality"]
            print(
                f"  OOS 结果: trades={oos['test_trades']} "
                f"WR={oq['win_rate']:.1%} Sharpe={oq['sharpe_ratio']:.2f} Q={oq['quality_score']:.1f}"
            )

            results.append({
                "split": i,
                "train_params": best_params,
                "oos": oos,
            })

        return results


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Walk-forward 验证框架")
    parser.add_argument("--pattern", type=str, required=True, help="State 模式, 如 D1=8,H4=8,H1=-F")
    parser.add_argument("--symbols", type=str, help="逗号分隔的品种列表，默认全部")
    parser.add_argument("--splits", type=int, default=3, help="切分段数 (默认 3)")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="训练段比例 (默认 0.7)")
    parser.add_argument("--db", type=str, default=DB_STATE, help="State 数据库路径")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else None
    validator = WalkForwardValidator(n_splits=args.splits, train_ratio=args.train_ratio, db_path=args.db)
    results = validator.validate(args.pattern, symbols=symbols)

    print("\n" + "=" * 60)
    print("Walk-forward 验证汇总")
    print("=" * 60)
    total_oos_trades = 0
    total_oos_pnl = 0.0
    for r in results:
        p = r["train_params"]
        q = r["oos"]["test_quality"]
        print(
            f"Split {r['split']}: {p['direction']} hold={p['hold_bars']} "
            f"SL={p['stop_loss_pct']} TP={p['take_profit_pct']} | "
            f"OOS trades={r['oos']['test_trades']} WR={q['win_rate']:.1%} "
            f"Sharpe={q['sharpe_ratio']:.2f} Q={q['quality_score']:.1f}"
        )
        total_oos_trades += r["oos"]["test_trades"]
        total_oos_pnl += q.get("total_pnl", 0.0)

    print(f"\n合计 OOS 交易数: {total_oos_trades}, 总收益: {total_oos_pnl:.2f}%")

    if results:
        avg_wr = np.mean([r["oos"]["test_quality"]["win_rate"] for r in results])
        avg_q = np.mean([r["oos"]["test_quality"]["quality_score"] for r in results])
        print(f"平均 OOS 胜率: {avg_wr:.1%}, 平均 OOS 质量分: {avg_q:.1f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
