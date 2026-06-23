#!/usr/bin/env python3
"""
v4 Phase 1 诊断分析脚本
基于v3 CSV输出，不动主体代码，纯数据探查验证假设A/B/C/D

假设A: 趋势强度替代趋势方向
假设B: 收缩质量分层
假设C: 突破确认机制
假设D: 品种选择优化
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter

# 加载v3数据
SETUPS_PATH = Path("reports/squeeze/squeeze_mt_setups_v3_20260605_1333.csv")
EVENTS_PATH = Path("reports/squeeze/squeeze_mt_events_v3_20260605_1333.csv")
TRADES_PATH = Path("reports/squeeze/squeeze_mt_trades_v3_20260605_1333.csv")

def load_data():
    setups = pd.read_csv(SETUPS_PATH)
    events = pd.read_csv(EVENTS_PATH)
    trades = pd.read_csv(TRADES_PATH)
    setups['timestamp'] = pd.to_datetime(setups['timestamp'])
    events['breakout_timestamp'] = pd.to_datetime(events['breakout_timestamp'])
    return setups, events, trades


def analyze_hypothesis_a(events):
    """假设A: 趋势强度替代趋势方向
    
    当前: bullish/bearish/neutral (只看方向)
    改进: strong/weak/neutral (看强度)
    
    但v3 CSV没有保存h4_adx/d1_adx... 需要用现有trend_bias + returns做间接分析
    """
    print("=" * 70)
    print("假设A: 趋势强度替代趋势方向")
    print("=" * 70)
    
    # 当前分层
    print("\n【当前趋势分层 (方向-only)】")
    for ta in ['with_trend', 'against_trend', 'neutral']:
        sub = events[events['trend_alignment'] == ta]
        win = (sub['returns_5bar'] > 0).mean() * 100
        exp = sub['returns_5bar'].mean() * 100
        print(f"  {ta:15s}: n={len(sub):4d}, 胜率={win:.1f}%, 期望={exp:.3f}%")
    
    # H4×D1 交叉分析 (用现有bias做强度代理)
    print("\n【H4×D1 趋势共振交叉】")
    events['h4d1'] = events['h4_trend_bias'] + '_' + events['d1_trend_bias']
    for combo in events['h4d1'].value_counts().index:
        sub = events[events['h4d1'] == combo]
        if len(sub) < 30:
            continue
        win = (sub['returns_5bar'] > 0).mean() * 100
        exp = sub['returns_5bar'].mean() * 100
        print(f"  {combo:25s}: n={len(sub):4d}, 胜率={win:.1f}%, 期望={exp:.3f}%")
    
    # 关键发现: 如果bullish+bullish vs bullish+neutral vs neutral+neutral的胜率差异
    strong = events[events['h4d1'].isin(['bullish_bullish', 'bearish_bearish'])]
    mixed = events[events['h4d1'].isin(['bullish_neutral', 'bearish_neutral', 'neutral_bullish', 'neutral_bearish'])]
    weak = events[events['h4d1'] == 'neutral_neutral']
    
    print(f"\n【强度代理分组】")
    for name, sub in [('双周期同向(强)', strong), ('单周期方向(中)', mixed), ('双neutral(弱)', weak)]:
        if len(sub) > 0:
            win = (sub['returns_5bar'] > 0).mean() * 100
            exp = sub['returns_5bar'].mean() * 100
            print(f"  {name:20s}: n={len(sub):4d}, 胜率={win:.1f}%, 期望={exp:.3f}%")
    
    # MFE分析: 强趋势下突破是否有更大运行空间
    print(f"\n【MFE对比 (突破后最大有利波动)】")
    for name, sub in [('双周期同向', strong), ('单周期方向', mixed), ('双neutral', weak)]:
        if len(sub) > 0:
            mfe = sub['mfe_pct'].mean() * 100
            mae = sub['mae_pct'].mean() * 100
            print(f"  {name:20s}: MFE={mfe:.3f}%, MAE={mae:.3f}%, MFE/MAE={mfe/max(mae,0.001):.2f}")
    
    return strong, mixed, weak


def analyze_hypothesis_b(setups, events):
    """假设B: 收缩质量分层
    
    分析score各子条件对胜率的贡献
    """
    print("\n" + "=" * 70)
    print("假设B: 收缩质量分层")
    print("=" * 70)
    
    # 合并setup和event
    merged = events.merge(setups[['setup_id', 'squeeze_score', 'conditions', 'adx', 'anchor_range_pct']], 
                          on='setup_id', how='left')
    
    print("\n【按Score分层】")
    for score in sorted(merged['squeeze_score'].unique()):
        sub = merged[merged['squeeze_score'] == score]
        win = (sub['returns_5bar'] > 0).mean() * 100
        exp = sub['returns_5bar'].mean() * 100
        print(f"  Score={score}: n={len(sub):4d}, 胜率={win:.1f}%, 期望={exp:.3f}%")
    
    # 解析conditions看各子条件
    print("\n【按Conditions解析】")
    all_conds = []
    for conds in merged['conditions'].dropna():
        all_conds.extend([c.strip() for c in str(conds).split('+')])
    cond_counts = Counter(all_conds)
    print(f"  条件出现频率: {dict(cond_counts.most_common())}")
    
    # 各条件的胜率贡献
    print("\n【各条件胜率贡献 (单变量)】")
    for cond in ['BB', 'SR', 'ADX<20', 'ADX<13', 'ADX<9']:
        has_cond = merged['conditions'].str.contains(cond, na=False)
        with_c = merged[has_cond]
        without_c = merged[~has_cond]
        if len(with_c) > 30 and len(without_c) > 30:
            win_with = (with_c['returns_5bar'] > 0).mean() * 100
            win_without = (without_c['returns_5bar'] > 0).mean() * 100
            diff = win_with - win_without
            print(f"  {cond:10s}: 有={win_with:.1f}% (n={len(with_c)}), 无={win_without:.1f}% (n={len(without_c)}), 差={diff:+.1f}%")
    
    # ADX绝对值分层
    print("\n【ADX绝对值分层】")
    merged['adx_bucket'] = pd.cut(merged['adx'], bins=[0, 10, 15, 20, 50], labels=['<10', '10-15', '15-20', '>20'])
    for bucket in merged['adx_bucket'].cat.categories:
        sub = merged[merged['adx_bucket'] == bucket]
        if len(sub) > 30:
            win = (sub['returns_5bar'] > 0).mean() * 100
            exp = sub['returns_5bar'].mean() * 100
            print(f"  ADX {bucket:6s}: n={len(sub):4d}, 胜率={win:.1f}%, 期望={exp:.3f}%")
    
    # anchor_range_pct分层 (波动率大小)
    print("\n【Anchor Range Pct分层 (收缩程度)】")
    merged['range_bucket'] = pd.qcut(merged['anchor_range_pct'], q=4, labels=['Q1(小)', 'Q2', 'Q3', 'Q4(大)'])
    for bucket in merged['range_bucket'].cat.categories:
        sub = merged[merged['range_bucket'] == bucket]
        win = (sub['returns_5bar'] > 0).mean() * 100
        exp = sub['returns_5bar'].mean() * 100
        range_val = sub['anchor_range_pct'].mean()
        print(f"  {bucket:8s}: n={len(sub):4d}, 胜率={win:.1f}%, 期望={exp:.3f}%, 平均range={range_val:.3f}%")
    
    return merged


def analyze_hypothesis_c(events):
    """假设C: 突破确认机制
    
    分析突破bar的质量特征
    但v3 CSV没有保存突破bar的OHLC... 用returns_1bar做代理
    """
    print("\n" + "=" * 70)
    print("假设C: 突破确认机制")
    print("=" * 70)
    
    # 用returns_1bar (突破后第1根K线close) 做代理
    # returns_1bar > 0 表示突破后第1根K线收在entry上方 = 初步确认
    print("\n【突破后第1根K线方向 (returns_1bar)】")
    
    events['r1_dir'] = np.where(events['returns_1bar'] > 0, 'positive', 
                         np.where(events['returns_1bar'] < 0, 'negative', 'flat'))
    
    for direction in ['up', 'down']:
        sub = events[events['breakout_direction'] == direction]
        print(f"\n  突破方向={direction}:")
        for r1 in ['positive', 'negative', 'flat']:
            s = sub[sub['r1_dir'] == r1]
            if len(s) > 30:
                win = (s['returns_5bar'] > 0).mean() * 100
                exp = s['returns_5bar'].mean() * 100
                print(f"    1bar {r1:8s}: n={len(s):4d}, 5bar胜率={win:.1f}%, 期望={exp:.3f}%")
    
    # 突破后1bar确认 vs 不确认的对比
    print(f"\n【突破后1bar确认效应】")
    for direction in ['up', 'down']:
        sub = events[events['breakout_direction'] == direction]
        confirmed = sub[sub['r1_dir'] == 'positive'] if direction == 'up' else sub[sub['r1_dir'] == 'negative']
        unconfirmed = sub[sub['r1_dir'] != ('positive' if direction == 'up' else 'negative')]
        
        if len(confirmed) > 30 and len(unconfirmed) > 30:
            c_win = (confirmed['returns_5bar'] > 0).mean() * 100
            u_win = (unconfirmed['returns_5bar'] > 0).mean() * 100
            c_exp = confirmed['returns_5bar'].mean() * 100
            u_exp = unconfirmed['returns_5bar'].mean() * 100
            print(f"  {direction:4s}: 确认 n={len(confirmed):4d} 胜率={c_win:.1f}% 期望={c_exp:.3f}% | "
                  f"未确认 n={len(unconfirmed):4d} 胜率={u_win:.1f}% 期望={u_exp:.3f}% | "
                  f"胜率差={c_win-u_win:+.1f}%")
    
    # MFE/MAE比率作为突破质量指标
    events['mfe_mae_ratio'] = events['mfe_pct'] / events['mae_pct'].abs().clip(lower=0.0001)
    events['quality_bucket'] = pd.qcut(events['mfe_mae_ratio'], q=3, labels=['low', 'mid', 'high'])
    
    print(f"\n【MFE/MAE比率分层 (突破质量)】")
    for q in ['low', 'mid', 'high']:
        sub = events[events['quality_bucket'] == q]
        win = (sub['returns_5bar'] > 0).mean() * 100
        exp = sub['returns_5bar'].mean() * 100
        ratio = sub['mfe_mae_ratio'].mean()
        print(f"  {q:4s}: n={len(sub):4d}, 胜率={win:.1f}%, 期望={exp:.3f}%, MFE/MAE={ratio:.2f}")


def analyze_hypothesis_d(events, trades):
    """假设D: 品种选择优化
    """
    print("\n" + "=" * 70)
    print("假设D: 品种选择优化")
    print("=" * 70)
    
    # 按品种统计
    print("\n【按品种统计 (唯一突破事件)】")
    symbol_stats = []
    for sym in sorted(events['symbol'].unique()):
        sub = events[events['symbol'] == sym]
        win = (sub['returns_5bar'] > 0).mean() * 100
        exp = sub['returns_5bar'].mean() * 100
        mfe = sub['mfe_pct'].mean() * 100
        mae = sub['mae_pct'].mean() * 100
        symbol_stats.append({
            'symbol': sym, 'n': len(sub), 'win': win, 'exp': exp,
            'mfe': mfe, 'mae': mae, 'ratio': mfe/max(abs(mae), 0.001)
        })
    
    stats_df = pd.DataFrame(symbol_stats).sort_values('exp', ascending=False)
    print(stats_df.to_string(index=False, float_format='%.3f'))
    
    # 白名单/黑名单
    positive = stats_df[stats_df['exp'] > 0]
    negative = stats_df[stats_df['exp'] <= 0]
    
    print(f"\n【正期望品种 ({len(positive)}个)】")
    print(f"  {list(positive['symbol'])}")
    print(f"  平均期望: {positive['exp'].mean():.3f}%")
    
    print(f"\n【负期望品种 ({len(negative)}个)】")
    print(f"  {list(negative['symbol'])}")
    print(f"  平均期望: {negative['exp'].mean():.3f}%")
    
    # 只保留正期望品种后的整体表现
    whitelist = list(positive['symbol'])
    filtered = events[events['symbol'].isin(whitelist)]
    print(f"\n【白名单过滤后整体】")
    print(f"  样本: {len(filtered)} / {len(events)}")
    print(f"  胜率: {(filtered['returns_5bar'] > 0).mean() * 100:.1f}%")
    print(f"  期望: {filtered['returns_5bar'].mean() * 100:.3f}%")
    
    # 交易成本后 (trades表)
    trades_filtered = trades[trades['symbol'].isin(whitelist)]
    print(f"\n【白名单 + 交易成本后】")
    print(f"  样本: {len(trades_filtered)} / {len(trades)}")
    print(f"  净胜率: {(trades_filtered['net_pnl_pct'] > 0).mean() * 100:.1f}%")
    print(f"  净期望: {trades_filtered['net_pnl_pct'].mean() * 100:.3f}%")
    
    return stats_df, whitelist


def combined_filter_analysis(merged, whitelist):
    """组合过滤效果分析"""
    print("\n" + "=" * 70)
    print("组合过滤效果 (假设A+B+D叠加)")
    print("=" * 70)
    
    # 基线
    baseline = merged
    print(f"\n【基线 (全部)】")
    print(f"  n={len(baseline)}, 胜率={(baseline['returns_5bar']>0).mean()*100:.1f}%, 期望={baseline['returns_5bar'].mean()*100:.3f}%")
    
    # 过滤1: 白名单
    f1 = merged[merged['symbol'].isin(whitelist)]
    print(f"\n【+ 白名单】")
    print(f"  n={len(f1)}, 胜率={(f1['returns_5bar']>0).mean()*100:.1f}%, 期望={f1['returns_5bar'].mean()*100:.3f}%")
    
    # 过滤2: + 双周期同向趋势 (假设A)
    f2 = f1[f1['h4d1'].isin(['bullish_bullish', 'bearish_bearish'])]
    print(f"\n【+ 双周期同向趋势】")
    print(f"  n={len(f2)}, 胜率={(f2['returns_5bar']>0).mean()*100:.1f}%, 期望={f2['returns_5bar'].mean()*100:.3f}%")
    
    # 过滤3: + ADX<10 (强收缩, 假设B)
    f3 = f2[f2['adx'] < 10]
    print(f"\n【+ ADX<10 (强收缩)】")
    print(f"  n={len(f3)}, 胜率={(f3['returns_5bar']>0).mean()*100:.1f}%, 期望={f3['returns_5bar'].mean()*100:.3f}%")
    
    # 过滤4: + 突破后1bar确认 (假设C)
    f3_up = f3[f3['breakout_direction'] == 'up']
    f3_down = f3[f3['breakout_direction'] == 'down']
    f4_up = f3_up[f3_up['returns_1bar'] > 0]
    f4_down = f3_down[f3_down['returns_1bar'] < 0]
    f4 = pd.concat([f4_up, f4_down])
    print(f"\n【+ 1bar确认】")
    print(f"  n={len(f4)}, 胜率={(f4['returns_5bar']>0).mean()*100:.1f}%, 期望={f4['returns_5bar'].mean()*100:.3f}%")


def main():
    print("=" * 70)
    print("v4 Phase 1 诊断分析")
    print("=" * 70)
    
    setups, events, trades = load_data()
    print(f"\n数据加载: setups={len(setups)}, events={len(events)}, trades={len(trades)}")
    
    # 假设A
    strong, mixed, weak = analyze_hypothesis_a(events)
    
    # 假设B
    merged = analyze_hypothesis_b(setups, events)
    
    # 假设C
    analyze_hypothesis_c(events)
    
    # 假设D
    stats_df, whitelist = analyze_hypothesis_d(events, trades)
    
    # 组合分析
    combined_filter_analysis(merged, whitelist)
    
    print("\n" + "=" * 70)
    print("Phase 1 诊断完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
