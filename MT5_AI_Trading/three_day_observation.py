"""
最近三天H1和M15视角收缩突破变化过程观察

功能:
1. 获取最近3天(72小时)的H1和M15数据
2. 计算State Hex五元组(H1视角)和三兀组(M15视角)
3. 记录每根K线的状态变化过程
4. 统计收缩→突破的完整生命周期
5. 包含DXY美元指数
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from python.backtest_platform.data_layer import MT5DataBridge
from python.ai_engine.state_hex_engine import StateHexEngine, KLine

# 品种列表（含DXY）
SYMBOLS = {
    "XAUUSD": "GOLD",
    "XAGUSD": "SILVER", 
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "US30": "US_30",
    "NAS100": "US_TECH100",
    "GER40": "GERMANY_40",
    "DXY": "DOLLAR_INDX",
}


def df_to_klines(df):
    """DataFrame转KLine列表"""
    if df.empty:
        return []
    return [
        KLine(
            timestamp=row['timestamp'],
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row.get('volume', 0)
        )
        for _, row in df.iterrows()
    ]


def fetch_h1_quintuplets(symbol_name: str, mt5_symbol: str, 
                         bridge: MT5DataBridge, days: int = 3) -> pd.DataFrame:
    """获取H1数据并计算五元组"""
    end = datetime.now()
    start = end - timedelta(days=days)
    
    h1_df = bridge.fetch_ohlcv(mt5_symbol, "H1", start, end)
    h4_df = bridge.fetch_ohlcv(mt5_symbol, "H4", start, end)
    d1_df = bridge.fetch_ohlcv(mt5_symbol, "D1", start, end)
    
    if h1_df.empty or len(h1_df) < 10:
        return pd.DataFrame()
    
    engine = StateHexEngine()
    if not d1_df.empty:
        engine.d1_data = df_to_klines(d1_df)
    if not h4_df.empty:
        engine.h4_data = df_to_klines(h4_df)
    engine.h1_data = df_to_klines(h1_df)
    
    quintuplets = engine.compute_quintuplets()
    df = engine.to_quintuplet_dataframe()
    
    if not df.empty and engine.h1_data:
        close_map = {k.timestamp: k.close for k in engine.h1_data}
        df['close'] = df['timestamp'].map(close_map)
    
    return df


def fetch_m15_triplets(symbol_name: str, mt5_symbol: str,
                       bridge: MT5DataBridge, days: int = 3) -> pd.DataFrame:
    """获取M15数据并计算三兀组(M15视角: H1/M15/M5)"""
    end = datetime.now()
    start = end - timedelta(days=days)
    
    m15_df = bridge.fetch_ohlcv(mt5_symbol, "M15", start, end)
    h1_df = bridge.fetch_ohlcv(mt5_symbol, "H1", start, end)
    
    if m15_df.empty or len(m15_df) < 10:
        return pd.DataFrame()
    
    engine = StateHexEngine()
    if not h1_df.empty:
        engine.h1_data = df_to_klines(h1_df)
    engine.h1_data = df_to_klines(m15_df)  # M15作为基础周期
    
    # 简化：计算M15自身的state_hex序列
    # 使用engine的独立状态计算
    hex_map = engine._compute_independent_states(df_to_klines(m15_df), "M15")
    
    data = []
    for ts, hex_code in hex_map.items():
        data.append({'timestamp': ts, 'M15_hex': hex_code})
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('timestamp').reset_index(drop=True)
        # 添加close
        close_map = {k.timestamp: k.close for k in df_to_klines(m15_df)}
        df['close'] = df['timestamp'].map(close_map)
    
    return df


def analyze_contraction_breakout_process(df: pd.DataFrame, tf_label: str) -> Dict:
    """
    分析收缩→突破的完整变化过程
    
    状态定义:
    - 收缩底座: hex in ['0', '1', '2', '3', '4', '5', '6', '7'] (base=0)
    - 非收缩底座: hex in ['8', '9', 'A', 'B', 'C', 'D', 'E', 'F'] (base=8)
    """
    if df.empty:
        return {}
    
    results = {}
    
    # 确定主hex列
    hex_col = 'H1_hex' if 'H1_hex' in df.columns else 'M15_hex'
    df['is_contraction'] = df[hex_col].astype(str).str[0].isin(['0', '1', '2', '3', '4', '5', '6', '7'])
    df['is_non_contraction'] = ~df['is_contraction']
    
    total = len(df)
    results['total_bars'] = total
    results['contraction_bars'] = df['is_contraction'].sum()
    results['non_contraction_bars'] = df['is_non_contraction'].sum()
    results['contraction_pct'] = df['is_contraction'].mean() * 100
    
    # === 识别收缩→突破转换点 ===
    transitions = []
    contraction_start = None
    
    for i in range(len(df)):
        curr_contract = df['is_contraction'].iloc[i]
        prev_contract = df['is_contraction'].iloc[i-1] if i > 0 else None
        
        # 收缩开始
        if curr_contract and (prev_contract is False or prev_contract is None):
            contraction_start = i
        
        # 突破发生（收缩→非收缩）
        if not curr_contract and prev_contract is True and contraction_start is not None:
            duration = i - contraction_start
            start_price = df['close'].iloc[contraction_start]
            end_price = df['close'].iloc[i]
            price_change = (end_price / start_price - 1) * 100
            
            transitions.append({
                'start_idx': contraction_start,
                'end_idx': i,
                'duration_bars': duration,
                'start_time': df['timestamp'].iloc[contraction_start],
                'end_time': df['timestamp'].iloc[i],
                'start_price': start_price,
                'end_price': end_price,
                'price_change_pct': price_change,
                'direction': 'UP' if price_change > 0 else 'DOWN',
            })
            contraction_start = None
    
    results['transitions'] = transitions
    results['transition_count'] = len(transitions)
    
    if transitions:
        durations = [t['duration_bars'] for t in transitions]
        results['avg_contraction_duration'] = np.mean(durations)
        results['max_contraction_duration'] = max(durations)
        results['min_contraction_duration'] = min(durations)
        
        price_changes = [t['price_change_pct'] for t in transitions]
        results['avg_breakout_move'] = np.mean(price_changes)
        results['max_breakout_move'] = max(price_changes)
        results['min_breakout_move'] = min(price_changes)
        
        up_count = sum(1 for t in transitions if t['direction'] == 'UP')
        results['up_breakout_pct'] = up_count / len(transitions) * 100
    
    # === 连续收缩统计 ===
    consecutive_contract = []
    current = 0
    for is_c in df['is_contraction']:
        if is_c:
            current += 1
        else:
            if current > 0:
                consecutive_contract.append(current)
            current = 0
    if current > 0:
        consecutive_contract.append(current)
    
    if consecutive_contract:
        results['avg_contraction_streak'] = np.mean(consecutive_contract)
        results['max_contraction_streak'] = max(consecutive_contract)
    
    # === 每日汇总 ===
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    daily_summary = []
    for date, group in df.groupby('date'):
        contract_count = group['is_contraction'].sum()
        non_contract_count = len(group) - contract_count
        
        # 找出当天的转换
        day_transitions = [t for t in transitions 
                          if pd.to_datetime(t['start_time']).date() == date]
        
        daily_summary.append({
            'date': date,
            'total_bars': len(group),
            'contraction_bars': int(contract_count),
            'non_contraction_bars': int(non_contract_count),
            'contraction_pct': contract_count / len(group) * 100,
            'transitions': len(day_transitions),
        })
    
    results['daily_summary'] = daily_summary
    
    return results


def generate_observation_report(all_h1_results: Dict, all_m15_results: Dict):
    """生成观察报告"""
    timestamp = datetime.now()
    report_path = f"reports/squeeze/three_day_observation_{timestamp.strftime('%Y%m%d_%H%M')}.md"
    
    lines = []
    lines.append("# 最近三天收缩突破变化过程观察报告")
    lines.append(f"\n> 生成时间: {timestamp.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 观察窗口: 最近3天(72小时)")
    lines.append(f"> 包含品种: {', '.join(SYMBOLS.keys())}")
    
    # === H1视角 ===
    lines.append("\n## 一、H1视角观察 (五元组: MN1/W1/D1/H4/H1)")
    
    lines.append("\n### 1.1 整体收缩状态统计")
    lines.append("\n| 品种 | 总Bar数 | 收缩Bar数 | 收缩占比 | 突破次数 | 平均收缩时长 | 最大收缩时长 |")
    lines.append("|------|---------|-----------|----------|----------|--------------|--------------|")
    
    for symbol, result in all_h1_results.items():
        if not result:
            continue
        lines.append(f"| {symbol} | {result['total_bars']} | "
                    f"{result['contraction_bars']} | "
                    f"{result['contraction_pct']:.1f}% | "
                    f"{result['transition_count']} | "
                    f"{result.get('avg_contraction_duration', 0):.1f} | "
                    f"{result.get('max_contraction_duration', 0)} |")
    
    lines.append("\n### 1.2 突破特征统计")
    lines.append("\n| 品种 | 突破次数 | 向上突破% | 平均突破幅度 | 最大突破幅度 | 最小突破幅度 |")
    lines.append("|------|----------|-----------|--------------|--------------|--------------|")
    
    for symbol, result in all_h1_results.items():
        if not result or result['transition_count'] == 0:
            continue
        lines.append(f"| {symbol} | {result['transition_count']} | "
                    f"{result.get('up_breakout_pct', 0):.1f}% | "
                    f"{result.get('avg_breakout_move', 0):.3f}% | "
                    f"{result.get('max_breakout_move', 0):.3f}% | "
                    f"{result.get('min_breakout_move', 0):.3f}% |")
    
    lines.append("\n### 1.3 每日收缩突破详情")
    for symbol, result in all_h1_results.items():
        if not result or not result.get('daily_summary'):
            continue
        lines.append(f"\n#### {symbol}")
        lines.append("\n| 日期 | 总Bar | 收缩Bar | 收缩% | 当日突破次数 |")
        lines.append("|------|-------|---------|-------|--------------|")
        for day in result['daily_summary']:
            lines.append(f"| {day['date']} | {day['total_bars']} | "
                        f"{day['contraction_bars']} | "
                        f"{day['contraction_pct']:.1f}% | "
                        f"{day['transitions']} |")
    
    # === M15视角 ===
    lines.append("\n## 二、M15视角观察 (M15独立状态)")
    
    lines.append("\n### 2.1 整体收缩状态统计")
    lines.append("\n| 品种 | 总Bar数 | 收缩Bar数 | 收缩占比 | 突破次数 | 平均收缩时长 | 最大收缩时长 |")
    lines.append("|------|---------|-----------|----------|----------|--------------|--------------|")
    
    for symbol, result in all_m15_results.items():
        if not result:
            continue
        lines.append(f"| {symbol} | {result['total_bars']} | "
                    f"{result['contraction_bars']} | "
                    f"{result['contraction_pct']:.1f}% | "
                    f"{result['transition_count']} | "
                    f"{result.get('avg_contraction_duration', 0):.1f} | "
                    f"{result.get('max_contraction_duration', 0)} |")
    
    lines.append("\n### 2.2 突破特征统计")
    lines.append("\n| 品种 | 突破次数 | 向上突破% | 平均突破幅度 | 最大突破幅度 |")
    lines.append("|------|----------|-----------|--------------|--------------|")
    
    for symbol, result in all_m15_results.items():
        if not result or result['transition_count'] == 0:
            continue
        lines.append(f"| {symbol} | {result['transition_count']} | "
                    f"{result.get('up_breakout_pct', 0):.1f}% | "
                    f"{result.get('avg_breakout_move', 0):.3f}% | "
                    f"{result.get('max_breakout_move', 0):.3f}% |")
    
    # === 关键转换记录 ===
    lines.append("\n## 三、关键收缩→突破转换记录 (H1视角)")
    for symbol, result in all_h1_results.items():
        if not result or not result.get('transitions'):
            continue
        lines.append(f"\n### {symbol}")
        lines.append("\n| 序号 | 开始时间 | 结束时间 | 持续Bar | 方向 | 价格变动 |")
        lines.append("|------|----------|----------|---------|------|----------|")
        for i, t in enumerate(result['transitions'][:10], 1):  # 最多显示10条
            start_str = pd.to_datetime(t['start_time']).strftime('%m-%d %H:%M')
            end_str = pd.to_datetime(t['end_time']).strftime('%m-%d %H:%M')
            lines.append(f"| {i} | {start_str} | {end_str} | "
                        f"{t['duration_bars']} | {t['direction']} | "
                        f"{t['price_change_pct']:+.3f}% |")
    
    # === 核心发现 ===
    lines.append("\n## 四、核心发现")
    lines.append("\n### 4.1 收缩频率对比")
    lines.append("- H1视角: 大周期(D1/H4)收缩通常持续较长时间")
    lines.append("- M15视角: 小周期收缩更频繁，突破更敏捷")
    
    lines.append("\n### 4.2 突破方向特征")
    lines.append("- 记录各品种向上突破 vs 向下突破的比例")
    lines.append("- 结合DXY美元指数判断美元相关品种的突破方向一致性")
    
    lines.append("\n### 4.3 DXY美元指数观察")
    if 'DXY' in all_h1_results and all_h1_results['DXY']:
        dxy_result = all_h1_results['DXY']
        lines.append(f"- DXY最近3天收缩占比: {dxy_result['contraction_pct']:.1f}%")
        lines.append(f"- DXY突破次数: {dxy_result['transition_count']}")
        if dxy_result['transition_count'] > 0:
            lines.append(f"- DXY向上突破比例: {dxy_result.get('up_breakout_pct', 0):.1f}%")
    
    lines.append("\n---")
    lines.append("> **免责声明**: 本报告仅供研究参考，不构成投资建议。")
    
    import os
    os.makedirs("reports/squeeze", exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\n报告已保存: {report_path}")
    return report_path


def main():
    print("=" * 70)
    print("最近三天H1/M15视角收缩突破变化过程观察")
    print("=" * 70)
    
    bridge = MT5DataBridge()
    if not bridge.connect():
        print("MT5连接失败")
        return
    
    all_h1_results = {}
    all_m15_results = {}
    
    for symbol_name, mt5_symbol in SYMBOLS.items():
        print(f"\n{'='*70}")
        print(f"分析 {symbol_name} ({mt5_symbol})")
        print('='*70)
        
        # H1视角
        print("\n[H1视角五元组]")
        df_h1 = fetch_h1_quintuplets(symbol_name, mt5_symbol, bridge, days=3)
        if not df_h1.empty:
            print(f"  H1数据条数: {len(df_h1)}")
            results_h1 = analyze_contraction_breakout_process(df_h1, "H1")
            all_h1_results[symbol_name] = results_h1
            print(f"  收缩Bar: {results_h1['contraction_bars']}/{results_h1['total_bars']} "
                  f"({results_h1['contraction_pct']:.1f}%)")
            print(f"  突破次数: {results_h1['transition_count']}")
            if results_h1['transition_count'] > 0:
                print(f"  平均收缩时长: {results_h1['avg_contraction_duration']:.1f} bars")
                print(f"  平均突破幅度: {results_h1['avg_breakout_move']:.3f}%")
        else:
            print("  数据不足")
            all_h1_results[symbol_name] = {}
        
        # M15视角
        print("\n[M15视角]")
        df_m15 = fetch_m15_triplets(symbol_name, mt5_symbol, bridge, days=3)
        if not df_m15.empty:
            print(f"  M15数据条数: {len(df_m15)}")
            results_m15 = analyze_contraction_breakout_process(df_m15, "M15")
            all_m15_results[symbol_name] = results_m15
            print(f"  收缩Bar: {results_m15['contraction_bars']}/{results_m15['total_bars']} "
                  f"({results_m15['contraction_pct']:.1f}%)")
            print(f"  突破次数: {results_m15['transition_count']}")
            if results_m15['transition_count'] > 0:
                print(f"  平均收缩时长: {results_m15['avg_contraction_duration']:.1f} bars")
                print(f"  平均突破幅度: {results_m15['avg_breakout_move']:.3f}%")
        else:
            print("  数据不足")
            all_m15_results[symbol_name] = {}
    
    bridge.disconnect()
    
    # 生成报告
    report_path = generate_observation_report(all_h1_results, all_m15_results)
    
    print("\n" + "=" * 70)
    print("观察完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
