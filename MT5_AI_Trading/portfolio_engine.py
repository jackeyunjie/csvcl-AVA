"""
portfolio_engine.py — Hermass 策略组合引擎
============================================
从 hermass_state.db / stock_state.db 提取已验证策略
→ 计算相关性 → 去重 → 仓位分配 → 输出组合 vs 单策略对比

核心公式:
  weight_i = quality_i / Σ(quality)
  position_i = weight_i × risk_budget / stop_loss_i
  quality   = WR × sqrt(N) × avg_ret (贝叶斯加权)
"""

import duckdb, json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys
sys.stdout.reconfigure(encoding='utf-8')

# ===== 策略定义 (从 forward_log.txt + validate_stock_signal.py 提取) =====
STRATEGIES = [
    {
        "id": "S1_JPY_EURJPY",
        "name": "EURJPY EF>=2",
        "source_db": "data/hermass_state.db",
        "market": "forex",
        "condition": "s.symbol='EURJPY' AND s.ef_count>=2 AND s.perspective='D1'",
        "direction": "LONG_SHORT",
        "hold_bars": 20,
        "n_samples": 179,
        "wr_5d": 60.0,
        "avg_ret_5d": 0.34,
        "wr_20d": 71.0,
        "avg_ret_20d": 1.61,
    },
    {
        "id": "S2_JPY_USDJPY",
        "name": "USDJPY EF>=2",
        "source_db": "data/hermass_state.db",
        "market": "forex",
        "condition": "s.symbol='USDJPY' AND s.ef_count>=2 AND s.perspective='D1'",
        "direction": "LONG_SHORT",
        "hold_bars": 20,
        "n_samples": 208,
        "wr_5d": 60.0,
        "avg_ret_5d": 0.26,
        "wr_20d": 64.0,
        "avg_ret_20d": 0.78,
    },
    {
        "id": "S3_JPY_GBPJPY",
        "name": "GBPJPY EF>=2",
        "source_db": "data/hermass_state.db",
        "market": "forex",
        "condition": "s.symbol='GBPJPY' AND s.ef_count>=2 AND s.perspective='D1'",
        "direction": "LONG_SHORT",
        "hold_bars": 20,
        "n_samples": 146,
        "wr_5d": 51.0,
        "avg_ret_5d": 0.17,
        "wr_20d": 57.0,
        "avg_ret_20d": 0.43,
    },
    {
        "id": "S4_STOCK_SCORE_NEG12",
        "name": "Stock score<=-12 (反转买入)",
        "source_db": "data/stock_state.db",
        "market": "stock",
        "condition": "s.d1_score <= -12 AND s.perspective='D1'",
        "direction": "LONG",
        "hold_bars": 5,
        "n_samples": 3955,
        "wr_5d": 55.5,
        "avg_ret_5d": 0.707,
        "wr_20d": 55.0,
        "avg_ret_20d": 1.678,
    },
    {
        "id": "S5_FOREX_PATTERN_REVERSAL",
        "name": "FX -1_-F_-F 极端反转",
        "source_db": "data/hermass_state.db",
        "market": "forex",
        "condition": "s.mn1_hex='-1' AND s.w1_hex='-F' AND s.d1_hex='-F' AND s.perspective='D1'",
        "direction": "LONG",
        "hold_bars": 5,
        "n_samples": 23,
        "wr_5d": 87.0,
        "avg_ret_5d": 1.05,
        "wr_20d": 87.0,
        "avg_ret_20d": 1.05,
    },
]

# 高质量品种白名单 (WR5>=55% 且 N>=50)
QUALITY_SYMBOLS_FOREX = [
    "EURJPY","USDJPY","GBPJPY","AUDJPY","GBPCHF","EURCHF"
]
QUALITY_STOCKS = [
    "CHEVRON","CONOCOPHILLIPS","CITIGROUP","COSTCO","EXXONMOBIL",
    "WELLSFARGO","INTEL","NVIDIA","GOOGLE","AMAZON","BOEING","MERCK"
]

print("=" * 65)
print("  Hermass 策略组合引擎 v1")
print("=" * 65)

# ===== Step 1: 策略质量控制 =====
print("\n[Step 1] 策略质量评估")

def quality_score(s):
    """贝叶斯加权质量分: WR × sqrt(N) × avg_ret — 平衡胜率、样本量、收益"""
    n = s.get("n_samples", 1)
    wr = s.get("wr_5d", 50) / 100.0
    ret = s.get("avg_ret_5d", 0)
    # sqrt(N)抑制小样本高胜率的虚假信号
    score = wr * (n ** 0.3) * max(ret, 0.01)  # n^0.3 温和惩罚小样本
    # 如果20日均收益显著更好，加分
    wr20 = s.get("wr_20d", 50) / 100.0
    ret20 = s.get("avg_ret_20d", 0)
    if ret20 > ret * 1.5:
        score *= 1.2  # 趋势延伸效应加分
    return round(score, 4)

