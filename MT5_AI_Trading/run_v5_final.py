"""
v5 最终执行脚本
整合 B1(14品种白名单) + A1(730天数据) + B2(出场规则修正)

执行流程:
1. v5基线研究 (B1+A1组合)
2. 出场规则对比 (B2修正)
3. 生成综合报告
4. 对比历史版本 (v3/v4/v5)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from squeeze_multi_timeframe_research_v5 import (
    MultiTimeframeSqueezeResearchV5, SYMBOL_MAP, SYMBOL_WHITELIST_V5,
    print_comparison_table
)
from squeeze_multi_timeframe_research_v4 import SYMBOL_WHITELIST
from datetime import datetime
import json


def main():
    print("="*100)
    print("  v5 最终研究执行 — 整合B1(14品种白名单) + A1(730天) + B2(出场规则修正)")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*100)
    
    all_results = {}
    
    # ============================
    # 1. v5基线研究 (B1+A1组合)
    # ============================
    print("\n" + "="*100)
    print("  第1步: v5基线研究 (14品种白名单 + 730天数据)")
    print("="*100)
    
    research_v5 = MultiTimeframeSqueezeResearchV5()
    
    # 临时修改v4的白名单供fetch_multi_timeframe_data使用
    orig_whitelist = SYMBOL_WHITELIST.copy()
    SYMBOL_WHITELIST.clear()
    SYMBOL_WHITELIST.update(SYMBOL_WHITELIST_V5)
    
    try:
        data = research_v5.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=730)
        
        if not data:
            print("错误: 未能获取数据")
            return
        
        research_v5.find_setups(
            min_squeeze_score=2, cooldown_bars=5, require_structural=False,
            use_whitelist=True, max_adx=12.0, min_anchor_range_pct=0.4
        )
        
        research_v5.detect_breakouts(
            max_wait_bars=30, min_breakout_anchor_multiple=0.1,
            require_1bar_confirmation=True
        )
        
        unique_events_v5 = research_v5._deduplicate_breakouts(research_v5.breakouts)
        
        # 运行三类出场规则回测
        research_v5.trades = research_v5._simulate_exit_rule(
            unique_events_v5, "fixed_hold_5bar")
        result_v5_5bar = research_v5.analyze(
            deduplicate=False, exit_rule_filter="fixed_hold_5bar")
        
        if result_v5_5bar:
            all_results['v5-5bar'] = result_v5_5bar
            print(f"\n  v5基线结果 (fixed_hold_5bar):")
            print(f"    Setup: {result_v5_5bar.total_setups}, 唯一突破: {result_v5_5bar.unique_breakouts}")
            print(f"    突破率: {result_v5_5bar.breakout_rate*100:.1f}%")
            print(f"    净胜率: {result_v5_5bar.net_win_rate_5bar*100:.1f}%")
            print(f"    净期望: {result_v5_5bar.net_expectancy_5bar:.3f}%")
            print(f"    Walk-Forward Train/Val/Test: "
                  f"{result_v5_5bar.train_metrics['expectancy']:.3f}% / "
                  f"{result_v5_5bar.validation_metrics['expectancy']:.3f}% / "
                  f"{result_v5_5bar.test_metrics['expectancy']:.3f}%")
            
            # 生成v5基线报告
            report_path, s_path, e_path, t_path = research_v5.generate_report(
                result_v5_5bar, exit_rule_name="fixed_hold_5bar")
            print(f"\n  报告已生成: {report_path}")
    finally:
        SYMBOL_WHITELIST.clear()
        SYMBOL_WHITELIST.update(orig_whitelist)
    
    # ============================
    # 2. 出场规则对比 (B2修正)
    # ============================
    print("\n" + "="*100)
    print("  第2步: 出场规则对比 (B2修正)")
    print("="*100)
    
    research_b2 = MultiTimeframeSqueezeResearchV5()
    
    # 恢复白名单
    SYMBOL_WHITELIST.clear()
    SYMBOL_WHITELIST.update(SYMBOL_WHITELIST_V5)
    
    try:
        data_b2 = research_b2.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=730)
        
        if data_b2:
            research_b2.find_setups(
                min_squeeze_score=2, cooldown_bars=5, require_structural=False,
                use_whitelist=True, max_adx=12.0, min_anchor_range_pct=0.4
            )
            
            research_b2.detect_breakouts(
                max_wait_bars=30, min_breakout_anchor_multiple=0.1,
                require_1bar_confirmation=True
            )
            
            unique_events_b2 = research_b2._deduplicate_breakouts(research_b2.breakouts)
            
            exit_comparison = research_b2.compare_exit_rules(unique_events_b2)
            all_results['B2_exit_rules'] = exit_comparison
            
            # 打印出场规则对比
            print(f"\n{'='*100}")
            print(f"  出场规则对比 (样本: {len(unique_events_b2)}个唯一突破)")
            print(f"{'='*100}")
            print(f"{'规则':<25} {'交易数':>8} {'胜率':>8} {'净期望':>10} {'平均Bar':>8} {'Train':>8} {'Val':>8} {'Test':>8}")
            print("-" * 100)
            
            for rule_name, rule_data in exit_comparison.items():
                print(f"{rule_name:<25} "
                      f"{rule_data['trades']:>8} "
                      f"{rule_data['win_rate']*100:>7.1f}% "
                      f"{rule_data['net_expectancy']:>9.3f}% "
                      f"{rule_data['avg_bars']:>7.1f} "
                      f"{rule_data['train_metrics']['expectancy']:>7.3f}% "
                      f"{rule_data['validation_metrics']['expectancy']:>7.3f}% "
                      f"{rule_data['test_metrics']['expectancy']:>7.3f}%")
            
            # 生成出场规则对比报告
            _generate_exit_rule_report(research_b2, exit_comparison, 
                                       len(unique_events_b2))
            
            # 同时生成每个规则的CSV
            for rule_name in exit_comparison:
                research_b2.trades = research_b2._simulate_exit_rule(
                    unique_events_b2, rule_name)
                result_r = research_b2.analyze(
                    deduplicate=False, exit_rule_filter=rule_name)
                if result_r:
                    research_b2.generate_report(
                        result_r, 
                        exit_rule_name=rule_name,
                        param_analysis={"exit_rule": rule_name})
    finally:
        SYMBOL_WHITELIST.clear()
        SYMBOL_WHITELIST.update(orig_whitelist)
    
    # ============================
    # 3. 版本对比汇总
    # ============================
    print("\n" + "="*100)
    print("  v3 / v4 / v5 版本对比汇总")
    print("="*100)
    
    baseline_data = {
        "v3_baseline": {
            "setup": 7230, "unique": 3286, "br": 71.7,
            "wr": 47.3, "net_exp": -0.005,
            "train": 0.006, "val": -0.029, "test": -0.026
        },
        "v4_baseline": {
            "setup": 573, "unique": 160, "br": 27.9,
            "wr": 65.6, "net_exp": 0.227,
            "train": 0.289, "val": 0.314, "test": -0.107
        },
        "v4_B1": {
            "setup": 527, "unique": 149, "br": 28.3,
            "wr": 66.4, "net_exp": 0.305,
            "train": 0.304, "val": 0.384, "test": 0.168
        },
        "v4_A1": {
            "setup": 1309, "unique": 332, "br": 25.4,
            "wr": 67.8, "net_exp": 0.233,
            "train": 0.205, "val": 0.424, "test": 0.155
        },
        "v4_A2": {
            "setup": 1638, "unique": 394, "br": 24.1,
            "wr": 64.2, "net_exp": 0.171,
            "train": 0.227, "val": 0.108, "test": 0.054
        },
    }
    
    print(f"\n{'版本':<15} {'Setup':>8} {'唯一':>8} {'突破率':>8} {'净胜率':>8} {'净期望':>10} {'Train':>8} {'Val':>8} {'Test':>8}")
    print("-" * 105)
    
    for name, d in baseline_data.items():
        print(f"{name:<15} {d['setup']:>8} {d['unique']:>8} "
              f"{d['br']:>7.1f}% {d['wr']:>7.1f}% {d['net_exp']:>9.3f}% "
              f"{d['train']:>7.3f}% {d['val']:>7.3f}% {d['test']:>7.3f}%")
    
    # v5结果
    if "v5-5bar" in all_results:
        r = all_results["v5-5bar"]
        print(f"{'v5_组合(B1+A1)':<15} {r.total_setups:>8} {r.unique_breakouts:>8} "
              f"{r.breakout_rate*100:>7.1f}% {r.net_win_rate_5bar*100:>7.1f}% "
              f"{r.net_expectancy_5bar:>9.3f}% "
              f"{r.train_metrics['expectancy']:>7.3f}% "
              f"{r.validation_metrics['expectancy']:>7.3f}% "
              f"{r.test_metrics['expectancy']:>7.3f}%")
    
    print("\n" + "="*100)
    print("  v5 全部执行完成")
    print("="*100)
    
    # 最终建议
    print("\n--- 最终建议 ---")
    
    if "v5-5bar" in all_results:
        r = all_results["v5-5bar"]
        test_exp = r.test_metrics.get('expectancy', 0)
        test_count = r.test_metrics.get('count', 0)
        
        print(f"\n  v5组合 (B1+A1): {r.unique_breakouts}个唯一突破, "
              f"净期望{r.net_expectancy_5bar:.3f}%, Test段{test_exp:.3f}%")
        
        if test_exp > 0 and test_count >= 30:
            print("  -> Test段净期望为正, 建议进入模拟盘观察")
        elif test_count < 30:
            print(f"  -> Test段仅{test_count}个样本, 统计判断力不足")
            print("  -> 建议: 保持当前参数, 等待实盘时间推进自然积累更多样本")
            print("  -> 或: 寻找更长的历史数据(如1095天/3年)")
        else:
            print("  -> Test段净期望为负, 暂不进入模拟盘")


def _generate_exit_rule_report(research, comparison, total_unique):
    """生成出场规则对比报告"""
    from pathlib import Path
    
    output_dir = Path("reports/squeeze")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    lines = []
    lines.append("# 出厂规则对比研究报告 v5")
    lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"\n总唯一突破事件: {total_unique}")
    
    # 总览对比
    lines.append("\n## 对比总览\n")
    lines.append("| 出场规则 | 交易数 | 胜率 | 净期望 | 平均Bar | Train | Val | Test |")
    lines.append("|----------|--------|------|--------|---------|-------|-----|------|")
    
    for rule_name, rule_data in comparison.items():
        lines.append(f"| {rule_name} | {rule_data['trades']} | "
                    f"{rule_data['win_rate']*100:.1f}% | "
                    f"{rule_data['net_expectancy']:.3f}% | "
                    f"{rule_data['avg_bars']:.1f} | "
                    f"{rule_data['train_metrics']['expectancy']:.3f}% | "
                    f"{rule_data['validation_metrics']['expectancy']:.3f}% | "
                    f"{rule_data['test_metrics']['expectancy']:.3f}% |")
    
    # 详细分析
    for rule_name, rule_data in comparison.items():
        lines.append(f"\n## {rule_name}\n")
        lines.append(f"- 交易数: {rule_data['trades']}")
        lines.append(f"- 胜率: {rule_data['win_rate']*100:.1f}%")
        lines.append(f"- 净期望: {rule_data['net_expectancy']:.3f}%")
        lines.append(f"- 平均持仓: {rule_data['avg_bars']:.1f}根K线")
        lines.append(f"- 平均MFE: {rule_data['avg_mfe']:.3f}%")
        lines.append(f"- 平均MAE: {rule_data['avg_mae']:.3f}%")
        
        # Walk-Forward
        lines.append(f"\n### Walk-Forward")
        lines.append("| 分区 | 交易数 | 胜率 | 净期望 |")
        lines.append("|------|--------|------|--------|")
        for fold in ["train_metrics", "validation_metrics", "test_metrics"]:
            m = rule_data[fold]
            lines.append(f"| {fold.replace('_metrics','')} | {m['count']} | "
                        f"{m['win_rate']*100:.1f}% | {m['expectancy']:.3f}% |")
    
    # 结论
    lines.append("\n## 结论\n")
    best_rule = max(comparison.items(), key=lambda x: x[1]['net_expectancy'])
    lines.append(f"- 最佳出场规则: **{best_rule[0]}** (净期望 {best_rule[1]['net_expectancy']:.3f}%)")
    
    # 检查Test段
    for rule_name, rule_data in comparison.items():
        test_exp = rule_data['test_metrics']['expectancy']
        test_cnt = rule_data['test_metrics']['count']
        if test_exp > 0 and test_cnt >= 30:
            lines.append(f"- {rule_name} Test段净期望为正(+{test_exp:.3f}%, n={test_cnt}), 可用于模拟盘")
    
    lines.append("\n---\n")
    lines.append("> **免责声明**: 本报告仅供研究参考, 不构成投资建议。")
    
    report_path = output_dir / f"squeeze_mt_exit_rule_comparison_v5_{timestamp}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  出场规则对比报告已生成: {report_path}")


if __name__ == "__main__":
    main()
