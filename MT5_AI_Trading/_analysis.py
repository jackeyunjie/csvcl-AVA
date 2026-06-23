import duckdb,os
c=duckdb.connect('data/hermass_state.db')

# EF分布
ef=c.execute("SELECT ef_count,COUNT(*) n,ROUND(COUNT(*)*100.0/12594,1) pct FROM state_snapshots GROUP BY ef_count ORDER BY ef_count DESC").fetchall()
print("EF分布:")
for r in ef: print(f"  EF={r[0]}: {r[1]:5d} ({r[2]}%)")

# EF=2品种
ef2=c.execute("SELECT symbol,COUNT(*) n FROM state_snapshots WHERE ef_count=2 GROUP BY symbol ORDER BY n DESC").fetchall()
print("\nEF=2品种:")
for r in ef2: print(f"  {r[0]:8s} {r[1]:3d}次")

# 正向TOP
pos=c.execute("""
    SELECT mn1_hex||'_'||w1_hex||'_'||d1_hex pat,COUNT(*) n
    FROM state_snapshots 
    WHERE ef_count>=1 AND mn1_score>=0 AND w1_score>=0 AND d1_score>=0 
    GROUP BY pat ORDER BY n DESC LIMIT 8
""").fetchall()
print("\n高频正向三元组:")
for r in pos: print(f"  {r[0]:20s} x{r[1]:4d}")

# 负向TOP
neg=c.execute("""
    SELECT mn1_hex||'_'||w1_hex||'_'||d1_hex pat,COUNT(*) n
    FROM state_snapshots 
    WHERE ef_count>=1 AND (mn1_score<0 OR w1_score<0 OR d1_score<0) 
    GROUP BY pat ORDER BY n DESC LIMIT 8
""").fetchall()
print("\n高频负向三元组:")
for r in neg: print(f"  {r[0]:20s} x{r[1]:4d}")

# State转移矩阵(简化)
print("\nD1 State转移TOP10 (EURUSD):")
trans=c.execute("""
    WITH lagged AS (
        SELECT d1_hex, LAG(d1_hex) OVER (ORDER BY date) prev
        FROM state_snapshots WHERE symbol='EURUSD' AND perspective='D1'
    )
    SELECT prev||'->'||d1_hex trans, COUNT(*) n
    FROM lagged WHERE prev IS NOT NULL
    GROUP BY trans ORDER BY n DESC LIMIT 10
""").fetchall()
for r in trans: print(f"  {r[0]:12s} x{r[1]:3d}")

c.close()
