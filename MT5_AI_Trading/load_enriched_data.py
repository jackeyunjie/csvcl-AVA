"""
合并数据加载器 - 种子数据(估值) + SEC EDGAR(财报)
解决：SEC EDGAR 没有 PE/PB/市值，种子数据没有真实财报
"""

import sys
import time
import datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "python" / "data"))

from fundamental_pipeline import (
    DuckDBManager, EquityFundamental, DATA_DIR, DB_PATH
)
from sec_edgar_fetcher import SECEdgarFetcher

# 种子数据：提供 PE/PB/市值/行业等估值数据
SEED_VALUATIONS = {
    # symbol: (PE, PB, PS, market_cap, beta, sector, industry)
    "AAPL": (28.5, 45.2, 7.8, 3.2e12, 1.2, "Technology", "Consumer Electronics"),
    "MSFT": (32.1, 12.8, 13.5, 3.0e12, 0.9, "Technology", "Software"),
    "GOOGL": (24.3, 7.1, 6.2, 2.1e12, 1.1, "Technology", "Internet Content"),
    "AMZN": (58.2, 8.5, 3.2, 2.0e12, 1.3, "Consumer Cyclical", "Internet Retail"),
    "META": (23.8, 8.2, 8.5, 1.3e12, 1.3, "Technology", "Social Media"),
    "NVDA": (62.5, 42.0, 30.1, 3.0e12, 1.7, "Technology", "Semiconductors"),
    "TSLA": (45.0, 12.5, 8.0, 800e9, 2.0, "Consumer Cyclical", "Auto Manufacturers"),
    "JPM": (12.5, 1.8, 3.5, 580e9, 1.1, "Financial Services", "Banks"),
    "BAC": (13.2, 1.2, 3.0, 320e9, 1.2, "Financial Services", "Banks"),
    "GS": (15.0, 1.5, 3.8, 160e9, 1.3, "Financial Services", "Capital Markets"),
    "WFC": (11.8, 1.3, 2.8, 220e9, 1.1, "Financial Services", "Banks"),
    "C": (10.5, 0.8, 2.2, 130e9, 1.4, "Financial Services", "Banks"),
    "WMT": (28.0, 6.5, 0.8, 520e9, 0.5, "Consumer Defensive", "Retail"),
    "COST": (48.0, 12.0, 1.5, 380e9, 0.7, "Consumer Defensive", "Retail"),
    "HD": (24.0, 500.0, 2.2, 380e9, 1.0, "Consumer Cyclical", "Home Improvement"),
    "PG": (26.0, 7.5, 4.8, 380e9, 0.5, "Consumer Defensive", "Household Products"),
    "KO": (24.0, 10.0, 6.0, 270e9, 0.6, "Consumer Defensive", "Beverages"),
    "PEP": (26.0, 12.0, 4.5, 240e9, 0.6, "Consumer Defensive", "Beverages"),
    "JNJ": (16.0, 5.5, 4.2, 380e9, 0.5, "Healthcare", "Drug Manufacturers"),
    "PFE": (18.0, 2.0, 2.5, 160e9, 0.7, "Healthcare", "Drug Manufacturers"),
    "UNH": (22.0, 6.0, 1.5, 520e9, 0.7, "Healthcare", "Healthcare Plans"),
    "ABBV": (18.0, 30.0, 5.5, 320e9, 0.7, "Healthcare", "Drug Manufacturers"),
    "LLY": (80.0, 40.0, 18.0, 700e9, 0.5, "Healthcare", "Drug Manufacturers"),
    "XOM": (14.0, 2.0, 1.5, 480e9, 0.8, "Energy", "Oil & Gas"),
    "CVX": (15.0, 1.8, 1.3, 300e9, 0.9, "Energy", "Oil & Gas"),
    "BA": (0, 0, 2.0, 130e9, 1.5, "Industrials", "Aerospace & Defense"),
    "CAT": (16.0, 6.0, 2.5, 170e9, 1.1, "Industrials", "Farm & Heavy Equipment"),
    "VZ": (10.0, 3.0, 1.5, 170e9, 0.5, "Communication Services", "Telecom"),
    "DIS": (35.0, 2.0, 3.0, 200e9, 1.3, "Communication Services", "Entertainment"),
    "NFLX": (40.0, 12.0, 8.0, 280e9, 1.3, "Communication Services", "Entertainment"),
    "CRM": (50.0, 5.0, 8.0, 270e9, 1.2, "Technology", "Software"),
}


def load_enriched_data():
    """加载合并数据：种子估值 + SEC EDGAR 财报"""
    print("=" * 50)
    print("合并数据加载：种子估值 + SEC EDGAR 财报")
    print("=" * 50)

    # 删除旧数据库
    import os
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print("[OK] 已删除旧数据库")

    db = DuckDBManager(DB_PATH)
    sec = SECEdgarFetcher()

    with db:
        db.init_tables()

        records = []
        sec_success = 0
        sec_fail = 0

        for symbol, valuation in SEED_VALUATIONS.items():
            pe, pb, ps, mc, beta, sector, industry = valuation

            # SEC EDGAR 拉取财报数据
            sec_data = {}
            try:
                sec_data = sec.get_fundamentals(symbol)
                if sec_data and sec_data.get("revenue"):
                    sec_success += 1
                    print(f"  [SEC] {symbol}: revenue={sec_data['revenue']:,.0f}")
                else:
                    sec_fail += 1
                    print(f"  [SEC] {symbol}: 无数据")
            except Exception as e:
                sec_fail += 1
                print(f"  [SEC] {symbol}: 错误 {e}")

            time.sleep(0.15)  # SEC 限流

            # 合并：种子估值 + SEC 财报
            record = EquityFundamental(
                symbol=symbol,
                date=dt.date.today().isoformat(),
                pe=pe if pe > 0 else None,
                pb=pb if pb > 0 else None,
                ps=ps,
                market_cap=mc,
                revenue_growth=None,
                earnings_growth=None,
                debt_to_equity=sec_data.get("debt_to_equity"),
                current_ratio=sec_data.get("current_ratio"),
                dividend_yield=sec_data.get("dividends_per_share"),
                beta=beta,
                sector=sector,
                industry=industry,
                fetched_at=dt.datetime.now().isoformat(),
            )
            records.append(record)

        # 批量写入
        db.upsert_equity(records)

        # 验证
        eq_count = db.conn.execute("SELECT COUNT(*) FROM equity_fundamentals").fetchone()[0]
        non_null = db.conn.execute("""
            SELECT COUNT(*) FROM equity_fundamentals
            WHERE pe IS NOT NULL AND debt_to_equity IS NOT NULL
        """).fetchone()[0]

        print(f"\n{'='*50}")
        print(f"合并数据加载完成:")
        print(f"  总记录: {eq_count}")
        print(f"  SEC EDGAR 成功: {sec_success}/{len(SEED_VALUATIONS)}")
        print(f"  SEC EDGAR 失败: {sec_fail}/{len(SEED_VALUATIONS)}")
        print(f"  完整记录(PE+负债率): {non_null}")
        print(f"{'='*50}")


if __name__ == "__main__":
    load_enriched_data()
