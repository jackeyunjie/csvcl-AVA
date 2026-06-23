"""
v5 模拟盘日报自动汇总脚本

功能:
1. 读取 simulation_logs/simulation_signals_YYYYMMDD.csv
2. 按品种/方向/确认状态汇总统计
3. 生成 Markdown 日报，格式与 SIMULATION_OBSERVATION_TEMPLATE_v5.md 对齐
4. 输出到 simulation_logs/daily_summary_YYYYMMDD.md

用法:
    python run_v5_daily_summary.py [--date YYYYMMDD] [--input-dir simulation_logs] [--output-dir simulation_logs]

    不指定 --date 则处理当天数据
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd


def generate_daily_summary(date_str: str = None, input_dir: str = "simulation_logs", output_dir: str = "simulation_logs"):
    """生成日报"""
    
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    
    input_path = Path(input_dir) / f"simulation_signals_{date_str}.csv"
    output_path = Path(output_dir) / f"daily_summary_{date_str}.md"
    
    print(f"=" * 60)
    print(f"v5 模拟盘日报汇总 | {date_str}")
    print(f"=" * 60)
    
    # 检查输入文件
    if not input_path.exists():
        print(f"未找到输入文件: {input_path}")
        print("请先运行 run_v5_simulation.py 生成信号数据")
        return None
    
    # 读取数据
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    
    if df.empty:
        print("信号数据为空")
        return None
    
    print(f"读取到 {len(df)} 条信号记录")
    
    # 解析时间
    df['scan_time'] = pd.to_datetime(df['scan_time'])
    df['setup_time'] = pd.to_datetime(df['setup_time'])
    
    # 生成日报内容
    lines = []
    lines.append(f"# 模拟盘日报 {date_str}")
    lines.append(f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 数据来源: {input_path.name}")
    lines.append(f"> 记录数: {len(df)}")
    
    # 1. 概览统计
    lines.append("\n## 1. 概览统计")
    
    confirmed_count = df['confirmed'].sum() if 'confirmed' in df.columns else 0
    pending_count = len(df) - confirmed_count
    
    lines.append(f"\n| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总信号数 | {len(df)} |")
    lines.append(f"| 已确认突破 | {confirmed_count} |")
    lines.append(f"| 待突破(pending) | {pending_count} |")
    lines.append(f"| 确认率 | {confirmed_count/len(df)*100:.1f}% |")
    
    # 2. 品种分布
    lines.append("\n## 2. 品种分布")
    
    symbol_stats = df.groupby('symbol').agg({
        'confirmed': ['count', 'sum'],
        'adx': 'mean',
        'anchor_range_pct': 'mean',
        'squeeze_score': 'mean'
    }).round(2)
    symbol_stats.columns = ['信号数', '确认数', '平均ADX', '平均区间%', '平均分数']
    symbol_stats = symbol_stats.reset_index()
    
    lines.append("\n| 品种 | 信号数 | 确认数 | 平均ADX | 平均区间% | 平均分数 |")
    lines.append("|------|--------|--------|---------|-----------|----------|")
    for _, row in symbol_stats.iterrows():
        lines.append(f"| {row['symbol']} | {row['信号数']} | {row['确认数']} | {row['平均ADX']} | {row['平均区间%']} | {row['平均分数']} |")
    
    # 3. 方向分布
    lines.append("\n## 3. 方向分布")
    
    if 'direction' in df.columns:
        direction_stats = df.groupby('direction').size()
        lines.append("\n| 方向 | 数量 |")
        lines.append("|------|------|")
        for direction, count in direction_stats.items():
            lines.append(f"| {direction} | {count} |")
    
    # 4. ADX 分布
    lines.append("\n## 4. ADX 分布")
    
    adx_mean = df['adx'].mean()
    adx_min = df['adx'].min()
    adx_max = df['adx'].max()
    adx_lt_12 = (df['adx'] < 12).sum()
    
    lines.append(f"\n| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 平均ADX | {adx_mean:.2f} |")
    lines.append(f"| 最小ADX | {adx_min:.2f} |")
    lines.append(f"| 最大ADX | {adx_max:.2f} |")
    lines.append(f"| ADX<12 (强收缩) | {adx_lt_12} ({adx_lt_12/len(df)*100:.1f}%) |")
    
    # 5. Anchor Range 分布
    lines.append("\n## 5. Anchor Range 分布")
    
    range_mean = df['anchor_range_pct'].mean()
    range_min = df['anchor_range_pct'].min()
    range_max = df['anchor_range_pct'].max()
    range_gt_50 = (df['anchor_range_pct'] >= 0.50).sum()
    
    lines.append(f"\n| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 平均区间% | {range_mean:.3f}% |")
    lines.append(f"| 最小区间% | {range_min:.3f}% |")
    lines.append(f"| 最大区间% | {range_max:.3f}% |")
    lines.append(f"| 区间>=0.50% | {range_gt_50} ({range_gt_50/len(df)*100:.1f}%) |")
    
    # 6. 趋势共振
    lines.append("\n## 6. 趋势共振状态")
    
    if 'h4_trend' in df.columns and 'd1_trend' in df.columns:
        trend_combo = df.groupby(['h4_trend', 'd1_trend']).size().reset_index(name='count')
        lines.append("\n| H4趋势 | D1趋势 | 数量 |")
        lines.append("|--------|--------|------|")
        for _, row in trend_combo.iterrows():
            lines.append(f"| {row['h4_trend']} | {row['d1_trend']} | {row['count']} |")
    
    # 7. 候选信号明细（与模板 Section 5 对齐）
    lines.append("\n## 7. 候选信号明细")
    
    lines.append("\n| 扫描时间 | 品种 | setup时间 | 方向 | 确认 | 分数 | ADX | 区间% | H4 | D1 | 入场价 | 止损价 |")
    lines.append("|----------|------|-----------|------|------|------|-----|-------|----|----|--------|--------|")
    
    for _, row in df.iterrows():
        scan_t = row['scan_time'].strftime('%H:%M') if pd.notna(row['scan_time']) else '-'
        setup_t = row['setup_time'].strftime('%m-%d %H:%M') if pd.notna(row['setup_time']) else '-'
        direction = row.get('direction', '-')
        confirmed = '是' if row.get('confirmed', False) else '否'
        score = int(row['squeeze_score']) if pd.notna(row['squeeze_score']) else '-'
        adx = f"{row['adx']:.1f}" if pd.notna(row['adx']) else '-'
        ar = f"{row['anchor_range_pct']:.3f}" if pd.notna(row['anchor_range_pct']) else '-'
        h4 = row.get('h4_trend', '-')
        d1 = row.get('d1_trend', '-')
        entry = f"{row['entry_price']:.5f}" if pd.notna(row.get('entry_price')) else '-'
        stop = f"{row['stop_price']:.5f}" if pd.notna(row.get('stop_price')) else '-'
        
        lines.append(f"| {scan_t} | {row['symbol']} | {setup_t} | {direction} | {confirmed} | {score} | {adx} | {ar} | {h4} | {d1} | {entry} | {stop} |")
    
    # 8. 异常检测
    lines.append("\n## 8. 异常检测")
    
    anomalies = []
    
    # 检查ADX异常高值（理论上应<12）
    high_adx = df[df['adx'] > 15]
    if len(high_adx) > 0:
        anomalies.append(f"- ADX>15 的信号: {len(high_adx)} 个（预期应<12）")
    
    # 检查区间异常小值
    low_range = df[df['anchor_range_pct'] < 0.30]
    if len(low_range) > 0:
        anomalies.append(f"- 区间<0.30% 的信号: {len(low_range)} 个（参数要求>=0.50%）")
    
    # 检查分数异常
    low_score = df[df['squeeze_score'] < 2]
    if len(low_score) > 0:
        anomalies.append(f"- 分数<2 的信号: {len(low_score)} 个（参数要求>=2）")
    
    # 检查同一品种多次信号
    dup_symbols = df['symbol'].value_counts()
    multi_signals = dup_symbols[dup_symbols > 3]
    if len(multi_signals) > 0:
        for sym, count in multi_signals.items():
            anomalies.append(f"- {sym} 当日信号过多: {count} 个（可能cooldown未生效）")
    
    if anomalies:
        lines.append("\n检测到以下异常：")
        for a in anomalies:
            lines.append(a)
    else:
        lines.append("\n未检测到明显异常。")
    
    # 9. 与回测预期对比
    lines.append("\n## 9. 与回测预期对比")
    
    lines.append("\n| 指标 | 回测预期 | 当日观测 | 偏差 |")
    lines.append("|------|----------|----------|------|")
    lines.append(f"| 日均信号数 | ~0.4个/品种 | {len(df)/14:.2f}个/品种 | {'正常' if 0.2 <= len(df)/14 <= 1.0 else '偏高' if len(df)/14 > 1.0 else '偏低'} |")
    lines.append(f"| 确认率 | ~35% | {confirmed_count/len(df)*100:.1f}% | {'正常' if 25 <= confirmed_count/len(df)*100 <= 45 else '偏差'} |")
    lines.append(f"| 平均ADX | <12 | {adx_mean:.2f} | {'正常' if adx_mean < 13 else '偏高'} |")
    lines.append(f"| 平均区间% | >0.50% | {range_mean:.3f}% | {'正常' if range_mean >= 0.45 else '偏低'} |")
    
    # 10. 结论
    lines.append("\n## 10. 当日结论")
    lines.append("\n- [ ] 扫描运行正常")
    lines.append("- [ ] 参数未漂移")
    lines.append("- [ ] 信号可解释")
    lines.append("- [ ] 无系统性异常")
    lines.append("\n**备注**: ")
    
    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    
    print(f"\n日报已生成: {output_path}")
    print(f"=" * 60)
    
    return output_path


def generate_weekly_summary(start_date_str: str, end_date_str: str = None, 
                            input_dir: str = "simulation_logs", output_dir: str = "simulation_logs"):
    """生成周报（可选）"""
    
    if end_date_str is None:
        end_date = datetime.strptime(start_date_str, "%Y%m%d")
        start_date = end_date - timedelta(days=6)
    else:
        start_date = datetime.strptime(start_date_str, "%Y%m%d")
        end_date = datetime.strptime(end_date_str, "%Y%m%d")
    
    # 收集多日数据
    all_data = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y%m%d")
        input_path = Path(input_dir) / f"simulation_signals_{date_str}.csv"
        if input_path.exists():
            df = pd.read_csv(input_path, encoding="utf-8-sig")
            df['date'] = date_str
            all_data.append(df)
        current += timedelta(days=1)
    
    if not all_data:
        print(f"未找到 {start_date_str} 至 {end_date.strftime('%Y%m%d')} 的数据")
        return None
    
    combined = pd.concat(all_data, ignore_index=True)
    
    # 生成周报
    week_str = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    output_path = Path(output_dir) / f"weekly_summary_{week_str}.md"
    
    lines = []
    lines.append(f"# 模拟盘周报 {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    lines.append(f"\n> 总记录数: {len(combined)}")
    lines.append(f"> 观察天数: {combined['date'].nunique()}")
    
    # 按日统计
    daily_stats = combined.groupby('date').agg({
        'confirmed': ['count', 'sum'],
        'adx': 'mean',
        'anchor_range_pct': 'mean'
    }).round(2)
    
    lines.append("\n## 按日统计")
    lines.append("\n| 日期 | 信号数 | 确认数 | 平均ADX | 平均区间% |")
    lines.append("|------|--------|--------|---------|-----------|")
    for date, row in daily_stats.iterrows():
        lines.append(f"| {date} | {row[('confirmed', 'count')]} | {row[('confirmed', 'sum')]} | {row[('adx', 'mean')]} | {row[('anchor_range_pct', 'mean')]} |")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"周报已生成: {output_path}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description="v5 模拟盘日报/周报自动汇总")
    parser.add_argument("--date", help="指定日期 (YYYYMMDD), 默认当天")
    parser.add_argument("--week-start", help="周报开始日期 (YYYYMMDD)")
    parser.add_argument("--week-end", help="周报结束日期 (YYYYMMDD), 默认week-start+6天")
    parser.add_argument("--input-dir", default="simulation_logs", help="输入目录")
    parser.add_argument("--output-dir", default="simulation_logs", help="输出目录")
    
    args = parser.parse_args()
    
    if args.week_start:
        generate_weekly_summary(args.week_start, args.week_end, args.input_dir, args.output_dir)
    else:
        generate_daily_summary(args.date, args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
