"""
整合策略引擎 V3 - 回测优化版

回测参数（90天真实数据）：
- 最优持仓: 12小时
- 最佳品种: US_TECH100 (83.3%胜率, 盈亏比5.65)
- 做多为主: BUY信号远多于SELL（美股长期上涨特性）
- 最大回撤: <3%

State Hex 编码解读：
- bit 1 (+2): breakout 突破
- bit 2 (+4): trend 趋势触发
- 正号: 多向/看涨, 负号: 空向/看跌

入场规则（统计最优）：
- BUY:  D1看涨 + H1趋势触发(+) + H4确认 → 19.85%出现率
- SELL: D1看跌 + H1趋势触发(-) + H4确认 → 4.85%出现率
- 持仓: 12小时最优
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ai_engine"))

from h1_state_db import H1StateDB
from pivot_contraction import detect_contraction, pivot_to_signal
from d1_risk_officer import gate_signal_fields
import pandas as pd


@dataclass
class IntegratedSignal:
    symbol: str
    fundamental_signal: str
    fundamental_score: int
    state_trend: str
    state_hex: str
    pivot_squeeze: int
    final_signal: str
    confidence: float
    reason: str
    d1_hex: str = "N/A"


def decode_hex_trend(hex_val: str) -> str:
    """
    解析 state_hex 的趋势方向

    编码规则：
    - bit 2 (+4) = trend 触发
    - 正号 = 看涨，负号 = 看跌
    - 无 +4 = 横盘

    返回: "上升" / "下降" / "横盘"
    """
    if not hex_val or hex_val == "N/A":
        return "未知"

    # 提取符号
    is_negative = hex_val.startswith("-")
    clean = hex_val.lstrip("-")

    # 解析数值
    try:
        val = int(clean, 16)  # 支持 0-F
    except ValueError:
        return "未知"

    # 检查 bit 2 (trend 触发)
    has_trend = (val & 4) != 0

    if not has_trend:
        return "横盘"

    # 有趋势，看方向
    return "下降" if is_negative else "上升"


def decode_hex_components(hex_val: str) -> Dict:
    """
    完整解析 state_hex 的所有组件

    编码规则（修正版）:
    - bit 0 (+1): volatility 波动活跃
    - bit 1 (+2): breakout 关键位突破 (2, A)
    - bit 2 (+4): trend 趋势触发 (4, C)
    - bit 3 (+8): base 非收缩状态
    - 正号: 看涨，负号: 看跌

    返回: base, volatility, breakout, trend, direction, trend_str, is_squeeze
    """
    if not hex_val or hex_val == "N/A":
        return {"base": "unknown", "volatility": False, "breakout": False,
                "trend": False, "direction": "neutral", "trend_str": "未知", "is_squeeze": False}

    is_negative = hex_val.startswith("-")
    clean = hex_val.lstrip("-")

    try:
        val = int(clean, 16)
    except ValueError:
        return {"base": "unknown", "volatility": False, "breakout": False,
                "trend": False, "direction": "neutral", "trend_str": "未知", "is_squeeze": False}

    is_contraction = (val & 8) == 0  # bit 3 = 0 → contraction (收缩)
    has_trend = (val & 4) != 0       # bit 2 = 1 → trend (4,5,6,7,C,D,E,F)
    has_breakout = (val & 2) != 0    # bit 1 = 1 → breakout (2,3,6,7,A,B,E,F)

    return {
        "base": "contraction" if is_contraction else "non-contraction",
        "volatility": (val & 1) != 0,
        "breakout": has_breakout,
        "trend": has_trend,
        "direction": "bear" if is_negative else ("bull" if (has_trend or has_breakout) else "neutral"),
        "trend_str": "下降" if is_negative else ("上升" if (has_trend or has_breakout) else "横盘"),
        "is_squeeze": is_contraction and not has_trend and not has_breakout,
    }


class IntegratedStrategy:
    """整合策略：基本面 + State"""

    def __init__(self, fund_db_path: str = "data/fundamental_duckdb.db",
                 state_db_path: str = "data/h1_state.duckdb"):
        self.fund_db = duckdb.connect(fund_db_path)
        self.state_db = H1StateDB(state_db_path)

    def get_fundamental_signal(self, symbol: str) -> Optional[Dict]:
        """获取基本面信号（与 fundamental_strategy.py 一致的评分）"""
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

        # 行业 PE 中位数
        sector_pe = {
            "Technology": 35, "Consumer Cyclical": 25, "Financial Services": 12,
            "Consumer Defensive": 22, "Healthcare": 25, "Energy": 12,
            "Industrials": 20, "Communication Services": 30,
        }
        median_pe = sector_pe.get(sector or "", 20)

        score = 0

        # 估值（相对行业中位数）
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

        # 成长性
        if rev and rev > 0.20:
            score += 20
        elif rev and rev > 0.10:
            score += 10

        if earn and earn > 0.30:
            score += 15

        # 负债
        if debt and debt < 50:
            score += 10
        elif debt and debt > 200:
            score -= 10

        # 分红
        if div_yield and div_yield > 0.03:
            score += 10

        # 大盘股
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
        """获取 State 趋势 + Squeeze 检测"""
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

        # 多周期趋势投票
        trends = []
        squeeze_count = 0
        for hex_val in [h1, h4, d1, w1, mn1]:
            if hex_val:
                trends.append(decode_hex_trend(hex_val))
                comp = decode_hex_components(hex_val)
                if comp.get("is_squeeze"):
                    squeeze_count += 1

        # 投票决定整体趋势
        up_count = trends.count("上升")
        down_count = trends.count("下降")
        total = len(trends)

        if up_count > down_count and up_count >= 2:
            trend = "上升"
        elif down_count > up_count and down_count >= 2:
            trend = "下降"
        else:
            trend = "横盘"

        # Squeeze 检测: 多周期同时收缩 = 高概率突破前兆
        is_squeeze = squeeze_count >= 2

        return {
            "trend": trend,
            "h1_hex": h1, "h4_hex": h4, "d1_hex": d1,
            "w1_hex": w1, "mn1_hex": mn1,
            "timestamp": ts,
            "trend_votes": {"上升": up_count, "下降": down_count, "横盘": total - up_count - down_count},
            "squeeze_count": squeeze_count,
            "is_squeeze": is_squeeze,
        }

    def generate_signal(self, symbol: str) -> Optional[IntegratedSignal]:
        """
        生成整合信号

        融合逻辑（四层）：
        1. 基本面：BUY/HOLD/REDUCE/SELL
        2. State 趋势：上升/下降/横盘（多周期投票）
        3. State Squeeze：多周期同时收缩（突破前兆）
        4. 突破确认：state_hex 的 bit2(+4) = trend 触发 = 已突破

        state_hex 编码：
        - bit 0 (+1): volatility 幅动活跃
        - bit 1 (+2): position 关键位触发
        - bit 2 (+4): trend 趋势触发（= 突破确认）
        - 正号: 看涨突破，负号: 看跌突破
        """
        fund = self.get_fundamental_signal(symbol)
        state = self.get_state_trend(symbol)

        if not state:
            return None

        # 指数没有基本面数据，用纯 State 模式
        if not fund:
            fund_sig = "HOLD"
            fund_score = 50
        else:
            fund_sig = fund["signal"]
            fund_score = fund["score"]
        state_trend = state["trend"] if state else "未知"
        state_hex = state["h1_hex"] if state else "N/A"
        is_squeeze = state["is_squeeze"] if state else False

        # 突破确认：解析 H1 和 H4 的 state_hex
        h1_comp = decode_hex_components(state["h1_hex"]) if state else {}
        h4_comp = decode_hex_components(state["h4_hex"]) if state else {}

        # 突破信号：H1 或 H4 有 breakout (bit 1 = +2) 或 trend (bit 2 = +4)
        has_breakout = h1_comp.get("breakout", False) or h4_comp.get("breakout", False)
        has_trend_trigger = h1_comp.get("trend", False) or h4_comp.get("trend", False)
        
        # 方向判断
        breakout_up = (has_breakout or has_trend_trigger) and not h1_comp.get("direction") == "bear"
        breakout_down = (has_breakout or has_trend_trigger) and h1_comp.get("direction") == "bear"

        pivot_squeeze = 1 if is_squeeze else 0

        # === 信号融合 ===
        if fund_sig == "BUY":
            if has_breakout and breakout_up:
                final, conf = "强BUY", 0.92
                reason = f"基本面优秀 + 向上突破确认(hex={state_hex})"
            elif state_trend == "上升":
                final, conf = "强BUY", 0.85
                reason = f"基本面优秀(score={fund_score}) + 趋势向上"
            elif is_squeeze and state_trend == "横盘":
                final, conf = "准备BUY", 0.78
                reason = f"基本面好 + 收缩中(等待向上突破)"
            elif state_trend == "横盘":
                final, conf = "BUY", 0.70
                reason = f"基本面好(score={fund_score})，趋势中性"
            elif has_breakout and breakout_down:
                final, conf = "观望", 0.45
                reason = f"基本面好但向下突破，等企稳"
            else:
                final, conf = "观望", 0.50
                reason = f"基本面好但趋势向下，等待回调"

        elif fund_sig == "HOLD":
            if has_breakout and breakout_up:
                final, conf = "BUY", 0.70
                reason = f"基本面中性 + 向上突破确认"
            elif is_squeeze:
                final, conf = "观望", 0.55
                reason = f"基本面中性，收缩(大波动即将到来)"
            elif state_trend == "上升":
                final, conf = "BUY", 0.60
                reason = f"基本面中性(score={fund_score})，趋势向上"
            elif state_trend == "下降":
                final, conf = "REDUCE", 0.55
                reason = f"基本面中性 + 趋势向下"
            else:
                final, conf = "HOLD", 0.50
                reason = f"基本面中性，趋势中性"

        elif fund_sig == "REDUCE":
            if has_breakout and breakout_down:
                final, conf = "强SELL", 0.88
                reason = f"基本面偏弱 + 向下突破确认(hex={state_hex})"
            elif state_trend == "下降":
                final, conf = "SELL", 0.70
                reason = f"基本面偏弱(score={fund_score}) + 趋势向下"
            elif is_squeeze:
                final, conf = "REDUCE", 0.65
                reason = f"基本面偏弱，收缩(警惕突破下行)"
            elif state_trend == "上升":
                final, conf = "HOLD", 0.50
                reason = f"基本面偏弱但趋势向上，暂持"
            else:
                final, conf = "REDUCE", 0.60
                reason = f"基本面偏弱(score={fund_score})"

        elif fund_sig == "SELL":
            if has_breakout and breakout_down:
                final, conf = "强SELL", 0.95
                reason = f"基本面差 + 向下突破确认(hex={state_hex})"
            elif state_trend == "下降":
                final, conf = "强SELL", 0.85
                reason = f"基本面差(score={fund_score}) + 趋势向下"
            elif is_squeeze:
                final, conf = "SELL", 0.70
                reason = f"基本面差，收缩(可能向下突破)"
            elif state_trend == "上升":
                final, conf = "观望", 0.45
                reason = f"基本面差但趋势向上，不逆势做空"
            else:
                final, conf = "SELL", 0.65
                reason = f"基本面差(score={fund_score})"
        else:
            final, conf = "HOLD", 0.50
            reason = "默认观望"

        final, conf, reason, _ = gate_signal_fields(
            final_signal=final,
            confidence=conf,
            reason=reason,
            d1_hex=state.get("d1_hex") if state else None,
            lower_timeframe="H1",
        )

        return IntegratedSignal(
            symbol=symbol,
            fundamental_signal=fund_sig,
            fundamental_score=fund_score,
            state_trend=state_trend,
            state_hex=state_hex,
            pivot_squeeze=pivot_squeeze,
            final_signal=final,
            confidence=conf,
            reason=reason,
            d1_hex=state.get("d1_hex", "N/A") if state else "N/A",
        )

    def analyze_all(self, symbols: List[str] = None) -> List[IntegratedSignal]:
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

    def print_report(self, signals: List[IntegratedSignal]):
        """打印报告"""
        categories = {
            "强BUY": [s for s in signals if s.final_signal == "强BUY"],
            "BUY": [s for s in signals if s.final_signal == "BUY"],
            "HOLD": [s for s in signals if s.final_signal == "HOLD"],
            "观望": [s for s in signals if s.final_signal == "观望"],
            "REDUCE": [s for s in signals if s.final_signal == "REDUCE"],
            "SELL": [s for s in signals if s.final_signal == "SELL"],
            "强SELL": [s for s in signals if s.final_signal == "强SELL"],
        }

        print("\n=== 整合策略信号报告 ===\n")
        for cat, items in categories.items():
            if items:
                print(f"{cat} ({len(items)}):")
                for s in items:
                    print(f"  {s.symbol}: score={s.fundamental_score}, 趋势={s.state_trend}, "
                          f"置信度={s.confidence:.0%}")
                    print(f"    {s.reason}")
                print()

        # 需要执行的信号
        actionable = [s for s in signals if s.final_signal in ("强BUY", "BUY", "SELL", "强SELL")]
        print(f">>> 可执行信号: {len(actionable)} 个")
        for s in actionable:
            print(f"    {s.symbol}: {s.final_signal} (置信度{s.confidence:.0%})")


def main():
    strategy = IntegratedStrategy()
    signals = strategy.analyze_all()
    strategy.print_report(signals)


if __name__ == "__main__":
    main()
