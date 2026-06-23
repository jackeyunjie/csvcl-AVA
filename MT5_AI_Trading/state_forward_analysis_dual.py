"""
State前向收益分析 - 双MT5平台
支持 KVB Prime MT5 + Ava Trade MT5
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
print("State前向收益分析 - 双MT5平台")
print("="*70)

# MT5平台配置
PLATFORMS = {
    "KVB": {
        "path": r"C:\Program Files\KVB Prime MT5 Terminal\terminal64.exe",
        "label": "KVB Prime"
    },
    "AVATRADE": {
        "path": r"D:\Program Files\Ava Trade MT5 Terminal\terminal64.exe", 
        "label": "Ava Trade"
    }
}

def calc_state(closes):
    """计算State编码"""
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

def analyze_platform(platform_key, platform_config):
    """分析单个平台"""
    label = platform_config["label"]
    path = platform_config["path"]
    
    print(f"\n{'='*70}")
    print(f"[{label}] 分析开始")
    print(f"{'='*70}")
    
    # 初始化MT5
    print(f"\n连接 {label}...")
    if not mt5.initialize(path=path):
        print(f"{label} 连接失败")
        return None
    print(f"{label} 已连接")
    
    # 获取品种列表
    symbols = [get_mt5_symbol(s, platform_key) for s in USER_SYMBOLS]
    
    all_data = []
    success = []
    failed = []
    
    for idx, symbol in enumerate(symbols, 1):
        user_name = USER_SYMBOLS[idx-1]
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 99999)
        if rates is None or len(rates) == 0:
            failed.append(user_name)
            continue
        
        closes = rates['close']
        times = rates['time']
        n = len(rates)
        
        cat = get_category(user_name)
        count = 0
        
        # 每20天采样
        for i in range(200, n - 20, 20):
            state, ef = calc_state(closes[:i+1])
            cp = closes[i]
            
            all_data.append({
                'platform': label,
                'user_symbol': user_name,
                'mt5_symbol': symbol,
                'category': cat,
                'timestamp': datetime.fromtimestamp(times[i]).strftime('%Y-%m-%d'),
                'state_hex': state,
                'ef_count': ef,
                'close_price': float(cp),
                'forward_return_1d': float((closes[i+1] - cp) / cp),
                'forward_return_5d': float((closes[i+5] - cp) / cp),
                'forward_return_20d': float((closes[i+20] - cp) / cp)
            })
            count += 1
        
        success.append(user_name)
        print(f"  [{idx:2d}/{len(symbols)}] {user_name:10s} ({cat:4s}): {count:4d} 样本")
    
    mt5.shutdown()
    
    print(f"\n  成功: {len(success)} | 失败: {len(failed)}")
    if failed:
        print(f"  失败: {', '.join(failed)}")
    print(f"  总样本: {len(all_data)}")
    
    return {
        'platform': label,
        'data': all_data,
        'success': success,
        'failed': failed
    }

# =====================================================================
# 分析两个平台
# =====================================================================
results = {}
for key, config in PLATFORMS.items():
    results[key] = analyze_platform(key, config)

# 合并数据
all_data = []
for r in results.values():
    if r and r['data']:
        all_data.extend(r['data'])

if len(all_data) == 0:
    print("无数据，退出")
    exit(1)

print(f"\n{'='*70}")
print(f"双平台总样本: {len(all_data)}")
print(f"{'='*70}")

# =====================================================================
# DuckDB分析
# =====================================================================
conn = duckdb.connect(":memory:")
df = pd.DataFrame(all_data)
conn.register('state_data', df)
conn.execute('CREATE TABLE state_analysis AS SELECT * FROM state_data')

# 1. 平台对比
print("\n【平台对比】")
platform_cmp = conn.execute('''
    SELECT 
        platform,
        COUNT(*) as n,
        COUNT(DISTINCT user_symbol) as symbols,
        ROUND(AVG(forward_return_5d)*100, 3) as ret_5d,
        ROUND(SUM(CASE WHEN forward_return_5d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as wr_5d
    FROM state_analysis
    GROUP BY platform
''').fetchdf()
print(platform_cmp.to_string(index=False))

# 2. EF共振分析 (双平台合并)
print("\n【EF共振分析 - 双平台合并】")
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
print(ef_analysis.to_string(index=False))

# 3. TOP20高胜率模式
print("\n【TOP20 高胜率State模式】")
top20 = conn.execute('''
    SELECT 
        state_hex as pattern,
        ef_count,
        COUNT(*) as n,
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
print(top20.to_string(index=False))

# 4. 分类别统计
print("\n【分类别统计】")
cat_stats = conn.execute('''
    SELECT 
        category,
        COUNT(*) as n,
        COUNT(DISTINCT user_symbol) as symbols,
        ROUND(AVG(forward_return_5d)*100, 3) as ret_5d,
        ROUND(SUM(CASE WHEN forward_return_5d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as wr_5d
    FROM state_analysis
    GROUP BY category
    ORDER BY n DESC
''').fetchdf()
print(cat_stats.to_string(index=False))

# =====================================================================
# 保存报告
# =====================================================================
report = {
    "generated_at": datetime.now().isoformat(),
    "platforms": {k: {
        "label": v["label"],
        "success": results[k]["success"] if results[k] else [],
        "failed": results[k]["failed"] if results[k] else []
    } for k, v in PLATFORMS.items()},
    "total_samples": len(all_data),
    "ef_analysis": ef_analysis.to_dict('records'),
    "top20_patterns": top20.to_dict('records'),
    "category_stats": cat_stats.to_dict('records'),
}

Path("data").mkdir(exist_ok=True)
with open("data/state_analysis_dual_report.json", 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2, default=str)

top20.to_csv("data/top20_dual.csv", index=False, encoding='utf-8-sig')

print(f"\n{'='*70}")
print("报告已保存:")
print("  data/state_analysis_dual_report.json")
print("  data/top20_dual.csv")
print(f"{'='*70}")

conn.close()
print("\n分析完成!")
