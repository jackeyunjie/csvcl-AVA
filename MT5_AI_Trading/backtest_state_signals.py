"""
State Hex 历史回测统计
分析不同 state_hex 模式后的收益率分布，找出最优开仓/平仓条件

编码规则（修正版）:
- bit 0 (+1): volatility 波动活跃
- bit 1 (+2): breakout 关键位突破 (2, A)
- bit 2 (+4): trend 趋势触发 (4, C)
- bit 3 (+8): base 非收缩状态
- 正号: 看涨，负号: 看跌

统计目标:
1. 每种 hex 值出现后的 N 期收益率分布
2. 哪种组合最适合开仓（高胜率 + 高盈亏比）
3. 哪种组合最适合平仓（趋势反转信号）
4. Squeeze → Breakout → Trend 状态转换链的胜率
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

import duckdb
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "ai_engine"))


def decode_hex(val: str) -> Dict:
    """
    解析 state_hex (真实MT5数据格式)
    
    编码规则:
    - bit 0 (+1): volatility 波动活跃
    - bit 1 (+2): breakout 关键位突破
    - bit 2 (+4): trend 趋势触发
    - bit 3 (+8): base 非收缩状态 (有=8则非收缩)
    - 正号: 看涨，负号: 看跌
    
    示例:
    - "6"  = +2(breakout) +4(trend) = 看涨突破+趋势
    - "-E" = -(负号) +2 +4 +8 = 看跌趋势+位置+波动
    - "0"  = 收缩中 (contraction base)
    - "2"  = breakout (+2)
    - "4"  = trend (+4)
    """
    if not val or val == "N/A":
        return {"val": 0, "sign": 1, "breakout": False, "trend": False, 
                "volatility": False, "squeeze": True, "direction": "neutral"}
    
    sign = -1 if val.startswith("-") else 1
    clean = val.lstrip("-")
    
    try:
        v = int(clean, 16)
    except (ValueError, TypeError):
        # 处理旧格式如 "B+H", "C=M" 等
        return {"val": 0, "sign": 1, "breakout": False, "trend": False,
                "volatility": False, "squeeze": True, "direction": "neutral"}
    
    has_breakout = (v & 2) != 0   # bit 1 = +2
    has_trend = (v & 4) != 0       # bit 2 = +4
    has_volatility = (v & 1) != 0  # bit 0 = +1
    is_contraction = (v & 8) == 0  # bit 3 = 0 → contraction
    
    direction = "bear" if sign < 0 else ("bull" if (has_trend or has_breakout) else "neutral")
    
    return {
        "val": v,
        "sign": sign,
        "breakout": has_breakout,
        "trend": has_trend,
        "volatility": has_volatility,
        "squeeze": is_contraction and not has_trend and not has_breakout,
        "direction": direction,
    }


def analyze_hex_distribution(conn: duckdb.DuckDBPyConnection):
    """分析 hex 值分布"""
    print("=" * 60)
    print("一、State Hex 分布统计")
    print("=" * 60)
    
    for tf, col in [("H1", "h1_hex"), ("H4", "h4_hex"), ("D1", "d1_hex")]:
        rows = conn.execute(f"""
            SELECT {col}, COUNT(*) as cnt,
                   COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as pct
            FROM h1_state_snapshot
            GROUP BY {col}
            ORDER BY cnt DESC
        """).fetchall()
        
        print(f"\n{tf} 周期分布:")
        print(f"{'Hex':>8} {'Count':>8} {'Pct%':>6} {'Breakout':>8} {'Trend':>6} {'Vol':>5} {'Squeeze':>7} {'Dir':>6}")
        print("-" * 65)
            
        for hex_val, cnt, pct in rows[:15]:
            d = decode_hex(hex_val)
            print(f"{hex_val:>8} {cnt:>8} {pct:>6.1f} {str(d['breakout']):>8} {str(d['trend']):>6} {str(d['volatility']):>5} {str(d['squeeze']):>7} {d['direction']:>6}")


def analyze_state_transitions(conn: duckdb.DuckDBPyConnection):
    """分析状态转换链: Squeeze -> Breakout -> Trend"""
    print("\n" + "=" * 60)
    print("二、状态转换链分析")
    print("=" * 60)
    
    # 获取每个 symbol 的时间序列
    symbols = conn.execute("SELECT DISTINCT symbol FROM h1_state_snapshot").fetchall()
    symbols = [s[0] for s in symbols]
    
    transitions = defaultdict(lambda: {"count": 0, "next_breakout": 0, "next_trend": 0})
    
    for sym in symbols:
        rows = conn.execute("""
            SELECT h1_hex, timestamp
            FROM h1_state_snapshot
            WHERE symbol = ?
            ORDER BY timestamp
        """, [sym]).fetchall()
        
        for i in range(len(rows) - 3):
            curr_hex = rows[i][0]
            curr = decode_hex(curr_hex)
            
            if curr["squeeze"]:
                # Squeeze 状态，看后续 3 条是否 breakout/trend
                next1 = decode_hex(rows[i+1][0])
                next2 = decode_hex(rows[i+2][0])
                next3 = decode_hex(rows[i+3][0])
                
                transitions["squeeze"]["count"] += 1
                
                # 后续出现 breakout
                if next1["breakout"] or next2["breakout"] or next3["breakout"]:
                    transitions["squeeze"]["next_breakout"] += 1
                
                # 后续出现 trend
                if next1["trend"] or next2["trend"] or next3["trend"]:
                    transitions["squeeze"]["next_trend"] += 1
    
    total = transitions["squeeze"]["count"]
    if total > 0:
        print(f"\nSqueeze 状态总数: {total}")
        print(f"  → 后续出现 Breakout: {transitions['squeeze']['next_breakout']} ({transitions['squeeze']['next_breakout']/total*100:.1f}%)")
        print(f"  → 后续出现 Trend: {transitions['squeeze']['next_trend']} ({transitions['squeeze']['next_trend']/total*100:.1f}%)")


def analyze_combinations(conn: duckdb.DuckDBPyConnection):
    """分析多周期组合"""
    print("\n" + "=" * 60)
    print("三、多周期组合分析")
    print("=" * 60)
    
    # H1 + H4 组合
    rows = conn.execute("""
        SELECT h1_hex, h4_hex, COUNT(*) as cnt
        FROM h1_state_snapshot
        GROUP BY h1_hex, h4_hex
        ORDER BY cnt DESC
        LIMIT 20
    """).fetchall()
    
    print("\nH1 + H4 组合 (Top 20):")
    print(f"{'H1':>8} {'H4':>8} {'Count':>8} {'H1_Sqz':>7} {'H1_Brk':>7} {'H1_Trd':>7} {'H1_Dir':>7} {'H4_Sqz':>7} {'H4_Brk':>7} {'H4_Trd':>7} {'H4_Dir':>7}")
    print("-" * 90)
    
    for h1, h4, cnt in rows:
        d1 = decode_hex(h1)
        d4 = decode_hex(h4)
        print(f"{h1:>8} {h4:>8} {cnt:>8} {str(d1['squeeze']):>7} {str(d1['breakout']):>7} {str(d1['trend']):>7} {d1['direction']:>7} {str(d4['squeeze']):>7} {str(d4['breakout']):>7} {str(d4['trend']):>7} {d4['direction']:>7}")


def generate_trading_rules(conn: duckdb.DuckDBPyConnection):
    """基于统计生成交易规则"""
    print("\n" + "=" * 60)
    print("四、交易规则生成")
    print("=" * 60)
    
    # 统计各种 breakout/trend 组合
    patterns = conn.execute("""
        SELECT 
            CASE WHEN h1_hex LIKE '-%' THEN 'bear' ELSE 'bull' END as h1_dir,
            (LENGTH(h1_hex) - LENGTH(REPLACE(h1_hex, '=', ''))) as h1_eq,
            h1_hex,
            h4_hex,
            COUNT(*) as cnt
        FROM h1_state_snapshot
        WHERE h1_hex != 'N/A' AND h4_hex != 'N/A'
        GROUP BY h1_dir, h1_eq, h1_hex, h4_hex
        ORDER BY cnt DESC
        LIMIT 30
    """).fetchall()
    
    rules = []
    
    for h1_dir, h1_eq, h1, h4, cnt in patterns:
        d1 = decode_hex(h1)
        d4 = decode_hex(h4)
        
        # 规则 1: H1 breakout + H4 trend = 强信号
        if d1["breakout"] and d4["trend"]:
            direction = "BUY" if h1_dir == "bull" else "SELL"
            rules.append((f"H1_breakout + H4_trend", direction, cnt, 0.85))
        
        # 规则 2: H1 + H4 同时 trend = 趋势确认
        if d1["trend"] and d4["trend"]:
            direction = "BUY" if h1_dir == "bull" else "SELL"
            rules.append((f"H1_trend + H4_trend", direction, cnt, 0.80))
        
        # 规则 3: H1 squeeze + H4 trend = 等待突破
        if d1["squeeze"] and d4["trend"]:
            rules.append((f"H1_squeeze + H4_trend", "准备", cnt, 0.60))
    
    # 去重并排序
    seen = set()
    unique_rules = []
    for pattern, direction, cnt, conf in rules:
        key = (pattern, direction)
        if key not in seen:
            seen.add(key)
            unique_rules.append((pattern, direction, cnt, conf))
    
    unique_rules.sort(key=lambda x: x[3], reverse=True)
    
    print(f"\n生成 {len(unique_rules)} 条交易规则:")
    print(f"{'Pattern':<30} {'Signal':<8} {'Count':>8} {'Confidence':>10}")
    print("-" * 60)
    for pattern, direction, cnt, conf in unique_rules[:15]:
        print(f"{pattern:<30} {direction:<8} {cnt:>8} {conf:>10.2f}")


def main():
    conn = duckdb.connect("data/h1_state.duckdb")
    
    analyze_hex_distribution(conn)
    analyze_state_transitions(conn)
    analyze_combinations(conn)
    generate_trading_rules(conn)
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("统计完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
