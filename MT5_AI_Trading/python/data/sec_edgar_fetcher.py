"""
SEC EDGAR 数据拉取器
- 官方美国证券交易委员会数据
- 完全免费，10次/秒限流
- 数据来源：上市公司10-K/10-Q财报（XBRL格式）

依赖: requests, pandas
"""

import time
import logging
import datetime as dt
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

import requests
import pandas as pd

logger = logging.getLogger("sec_edgar")

# SEC EDGAR API 端点
SEC_BASE = "https://data.sec.gov"
SEC_SUBMISSIONS = f"{SEC_BASE}/submissions"
SEC_FACTS = f"{SEC_BASE}/api/xbrl/companyfacts"
SEC_CONCEPT = f"{SEC_BASE}/api/xbrl/companyconcept"

# User-Agent（SEC 要求）
HEADERS = {
    "User-Agent": "AIQuantTrading research@example.com",
    "Accept": "application/json",
}

# 股票代码 → CIK 映射（SEC 用 CIK 编号）
SYMBOL_TO_CIK = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
    "NVDA": "0001045810",
    "TSLA": "0001318605",
    "JPM": "0000019617",
    "BAC": "0000070858",
    "GS": "0000886982",
    "WFC": "0000072971",
    "C": "0000831001",
    "WMT": "0000104169",
    "COST": "0000909832",
    "HD": "0000354950",
    "PG": "0000080424",
    "KO": "0000021344",
    "PEP": "0000077476",
    "JNJ": "0000200406",
    "PFE": "0000078003",
    "UNH": "0000731766",
    "ABBV": "0001551152",
    "LLY": "0000059478",
    "XOM": "0000034088",
    "CVX": "0000093410",
    "BA": "0000012927",
    "CAT": "0000018230",
    "VZ": "0000732712",
    "DIS": "0001001039",
    "NFLX": "0001065280",
    "CRM": "0001108524",
}

# XBRL 概念映射（GAAP 标准标签）
GAAP_CONCEPTS = {
    "revenue": "Revenues",
    "net_income": "NetIncomeLoss",
    "total_assets": "Assets",
    "total_liabilities": "Liabilities",
    "stockholders_equity": "StockholdersEquity",
    "earnings_per_share": "EarningsPerShareBasic",
    "shares_outstanding": "CommonStockSharesOutstanding",
    "dividends_per_share": "CommonStockDividendsPerShareDeclaredPerShare",
    "current_assets": "AssetsCurrent",
    "current_liabilities": "LiabilitiesCurrent",
    "long_term_debt": "LongTermDebt",
    "cash": "CashAndCashEquivalentsAtCarryingValue",
}


