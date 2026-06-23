"""
多周期收缩观测 - 实际运行

从MT5获取多周期数据，运行独立Agent观测，然后进行跨周期辩论
"""
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent / "python"))

import pandas as pd
import numpy as np

from analytics.multi_timeframe_squeeze import MultiTimeframeSqueezeSystem, CrossTimeframeSignal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("mtf_debate")

# 品种映射
SYMBOL_MAP = {
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
    "XAUUSD": "GOLD",
    "XAGUSD": "SILVER",
    "US30": "US_30",
    "US500": "US_500",
    "NAS100": "US_TECH100",
    "GER40": "GERMANY_40",
    "UK100": "UK_100",
    "USOIL": "CrudeOIL",
    "UKOIL": "BRENT_OIL",
    "BTCUSD": "BTCUSD",
    "ETHUSD": "ETHUSD",
}


def run_debate_for_symbol(std_name: str, mt5_name: str,
                          timeframes: list = None) -> CrossTimeframeSignal:
    """对单个品种运行多周期辩论"""
    if timeframes is None:
        timeframes = ["MN1", "W1", "D1", "H4", "H1"]

    logger.info(f"\n{'='*60}")
    logger.info(f"多周期辩论: {std_name}")
    logger.info(f"{'='*60}")

    system = MultiTimeframeSqueezeSystem()
    signal = system.analyze_from_mt5(std_name, mt5_name, timeframes, lookback_days=120)

    return signal


