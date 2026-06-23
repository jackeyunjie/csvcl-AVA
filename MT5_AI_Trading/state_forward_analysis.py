"""
State前向收益分析 - KVB MT4/MT5 全品种
分批处理，高效计算
"""
import duckdb
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import MetaTrader5 as mt5
from symbol_mapping_dual import get_mt5_symbol, get_category, USER_SYMBOLS

print("="*70)
print("State前向收益分析 - KVB全品种(含对照表)")
print("="*70)

# 选择平台: "KVB" 或 "AVATRADE"
PLATFORM = "KVB"  # 默认使用KVB

# 使用对照表转换品种名
SYMBOLS = [get_mt5_symbol(s, PLATFORM) for s in USER_SYMBOLS]
print(f"使用平台: {PLATFORM}")
print(f"品种数: {len(SYMBOLS)}")

# 初始化MT5
print("\n[1/4] 连接MT5...")
if not mt5.initialize():
    print("MT5初始化失败")
    exit(1)
print("MT5已连接")

conn = duckdb.connect(":memory:")

def calc_state(closes):
    n = len(closes)
    if n < 35:
        return "C=L", 0
    
    sma20 = np.mean(closes[-20:])
    std20 = np.std(closes[-20:])
    price = closes[-1]
    
    if std20 == 0:
        pos = "C"
    elif price > sma20 + 2*std20:
        pos = "A"
    elif price > sma20 + 0.5*std20:
        pos = "B"
    elif price > sma20 - 0.5*std20:
        pos = "C"
    elif price > sma20 - 2*std20:
        pos = "D"
    else:
        pos = "E"
    
    ema10 = np.mean(closes[-10:])
    ema30 = np.mean(closes[-30:])
    if ema10 > ema30 * 1.001:
        trend = "+"
    elif ema10 < ema30 * 0.999:
        trend = "-"
    else:
        trend = "="
    
    recent = closes[-16:]
    changes = np.diff(recent) / recent[:-1]
    vol = np.std(changes)
    if vol > 0.015:
        vol_state = "H"
    elif vol > 0.008:
        vol_state = "M"
    else:
        vol_state = "L"
    
    state = f"{pos}{trend}{vol_state}"
    
    ef = 0
    if pos in ["D", "E"] and trend == "-":
        ef += 1
    if pos in ["A", "B"] and trend == "+":
        ef += 1
    if vol_state == "H":
        ef += 1
    
    return state, ef

# =====================================================================
# 步骤1: 从MT5获取数据
# =====================================================================
print("\n[2/4] 从MT5获取数据...")

all_data = []
success = []
failed = []

for idx, symbol in enumerate(SYMBOLS, 1):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 99999)
    if rates is None or len(rates) == 0:
        failed.append(symbol)
        continue
    
    closes = rates['close']
    times = rates['time']
    n = len(rates)
    
    cat = get_category(symbol)
    count = 0
    
    # 每20天采样
    for i in range(200, n - 20, 20):
        state, ef = calc_state(closes[:i+1])
        cp = closes[i]
        
        all_data.append({
            'symbol': symbol,
            'category': cat,
            'timestamp': datetime.fromtimestamp(times[i]).strftime('%Y-%m-%d'),
            'state_hex': state,
            'ef_count': ef,
            'forward_return_1d': float((closes[i+1] - cp) / cp),
            'forward_return_5d': float((closes[i+5] - cp) / cp),
            'forward_return_20d': float((closes[i+20] - cp) / cp)
        })
        count += 1
    
    success.append(symbol)
    print(f"  [{idx:2d}/{len(SYMBOLS)}] {symbol:10s} ({cat:4s}): {count:4d} 样本")

mt5.shutdown()

print(f"\n  成功: {len(success)} 品种 | 失败: {len(failed)} 品种")
if failed:
    print(f"  失败: {', '.join(failed)}")
print(f"  总样本: {len(all_data)} 条")

if len(all_data) == 0:
    print("无数据，退出")
    exit(1)

# 创建DuckDB表
df = pd.DataFrame(all_data)
conn.register('state_data', df)
conn.execute('CREATE TABLE state_analysis AS SELECT * FROM state_data')

# =====================================================================
# 步骤2: State组合表现
# =====================================================================
print("\n[3/4] State组合历史表现...")

