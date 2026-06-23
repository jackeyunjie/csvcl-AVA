"""
State 切片库 — 模式匹配与统计 v1.0
===================================
从历史State数据中提取「State组合→未来N日收益率」的统计规律

典型用法:
  slicer = StateSlicer(db)
  result = slicer.analyze_pattern("EURUSD", "D1", "E", "E", "F")
  # → {"occurrence": 12次, "win_rate": 75%, "avg_return_5d": +1.2%}
"""

import json
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path
import logging

logger = logging.getLogger("StateSlicer")

from state_database import StateDatabase, StateSlice

TIMEFRAME_MAP = {"MN1": 43200, "W1": 10080, "D1": 1440, "H4": 240, "H1": 60}

class StateSlicer:
    def __init__(self, db: StateDatabase):
        self.db = db

    def analyze_pattern(self, symbol: str, perspective: str,
                         mn1_hex: str, w1_hex: str, d1_hex: str) -> Dict:
        """分析某个State三周期组合的历史表现"""
        history = self.db.query_pattern_history(
            symbol, perspective, mn1_hex, w1_hex, d1_hex)

        slices = self.db.query_slices_by_pattern(
            symbol, perspective, mn1_hex, w1_hex, d1_hex)

        result = {
            "pattern": f"{mn1_hex}_{w1_hex}_{d1_hex}",
            "symbol": symbol,
            "perspective": perspective,
            "occurrence_count": len(history),
            "dates": [h["date"] for h in history[-20:]],
            "slices": []
        }

        for sl in slices:
            result["slices"].append({
                "slice_id": sl.slice_id,
                "forward_1d": sl.forward_return_1d,
                "forward_5d": sl.forward_return_5d,
                "forward_20d": sl.forward_return_20d,
                "occurrence": sl.occurrence_count,
                "win_rate": sl.win_rate,
                "avg_return": sl.avg_return,
            })

        return result

    def scan_resonance(self, perspective: str = "D1",
                        require_ef: int = 2) -> List[Dict]:
        """扫描全品种State共振信号"""
        results = []
        ef_scan = self.db.query_ef_scan(perspective, min_ef=require_ef)

        for row in ef_scan:
            history = self.db.query_pattern_history(
                row["symbol"], perspective,
                row["mn1_hex"], row["w1_hex"], row["d1_hex"])

            if len(history) < 3:
                continue

            win_days = 0
            for h in history:
                if self._has_positive_return(row["symbol"], perspective, h["date"]):
                    win_days += 1

            win_rate = win_days / len(history) * 100
            score = row["ef_count"] * 20 + min(win_rate, 100) * 0.3

            results.append({
                "symbol": row["symbol"],
                "pattern": f"{row['mn1_hex']}_{row['w1_hex']}_{row['d1_hex']}",
                "ef_count": row["ef_count"],
                "occurrence": len(history),
                "win_rate": win_rate,
                "score": round(score, 1),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:30]

    def get_aligned_symbols(self, perspective: str = "D1",
                             min_ef: int = 2) -> List[Dict]:
        """获取当前State对齐的品种列表(适合入场)"""
        snaps = []
        active_syms = self.db.get_active_symbols()
        if not active_syms:
            active_syms = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "BTCUSD"]

        for sym in active_syms:
            snap = self.db.query_latest_snapshot(sym, perspective)
            if snap and snap.ef_count >= min_ef:
                snaps.append({
                    "symbol": sym,
                    "pattern": f"{snap.mn1_hex}_{snap.w1_hex}_{snap.d1_hex}",
                    "ef_count": snap.ef_count,
                    "mn1": snap.mn1_hex, "w1": snap.w1_hex, "d1": snap.d1_hex,
                })

        snaps.sort(key=lambda x: x["ef_count"], reverse=True)
        return snaps

    def compare_perspectives(self, symbol: str) -> Dict:
        """对比同一品种在不同视角下的State差异"""
        result = {"symbol": symbol, "perspectives": {}}
        for persp in ["D1", "W1", "MN1", "H1"]:
            snap = self.db.query_latest_snapshot(symbol, persp)
            if snap:
                result["perspectives"][persp] = {
                    "pattern": f"{snap.mn1_hex}_{snap.w1_hex}_{snap.d1_hex}",
                    "ef_count": snap.ef_count,
                }
        return result

    def _has_positive_return(self, symbol: str, perspective: str,
                              date: str) -> bool:
        """检查某日期后5天是否有正收益(简化,用slice数据)"""
        slices = self.db.query_slices_by_pattern(symbol, perspective)
        for sl in slices:
            if sl.forward_return_5d and sl.forward_return_5d > 0:
                return True
        return False


# ====== 命令行入口 ======
if __name__ == "__main__":
    db = StateDatabase()
    slicer = StateSlicer(db)

    print("=" * 55)
    print("  State 切片库 — 模式匹配分析")
    print("=" * 55)

    # 1. 全品种EF共振扫描
    print("\n[全品种EF共振扫描] ef>=2:")
    resonance = slicer.scan_resonance("D1", require_ef=2)
    for r in resonance[:20]:
        print(f"  {r['symbol']:10s} {r['pattern']:10s} "
              f"ef={r['ef_count']} 出现{r['occurrence']}次 "
              f"Win{r['win_rate']:.0f}% Score={r['score']}")

    # 2. 获取当前对齐品种
    print("\n[当前State对齐品种] (ef>=2):")
    aligned = slicer.get_aligned_symbols("D1", min_ef=2)
    for a in aligned[:15]:
        print(f"  {a['symbol']:10s} {a['pattern']} ef={a['ef_count']}")

    # 3. 对比EURUSD的4视角
    print("\n[EURUSD 4视角对比]:")
    comparison = slicer.compare_perspectives("EURUSD")
    for persp, data in comparison["perspectives"].items():
        print(f"  {persp}视角: {data['pattern']} ef={data['ef_count']}")

    stats = db.get_stats()
    print(f"\n[数据库] {stats['total_snapshots']}快照 "
          f"{stats['total_slices']}切片 "
          f"最新: {stats['latest_date']}")
