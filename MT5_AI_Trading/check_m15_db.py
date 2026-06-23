"""验证 M15 State 数据库"""
from python.data.m15_state_db import M15StateDB

db = M15StateDB('data/m15_state.duckdb')

print("=" * 60)
print("M15 State 数据库验证")
print("=" * 60)

for sym in ['US_30', 'US_500', 'US_TECH100']:
    s = db.get_summary(sym)
    print(f"\n{sym}:")
    print(f"  总记录: {s['total_rows']} 条")
    print(f"  时间范围: {s['earliest']} ~ {s['latest']}")

    latest = db.get_latest(sym)
    if latest:
        print(f"  最新 M15={latest.get('m15_hex')}, H1={latest.get('h1_hex')}, D1={latest.get('d1_hex')}")
        print(f"  SR突破={latest.get('sr_breakout')}, 方向={latest.get('breakout_direction')}, 突破周期={latest.get('breakout_tf')}")

print("\n" + "=" * 60)
print("SR突破统计")
print("=" * 60)
conn = db._get_conn()
rows = conn.execute("""
    SELECT symbol, breakout_direction, COUNT(*) as cnt
    FROM m15_state_snapshot
    WHERE sr_breakout = TRUE
    GROUP BY symbol, breakout_direction
    ORDER BY symbol, breakout_direction
""").fetchall()
for r in rows:
    print(f"  {r[0]} {r[1]}: {r[2]} 次")

# 总统计
total = conn.execute("SELECT COUNT(*) FROM m15_state_snapshot").fetchone()[0]
print(f"\n总计: {total} 条 M15 State")

db.close()
print("\n验证完成!")
