"""
策略搜索引擎 (Strategy Miner) - 科研级实验执行器

从 State 数据中系统性发现盈利模式：
1. 定义 State 模式 (如 D1=6 + H1=4)
2. 在历史数据中找到所有出现该模式的时刻
3. 测试不同参数组合 (止损/持仓/方向)
4. 统计胜率/Sharpe/最大回撤
5. 过滤: 样本数/年份稳定性/品种稳定性
6. 写入 experiments.db + 生成报告

用法:
  python strategy_miner.py --scan-all              # 扫描所有高频模式
  python strategy_miner.py --pattern "D1=6,H1=4"   # 指定模式
  python strategy_miner.py --report                 # 生成报告
"""

import sys
import json
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from itertools import product

import duckdb
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("strategy_miner")

DB_STATE = "data/h1_state.duckdb"
DB_EXPERIMENTS = "data/experiments.duckdb"


# ============================================================================
# 实验数据库
# ============================================================================

class ExperimentDB:
    """实验记录数据库"""

    def __init__(self, db_path: str = DB_EXPERIMENTS):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        import os
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self.conn = duckdb.connect(self.db_path)
        self._create_tables()
        return self

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id VARCHAR PRIMARY KEY,
                pattern VARCHAR NOT NULL,
                pattern_desc VARCHAR,
                direction VARCHAR,
                hold_bars INTEGER,
                stop_loss_pct DOUBLE,
                take_profit_pct DOUBLE,
                symbols VARCHAR,
                total_trades INTEGER,
                win_rate DOUBLE,
                avg_pnl DOUBLE,
                total_pnl DOUBLE,
                sharpe_ratio DOUBLE,
                max_drawdown DOUBLE,
                profit_factor DOUBLE,
                avg_hold_bars DOUBLE,
                sample_per_symbol DOUBLE,
                year_stability DOUBLE,
                symbol_stability DOUBLE,
                quality_score DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR DEFAULT 'candidate'
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS experiment_trades (
                experiment_id VARCHAR,
                symbol VARCHAR,
                direction VARCHAR,
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                hold_bars INTEGER,
                pnl_pct DOUBLE,
                exit_reason VARCHAR,
                PRIMARY KEY (experiment_id, symbol, entry_time)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_state_matrix (
                state_pattern VARCHAR,
                experiment_id VARCHAR,
                quality_score DOUBLE,
                win_rate DOUBLE,
                direction VARCHAR,
                PRIMARY KEY (state_pattern, experiment_id)
            )
        """)

    def save_experiment(self, exp: Dict):
        self.conn.execute("""
            INSERT OR REPLACE INTO experiments (
                experiment_id, pattern, pattern_desc, direction, hold_bars,
                stop_loss_pct, take_profit_pct, symbols, total_trades,
                win_rate, avg_pnl, total_pnl, sharpe_ratio, max_drawdown,
                profit_factor, avg_hold_bars, sample_per_symbol, year_stability,
                symbol_stability, quality_score, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate')
        """, [
            exp["experiment_id"], exp["pattern"], exp.get("pattern_desc", ""),
            exp["direction"], exp["hold_bars"], exp["stop_loss_pct"],
            exp["take_profit_pct"], exp.get("symbols", ""), exp["total_trades"],
            exp["win_rate"], exp["avg_pnl"], exp["total_pnl"],
            exp.get("sharpe_ratio", 0), exp["max_drawdown"],
            exp.get("profit_factor", 0), exp.get("avg_hold_bars", 0),
            exp.get("sample_per_symbol", 0), exp.get("year_stability", 0),
            exp.get("symbol_stability", 0), exp.get("quality_score", 0),
            datetime.now()
        ])

    def save_trades(self, experiment_id: str, trades: List[Dict]):
        for t in trades:
            self.conn.execute("""
                INSERT OR REPLACE INTO experiment_trades VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [experiment_id, t["symbol"], t["direction"], t["entry_time"],
                  t.get("exit_time"), t["hold_bars"], t["pnl_pct"], t["exit_reason"]])

    def save_matrix(self, state_pattern: str, experiment_id: str, quality: float, win_rate: float, direction: str):
        self.conn.execute("""
            INSERT OR REPLACE INTO strategy_state_matrix VALUES (?, ?, ?, ?, ?)
        """, [state_pattern, experiment_id, quality, win_rate, direction])

    def get_top_experiments(self, limit: int = 20) -> pd.DataFrame:
        return self.conn.execute(f"""
            SELECT * FROM experiments
            WHERE total_trades >= 10 AND quality_score > 0
            ORDER BY quality_score DESC
            LIMIT {limit}
        """).fetchdf()

    def get_experiment(self, experiment_id: str) -> Optional[Dict]:
        df = self.conn.execute(
            "SELECT * FROM experiments WHERE experiment_id = ?", [experiment_id]
        ).fetchdf()
        return df.iloc[0].to_dict() if not df.empty else None

    def close(self):
        if self.conn:
            self.conn.close()


# ============================================================================
# State 模式解析
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
    """
    解析模式字符串: "D1=6,H1=4,H4=2" → {timeframe: hex_value}
    """
    parts = {}
    for item in pattern_str.split(","):
        if "=" in item:
            tf, val = item.strip().split("=")
            parts[tf.strip().upper()] = val.strip()
    return parts


def pattern_to_desc(pattern: Dict) -> str:
    """模式描述"""
    descs = []
    for tf, hex_val in sorted(pattern.items()):
        comp = decode_hex(hex_val)
        dir_str = comp["dir"]
        extras = []
        if comp["trend"]:
            extras.append("trend")
        if comp["breakout"]:
            extras.append("breakout")
        if comp["squeeze"]:
            extras.append("squeeze")
        extra_str = f"({','.join(extras)})" if extras else ""
        descs.append(f"{tf}={hex_val}{extra_str}")
    return " + ".join(descs)


def match_pattern(row: pd.Series, pattern: Dict) -> bool:
    """检查一行数据是否匹配模式"""
    for tf, expected_hex in pattern.items():
        col = f"{tf.lower()}_hex"
        if col not in row.index:
            return False
        if str(row[col]) != expected_hex:
            return False
    return True


# ============================================================================
# 回测引擎
# ============================================================================

def backtest_pattern(
    df: pd.DataFrame,
    pattern: Dict,
    direction: str,
    hold_bars: int,
    stop_loss_pct: float,
    take_profit_pct: float,
) -> Dict:
    """
    回测指定模式

    Returns: {total_trades, wins, losses, pnl_list, trades}
    """
    trades = []
    in_trade = False
    entry_idx = 0
    entry_pnl = 0.0
    hold_count = 0

    for i in range(len(df)):
        row = df.iloc[i]

        if in_trade:
            hold_count += 1
            h1_dir = decode_hex(row.get("h1_hex", ""))["dir"]

            # 收益模拟
            if direction == "long":
                if h1_dir == "bull":
                    entry_pnl += 0.12
                elif h1_dir == "bear":
                    entry_pnl -= 0.18
            else:
                if h1_dir == "bear":
                    entry_pnl += 0.12
                elif h1_dir == "bull":
                    entry_pnl -= 0.18

            # 平仓检查
            exit_reason = ""
            if entry_pnl <= -stop_loss_pct:
                exit_reason = "stop_loss"
            elif entry_pnl >= take_profit_pct:
                exit_reason = "take_profit"
            elif hold_count >= hold_bars:
                exit_reason = "time_exit"

            if exit_reason:
                trades.append({
                    "symbol": df.attrs.get("symbol", "unknown"),
                    "direction": direction,
                    "entry_time": str(df.iloc[entry_idx].get("timestamp", "")),
                    "exit_time": str(row.get("timestamp", "")),
                    "hold_bars": hold_count,
                    "pnl_pct": round(entry_pnl, 3),
                    "exit_reason": exit_reason,
                })
                in_trade = False

        else:
            if match_pattern(row, pattern):
                in_trade = True
                entry_idx = i
                entry_pnl = 0.0
                hold_count = 0

    return {"trades": trades}


# ============================================================================
# 质量评估
# ============================================================================

def evaluate_quality(trades: List[Dict], symbols: List[str]) -> Dict:
    """评估实验质量"""
    if not trades:
        return {"quality_score": 0, "total_trades": 0}

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total = len(trades)
    win_rate = len(wins) / total if total > 0 else 0
    avg_pnl = np.mean(pnls) if pnls else 0
    total_pnl = sum(pnls)

    # Sharpe (简化)
    if len(pnls) > 1:
        sharpe = np.mean(pnls) / np.std(pnls) if np.std(pnls) > 0 else 0
    else:
        sharpe = 0

    # 最大回撤
    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdown = peak - cumulative
    max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0

    # 盈亏比
    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 1
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

    # 年份稳定性 (按季度统计胜率)
    year_stability = 0
    if total >= 20:
        quarter_size = max(1, total // 4)
        quarter_wins = []
        for q in range(4):
            start = q * quarter_size
            end = min(start + quarter_size, total)
            q_pnls = pnls[start:end]
            q_wr = len([p for p in q_pnls if p > 0]) / len(q_pnls) if q_pnls else 0
            quarter_wins.append(q_wr)
        year_stability = 1 - np.std(quarter_wins) if len(quarter_wins) > 1 else 0

    # 品种稳定性
    symbol_stability = 0
    if len(symbols) > 1:
        sym_wr = []
        for sym in symbols:
            sym_trades = [t for t in trades if t["symbol"] == sym]
            if sym_trades:
                sym_wr.append(len([t for t in sym_trades if t["pnl_pct"] > 0]) / len(sym_trades))
        symbol_stability = 1 - np.std(sym_wr) if len(sym_wr) > 1 else 0

    # 样本数 / 品种
    sample_per_symbol = total / len(symbols) if symbols else total

    # 综合质量分 (0-100)
    quality = 0
    if total >= 10:
        quality += min(20, win_rate * 25)  # 胜率贡献 (max 20)
        quality += min(20, sharpe * 5)  # Sharpe贡献 (max 20)
        quality += min(15, profit_factor * 5)  # 盈亏比贡献 (max 15)
        quality += min(15, year_stability * 20)  # 年份稳定性 (max 15)
        quality += min(15, symbol_stability * 20)  # 品种稳定性 (max 15)
        quality += min(15, sample_per_symbol / 5)  # 样本充分性 (max 15)
        quality = max(0, min(100, quality))

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
# 策略搜索引擎
# ============================================================================

class StrategyMiner:
    """策略搜索引擎"""

    def __init__(self):
        self.state_conn = duckdb.connect(DB_STATE, read_only=True)
        self.exp_db = ExperimentDB()
        self.exp_db.connect()
        self.all_data = self._load_all_data()

    def _load_all_data(self) -> Dict[str, pd.DataFrame]:
        """加载所有品种的 State 数据"""
        symbols = self.state_conn.execute(
            "SELECT DISTINCT symbol FROM h1_state_snapshot"
        ).fetchdf()["symbol"].tolist()

        data = {}
        for sym in symbols:
            df = self.state_conn.execute("""
                SELECT timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex
                FROM h1_state_snapshot WHERE symbol = ?
                ORDER BY timestamp
            """, [sym]).fetchdf()
            df.attrs["symbol"] = sym
            data[sym] = df

        logger.info(f"加载 {len(data)} 个品种, 总计 {sum(len(d) for d in data.values())} 条")
        return data

    def find_high_freq_patterns(self, min_occurrences: int = 30) -> List[Dict]:
        """找出高频 State 模式"""
        pattern_counts = {}

        for sym, df in self.all_data.items():
            for _, row in df.iterrows():
                d1 = str(row.get("d1_hex", ""))
                h4 = str(row.get("h4_hex", ""))
                h1 = str(row.get("h1_hex", ""))

                # 只看有趋势触发的模式
                h1_comp = decode_hex(h1)
                if not h1_comp["trend"]:
                    continue

                pattern_key = f"D1={d1},H4={h4},H1={h1}"
                if pattern_key not in pattern_counts:
                    pattern_counts[pattern_key] = {"count": 0, "symbols": set()}
                pattern_counts[pattern_key]["count"] += 1
                pattern_counts[pattern_key]["symbols"].add(sym)

        # 过滤：至少出现在2个品种，总次数 >= min_occurrences
        valid = []
        for pattern_str, info in pattern_counts.items():
            if info["count"] >= min_occurrences and len(info["symbols"]) >= 2:
                valid.append({
                    "pattern": pattern_str,
                    "count": info["count"],
                    "symbols": list(info["symbols"]),
                })

        valid.sort(key=lambda x: -x["count"])
        logger.info(f"找到 {len(valid)} 个高频模式 (>= {min_occurrences}次, >= 2品种)")
        return valid

    def run_experiment(
        self,
        pattern_str: str,
        direction: str,
        hold_bars: int,
        stop_loss_pct: float,
        take_profit_pct: float,
        symbols: List[str] = None,
    ) -> Dict:
        """运行单个实验"""
        pattern = parse_pattern(pattern_str)
        symbols = symbols or list(self.all_data.keys())

        all_trades = []
        for sym in symbols:
            if sym not in self.all_data:
                continue
            df = self.all_data[sym]
            df.attrs["symbol"] = sym
            result = backtest_pattern(df, pattern, direction, hold_bars, stop_loss_pct, take_profit_pct)
            all_trades.extend(result["trades"])

        quality = evaluate_quality(all_trades, symbols)

        # 生成实验ID
        exp_key = f"{pattern_str}|{direction}|{hold_bars}|{stop_loss_pct}|{take_profit_pct}"
        exp_id = hashlib.md5(exp_key.encode()).hexdigest()[:12]

        experiment = {
            "experiment_id": exp_id,
            "pattern": pattern_str,
            "pattern_desc": pattern_to_desc(pattern),
            "direction": direction,
            "hold_bars": hold_bars,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "symbols": ",".join(symbols),
            **quality,
        }

        return experiment, all_trades

    def scan_pattern(self, pattern_str: str, symbols: List[str] = None) -> List[Dict]:
        """对单个模式扫描所有参数组合"""
        directions = ["long", "short"]
        hold_options = [6, 12, 24, 48]
        sl_options = [1.0, 2.0, 3.0]
        tp_options = [2.0, 3.0, 5.0]

        results = []
        for direction, hold, sl, tp in product(directions, hold_options, sl_options, tp_options):
            exp, trades = self.run_experiment(pattern_str, direction, hold, sl, tp, symbols)
            if exp["total_trades"] >= 5:
                results.append(exp)
                self.exp_db.save_experiment(exp)
                self.exp_db.save_trades(exp["experiment_id"], trades)
                self.exp_db.save_matrix(pattern_str, exp["experiment_id"],
                                        exp["quality_score"], exp["win_rate"], direction)

        # 按质量分排序
        results.sort(key=lambda x: -x["quality_score"])
        return results

    def scan_all(self, top_n: int = 20) -> Dict:
        """扫描所有高频模式"""
        patterns = self.find_high_freq_patterns(min_occurrences=30)
        all_results = []

        for i, p in enumerate(patterns[:top_n]):
            logger.info(f"[{i+1}/{min(top_n, len(patterns))}] 扫描: {p['pattern']} ({p['count']}次)")
            results = self.scan_pattern(p["pattern"])
            if results:
                best = results[0]
                all_results.append(best)
                logger.info(f"  最优: {best['direction']} hold={best['hold_bars']} "
                            f"WR={best['win_rate']:.1%} quality={best['quality_score']}")

        all_results.sort(key=lambda x: -x["quality_score"])
        return {"total_patterns": len(patterns), "scanned": min(top_n, len(patterns)),
                "results": all_results}

    def generate_report(self, results: Dict = None) -> str:
        """生成 Markdown 报告"""
        if results is None:
            top = self.exp_db.get_top_experiments(20)
        else:
            top = pd.DataFrame(results.get("results", []))

        if top.empty:
            return "# 策略搜索报告\n\n无有效实验结果。"

        lines = [
            "# 策略搜索报告",
            f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"\n## Top {len(top)} 策略\n",
            "| 排名 | 模式 | 方向 | 持仓 | 胜率 | Sharpe | 盈亏比 | 最大回撤 | 质量分 |",
            "|------|------|------|------|------|--------|--------|---------|--------|",
        ]

        for i, (_, row) in enumerate(top.iterrows()):
            lines.append(
                f"| {i+1} | {row.get('pattern','')} | {row.get('direction','')} | "
                f"{row.get('hold_bars','')}h | {row.get('win_rate',0):.1%} | "
                f"{row.get('sharpe_ratio',0):.2f} | {row.get('profit_factor',0):.2f} | "
                f"{row.get('max_drawdown',0):.1f}% | {row.get('quality_score',0):.0f} |"
            )

        lines.append("\n## 策略-STATE 适配矩阵\n")
        lines.append("模式 → 最优策略映射 (quality_score > 50 的实验)\n")

        matrix = self.exp_db.conn.execute("""
            SELECT state_pattern, experiment_id, quality_score, win_rate, direction
            FROM strategy_state_matrix
            WHERE quality_score > 50
            ORDER BY quality_score DESC
            LIMIT 30
        """).fetchdf()

        if not matrix.empty:
            lines.append("| State 模式 | 实验ID | 质量分 | 胜率 | 方向 |")
            lines.append("|-----------|--------|--------|------|------|")
            for _, r in matrix.iterrows():
                lines.append(f"| {r['state_pattern']} | {r['experiment_id']} | "
                             f"{r['quality_score']:.0f} | {r['win_rate']:.1%} | {r['direction']} |")

        return "\n".join(lines)

    def close(self):
        self.state_conn.close()
        self.exp_db.close()


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="策略搜索引擎")
    parser.add_argument("--scan-all", action="store_true", help="扫描所有高频模式")
    parser.add_argument("--pattern", type=str, help="指定模式 (如 'D1=6,H1=4')")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--top", type=int, default=20, help="扫描前N个模式")
    args = parser.parse_args()

    miner = StrategyMiner()

    if args.report:
        report = miner.generate_report()
        report_path = "data/strategy_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已生成: {report_path}")
        print(report)

    elif args.pattern:
        logger.info(f"扫描模式: {args.pattern}")
        results = miner.scan_pattern(args.pattern)
        if results:
            print(f"\nTop 5 参数组合:")
            for i, r in enumerate(results[:5]):
                print(f"  {i+1}. {r['direction']} hold={r['hold_bars']}h "
                      f"SL={r['stop_loss_pct']} TP={r['take_profit_pct']} "
                      f"WR={r['win_rate']:.1%} quality={r['quality_score']}")

    elif args.scan_all:
        logger.info(f"全量扫描 Top {args.top} 模式...")
        results = miner.scan_all(top_n=args.top)

        # 保存报告
        report = miner.generate_report(results)
        with open("data/strategy_report.md", "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n{'='*60}")
        print(f"扫描完成: {results['scanned']} 个模式")
        print(f"有效策略: {len(results['results'])} 个")
        print(f"报告: data/strategy_report.md")
        print(f"{'='*60}")

        if results["results"]:
            print(f"\nTop 5:")
            for i, r in enumerate(results["results"][:5]):
                print(f"  {i+1}. {r['pattern']} | {r['direction']} hold={r['hold_bars']}h "
                      f"WR={r['win_rate']:.1%} PF={r['profit_factor']:.2f} Q={r['quality_score']}")

    else:
        # 默认：显示高频模式
        patterns = miner.find_high_freq_patterns(min_occurrences=20)
        print(f"\n高频 State 模式 (Top 20):")
        for i, p in enumerate(patterns[:20]):
            comp = parse_pattern(p["pattern"])
            desc = pattern_to_desc(comp)
            print(f"  {i+1:2d}. {p['pattern']:30s} {p['count']:>5}次 {len(p['symbols'])}品种  {desc}")

    miner.close()


if __name__ == "__main__":
    main()
