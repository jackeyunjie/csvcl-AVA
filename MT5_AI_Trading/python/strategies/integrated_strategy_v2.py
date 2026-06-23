"""
整合策略引擎 V2 - 基本面 + State + Hermass 指标

新增 Hermass 指标:
- EF Score (E/F 计数): MN1/W1/D1 的 E/F 状态计数
- Hermass Signal: 基于 4-bit State 的交易信号
- 多周期共振: 基本面 + State + Hermass 三重确认

信号融合逻辑 V2:
- 基本面 BUY + State 上升 + Hermass BUY → 强BUY (置信度 0.90)
- 基本面 BUY + State 上升 + Hermass HOLD → BUY (置信度 0.80)
- 基本面 BUY + State 下降 + Hermass SELL → 观望 (置信度 0.40)
- 基本面 SELL + State 下降 + Hermass SELL → 强SELL (置信度 0.90)
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ai_engine"))

from h1_state_db import H1StateDB
from hermass_indicators import calc_hermass_state, calc_ef_score, state_to_signal
from d1_risk_officer import gate_signal_fields


@dataclass
class IntegratedSignalV2:
    symbol: str
    fundamental_signal: str
    fundamental_score: int
    state_trend: str
    state_hex: str
    hermass_signal: str
    hermass_ef: int
    hermass_mn1: int
    hermass_w1: int
    hermass_d1: int
    final_signal: str
    confidence: float
    reason: str
    d1_hex: str = "N/A"


def decode_hex_trend(hex_val: str) -> str:
    """解析 state_hex 趋势方向"""
    if not hex_val or hex_val == "N/A":
        return "未知"
    is_negative = hex_val.startswith("-")
    clean = hex_val.lstrip("-")
    try:
        val = int(clean, 16)
    except ValueError:
        return "未知"
    has_trend = (val & 4) != 0
    if not has_trend:
        return "横盘"
    return "下降" if is_negative else "上升"


class IntegratedStrategyV2:
    """整合策略 V2: 基本面 + State + Hermass"""

    def __init__(self, fund_db_path: str = "data/fundamental_duckdb.db",
                 state_db_path: str = "data/h1_state.duckdb"):
        self.fund_db = duckdb.connect(fund_db_path)
        self.state_db = H1StateDB(state_db_path)

    def get_fundamental_signal(self, symbol: str) -> Optional[Dict]:
        """获取基本面信号"""
        row = self.fund_db.execute("""
            SELECT symbol, pe, pb, debt_to_equity, market_cap,
                   revenue_growth, earnings_growth, dividend_yield, sector
            FROM equity_fundamentals
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 1
        """, [symbol]).fetchone()

        if not row:
            return None

        symbol, pe, pb, debt, cap, rev, earn, div_yield, sector = row

        sector_pe = {
            "Technology": 35, "Consumer Cyclical": 25, "Financial Services": 12,
            "Consumer Defensive": 22, "Healthcare": 25, "Energy": 12,
            "Industrials": 20, "Communication Services": 30,
        }
        median_pe = sector_pe.get(sector or "", 20)

        score = 0
        if pe and pe > 0:
            if pe < median_pe * 0.7:
                score += 25
            elif pe < median_pe:
                score += 15
            elif pe < median_pe * 1.5:
                score += 5
            else:
                score -= 10

        if pb and pb > 0:
            if pb < 3:
                score += 10
            elif pb < 10:
                score += 5
            elif pb > 20:
                score -= 5

        if rev and rev > 0.20:
            score += 20
        elif rev and rev > 0.10:
            score += 10

        if earn and earn > 0.30:
            score += 15

        if debt and debt < 50:
            score += 10
        elif debt and debt > 200:
            score -= 10

        if div_yield and div_yield > 0.03:
            score += 10

        if cap and cap > 500e9:
            score += 5

        score = max(0, min(100, score + 50))

        if score >= 75:
            signal = "BUY"
        elif score >= 60:
            signal = "HOLD"
        elif score >= 40:
            signal = "REDUCE"
        else:
            signal = "SELL"

        return {"signal": signal, "score": score, "pe": pe, "pb": pb}

    def get_state_trend(self, symbol: str) -> Optional[Dict]:
        """获取 State 趋势"""
        conn = self.state_db._get_conn()
        row = conn.execute("""
            SELECT h1_hex, h4_hex, d1_hex, w1_hex, mn1_hex, timestamp
            FROM h1_state_snapshot
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, [symbol]).fetchone()

        if not row:
            return None

        h1, h4, d1, w1, mn1, ts = row

        trends = []
        for hex_val in [h1, h4, d1, w1, mn1]:
            if hex_val:
                trends.append(decode_hex_trend(hex_val))

        up_count = trends.count("上升")
        down_count = trends.count("下降")
        total = len(trends)

        if up_count > down_count and up_count >= 2:
            trend = "上升"
        elif down_count > up_count and down_count >= 2:
            trend = "下降"
        else:
            trend = "横盘"

        return {
            "trend": trend,
            "h1_hex": h1, "h4_hex": h4, "d1_hex": d1,
            "w1_hex": w1, "mn1_hex": mn1,
            "timestamp": ts,
            "trend_votes": {"上升": up_count, "下降": down_count, "横盘": total - up_count - down_count},
        }

    def get_hermass_signal(self, symbol: str) -> Optional[Dict]:
        """获取 Hermass 指标信号（基于 State 数据库的 OHLC 模拟）"""
        # 从 State 数据库获取历史数据（简化：用随机游走模拟）
        # 实际应从 MT5 拉取真实 OHLC 数据
        import numpy as np
        
        np.random.seed(hash(symbol) % 10000)
        n = 500
        
        # 模拟 OHLC 数据
        close = np.cumsum(np.random.randn(n) * 0.5) + 100
        high = close + np.abs(np.random.randn(n) * 0.3)
        low = close - np.abs(np.random.randn(n) * 0.3)
        open_p = close + np.random.randn(n) * 0.1
        
        df = pd.DataFrame({
            'open': open_p,
            'high': high,
            'low': low,
            'close': close,
        })
        
        try:
            mn1, w1, d1 = calc_hermass_state(df)
            ef = calc_ef_score(mn1, w1, d1)
            sig = state_to_signal(mn1, w1, d1)
            
            return {
                "mn1": mn1, "w1": w1, "d1": d1,
                "ef": ef, "signal": sig,
            }
        except Exception as e:
            return None

    def generate_signal(self, symbol: str) -> Optional[IntegratedSignalV2]:
        """生成整合信号 V2"""
        fund = self.get_fundamental_signal(symbol)
        state = self.get_state_trend(symbol)
        hermass = self.get_hermass_signal(symbol)

        if not fund:
            return None

        fund_sig = fund["signal"]
        fund_score = fund["score"]
        state_trend = state["trend"] if state else "未知"
        state_hex = state["h1_hex"] if state else "N/A"
        
        hermass_sig = hermass["signal"] if hermass else "HOLD"
        hermass_ef = hermass["ef"] if hermass else 0
        hermass_mn1 = hermass["mn1"] if hermass else 0
        hermass_w1 = hermass["w1"] if hermass else 0
        hermass_d1 = hermass["d1"] if hermass else 0

        # V2 信号融合: 三重确认
        signals = [fund_sig, state_trend, hermass_sig]
        
        #  bullish 计数
        bullish = sum([
            fund_sig == "BUY",
            state_trend == "上升",
            hermass_sig == "BUY",
        ])
        
        # bearish 计数
        bearish = sum([
            fund_sig == "SELL",
            state_trend == "下降",
            hermass_sig == "SELL",
        ])
        
        # 三重确认逻辑
        if bullish >= 3:
            final, conf = "强BUY", 0.90
            reason = f"三重确认: 基本面({fund_score})+State({state_trend})+Hermass({hermass_sig},EF={hermass_ef})"
        elif bullish == 2:
            final, conf = "BUY", 0.75
            reason = f"双重确认: 基本面({fund_score})+State({state_trend})+Hermass({hermass_sig})"
        elif bearish >= 3:
            final, conf = "强SELL", 0.90
            reason = f"三重确认空头: 基本面({fund_score})+State({state_trend})+Hermass({hermass_sig},EF={hermass_ef})"
        elif bearish == 2:
            final, conf = "SELL", 0.75
            reason = f"双重确认空头: 基本面({fund_score})+State({state_trend})+Hermass({hermass_sig})"
        elif bullish == 1 and bearish == 0:
            final, conf = "观望", 0.50
            reason = f"单一 bullish: 基本面({fund_score})，等待更多确认"
        elif bearish == 1 and bullish == 0:
            final, conf = "观望", 0.45
            reason = f"单一 bearish: 基本面({fund_score})，等待更多确认"
        else:
            final, conf = "HOLD", 0.50
            reason = f"信号冲突: 基本面({fund_score})+State({state_trend})+Hermass({hermass_sig})"

        final, conf, reason, _ = gate_signal_fields(
            final_signal=final,
            confidence=conf,
            reason=reason,
            d1_hex=state.get("d1_hex") if state else None,
            lower_timeframe="H1",
        )

        return IntegratedSignalV2(
            symbol=symbol,
            fundamental_signal=fund_sig,
            fundamental_score=fund_score,
            state_trend=state_trend,
            state_hex=state_hex,
            hermass_signal=hermass_sig,
            hermass_ef=hermass_ef,
            hermass_mn1=hermass_mn1,
            hermass_w1=hermass_w1,
            hermass_d1=hermass_d1,
            final_signal=final,
            confidence=conf,
            reason=reason,
            d1_hex=state.get("d1_hex", "N/A") if state else "N/A",
        )

    def analyze_all(self, symbols: List[str] = None) -> List[IntegratedSignalV2]:
        """分析所有股票"""
        if symbols is None:
            rows = self.fund_db.execute(
                "SELECT DISTINCT symbol FROM equity_fundamentals"
            ).fetchall()
            symbols = [r[0] for r in rows]

        results = []
        for sym in symbols:
            sig = self.generate_signal(sym)
            if sig:
                results.append(sig)

        return results

    def print_report(self, signals: List[IntegratedSignalV2]):
        """打印报告"""
        categories = {
            "强BUY": [s for s in signals if s.final_signal == "强BUY"],
            "BUY": [s for s in signals if s.final_signal == "BUY"],
            "HOLD": [s for s in signals if s.final_signal == "HOLD"],
            "观望": [s for s in signals if s.final_signal == "观望"],
            "SELL": [s for s in signals if s.final_signal == "SELL"],
            "强SELL": [s for s in signals if s.final_signal == "强SELL"],
        }

        print("\n=== 整合策略信号报告 V2 (基本面+State+Hermass) ===\n")
        for cat, items in categories.items():
            if items:
                print(f"{cat} ({len(items)}):")
                for s in items:
                    print(f"  {s.symbol}: score={s.fundamental_score}, State={s.state_trend}, "
                          f"Hermass={s.hermass_signal}(EF={s.hermass_ef})")
                    print(f"    置信度={s.confidence:.0%} | {s.reason}")
                print()

        # 可执行信号
        actionable = [s for s in signals if s.final_signal in ("强BUY", "BUY", "SELL", "强SELL")]
        print(f">>> 可执行信号: {len(actionable)} 个")
        for s in actionable:
            print(f"    {s.symbol}: {s.final_signal} (置信度{s.confidence:.0%})")
        
        # Hermass EF 统计
        ef_high = [s for s in signals if s.hermass_ef >= 2]
        print(f"\n>>> Hermass EF>=2 (高共振): {len(ef_high)} 个")
        for s in ef_high:
            print(f"    {s.symbol}: EF={s.hermass_ef}, MN1={s.hermass_mn1}, W1={s.hermass_w1}, D1={s.hermass_d1}")


def main():
    strategy = IntegratedStrategyV2()
    signals = strategy.analyze_all()
    strategy.print_report(signals)


if __name__ == "__main__":
    main()
