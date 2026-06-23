"""
score<=-12 三维验证: 年份/品种/成本修正
"""
import duckdb

c = duckdb.connect("data/stock_state.db")

# === 1. 按年份拆分 ===
print("=" * 65)
print("  验证1: score<=-12 按年份拆分")
y = c.execute("""
    SELECT STRFTIME(s.date, '%Y') yr, COUNT(*) n,
           ROUND(AVG(f.r5), 3) a5, ROUND(AVG(f.r20), 3) a20,
           ROUND(AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END)*100, 1) wr5,
           ROUND(AVG(CASE WHEN f.r20>0 THEN 1 ELSE 0 END)*100, 1) wr20
    FROM state_snapshots s
    JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
    WHERE s.d1_score <= -12 AND s.perspective='D1' AND f.r5 IS NOT NULL
    GROUP BY yr ORDER BY yr
""").fetchall()
print(f"  {'Year':6s} {'N':>4s} {'5dAvg':>8s} {'WR5':>6s} {'20dAvg':>8s} {'WR20':>6s}")
print(f"  {'-'*45}")
good, bad = 0, 0
for r in y:
    flag = "✓" if r[4] >= 50 else "✗"
    if r[4] >= 50: good += 1
    else: bad += 1
    print(f"  {r[0]:6s} {r[1]:4d} {r[2]:+7.2f}% {r[3]:5.1f}% {r[4]:+7.2f}% {r[5]:5.1f}% {flag}")
print(f"  年份一致性: {good}/{good+bad} 年份 WR5>=50%")

# === 2. 按品种拆分 ===
print("\n" + "=" * 65)
print("  验证2: score<=-12 按品种拆分")
by_sym = c.execute("""
    SELECT s.symbol, COUNT(*) n,
           ROUND(AVG(f.r5), 3) a5,
           ROUND(AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END)*100, 1) wr5,
           ROUND(AVG(CASE WHEN f.r5>0 THEN f.r5 ELSE 0 END),3) avg_win,
           ROUND(AVG(CASE WHEN f.r5<0 THEN -f.r5 ELSE 0 END),3) avg_loss,
           ROUND(AVG(f.r20), 3) a20
    FROM state_snapshots s
    JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
    WHERE s.d1_score <= -12 AND s.perspective='D1' AND f.r5 IS NOT NULL
    GROUP BY s.symbol
    HAVING COUNT(*) >= 10
    ORDER BY wr5 DESC
""").fetchall()

print(f"  {'Symbol':22s} {'N':>4s} {'5d':>8s} {'WR5':>6s} {'Win':>7s} {'Loss':>7s} {'20d':>8s}")
print(f"  {'-'*72}")
profitable, total_sym = 0, 0
for r in by_sym:
    total_sym += 1
    if r[3] >= 50: profitable += 1
    print(f"  {r[0]:22s} {r[1]:4d} {r[2]:+7.2f}% {r[3]:5.1f}% {r[4]:+6.2f}% {r[5]:+6.2f}% {r[6]:+7.2f}%")
print(f"  品种一致性: {profitable}/{total_sym} 品种 WR5>=50%")

total_n = sum(r[1] for r in by_sym)
top3 = sorted(by_sym, key=lambda x: x[1], reverse=True)[:3]
top3_pct = sum(r[1] for r in top3) / total_n * 100
print(f"  Top3集中度: {top3_pct:.0f}% ({top3[0][0]}:{top3[0][1]}, {top3[1][0]}:{top3[1][1]}, {top3[2][0]}:{top3[2][1]})")

# === 3. 扣除交易成本 ===
print("\n" + "=" * 65)
print("  验证3: 扣除交易成本后的期望值 (score<=-12)")
for cost in [0, 0.1, 0.2, 0.3, 0.5]:
    r = c.execute(f"""
        SELECT COUNT(*) n,
               ROUND(AVG(f.r5) - {cost}, 3) adj_5d,
               ROUND(AVG(CASE WHEN f.r5>{cost} THEN 1 ELSE 0 END)*100, 1) wr5_adj,
               ROUND(AVG(f.r20) - {cost*2}, 3) adj_20d,
               ROUND(AVG(CASE WHEN f.r20>{cost*2} THEN 1 ELSE 0 END)*100, 1) wr20_adj
        FROM state_snapshots s
        JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
        WHERE s.d1_score <= -12 AND s.perspective='D1' AND f.r5 IS NOT NULL
    """).fetchone()
    # Net EV = adjusted average return per trade
    print(f"  成本={cost}%: N={r[0]} 净5d={r[1]:+.3f}% WR={r[2]:.0f}% 净20d={r[3]:+.3f}% WR20={r[4]:.0f}%")

# === 4. 时间序列衰减(1/3/5/10/20d)  [use fwd + daily_prices]
print("\n" + "=" * 65)
print("  补充: score<=-12 收益率时间衰减")
for days in [5, 20]:
    col = "f5" if days == 5 else "f20"
    r = c.execute(f"""
        SELECT COUNT(*),
               ROUND(AVG((f.{col} - f.close)/f.close*100), 3),
               ROUND(AVG(CASE WHEN f.{col}>f.close THEN 1 ELSE 0 END)*100,1)
        FROM state_snapshots s
        JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
        WHERE s.d1_score <= -12 AND s.perspective='D1' AND f.{col} IS NOT NULL
    """).fetchone()
    print(f"  {days:2d}d: N={r[0]} avg={r[1]:+.3f}% WR={r[2]}%")

# === 5. 正负对比(score<=-12 vs score>=12 vs all) ===
print("\n" + "=" * 65)
print("  对比: 不同信号级别 vs 随机入场")
for label, cond in [
    ("score<=-12","s.d1_score <= -12"),
    ("score>=12","s.d1_score >= 12"),
    ("|score|<12 (弱信号)","abs(s.d1_score) < 12"),
]:
    r = c.execute(f"""
        SELECT COUNT(*), ROUND(AVG(f.r5), 3),
               ROUND(AVG(CASE WHEN f.r5>0 THEN 1 ELSE 0 END)*100,1),
               ROUND(AVG(f.r20), 3)
        FROM state_snapshots s
        JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
        WHERE ({cond}) AND s.perspective='D1' AND f.r5 IS NOT NULL
    """).fetchone()
    print(f"  {label:25s} N={r[0]:5d} 5d={r[1]:+7.3f}% WR5={r[2]:.0f}% 20d={r[3]:+7.3f}%")

c.close()
import os
print(f"\nDone: {os.path.getsize('data/stock_state.db')/1024/1024:.0f}MB")
