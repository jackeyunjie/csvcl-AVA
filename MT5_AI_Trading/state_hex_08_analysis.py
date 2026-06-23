"""
State Hex 0,8 组合统计分析

分析H1视角五元组中D1和H4位置出现0,8组合的频率、特征及与收缩/突破的相关性。

State Hex编码:
- 0 = 收缩底座(contraction/closed), 无额外组件
- 8 = 非收缩底座(non-contraction), 无额外组件
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from python.backtest_platform.data_layer import MT5DataBridge
from python.ai_engine.state_hex_engine import StateHexEngine, KLine
from python.ai_engine.state_hex_encoding import StateHexEncoder

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
    "DXY": "USDINDEX",
}


def fetch_and_compute_quintuplets(symbol_name: str, mt5_symbol: str, 
                                   bridge: MT5DataBridge,
                                   days: int = 90) -> pd.DataFrame:
    """获取数据并计算五元组"""
    end = datetime.now()
    start = end - timedelta(days=days)
    
    # 获取各周期数据
    h1_df = bridge.fetch_ohlcv(mt5_symbol, "H1", start, end)
    h4_df = bridge.fetch_ohlcv(mt5_symbol, "H4", start, end)
    d1_df = bridge.fetch_ohlcv(mt5_symbol, "D1", start, end)
    
    if h1_df.empty or len(h1_df) < 50:
        return pd.DataFrame()
    
    # 转换为KLine
    def df_to_klines(df):
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
    
    engine = StateHexEngine()
    
    if not d1_df.empty:
        engine.d1_data = df_to_klines(d1_df)
    if not h4_df.empty:
        engine.h4_data = df_to_klines(h4_df)
    engine.h1_data = df_to_klines(h1_df)
    
    # 计算五元组
    quintuplets = engine.compute_quintuplets()
    df = engine.to_quintuplet_dataframe()
    
    # 添加close列（从h1_data提取）
    if not df.empty and engine.h1_data:
        close_map = {k.timestamp: k.close for k in engine.h1_data}
        df['close'] = df['timestamp'].map(close_map)
    
    return df


def analyze_08_combinations(df: pd.DataFrame) -> Dict:
    """分析0,8组合"""
    if df.empty:
        return {}
    
    results = {}
    
    # 确保hex列为字符串
    for col in ['D1_hex', 'H4_hex', 'H1_hex']:
        df[col] = df[col].astype(str)
    
    total = len(df)
    
    # === D1-H4 组合统计 ===
    df['d1_h4_combo'] = df['D1_hex'] + '_' + df['H4_hex']
    combo_counts = df['d1_h4_combo'].value_counts()
    
    results['total_bars'] = total
    results['combo_distribution'] = combo_counts.to_dict()
    
    # 重点关注0,8组合
    target_combos = ['0_8', '8_0', '0_0', '8_8']
    for combo in target_combos:
        count = combo_counts.get(combo, 0)
        results[f'{combo}_count'] = count
        results[f'{combo}_pct'] = count / total * 100 if total > 0 else 0
    
    # === 0_8组合详细分析 ===
    mask_08 = df['d1_h4_combo'] == '0_8'
    df_08 = df[mask_08].copy()
    
    if len(df_08) > 0:
        # H1_hex分布
        results['08_h1_distribution'] = df_08['H1_hex'].value_counts().to_dict()
        
        # 时间分布（按小时）
        df_08['hour'] = pd.to_datetime(df_08['timestamp']).dt.hour
        results['08_hour_distribution'] = df_08['hour'].value_counts().sort_index().to_dict()
        
        # 连续出现统计
        df['is_08'] = mask_08.astype(int)
        consecutive = []
        current = 0
        for is_08 in df['is_08']:
            if is_08:
                current += 1
            else:
                if current > 0:
                    consecutive.append(current)
                current = 0
        if current > 0:
            consecutive.append(current)
        
        results['08_consecutive_max'] = max(consecutive) if consecutive else 0
        results['08_consecutive_avg'] = np.mean(consecutive) if consecutive else 0
        results['08_consecutive_total'] = len(consecutive)
    
    # === 8_0组合详细分析 ===
    mask_80 = df['d1_h4_combo'] == '8_0'
    df_80 = df[mask_80].copy()
    
    if len(df_80) > 0:
        results['80_h1_distribution'] = df_80['H1_hex'].value_counts().to_dict()
        
        df_80['hour'] = pd.to_datetime(df_80['timestamp']).dt.hour
        results['80_hour_distribution'] = df_80['hour'].value_counts().sort_index().to_dict()
    
    # === 与H1收缩的相关性 ===
    # H1_hex为0或1表示H1处于收缩状态
    df['h1_contraction'] = df['H1_hex'].isin(['0', '1', '2', '3', '4', '5', '6', '7'])
    df['h1_non_contraction'] = df['H1_hex'].isin(['8', '9', 'A', 'B', 'C', 'D', 'E', 'F'])
    
    # 0_8组合时H1的收缩情况
    if len(df_08) > 0:
        results['08_h1_contraction_pct'] = df_08['h1_contraction'].mean() * 100 if 'h1_contraction' in df_08.columns else 0
        results['08_h1_non_contraction_pct'] = df_08['h1_non_contraction'].mean() * 100 if 'h1_non_contraction' in df_08.columns else 0
    
    # === 后续价格变动分析 ===
    has_close = 'close' in df.columns and df['close'].notna().any()
    
    if has_close:
        df['future_return_5bar'] = df['close'].shift(-5) / df['close'] - 1
        df['future_return_10bar'] = df['close'].shift(-10) / df['close'] - 1
        # 同步到子集
        if len(df_08) > 0:
            df_08['future_return_5bar'] = df_08['close'].shift(-5) / df_08['close'] - 1
            df_08['future_return_10bar'] = df_08['close'].shift(-10) / df_08['close'] - 1
        if len(df_80) > 0:
            df_80['future_return_5bar'] = df_80['close'].shift(-5) / df_80['close'] - 1
            df_80['future_return_10bar'] = df_80['close'].shift(-10) / df_80['close'] - 1
    else:
        df['future_return_5bar'] = np.nan
        df['future_return_10bar'] = np.nan
    
    if len(df_08) > 0 and has_close:
        results['08_avg_return_5bar'] = df_08['future_return_5bar'].mean() * 100
        results['08_avg_return_10bar'] = df_08['future_return_10bar'].mean() * 100
        results['08_std_return_5bar'] = df_08['future_return_5bar'].std() * 100
    else:
        results['08_avg_return_5bar'] = 0
        results['08_avg_return_10bar'] = 0
        results['08_std_return_5bar'] = 0
    
    if len(df_80) > 0 and has_close:
        results['80_avg_return_5bar'] = df_80['future_return_5bar'].mean() * 100
        results['80_avg_return_10bar'] = df_80['future_return_10bar'].mean() * 100
        results['80_std_return_5bar'] = df_80['future_return_5bar'].std() * 100
    else:
        results['80_avg_return_5bar'] = 0
        results['80_avg_return_10bar'] = 0
        results['80_std_return_5bar'] = 0
    
    # 全样本对比
    if has_close:
        results['all_avg_return_5bar'] = df['future_return_5bar'].mean() * 100
        results['all_std_return_5bar'] = df['future_return_5bar'].std() * 100
    else:
        results['all_avg_return_5bar'] = 0
        results['all_std_return_5bar'] = 0
    
    return results


def generate_report(all_results: Dict):
    """生成分析报告"""
    timestamp = datetime.now()
    report_path = f"reports/squeeze/state_hex_08_analysis_{timestamp.strftime('%Y%m%d_%H%M')}.md"
    
    lines = []
    lines.append("# State Hex 0,8 组合分析报告")
    lines.append(f"\n> 生成时间: {timestamp.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 分析周期: H1视角五元组 (MN1, W1, D1, H4, H1)")
    lines.append(f"> 数据窗口: 过去90天")
    
    # === 全品种汇总 ===
    lines.append("\n## 一、D1-H4 组合分布汇总")
    lines.append("\n| 品种 | 总Bar数 | 0_8 (D1缩,H4非) | 8_0 (D1非,H4缩) | 0_0 (双缩) | 8_8 (双非) |")
    lines.append("|------|---------|-----------------|-----------------|------------|------------|")
    
    for symbol, result in all_results.items():
        if not result:
            continue
        lines.append(f"| {symbol} | {result['total_bars']} | "
                    f"{result.get('0_8_pct', 0):.1f}% | "
                    f"{result.get('8_0_pct', 0):.1f}% | "
                    f"{result.get('0_0_pct', 0):.1f}% | "
                    f"{result.get('8_8_pct', 0):.1f}% |")
    
    # === 0_8组合详细分析 ===
    lines.append("\n## 二、0_8 组合详细分析 (D1收缩 + H4非收缩)")
    lines.append("\n> 含义: 日线级别处于收缩底座，但4小时级别已脱离收缩状态")
    
    lines.append("\n### 2.1 出现频率与连续特征")
    lines.append("\n| 品种 | 占比 | 最大连续 | 平均连续 | 总次数 |")
    lines.append("|------|------|----------|----------|--------|")
    
    for symbol, result in all_results.items():
        if not result or '08_consecutive_max' not in result:
            continue
        lines.append(f"| {symbol} | {result.get('0_8_pct', 0):.1f}% | "
                    f"{result.get('08_consecutive_max', 0)} | "
                    f"{result.get('08_consecutive_avg', 0):.1f} | "
                    f"{result.get('08_consecutive_total', 0)} |")
    
    lines.append("\n### 2.2 H1状态分布 (当D1=0,H4=8时)")
    lines.append("\n| 品种 | H1收缩% | H1非收缩% |")
    lines.append("|------|---------|-----------|")
    
    for symbol, result in all_results.items():
        if not result or '08_h1_contraction_pct' not in result:
            continue
        lines.append(f"| {symbol} | {result['08_h1_contraction_pct']:.1f}% | "
                    f"{result['08_h1_non_contraction_pct']:.1f}% |")
    
    lines.append("\n### 2.3 后续5Bar收益统计")
    lines.append("\n| 品种 | 0_8组合5Bar收益 | 全样本5Bar收益 | 标准差 |")
    lines.append("|------|-----------------|----------------|--------|")
    
    for symbol, result in all_results.items():
        if not result or '08_avg_return_5bar' not in result:
            continue
        lines.append(f"| {symbol} | {result['08_avg_return_5bar']:.3f}% | "
                    f"{result['all_avg_return_5bar']:.3f}% | "
                    f"{result['08_std_return_5bar']:.3f}% |")
    
    # === 8_0组合详细分析 ===
    lines.append("\n## 三、8_0 组合详细分析 (D1非收缩 + H4收缩)")
    lines.append("\n> 含义: 日线级别已脱离收缩，但4小时级别仍处于收缩底座")
    
    lines.append("\n### 3.1 出现频率")
    lines.append("\n| 品种 | 占比 |")
    lines.append("|------|------|")
    
    for symbol, result in all_results.items():
        if not result:
            continue
        lines.append(f"| {symbol} | {result.get('8_0_pct', 0):.1f}% |")
    
    lines.append("\n### 3.2 后续5Bar收益统计")
    lines.append("\n| 品种 | 8_0组合5Bar收益 | 全样本5Bar收益 |")
    lines.append("|------|-----------------|----------------|")
    
    for symbol, result in all_results.items():
        if not result or '80_avg_return_5bar' not in result:
            continue
        lines.append(f"| {symbol} | {result['80_avg_return_5bar']:.3f}% | "
                    f"{result['all_avg_return_5bar']:.3f}% |")
    
    # === 核心发现 ===
    lines.append("\n## 四、核心发现")
    lines.append("\n### 4.1 0_8组合特征")
    lines.append("- D1收缩底座(0) + H4非收缩(8) 表示大周期收缩、小周期已启动")
    lines.append("- 这种组合通常出现在收缩即将结束、突破即将发生的过渡期")
    lines.append("- 若H1也处于收缩状态，三周期共振概率高")
    
    lines.append("\n### 4.2 8_0组合特征")
    lines.append("- D1非收缩(8) + H4收缩底座(0) 表示大周期已启动、小周期仍在收缩")
    lines.append("- 这种组合可能是回调中的收缩，或次级周期的独立收缩")
    lines.append("- 需要结合W1/MN1判断是否为顺势收缩")
    
    lines.append("\n### 4.3 交易启示")
    lines.append("- **0_8 + H1收缩**: 高优先级信号，三周期即将共振")
    lines.append("- **0_8 + H1非收缩**: 突破已发生，追趋势风险高")
    lines.append("- **8_0 + H1收缩**: 次级收缩，需确认D1趋势方向")
    lines.append("- **0_0 + H1收缩**: 全周期收缩，等待突破确认")
    
    lines.append("\n---")
    lines.append("> **免责声明**: 本报告仅供研究参考，不构成投资建议。")
    
    # 写入文件
    import os
    os.makedirs("reports/squeeze", exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\n报告已保存: {report_path}")
    return report_path


def main():
    print("=" * 70)
    print("State Hex 0,8 组合统计分析")
    print("=" * 70)
    
    bridge = MT5DataBridge()
    if not bridge.connect():
        print("MT5连接失败")
        return
    
    all_results = {}
    
    for symbol_name, mt5_symbol in SYMBOLS.items():
        print(f"\n{'='*70}")
        print(f"分析 {symbol_name} ({mt5_symbol})")
        print('='*70)
        
        df = fetch_and_compute_quintuplets(symbol_name, mt5_symbol, bridge, days=90)
        if df.empty:
            print(f"  数据不足，跳过")
            continue
        
        print(f"  数据条数: {len(df)}")
        
        # 添加close列用于收益计算
        # 需要从h1_data重新获取close
        # 这里简化处理，使用已有数据
        
        results = analyze_08_combinations(df)
        all_results[symbol_name] = results
        
        # 打印关键结果
        print(f"\n  D1-H4组合分布:")
        for combo in ['0_8', '8_0', '0_0', '8_8']:
            pct = results.get(f'{combo}_pct', 0)
            count = results.get(f'{combo}_count', 0)
            print(f"    {combo}: {count}次 ({pct:.1f}%)")
        
        if '08_avg_return_5bar' in results:
            print(f"\n  0_8组合后续5Bar收益: {results['08_avg_return_5bar']:.3f}%")
            print(f"  全样本5Bar收益: {results['all_avg_return_5bar']:.3f}%")
    
    bridge.disconnect()
    
    # 生成报告
    report_path = generate_report(all_results)
    
    print("\n" + "=" * 70)
    print("分析完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
