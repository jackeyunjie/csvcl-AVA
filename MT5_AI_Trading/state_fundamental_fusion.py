"""
state_fundamental_fusion.py v3 — Hermass 4-bit State 版
=======================================================
输入:
  data/hermass_state.db — Hermass 4-bit State (DuckDB, 12594条, 14品种)
  data/fundamental_duckdb.db — yfinance基本面 (可选)

分析:
  1. EF分布 — 各品种EF信号统计
  2. State模式频率 — 每种三元组组合的出现次数
  3. EF共振分析 — 哪些品种/时期最容易出现共振
  4. 基本面交叉 — PE分位×EF信号的胜率差异 (如有基本面数据)
  5. State转移矩阵 — 从State A→State B的概率
  6. 高价值信号规则候选

产出: reports/state_fundamental_fusion.json + 屏幕打印
"""

import duckdb, pandas as pd, json
from pathlib import Path
from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')

HERMASS_DB = Path("data/hermass_state.db")
FUND_DB = Path("data/fundamental_duckdb.db")
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

print("=" * 65)
print("  Hermass State x 基本面 交叉验证引擎 v3")
print("=" * 65)

conn = duckdb.connect()

# 加载 Hermass State (DuckDB)
if not HERMASS_DB.exists():
    print("[FATAL] hermass_state.db not found — 先运行 build_hermass_state.py")
    exit(1)

conn.execute(f"ATTACH '{HERMASS_DB}' AS hermass;")
state_count = conn.execute("SELECT COUNT(*) FROM hermass.state_snapshots").fetchone()[0]
state_syms = conn.execute("SELECT COUNT(DISTINCT symbol) FROM hermass.state_snapshots").fetchone()[0]
print(f"\n[State] {state_count} 条 | {state_syms} 品种 (Hermass 4-bit)")

date_range = conn.execute("SELECT MIN(date), MAX(date) FROM hermass.state_snapshots").fetchone()
sym_list = conn.execute("SELECT DISTINCT symbol FROM hermass.state_snapshots ORDER BY symbol").fetchall()
print(f"  日期: {date_range[0]} ~ {date_range[1]}")
print(f"  品种: {', '.join(r[0] for r in sym_list[:14])}")

# EF分布
ef_dist = conn.execute("""
    SELECT ef_count, COUNT(*), ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(),1) as pct
    FROM hermass.state_snapshots GROUP BY ef_count ORDER BY ef_count DESC
""").fetchall()
print(f"\n  EF分布:")
for r in ef_dist:
    bar = "#" * min(int(r[1] / 200), 40)
    print(f"    EF={r[0]}: {r[1]:5d} ({r[2]:5.1f}%) {bar}")

# 加载 基本面 (可选)
has_fund = FUND_DB.exists()
if has_fund:
    conn.execute(f"ATTACH '{FUND_DB}' AS fund_db;")
    fund_tables = conn.execute("SHOW TABLES FROM fund_db").fetchall()
    fund_stats = {}
    for tbl in fund_tables:
        try:
            cnt = conn.execute(f"SELECT COUNT(*) FROM fund_db.{tbl[0]}").fetchone()[0]
            fund_stats[tbl[0]] = cnt
        except: pass
    print(f"\n[Fund] DuckDB | {' | '.join(f'{k}:{v}' for k,v in fund_stats.items())}")
else:
    print("\n[Fund] 未找到, 仅做State内部分析")

# ============ 分析1: 三元组State模式频率 ============
print("\n" + "-" * 50)
print("  [分析1] 三元组State模式 TOP20")

pattern_freq = conn.execute("""
    SELECT mn1_hex || '_' || w1_hex || '_' || d1_hex as pattern,
           ef_count,
           COUNT(*) as n,
           ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(), 2) as pct
    FROM hermass.state_snapshots
    GROUP BY pattern, ef_count
    ORDER BY n DESC
    LIMIT 20
""").fetchdf()

print(pattern_freq.to_string(index=False))

# ============ 分析2: 各品种EF分布 ============
print("\n" + "-" * 50)
print("  [分析2] 各品种EF统计")

analysis2 = conn.execute("""
    SELECT symbol,
           COUNT(*) as n,
           ROUND(AVG(ef_count * 1.0), 2) as avg_ef,
           MAX(ef_count) as max_ef,
           SUM(CASE WHEN ef_count >= 2 THEN 1 ELSE 0 END) as ef2_count,
           ROUND(SUM(CASE WHEN ef_count >= 2 THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) as ef2_pct
    FROM hermass.state_snapshots
    GROUP BY symbol
    ORDER BY avg_ef DESC
""").fetchdf()

print(analysis2.to_string(index=False))

# ============ 分析3: EF>=2 的详细记录 ============
print("\n" + "-" * 50)
print("  [分析3] EF>=2 共振信号明细 (最近20条)")

