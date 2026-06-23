"""
v5 参数敏感性分析
扫描 max_adx × min_anchor_range_pct × cooldown_bars 参数空间

扫描范围(轻量级,围绕baseline±1步进):
- max_adx: 10, 11, 12(baseline), 13, 14
- min_anchor_range_pct: 0.35, 0.40, 0.45(baseline), 0.50
- cooldown_bars: 3, 5(baseline), 7

输出: 参数敏感性报告 + 最优参数组合推荐
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from squeeze_multi_timeframe_research_v5 import (
    MultiTimeframeSqueezeResearchV5, SYMBOL_MAP, SYMBOL_WHITELIST_V5
)
from squeeze_multi_timeframe_research_v4 import SYMBOL_WHITELIST
from datetime import datetime
import json


def run_sensitivity_scan():
    print("="*100)
    print("  v5 参数敏感性分析")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*100)
    
    # 参数扫描范围
    max_adx_values = [10, 11, 12, 13, 14]
    min_range_values = [0.35, 0.40, 0.45, 0.50]
    cooldown_values = [3, 5, 7]
    
    total_combinations = len(max_adx_values) * len(min_range_values) * len(cooldown_values)
    print(f"\n总组合数: {total_combinations}")
    print(f"max_adx: {max_adx_values}")
    print(f"min_range: {min_range_values}")
    print(f"cooldown: {cooldown_values}")
    print("="*100)
    
    # 先获取数据(只获取一次)
    print("\n[1/2] 获取数据(730天, 14品种)...")
    research = MultiTimeframeSqueezeResearchV5()
    
    orig_whitelist = SYMBOL_WHITELIST.copy()
    SYMBOL_WHITELIST.clear()
    SYMBOL_WHITELIST.update(SYMBOL_WHITELIST_V5)
    
    try:
        data = research.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=730)
        if not data:
            print("错误: 未能获取数据")
            return
        print(f"  数据获取完成: {len(data)}个品种")
    except Exception as e:
        print(f"数据获取失败: {e}")
        return
    
    # 扫描所有参数组合
    print("\n[2/2] 扫描参数组合...")
    results = []
    best_test_exp = -999
    best_params = None
    best_result = None
    
    for i, max_adx in enumerate(max_adx_values):
        for j, min_range in enumerate(min_range_values):
            for k, cooldown in enumerate(cooldown_values):
                combo_idx = i * len(min_range_values) * len(cooldown_values) + j * len(cooldown_values) + k + 1
                print(f"\n  [{combo_idx}/{total_combinations}] max_adx={max_adx}, min_range={min_range:.2f}%, cooldown={cooldown}")
                
                # 创建新的research实例(共享数据)
                r = MultiTimeframeSqueezeResearchV5()
                r.raw_data = data
                
                try:
                    r.find_setups(
                        min_squeeze_score=2,
                        cooldown_bars=cooldown,
                        require_structural=False,
                        use_whitelist=True,
                        max_adx=max_adx,
                        min_anchor_range_pct=min_range
                    )
                    
                    r.detect_breakouts(
                        max_wait_bars=30,
                        min_breakout_anchor_multiple=0.1,
                        require_1bar_confirmation=True
                    )
                    
                    unique_events = r._deduplicate_breakouts(r.breakouts)
                    
                    if len(unique_events) < 20:
                        print(f"    样本不足({len(unique_events)}), 跳过")
                        results.append({
                            "max_adx": max_adx,
                            "min_range": min_range,
                            "cooldown": cooldown,
                            "setups": len(r.setups),
                            "unique": len(unique_events),
                            "skipped": True
                        })
                        continue
                    
                    # 模拟交易(fixed_hold_5bar)
                    r.trades = r._simulate_exit_rule(unique_events, "fixed_hold_5bar")
                    result = r.analyze(deduplicate=False, exit_rule_filter="fixed_hold_5bar")
                    
                    if result:
                        test_exp = result.test_metrics.get('expectancy', 0)
                        test_count = result.test_metrics.get('count', 0)
                        
                        print(f"    Setup: {result.total_setups}, 唯一突破: {result.unique_breakouts}")
                        print(f"    净胜率: {result.net_win_rate_5bar*100:.1f}%, 净期望: {result.net_expectancy_5bar:.3f}%")
                        print(f"    Train: {result.train_metrics['expectancy']:.3f}%, Val: {result.validation_metrics['expectancy']:.3f}%, Test: {test_exp:.3f}% (n={test_count})")
                        
                        row = {
                            "max_adx": max_adx,
                            "min_range": min_range,
                            "cooldown": cooldown,
                            "setups": result.total_setups,
                            "unique": result.unique_breakouts,
                            "breakout_rate": result.breakout_rate,
                            "net_win_rate": result.net_win_rate_5bar,
                            "net_expectancy": result.net_expectancy_5bar,
                            "train_exp": result.train_metrics['expectancy'],
                            "val_exp": result.validation_metrics['expectancy'],
                            "test_exp": test_exp,
                            "test_count": test_count,
                            "skipped": False
                        }
                        results.append(row)
                        
                        # 记录最优(Test段期望最高且样本>=20)
                        if test_count >= 20 and test_exp > best_test_exp:
                            best_test_exp = test_exp
                            best_params = (max_adx, min_range, cooldown)
                            best_result = result
                    else:
                        print(f"    分析失败")
                        results.append({
                            "max_adx": max_adx,
                            "min_range": min_range,
                            "cooldown": cooldown,
                            "skipped": True
                        })
                        
                except Exception as e:
                    print(f"    错误: {e}")
                    results.append({
                        "max_adx": max_adx,
                        "min_range": min_range,
                        "cooldown": cooldown,
                        "skipped": True,
                        "error": str(e)
                    })
    
    # 恢复白名单
    SYMBOL_WHITELIST.clear()
    SYMBOL_WHITELIST.update(orig_whitelist)
    
    # 生成报告
    _generate_sensitivity_report(results, best_params, best_result, total_combinations)
    
    print("\n" + "="*100)
    print("  参数敏感性分析完成")
    print("="*100)
    
    if best_params:
        print(f"\n  最优参数组合(按Test段期望):")
        print(f"    max_adx={best_params[0]}, min_range={best_params[1]:.2f}%, cooldown={best_params[2]}")
        print(f"    Test段期望: {best_test_exp:.3f}%")
    
    return results, best_params


def _generate_sensitivity_report(results, best_params, best_result, total):
    """生成敏感性分析报告"""
    output_dir = Path("reports/squeeze")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    lines = []
    lines.append("# v5 参数敏感性分析报告")
    lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"\n扫描范围: {total}个参数组合")
    
    # 参数范围
    lines.append("\n## 参数范围")
    lines.append("- max_adx: 10, 11, 12(baseline), 13, 14")
    lines.append("- min_anchor_range_pct: 0.35, 0.40, 0.45(baseline), 0.50")
    lines.append("- cooldown_bars: 3, 5(baseline), 7")
    
    # 完整结果表
    lines.append("\n## 完整结果")
    lines.append("| max_adx | min_range | cooldown | Setup | 唯一突破 | 突破率 | 净胜率 | 净期望 | Train | Val | Test | Test_n |")
    lines.append("|---------|-----------|----------|-------|----------|--------|--------|--------|-------|-----|------|--------|")
    
    for r in results:
        if r.get("skipped"):
            lines.append(f"| {r['max_adx']} | {r['min_range']:.2f} | {r['cooldown']} | - | - | - | - | - | - | - | - | - |")
        else:
            lines.append(
                f"| {r['max_adx']} | {r['min_range']:.2f} | {r['cooldown']} | "
                f"{r['setups']} | {r['unique']} | {r['breakout_rate']*100:.1f}% | "
                f"{r['net_win_rate']*100:.1f}% | {r['net_expectancy']:.3f}% | "
                f"{r['train_exp']:.3f}% | {r['val_exp']:.3f}% | {r['test_exp']:.3f}% | {r['test_count']} |"
            )
    
    # 最优参数
    if best_params:
        lines.append("\n## 最优参数组合")
        lines.append(f"- max_adx: **{best_params[0]}** (baseline=12)")
        lines.append(f"- min_range: **{best_params[1]:.2f}%** (baseline=0.45%)")
        lines.append(f"- cooldown: **{best_params[2]}** (baseline=5)")
        lines.append(f"- Test段期望: **{best_result.test_metrics['expectancy']:.3f}%**")
        lines.append(f"- Test段样本: **{best_result.test_metrics['count']}**")
        
        # 与baseline对比
        baseline = next((r for r in results if r['max_adx']==12 and r['min_range']==0.45 and r['cooldown']==5 and not r.get('skipped')), None)
        if baseline:
            lines.append("\n### 与baseline(12, 0.45, 5)对比")
            lines.append(f"| 指标 | Baseline | 最优 | 变化 |")
            lines.append(f"|------|----------|------|------|")
            lines.append(f"| Setup | {baseline['setups']} | {best_result.total_setups} | {best_result.total_setups - baseline['setups']:+d} |")
            lines.append(f"| 唯一突破 | {baseline['unique']} | {best_result.unique_breakouts} | {best_result.unique_breakouts - baseline['unique']:+d} |")
            lines.append(f"| 净胜率 | {baseline['net_win_rate']*100:.1f}% | {best_result.net_win_rate_5bar*100:.1f}% | {(best_result.net_win_rate_5bar - baseline['net_win_rate'])*100:+.1f}pp |")
            lines.append(f"| 净期望 | {baseline['net_expectancy']:.3f}% | {best_result.net_expectancy_5bar:.3f}% | {best_result.net_expectancy_5bar - baseline['net_expectancy']:+.3f}% |")
            lines.append(f"| Test期望 | {baseline['test_exp']:.3f}% | {best_result.test_metrics['expectancy']:.3f}% | {best_result.test_metrics['expectancy'] - baseline['test_exp']:+.3f}% |")
    
    # 参数敏感性观察
    lines.append("\n## 参数敏感性观察")
    
    # 按max_adx聚合
    lines.append("\n### max_adx影响")
    lines.append("| max_adx | 平均Setup | 平均唯一 | 平均净期望 | 平均Test期望 |")
    lines.append("|---------|-----------|----------|------------|--------------|")
    for max_adx in [10, 11, 12, 13, 14]:
        subset = [r for r in results if r['max_adx'] == max_adx and not r.get('skipped')]
        if subset:
            avg_setups = sum(r['setups'] for r in subset) / len(subset)
            avg_unique = sum(r['unique'] for r in subset) / len(subset)
            avg_exp = sum(r['net_expectancy'] for r in subset) / len(subset)
            avg_test = sum(r['test_exp'] for r in subset) / len(subset)
            lines.append(f"| {max_adx} | {avg_setups:.0f} | {avg_unique:.0f} | {avg_exp:.3f}% | {avg_test:.3f}% |")
    
    # 按min_range聚合
    lines.append("\n### min_range影响")
    lines.append("| min_range | 平均Setup | 平均唯一 | 平均净期望 | 平均Test期望 |")
    lines.append("|-----------|-----------|----------|------------|--------------|")
    for min_range in [0.35, 0.40, 0.45, 0.50]:
        subset = [r for r in results if abs(r['min_range'] - min_range) < 0.001 and not r.get('skipped')]
        if subset:
            avg_setups = sum(r['setups'] for r in subset) / len(subset)
            avg_unique = sum(r['unique'] for r in subset) / len(subset)
            avg_exp = sum(r['net_expectancy'] for r in subset) / len(subset)
            avg_test = sum(r['test_exp'] for r in subset) / len(subset)
            lines.append(f"| {min_range:.2f}% | {avg_setups:.0f} | {avg_unique:.0f} | {avg_exp:.3f}% | {avg_test:.3f}% |")
    
    # 按cooldown聚合
    lines.append("\n### cooldown影响")
    lines.append("| cooldown | 平均Setup | 平均唯一 | 平均净期望 | 平均Test期望 |")
    lines.append("|----------|-----------|----------|------------|--------------|")
    for cooldown in [3, 5, 7]:
        subset = [r for r in results if r['cooldown'] == cooldown and not r.get('skipped')]
        if subset:
            avg_setups = sum(r['setups'] for r in subset) / len(subset)
            avg_unique = sum(r['unique'] for r in subset) / len(subset)
            avg_exp = sum(r['net_expectancy'] for r in subset) / len(subset)
            avg_test = sum(r['test_exp'] for r in subset) / len(subset)
            lines.append(f"| {cooldown} | {avg_setups:.0f} | {avg_unique:.0f} | {avg_exp:.3f}% | {avg_test:.3f}% |")
    
    lines.append("\n---")
    lines.append("> **免责声明**: 本报告仅供研究参考, 不构成投资建议。")
    
    report_path = output_dir / f"squeeze_mt_sensitivity_v5_{timestamp}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  敏感性报告已生成: {report_path}")
    
    # 同时保存JSON
    json_path = output_dir / f"squeeze_mt_sensitivity_v5_{timestamp}.json"
    json_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"  JSON数据已保存: {json_path}")


if __name__ == "__main__":
    run_sensitivity_scan()
