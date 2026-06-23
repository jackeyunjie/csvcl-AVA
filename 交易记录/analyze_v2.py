"""
MT4 交易记录精确解析器 v2.0
解析 KVB Prime MT4 DetailedStatement HTML
"""

import re, html, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

FOLDER = Path(r"d:\qoder\csvcl - AVA\交易记录")

def parse_mt4_html(filepath):
    raw = filepath.read_text(encoding="utf-8", errors="ignore")
    text = html.unescape(raw)

    # 账号 + 名称
    acc = re.search(r"Account:\s*(\d+)", text)
    name = re.search(r"Name:\s*([^<\n]+)", text)
    currency = re.search(r"Currency:\s*(\w+)", text)
    acc_id = acc.group(1) if acc else "?"
    acc_name = name.group(1).strip() if name else "?"

    # 找 "Closed Transactions" 表
    # 每个 TR 可能是一个交易行(table row)或多行(因为MT4会加注释行)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I)

    trades = []
    balance_ops = []

    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.I)
        clean = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip() for c in cells]

        # 过滤空行、表头
        if len(clean) < 2:
            continue
        if "Ticket" in clean[0] and "Open Time" in clean[1]:
            continue

        # Column mapping: Ticket(0), OpenTime(1), Type(2), Size(3), Item(4),
        #   Price(5), SL(6), TP(7), CloseTime(8), ClosePrice(9),
        #   Commission(10), Taxes(11), Swap(12), Profit(13)
        # But some rows span 2 <tr> (comment line), so cleaner check:

        ticket = clean[0]
        if not ticket.isdigit():
            continue

        # 类型判断
        tp = ""
        for c in clean:
            cl = c.lower()
            if cl in ("buy", "sell", "balance", "buy limit", "sell limit",
                       "buy stop", "sell stop", "credit"):
                tp = cl
                break

        if not tp:
            # 尝试从相邻行推断 - 某些行因为多行<tr>分散了，跳过
            if "Archived" in row or "CRM" in row:
                continue
            if len(clean) >= 2 and clean[1].lower() in ("buy", "sell"):
                tp = clean[1].lower()

        if tp in ("balance", "credit"):
            # 余额操作，不计入交易统计但记录
            profit_str = ""
            for c in reversed(clean):
                c_clean = c.replace(" ", "").replace(",", "").replace("\xa0", "")
                if re.match(r"^[-]?\d+\.\d{2}$", c_clean):
                    profit_str = c_clean
                    break
            prof = float(profit_str) if profit_str else 0
            balance_ops.append({"ticket": ticket, "profit": prof, "comment": clean[-2] if len(clean) >= 2 else ""})
            continue

        if tp not in ("buy", "sell"):
            continue

        # 查找品种 (Item列，通常在第5列index=4)
        item = ""
        for c in clean[3:]:
            c_stripped = c.replace(",", "").replace(".", "").replace("#", "").strip()
            if c_stripped and not c_stripped.replace("-", "").isdigit():
                item = c
                break

        # 查找手数
        lots_str = ""
        for c in clean[2:6]:
            c_stripped = c.replace(" ", "").replace(",", "")
            if re.match(r"^\d+\.\d{2}$", c_stripped):
                lots_str = c_stripped
                break

        # 查找盈亏
        profit_str = ""
        for c in reversed(clean):
            c_clean = c.replace(" ", "").replace(",", "").replace("\xa0", "")
            if re.match(r"^[-]?\d+\.\d{2}$", c_clean):
                profit_str = c_clean
                break

        profit = float(profit_str) if profit_str else 0
        lots = float(lots_str) if lots_str else 0

        # 开仓/平仓时间
        open_time_str = clean[1] if len(clean) > 1 else ""
        close_time_str = ""
        for c in clean[6:]:
            if re.match(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}", c):
                close_time_str = c
                break

        trades.append({
            "ticket": ticket,
            "type": tp,
            "lots": lots,
            "item": item,
            "profit": profit,
            "open_time": open_time_str,
            "close_time": close_time_str,
        })

    return {
        "file": filepath.name,
        "account": acc_id,
        "name": acc_name,
        "currency": currency.group(1) if currency else "USD",
        "trades": trades,
        "total_op_count": len(balance_ops),
    }