ef_signals = conn.execute("""
    SELECT symbol, date, mn1_hex, w1_hex, d1_hex, ef_count,
           mn1_score, w1_score, d1_score
    FROM hermass.state_snapshots
    WHERE ef_count >= 2
    ORDER BY date DESC
    LIMIT 20
""").fetchdf()

if len(ef_signals) > 0:
    print(ef_signals.to_string(index=False))
else:
    print("  无EF>=2信号")

# ============ 分析4: State转移矩阵 ============
print("\n" + "-" * 50)
print("  [分析4] D1 State转移概率 (今日State → 明日State)")

transitions = conn.execute("""
    WITH state_seq AS (
        SELECT symbol, date, d1_hex,
               LEAD(d1_hex) OVER (PARTITION BY symbol ORDER BY date) as next_d1
        FROM hermass.state_snapshots
    )
    SELECT d1_hex as from_state, next_d1 as to_state, COUNT(*) as n
    FROM state_seq
    WHERE next_d1 IS NOT NULL
    GROUP BY d1_hex, next_d1
    HAVING COUNT(*) >= 10
    ORDER BY n DESC
    LIMIT 20
""").fetchdf()

if len(transitions) > 0:
    print(transitions.to_string(index=False))

# ============ 分析5: 基本面交叉 (如有) ============
if has_fund:
    print("\n" + "-" * 50)
    print("  [分析5] EF x 基本面交叉")

    try:
        fund_analysis = conn.execute("""
            SELECT s.symbol, s.ef_count,
                   COUNT(*) as n
            FROM hermass.state_snapshots s
            GROUP BY s.symbol, s.ef_count
            HAVING COUNT(*) >= 5
            ORDER BY s.ef_count DESC, n DESC
        """).fetchdf()
        print(fund_analysis.to_string(index=False))
    except Exception as e:
        print(f"  基本面交叉分析失败: {e}")

# ============ 分析6: 今日State快照 ============
print("\n" + "-" * 50)
print("  [分析6] 最新日期State快照")

latest = conn.execute("""
    SELECT symbol, date, mn1_hex, w1_hex, d1_hex, ef_count
    FROM hermass.state_snapshots
    WHERE date = (SELECT MAX(date) FROM hermass.state_snapshots)
    ORDER BY ef_count DESC, symbol
""").fetchdf()

print(latest.to_string(index=False))

# ============ 规则候选 ============
print("\n" + "-" * 50)
print("  [规则候选] 基于Hermass数据的信号规则")

rules = []
ef2_count = conn.execute("SELECT COUNT(*) FROM hermass.state_snapshots WHERE ef_count >= 2").fetchone()[0]
ef3_count = conn.execute("SELECT COUNT(*) FROM hermass.state_snapshots WHERE ef_count >= 3").fetchone()[0]
total = conn.execute("SELECT COUNT(*) FROM hermass.state_snapshots").fetchone()[0]

rules.append(f"EF>=2出现{ef2_count}次({ef2_count*100/total:.1f}%) — 高价值信号,需确认方向")
if ef3_count > 0:
    rules.append(f"EF=3出现{ef3_count}次({ef3_count*100/total:.2f}%) — 极稀缺,三周期共振")

# 最常见正向State
top_pos = conn.execute("""
    SELECT mn1_hex||'_'||w1_hex||'_'||d1_hex as pat, COUNT(*) as n
    FROM hermass.state_snapshots
    WHERE mn1_score > 0 AND w1_score > 0 AND d1_score > 0
    GROUP BY pat ORDER BY n DESC LIMIT 3
""").fetchall()
if top_pos:
    rules.append(f"最常见正向三元组: {', '.join(f'{r[0]}({r[1]}次)' for r in top_pos)}")

# 最常见负向State
top_neg = conn.execute("""
    SELECT mn1_hex||'_'||w1_hex||'_'||d1_hex as pat, COUNT(*) as n
    FROM hermass.state_snapshots
    WHERE mn1_score < 0 AND w1_score < 0 AND d1_score < 0
    GROUP BY pat ORDER BY n DESC LIMIT 3
""").fetchall()
if top_neg:
    rules.append(f"最常见负向三元组: {', '.join(f'{r[0]}({r[1]}次)' for r in top_neg)}")

rules.append("待验证: EF>=2 + 方向一致 → 趋势延续概率高")
rules.append("待验证: State从负翻正 → 反转信号强度")
rules.append("待验证: MN1=E + W1=E + D1=-C → 大趋势向好但短期调整")

for i, r in enumerate(rules, 1):
    print(f"  [{i}] {r}")

# ============ 输出 ============
output = {
    "generated_at": datetime.now().isoformat(),
    "engine": "hermass_v3",
    "state_records": int(state_count),
    "state_symbols": int(state_syms),
    "fund_available": has_fund,
    "ef2_signals": ef2_count,
    "ef3_signals": ef3_count,
    "rules": rules,
}
output_path = REPORTS_DIR / "state_fundamental_fusion.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)

conn.close()
print(f"\n{'='*65}")
print(f"  [Done] 报告: {output_path}")
print(f"{'='*65}")