selected = []
for s in STRATEGIES:
    q = quality_score(s)
    s["quality"] = q
    flag = "✓" if q > 0.05 else "⚠️"
    print(f"  {flag} {s['id']:28s} N={s['n_samples']:4d} WR5={s['wr_5d']}% "
          f"R5={s['avg_ret_5d']:+.3f}% Q={q:.4f}")
    if q > 0.03:
        selected.append(s)

print(f"\n  Selected: {len(selected)}/{len(STRATEGIES)} strategies (Q>0.03)")

# ===== Step 2: 策略收益序列提取 (从DB JOIN) =====
print(f"\n[Step 2] 提取策略收益序列")

def get_strategy_returns(s):
    """从DB提取某策略的每笔收益序列"""
    db = duckdb.connect(s["source_db"])
    try:
        cond = s["condition"]
        days = s.get("hold_bars", 5)
        col = "r5" if days == 5 else "r20"
        if days == 20:
            col = "r20"
        elif days == 10:
            col = "r10"
        rows = db.execute(f"""
            SELECT s.date, s.symbol, f.{col} as ret
            FROM state_snapshots s
            JOIN fwd f ON s.symbol=f.symbol AND s.date=f.date
            WHERE ({cond}) AND f.{col} IS NOT NULL
            ORDER BY s.date
        """).fetchall()
        return [(r[0], r[1], float(r[2])) for r in rows]
    except Exception as e:
        print(f"    {s['id']}: DB error — {str(e)[:60]}")
        return []
    finally:
        db.close()

strategy_returns = {}
for s in selected:
    rets = get_strategy_returns(s)
    if len(rets) >= 10:
        strategy_returns[s["id"]] = rets
        avg = sum(r[2] for r in rets) / len(rets)
        wr = sum(1 for r in rets if r[2] > 0) / len(rets) * 100
        print(f"  {s['id']:30s} {len(rets):4d} trades | avg={avg:+.3f}% | WR={wr:.0f}%")
    else:
        print(f"  {s['id']:30s} skipped (N={len(rets)} insufficient)")

# ===== Step 3: 相关性矩阵 =====
print(f"\n[Step 3] 策略相关性矩阵")

strategies_with_data = list(strategy_returns.keys())
n = len(strategies_with_data)
corr = [[0.0]*n for _ in range(n)]

for i in range(n):
    for j in range(i, n):
        if i == j:
            corr[i][j] = 1.0
            continue
        # 按日期对齐两个策略的收益
        ri = strategy_returns[strategies_with_data[i]]
        rj = strategy_returns[strategies_with_data[j]]
        # 按日期+品种取交集
        di = {(r[0], r[1]): r[2] for r in ri}
        dj = {(r[0], r[1]): r[2] for r in rj}
        common = set(di.keys()) & set(dj.keys())
        if len(common) < 10:
            corr[i][j] = corr[j][i] = 0
            continue
        xi = [di[k] for k in common]
        xj = [dj[k] for k in common]
        mi, mj = sum(xi)/len(xi), sum(xj)/len(xj)
        cov = sum((a-mi)*(b-mj) for a,b in zip(xi,xj)) / len(xi)
        si = (sum((a-mi)**2 for a in xi) / len(xi)) ** 0.5
        sj = (sum((b-mj)**2 for b in xj) / len(xj)) ** 0.5
        corr[i][j] = corr[j][i] = round(cov/(si*sj+1e-9), 3)

print(f"  {'ID':30s}", end="")
for sid in strategies_with_data:
    print(f"{sid[-12:]:>8s}", end="")
print()
for i in range(n):
    print(f"  {strategies_with_data[i]:30s}", end="")
    for j in range(n):
        print(f"  {corr[i][j]:+.3f}", end="")
    print()

# 高相关性警告
high_corr = []
for i in range(n):
    for j in range(i+1, n):
        if abs(corr[i][j]) > 0.5:
            high_corr.append((strategies_with_data[i], strategies_with_data[j], corr[i][j]))
            print(f"  ⚠️ HIGH CORR: {strategies_with_data[i]} ↔ {strategies_with_data[j]} = {corr[i][j]:.3f}")

# ===== Step 4: 去相关性过滤 =====
print(f"\n[Step 4] 去相关性聚合")

# 贪婪算法：按quality排序，逐个加入，跳过corr>0.5的
final_pool = []
for s in sorted(selected, key=lambda x: x["quality"], reverse=True):
    sid = s["id"]
    if sid not in strategy_returns:
        continue
    conflict = False
    for existing in final_pool:
        ei = strategies_with_data.index(existing["id"]) if existing["id"] in strategies_with_data else -1
        si = strategies_with_data.index(sid) if sid in strategies_with_data else -1
        if ei >= 0 and si >= 0 and abs(corr[si][ei]) > 0.5:
            conflict = True
            break
    if not conflict:
        s["status"] = "INCLUDED"
        final_pool.append(s)
    else:
        s["status"] = "CORRELATED"

for s in selected:
    sid = s["id"]
    if sid not in strategy_returns:
        s["status"] = "NO_DATA"
    flag = "✓" if s.get("status") == "INCLUDED" else "✗"
    print(f"  {flag} {s['id']:30s} Q={s['quality']:.4f} → {s.get('status','?')}")

