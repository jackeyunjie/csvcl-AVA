import duckdb
c=duckdb.connect('data/hermass_state.db')

# EF=3
ef3=c.execute("""
    SELECT COUNT(*),AVG(f.r5),AVG(CASE WHEN r5>0 THEN 1 ELSE 0 END)
    FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
    WHERE s.ef_count=3 AND f.r5 IS NOT NULL
""").fetchone()
if ef3[0]:
    print(f"EF=3: N={ef3[0]} 5d={ef3[1]:+.3f}% WR5={ef3[2]*100:.0f}%")
else:
    print("EF=3: 0 (无向前价格数据覆盖)")

# JPYX EF>=2
jp=c.execute("""
    SELECT s.symbol,COUNT(*) n,AVG(f.r5) a5,
           AVG(CASE WHEN r5>0 THEN 1 ELSE 0 END) w5,
           AVG(f.r20) a20,AVG(CASE WHEN r20>0 THEN 1 ELSE 0 END) w20
    FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
    WHERE s.ef_count>=2 AND s.symbol IN('EURJPY','USDJPY','GBPJPY','AUDJPY')
    AND f.r5 IS NOT NULL
    GROUP BY s.symbol ORDER BY w5 DESC
""").fetchall()
total_jp=sum(r[1] for r in jp)
print(f"\nJPY交叉 EF>=2 合计{total_jp}次:")
for r in jp: print(f"  {r[0]:8s} N={r[1]:4d} WR5={r[3]*100:.0f}% WR20={r[5]*100:.0f}%  5d={r[2]:+.2f}% 20d={r[4]:+.2f}%")

# N>=50 Top
top=c.execute("""
    SELECT mn1_hex||'_'||w1_hex||'_'||d1_hex pat,COUNT(*) n,
           AVG(f.r5) a5,AVG(CASE WHEN r5>0 THEN 1 ELSE 0 END) w5
    FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
    WHERE s.perspective='D1' AND f.r5 IS NOT NULL
    GROUP BY pat HAVING COUNT(*)>=50 ORDER BY a5 DESC LIMIT 10
""").fetchall()
print(f"\nN>=50 高收益State模式:")
for r in top: print(f"  {r[0]:20s} N={r[1]:4d} 5d={r[2]:+6.2f}% WR={r[3]*100:5.0f}%")

# EF=2 + specific filter
print("\nEF=2 + position_bit=2 (突破):")
ef2_pos = c.execute("""
    SELECT COUNT(*),AVG(f.r5),AVG(CASE WHEN r5>0 THEN 1 ELSE 0 END),
           AVG(f.r20),AVG(CASE WHEN r20>0 THEN 1 ELSE 0 END)
    FROM state_snapshots s JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
    WHERE s.ef_count=2 AND s.d1_score IN (14,15) AND f.r5 IS NOT NULL
""").fetchone()
print(f"  N={ef2_pos[0]} 5d={ef2_pos[1]:+.2f}% WR5={ef2_pos[2]*100:.0f}% 20d={ef2_pos[3]:+.2f}% WR20={ef2_pos[4]*100:.0f}%")

c.close()
