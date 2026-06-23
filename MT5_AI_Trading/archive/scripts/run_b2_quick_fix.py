"""快速重跑v5 B2出场规则对比 (数据复用已有)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from squeeze_multi_timeframe_research_v5 import (
    MultiTimeframeSqueezeResearchV5, SYMBOL_MAP, SYMBOL_WHITELIST_V5
)
from squeeze_multi_timeframe_research_v4 import SYMBOL_WHITELIST

orig = SYMBOL_WHITELIST.copy()
SYMBOL_WHITELIST.clear()
SYMBOL_WHITELIST.update(SYMBOL_WHITELIST_V5)

research = MultiTimeframeSqueezeResearchV5()
data = research.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=730)

if data:
    research.find_setups(
        min_squeeze_score=2, cooldown_bars=5, require_structural=False,
        use_whitelist=True, max_adx=12.0, min_anchor_range_pct=0.4
    )
    research.detect_breakouts(
        max_wait_bars=30, min_breakout_anchor_multiple=0.1,
        require_1bar_confirmation=True
    )
    
    unique_events = research._deduplicate_breakouts(research.breakouts)
    
    print(f"\n唯一突破事件: {len(unique_events)}")
    print(f"\n{'='*100}")
    print(f"  出场规则对比 (v5修正版, 前缀匹配)")
    print(f"{'='*100}")
    print(f"{'规则':<25} {'交易数':>8} {'胜率':>8} {'净期望':>10} {'平均Bar':>8} {'Train':>8} {'Val':>8} {'Test':>8}")
    print("-" * 100)
    
    for rule_name in ["fixed_hold_5bar", "structure_stop", "1r_partial"]:
        research.trades = research._simulate_exit_rule(unique_events, rule_name)
        result = research.analyze(deduplicate=False, exit_rule_filter=rule_name)
        
        if result:
            # 统计该规则的交易
            rule_trades = [t for t in research.trades 
                          if t.exit_rule == rule_name 
                          or t.exit_rule.startswith(rule_name + "_")]
            
            # 细分统计
            exit_types = {}
            for t in rule_trades:
                et = t.exit_rule
                exit_types[et] = exit_types.get(et, 0) + 1
            
            avg_bars = sum(t.bars_held for t in rule_trades) / len(rule_trades) if rule_trades else 0
            
            print(f"{rule_name:<25} "
                  f"{len(rule_trades):>8} "
                  f"{result.net_win_rate_5bar*100:>7.1f}% "
                  f"{result.net_expectancy_5bar:>9.3f}% "
                  f"{avg_bars:>7.1f} "
                  f"{result.train_metrics['expectancy']:>7.3f}% "
                  f"{result.validation_metrics['expectancy']:>7.3f}% "
                  f"{result.test_metrics['expectancy']:>7.3f}%")
            
            print(f"  子类型: {exit_types}")
            
            # Test段详情
            if result.test_metrics['count'] > 0:
                print(f"  Test段: {result.test_metrics['count']}笔, "
                      f"胜率{result.test_metrics['win_rate']*100:.1f}%, "
                      f"期望{result.test_metrics['expectancy']:.3f}%")

SYMBOL_WHITELIST.clear()
SYMBOL_WHITELIST.update(orig)
