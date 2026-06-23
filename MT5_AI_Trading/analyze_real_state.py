"""
分析真实 MT5 State 数据
"""
import duckdb
import json

conn = duckdb.connect('data/h1_state.duckdb', read_only=True)

print("=== 真实 State Hex 分析 ===\n")

# 检查是否有真实数据（EURUSD等）
print("1. Symbols:")
rows = conn.execute("SELECT DISTINCT symbol FROM h1_state_snapshot ORDER BY symbol").fetchall()
symbols = [r[0] for r in rows]
print(f"   共 {len(symbols)} 个品种")
print(f"   前10: {symbols[:10]}")

# 检查 hex 格式
print("\n2. H1 Hex 格式样本:")
rows = conn.execute("""
    SELECT DISTINCT h1_hex 
    FROM h1_state_snapshot 
    WHERE h1_hex != 'N/A'
    ORDER BY h1_hex
    LIMIT 30
""").fetchall()
print(f"   唯一值数量: {len(rows)}")
print(f"   样本: {[r[0] for r in rows[:20]]}")

# 检查是否有真实格式（纯数字/字母如 4, -E, 6, 0, 2）
real_format = [r[0] for r in rows if r[0] and (r[0].lstrip('-') in '0123456789ABCDEF' or len(r[0].lstrip('-')) <= 2)]
print(f"\n   真实格式(纯hex): {real_format[:10]}")

# 检查旧格式（带 + = 如 B+H, C=M）
old_format = [r[0] for r in rows if r[0] and ('+' in r[0] or '=' in r[0])]
print(f"   旧格式(模拟数据): {old_format[:10]}")

# 统计真实 vs 旧格式比例
print("\n3. 格式分布:")
rows = conn.execute("""
    SELECT 
        CASE 
            WHEN h1_hex LIKE '%+%' OR h1_hex LIKE '%=%' THEN 'old_format'
            WHEN h1_hex REGEXP '^-?[0-9A-Fa-f]+$' THEN 'real_format'
            ELSE 'other'
        END as fmt,
        COUNT(*) as cnt
    FROM h1_state_snapshot
    GROUP BY fmt
    ORDER BY cnt DESC
""").fetchall()
for fmt, cnt in rows:
    print(f"   {fmt}: {cnt}")

# 真实数据的 hex 分布
print("\n4. 真实格式 Hex 分布:")
rows = conn.execute("""
    SELECT h1_hex, COUNT(*) as cnt
    FROM h1_state_snapshot
    WHERE h1_hex REGEXP '^-?[0-9A-Fa-f]+$' AND h1_hex != 'N/A'
    GROUP BY h1_hex
    ORDER BY cnt DESC
    LIMIT 20
""").fetchall()
print(f"{'Hex':>6} {'Count':>8} {'解码':>20}")
print("-" * 40)
for hex_val, cnt in rows:
    # 解码
    sign = -1 if hex_val.startswith('-') else 1
    clean = hex_val.lstrip('-')
    try:
        v = int(clean, 16)
        bits = []
        if v & 1: bits.append("vol")
        if v & 2: bits.append("brk")
        if v & 4: bits.append("trd")
        if v & 8: bits.append("base")
        dir_str = "看跌" if sign < 0 else "看涨"
        decode = f"{dir_str} {'+'.join(bits) if bits else 'squeeze'}"
    except:
        decode = "解析失败"
    print(f"{hex_val:>6} {cnt:>8} {decode:>20}")

conn.close()
print("\n=== 分析完成 ===")
