import duckdb

# Top 策略模式 (从 strategy_mining_report_20260604_092057.md)
TOP_PATTERNS = [
    # (模式名称, 匹配条件函数, 方向, 持仓, 评分, 胜率, 盈亏比)
    ("H1=-F", lambda s: s['h1'] == '-F', 'short', 5, 97.1, '92.8%', 25.12),
    ("D1=8,H4=8,H1=-F", lambda s: s['d1'] == '8' and s['h4'] == '8' and s['h1'] == '-F', 'short', 5, 96.2, '93.6%', 27.15),
    ("H4=-F,H1=-F", lambda s: s['h4'] == '-F' and s['h1'] == '-F', 'short', 5, 95.4, '92.8%', 25.39),
    ("D1=-F,H4=-F,H1=-F", lambda s: s['d1'] == '-F' and s['h4'] == '-F' and s['h1'] == '-F', 'short', 5, 93.8, '91.7%', 21.16),
    ("D1=8,H4=8,H1=-F", lambda s: s['d1'] == '8' and s['h4'] == '8' and s['h1'] == '-F', 'short', 10, 93.5, '85.6%', 14.81),
    ("H1=-E", lambda s: s['h1'] == '-E', 'short', 5, 92.9, '92.7%', 25.37),
    ("H1=-F", lambda s: s['h1'] == '-F', 'short', 10, 92.9, '83.5%', 12.72),
    ("H1=-6", lambda s: s['h1'] == '-6', 'short', 5, 91.4, '87.3%', 12.40),
    ("D1=-F,H1=-F", lambda s: s['d1'] == '-F' and s['h1'] == '-F', 'short', 5, 91.3, '90.9%', 19.13),
    ("D1=6,H1=2", lambda s: s['d1'] == '6' and s['h1'] == '2', 'long', 5, 90.1, '90.8%', 13.72),
]

conn = duckdb.connect('data/h1_state.duckdb')

# 获取最新状态
rows = conn.execute('''
    SELECT symbol, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex
    FROM h1_state_snapshot
    WHERE timestamp = (SELECT MAX(timestamp) FROM h1_state_snapshot)
    ORDER BY symbol
''').fetchall()

conn.close()

# 构建品种状态字典
symbols_state = {}
for r in rows:
    symbols_state[r[0]] = {
        'mn1': r[1], 'w1': r[2], 'd1': r[3], 'h4': r[4], 'h1': r[5]
    }

print("=" * 80)
print("当前市场状态与Top策略匹配分析")
print("=" * 80)
print(f"数据时间: 2026-06-04 01:00 | 品种数: {len(symbols_state)}")
print()

# 匹配策略
opportunities = []
for pattern_name, matcher, direction, hold, score, win_rate, profit_ratio in TOP_PATTERNS:
    matched = []
    for sym, state in symbols_state.items():
        if matcher(state):
            matched.append(sym)
    if matched:
        opportunities.append({
            'pattern': pattern_name,
            'direction': direction,
            'hold': hold,
            'score': score,
            'win_rate': win_rate,
            'profit_ratio': profit_ratio,
            'symbols': matched
        })

# 去重：同一品种只保留最高评分的机会
symbol_best = {}
for opp in opportunities:
    for sym in opp['symbols']:
        if sym not in symbol_best or opp['score'] > symbol_best[sym]['score']:
            symbol_best[sym] = {
                'pattern': opp['pattern'],
                'direction': opp['direction'],
                'hold': opp['hold'],
                'score': opp['score'],
                'win_rate': opp['win_rate'],
                'profit_ratio': opp['profit_ratio']
            }

if symbol_best:
    print(f"发现 {len(symbol_best)} 个交易机会：")
    print()
    print(f"{'品种':<20} | {'策略模式':<25} | {'方向':<6} | {'持仓':>4} | {'评分':>6} | {'胜率':>6} | {'盈亏比':>6}")
    print("-" * 100)
    for sym, info in sorted(symbol_best.items(), key=lambda x: -x[1]['score']):
        print(f"{sym:<20} | {info['pattern']:<25} | {info['direction']:<6} | {info['hold']:>4}h | {info['score']:>6.1f} | {info['win_rate']:>6} | {info['profit_ratio']:>6.2f}")
else:
    print("当前市场暂无品种匹配Top 10策略模式。")
    print()
    print("各品种H1 State分布：")
    h1_counts = {}
    for state in symbols_state.values():
        h1 = state['h1']
        h1_counts[h1] = h1_counts.get(h1, 0) + 1
    for h1, cnt in sorted(h1_counts.items(), key=lambda x: -x[1]):
        print(f"  H1={h1}: {cnt}个品种")

print()
print("=" * 80)
print("详细状态（按品种）")
print("=" * 80)
for sym in sorted(symbols_state.keys()):
    s = symbols_state[sym]
    match_info = symbol_best.get(sym)
    if match_info:
        flag = f" [{match_info['direction'].upper()}]"
    else:
        flag = ""
    print(f"{sym:<20} | MN1={s['mn1']:>3} | W1={s['w1']:>3} | D1={s['d1']:>3} | H4={s['h4']:>3} | H1={s['h1']:>3}{flag}")
