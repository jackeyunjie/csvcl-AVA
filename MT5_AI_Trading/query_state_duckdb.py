"""
DuckDB State数据库查询示例
展示DuckDB的强大分析能力
"""
import duckdb
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/state_duckdb.db")

if not DB_PATH.exists():
    print("数据库不存在，请先运行 build_state_duckdb.py")
    exit(1)

conn = duckdb.connect(str(DB_PATH))

print("="*60)
print("DuckDB State数据库查询")
print("="*60)

# 1. 基本统计
print("\n【1】基本统计")
result = conn.execute('''
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT symbol) as symbols,
        MIN(timestamp) as start_date,
        MAX(timestamp) as end_date
    FROM state_snapshots
''').fetchone()
print(f"总记录: {result[0]}")
print(f"品种数: {result[1]}")
print(f"时间跨度: {result[2]} ~ {result[3]}")

# 2. EF分布
print("\n【2】EF信号分布")
df_ef = conn.execute('''
    SELECT 
        ef_count,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
    FROM state_snapshots
    GROUP BY ef_count
    ORDER BY ef_count
''').fetchdf()
print(df_ef.to_string(index=False))

# 3. 各品种State统计
print("\n【3】各品种快照数 (Top 10)")
df_symbols = conn.execute('''
    SELECT 
        symbol,
        COUNT(*) as snapshots,
        ROUND(AVG(ef_count), 2) as avg_ef,
        MAX(ef_count) as max_ef
    FROM state_snapshots
    GROUP BY symbol
    ORDER BY snapshots DESC
    LIMIT 10
''').fetchdf()
print(df_symbols.to_string(index=False))

# 4. 高EF信号查询 (DuckDB快速过滤)
print("\n【4】高EF信号历史 (ef>=2) - 最近20条")
df_high_ef = conn.execute('''
    SELECT 
        timestamp,
        symbol,
        state_hex,
        ef_count
    FROM state_snapshots
    WHERE ef_count >= 2
    ORDER BY timestamp DESC
    LIMIT 20
''').fetchdf()
if len(df_high_ef) > 0:
    print(df_high_ef.to_string(index=False))
else:
    print("  无高EF信号记录")

# 5. State转换分析 (DuckDB LAG窗口函数)
print("\n【5】EURUSD State转换分析")
df_transitions = conn.execute('''
    WITH state_lag AS (
        SELECT 
            timestamp,
            state_hex,
            ef_count,
            LAG(state_hex) OVER (ORDER BY timestamp) as prev_state
        FROM state_snapshots
        WHERE symbol = 'EURUSD'
    )
    SELECT 
        prev_state || ' -> ' || state_hex as transition,
        COUNT(*) as frequency
    FROM state_lag
    WHERE prev_state IS NOT NULL
    GROUP BY prev_state, state_hex
    ORDER BY frequency DESC
    LIMIT 10
''').fetchdf()
print(df_transitions.to_string(index=False))

# 6. 月度EF信号统计 (DuckDB时间聚合)
print("\n【6】EURUSD月度高EF信号统计")
df_monthly = conn.execute('''
    SELECT 
        strftime(timestamp, '%Y-%m') as month,
        COUNT(*) as total_days,
        SUM(CASE WHEN ef_count >= 1 THEN 1 ELSE 0 END) as signal_days,
        ROUND(AVG(ef_count), 2) as avg_ef
    FROM state_snapshots
    WHERE symbol = 'EURUSD'
    GROUP BY strftime(timestamp, '%Y-%m')
    HAVING COUNT(*) > 5
    ORDER BY month DESC
    LIMIT 12
''').fetchdf()
print(df_monthly.to_string(index=False))

# 7. 导出为Pandas (DuckDB原生支持)
print("\n【7】导出为Pandas DataFrame")
df_full = conn.execute('''
    SELECT * FROM state_snapshots
''').fetchdf()
print(f"DataFrame形状: {df_full.shape}")
print(f"列: {list(df_full.columns)}")

# 8. 复杂分析: 寻找State模式
print("\n【8】最常见State模式 (Top 10)")
df_patterns = conn.execute('''
    SELECT 
        state_hex,
        COUNT(*) as frequency,
        ROUND(AVG(ef_count), 2) as avg_ef,
        COUNT(DISTINCT symbol) as symbols
    FROM state_snapshots
    GROUP BY state_hex
    ORDER BY frequency DESC
    LIMIT 10
''').fetchdf()
print(df_patterns.to_string(index=False))

conn.close()

print("\n" + "="*60)
print("DuckDB查询完成!")
print("="*60)
