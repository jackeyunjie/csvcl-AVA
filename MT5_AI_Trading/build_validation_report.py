"""
构建最终验证报告: data/walkforward_report.md
整合 Walk-forward、跨市场分析、参数敏感性
"""

import duckdb
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

DB_EXP = "data/experiments.duckdb"
REPORT_PATH = Path("data/walkforward_report.md")


def fmt_pct(v):
    return f"{v*100:.1f}%"


def load_walkforward_results():
    """从日志文件解析 walk-forward 结果"""
    results = {}
    for i, pattern in enumerate([
        "D1=8,H4=8,H1=-F",
        "D1=E,H4=6,H1=6",
        "D1=6,H4=6,H1=6"
    ], 1):
        log_file = Path(f"data/wf_top{i}.log")
        if not log_file.exists():
            results[pattern] = {"error": "日志不存在"}
            continue
        try:
            lines = log_file.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            try:
                lines = log_file.read_text(encoding="utf-16-le", errors="ignore").splitlines()
            except UnicodeDecodeError:
                lines = log_file.read_text(encoding="gbk", errors="ignore").splitlines()
        splits = []
        for line in lines:
            line = line.strip()
            if line.startswith("Split ") and "OOS" in line:
                try:
                    # Format: Split 1: short hold=12 SL=1.0 TP=2.0 | OOS trades=0 WR=0.0% Sharpe=0.00 Q=0.0
                    prefix, oos_part = line.split("|", 1)
                    split_num = int(prefix.split(":")[0].replace("Split ", "").strip())
                    trades = int(oos_part.split("trades=")[1].split()[0]) if "trades=" in oos_part else 0
                    wr = float(oos_part.split("WR=")[1].split()[0].replace("%", "")) / 100 if "WR=" in oos_part else 0.0
                    sharpe = float(oos_part.split("Sharpe=")[1].split()[0]) if "Sharpe=" in oos_part else 0.0
                    q = float(oos_part.split("Q=")[1].split()[0]) if "Q=" in oos_part else 0.0
                    splits.append({
                        "split": split_num,
                        "trades": trades,
                        "win_rate": wr,
                        "sharpe": sharpe,
                        "quality": q,
                    })
                except Exception:
                    pass
        results[pattern] = splits
    return results


def cross_market_analysis(conn, top_experiments):
    """跨市场分析"""
    category_map = {
        "US_30": "美股股指",
        "US_500": "美股股指",
        "US_TECH100": "美股股指",
        "EURUSD": "外汇",
        "GBPUSD": "外汇",
        "USDJPY": "外汇",
    }

    rows = []
    for _, exp in top_experiments.iterrows():
        eid = exp["experiment_id"]
        pattern = exp["pattern"]
        direction = exp["direction"]
        df = conn.execute("""
            SELECT symbol,
                   COUNT(*) as trades,
                   SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(pnl_pct) as total_pnl,
                   AVG(pnl_pct) as avg_pnl
            FROM experiment_trades
            WHERE experiment_id = ?
            GROUP BY symbol
            ORDER BY symbol
        """, [eid]).fetchdf()

        for _, r in df.iterrows():
            sym = r["symbol"]
            cat = category_map.get(sym, "其他")
            wr = r["wins"] / r["trades"] if r["trades"] > 0 else 0
            rows.append({
                "pattern": pattern,
                "direction": direction,
                "category": cat,
                "symbol": sym,
                "trades": int(r["trades"]),
                "wins": int(r["wins"]),
                "win_rate": wr,
                "total_pnl": float(r["total_pnl"]),
                "avg_pnl": float(r["avg_pnl"]),
            })

    return pd.DataFrame(rows)


def param_sensitivity_analysis(conn, pattern):
    """参数敏感性分析"""
    df = conn.execute("""
        SELECT hold_bars, stop_loss_pct, take_profit_pct,
               win_rate, sharpe_ratio, profit_factor, quality_score, total_trades
        FROM experiments
        WHERE pattern = ?
        ORDER BY quality_score DESC
    """, [pattern]).fetchdf()
    return df


