"""
美股基本面 + 宏观指标数据管道
存储: data/fundamental_duckdb.db
表: equity_fundamentals, macro_indicators
更新: 每周末自动拉取
"""

import os
import sys
import json
import time
import logging
import datetime as dt
import warnings
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

import duckdb
import yfinance as yf
import pandas as pd
import numpy as np

# 抑制 yfinance 废弃警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# SEC EDGAR 数据源
try:
    from sec_edgar_fetcher import SECEdgarFetcher
except ImportError:
    from python.data.sec_edgar_fetcher import SECEdgarFetcher

# FRED API (免费，需申请key)
try:
    from fredapi import Fred
except ImportError:
    Fred = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/fundamental_pipeline.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("fundamental_pipeline")

# 路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "fundamental_duckdb.db"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 30只美股个股 (大盘蓝筹 + 科技 + 金融 + 消费 + 医疗)
EQUITY_UNIVERSE = [
    # 科技七巨头
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    # 金融
    "JPM", "BAC", "GS", "WFC", "C",
    # 消费
    "WMT", "COST", "HD", "PG", "KO", "PEP",
    # 医疗
    "JNJ", "PFE", "UNH", "ABBV", "LLY",
    # 工业/能源
    "XOM", "CVX", "BA", "CAT",
    # 通信/其他
    "VZ", "DIS", "NFLX", "CRM",
]

# FRED 宏观指标代码
FRED_SERIES = {
    "US10Y": "DGS10",           # 10年期国债收益率
    "US2Y": "DGS2",             # 2年期国债收益率
    "US3M": "DGS3MO",           # 3个月国债收益率
    "CPI_YoY": "CPIAUCSL",      # CPI (月度，需计算同比)
    "Core_PCE": "PCEPILFE",     # 核心PCE物价指数
    "Unemployment": "UNRATE",   # 失业率
    "Initial_Claims": "ICSA",   # 初请失业金人数
    "VIX": "VIXCLS",            # VIX收盘 (FRED上可能不完整，备用yfinance ^VIX)
    "Fed_Funds": "DFF",         # 联邦基金利率
    "GDP": "GDP",               # GDP (季度)
}


@dataclass
class EquityFundamental:
    symbol: str
    date: str
    pe: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    market_cap: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    insider_buying: Optional[float] = None
    institutional_ownership: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    fetched_at: Optional[str] = None


@dataclass
class MacroIndicator:
    date: str
    us10y: Optional[float] = None
    us2y: Optional[float] = None
    us3m: Optional[float] = None
    cpi_yoy: Optional[float] = None
    core_pce: Optional[float] = None
    unemployment: Optional[float] = None
    initial_claims: Optional[float] = None
    vix: Optional[float] = None
    fed_funds: Optional[float] = None
    gdp: Optional[float] = None
    fetched_at: Optional[str] = None