total_quality = sum(s["quality"] for s in final_pool)
print(f"\n  最终策略池: {len(final_pool)} 个 | 总质量分: {total_quality:.4f}")

# ===== Step 5: 仓位分配 =====
print(f"\n[Step 5] 仓位分配 (2%风险预算)")

ACCOUNT = 10000.0
RISK_BUDGET_PCT = 0.02  # 总风险 2%
RISK_BUDGET = ACCOUNT * RISK_BUDGET_PCT

print(f"  账户: ${ACCOUNT:,.0f} | 风险预算: ${RISK_BUDGET:,.0f} ({RISK_BUDGET_PCT*100}%)")
print(f"  {'Strategy':30s} {'Weight':>7s} {'ATR%':>7s} {'Lots(0.01)':>10s} {'Risk$':>8s}")
print(f"  {'-'*65}")

allocations = []
for s in final_pool:
    w = s["quality"] / total_quality
    # ATR估算: avg_ret_5d 的2倍作为波动代理
    avg_ret = abs(s.get("avg_ret_5d", 0.5))
    atr_pct = max(avg_ret * 2.5, 0.3)  # 至少0.3%
    risk_alloc = w * RISK_BUDGET
    # 单策略风险上限: 40% of budget
    risk_alloc = min(risk_alloc, RISK_BUDGET * 0.40)
    lots = risk_alloc / (atr_pct / 100 * ACCOUNT / 100)  # simplified
    lots = round(max(lots, 0.01), 2)

    s["weight"] = round(w, 3)
    s["atr_pct"] = round(atr_pct, 1)
    s["lots"] = lots
    allocations.append(s)

    print(f"  {s['id']:30s} {w:6.1%} {atr_pct:6.1f}% {lots:9.2f} ${risk_alloc:7,.0f}")

# ===== Step 6: 方向暴露检查 =====
print(f"\n[Step 6] 方向暴露检查")
long_weight = sum(s.get("weight", 0) for s in final_pool if s.get("direction") in ("LONG", "LONG_SHORT"))
short_weight = sum(s.get("weight", 0) for s in final_pool if s.get("direction") == "SHORT")
print(f"  Long总权重:  {long_weight:.1%} (上限60%) {'✓' if long_weight<0.6 else '⚠️ OVERWEIGHT'}")
print(f"  Short总权重: {short_weight:.1%} (上限40%)")
print(f"  Net敞口:     {(long_weight-short_weight):.1%}")

# ===== Step 7: 策略池综合统计 =====
print(f"\n[Step 7] 策略池综合统计")

pool_trades = []
pool_signals_per_year = defaultdict(int)
for s in final_pool:
    sid = s["id"]
    if sid not in strategy_returns:
        continue
    for date, sym, ret in strategy_returns[sid]:
        pool_trades.append(ret)
        yr = str(date)[:4]
        pool_signals_per_year[yr] += 1

pool_avg = sum(pool_trades)/len(pool_trades)
pool_wr = sum(1 for r in pool_trades if r > 0)/len(pool_trades)*100
pool_n = len(pool_trades)

print(f"  总交易: {pool_n} | 均收益: {pool_avg:+.2f}% | 胜率: {pool_wr:.0f}%")
print(f"  年信号量: {dict(sorted(pool_signals_per_year.items()))}")

# 单策略对比
print(f"\n  {'Strategy':30s} {'Trades':>6s} {'Avg':>8s} {'WR':>6s} {'Sharpe*':>8s}")
print(f"  {'-'*62}")
for s in final_pool:
    sid = s["id"]
    if sid not in strategy_returns:
        continue
    rets = [r[2] for r in strategy_returns[sid]]
    avg = sum(rets)/len(rets)
    wr = sum(1 for r in rets if r > 0)/len(rets)*100
    std = (sum((r-avg)**2 for r in rets)/len(rets))**0.5
    sharpe = avg/std if std > 0 else 0
    print(f"  {sid:30s} {len(rets):6d} {avg:+7.2f}% {wr:5.0f}% {sharpe:+7.2f}")

# ===== 输出文件 =====
output = {
    "generated_at": datetime.now().isoformat(),
    "strategies_total": len(STRATEGIES),
    "strategies_selected": len(selected),
    "strategies_in_pool": len(final_pool),
    "quality_scores": {s["id"]: s["quality"] for s in STRATEGIES},
    "correlation_matrix": {strategies_with_data[i]: {strategies_with_data[j]: corr[i][j] for j in range(n)} for i in range(n)},
    "portfolio": [{"id": s["id"], "weight": s.get("weight",0), "atr_pct": s.get("atr_pct",0), "lots": s.get("lots",0), "status": s.get("status","?")} for s in selected],
    "pool_stats": {"total_trades": pool_n, "avg_ret_pct": pool_avg, "win_rate": pool_wr},
}

Path("reports").mkdir(exist_ok=True)
with open("reports/portfolio_engine.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)

print(f"\n{'='*65}")
print(f"  [Done] 报告: reports/portfolio_engine.json")
print(f"{'='*65}")