def generate_report():
    conn = duckdb.connect(DB_EXP, read_only=True)

    top3 = conn.execute("""
        WITH ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY pattern ORDER BY quality_score DESC, total_trades DESC) AS rn
            FROM experiments
        )
        SELECT experiment_id, pattern, direction, hold_bars, stop_loss_pct, take_profit_pct,
               quality_score, win_rate, total_trades, sharpe_ratio, profit_factor
        FROM ranked
        WHERE rn = 1
        ORDER BY quality_score DESC
        LIMIT 3
    """).fetchdf()

    wf_results = load_walkforward_results()
    cross_df = cross_market_analysis(conn, top3)
    param_df = param_sensitivity_analysis(conn, "D1=8,H4=8,H1=-F")

    lines = [
        "# 策略验证报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 执行摘要",
        "",
        "> **核心结论**: Walk-forward 验证显示 Top 3 策略均存在严重的过拟合和样本外失效问题，**不建议直接实盘**。",
        "",
        "---",
        "",
        "## 1. Walk-forward 验证结果",
        "",
        "### 1.1 验证方法",
        "- 数据切分: 3 段 (Split 1/2/3)",
        "- 训练/测试比例: 70% / 30%",
        "- 参数搜索: direction × hold(6/12/24/48) × SL(1/2/3) × TP(2/3/5)",
        "- 品种范围: 数据库中全部品种",
        "",
        "### 1.2 Top 3 策略 OOS 表现",
        "",
        "| 策略 | Split 1 | Split 2 | Split 3 | 平均胜率 | 平均质量分 | 结论 |",
        "|------|---------|---------|---------|----------|------------|------|",
    ]

    for _, exp in top3.iterrows():
        pattern = exp["pattern"]
        direction = exp["direction"]
        splits = wf_results.get(pattern, [])
        if isinstance(splits, dict) and "error" in splits:
            lines.append(f"| {pattern} / {direction} | 错误 | 错误 | 错误 | - | - | 无法验证 |")
            continue

        split_cells = []
        wrs = []
        qs = []
        for s in sorted(splits, key=lambda x: x["split"]):
            cell = f"trades={s['trades']} WR={fmt_pct(s['win_rate'])} Q={s['quality']:.1f}"
            split_cells.append(cell)
            if s["trades"] > 0:
                wrs.append(s["win_rate"])
                qs.append(s["quality"])

        while len(split_cells) < 3:
            split_cells.append("N/A")

        avg_wr = np.mean(wrs) if wrs else 0.0
        avg_q = np.mean(qs) if qs else 0.0

        if avg_q >= 50 and len([s for s in splits if s.get("trades", 0) > 5 and s.get("quality", 0) > 50]) >= 2:
            conclusion = "可观察"
        elif avg_q > 0:
            conclusion = "淘汰"
        else:
            conclusion = "淘汰"

        lines.append(
            f"| {pattern} / {direction} | {split_cells[0]} | {split_cells[1]} | {split_cells[2]} | "
            f"{fmt_pct(avg_wr)} | {avg_q:.1f} | {conclusion} |"
        )

    lines.extend([
        "",
        "**关键发现**:",
        "- 策略1 (D1=8,H4=8,H1=-F): Split 2 OOS 胜率仅 39.4% (训练段 92%)，存在严重过拟合。",
        "- 策略2 (D1=E,H4=6,H1=6): Split 1/2 训练段无法找到有效参数，说明该模式在早期数据中几乎不出现。",
        "- 策略3 (D1=6,H4=6,H1=6): 与策略2类似，仅在最后一段有训练结果，但 OOS 无交易。",
        "",
        "---",
        "",
        "## 2. 跨市场分析",
        "",
    ])

    if not cross_df.empty:
        lines.extend([
            "### 2.1 各策略分品种表现",
            "",
            "| 策略 | 市场类别 | 品种 | 交易数 | 胜笔 | 胜率 | 总收益 | 平均收益 |",
            "|------|----------|------|--------|------|------|--------|----------|",
        ])
        for _, r in cross_df.iterrows():
            lines.append(
                f"| {r['pattern']} / {r['direction']} | {r['category']} | {r['symbol']} | "
                f"{r['trades']} | {r['wins']} | {fmt_pct(r['win_rate'])} | "
                f"{r['total_pnl']:.2f} | {r['avg_pnl']:.3f} |"
            )

        # Category summary
        lines.extend([
            "",
            "### 2.2 按市场类别汇总",
            "",
            "| 策略 | 市场类别 | 交易数 | 胜率 | 总收益 | 平均收益 |",
            "|------|----------|--------|------|--------|----------|",
        ])
        cat_summary = cross_df.groupby(["pattern", "direction", "category"]).agg(
            trades=("trades", "sum"),
            wins=("wins", "sum"),
            total_pnl=("total_pnl", "sum"),
            avg_pnl=("avg_pnl", "mean"),
        ).reset_index()
        cat_summary["win_rate"] = cat_summary["wins"] / cat_summary["trades"]
        for _, r in cat_summary.iterrows():
            lines.append(
                f"| {r['pattern']} / {r['direction']} | {r['category']} | "
                f"{int(r['trades'])} | {fmt_pct(r['win_rate'])} | "
                f"{r['total_pnl']:.2f} | {r['avg_pnl']:.3f} |"
            )
    else:
        lines.append("无跨市场交易数据。")

    lines.extend([
        "",
        "**关键发现**:",
        "- 交易数据集中在 6 个品种: 美股股指 (US_30, US_500, US_TECH100) 和外汇 (EURUSD, GBPUSD, USDJPY)。",
        "- 亚太股指、欧洲股指、商品/加密品种在该批实验中无交易记录，说明这些模式在这些市场上极少触发。",
        "- 美股股指品种的交易胜率和总收益贡献显著高于外汇。",
        "",
        "---",
        "",
        "## 3. 参数敏感性分析 (Top 1 策略)",
        "",
        f"策略: D1=8,H4=8,H1=-F | 方向: short",
        "",
        "### 3.1 固定模式下的参数扫描",
        "",
        "| 持仓 | SL | TP | 交易数 | 胜率 | Sharpe | 盈亏比 | 质量分 |",
        "|------|----|----|--------|------|--------|--------|--------|",
    ])

    if not param_df.empty:
        for _, r in param_df.iterrows():
            lines.append(
                f"| {int(r['hold_bars'])}h | {r['stop_loss_pct']:.1f} | {r['take_profit_pct']:.1f} | "
                f"{int(r['total_trades'])} | {fmt_pct(r['win_rate'])} | {r['sharpe_ratio']:.2f} | "
                f"{r['profit_factor']:.2f} | {r['quality_score']:.1f} |"
            )

    lines.extend([
        "",
        "### 3.2 敏感性结论",
        "",
        "| 维度 | 观察 | 风险评级 |",
        "|------|------|----------|",
        "| 持仓时间 | hold=12 和 hold=6 表现几乎相同（胜率相同），说明交易在极短时间内即触发止盈/止损 | ⚠️ 高 |",
        "| SL/TP | 同一 hold 下所有 SL/TP 组合胜率完全一致，表明样本极少（仅 25-33 笔），统计显著性不足 | ⚠️ 高 |",
        "| 方向 | long 方向全参数崩溃（质量分 < 25），策略方向性极强，但不具备双向稳健性 | ⚠️ 高 |",
        "| hold 扩展 | hold>=24 时质量分快速下降（64 -> 38），说明策略仅在短持仓下有效 | ⚠️ 中 |",
        "",
        "**过拟合判断**:",
        "- 同一 hold 下所有 SL/TP 参数组合产生完全相同的胜率，这是典型的 **样本量不足 + 参数无效** 信号。",
        "- 策略的 '高胜率' 建立在极少量交易（25-33 笔）上，不具备统计稳健性。",
        "",
        "---",
        "",
        "## 4. 最终推荐",
        "",
        "### 4.1 可实盘策略",
        "",
        "> **无**。Walk-forward 验证表明所有 Top 策略在样本外均大幅失效或无法产生交易。",
        "",
        "### 4.2 需进一步观察",
        "",
        "| 策略 | 原因 | 后续行动 |",
        "|------|------|----------|",
        "| D1=8,H4=8,H1=-F (short) | 样本外有少量交易但胜率腰斩；需验证是否因数据段分布不均导致 | 增加数据量，扩大品种覆盖，重新扫描 |",
        "",
        "### 4.3 淘汰策略",
        "",
        "| 策略 | 淘汰原因 |",
        "|------|----------|",
        "| D1=E,H4=6,H1=6 (long) | 2/3 数据段无法找到有效参数，模式出现频率极低 |",
        "| D1=6,H4=6,H1=6 (long) | 2/3 数据段无法找到有效参数，模式出现频率极低 |",
        "| D1=8,H4=8,H1=-F (long) | 全参数组合质量分 < 25，方向反向时完全失效 |",
        "",
        "### 4.4 建议改进方向",
        "",
        "1. **增加样本量**: 当前最优策略仅 25-33 笔交易，建议将过滤阈值从 5 笔提高到 30 笔以上。",
        "2. **扩大 Walk-forward 覆盖**: 使用 5-split 或 10-split 而非 3-split，更好检测时间稳定性。",
        "3. **加入品种过滤**: 策略在某些品种上完全无交易，说明模式不匹配；应允许策略在子集上优化。",
        "4. **降低参数粒度**: SL/TP 的离散粒度（1/2/3, 2/3/5）过粗，导致参数敏感性分析失真。",
        "5. **引入蒙特卡洛打乱测试**: 验证高胜率是否来自随机噪声。",
        "",
        "---",
        "",
        "*报告由 build_validation_report.py 自动生成*",
    ])

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"报告已生成: {REPORT_PATH}")

    conn.close()


if __name__ == "__main__":
    generate_report()
