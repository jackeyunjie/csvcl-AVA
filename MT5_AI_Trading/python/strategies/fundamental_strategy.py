"""
基本面策略引擎 - 基于美股基本面数据生成交易信号
通过 ZeroMQ 发送给 MT5 EA 执行

信号逻辑:
- 价值型: PE < 行业均值 && PB < 3 && 负债率合理 → BUY
- 成长型: 收入增长 > 20% && 盈利增长 > 15% → BUY
- 宏观避险: VIX > 30 || 收益率曲线倒挂 → 减仓/观望
- 分红型: 股息率 > 3% && 派息稳定 → BUY
"""

import os
import sys
import json
import time
import logging
import datetime as dt
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import duckdb
import pandas as pd
import numpy as np

# 添加项目路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "python" / "core"))

from mt5_bridge import MT5Bridge, OrderResult

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/fundamental_strategy.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("fundamental_strategy")

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "fundamental_duckdb.db"


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    REDUCE = "REDUCE"


@dataclass
class FundamentalSignal:
    """基本面交易信号"""
    symbol: str
    signal: SignalType
    score: float          # 信号强度 0-100
    reason: str           # 信号原因
    pe: Optional[float] = None
    pb: Optional[float] = None
    market_cap: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    debt_to_equity: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    macro_vix: Optional[float] = None
    macro_us10y: Optional[float] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = dt.datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "signal": self.signal.value,
            "score": self.score,
            "reason": self.reason,
            "pe": self.pe,
            "pb": self.pb,
            "market_cap": self.market_cap,
            "revenue_growth": self.revenue_growth,
            "earnings_growth": self.earnings_growth,
            "debt_to_equity": self.debt_to_equity,
            "dividend_yield": self.dividend_yield,
            "beta": self.beta,
            "macro_vix": self.macro_vix,
            "macro_us10y": self.macro_us10y,
            "timestamp": self.timestamp,
        }


