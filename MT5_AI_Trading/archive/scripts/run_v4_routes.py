"""
v4 四条路线并行执行脚本
路线B1: 移除USOIL+EURGBP
路线A1: 扩展数据窗口到730天
路线A2: 微调参数(max_adx 12→15, min_range 0.4%→0.3%)
路线B2: 出场规则优化对比
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from squeeze_multi_timeframe_research_v4 import (
    MultiTimeframeSqueezeResearchV4, SYMBOL_MAP, SYMBOL_WHITELIST, get_symbol_cost
)
from datetime import datetime


def run_route_b1():
    """路线B1: 移除USOIL+EURGBP"""
    print("\n" + "="*70)
    print("路线B1: 移除USOIL+EURGBP")
    print("="*70)
    
    whitelist_b1 = SYMBOL_WHITELIST - {"USOIL", "EURGBP"}
    
    research = MultiTimeframeSqueezeResearchV4()
    data = research.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=365)
    
    if not data:
        print("错误: 未能获取数据")
        return None
    
    # 临时修改白名单
    original_whitelist = SYMBOL_WHITELIST.copy()
    SYMBOL_WHITELIST.clear()
    SYMBOL_WHITELIST.update(whitelist_b1)
    
    try:
        research.find_setups(
            min_squeeze_score=2, cooldown_bars=5, require_structural=False,
            use_whitelist=True, max_adx=12.0, min_anchor_range_pct=0.4
        )
        
        research.detect_breakouts(
            max_wait_bars=30, min_breakout_anchor_multiple=0.1,
            require_1bar_confirmation=True
        )
        
        unique_events = research._deduplicate_breakouts(research.breakouts)
        research.run_trade_backtest(unique_events)
        result = research.analyze(deduplicate=True)
        
        if result:
            print(f"\nB1结果:")
            print(f"  Setup: {result.total_setups}, 突破: {result.total_breakouts}, 唯一: {result.unique_breakouts}")
            print(f"  突破率: {result.breakout_rate*100:.1f}%")
            print(f"  5bar胜率(唯一): {result.unique_win_rate_5bar*100:.1f}%")
            print(f"  净期望: {result.net_expectancy_5bar:.3f}%")
            print(f"  Walk-Forward Train/Val/Test: {result.train_metrics['expectancy']:.3f}% / {result.validation_metrics['expectancy']:.3f}% / {result.test_metrics['expectancy']:.3f}%")
    finally:
        SYMBOL_WHITELIST.clear()
        SYMBOL_WHITELIST.update(original_whitelist)
    
    return result


def run_route_a1():
    """路线A1: 扩展数据窗口到730天"""
    print("\n" + "="*70)
    print("路线A1: 扩展数据窗口到730天")
    print("="*70)
    
    research = MultiTimeframeSqueezeResearchV4()
    data = research.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=730)
    
    if not data:
        print("错误: 未能获取数据")
        return None
    
    research.find_setups(
        min_squeeze_score=2, cooldown_bars=5, require_structural=False,
        use_whitelist=True, max_adx=12.0, min_anchor_range_pct=0.4
    )
    
    research.detect_breakouts(
        max_wait_bars=30, min_breakout_anchor_multiple=0.1,
        require_1bar_confirmation=True
    )
    
    unique_events = research._deduplicate_breakouts(research.breakouts)
    research.run_trade_backtest(unique_events)
    result = research.analyze(deduplicate=True)
    
    if result:
        print(f"\nA1结果:")
        print(f"  Setup: {result.total_setups}, 突破: {result.total_breakouts}, 唯一: {result.unique_breakouts}")
        print(f"  突破率: {result.breakout_rate*100:.1f}%")
        print(f"  5bar胜率(唯一): {result.unique_win_rate_5bar*100:.1f}%")
        print(f"  净期望: {result.net_expectancy_5bar:.3f}%")
        print(f"  Walk-Forward Train/Val/Test: {result.train_metrics['expectancy']:.3f}% / {result.validation_metrics['expectancy']:.3f}% / {result.test_metrics['expectancy']:.3f}%")
    
    return result


def run_route_a2():
    """路线A2: 微调参数"""
    print("\n" + "="*70)
    print("路线A2: 微调参数 (max_adx=15, min_range=0.3%)")
    print("="*70)
    
    research = MultiTimeframeSqueezeResearchV4()
    data = research.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=365)
    
    if not data:
        print("错误: 未能获取数据")
        return None
    
    research.find_setups(
        min_squeeze_score=2, cooldown_bars=5, require_structural=False,
        use_whitelist=True, max_adx=15.0, min_anchor_range_pct=0.3
    )
    
    research.detect_breakouts(
        max_wait_bars=30, min_breakout_anchor_multiple=0.1,
        require_1bar_confirmation=True
    )
    
    unique_events = research._deduplicate_breakouts(research.breakouts)
    research.run_trade_backtest(unique_events)
    result = research.analyze(deduplicate=True)
    
    if result:
        print(f"\nA2结果:")
        print(f"  Setup: {result.total_setups}, 突破: {result.total_breakouts}, 唯一: {result.unique_breakouts}")
        print(f"  突破率: {result.breakout_rate*100:.1f}%")
        print(f"  5bar胜率(唯一): {result.unique_win_rate_5bar*100:.1f}%")
        print(f"  净期望: {result.net_expectancy_5bar:.3f}%")
        print(f"  Walk-Forward Train/Val/Test: {result.train_metrics['expectancy']:.3f}% / {result.validation_metrics['expectancy']:.3f}% / {result.test_metrics['expectancy']:.3f}%")
    
    return result


def run_route_b2():
    """路线B2: 出场规则优化对比"""
    print("\n" + "="*70)
    print("路线B2: 出场规则优化对比")
    print("="*70)
    
    results = {}
    
    # B2-1: structure_stop (以anchor对边止损)
    print("\n--- B2-1: Structure Stop (anchor对边止损) ---")
    research = MultiTimeframeSqueezeResearchV4()
    data = research.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=365)
    
    if not data:
        return None
    
    research.find_setups(
        min_squeeze_score=2, cooldown_bars=5, require_structural=False,
        use_whitelist=True, max_adx=12.0, min_anchor_range_pct=0.4
    )
    
    research.detect_breakouts(
        max_wait_bars=30, min_breakout_anchor_multiple=0.1,
        require_1bar_confirmation=True
    )
    
    unique_events = research._deduplicate_breakouts(research.breakouts)
    
    # 使用structure_stop回测
    trades = []
    for evt in unique_events:
        symbol = evt.setup.symbol
        h1_df = research.raw_data.get(symbol, {}).get("H1")
        if h1_df is None:
            continue
        
        entry_idx = h1_df[h1_df['timestamp'] == evt.breakout_timestamp].index
        if len(entry_idx) == 0:
            continue
        entry_idx = entry_idx[0]
        
        entry_price = evt.entry_price
        direction = evt.breakout_direction
        
        # Structure stop: anchor对边
        stop_price = evt.setup.anchor_low if direction == "up" else evt.setup.anchor_high
        if stop_price is None:
            continue
        
        exit_price = None
        exit_time = None
        exit_rule = "structure_stop"
        bars_held = 0
        mfe = 0.0
        mae = 0.0
        
        for j in range(entry_idx + 1, min(entry_idx + 31, len(h1_df))):
            bar = h1_df.iloc[j]
            bars_held += 1
            
            if direction == "up":
                mfe = max(mfe, (bar['high'] - entry_price) / entry_price * 100)
                mae = min(mae, (bar['low'] - entry_price) / entry_price * 100)
                if bar['low'] <= stop_price:
                    exit_price = stop_price
                    exit_time = bar['timestamp']
                    exit_rule = "structure_stop"
                    break
            else:
                mfe = max(mfe, (entry_price - bar['low']) / entry_price * 100)
                mae = min(mae, (entry_price - bar['high']) / entry_price * 100)
                if bar['high'] >= stop_price:
                    exit_price = stop_price
                    exit_time = bar['timestamp']
                    exit_rule = "structure_stop"
                    break
        
        if exit_price is None:
            last_bar = h1_df.iloc[min(entry_idx + 30, len(h1_df) - 1)]
            exit_price = last_bar['close']
            exit_time = last_bar['timestamp']
            exit_rule = "time_exit_30bar"
            bars_held = min(30, len(h1_df) - entry_idx - 1)
        
        if direction == "up":
            gross_pnl = (exit_price - entry_price) / entry_price * 100
        else:
            gross_pnl = (entry_price - exit_price) / entry_price * 100
        
        cost = get_symbol_cost(symbol)
        total_cost = cost['spread_pct'] + cost['commission_pct']
        net_pnl = gross_pnl - total_cost
        
        from squeeze_multi_timeframe_research_v3 import Trade
        trade = Trade(
            trade_id=f"tr_{evt.event_id}", event_id=evt.event_id,
            symbol=symbol, direction=direction,
            entry_time=evt.breakout_timestamp, entry_price=entry_price,
            exit_time=exit_time, exit_price=exit_price, exit_rule=exit_rule,
            gross_pnl_pct=gross_pnl, cost_pct=cost, net_pnl_pct=net_pnl,
            mfe_pct=mfe, mae_pct=mae, bars_held=bars_held, fold="train"
        )
        trades.append(trade)
    
    research.trades = trades
    result = research.analyze(deduplicate=True)
    if result:
        print(f"  Setup: {result.total_setups}, 唯一突破: {result.unique_breakouts}")
        print(f"  净胜率: {result.net_win_rate_5bar*100:.1f}%, 净期望: {result.net_expectancy_5bar:.3f}%")
        results['structure_stop'] = result
    
    # B2-2: 1R_partial (1R减仓50% + 剩余trailing)
    print("\n--- B2-2: 1R Partial (1R减仓50% + trailing剩余) ---")
    research2 = MultiTimeframeSqueezeResearchV4()
    data = research2.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=365)
    
    if not data:
        return None
    
    research2.find_setups(
        min_squeeze_score=2, cooldown_bars=5, require_structural=False,
        use_whitelist=True, max_adx=12.0, min_anchor_range_pct=0.4
    )
    
    research2.detect_breakouts(
        max_wait_bars=30, min_breakout_anchor_multiple=0.1,
        require_1bar_confirmation=True
    )
    
    unique_events2 = research2._deduplicate_breakouts(research2.breakouts)
    
    trades2 = []
    for evt in unique_events2:
        symbol = evt.setup.symbol
        h1_df = research2.raw_data.get(symbol, {}).get("H1")
        if h1_df is None:
            continue
        
        entry_idx = h1_df[h1_df['timestamp'] == evt.breakout_timestamp].index
        if len(entry_idx) == 0:
            continue
        entry_idx = entry_idx[0]
        
        entry_price = evt.entry_price
        direction = evt.breakout_direction
        
        # 1R距离
        stop_price = evt.setup.anchor_low if direction == "up" else evt.setup.anchor_high
        if stop_price is None:
            continue
        
        risk = abs(entry_price - stop_price) / entry_price * 100
        if risk <= 0:
            continue
        
        target_1r = entry_price + (entry_price * risk / 100) if direction == "up" else entry_price - (entry_price * risk / 100)
        
        exit_price = None
        exit_time = None
        exit_rule = "time_exit"
        bars_held = 0
        mfe = 0.0
        mae = 0.0
        partial_done = False
        trailing_stop = stop_price
        
        for j in range(entry_idx + 1, min(entry_idx + 31, len(h1_df))):
            bar = h1_df.iloc[j]
            bars_held += 1
            
            if direction == "up":
                mfe = max(mfe, (bar['high'] - entry_price) / entry_price * 100)
                mae = min(mae, (bar['low'] - entry_price) / entry_price * 100)
                
                if not partial_done and bar['high'] >= target_1r:
                    # 1R减仓50%，剩余移到breakeven
                    partial_done = True
                    trailing_stop = entry_price
                
                if partial_done and bar['low'] <= trailing_stop:
                    exit_price = trailing_stop
                    exit_time = bar['timestamp']
                    exit_rule = "trailing_stop"
                    break
                
                if not partial_done and bar['low'] <= stop_price:
                    exit_price = stop_price
                    exit_time = bar['timestamp']
                    exit_rule = "full_stop"
                    break
            else:
                mfe = max(mfe, (entry_price - bar['low']) / entry_price * 100)
                mae = min(mae, (entry_price - bar['high']) / entry_price * 100)
                
                if not partial_done and bar['low'] <= target_1r:
                    partial_done = True
                    trailing_stop = entry_price
                
                if partial_done and bar['high'] >= trailing_stop:
                    exit_price = trailing_stop
                    exit_time = bar['timestamp']
                    exit_rule = "trailing_stop"
                    break
                
                if not partial_done and bar['high'] >= stop_price:
                    exit_price = stop_price
                    exit_time = bar['timestamp']
                    exit_rule = "full_stop"
                    break
        
        if exit_price is None:
            last_bar = h1_df.iloc[min(entry_idx + 30, len(h1_df) - 1)]
            exit_price = last_bar['close']
            exit_time = last_bar['timestamp']
            exit_rule = "time_exit_30bar"
            bars_held = min(30, len(h1_df) - entry_idx - 1)
        
        # 简化: 假设50%仓位在1R平仓，剩余50%在最终出场价平仓
        if partial_done:
            if direction == "up":
                gross_pnl = 0.5 * risk + 0.5 * (exit_price - entry_price) / entry_price * 100
            else:
                gross_pnl = 0.5 * risk + 0.5 * (entry_price - exit_price) / entry_price * 100
        else:
            if direction == "up":
                gross_pnl = (exit_price - entry_price) / entry_price * 100
            else:
                gross_pnl = (entry_price - exit_price) / entry_price * 100
        
        cost = get_symbol_cost(symbol)
        total_cost = cost['spread_pct'] + cost['commission_pct']
        net_pnl = gross_pnl - total_cost
        
        from squeeze_multi_timeframe_research_v3 import Trade
        trade = Trade(
            trade_id=f"tr_{evt.event_id}", event_id=evt.event_id,
            symbol=symbol, direction=direction,
            entry_time=evt.breakout_timestamp, entry_price=entry_price,
            exit_time=exit_time, exit_price=exit_price, exit_rule=exit_rule,
            gross_pnl_pct=gross_pnl, cost_pct=cost, net_pnl_pct=net_pnl,
            mfe_pct=mfe, mae_pct=mae, bars_held=bars_held, fold="train"
        )
        trades2.append(trade)
    
    research2.trades = trades2
    result2 = research2.analyze(deduplicate=True)
    if result2:
        print(f"  Setup: {result2.total_setups}, 唯一突破: {result2.unique_breakouts}")
        print(f"  净胜率: {result2.net_win_rate_5bar*100:.1f}%, 净期望: {result2.net_expectancy_5bar:.3f}%")
        results['1r_partial'] = result2
    
    return results


def main():
    print("="*70)
    print("v4 四条路线并行执行")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    all_results = {}
    
    # 路线B1
    all_results['B1'] = run_route_b1()
    
    # 路线A1
    all_results['A1'] = run_route_a1()
    
    # 路线A2
    all_results['A2'] = run_route_a2()
    
    # 路线B2
    all_results['B2'] = run_route_b2()
    
    # 汇总
    print("\n" + "="*70)
    print("四条路线汇总对比")
    print("="*70)
    
    baseline = {
        'setup': 573, 'unique': 160, 'breakout_rate': 27.9,
        'win_rate': 58.8, 'net_exp': 0.227,
        'train': 0.289, 'val': 0.314, 'test': -0.107
    }
    
    print(f"\n{'路线':<12} {'Setup':>8} {'唯一':>8} {'突破率':>8} {'胜率':>8} {'净期望':>10} {'Train':>8} {'Val':>8} {'Test':>8}")
    print("-" * 90)
    print(f"{'Baseline':<12} {baseline['setup']:>8} {baseline['unique']:>8} {baseline['breakout_rate']:>7.1f}% {baseline['win_rate']:>7.1f}% {baseline['net_exp']:>9.3f}% {baseline['train']:>7.3f}% {baseline['val']:>7.3f}% {baseline['test']:>7.3f}%")
    
    for route, result in all_results.items():
        if result is None:
            print(f"{route:<12} {'失败':>8}")
            continue
        if route == 'B2':
            for sub, sub_res in result.items():
                if sub_res:
                    print(f"{'B2-'+sub:<12} {sub_res.total_setups:>8} {sub_res.unique_breakouts:>8} {sub_res.breakout_rate*100:>7.1f}% {sub_res.net_win_rate_5bar*100:>7.1f}% {sub_res.net_expectancy_5bar:>9.3f}% {sub_res.train_metrics['expectancy']:>7.3f}% {sub_res.validation_metrics['expectancy']:>7.3f}% {sub_res.test_metrics['expectancy']:>7.3f}%")
        else:
            print(f"{route:<12} {result.total_setups:>8} {result.unique_breakouts:>8} {result.breakout_rate*100:>7.1f}% {result.net_win_rate_5bar*100:>7.1f}% {result.net_expectancy_5bar:>9.3f}% {result.train_metrics['expectancy']:>7.3f}% {result.validation_metrics['expectancy']:>7.3f}% {result.test_metrics['expectancy']:>7.3f}%")
    
    print("\n" + "="*70)
    print("全部路线执行完成")
    print("="*70)


if __name__ == "__main__":
    main()
