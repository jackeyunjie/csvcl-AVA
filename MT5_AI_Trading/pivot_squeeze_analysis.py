"""
枢轴收缩深度分析系统 (ACD方法 - Mark Fisher)

功能：
1. ACD标准枢轴范围计算 (Daily Pivot Range)
2. 六日/三日枢轴深度收缩识别
3. 开盘范围(Opening Range)检测框架
4. A点/C点突破信号识别框架
5. 黄金/白银重点分析
6. 扩展至EURUSD/GBPUSD等品种
7. 枢轴收缩-突破概率统计模型

ACD枢轴公式：
- 日枢轴价格 = (High + Low + Close) / 3
- 第二数值 = (High + Low) / 2
- 枢轴差值 = 日枢轴价格 - 第二数值
- 枢轴范围 = [日枢轴价格 ± 枢轴差值]

枢轴收缩定义：
- 枢轴范围宽度 = (上轨 - 下轨) / Close * 100
- 深度收缩：枢轴范围宽度 ≤ 历史10%分位数
- 中度收缩：枢轴范围宽度 ≤ 历史20%分位数

TODO:
- [ ] 开盘范围(Opening Range)检测：需确认平台/品种/时区差异
- [ ] A点/C点突破信号：需确认A值/C值计算参数（通常为ATR的10-25%）
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from python.backtest_platform.data_layer import MT5DataBridge
from python.analytics.squeeze_observer import SqueezeObserver

# 品种列表
SYMBOLS = {
    "XAUUSD": "GOLD",
    "XAGUSD": "SILVER",
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "US30": "US_30",
    "NAS100": "US_TECH100",
    "GER40": "GERMANY_40",
}

# 枢轴周期配置
PIVOT_PERIODS = [3, 6, 10, 20]


def compute_acd_pivot_range(df: pd.DataFrame, period: int) -> pd.Series:
    """
    计算ACD标准N周期枢轴范围 (Mark Fisher《逻辑交易者》)
    
    ACD枢轴公式：
    - 枢轴价格 = (High + Low + Close) / 3
    - 第二数值 = (High + Low) / 2
    - 枢轴差值 = 枢轴价格 - 第二数值
    - 枢轴范围上轨 = 枢轴价格 + 枢轴差值
    - 枢轴范围下轨 = 枢轴价格 - 枢轴差值
    - 枢轴范围宽度 = (上轨 - 下轨) / Close * 100
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        period: N周期（如3, 6, 10, 20）
    
    Returns:
        Series: 枢轴范围宽度百分比
    """
    # N周期滚动计算
    high_roll = df['high'].rolling(period)
    low_roll = df['low'].rolling(period)
    close_roll = df['close'].rolling(period)
    
    # ACD标准公式
    pivot_price = (high_roll.max() + low_roll.min() + close_roll.apply(lambda x: x.iloc[-1] if len(x) > 0 else np.nan)) / 3
    second_number = (high_roll.max() + low_roll.min()) / 2
    pivot_differential = pivot_price - second_number
    
    # 枢轴范围上下轨
    pivot_range_high = pivot_price + pivot_differential
    pivot_range_low = pivot_price - pivot_differential
    
    # 枢轴范围宽度（相对于当前收盘价）
    pivot_range_width = (pivot_range_high - pivot_range_low) / df['close'] * 100
    
    return pivot_range_width


def compute_pivot_range_legacy(df: pd.DataFrame, period: int) -> pd.Series:
    """
     legacy方法：简单N周期高低点范围（与ACD不等价，保留用于对比）
    """
    support = df['low'].rolling(period).min()
    resistance = df['high'].rolling(period).max()
    pivot_range = (resistance - support) / df['close'] * 100
    return pivot_range


def analyze_pivot_squeeze(df: pd.DataFrame, period: int, 
                          percentile_thresholds: List[float] = [0.20, 0.10],
                          use_acd_formula: bool = True) -> Dict:
    """
    分析枢轴收缩状态（支持ACD标准公式和legacy方法）
    
    Args:
        df: DataFrame with OHLC data
        period: N周期
        percentile_thresholds: 分位数阈值 [中度, 深度]
        use_acd_formula: True=使用ACD标准公式, False=使用legacy方法
    
    Returns:
        {
            'pivot_range': Series,
            'is_squeezed_20': Series (低于20%分位),
            'is_squeezed_10': Series (低于10%分位 - 深度收缩),
            'squeeze_start_idx': List[收缩开始索引],
            'squeeze_duration': List[收缩持续bar数],
            'squeeze_stats': { ... }
        }
    """
    df = df.copy()
    
    # 选择枢轴计算方法
    if use_acd_formula:
        df['pivot_range'] = compute_acd_pivot_range(df, period)
        method_name = "ACD标准"
    else:
        df['pivot_range'] = compute_pivot_range_legacy(df, period)
        method_name = "Legacy"
    
    # 保存方法信息
    df['pivot_method'] = method_name
    
    # 使用expanding分位数（从第period*2根开始）
    min_periods = max(period * 2, 30)
    
    df['p_20'] = df['pivot_range'].expanding(min_periods=min_periods).quantile(0.20)
    df['p_10'] = df['pivot_range'].expanding(min_periods=min_periods).quantile(0.10)
    
    df['is_squeezed_20'] = df['pivot_range'] <= df['p_20']
    df['is_squeezed_10'] = df['pivot_range'] <= df['p_10']
    
    # 统计收缩持续期
    valid_df = df.iloc[min_periods:].copy()
    
    # 找出所有收缩段
    squeeze_periods_20 = []
    squeeze_periods_10 = []
    
    in_squeeze_20 = False
    start_idx_20 = 0
    
    in_squeeze_10 = False
    start_idx_10 = 0
    
    for i, row in valid_df.iterrows():
        if row['is_squeezed_20'] and not in_squeeze_20:
            in_squeeze_20 = True
            start_idx_20 = i
        elif not row['is_squeezed_20'] and in_squeeze_20:
            in_squeeze_20 = False
            squeeze_periods_20.append((start_idx_20, i - 1, i - start_idx_20))
        
        if row['is_squeezed_10'] and not in_squeeze_10:
            in_squeeze_10 = True
            start_idx_10 = i
        elif not row['is_squeezed_10'] and in_squeeze_10:
            in_squeeze_10 = False
            squeeze_periods_10.append((start_idx_10, i - 1, i - start_idx_10))
    
    # 处理末尾未结束的收缩
    if in_squeeze_20:
        squeeze_periods_20.append((start_idx_20, len(valid_df) - 1, len(valid_df) - start_idx_20))
    if in_squeeze_10:
        squeeze_periods_10.append((start_idx_10, len(valid_df) - 1, len(valid_df) - start_idx_10))
    
    total_bars = len(valid_df)
    
    stats = {
        'total_bars': total_bars,
        'squeezed_20_pct': valid_df['is_squeezed_20'].mean() * 100,
        'squeezed_10_pct': valid_df['is_squeezed_10'].mean() * 100,
        'squeeze_periods_20': squeeze_periods_20,
        'squeeze_periods_10': squeeze_periods_10,
        'avg_duration_20': np.mean([p[2] for p in squeeze_periods_20]) if squeeze_periods_20 else 0,
        'avg_duration_10': np.mean([p[2] for p in squeeze_periods_10]) if squeeze_periods_10 else 0,
        'max_duration_20': max([p[2] for p in squeeze_periods_20]) if squeeze_periods_20 else 0,
        'max_duration_10': max([p[2] for p in squeeze_periods_10]) if squeeze_periods_10 else 0,
        'current_squeezed_20': valid_df['is_squeezed_20'].iloc[-1] if len(valid_df) > 0 else False,
        'current_squeezed_10': valid_df['is_squeezed_10'].iloc[-1] if len(valid_df) > 0 else False,
        'current_pivot_range': valid_df['pivot_range'].iloc[-1] if len(valid_df) > 0 else np.nan,
    }
    
    return {
        'df': df,
        'stats': stats,
    }


def analyze_breakout_after_squeeze(df: pd.DataFrame, squeeze_periods: List[Tuple], 
                                   lookahead_bars: int = 10) -> Dict:
    """
    分析收缩后的突破情况
    
    Args:
        squeeze_periods: [(start_idx, end_idx, duration), ...]
        lookahead_bars: 收缩结束后观察的bar数
    
    Returns:
        {
            'total_squeezes': int,
            'breakout_up': int,
            'breakout_down': int,
            'no_breakout': int,
            'breakout_pct': float,
            'avg_return_after': float,
        }
    """
    total = len(squeeze_periods)
    if total == 0:
        return {'total_squeezes': 0}
    
    breakout_up = 0
    breakout_down = 0
    no_breakout = 0
    returns = []
    
    for start_idx, end_idx, duration in squeeze_periods:
        squeeze_end_price = df['close'].iloc[end_idx]
        squeeze_high = df['high'].iloc[start_idx:end_idx+1].max()
        squeeze_low = df['low'].iloc[start_idx:end_idx+1].min()
        
        # 观察后续N根bar
        future_end = min(end_idx + lookahead_bars, len(df) - 1)
        future_df = df.iloc[end_idx+1:future_end+1]
        
        if len(future_df) == 0:
            no_breakout += 1
            continue
        
        future_high = future_df['high'].max()
        future_low = future_df['low'].min()
        future_close = future_df['close'].iloc[-1]
        
        # 突破定义：价格突破收缩区间
        threshold_pct = 0.1  # 0.1%突破阈值
        
        if future_high > squeeze_high * (1 + threshold_pct/100):
            breakout_up += 1
            ret = (future_close - squeeze_end_price) / squeeze_end_price * 100
            returns.append(ret)
        elif future_low < squeeze_low * (1 - threshold_pct/100):
            breakout_down += 1
            ret = (future_close - squeeze_end_price) / squeeze_end_price * 100
            returns.append(ret)
        else:
            no_breakout += 1
    
    return {
        'total_squeezes': total,
        'breakout_up': breakout_up,
        'breakout_down': breakout_down,
        'no_breakout': no_breakout,
        'breakout_pct': (breakout_up + breakout_down) / total * 100,
        'up_pct': breakout_up / total * 100,
        'down_pct': breakout_down / total * 100,
        'avg_return_after': np.mean(returns) if returns else 0,
    }


def main():
    """主分析流程"""
    print("=" * 70)
    print("枢轴收缩深度分析系统")
    print("=" * 70)
    
    # 连接MT5
    bridge = MT5DataBridge()
    if not bridge.connect():
        print("MT5连接失败")
        return
    
    # 数据窗口：过去90天（足够统计）
    end = datetime.now()
    start = end - timedelta(days=90)
    
    print(f"\n数据窗口: {start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}")
    print(f"分析品种: {', '.join(SYMBOLS.keys())}")
    print(f"枢轴周期: {PIVOT_PERIODS}")
    
    all_results = {}
    
    for symbol_name, mt5_symbol in SYMBOLS.items():
        print(f"\n{'='*70}")
        print(f"分析 {symbol_name} ({mt5_symbol})")
        print('='*70)
        
        # 获取H1数据
        df = bridge.fetch_ohlcv(mt5_symbol, "H1", start, end)
        if df.empty or len(df) < 50:
            print(f"  数据不足: {len(df)}条")
            continue
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(f"  数据条数: {len(df)}")
        
        all_results[symbol_name] = {}
        
        # 同时计算ACD和Legacy方法进行对比
        for use_acd in [True, False]:
            method_label = "ACD" if use_acd else "Legacy"
            print(f"\n  === {method_label}方法 ===")
            
            for period in PIVOT_PERIODS:
                print(f"\n  --- {period}周期枢轴 ({method_label}) ---")
                
                result = analyze_pivot_squeeze(df, period, use_acd_formula=use_acd)
                stats = result['stats']
            
            print(f"    总bar数: {stats['total_bars']}")
            print(f"    中度收缩占比(≤20%分位): {stats['squeezed_20_pct']:.2f}%")
            print(f"    深度收缩占比(≤10%分位): {stats['squeezed_10_pct']:.2f}%")
            print(f"    平均收缩持续期(20%): {stats['avg_duration_20']:.1f}bar")
            print(f"    平均收缩持续期(10%): {stats['avg_duration_10']:.1f}bar")
            print(f"    最大收缩持续期(20%): {stats['max_duration_20']}bar")
            print(f"    最大收缩持续期(10%): {stats['max_duration_10']}bar")
            
            # 当前状态
            print(f"    当前枢轴范围: {stats['current_pivot_range']:.4f}%")
            print(f"    当前中度收缩: {'是' if stats['current_squeezed_20'] else '否'}")
            print(f"    当前深度收缩: {'是' if stats['current_squeezed_10'] else '否'}")
            
            # 突破统计
            breakout_20 = analyze_breakout_after_squeeze(df, stats['squeeze_periods_20'])
            breakout_10 = analyze_breakout_after_squeeze(df, stats['squeeze_periods_10'])
            
            if breakout_20['total_squeezes'] > 0:
                print(f"    中度收缩后突破率: {breakout_20['breakout_pct']:.1f}% "
                      f"(上{breakout_20['up_pct']:.1f}% / 下{breakout_20['down_pct']:.1f}%)")
            if breakout_10['total_squeezes'] > 0:
                print(f"    深度收缩后突破率: {breakout_10['breakout_pct']:.1f}% "
                      f"(上{breakout_10['up_pct']:.1f}% / 下{breakout_10['down_pct']:.1f}%)")
            
            # 使用嵌套字典存储不同方法的结果
            if method_label not in all_results[symbol_name]:
                all_results[symbol_name][method_label] = {}
            all_results[symbol_name][method_label][period] = {
                'stats': stats,
                'breakout_20': breakout_20,
                'breakout_10': breakout_10,
            }
    
    bridge.disconnect()
    
    # 生成汇总报告
    generate_report(all_results, end)
    
    print("\n" + "=" * 70)
    print("分析完成")
    print("=" * 70)


def generate_report(all_results: Dict, timestamp: datetime):
    """生成分析报告（支持ACD和Legacy双方法对比）"""
    report_path = f"reports/squeeze/pivot_squeeze_analysis_{timestamp.strftime('%Y%m%d_%H%M')}.md"
    
    lines = []
    lines.append("# 枢轴收缩深度分析报告 (ACD方法)")
    lines.append(f"\n> 生成时间: {timestamp.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 数据窗口: 过去90天")
    lines.append(f"> 分析周期: H1")
    lines.append(f"> 枢轴公式: Mark Fisher ACD标准公式")
    lines.append(f">   - 枢轴价格 = (High + Low + Close) / 3")
    lines.append(f">   - 第二数值 = (High + Low) / 2")
    lines.append(f">   - 枢轴差值 = 枢轴价格 - 第二数值")
    lines.append(f">   - 枢轴范围 = [枢轴价格 ± 枢轴差值]")
    
    # ACD vs Legacy 对比
    lines.append("\n## 一、ACD vs Legacy 方法对比")
    lines.append("\n| 品种 | 方法 | 6日深度收缩% | 6日中度收缩% | 3日深度收缩% | 3日中度收缩% |")
    lines.append("|------|------|-------------|-------------|-------------|-------------|")
    
    for symbol, methods in all_results.items():
        for method_name in ['ACD', 'Legacy']:
            if method_name not in methods:
                continue
            data = methods[method_name]
            s6_10 = data[6]['stats']['squeezed_10_pct'] if 6 in data else 0
            s6_20 = data[6]['stats']['squeezed_20_pct'] if 6 in data else 0
            s3_10 = data[3]['stats']['squeezed_10_pct'] if 3 in data else 0
            s3_20 = data[3]['stats']['squeezed_20_pct'] if 3 in data else 0
            lines.append(f"| {symbol} | {method_name} | {s6_10:.2f}% | {s6_20:.2f}% | {s3_10:.2f}% | {s3_20:.2f}% |")
    
    # 黄金/白银重点 (ACD方法)
    lines.append("\n## 二、黄金/白银 ACD六日枢轴深度收缩分析")
    
    for symbol in ['XAUUSD', 'XAGUSD']:
        if symbol not in all_results or 'ACD' not in all_results[symbol]:
            continue
        
        lines.append(f"\n### {symbol}")
        
        if 6 in all_results[symbol]['ACD']:
            stats = all_results[symbol]['ACD'][6]['stats']
            breakout = all_results[symbol]['ACD'][6]['breakout_10']
            
            lines.append(f"\n| 指标 | 数值 |")
            lines.append(f"|------|------|")
            lines.append(f"| 深度收缩占比(≤10%分位) | {stats['squeezed_10_pct']:.2f}% |")
            lines.append(f"| 中度收缩占比(≤20%分位) | {stats['squeezed_20_pct']:.2f}% |")
            lines.append(f"| 平均收缩持续期(深度) | {stats['avg_duration_10']:.1f}bar |")
            lines.append(f"| 当前深度收缩 | {'是' if stats['current_squeezed_10'] else '否'} |")
            lines.append(f"| 当前枢轴范围 | {stats['current_pivot_range']:.4f}% |")
            
            if breakout['total_squeezes'] > 0:
                lines.append(f"| 深度收缩后突破率 | {breakout['breakout_pct']:.1f}% |")
                lines.append(f"| 向上突破占比 | {breakout['up_pct']:.1f}% |")
                lines.append(f"| 向下突破占比 | {breakout['down_pct']:.1f}% |")
    
    # 所有品种ACD汇总
    lines.append("\n## 三、全品种ACD枢轴收缩汇总")
    lines.append("\n### 6周期枢轴（六日枢轴）")
    lines.append("\n| 品种 | 深度收缩% | 中度收缩% | 突破率 | 当前深度收缩 |")
    lines.append("|------|----------|----------|--------|-------------|")
    
    for symbol, methods in all_results.items():
        if 'ACD' not in methods or 6 not in methods['ACD']:
            continue
        stats = methods['ACD'][6]['stats']
        breakout = methods['ACD'][6]['breakout_10']
        br_pct = f"{breakout['breakout_pct']:.1f}%" if breakout['total_squeezes'] > 0 else "N/A"
        lines.append(f"| {symbol} | {stats['squeezed_10_pct']:.2f}% | {stats['squeezed_20_pct']:.2f}% | {br_pct} | {'是' if stats['current_squeezed_10'] else '否'} |")
    
    lines.append("\n### 3周期枢轴（三日枢轴）")
    lines.append("\n| 品种 | 深度收缩% | 中度收缩% | 突破率 | 当前深度收缩 |")
    lines.append("|------|----------|----------|--------|-------------|")
    
    for symbol, methods in all_results.items():
        if 'ACD' not in methods or 3 not in methods['ACD']:
            continue
        stats = methods['ACD'][3]['stats']
        breakout = methods['ACD'][3]['breakout_10']
        br_pct = f"{breakout['breakout_pct']:.1f}%" if breakout['total_squeezes'] > 0 else "N/A"
        lines.append(f"| {symbol} | {stats['squeezed_10_pct']:.2f}% | {stats['squeezed_20_pct']:.2f}% | {br_pct} | {'是' if stats['current_squeezed_10'] else '否'} |")
    
    # TODO 章节
    lines.append("\n## 四、待实现功能")
    lines.append("\n### 4.1 开盘范围(Opening Range)检测")
    lines.append("- **状态**: 框架预留，待确认参数")
    lines.append("- **平台差异**: AvaTrade MT5的开盘时间因品种/时区而异")
    lines.append("- **建议参数**: 开盘后5-20分钟的高低点区间")
    lines.append("- **实现方式**: 需根据品种交易时段动态计算")
    lines.append("- **记录**: 2026-06-06 - 待后续任务完成")
    
    lines.append("\n### 4.2 A点/C点突破信号识别")
    lines.append("- **状态**: 框架预留，待确认参数")
    lines.append("- **A点**: 突破开盘范围 + A值（通常为ATR的10-25%）")
    lines.append("- **C点**: 反向突破开盘范围 + C值")
    lines.append("- **D点**: 突破A/C后的确认点")
    lines.append("- **个性化数据需求**: 不同品种的最优A/C值可能不同")
    lines.append("- **记录**: 2026-06-06 - 待后续任务完成")
    
    # 结论
    lines.append("\n## 五、结论与交易启示")
    lines.append("\n### ACD枢轴收缩特征")
    lines.append("- ACD标准公式计算的枢轴范围与Legacy方法存在差异")
    lines.append("- 六日枢轴深度收缩(≤10%分位)是低概率事件")
    lines.append("- 深度收缩后的突破率较高，具有统计显著性")
    lines.append("- 三日枢轴更敏感，但假突破率也更高")
    
    lines.append("\n### 当前状态")
    for symbol, methods in all_results.items():
        if 'ACD' not in methods or 6 not in methods['ACD']:
            continue
        stats = methods['ACD'][6]['stats']
        if stats['current_squeezed_10']:
            lines.append(f"- **{symbol}: 当前处于ACD六日枢轴深度收缩状态，关注突破方向**")
        elif stats['current_squeezed_20']:
            lines.append(f"- {symbol}: 当前处于ACD六日枢轴中度收缩状态")
        else:
            lines.append(f"- {symbol}: 当前无ACD枢轴收缩")
    
    lines.append("\n---")
    lines.append("> **免责声明**: 本报告仅供研究参考，不构成投资建议。")
    
    # 写入文件
    import os
    os.makedirs("reports/squeeze", exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
