import re, html, os
from pathlib import Path
from collections import Counter

print("=" * 70)
print("  AI 交易记录分析器 — 4份报告全解析")
print("=" * 70)

FOLDER = Path(r"d:\qoder\csvcl - AVA\交易记录")

for f in sorted(FOLDER.glob("*.ht*")):
    print(f"\n{'='*60}")
    print(f"  文件: {f.name} ({f.stat().st_size:,} 字节)")
    print(f"{'='*60}")

    raw = f.read_text(encoding="utf-8", errors="ignore")
    text = html.unescape(raw)

    # --- 账号 ---
    acc_m = re.search(r"登录\s*[:：]?\s*(\d+)|Login\s*[:：]?\s*(\d+)|Account[:\s]*(\d+)", text, re.I)
    acc = acc_m.group(1) or acc_m.group(2) or acc_m.group(3) or "?"

    # --- 名称 ---
    name_m = re.search(r"名称\s*[:：]?\s*([^\n<]+)|Name[:\s]*([A-Za-z0-9 ]+)", text, re.I)
    name = (name_m.group(1) or name_m.group(2) or "").strip()

    # --- 金额 ---
    currency_m = re.search(r"(USD|EUR|GBP|JPY)", text, re.I)
    currency = currency_m.group(1) if currency_m else "USD"
    deposits = re.findall(r"入金[^<]*?([\d,]+\.?\d*)", text)
    withdrawals = re.findall(r"出金[^<]*?([\d,]+\.?\d*)", text)
    balance_m = re.findall(r"余[额]?\s*[:\s]*([\d,]+\.?\d*)", text)

    # --- 日期范围 ---
    dates = re.findall(r"(\d{4}\.\d{2}\.\d{2}|\d{4}-\d{2}-\d{2})", text)
    date_range = f"{dates[0]} ~ {dates[-1]}" if len(dates) >= 2 else "未知"

    print(f"  账号: {acc}  ({name})  |  币种: {currency}")
    print(f"  时间: {date_range}")
    if balance_m:
        print(f"  终余额: {balance_m[0]}")

    # --- 解析交易table ---
    # MT4详细报告格式: <tr>开仓时间<td>品种<td>类型<td>手数<td>开仓价<td>平仓价<td>盈亏...
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I)

    trades = []
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.I)
        if len(cells) < 7:
            continue
        clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        # 跳过表头
        if any(kw in clean[0] for kw in ["时间", "Time", "品种", "Symbol", "Ticket", "单号"]):
            continue
        # 尝试提取盈亏金额
        profit_str = ""
        for c in clean:
            if re.match(r"^[-]?[\d,]+\.\d{2}$", c):
                profit_str = c
                break
        if not profit_str:
            continue
        try:
            profit = float(profit_str.replace(",", ""))
        except:
            continue
        trades.append({
            "symbol": clean[1] if len(clean) > 1 else "?",
            "type": clean[2] if len(clean) > 2 else "?",
            "lots": clean[3] if len(clean) > 3 else "?",
            "profit": profit,
            "open_time": clean[0] if len(clean) > 0 else "?",
        })

    if not trades:
        print("  [无交易数据或格式不匹配]")
        continue

    total = len(trades)
    wins = [t for t in trades if t["profit"] > 0]
    losses = [t for t in trades if t["profit"] < 0]
    zeros = [t for t in trades if t["profit"] == 0]
    win_rate = len(wins) / total * 100 if total > 0 else 0
    total_profit = sum(t["profit"] for t in trades)
    avg_win = sum(t["profit"] for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t["profit"] for t in losses) / len(losses)) if losses else 0
    profit_factor = sum(t["profit"] for t in wins) / abs(sum(t["profit"] for t in losses)) if losses and sum(t["profit"] for t in losses) != 0 else 0
    max_win = max(t["profit"] for t in trades)
    max_loss = min(t["profit"] for t in trades)

    print(f"\n  总交易: {total}笔  |  赢: {len(wins)}  |  输: {len(losses)}  |  平: {len(zeros)}")
    print(f"  胜率: {win_rate:.1f}%  |  总盈亏: ${total_profit:,.2f}")
    print(f"  均盈: ${avg_win:,.2f}  |  均亏: ${avg_loss:,.2f}")
    print(f"  盈亏比: 1:{avg_win/avg_loss:.2f}" if avg_loss > 0 else "  盈亏比: N/A")
    print(f"  盈利因子: {profit_factor:.2f}  |  最大盈: ${max_win:,.2f}  |  最大亏: ${max_loss:,.2f}")

    # 品种分布
    sym_counter = Counter(t["symbol"] for t in trades)
    print(f"\n  品种分布 (Top 10):")
    for sym, cnt in sym_counter.most_common(10):
        sym_wins = len([t for t in trades if t["symbol"] == sym and t["profit"] > 0])
        sym_pl = sum(t["profit"] for t in trades if t["symbol"] == sym)
        rate = sym_wins / cnt * 100 if cnt > 0 else 0
        print(f"    {sym:12s}  {cnt:4d}笔  胜率{rate:5.1f}%  盈亏${sym_pl:,.2f}")

    # 最大连续亏损
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
    print(f"\n  最大连亏: {max_streak}笔  (连亏总金额: ${max_streak_pnl:,.2f})")

print(f"\n{'='*70}")
print("  分析完成。正在生成综合报告...")
print(f"{'='*70}")
