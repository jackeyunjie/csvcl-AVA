import duckdb
from datetime import datetime
import sys
sys.path.insert(0, '.')
from python.ai_engine.contraction_agents import (
    MultiTimeframeContractionSystem, print_contraction_report
)

# Top 策略模式 (从 strategy_mining_report_20260604_092057.md)
TOP_PATTERNS = [
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

# 按品种分别获取最新状态（解决不同品种最新时间不同的问题）
rows = conn.execute('''
    SELECT symbol, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex, timestamp
    FROM h1_state_snapshot s1
    WHERE timestamp = (
        SELECT MAX(timestamp) 
        FROM h1_state_snapshot s2 
        WHERE s2.symbol = s1.symbol
    )
    ORDER BY symbol
''').fetchall()

conn.close()

# 构建品种状态字典
symbols_state = {}
for r in rows:
    symbols_state[r[0]] = {
        'mn1': r[1], 'w1': r[2], 'd1': r[3], 'h4': r[4], 'h1': r[5],
        'timestamp': r[6]
    }

print("=" * 100)
print("AVATRADE MT5 - 当前市场状态与Top策略匹配分析")
print("=" * 100)
print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"数据覆盖: {len(symbols_state)} 个品种")
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

# 跨周期共振验证：过滤大周期冲突的假信号
def check_resonance(sym, state, direction):
    """
    验证跨周期共振：
    - LONG: 需要 D1 和 H4 至少一个支持多头（>=6 或收缩后突破）
    - SHORT: 需要 D1 和 H4 至少一个支持空头（<=-6 或收缩后突破）
    - 如果大周期完全反向，降级为"回调/反弹"而非趋势信号
    """
    mn1, w1, d1, h4, h1 = state['mn1'], state['w1'], state['d1'], state['h4'], state['h1']
    
    # 将 hex 转为数值判断趋势方向
    def hex_value(h):
        try:
            # 处理负号
            negative = h.startswith('-')
            val = int(h.lstrip('-'), 16)
            return -val if negative else val
        except:
            return 0
    
    d1_val = hex_value(d1)
    h4_val = hex_value(h4)
    w1_val = hex_value(w1)
    mn1_val = hex_value(mn1)
    
    # 判断大周期方向
    big_bull = sum([1 for v in [mn1_val, w1_val, d1_val] if v >= 6])
    big_bear = sum([1 for v in [mn1_val, w1_val, d1_val] if v <= -6])
    
    if direction == 'long':
        # LONG 需要大周期至少一个支持多头，且没有强空头冲突
        if big_bear >= 2:
            return False, "大周期强空头冲突"
        if big_bull == 0 and d1_val < 0:
            return False, "D1/H4空头无共振"
        return True, "共振确认"
    else:
        # SHORT 需要大周期至少一个支持空头，且没有强多头冲突
        if big_bull >= 2:
            return False, "大周期强多头冲突"
        if big_bear == 0 and d1_val > 0:
            return False, "D1/H4多头无共振"
        return True, "共振确认"

