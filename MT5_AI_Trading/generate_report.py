import duckdb
import json
from datetime import datetime

DB_PATH = "data/fundamental_duckdb.db"

print("=== 数据管道执行报告 ===\n")

conn = duckdb.connect(DB_PATH)

# 1. 数据概况
eq_count = conn.execute("SELECT COUNT(*) FROM equity_fundamentals").fetchone()[0]
eq_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM equity_fundamentals").fetchone()[0]
eq_latest = conn.execute("SELECT MAX(date) FROM equity_fundamentals").fetchone()[0]
macro_count = conn.execute("SELECT COUNT(*) FROM macro_indicators").fetchone()[0]

print(f"数据源: SEC EDGAR + yfinance")
print(f"股票数: {eq_symbols}/30 成功")
print(f"总记录: {eq_count} 条")
print(f"最新日期: {eq_latest}")
print(f"宏观数据: {macro_count} 条")

# 2. 各股票数据质量
print("\n=== 数据质量 ===")
quality = conn.execute("""
    SELECT 
        symbol,
        pe,
        pb,
        market_cap,
        revenue_growth,
        earnings_growth,
        debt_to_equity,
        current_ratio
    FROM equity_fundamentals
    WHERE date = (SELECT MAX(date) FROM equity_fundamentals)
    ORDER BY symbol
""").fetchall()

for row in quality:
    symbol, pe, pb, cap, rev, earn, debt, curr = row
    missing = []
    if pe is None: missing.append("PE")
    if pb is None: missing.append("PB")
    if cap is None: missing.append("市值")
    if rev is None: missing.append("营收增长")
    if earn is None: missing.append("盈利增长")
    if debt is None: missing.append("负债率")
    if curr is None: missing.append("流动比率")
    status = "完整" if not missing else f"缺: {', '.join(missing)}"
    cap_str = f"{cap/1e9:.1f}B" if cap else "N/A"
    print(f"  {symbol}: PE={pe}, PB={pb}, 市值={cap_str} | {status}")

# 3. 策略信号（简化版）
print("\n=== 策略信号 ===")
signals = conn.execute("""
    SELECT 
        symbol,
        pe,
        pb,
        revenue_growth,
        earnings_growth,
        debt_to_equity,
        dividend_yield
    FROM equity_fundamentals
    WHERE date = (SELECT MAX(date) FROM equity_fundamentals)
    ORDER BY symbol
""").fetchall()

buy_signals = []
sell_signals = []

for row in signals:
    symbol, pe, pb, rev, earn, debt, div = row
    score = 50
    reasons = []
    
    # 估值评分
    if pe and pe < 20:
        score += 15
        reasons.append("低PE")
    elif pe and pe > 40:
        score -= 15
        reasons.append("高PE")
    
    if pb and pb < 2:
        score += 10
        reasons.append("低PB")
    elif pb and pb > 5:
        score -= 10
        reasons.append("高PB")
    
    # 增长评分
    if rev and rev > 0.15:
        score += 10
        reasons.append("高增长")
    elif rev and rev < 0:
        score -= 10
        reasons.append("负增长")
    
    if earn and earn > 0.20:
        score += 10
        reasons.append("高盈利增长")
    
    # 财务健康
    if debt and debt < 1:
        score += 5
        reasons.append("低负债")
    elif debt and debt > 3:
        score -= 10
        reasons.append("高负债")
    
    # 分红
    if div and div > 0.03:
        score += 5
        reasons.append("高分红")
    
    score = max(0, min(100, score))
    
    if score >= 70:
        buy_signals.append((symbol, score, reasons))
    elif score <= 30:
        sell_signals.append((symbol, score, reasons))

print(f"\nBUY 信号 ({len(buy_signals)}个):")
for symbol, score, reasons in sorted(buy_signals, key=lambda x: -x[1]):
    print(f"  {symbol}: score={score} ({', '.join(reasons)})")

print(f"\nSELL 信号 ({len(sell_signals)}个):")
for symbol, score, reasons in sorted(sell_signals, key=lambda x: x[1]):
    print(f"  {symbol}: score={score} ({', '.join(reasons)})")

# 4. 问题记录
print("\n=== 问题记录 ===")
failed = conn.execute("""
    SELECT symbol FROM equity_fundamentals 
    WHERE date = (SELECT MAX(date) FROM equity_fundamentals)
    AND pe IS NULL AND pb IS NULL
""").fetchall()
if failed:
    print(f"  数据缺失: {', '.join([r[0] for r in failed])}")
else:
    print("  无重大问题")

conn.close()
print("\n=== 报告完成 ===")
