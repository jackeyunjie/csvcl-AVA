import duckdb
import pandas as pd
from datetime import datetime, timedelta

conn = duckdb.connect('data/h1_state.duckdb', read_only=True)

# 查看表结构
desc = conn.execute("DESCRIBE h1_state_snapshot").fetchdf()
print('h1_state_snapshot 表结构:')
print(desc.to_string())

# 查看GERMANY_40最近的数据
df = conn.execute("""
    SELECT symbol, timestamp, h1_hex, d1_hex, h4_hex
    FROM h1_state_snapshot 
    WHERE symbol = 'GERMANY_40' 
    ORDER BY timestamp DESC 
    LIMIT 30
""").fetchdf()
print('\nGERMANY_40最近30条:')
print(df.to_string())

# 查找h1_hex相同（完全横盘）的时间段
# 先查看数据特征
print('\n' + '='*80)
print('GERMANY_40数据时间范围')
print('='*80)

range_df = conn.execute("""
    SELECT 
        MIN(timestamp) as start_time,
        MAX(timestamp) as end_time,
        COUNT(*) as total_rows
    FROM h1_state_snapshot 
    WHERE symbol = 'GERMANY_40'
""").fetchdf()
print(range_df.to_string())

# 查找连续的相同h1_hex（表示H1小时价格横盘）
print('\n' + '='*80)
print('查找H1小时价格横盘模式分析')
print('='*80)

# 获取所有数据按时间排序
all_df = conn.execute("""
    SELECT symbol, timestamp, h1_hex, d1_hex, h4_hex
    FROM h1_state_snapshot 
    WHERE symbol = 'GERMANY_40'
    ORDER BY timestamp ASC
""").fetchdf()

# 分析连续相同h1_hex的情况
print(f'\n总数据量: {len(all_df)} 条')

# 查找h1_hex连续相同的序列
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
        WHERE symbol = 'GERMANY_40' 
          AND timestamp > ?
        ORDER BY timestamp ASC
        LIMIT 30
    """, [end_time]).fetchdf()
    
    print(f'\n横盘后30条走势:')
    print(after_df.to_string())

conn.close()