# ============ Main ============
all_results = []
for f in sorted(FOLDER.glob("*.htm*")):
    if "ReportHistory" in f.name:
        continue  # MT5格式不同，单独处理
    result = parse_mt4_html(f)
    all_results.append(result)

    trades = result["trades"]
    if not trades:
        print(f"\n{f.name}: 未解析到交易")
        continue

    total = len(trades)
    wins = [t for t in trades if t["profit"] > 0]
    losses = [t for t in trades if t["profit"] < 0]
    zeros = [t for t in trades if t["profit"] == 0]
    total_pnl = sum(t["profit"] for t in trades)
    win_rate = len(wins) / total * 100 if total > 0 else 0
    avg_win = sum(t["profit"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["profit"] for t in losses) / len(losses) if losses else 0
    profit_factor = sum(t["profit"] for t in wins) / abs(sum(t["profit"] for t in losses)) if losses and sum(t["profit"] for t in losses) != 0 else 999
    max_win = max(t["profit"] for t in trades)
    max_loss = min(t["profit"] for t in trades)
    total_commission = sum(t["profit"] for t in trades)  # placeholder

    buys = [t for t in trades if t["type"] == "buy"]
    sells = [t for t in trades if t["type"] == "sell"]
    buy_win_rate = len([t for t in buys if t["profit"] > 0]) / len(buys) * 100 if buys else 0
    sell_win_rate = len([t for t in sells if t["profit"] > 0]) / len(sells) * 100 if sells else 0

    print(f"\n{'='*70}")
    print(f"  [{result['account']}] {result['name']} - {result['file']}")
    print(f"{'='*70}")
    print(f"  总交易: {total}笔  买{len(buys)}/卖{len(sells)}")
    print(f"  赢: {len(wins)}({win_rate:.1f}%) | 输: {len(losses)}({100-win_rate:.1f}%) | 平: {len(zeros)}")
    print(f"  总盈亏: ${total_pnl:,.2f}")
    print(f"  均盈: ${avg_win:,.2f} | 均亏: ${avg_loss:,.2f}")
    print(f"  盈亏比: {abs(avg_win/avg_loss):.2f}" if avg_loss else "  盈亏比: N/A")
    print(f"  盈利因子: {profit_factor:.2f}")
    print(f"  最大盈: ${max_win:,.2f} | 最大亏: ${max_loss:,.2f}")
    print(f"  多单胜率: {buy_win_rate:.1f}% | 空单胜率: {sell_win_rate:.1f}%")

    # 品种分析
    sym_stats = defaultdict(lambda: {"count": 0, "wins": 0, "pnl": 0.0, "lots": 0.0})
    for t in trades:
        s = t["item"] or "?"
        sym_stats[s]["count"] += 1
        sym_stats[s]["pnl"] += t["profit"]
        sym_stats[s]["lots"] += t["lots"]
        if t["profit"] > 0:
            sym_stats[s]["wins"] += 1

    print(f"\n  品种明细:")
    for sym in sorted(sym_stats, key=lambda k: sym_stats[k]["pnl"], reverse=True):
        st = sym_stats[sym]
        wr = st["wins"] / st["count"] * 100 if st["count"] else 0
        print(f"    {sym:10s} {st['count']:4d}笔  Win{wr:5.0f}%  PnL${st['pnl']:+9,.2f}  Lots{st['lots']:5.2f}")

    # 最大连亏
    streak = 0
    max_streak = 0
    streak_pnl = 0
    max_streak_pnl = 0
    for t in trades:
        if t["profit"] < 0:
            streak += 1
            streak_pnl += t["profit"]
            if streak > max_streak:
                max_streak = streak
            if streak_pnl < max_streak_pnl:
                max_streak_pnl = streak_pnl
        else:
            streak = 0
            streak_pnl = 0
    print(f"\n  最大连亏: {max_streak}笔 (总${max_streak_pnl:,.2f})")

    # 最大单品种亏损集
    baba_trades = [t for t in trades if "baba" in (t["item"] or "").lower()]
    if baba_trades:
        baba_pnl = sum(t["profit"] for t in baba_trades)
        print(f"  #BABA 单品种总盈亏: ${baba_pnl:,.2f} ({len(baba_trades)}笔)")

# 汇总
print(f"\n{'='*70}")
print("  三账户汇总")
print(f"{'='*70}")
merged = []
for r in all_results:
    merged.extend(r["trades"])
total = len(merged)
wins = [t for t in merged if t["profit"] > 0]
losses = [t for t in merged if t["profit"] < 0]
total_pnl = sum(t["profit"] for t in merged)
avg_win = sum(t["profit"] for t in wins) / len(wins) if wins else 0
avg_loss = sum(t["profit"] for t in losses) / len(losses) if losses else 0
print(f"  总笔数: {total}  总盈亏: ${total_pnl:,.2f}")
print(f"  胜率: {len(wins)/total*100:.1f}%  盈亏比: {abs(avg_win/avg_loss):.2f}" if avg_loss else "")

# 合并品种
sym_merged = defaultdict(lambda: {"count": 0, "pnl": 0.0})
for t in merged:
    s = t["item"] or "?"
    sym_merged[s]["count"] += 1
    sym_merged[s]["pnl"] += t["profit"]
print(f"\n  全账户品种盈亏排名:")
for sym in sorted(sym_merged, key=lambda k: sym_merged[k]["pnl"]):
    st = sym_merged[sym]
    print(f"    {sym:10s} {st['count']:4d}笔  ${st['pnl']:+9,.2f}")