# 去重：同一品种只保留最高评分的机会，并验证共振
symbol_best = {}
for opp in opportunities:
    for sym in opp['symbols']:
        state = symbols_state[sym]
        resonant, reason = check_resonance(sym, state, opp['direction'])
        if not resonant:
            continue  # 过滤掉非共振信号
        if sym not in symbol_best or opp['score'] > symbol_best[sym]['score']:
            symbol_best[sym] = {
                'pattern': opp['pattern'],
                'direction': opp['direction'],
                'hold': opp['hold'],
                'score': opp['score'],
                'win_rate': opp['win_rate'],
                'profit_ratio': opp['profit_ratio'],
                'resonance': reason
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
print("=" * 100)
print("详细状态（按品种 - 仅显示指数/外汇/大宗商品）")
print("=" * 100)

# 优先显示主要交易品种
priority_symbols = ['GER30', 'UK_100', 'US_30', 'US_500', 'US_TECH100', 'JP225', 'HK_50', 
                    'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF',
                    'XAUUSD', 'USOIL', 'BRENT_OIL', 'SILVER', 'NATURAL_GAS', 'BTCUSD',
                    'FRANCE_40', 'ITALY_40', 'SWISS_20', 'EUROPE_50', 'CHINA_A50', 'GERMANY_TECH30']

print(f"{'品种':<20} | {'MN1':>4} | {'W1':>4} | {'D1':>4} | {'H4':>4} | {'H1':>4} | {'信号':<10}")
print("-" * 80)

# 判断品种状态标签（带共振验证）
def get_state_label(sym, state):
    """根据五元组判断状态标签"""
    mn1, w1, d1, h4, h1 = state['mn1'], state['w1'], state['d1'], state['h4'], state['h1']
    
    def hex_value(h):
        try:
            negative = h.startswith('-')
            val = int(h.lstrip('-'), 16)
            return -val if negative else val
        except:
            return 0
    
    d1_val = hex_value(d1)
    h4_val = hex_value(h4)
    h1_val = hex_value(h1)
    w1_val = hex_value(w1)
    mn1_val = hex_value(mn1)
    
    # 检查是否有Top策略信号
    if sym in symbol_best:
        return f"[{symbol_best[sym]['direction'].upper()}]"
    
    # 判断趋势/收缩/震荡
    big_bull = sum([1 for v in [mn1_val, w1_val, d1_val] if v >= 6])
    big_bear = sum([1 for v in [mn1_val, w1_val, d1_val] if v <= -6])
    
    h1_trend = abs(h1_val) >= 6
    h1_contract = h1 in ['C','D','E','F','-C','-D','-E','-F']
    
    if h1_trend:
        if h1_val > 0:
            if big_bull >= 1:
                return "多头趋势"
            elif big_bear >= 1:
                return "反弹(逆大周期)"
            else:
                return "多头试探"
        else:
            if big_bear >= 1:
                return "空头趋势"
            elif big_bull >= 1:
                return "回调(逆大周期)"
            else:
                return "空头试探"
    elif h1_contract:
        if big_bull >= 2 and h1_val < 0:
            return "回调收缩"
        elif big_bear >= 2 and h1_val > 0:
            return "反弹收缩"
        else:
            return "收缩整理"
    else:
        return "震荡观望"

# 先显示优先品种
for sym in priority_symbols:
    if sym in symbols_state:
        s = symbols_state[sym]
        flag = get_state_label(sym, s)
        print(f"{sym:<20} | {s['mn1']:>4} | {s['w1']:>4} | {s['d1']:>4} | {s['h4']:>4} | {s['h1']:>4} | {flag:<15}")

# 再显示其他有信号的品种
print()
if symbol_best:
    other_signals = [s for s in symbol_best.keys() if s not in priority_symbols]
    if other_signals:
        print("其他有信号品种:")
        for sym in sorted(other_signals):
            s = symbols_state[sym]
            match_info = symbol_best[sym]
            flag = get_state_label(sym, s)
            print(f"{sym:<20} | {s['mn1']:>4} | {s['w1']:>4} | {s['d1']:>4} | {s['h4']:>4} | {s['h1']:>4} | {flag:<15}")

print()
print("=" * 100)
print("多周期收缩Agent观察报告")
print("=" * 100)

# 初始化收缩跟踪系统
contraction_system = MultiTimeframeContractionSystem('data/h1_state.duckdb')

# 分析优先品种的收缩状态
priority_contraction_obs = {}
for sym in priority_symbols:
    if sym in symbols_state:
        s = symbols_state[sym]
        state = {
            'mn1_hex': s['mn1'], 'w1_hex': s['w1'], 'd1_hex': s['d1'],
            'h4_hex': s['h4'], 'h1_hex': s['h1']
        }
        obs = contraction_system.analyze_all(sym, state)
        priority_contraction_obs[sym] = obs
        
        # 只显示有收缩的品种
        contracting = [o for o in obs if o.contraction_level > 0]
        if contracting:
            print(f"\n【{sym}】")
            for o in contracting:
                alert_icon = {'normal':'○','watch':'△','alert':'▲','critical':'🔴'}.get(o.alert_level, '○')
                sync_mark = "⚡" if o.related_timeframes else ""
                print(f"  {alert_icon} {o.timeframe}:{o.hex_value} "
                      f"突破概率{o.breakout_probability:.0%}|{o.breakout_direction} "
                      f"{sync_mark}")
                if o.related_timeframes:
                    print(f"     同步: {','.join(o.related_timeframes)}")

# 找出跨周期同步收缩的关键品种
print(f"\n{'='*100}")
print("关键收缩警报（跨周期同步）")
print(f"{'='*100}")

critical_symbols = []
for sym, obs in priority_contraction_obs.items():
    sync = [o for o in obs if o.contraction_level >= 3 and o.related_timeframes]
    critical = [o for o in obs if o.alert_level == 'critical']
    if sync or critical:
        critical_symbols.append((sym, sync, critical))

if critical_symbols:
    for sym, sync, critical in sorted(critical_symbols, 
                                      key=lambda x: sum(o.contraction_level for o in x[1]), 
                                      reverse=True):
        print(f"\n🔴 {sym}")
        for o in sync:
            print(f"   {o.timeframe}:{o.hex_value} 等级{o.contraction_level} "
                  f"突破{o.breakout_direction}概率{o.breakout_probability:.0%}")
else:
    print("暂无跨周期同步收缩警报")

print()
print("=" * 100)
print("收缩/突破/趋势分析")
print("=" * 100)

# 分析收缩状态 (H1 hex 以 C/D/E/F 或 -C/-D/-E/-F 结尾表示收缩)
contraction_states = ['C', 'D', 'E', 'F', '-C', '-D', '-E', '-F']
contraction_symbols = []
for sym, state in symbols_state.items():
    if state['h1'] in contraction_states:
        contraction_symbols.append((sym, state['h1'], state['d1'], state['h4']))

if contraction_symbols:
    print(f"\nH1收缩状态品种 ({len(contraction_symbols)}个):")
    print(f"{'品种':<20} | {'H1':>4} | {'D1':>4} | {'H4':>4} | {'说明':<30}")
    print("-" * 70)
    for sym, h1, d1, h4 in sorted(contraction_symbols, key=lambda x: x[1]):
        desc = ""
        if h1 in ['F', '-F']:
            desc = "强收缩 - 等待突破"
        elif h1 in ['E', '-E']:
            desc = "收缩中 - 观察"
        elif h1 in ['D', '-D']:
            desc = "轻微收缩"
        elif h1 in ['C', '-C']:
            desc = "早期收缩"
        print(f"{sym:<20} | {h1:>4} | {d1:>4} | {h4:>4} | {desc:<30}")

# 分析趋势状态 (H1 hex 为 6/7/8 或 -6/-7/-8 表示趋势，带共振验证)
trend_states = ['6', '7', '8', '-6', '-7', '-8']
trend_symbols = []
for sym, state in symbols_state.items():
    if state['h1'] in trend_states:
        trend_symbols.append((sym, state['h1'], state['d1'], state['h4'], state['w1'], state['mn1']))

if trend_symbols:
    print(f"\nH1趋势状态品种 ({len(trend_symbols)}个):")
    print(f"{'品种':<20} | {'H1':>4} | {'D1':>4} | {'H4':>4} | {'方向':<15} | {'共振':<10}")
    print("-" * 80)
    for sym, h1, d1, h4, w1, mn1 in sorted(trend_symbols, key=lambda x: x[1]):
        def hex_value(h):
            try:
                negative = h.startswith('-')
                val = int(h.lstrip('-'), 16)
                return -val if negative else val
            except:
                return 0
        
        d1_val = hex_value(d1)
        h4_val = hex_value(h4)
        h1_val = hex_value(h1)
        w1_val = hex_value(w1)
        mn1_val = hex_value(mn1)
        
        big_bull = sum([1 for v in [mn1_val, w1_val, d1_val] if v >= 6])
        big_bear = sum([1 for v in [mn1_val, w1_val, d1_val] if v <= -6])
        
        if h1_val > 0:
            if big_bear >= 2:
                direction = "反弹(逆大周期)"
                resonance = "⚠弱"
            elif big_bull >= 1:
                direction = "多头趋势"
                resonance = "✓强"
            else:
                direction = "多头试探"
                resonance = "△中"
        else:
            if big_bull >= 2:
                direction = "回调(逆大周期)"
                resonance = "⚠弱"
            elif big_bear >= 1:
                direction = "空头趋势"
                resonance = "✓强"
            else:
                direction = "空头试探"
                resonance = "△中"
        
        print(f"{sym:<20} | {h1:>4} | {d1:>4} | {h4:>4} | {direction:<15} | {resonance:<10}")

print()
print("=" * 100)