class SECEdgarFetcher:
    """SEC EDGAR 数据拉取器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._last_request_time = 0

    def _rate_limit(self):
        """限流：确保每秒不超过10次请求"""
        elapsed = time.time() - self._last_request_time
        if elapsed < 0.11:  # 100ms 间隔 = 10次/秒
            time.sleep(0.11 - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """带限流和重试的GET请求"""
        for attempt in range(max_retries):
            self._rate_limit()
            try:
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    wait = 60 * (attempt + 1)
                    logger.warning(f"SEC EDGAR 限流，等待{wait}秒...")
                    time.sleep(wait)
                    continue
                logger.warning(f"SEC EDGAR 请求失败: {resp.status_code} {url}")
                return None
            except requests.exceptions.SSLError as e:
                wait = 5 * (attempt + 1)
                logger.warning(f"SSL 错误，{wait}秒后重试 ({attempt+1}/{max_retries}): {e}")
                time.sleep(wait)
            except requests.exceptions.ConnectionError as e:
                wait = 10 * (attempt + 1)
                logger.warning(f"连接错误，{wait}秒后重试 ({attempt+1}/{max_retries}): {e}")
                time.sleep(wait)
            except Exception as e:
                logger.error(f"SEC EDGAR 请求异常: {e}")
                return None
        return None

    def get_company_facts(self, symbol: str) -> Optional[Dict]:
        """获取公司全部 XBRL 财务数据"""
        cik = SYMBOL_TO_CIK.get(symbol.upper())
        if not cik:
            logger.warning(f"[{symbol}] 无 CIK 映射")
            return None

        url = f"{SEC_FACTS}/CIK{cik}.json"
        return self._get(url)

    def get_company_submissions(self, symbol: str) -> Optional[Dict]:
        """获取公司提交历史"""
        cik = SYMBOL_TO_CIK.get(symbol.upper())
        if not cik:
            return None

        url = f"{SEC_SUBMISSIONS}/CIK{cik}.json"
        return self._get(url)

    def get_financial_metric(self, symbol: str, concept: str) -> Optional[List[Dict]]:
        """获取单个财务指标的时间序列"""
        cik = SYMBOL_TO_CIK.get(symbol.upper())
        if not cik:
            return None

        gaap_name = GAAP_CONCEPTS.get(concept, concept)
        url = f"{SEC_CONCEPT}/CIK{cik}/us-gaap/{gaap_name}.json"
        data = self._get(url)

        if not data or "units" not in data:
            return None

        # 提取 USD 单位的数据
        usd_data = data["units"].get("USD", [])
        if not usd_data:
            # 尝试 shares 单位
            usd_data = data["units"].get("shares", [])

        return usd_data

    def get_latest_value(self, symbol: str, concept: str, period_type: str = "quarterly") -> Optional[float]:
        """获取最新财务指标值"""
        records = self.get_financial_metric(symbol, concept)
        if not records:
            return None

        # 过滤：只取 10-K（年报）或 10-Q（季报）
        if period_type == "quarterly":
            filtered = [r for r in records if r.get("form") in ("10-Q", "10-K")]
        else:
            filtered = [r for r in records if r.get("form") == "10-K"]

        if not filtered:
            filtered = records  # 备用：取全部

        # 按日期排序，取最新
        filtered.sort(key=lambda x: x.get("end", ""), reverse=True)

        if filtered:
            return filtered[0].get("val")
        return None

    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """获取完整基本面数据"""
        result = {
            "symbol": symbol,
            "source": "SEC_EDGAR",
            "fetched_at": dt.datetime.now().isoformat(),
        }

        facts = self.get_company_facts(symbol)
        if not facts:
            return result

        entity_name = facts.get("entityName", "")
        result["company_name"] = entity_name

        gaap = facts.get("facts", {}).get("us-gaap", {})

        # 提取关键指标
        def extract_latest(concept_key: str) -> Optional[float]:
            """从 XBRL 数据中提取最新值"""
            gaap_name = GAAP_CONCEPTS.get(concept_key)
            if not gaap_name or gaap_name not in gaap:
                return None

            entries = gaap[gaap_name].get("units", {}).get("USD", [])
            if not entries:
                entries = gaap[gaap_name].get("units", {}).get("shares", [])
            if not entries:
                return None

            # 只取最新季度数据（10-Q 或 10-K）
            quarterly = [e for e in entries if e.get("form") in ("10-Q", "10-K")]
            if not quarterly:
                quarterly = entries

            quarterly.sort(key=lambda x: x.get("end", ""), reverse=True)
            return quarterly[0].get("val") if quarterly else None

        # 营收
        revenue = extract_latest("revenue")
        result["revenue"] = revenue

        # 净利润
        net_income = extract_latest("net_income")
        result["net_income"] = net_income

        # 总资产
        total_assets = extract_latest("total_assets")
        result["total_assets"] = total_assets

        # 总负债
        total_liabilities = extract_latest("total_liabilities")
        result["total_liabilities"] = total_liabilities

        # 股东权益
        equity = extract_latest("stockholders_equity")
        result["stockholders_equity"] = equity

        # EPS
        eps = extract_latest("earnings_per_share")
        result["eps"] = eps

        # 流动比率
        current_assets = extract_latest("current_assets")
        current_liiv = extract_latest("current_liabilities")
        if current_assets and current_liiv and current_liiv > 0:
            result["current_ratio"] = current_assets / current_liiv

        # 负债率
        if total_liabilities and equity and equity > 0:
            result["debt_to_equity"] = (total_liabilities / equity) * 100

        # 股息
        dividends = extract_latest("dividends_per_share")
        result["dividends_per_share"] = dividends

        return result


def test_sec_edgar():
    """测试 SEC EDGAR 拉取"""
    fetcher = SECEdgarFetcher()

    test_symbols = ["AAPL", "MSFT", "TSLA"]

    for symbol in test_symbols:
        print(f"\n{'='*50}")
        print(f"拉取 {symbol}...")
        data = fetcher.get_fundamentals(symbol)

        if data.get("revenue"):
            print(f"  公司: {data.get('company_name', 'N/A')}")
            print(f"  营收: ${data['revenue']:,.0f}")
            print(f"  净利润: ${data.get('net_income', 0):,.0f}")
            print(f"  EPS: ${data.get('eps', 0):.2f}")
            print(f"  负债率: {data.get('debt_to_equity', 0):.1f}%")
            print(f"  流动比率: {data.get('current_ratio', 0):.2f}")
        else:
            print(f"  数据拉取失败或为空")

        time.sleep(0.5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_sec_edgar()
