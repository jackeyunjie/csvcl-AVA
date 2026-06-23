"""
种子数据加载器 - 当外部API不可用时，用模拟数据跑通流程
用于验证 DuckDB → 策略引擎 → MT5 EA 的完整管道
"""

import sys
import datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "python" / "data"))

from fundamental_pipeline import (
    DuckDBManager, EquityFundamental, MacroIndicator,
    DATA_DIR, DB_PATH
)

# 30只美股的种子数据（基于真实市场大致水平）
SEED_EQUITIES = [
    # symbol, PE, PB, PS, market_cap, rev_growth, earn_growth, debt_equity, current_ratio, div_yield, beta, sector
    ("AAPL", 28.5, 45.2, 7.8, 3.2e12, 0.08, 0.12, 180, 1.07, 0.005, 1.2, "Technology"),
    ("MSFT", 32.1, 12.8, 13.5, 3.0e12, 0.16, 0.20, 45, 1.28, 0.008, 0.9, "Technology"),
    ("GOOGL", 24.3, 7.1, 6.2, 2.1e12, 0.14, 0.25, 15, 2.10, 0.0, 1.1, "Technology"),
    ("AMZN", 58.2, 8.5, 3.2, 2.0e12, 0.12, 0.35, 55, 1.09, 0.0, 1.3, "Consumer Cyclical"),
    ("META", 23.8, 8.2, 8.5, 1.3e12, 0.22, 0.35, 30, 2.75, 0.004, 1.3, "Technology"),
    ("NVDA", 62.5, 42.0, 30.1, 3.0e12, 0.55, 0.80, 40, 4.20, 0.001, 1.7, "Technology"),
    ("TSLA", 45.0, 12.5, 8.0, 800e9, 0.15, 0.10, 20, 1.80, 0.0, 2.0, "Consumer Cyclical"),
    ("JPM", 12.5, 1.8, 3.5, 580e9, 0.10, 0.15, 0, 0, 0.025, 1.1, "Financial Services"),
    ("BAC", 13.2, 1.2, 3.0, 320e9, 0.08, 0.12, 0, 0, 0.027, 1.2, "Financial Services"),
    ("GS", 15.0, 1.5, 3.8, 160e9, 0.12, 0.18, 0, 0, 0.024, 1.3, "Financial Services"),
    ("WFC", 11.8, 1.3, 2.8, 220e9, 0.06, 0.10, 0, 0, 0.028, 1.1, "Financial Services"),
    ("C", 10.5, 0.8, 2.2, 130e9, 0.05, 0.08, 0, 0, 0.035, 1.4, "Financial Services"),
    ("WMT", 28.0, 6.5, 0.8, 520e9, 0.05, 0.08, 65, 0.85, 0.013, 0.5, "Consumer Defensive"),
    ("COST", 48.0, 12.0, 1.5, 380e9, 0.08, 0.10, 45, 1.20, 0.006, 0.7, "Consumer Defensive"),
    ("HD", 24.0, 500.0, 2.2, 380e9, 0.03, 0.05, 0, 0, 0.024, 1.0, "Consumer Cyclical"),
    ("PG", 26.0, 7.5, 4.8, 380e9, 0.04, 0.06, 60, 0.80, 0.024, 0.5, "Consumer Defensive"),
    ("KO", 24.0, 10.0, 6.0, 270e9, 0.03, 0.05, 150, 1.10, 0.030, 0.6, "Consumer Defensive"),
    ("PEP", 26.0, 12.0, 4.5, 240e9, 0.05, 0.08, 200, 0.90, 0.028, 0.6, "Consumer Defensive"),
    ("JNJ", 16.0, 5.5, 4.2, 380e9, 0.03, 0.05, 45, 1.30, 0.030, 0.5, "Healthcare"),
    ("PFE", 18.0, 2.0, 2.5, 160e9, -0.20, -0.30, 60, 1.50, 0.058, 0.7, "Healthcare"),
    ("UNH", 22.0, 6.0, 1.5, 520e9, 0.12, 0.15, 65, 0.85, 0.013, 0.7, "Healthcare"),
    ("ABBV", 18.0, 30.0, 5.5, 320e9, 0.05, 0.08, 0, 0, 0.035, 0.7, "Healthcare"),
    ("LLY", 80.0, 40.0, 18.0, 700e9, 0.28, 0.35, 200, 1.10, 0.007, 0.5, "Healthcare"),
    ("XOM", 14.0, 2.0, 1.5, 480e9, 0.05, 0.10, 20, 1.30, 0.032, 0.8, "Energy"),
    ("CVX", 15.0, 1.8, 1.3, 300e9, 0.03, 0.08, 15, 1.40, 0.038, 0.9, "Energy"),
    ("BA", 0, 0, 2.0, 130e9, 0.10, 0, 0, 0, 0, 1.5, "Industrials"),
    ("CAT", 16.0, 6.0, 2.5, 170e9, 0.05, 0.10, 200, 1.30, 0.017, 1.1, "Industrials"),
    ("VZ", 10.0, 3.0, 1.5, 170e9, 0.02, 0.03, 150, 0.70, 0.065, 0.5, "Communication Services"),
    ("DIS", 35.0, 2.0, 3.0, 200e9, 0.05, 0.10, 45, 1.00, 0.0, 1.3, "Communication Services"),
    ("NFLX", 40.0, 12.0, 8.0, 280e9, 0.12, 0.20, 60, 1.10, 0.0, 1.3, "Communication Services"),
    ("CRM", 50.0, 5.0, 8.0, 270e9, 0.11, 0.20, 15, 1.10, 0.0, 1.2, "Technology"),
]

