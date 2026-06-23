"""
D1/H1/M15 收缩信号观察报警统计报告
汇总三个交易周期Agent的收缩状态，生成报警统计
"""

import duckdb
from datetime import datetime
import sys
sys.path.insert(0, '.')
from python.ai_engine.contraction_agents import (
    MultiTimeframeContractionSystem, ContractionObservation
)


def generate_contraction_alert_report(db_path: str = 'data/h1_state.duckdb'):
    """生成收缩报警统计报告"""
    
    conn = duckdb.connect(db_path, read_only=True)
    
    # 获取最新状态
    rows = conn.execute('''
        SELECT symbol, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex
        FROM h1_state_snapshot s1
        WHERE timestamp = (
            SELECT MAX(timestamp) 
            FROM h1_state_snapshot s2 
            WHERE s2.symbol = s1.symbol
        )
        ORDER BY symbol
    ''').fetchall()
    
    conn.close()
    
    # 优先品种
    priority_symbols = [
        'GER30', 'UK_100', 'US_30', 'US_500', 'US_TECH100', 'JP225', 'HK_50',
        'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF',
        'XAUUSD', 'USOIL', 'BRENT_OIL', 'SILVER', 'NATURAL_GAS', 'BTCUSD',
        'FRANCE_40', 'ITALY_40', 'SWISS_20', 'EUROPE_50', 'CHINA_A50', 'GERMANY_TECH30'
    ]
    
    # 初始化收缩系统
    system = MultiTimeframeContractionSystem(db_path)
    
    # 收集所有观察
    all_observations = []
    priority_obs = {}
    
    for row in rows:
        symbol = row[0]
        state = {
            'mn1_hex': row[1], 'w1_hex': row[2], 'd1_hex': row[3],
            'h4_hex': row[4], 'h1_hex': row[5]
        }
        obs = system.analyze_all(symbol, state)
        
        # 只保留收缩状态
        contracting = [o for o in obs if o.contraction_level > 0]
        if contracting:
            all_observations.extend(contracting)
            if symbol in priority_symbols:
                priority_obs[symbol] = contracting
    
    # 开始输出报告
    print("=" * 100)
    print("D1/H1/M15 收缩信号观察报警统计报告")
    print("=" * 100)
    print(f"统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"覆盖品种: {len(rows)} 个")
    print()
    
    # === 1. 各周期收缩统计 ===
    print("-" * 100)
    print("【一、各周期收缩统计】")
    print("-" * 100)
    
    for tf in ['D1', 'H1', 'M15']:
        tf_obs = [o for o in all_observations if o.timeframe == tf]
        
        # 按等级分组
        level_counts = {}
        for o in tf_obs:
            level_counts[o.contraction_level] = level_counts.get(o.contraction_level, 0) + 1
        
        print(f"\n{tf} Agent: 共 {len(tf_obs)} 个品种收缩")
        print(f"  等级1(早期C): {level_counts.get(1, 0)} 个")
        print(f"  等级2(发展D): {level_counts.get(2, 0)} 个")
        print(f"  等级3(成熟E): {level_counts.get(3, 0)} 个")
        print(f"  等级4(极端F): {level_counts.get(4, 0)} 个")
        
        # 显示该周期的关键品种
        critical = [o for o in tf_obs if o.alert_level in ['alert', 'critical']]
        if critical:
            print(f"  关键警报({len(critical)}个):")
            for o in sorted(critical, key=lambda x: -x.contraction_level):
                direction = "↓" if o.breakout_direction == 'down' else "↑"
                print(f"    {direction} {o.symbol:<15} {o.hex_value} 突破概率{o.breakout_probability:.0%}")
    
    # === 2. 跨周期同步收缩 ===
    print(f"\n{'-'*100}")
    print("【二、跨周期同步收缩（多周期联动）】")
    print(f"{'-'*100}")
    
    sync_symbols = {}
    for obs in all_observations:
        if obs.contraction_level >= 3 and obs.related_timeframes:
            if obs.symbol not in sync_symbols:
                sync_symbols[obs.symbol] = []
            sync_symbols[obs.symbol].append(obs)
    
    if sync_symbols:
        # 按同步周期数排序
        sorted_sync = sorted(sync_symbols.items(), 
                            key=lambda x: len(x[1]), 
                            reverse=True)
        
        for symbol, obs_list in sorted_sync:
            if symbol in priority_symbols or len(obs_list) >= 2:
                print(f"\n🔴 {symbol}")
                for o in sorted(obs_list, key=lambda x: x.timeframe):
                    sync_tf = ','.join(o.related_timeframes)
                    direction = "↓" if o.breakout_direction == 'down' else "↑"
                    print(f"   {direction} {o.timeframe}:{o.hex_value} "
                          f"等级{o.contraction_level} 突破概率{o.breakout_probability:.0%} "
                          f"[同步:{sync_tf}]")
    else:
        print("\n暂无跨周期同步收缩")
    
    # === 3. 优先品种收缩状态 ===
    print(f"\n{'-'*100}")
    print("【三、优先品种收缩状态速览】")
    print(f"{'-'*100}")
    
    print(f"\n{'品种':<15} | {'D1':>4} | {'H1':>4} | {'M15':>4} | {'最高等级':>6} | {'警报':>6}")
    print("-" * 60)
    
    for sym in priority_symbols:
        if sym in priority_obs:
            obs = priority_obs[sym]
            d1 = next((o.hex_value for o in obs if o.timeframe == 'D1'), '-')
            h1 = next((o.hex_value for o in obs if o.timeframe == 'H1'), '-')
            m15 = next((o.hex_value for o in obs if o.timeframe == 'M15'), '-')
            max_level = max(o.contraction_level for o in obs)
            
            alerts = [o.alert_level for o in obs if o.alert_level in ['alert', 'critical']]
            alert_str = '🔴' if 'critical' in alerts else '▲' if 'alert' in alerts else '△' if alerts else '○'
            
            print(f"{sym:<15} | {d1:>4} | {h1:>4} | {m15:>4} | {max_level:>6} | {alert_str:>6}")
    
    # === 4. 突破方向统计 ===
    print(f"\n{'-'*100}")
    print("【四、突破方向统计】")
    print(f"{'-'*100}")
    
    up_count = len([o for o in all_observations if o.breakout_direction == 'up' and o.contraction_level >= 2])
    down_count = len([o for o in all_observations if o.breakout_direction == 'down' and o.contraction_level >= 2])
    
    print(f"\n向上突破预期: {up_count} 个品种")
    print(f"向下突破预期: {down_count} 个品种")
    
    if up_count > down_count * 1.5:
        print("📊 整体偏向: 多头突破占优")
    elif down_count > up_count * 1.5:
        print("📊 整体偏向: 空头突破占优")
    else:
        print("📊 整体偏向: 多空均衡")
    
    # === 5. 关键推荐 ===
    print(f"\n{'='*100}")
    print("【五、关键观察推荐】")
    print(f"{'='*100}")
    
    # 找出最值得关注的品种
    key_symbols = []
    for sym, obs_list in priority_obs.items():
        max_level = max(o.contraction_level for o in obs_list)
        has_sync = any(len(o.related_timeframes) > 0 for o in obs_list if o.contraction_level >= 3)
        score = max_level * 10 + (5 if has_sync else 0)
        key_symbols.append((sym, score, obs_list))
    
    key_symbols.sort(key=lambda x: -x[1])
    
    print("\nTop 5 关键观察品种:")
    for i, (sym, score, obs_list) in enumerate(key_symbols[:5], 1):
        main_obs = max(obs_list, key=lambda x: x.contraction_level)
        direction = "向下" if main_obs.breakout_direction == 'down' else "向上"
        sync_info = "+跨周期同步" if any(len(o.related_timeframes) > 0 for o in obs_list if o.contraction_level >= 3) else ""
        print(f"{i}. {sym}: {main_obs.timeframe}{main_obs.hex_value} "
              f"预期{direction}突破{main_obs.breakout_probability:.0%} {sync_info}")
    
    print(f"\n{'='*100}")


if __name__ == '__main__':
    generate_contraction_alert_report()