class DuckDBManager:
    """DuckDB 数据库管理器"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[duckdb.DuckDBPyConnection] = None

    def connect(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        return self

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def init_tables(self):
        """初始化表结构"""
        # 个股基本面表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS equity_fundamentals (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                pe DOUBLE,
                pb DOUBLE,
                ps DOUBLE,
                market_cap DOUBLE,
                revenue_growth DOUBLE,
                earnings_growth DOUBLE,
                debt_to_equity DOUBLE,
                current_ratio DOUBLE,
                insider_buying DOUBLE,
                institutional_ownership DOUBLE,
                dividend_yield DOUBLE,
                beta DOUBLE,
                sector VARCHAR,
                industry VARCHAR,
                fetched_at TIMESTAMP,
                PRIMARY KEY (symbol, date)
            )
        """)

        # 宏观指标表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS macro_indicators (
                date DATE NOT NULL PRIMARY KEY,
                us10y DOUBLE,
                us2y DOUBLE,
                us3m DOUBLE,
                cpi_yoy DOUBLE,
                core_pce DOUBLE,
                unemployment DOUBLE,
                initial_claims DOUBLE,
                vix DOUBLE,
                fed_funds DOUBLE,
                gdp DOUBLE,
                fetched_at TIMESTAMP
            )
        """)

        # 创建索引加速查询
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_eq_date ON equity_fundamentals(date);
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_eq_symbol ON equity_fundamentals(symbol);
        """)
        logger.info("DuckDB 表初始化完成")

    def upsert_equity(self, records: List[EquityFundamental]):
        """插入或更新个股基本面数据"""
        if not records:
            return
        df = pd.DataFrame([asdict(r) for r in records])
        df["date"] = pd.to_datetime(df["date"]).dt.date
        # 确保 fetched_at 有值
        if "fetched_at" not in df.columns or df["fetched_at"].isna().all():
            df["fetched_at"] = pd.Timestamp.now()

        # 只保留表存在的列
        table_cols = [
            "symbol", "date", "pe", "pb", "ps", "market_cap",
            "revenue_growth", "earnings_growth", "debt_to_equity", "current_ratio",
            "insider_buying", "institutional_ownership", "dividend_yield", "beta",
            "sector", "industry", "fetched_at"
        ]
        df = df[[c for c in table_cols if c in df.columns]]

        # 先删除已存在的记录，再插入
        for _, row in df.iterrows():
            self.conn.execute(
                "DELETE FROM equity_fundamentals WHERE symbol = ? AND date = ?",
                [row["symbol"], row["date"]],
            )

        self.conn.register("temp_equity", df)
        # 显式指定列，避免列数不匹配
        cols = ", ".join(df.columns)
        self.conn.execute(f"""
            INSERT INTO equity_fundamentals ({cols})
            SELECT {cols} FROM temp_equity
        """)
        self.conn.unregister("temp_equity")
        logger.info(f"Upserted {len(records)} equity records")

    def upsert_macro(self, records: List[MacroIndicator]):
        """插入或更新宏观指标数据"""
        if not records:
            return
        df = pd.DataFrame([asdict(r) for r in records])
        df["date"] = pd.to_datetime(df["date"]).dt.date

        for _, row in df.iterrows():
            self.conn.execute(
                "DELETE FROM macro_indicators WHERE date = ?",
                [row["date"]],
            )

        self.conn.register("temp_macro", df)
        self.conn.execute("""
            INSERT INTO macro_indicators
            SELECT * FROM temp_macro
        """)
        self.conn.unregister("temp_macro")
        logger.info(f"Upserted {len(records)} macro records")

    def get_latest_equity_date(self, symbol: str) -> Optional[dt.date]:
        """获取某只股票最新数据日期"""
        result = self.conn.execute(
            "SELECT MAX(date) FROM equity_fundamentals WHERE symbol = ?",
            [symbol],
        ).fetchone()
        return result[0] if result and result[0] else None

    def get_latest_macro_date(self) -> Optional[dt.date]:
        """获取宏观指标最新日期"""
        result = self.conn.execute(
            "SELECT MAX(date) FROM macro_indicators"
        ).fetchone()
        return result[0] if result and result[0] else None

    def query_equity(self, symbol: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
        """查询个股基本面"""
        sql = "SELECT * FROM equity_fundamentals WHERE 1=1"
        params = []
        if symbol:
            sql += " AND symbol = ?"
            params.append(symbol)
        if start:
            sql += " AND date >= ?"
            params.append(start)
        if end:
            sql += " AND date <= ?"
            params.append(end)
        sql += " ORDER BY date DESC"
        return self.conn.execute(sql, params).fetchdf()

    def query_macro(self, start: Optional[str] = None, end: Optional[str] = None):
        """查询宏观指标"""
        sql = "SELECT * FROM macro_indicators WHERE 1=1"
        params = []
        if start:
            sql += " AND date >= ?"
            params.append(start)
        if end:
            sql += " AND date <= ?"
            params.append(end)
        sql += " ORDER BY date DESC"
        return self.conn.execute(sql, params).fetchdf()


class YFinanceFetcher:
    """yfinance 数据拉取器"""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or DATA_DIR / "fundamental_cache"
        self.cache_dir.mkdir(exist_ok=True)

    def fetch_equity_batch(self, symbols: List[str]) -> List[EquityFundamental]:
        """批量拉取多只股票基本面，减少请求次数避免限流"""
        records = []
        # yfinance 批量 info 接口
        tickers_obj = yf.Tickers(" ".join(symbols))
        time.sleep(2)  # 初始等待

        for symbol in symbols:
            try:
                time.sleep(0.8)  # 每只间隔 0.8 秒
                ticker = tickers_obj.tickers.get(symbol)
                if not ticker:
                    ticker = yf.Ticker(symbol)
                    time.sleep(1)

                info = ticker.info
                if not info:
                    logger.warning(f"[{symbol}] 无 info 数据")
                    continue

                # 财务数据 (季度)
                revenue_growth = None
                earnings_growth = None
                try:
                    income_q = ticker.quarterly_income_stmt
                    if income_q is not None and not income_q.empty:
                        if "Total Revenue" in income_q.index:
                            rev = income_q.loc["Total Revenue"]
                            rev_vals = rev.dropna().values
                            if len(rev_vals) >= 2:
                                revenue_growth = float((rev_vals[0] - rev_vals[1]) / abs(rev_vals[1]))
                        if "Net Income" in income_q.index:
                            ni = income_q.loc["Net Income"]
                            ni_vals = ni.dropna().values
                            if len(ni_vals) >= 2:
                                earnings_growth = float((ni_vals[0] - ni_vals[1]) / abs(ni_vals[1]))
                except Exception as e:
                    logger.debug(f"[{symbol}] 财务数据错误: {e}")

                # institutional
                institutional_ownership = None
                try:
                    holders = ticker.institutional_holders
                    if holders is not None and not holders.empty:
                        total_inst = holders["Shares"].sum() if "Shares" in holders.columns else None
                        so = info.get("sharesOutstanding")
                        if total_inst and so:
                            institutional_ownership = float(total_inst / so)
                except Exception:
                    pass

                record = EquityFundamental(
                    symbol=symbol,
                    date=dt.date.today().isoformat(),
                    pe=info.get("trailingPE") or info.get("forwardPE"),
                    pb=info.get("priceToBook"),
                    ps=info.get("priceToSalesTrailing12Months"),
                    market_cap=info.get("marketCap"),
                    revenue_growth=revenue_growth,
                    earnings_growth=earnings_growth,
                    debt_to_equity=info.get("debtToEquity"),
                    current_ratio=info.get("currentRatio"),
                    insider_buying=None,
                    institutional_ownership=institutional_ownership,
                    dividend_yield=info.get("dividendYield"),
                    beta=info.get("beta"),
                    sector=info.get("sector"),
                    industry=info.get("industry"),
                    fetched_at=dt.datetime.now().isoformat(),
                )
                logger.info(f"[{symbol}] PE={record.pe}, MarketCap={record.market_cap}")
                records.append(record)

            except Exception as e:
                logger.error(f"[{symbol}] 拉取失败: {e}")

        return records

    def fetch_equity(self, symbol: str, max_retries: int = 3) -> Optional[EquityFundamental]:
        """单只股票拉取（兼容旧接口）"""
        results = self.fetch_equity_batch([symbol])
        return results[0] if results else None

    def fetch_vix(self) -> Optional[float]:
        """从 yfinance 拉 VIX"""
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="5d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception as e:
            logger.warning(f"VIX拉取失败: {e}")
        return None


class MultiSourceFetcher:
    """多数据源拉取器 - SEC EDGAR (主) + yfinance (备用)"""

    def __init__(self):
        self.sec = SECEdgarFetcher()
        self.yf = YFinanceFetcher()

    def fetch_equity(self, symbol: str) -> Optional[EquityFundamental]:
        """拉取单只股票基本面 - SEC EDGAR 优先，yfinance 备用"""
        record = None

        # 方案1: SEC EDGAR
        try:
            sec_data = self.sec.get_fundamentals(symbol)
            if sec_data and sec_data.get("revenue"):
                logger.info(f"[{symbol}] SEC EDGAR 数据获取成功")
                record = self._convert_sec_to_equity(symbol, sec_data)
        except Exception as e:
            logger.warning(f"[{symbol}] SEC EDGAR 失败: {e}")

        # 方案2: yfinance 备用
        if not record:
            logger.info(f"[{symbol}] 尝试 yfinance 备用...")
            try:
                yf_records = self.yf.fetch_equity_batch([symbol])
                if yf_records:
                    record = yf_records[0]
                    logger.info(f"[{symbol}] yfinance 数据获取成功")
            except Exception as e:
                logger.error(f"[{symbol}] yfinance 也失败: {e}")

        return record

    def fetch_equity_batch(self, symbols: List[str]) -> List[EquityFundamental]:
        """批量拉取 - SEC EDGAR 优先"""
        records = []
        yf_fallback = []

        for symbol in symbols:
            try:
                # 先试 SEC EDGAR
                sec_data = self.sec.get_fundamentals(symbol)
                if sec_data and sec_data.get("revenue"):
                    record = self._convert_sec_to_equity(symbol, sec_data)
                    if record:
                        records.append(record)
                        continue

                # SEC 失败，加入 yfinance 备用列表
                yf_fallback.append(symbol)

            except Exception as e:
                logger.warning(f"[{symbol}] SEC EDGAR 失败: {e}")
                yf_fallback.append(symbol)

            time.sleep(0.15)  # SEC 限流保护

        # yfinance 备用
        if yf_fallback:
            logger.info(f"SEC EDGAR 失败 {len(yf_fallback)} 只，使用 yfinance 备用")
            yf_records = self.yf.fetch_equity_batch(yf_fallback)
            records.extend(yf_records)

        return records

    def _convert_sec_to_equity(self, symbol: str, sec_data: Dict) -> Optional[EquityFundamental]:
        """将 SEC EDGAR 数据转换为 EquityFundamental 格式"""
        try:
            revenue = sec_data.get("revenue")
            net_income = sec_data.get("net_income")
            equity = sec_data.get("stockholders_equity")

            # 计算 PE（需要当前价格，SEC没有）
            # SEC EDGAR 不直接提供 PE/PB，这些需要实时价格
            # 但我们可以计算其他指标

            return EquityFundamental(
                symbol=symbol,
                date=dt.date.today().isoformat(),
                pe=None,  # 需要实时价格
                pb=None,  # 需要实时价格
                ps=None,
                market_cap=None,
                revenue_growth=None,  # 需要历史数据对比
                earnings_growth=None,
                debt_to_equity=sec_data.get("debt_to_equity"),
                current_ratio=sec_data.get("current_ratio"),
                insider_buying=None,
                institutional_ownership=None,
                dividend_yield=sec_data.get("dividends_per_share"),
                beta=None,
                sector=None,
                industry=None,
                fetched_at=dt.datetime.now().isoformat(),
            )
        except Exception as e:
            logger.error(f"[{symbol}] SEC 数据转换失败: {e}")
            return None


class FREDFetcher:
    """FRED 宏观数据拉取器"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FRED_API_KEY")
        self.fred = Fred(api_key=self.api_key) if Fred and self.api_key else None
        if not self.fred:
            logger.warning("FRED API key 未配置，宏观数据将使用 yfinance 备用方案")

    def fetch_all(self, start_date: Optional[str] = None) -> List[MacroIndicator]:
        """拉取所有宏观指标"""
        if not self.fred:
            return self._fetch_macro_from_yfinance(start_date)

        start = start_date or "2020-01-01"
        end = dt.date.today().isoformat()

        data_dict: Dict[str, pd.Series] = {}

        for name, series_id in FRED_SERIES.items():
            try:
                series = self.fred.get_series(series_id, observation_start=start, observation_end=end)
                if series is not None and not series.empty:
                    data_dict[name] = series
                    logger.info(f"[FRED] {name} ({series_id}): {len(series)} 条记录")
                else:
                    logger.warning(f"[FRED] {name} ({series_id}) 无数据")
            except Exception as e:
                logger.error(f"[FRED] {name} 拉取失败: {e}")

        # CPI 需要计算同比
        if "CPI_YoY" in data_dict:
            cpi = data_dict["CPI_YoY"]
            data_dict["CPI_YoY"] = cpi.pct_change(periods=12) * 100

        # 合并所有日期
        all_dates = set()
        for s in data_dict.values():
            all_dates.update(s.index)

        records = []
        for d in sorted(all_dates):
            d_str = d.strftime("%Y-%m-%d") if isinstance(d, (pd.Timestamp, dt.datetime)) else str(d)
            r = MacroIndicator(
                date=d_str,
                us10y=_safe_get(data_dict, "US10Y", d),
                us2y=_safe_get(data_dict, "US2Y", d),
                us3m=_safe_get(data_dict, "US3M", d),
                cpi_yoy=_safe_get(data_dict, "CPI_YoY", d),
                core_pce=_safe_get(data_dict, "Core_PCE", d),
                unemployment=_safe_get(data_dict, "Unemployment", d),
                initial_claims=_safe_get(data_dict, "Initial_Claims", d),
                vix=_safe_get(data_dict, "VIX", d),
                fed_funds=_safe_get(data_dict, "Fed_Funds", d),
                gdp=_safe_get(data_dict, "GDP", d),
                fetched_at=dt.datetime.now().isoformat(),
            )
            records.append(r)

        return records

    def _fetch_macro_from_yfinance(self, start_date: Optional[str] = None) -> List[MacroIndicator]:
        """无 FRED key 时的备用方案：用 yfinance 拉 ^TNX, ^FVX, ^IRX 等"""
        logger.info("使用 yfinance 备用方案拉宏观数据")
        start = start_date or "2020-01-01"

        tickers = {
            "US10Y": "^TNX",   # 10年期
            "US2Y": "^FVX",    # 5年期 (近似)
            "US3M": "^IRX",    # 13周国库券
        }

        data_dict = {}
        for name, tkr in tickers.items():
            try:
                hist = yf.Ticker(tkr).history(start=start)
                if not hist.empty:
                    data_dict[name] = hist["Close"]
            except Exception as e:
                logger.warning(f"备用方案 {name} 失败: {e}")

        # VIX
        vix_val = YFinanceFetcher().fetch_vix()

        # 合并
        all_dates = set()
        for s in data_dict.values():
            all_dates.update(s.index)

        records = []
        for d in sorted(all_dates):
            d_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
            records.append(MacroIndicator(
                date=d_str,
                us10y=_safe_get(data_dict, "US10Y", d),
                us2y=_safe_get(data_dict, "US2Y", d),
                us3m=_safe_get(data_dict, "US3M", d),
                vix=vix_val if d == max(all_dates) else None,
                fetched_at=dt.datetime.now().isoformat(),
            ))

        return records


def _safe_get(data_dict: Dict, key: str, date) -> Optional[float]:
    """安全获取 Series 值"""
    if key not in data_dict:
        return None
    try:
        val = data_dict[key].get(date)
        if pd.isna(val):
            return None
        return float(val)
    except Exception:
        return None


class FundamentalPipeline:
    """主管道控制器 - 多数据源版本"""

    def __init__(self):
        self.db = DuckDBManager(DB_PATH)
        self.fetcher = MultiSourceFetcher()  # SEC EDGAR + yfinance
        self.fred_fetcher = FREDFetcher()

    def run_equity(self, symbols: Optional[List[str]] = None, force: bool = False):
        """执行个股基本面拉取（批量模式）"""
        symbols = symbols or EQUITY_UNIVERSE

        # 过滤已是最新的
        need_fetch = []
        with self.db:
            for sym in symbols:
                if not force:
                    latest = self.db.get_latest_equity_date(sym)
                    if latest and (dt.date.today() - latest).days < 3:
                        logger.info(f"[{sym}] 数据已是最新 ({latest}), 跳过")
                        continue
                need_fetch.append(sym)

        if not need_fetch:
            logger.info("所有个股数据已是最新")
            return []

        # 批量拉取
        records = self.fetcher.fetch_equity_batch(need_fetch)

        with self.db:
            if records:
                self.db.upsert_equity(records)

        logger.info(f"个股基本面更新完成: {len(records)}/{len(need_fetch)} 条")
        return records

    def run_macro(self, force: bool = False):
        """执行宏观指标拉取"""
        with self.db:
            if not force:
                latest = self.db.get_latest_macro_date()
                if latest and (dt.date.today() - latest).days < 3:
                    logger.info(f"宏观数据已是最新 ({latest}), 跳过")
                    return []

            records = self.fred_fetcher.fetch_all()
            if records:
                self.db.upsert_macro(records)

        logger.info(f"宏观指标更新完成: {len(records)} 条")
        return records

    def run_full(self, symbols: Optional[List[str]] = None, force: bool = False):
        """全量更新"""
        logger.info("=" * 50)
        logger.info("开始全量数据更新")
        logger.info("=" * 50)

        # 初始化表
        with self.db:
            self.db.init_tables()

        # 个股
        equity_records = self.run_equity(symbols, force)

        # 宏观
        macro_records = self.run_macro(force)

        # 汇总
        logger.info("=" * 50)
        logger.info("更新汇总:")
        logger.info(f"  个股: {len(equity_records)} 条")
        logger.info(f"  宏观: {len(macro_records)} 条")
        logger.info("=" * 50)

        return {
            "equity_count": len(equity_records),
            "macro_count": len(macro_records),
        }

    def get_summary(self) -> Dict:
        """获取数据库汇总信息"""
        with self.db:
            eq_count = self.db.conn.execute("SELECT COUNT(*) FROM equity_fundamentals").fetchone()[0]
            macro_count = self.db.conn.execute("SELECT COUNT(*) FROM macro_indicators").fetchone()[0]
            eq_symbols = self.db.conn.execute("SELECT COUNT(DISTINCT symbol) FROM equity_fundamentals").fetchone()[0]
            eq_latest = self.db.conn.execute("SELECT MAX(date) FROM equity_fundamentals").fetchone()[0]
            macro_latest = self.db.conn.execute("SELECT MAX(date) FROM macro_indicators").fetchone()[0]

        return {
            "equity_records": eq_count,
            "equity_symbols": eq_symbols,
            "equity_latest": str(eq_latest) if eq_latest else None,
            "macro_records": macro_count,
            "macro_latest": str(macro_latest) if macro_latest else None,
        }


# ---------- 定时调度 ----------

def should_run_weekend() -> bool:
    """检查是否是周末（周五收盘后或周六）"""
    now = dt.datetime.now()
    return now.weekday() in [4, 5]  # 周五、周六


def scheduled_update():
    """定时更新入口"""
    logger.info("定时任务触发")
    pipeline = FundamentalPipeline()
    pipeline.run_full()
    summary = pipeline.get_summary()
    logger.info(f"定时更新完成: {json.dumps(summary, indent=2, default=str)}")


# ---------- CLI ----------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="美股基本面 + 宏观指标数据管道")
    parser.add_argument("--symbols", nargs="+", help="指定股票代码")
    parser.add_argument("--force", action="store_true", help="强制更新")
    parser.add_argument("--equity-only", action="store_true", help="仅更新个股")
    parser.add_argument("--macro-only", action="store_true", help="仅更新宏观")
    parser.add_argument("--summary", action="store_true", help="显示数据库汇总")
    parser.add_argument("--schedule", action="store_true", help="启动定时调度(每周末)")
    parser.add_argument("--query-eq", type=str, help="查询个股数据 (symbol)")
    parser.add_argument("--query-macro", action="store_true", help="查询宏观数据")
    args = parser.parse_args()

    pipeline = FundamentalPipeline()

    if args.summary:
        print(json.dumps(pipeline.get_summary(), indent=2, default=str))

    elif args.query_eq:
        with pipeline.db:
            df = pipeline.db.query_equity(symbol=args.query_eq)
            print(df.to_string())

    elif args.query_macro:
        with pipeline.db:
            df = pipeline.db.query_macro()
            print(df.to_string())

    elif args.schedule:
        import schedule
        import time

        # 每周五 21:00 (美股收盘后)
        schedule.every().friday.at("21:00").do(scheduled_update)
        logger.info("定时调度已启动，每周五 21:00 更新")

        while True:
            schedule.run_pending()
            time.sleep(60)

    elif args.equity_only:
        pipeline.run_equity(args.symbols, force=args.force)

    elif args.macro_only:
        pipeline.run_macro(force=args.force)

    else:
        # 默认全量更新
        pipeline.run_full(args.symbols, force=args.force)
        print(json.dumps(pipeline.get_summary(), indent=2, default=str))