# 宏观数据种子
SEED_MACRO = MacroIndicator(
    date=dt.date.today().isoformat(),
    us10y=4.30,
    us2y=4.05,
    us3m=4.20,
    cpi_yoy=3.4,
    core_pce=2.8,
    unemployment=3.9,
    initial_claims=215000,
    vix=15.2,
    fed_funds=5.25,
    gdp=2.5,
    fetched_at=dt.datetime.now().isoformat(),
)


def load_seed_data():
    """加载种子数据到 DuckDB"""
    print("=" * 50)
    print("加载种子数据（模拟数据）")
    print("=" * 50)

    # 删除旧数据库，确保表结构正确
    import os
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print("已删除旧数据库")

    db = DuckDBManager(DB_PATH)
    with db:
        db.init_tables()

        # 加载个股数据
        records = []
        for row in SEED_EQUITIES:
            symbol, pe, pb, ps, mc, rg, eg, de, cr, dy, beta, sector = row
            records.append(EquityFundamental(
                symbol=symbol,
                date=dt.date.today().isoformat(),
                pe=pe if pe > 0 else None,
                pb=pb if pb > 0 else None,
                ps=ps,
                market_cap=mc,
                revenue_growth=rg,
                earnings_growth=eg,
                debt_to_equity=de if de > 0 else None,
                current_ratio=cr if cr > 0 else None,
                dividend_yield=dy if dy > 0 else None,
                beta=beta,
                sector=sector,
                fetched_at=dt.datetime.now().isoformat(),
            ))

        db.upsert_equity(records)
        print(f"[OK] 加载 {len(records)} 只股票种子数据")

        # 加载宏观数据
        db.upsert_macro([SEED_MACRO])
        print("[OK] 加载宏观数据种子")

        # 验证
        eq_count = db.conn.execute("SELECT COUNT(*) FROM equity_fundamentals").fetchone()[0]
        macro_count = db.conn.execute("SELECT COUNT(*) FROM macro_indicators").fetchone()[0]
        print(f"\n数据库统计:")
        print(f"  个股记录: {eq_count}")
        print(f"  宏观记录: {macro_count}")

    print("\n[OK] 种子数据加载完成！可以运行策略分析了。")


if __name__ == "__main__":
    load_seed_data()