class FundamentalAnalyzer:
    """基本面分析器"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[duckdb.DuckDBPyConnection] = None

    def connect(self):
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

    def get_latest_equity_data(self) -> pd.DataFrame:
        """获取最新个股基本面数据"""
        sql = """
            SELECT *
            FROM equity_fundamentals
            WHERE date = (SELECT MAX(date) FROM equity_fundamentals)
        """
        return self.conn.execute(sql).fetchdf()

    def get_latest_macro(self) -> pd.DataFrame:
        """获取最新宏观指标"""
        sql = """
            SELECT *
            FROM macro_indicators
            ORDER BY date DESC
            LIMIT 1
        """
        return self.conn.execute(sql).fetchdf()

    def analyze(self, symbol: str) -> FundamentalSignal:
        """分析单只股票，生成交易信号"""
        # 获取个股数据
        df_eq = self.conn.execute(
            "SELECT * FROM equity_fundamentals WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            [symbol],
        ).fetchdf()

        if df_eq.empty:
            return FundamentalSignal(
                symbol=symbol,
                signal=SignalType.HOLD,
                score=0,
                reason="无基本面数据",
            )

        row = df_eq.iloc[0]

        # 获取宏观数据
        df_macro = self.conn.execute(
            "SELECT * FROM macro_indicators ORDER BY date DESC LIMIT 1"
        ).fetchdf()

        macro_vix = df_macro["vix"].iloc[0] if not df_macro.empty and "vix" in df_macro.columns else None
        macro_us10y = df_macro["us10y"].iloc[0] if not df_macro.empty and "us10y" in df_macro.columns else None
        macro_us2y = df_macro["us2y"].iloc[0] if not df_macro.empty and "us2y" in df_macro.columns else None

        # 信号评分系统
        score = 0
        reasons = []

        pe = row.get("pe")
        pb = row.get("pb")
        ps = row.get("ps")
        rev_growth = row.get("revenue_growth")
        earn_growth = row.get("earnings_growth")
        de = row.get("debt_to_equity")
        div_yield = row.get("dividend_yield")
        beta = row.get("beta")
        market_cap = row.get("market_cap")

        # 行业估值中位数（用于相对估值）
        sector_pe_median = {
            "Technology": 35, "Consumer Cyclical": 25, "Financial Services": 12,
            "Consumer Defensive": 22, "Healthcare": 25, "Energy": 12,
            "Industrials": 20, "Communication Services": 30,
        }
        sector = row.get("sector", "")
        median_pe = sector_pe_median.get(sector, 20)

        # 1. 估值评分 (PE/PB) - 相对于行业中位数
        if pe is not None and pe > 0:
            if pe < median_pe * 0.7:  # 低于行业70%
                score += 25
                reasons.append(f"低PE({pe:.1f}<{median_pe*0.7:.0f})")
            elif pe < median_pe:  # 低于行业中位数
                score += 15
                reasons.append(f"合理PE({pe:.1f}<{median_pe})")
            elif pe < median_pe * 1.5:  # 高于行业但不离谱
                score += 5
                reasons.append(f"PE({pe:.1f})偏高")
            else:  # 远高于行业
                score -= 10
                reasons.append(f"高PE({pe:.1f}>{median_pe*1.5:.0f})")

        if pb is not None and pb > 0:
            if pb < 3:
                score += 10
                reasons.append(f"低PB({pb:.1f})")
            elif pb < 10:
                score += 5
                reasons.append(f"PB({pb:.1f})")
            elif pb > 20:
                score -= 5
                reasons.append(f"高PB({pb:.1f})")

        # 2. 成长性评分
        if rev_growth is not None:
            if rev_growth > 0.20:
                score += 20
                reasons.append(f"高营收增长({rev_growth*100:.0f}%)")
            elif rev_growth > 0.10:
                score += 10
                reasons.append(f"营收增长({rev_growth*100:.0f}%)")
            elif rev_growth < -0.10:
                score -= 15
                reasons.append(f"营收下滑({rev_growth*100:.0f}%)")

        if earn_growth is not None:
            if earn_growth > 0.30:
                score += 15
                reasons.append(f"高盈利增长({earn_growth*100:.0f}%)")
            elif earn_growth < -0.20:
                score -= 15
                reasons.append(f"盈利下滑({earn_growth*100:.0f}%)")

        # 3. 财务健康
        if de is not None:
            if de < 50:
                score += 10
                reasons.append("低负债")
            elif de > 200:
                score -= 10
                reasons.append(f"高负债({de:.0f}%)")

        # 4. 分红
        if div_yield is not None and div_yield > 0:
            if div_yield > 0.03:
                score += 10
                reasons.append(f"高分红({div_yield*100:.1f}%)")

        # 5. 大盘股加分（稳定性）
        if market_cap is not None and market_cap > 500e9:
            score += 5
            reasons.append("大盘股")

        # 6. 宏观环境
        if macro_vix is not None and macro_vix > 30:
            score -= 15
            reasons.append(f"高波动(VIX={macro_vix:.1f})")

        if macro_us10y is not None and macro_us2y is not None:
            if macro_us2y > macro_us10y:
                score -= 10
                reasons.append("收益率曲线倒挂")

        # 确定信号（调整阈值适配当前市场）
        if score >= 25:
            signal = SignalType.BUY
        elif score <= -20:
            signal = SignalType.SELL
        elif score <= 0:
            signal = SignalType.REDUCE
        else:
            signal = SignalType.HOLD

        return FundamentalSignal(
            symbol=symbol,
            signal=signal,
            score=max(0, min(100, score + 50)),  # 归一化到 0-100
            reason="; ".join(reasons) if reasons else "中性",
            pe=pe,
            pb=pb,
            market_cap=market_cap,
            revenue_growth=rev_growth,
            earnings_growth=earn_growth,
            debt_to_equity=de,
            dividend_yield=div_yield,
            beta=beta,
            macro_vix=macro_vix,
            macro_us10y=macro_us10y,
        )

    def analyze_all(self, symbols: Optional[List[str]] = None) -> List[FundamentalSignal]:
        """分析所有股票"""
        if symbols is None:
            df = self.conn.execute(
                "SELECT DISTINCT symbol FROM equity_fundamentals"
            ).fetchdf()
            symbols = df["symbol"].tolist()

        signals = []
        for sym in symbols:
            try:
                sig = self.analyze(sym)
                signals.append(sig)
            except Exception as e:
                logger.error(f"[{sym}] 分析失败: {e}")

        return signals


class FundamentalStrategyExecutor:
    """基本面策略执行器 - 连接MT5 EA (AVATRADE)"""

    def __init__(
        self,
        mt5_host: str = "localhost",
        pub_port: int = 5565,
        req_port: int = 5566,
        db_path: Path = DB_PATH,
        dry_run: bool = True,
    ):
        self.analyzer = FundamentalAnalyzer(db_path)
        self.bridge = MT5Bridge(mt5_host, pub_port, req_port)
        self.dry_run = dry_run
        self.signals_history: List[Dict] = []

    def start(self):
        """启动策略"""
        logger.info("基本面策略启动")
        self.bridge.connect()

    def stop(self):
        """停止策略"""
        logger.info("基本面策略停止")
        self.bridge.disconnect()

    def generate_signals(self) -> List[FundamentalSignal]:
        """生成交易信号"""
        with self.analyzer:
            signals = self.analyzer.analyze_all()

        # 过滤出 BUY/SELL 信号
        active_signals = [s for s in signals if s.signal in (SignalType.BUY, SignalType.SELL)]
        active_signals.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"生成 {len(active_signals)} 个交易信号")
        for s in active_signals[:10]:
            logger.info(f"  {s.symbol}: {s.signal.value} (score={s.score:.0f}) - {s.reason}")

        return active_signals

    def execute_signal(self, signal: FundamentalSignal, volume: float = 0.01):
        """执行单个信号"""
        if self.dry_run:
            logger.info(f"[DRY-RUN] {signal.symbol} {signal.signal.value} vol={volume}")
            return None

        if signal.signal == SignalType.BUY:
            action = "BUY"
        elif signal.signal == SignalType.SELL:
            action = "SELL"
        else:
            return None

        # 构建指令
        order = {
            "type": "order",
            "symbol": signal.symbol,
            "action": action,
            "volume": volume,
            "comment": f"Fundamental|score={signal.score:.0f}",
        }

        try:
            result = self.bridge.send_order(order)
            logger.info(f"[{signal.symbol}] 订单结果: {result}")
            return result
        except Exception as e:
            logger.error(f"[{signal.symbol}] 下单失败: {e}")
            return None

    def run_once(self, top_n: int = 5, volume: float = 0.01):
        """运行一次策略循环"""
        signals = self.generate_signals()

        # 只执行前 N 个最强信号
        for sig in signals[:top_n]:
            self.execute_signal(sig, volume)
            time.sleep(0.5)

        # 保存信号历史
        self.signals_history.extend([s.to_dict() for s in signals])

        return signals

    def save_signals(self, path: Optional[Path] = None):
        """保存信号历史"""
        path = path or DATA_DIR / "fundamental_signals.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.signals_history, f, indent=2, default=str)
        logger.info(f"信号历史已保存: {path}")


# ---------- CLI ----------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="基本面策略引擎")
    parser.add_argument("--analyze", type=str, help="分析单只股票")
    parser.add_argument("--analyze-all", action="store_true", help="分析所有股票")
    parser.add_argument("--execute", action="store_true", help="连接MT5执行交易")
    parser.add_argument("--top-n", type=int, default=5, help="执行前N个信号")
    parser.add_argument("--volume", type=float, default=0.01, help="交易量")
    parser.add_argument("--live", action="store_true", help="实盘模式(默认Dry-Run)")
    parser.add_argument("--host", default="localhost", help="MT5主机")
    parser.add_argument("--pub-port", type=int, default=5565, help="MT5 PUB端口")
    parser.add_argument("--req-port", type=int, default=5566, help="MT5 REQ端口")
    args = parser.parse_args()

    if args.analyze:
        with FundamentalAnalyzer() as analyzer:
            sig = analyzer.analyze(args.analyze)
            print(json.dumps(sig.to_dict(), indent=2, default=str))

    elif args.analyze_all:
        with FundamentalAnalyzer() as analyzer:
            signals = analyzer.analyze_all()
            for s in signals:
                if s.signal in (SignalType.BUY, SignalType.SELL):
                    print(f"{s.symbol}: {s.signal.value} (score={s.score:.0f}) - {s.reason}")

    elif args.execute:
        executor = FundamentalStrategyExecutor(
            mt5_host=args.host,
            req_port=args.req_port,
            dry_run=not args.live,
        )
        executor.start()
        try:
            executor.run_once(top_n=args.top_n, volume=args.volume)
            executor.save_signals()
        finally:
            executor.stop()

    else:
        # 默认：分析所有并输出
        with FundamentalAnalyzer() as analyzer:
            signals = analyzer.analyze_all()
            buy_signals = [s for s in signals if s.signal == SignalType.BUY]
            sell_signals = [s for s in signals if s.signal == SignalType.SELL]

            print(f"\n=== 基本面信号汇总 ===")
            print(f"BUY: {len(buy_signals)}")
            print(f"SELL: {len(sell_signals)}")
            print(f"\n--- TOP BUY ---")
            for s in sorted(buy_signals, key=lambda x: x.score, reverse=True)[:10]:
                print(f"  {s.symbol}: score={s.score:.0f}, PE={s.pe}, {s.reason}")