def main():
    print("=" * 70)
    print("多周期收缩观测系统 - 跨周期辩论")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    # 选择重点品种进行多周期分析
    priority_symbols = [
        ("EURUSD", "EURUSD"),
        ("GBPUSD", "GBPUSD"),
        ("USDJPY", "USDJPY"),
        ("XAUUSD", "GOLD"),
        ("US30", "US_30"),
        ("US500", "US_500"),
        ("NAS100", "US_TECH100"),
        ("GER40", "GERMANY_40"),
        ("BTCUSD", "BTCUSD"),
    ]

    timeframes = ["MN1", "W1", "D1", "H4", "H1"]
    all_signals = []

    for std_name, mt5_name in priority_symbols:
        try:
            signal = run_debate_for_symbol(std_name, mt5_name, timeframes)
            if signal:
                all_signals.append(signal)
                print(f"\n{signal.debate_summary}")
                print(f"\n>>> 最终信号: {signal.consensus_direction.upper()} "
                      f"(信心={signal.consensus_confidence:.2f}, "
                      f"阶段={signal.opportunity_stage}, "
                      f"突破共振={signal.breakout_resonance_score}个周期)\n")
        except Exception as e:
            logger.error(f"分析失败 {std_name}: {e}")

    # 汇总所有信号
    print("\n" + "=" * 70)
    print("多周期信号汇总")
    print("=" * 70)

    long_signals = [s for s in all_signals if s.consensus_direction == "long"]
    short_signals = [s for s in all_signals if s.consensus_direction == "short"]
    hold_signals = [s for s in all_signals if s.consensus_direction == "hold"]
    best_opportunities = [s for s in all_signals if s.opportunity_stage == "resonant_breakout"]
    leading_breakouts = [s for s in all_signals if s.opportunity_stage == "leading_breakout"]
    squeeze_setups = [s for s in all_signals if s.opportunity_stage == "squeeze_setup"]

    if long_signals:
        print(f"\n【做多信号】({len(long_signals)}个):")
        for s in sorted(long_signals, key=lambda x: x.consensus_confidence, reverse=True):
            print(f"  {s.symbol:8s}: 信心={s.consensus_confidence:.2f}, "
                  f"阶段={s.opportunity_stage}, "
                  f"突破共振={s.breakout_resonance_score}个周期 ({', '.join(s.breakout_resonance_timeframes)})")

    if short_signals:
        print(f"\n【做空信号】({len(short_signals)}个):")
        for s in sorted(short_signals, key=lambda x: x.consensus_confidence, reverse=True):
            print(f"  {s.symbol:8s}: 信心={s.consensus_confidence:.2f}, "
                  f"阶段={s.opportunity_stage}, "
                  f"突破共振={s.breakout_resonance_score}个周期 ({', '.join(s.breakout_resonance_timeframes)})")

    if hold_signals:
        print(f"\n【观望】({len(hold_signals)}个):")
        for s in hold_signals:
            print(f"  {s.symbol:8s}: 信心={s.consensus_confidence:.2f}, "
                  f"阶段={s.opportunity_stage}, 收缩底座={s.setup_resonance_score}个周期")

    if best_opportunities:
        print(f"\n【最佳交易机会】({len(best_opportunities)}个，多周期收缩后同向共振突破):")
        for s in sorted(best_opportunities, key=lambda x: x.consensus_confidence, reverse=True):
            print(f"  {s.symbol:8s}: {s.consensus_direction.upper()} "
                  f"信心={s.consensus_confidence:.2f}, "
                  f"突破={s.breakout_resonance_score}周期({', '.join(s.breakout_resonance_timeframes)}), "
                  f"底座={s.setup_resonance_score}周期")

    if leading_breakouts:
        print(f"\n【领先突破】({len(leading_breakouts)}个，等待第二周期确认):")
        for s in sorted(leading_breakouts, key=lambda x: x.consensus_confidence, reverse=True):
            print(f"  {s.symbol:8s}: {s.consensus_direction.upper()} "
                  f"信心={s.consensus_confidence:.2f}, "
                  f"突破={s.breakout_resonance_score}周期, 底座={s.setup_resonance_score}周期")

    if squeeze_setups:
        print(f"\n【等待突破的收缩底座】({len(squeeze_setups)}个):")
        for s in sorted(squeeze_setups, key=lambda x: x.setup_resonance_score, reverse=True):
            print(f"  {s.symbol:8s}: 收缩底座={s.setup_resonance_score}周期 "
                  f"({', '.join(s.setup_resonance_timeframes)})")

    # 高共振品种（多周期同步收缩）
    high_resonance = [s for s in all_signals if s.resonance_score >= 2]
    if high_resonance:
        print(f"\n【高共振品种】({len(high_resonance)}个，多周期同步收缩）:")
        for s in sorted(high_resonance, key=lambda x: x.resonance_score, reverse=True):
            print(f"  {s.symbol:8s}: {s.resonance_score}个周期共振 "
                  f"({', '.join(s.resonance_timeframes)}), 方向={s.consensus_direction}")

    print("\n" + "=" * 70)

    # 保存报告
    report_lines = []
    report_lines.append("# 多周期收缩观测报告")
    report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    report_lines.append("## 信号汇总\n")
    report_lines.append(f"- 做多: {len(long_signals)}个")
    report_lines.append(f"- 做空: {len(short_signals)}个")
    report_lines.append(f"- 观望: {len(hold_signals)}个")
    report_lines.append(f"- 最佳交易机会(共振突破): {len(best_opportunities)}个")
    report_lines.append(f"- 领先突破: {len(leading_breakouts)}个")
    report_lines.append(f"- 等待突破的收缩底座: {len(squeeze_setups)}个")
    report_lines.append(f"- 高共振(>=2周期): {len(high_resonance)}个\n")

    report_lines.append("## 最佳交易机会\n")
    if best_opportunities:
        report_lines.append("| 品种 | 方向 | 信心 | 突破周期 | 收缩底座 | 说明 |")
        report_lines.append("|------|------|------|----------|----------|------|")
        for s in sorted(best_opportunities, key=lambda x: x.consensus_confidence, reverse=True):
            report_lines.append(
                f"| {s.symbol} | {s.consensus_direction.upper()} | {s.consensus_confidence:.2f} | "
                f"{','.join(s.breakout_resonance_timeframes)} | {','.join(s.setup_resonance_timeframes)} | "
                f"{s.action_note} |"
            )
    else:
        report_lines.append("当前无多周期收缩后同向共振突破。")
    report_lines.append("")

    report_lines.append("## 详细辩论记录\n")
    for s in all_signals:
        report_lines.append(f"### {s.symbol}")
        report_lines.append(f"```")
        report_lines.append(s.debate_summary)
        report_lines.append(f"```")
        report_lines.append(f"- **最终信号**: {s.consensus_direction.upper()}")
        report_lines.append(f"- **信心度**: {s.consensus_confidence:.2f}")
        report_lines.append(f"- **机会阶段**: {s.opportunity_stage}")
        report_lines.append(f"- **当前收缩周期**: {s.resonance_score}个 ({', '.join(s.resonance_timeframes)})")
        report_lines.append(f"- **收缩底座周期**: {s.setup_resonance_score}个 ({', '.join(s.setup_resonance_timeframes)})")
        report_lines.append(f"- **突破确认周期**: {s.breakout_resonance_score}个 ({', '.join(s.breakout_resonance_timeframes)})")
        report_lines.append("")

    report_content = "\n".join(report_lines)

    # 保存
    from squeeze_report import save_report
    save_report(report_content, sync_obsidian=True)
    logger.info("报告已保存并同步到Obsidian")


if __name__ == "__main__":
    main()
