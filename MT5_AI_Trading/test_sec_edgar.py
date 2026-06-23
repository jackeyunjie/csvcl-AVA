"""测试 SEC EDGAR 数据拉取"""
import sys
import logging
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "python" / "data"))

from sec_edgar_fetcher import SECEdgarFetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

fetcher = SECEdgarFetcher()

# 测试几只股票
test_symbols = ["AAPL", "MSFT", "TSLA"]

for symbol in test_symbols:
    print(f"\n{'='*50}")
    print(f"拉取 {symbol}...")
    data = fetcher.get_fundamentals(symbol)

    if data.get("revenue"):
        company = data.get('company_name', 'N/A').replace('\xa0', ' ')
        print(f"  公司: {company}")
        print(f"  营收: ${data['revenue']:,.0f}")
        net_income = data.get('net_income')
        print(f"  净利润: ${net_income:,.0f}" if net_income else "  净利润: N/A")
        eps = data.get('eps')
        print(f"  EPS: ${eps:.2f}" if eps else "  EPS: N/A")
        de = data.get('debt_to_equity')
        print(f"  负债率: {de:.1f}%" if de else "  负债率: N/A")
        cr = data.get('current_ratio')
        print(f"  流动比率: {cr:.2f}" if cr else "  流动比率: N/A")
        print(f"  来源: {data.get('source')}")
    else:
        print(f"  数据拉取失败或为空")
        print(f"  返回数据: {data}")