state_perf = conn.execute('''
    SELECT 
        state_hex as pattern,
        COUNT(*) as n,
        ROUND(AVG(forward_return_1d)*100, 3) as ret_1d,
        ROUND(AVG(forward_return_5d)*100, 3) as ret_5d,
        ROUND(AVG(forward_return_20d)*100, 3) as ret_20d,
        ROUND(SUM(CASE WHEN forward_return_5d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as wr_5d,
        ROUND(SUM(CASE WHEN forward_return_1d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as wr_1d,
        ROUND(SUM(CASE WHEN forward_return_20d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as wr_20d,
        ROUND(STDDEV(forward_return_5d)*100, 3) as vol_5d,
        ROUND(AVG(forward_return_5d) / NULLIF(STDDEV(forward_return_5d), 0), 3) as sharpe
    FROM state_analysis
    GROUP BY state_hex
    HAVING COUNT(*) >= 5
    ORDER BY ret_5d DESC
''').fetchdf()

print(f"  发现 {len(state_perf)} 种State模式")
print("\n  TOP15 State模式 (按5日收益排序):")
print(state_perf.head(15).to_string(index=False))

# 分类别表现
print("\n  分类别TOP5:")
for cat in ["股指", "外汇", "现货", "个股", "加密货币"]:
    cat_df = conn.execute(f'''
        SELECT state_hex, COUNT(*) as n,
               ROUND(AVG(forward_return_5d)*100, 3) as ret_5d,
               ROUND(SUM(CASE WHEN forward_return_5d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as wr_5d
        FROM state_analysis
        WHERE category = '{cat}'
        GROUP BY state_hex
        HAVING COUNT(*) >= 3
        ORDER BY ret_5d DESC
        LIMIT 5
    ''').fetchdf()
    if len(cat_df) > 0:
        print(f"\n  {cat}:")
        print(cat_df.to_string(index=False))

# =====================================================================
# 步骤3: EF共振分析
# =====================================================================
print("\n[4/4] EF共振胜率分析...")

ef_analysis = conn.execute('''
    SELECT 
        ef_count,
        COUNT(*) as n,
        ROUND(AVG(forward_return_5d)*100, 3) as ret_5d,
        ROUND(SUM(CASE WHEN forward_return_5d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as wr_5d,
        ROUND(AVG(forward_return_1d)*100, 3) as ret_1d,
        ROUND(AVG(forward_return_20d)*100, 3) as ret_20d,
        ROUND(STDDEV(forward_return_5d)*100, 3) as vol,
        ROUND(AVG(forward_return_5d) / NULLIF(STDDEV(forward_return_5d), 0), 3) as sharpe
    FROM state_analysis
    GROUP BY ef_count
    ORDER BY ef_count DESC
''').fetchdf()

print("\n  EF共振分析:")
print(ef_analysis.to_string(index=False))

# TOP20高胜率
top20 = conn.execute('''
    SELECT 
        state_hex as pattern, ef_count, COUNT(*) as n,
        ROUND(AVG(forward_return_5d)*100, 3) as ret_5d,
        ROUND(SUM(CASE WHEN forward_return_5d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as wr_5d,
        ROUND(AVG(forward_return_1d)*100, 3) as ret_1d,
        ROUND(AVG(forward_return_20d)*100, 3) as ret_20d,
        ROUND(STDDEV(forward_return_5d)*100, 3) as vol,
        ROUND(AVG(forward_return_5d) / NULLIF(STDDEV(forward_return_5d), 0), 3) as sharpe
    FROM state_analysis
    GROUP BY state_hex, ef_count
    HAVING COUNT(*) >= 5
    ORDER BY wr_5d DESC, ret_5d DESC
    LIMIT 20
''').fetchdf()

print("\n  TOP20 高胜率State模式:")
print(top20.to_string(index=False))

# =====================================================================
# 保存报告
# =====================================================================
report = {
    "generated_at": datetime.now().isoformat(),
    "total_samples": len(all_data),
    "symbols_success": success,
    "symbols_failed": failed,
    "ef_analysis": ef_analysis.to_dict('records'),
    "top20_patterns": top20.to_dict('records'),
}

Path("data").mkdir(exist_ok=True)
with open("data/state_analysis_report.json", 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2, default=str)

top20.to_csv("data/top20_patterns.csv", index=False, encoding='utf-8-sig')
state_perf.to_csv("data/all_patterns.csv", index=False, encoding='utf-8-sig')

print(f"\n{'='*70}")
print("报告已保存:")
print("  data/state_analysis_report.json")
print("  data/top20_patterns.csv")
print("  data/all_patterns.csv")
print(f"{'='*70}")

print("\n【EF共振效果】")
for _, row in ef_analysis.iterrows():
    print(f"  EF={int(row['ef_count'])}: 样本{int(row['n'])} | 5日收益{row['ret_5d']}% | 胜率{row['wr_5d']}% | 夏普{row['sharpe']}")

conn.close()
print(f"\n{'='*70}")
print("分析完成!")
print(f"{'='*70}")
