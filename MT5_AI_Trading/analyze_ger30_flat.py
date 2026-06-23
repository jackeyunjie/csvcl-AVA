import duckdb
import pandas as pd

conn = duckdb.connect('data/h1_state.duckdb', read_only=True)

# 查看GER30最近的数据
df = conn.execute("""
    SELECT symbol, timestamp, h1_hex, d1_hex, h4_hex
    FROM h1_state_snapshot 
    WHERE symbol = 'GER30' 
    ORDER BY timestamp DESC 
    LIMIT 30
""").fetchdf()
print('GER30最近30条:')
print(df.to_string())

# 获取所有数据按时间排序
all_df = conn.execute("""
    SELECT symbol, timestamp, h1_hex, d1_hex, h4_hex
    FROM h1_state_snapshot 
    WHERE symbol = 'GER30'
    ORDER BY timestamp ASC
""").fetchdf()

print(f'\n总数据量: {len(all_df)} 条')

# 分析连续相同h1_hex的情况（表示H1小时state未变化，价格横盘）
all_df['h1_hex_prev'] = all_df['h1_hex'].shift(1)
all_df['is_same'] = all_df['h1_hex'] == all_df['h1_hex_prev']
all_df['group'] = (~all_df['is_same']).cumsum()

# 统计每个连续组的时长
groups = all_df.groupby('group').agg({
    'timestamp': ['min', 'max', 'count'],
    'h1_hex': 'first'
}).reset_index()
groups.columns = ['group', 'start_time', 'end_time', 'count', 'h1_hex']

# 过滤出连续2条以上的横盘
flat_groups = groups[groups['count'] >= 2].sort_values('end_time', ascending=False)
print(f'\n找到 {len(flat_groups)} 组连续相同h1_hex的横盘（>=2条）:')
print(flat_groups.head(20).to_string())

# 分析最近一次横盘后的走势
if len(flat_groups) > 0:
    latest_flat = flat_groups.iloc[0]
    end_time = latest_flat['end_time']
    print('\n' + '='*80)
    print(f'最近一次横盘分析:')
    print(f'  时间段: {latest_flat["start_time"]} ~ {end_time}')
    print(f'  持续条数: {latest_flat["count"]}')
    print(f'  h1_hex: {latest_flat["h1_hex"]}')
    print('='*80)
    
    # 获取横盘后的数据
    after_df = conn.execute("""
        SELECT symbol, timestamp, h1_hex, d1_hex, h4_hex
        FROM h1_state_snapshot 
        WHERE symbol = 'GER30' 
          AND timestamp > ?
        ORDER BY timestamp ASC
        LIMIT 30
    """, [end_time]).fetchdf()
    
    print(f'\n横盘后30条走势:')
    print(after_df.to_string())
    
    # 统计历史所有横盘后的走势规律
    print('\n' + '='*80)
    print('历史横盘后走势统计（所有>=2条横盘）')
    print('='*80)
    
    results = []
    for idx, row in flat_groups.head(50).iterrows():
        flat_end = row['end_time']
        flat_hex = row['h1_hex']
        
        # 获取横盘后1条、5条、10条、20条的h1_hex变化
        after = conn.execute("""
            SELECT h1_hex
            FROM h1_state_snapshot 
            WHERE symbol = 'GER30' 
              AND timestamp > ?
            ORDER BY timestamp ASC
            LIMIT 20
        """, [flat_end]).fetchdf()
        
        if len(after) >= 1:
            h1_1 = after['h1_hex'].iloc[0]
            h1_5 = after['h1_hex'].iloc[4] if len(after) >= 5 else None
            h1_10 = after['h1_hex'].iloc[9] if len(after) >= 10 else None
            h1_20 = after['h1_hex'].iloc[19] if len(after) >= 20 else None
            
            # 判断方向变化
            def get_direction(hex_val):
                if hex_val and hex_val.startswith('-'):
                    return 'down'
                elif hex_val and hex_val.startswith('+'):
                    return 'up'
                else:
                    return 'neutral'
            
            flat_dir = get_direction(flat_hex)
            after1_dir = get_direction(h1_1)
            
            results.append({
                'flat_end': flat_end,
                'flat_hex': flat_hex,
                'flat_count': row['count'],
                'after1_hex': h1_1,
                'after1_dir': after1_dir,
                'after5_hex': h1_5,
                'after10_hex': h1_10,
                'after20_hex': h1_20,
                'changed': flat_hex != h1_1
            })
    
    results_df = pd.DataFrame(results)
    print(f'\n统计了 {len(results_df)} 次横盘事件:')
    print(results_df.to_string())
    
    # 统计规律
    print('\n' + '='*80)
    print('横盘后走势规律统计')
    print('='*80)
    
    changed = results_df['changed'].sum()
    unchanged = len(results_df) - changed
    print(f'横盘后下一小时state变化: {changed} 次 ({changed/len(results_df)*100:.1f}%)')
    print(f'横盘后下一小时state不变: {unchanged} 次 ({unchanged/len(results_df)*100:.1f}%)')
    
    # 按横盘时的state分类
    print('\n按横盘时h1_hex分类统计:')
    for hex_val in results_df['flat_hex'].unique()[:10]:
        subset = results_df[results_df['flat_hex'] == hex_val]
        if len(subset) > 0:
            changes = subset['changed'].sum()
            print(f'  h1_hex={hex_val}: 共{len(subset)}次, 变化{changes}次, 不变{len(subset)-changes}次')

conn.close()
