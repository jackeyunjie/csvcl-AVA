"""
收缩观测报告生成器

用法:
  python squeeze_report.py                    # 生成全品种报告
  python squeeze_report.py --symbol EURUSD    # 单品种报告
  python squeeze_report.py --obsidian         # 同步到Obsidian
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "python"))

from analytics.squeeze_observer import SqueezeObserver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("squeeze_report")

# 路径配置
PROJECT_DIR = Path(__file__).parent
REPORTS_DIR = PROJECT_DIR / "reports" / "squeeze"
OBSIDIAN_DIR = Path("C:/Users/MECHREVO/Documents/Obsidian Vault/Trading/SqueezeObserver")


def ensure_dirs():
    """确保报告目录存在"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)


def generate_current_status_table(df) -> str:
    """生成当前市场收缩状态表"""
    if df.empty:
        return "暂无数据\n"
    
    # 取最新时间戳的数据
    latest_ts = df['timestamp'].max()
    latest_df = df[df['timestamp'] == latest_ts].copy()
    
    lines = []
    lines.append(f"### 当前时间: {latest_ts}")
    lines.append(f"### 活跃品种数: {len(latest_df)}")
    lines.append("")
    lines.append("| 品种 | 周期 | BB收缩20 | 枢轴收缩 | SR收缩 | ADX | ADX<20 | ADX<13 | ADX<9 | State=0 | 收缩分数 | 条件 |")
    lines.append("|------|------|----------|----------|--------|-----|--------|--------|-------|---------|----------|------|")
    
    for _, row in latest_df.iterrows():
        bb = "Y" if row['bb_squeezed_20'] else ""
        pivot = "Y" if row['pivot_squeezed'] else ""
        sr = "Y" if row.get('sr_squeezed', False) else ""
        adx_val = f"{row['adx']:.1f}" if not pd.isna(row['adx']) else "N/A"
        adx20 = "Y" if row['adx_lt_20'] else ""
        adx13 = "Y" if row['adx_lt_13'] else ""
        adx9 = "Y" if row['adx_lt_9'] else ""
        state0 = "Y" if row['state_is_zero'] else ""
        score = int(row['squeeze_score'])
        conditions = row['squeeze_conditions'] if pd.notna(row['squeeze_conditions']) else ""

        lines.append(f"| {row['symbol']} | {row['timeframe']} | {bb} | {pivot} | {sr} | {adx_val} | {adx20} | {adx13} | {adx9} | {state0} | {score} | {conditions} |")
    
    return "\n".join(lines)


def generate_stats_section(stats: dict) -> str:
    """生成统计汇总"""
    lines = []
    lines.append("## 二、历史统计汇总")
    lines.append("")
    lines.append(f"- 总记录数: **{stats.get('total_records', 0):,}**")
    lines.append(f"- 品种数: **{stats.get('total_symbols', 0)}**")
    lines.append(f"- 周期: {', '.join(stats.get('timeframes', []))}")
    lines.append("")
    
    lines.append("### State=0 出现统计")
    lines.append(f"- 出现次数: {stats.get('state_zero_count', 0):,}")
    lines.append(f"- 占比: {stats.get('state_zero_pct', 0):.2f}%")
    lines.append("")
    
    lines.append("### 布林带宽收缩统计")
    lines.append(f"- BB低于20%分位: {stats.get('bb_squeezed_20_count', 0):,} ({stats.get('bb_squeezed_20_pct', 0):.2f}%)")
    lines.append(f"- BB低于10%分位: {stats.get('bb_squeezed_10_count', 0):,} ({stats.get('bb_squeezed_10_pct', 0):.2f}%)")
    lines.append(f"- BB低于5%分位: {stats.get('bb_squeezed_5_count', 0):,} ({stats.get('bb_squeezed_5_pct', 0):.2f}%)")
    lines.append("")
    
    lines.append("### 枢轴收缩统计")
    lines.append(f"- 枢轴低于20%分位: {stats.get('pivot_squeezed_count', 0):,} ({stats.get('pivot_squeezed_pct', 0):.2f}%)")
    lines.append("")

    lines.append("### SR支撑阻力位间距收缩统计")
    lines.append(f"- SR间距低于20%分位: {stats.get('sr_squeezed_count', 0):,} ({stats.get('sr_squeezed_pct', 0):.2f}%)")
    lines.append("- **说明**: SR间距 = (N周期最高 - N周期最低) / 收盘价 × 100%，反映支撑阻力带的宽度")
    lines.append("- **意义**: SR间距收缩表示支撑阻力位之间的空间被压缩，突破后的潜在运行空间更大（弹簧效应）")
    lines.append("")

    lines.append("### ADX极端低值统计")
    lines.append(f"- ADX < 20: {stats.get('adx_lt_20_count', 0):,} ({stats.get('adx_lt_20_pct', 0):.2f}%)")
    lines.append(f"- ADX < 13: {stats.get('adx_lt_13_count', 0):,} ({stats.get('adx_lt_13_pct', 0):.2f}%)")
    lines.append(f"- ADX < 9: {stats.get('adx_lt_9_count', 0):,} ({stats.get('adx_lt_9_pct', 0):.2f}%)")
    lines.append("")
    
    lines.append("### 多指标共振（收缩分数≥3）")
    lines.append(f"- 高收缩次数: {stats.get('high_squeeze_count', 0):,} ({stats.get('high_squeeze_pct', 0):.2f}%)")
    lines.append("")
    
    lines.append("### 收缩分数分布")
    score_dist = stats.get('squeeze_score_dist', {})
    for score in sorted(score_dist.keys()):
        lines.append(f"- 分数={score}: {score_dist[score]:,}次")
    lines.append("")
    
    return "\n".join(lines)


def generate_opportunities_table(df) -> str:
    """生成当前交易机会表"""
    if df.empty:
        return "暂无交易机会\n"
    
    # 取最新时间戳，筛选收缩分数>=2的
    latest_ts = df['timestamp'].max()
    opportunities = df[(df['timestamp'] == latest_ts) & (df['squeeze_score'] >= 2)].copy()
    
    if opportunities.empty:
        return "当前无高收缩品种\n"
    
    # 按收缩分数排序
    opportunities = opportunities.sort_values('squeeze_score', ascending=False)
    
    lines = []
    lines.append("| 排名 | 品种 | 周期 | 收缩分数 | 满足条件 | 建议关注 |")
    lines.append("|------|------|------|----------|----------|----------|")
    
    for i, (_, row) in enumerate(opportunities.iterrows(), 1):
        conditions = row['squeeze_conditions'] if pd.notna(row['squeeze_conditions']) else ""
        lines.append(f"| {i} | {row['symbol']} | {row['timeframe']} | {int(row['squeeze_score'])} | {conditions} | 等待突破确认 |")
    
    return "\n".join(lines)


def generate_report(df, stats: dict) -> str:
    """生成完整Markdown报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = []
    lines.append(f"# 收缩观测报告 - {now}")
    lines.append("")
    lines.append("> 基于\"收缩带来扩张\"交易理念的多周期收缩观测")
    lines.append("> 观测指标：布林带宽、枢轴收缩、ADX低值、State=0、SR间距")
    lines.append("")
    
    # 一、当前市场收缩状态
    lines.append("## 一、当前市场收缩状态概览")
    lines.append("")
    lines.append(generate_current_status_table(df))
    lines.append("")
    
    # 二、历史统计
    lines.append(generate_stats_section(stats))
    lines.append("")
    
    # 三、交易机会
    lines.append("## 三、当前交易机会（收缩分数≥2）")
    lines.append("")
    lines.append(generate_opportunities_table(df))
    lines.append("")
    
    # 四、指标说明
    lines.append("## 四、指标说明")
    lines.append("")
    lines.append("### 布林带宽收缩")
    lines.append("- **公式**: (上轨 - 下轨) / 中轨")
    lines.append("- **判定**: 当前值低于过去30天历史数据的20%/10%/5%分位")
    lines.append("- **含义**: 价格波动收窄，即将选择方向")
    lines.append("")
    lines.append("### 枢轴收缩")
    lines.append("- **公式**: (20周期最高 - 20周期最低) / 收盘价 × 100")
    lines.append("- **判定**: 低于过去30天最低20%分位")
    lines.append("- **含义**: N周期内价格波动幅度收窄")
    lines.append("")

    lines.append("### SR支撑阻力位间距收缩")
    lines.append("- **公式**: (N周期阻力位 - N周期支撑位) / 收盘价 × 100")
    lines.append("- **判定**: 低于历史20%分位")
    lines.append("- **含义**: 支撑阻力带宽度收缩，价格被限制在更窄区间内，突破后潜在空间更大")
    lines.append("- **与枢轴收缩的区别**: 枢轴收缩关注波动幅度，SR间距关注支撑阻力带的结构压缩")
    lines.append("")

    lines.append("### ADX极端低值")
    lines.append("- **参数**: ADX(14)")
    lines.append("- **阈值**: <20(弱趋势) / <13(极弱) / <9(几乎无趋势)")
    lines.append("- **含义**: 趋势强度极弱，市场处于盘整")
    lines.append("")
    lines.append("### State=0")
    lines.append("- **含义**: state_hex=0，收缩底座，无额外组件")
    lines.append("- **编码**: compression=closed, trend=neutral, position=neutral, volatility=neutral")
    lines.append("")
    lines.append("### 收缩分数")
    lines.append("- **计算**: 同时满足的收缩条件数量")
    lines.append("- **高分**: ≥3表示多指标共振，突破概率较高")
    lines.append("")
    
    # 五、强化学习数据
    lines.append("## 五、强化学习应用方向")
    lines.append("")
    lines.append("### 状态空间 (State)")
    lines.append("- 布林带宽分位数")
    lines.append("- 枢轴范围分位数")
    lines.append("- ADX值")
    lines.append("- State_hex编码")
    lines.append("- 多周期同步收缩标志")
    lines.append("")
    lines.append("### 动作空间 (Action)")
    lines.append("- 0: 观望")
    lines.append("- 1: 做多（预期向上突破）")
    lines.append("- 2: 做空（预期向下突破）")
    lines.append("")
    lines.append("### 奖励函数 (Reward)")
    lines.append("- 突破后N根K线收益率")
    lines.append("- 考虑最大回撤的夏普比率")
    lines.append("- 突破方向正确性")
    lines.append("")
    
    return "\n".join(lines)


def generate_squeeze_report(df, observer, output_dir: str = None, 
                            obsidian_vault: str = None) -> tuple:
    """
    生成收缩观测报告并保存
    
    Args:
        df: analyze_all返回的DataFrame
        observer: SqueezeObserver实例
        output_dir: 报告输出目录
        obsidian_vault: Obsidian Vault路径
        
    Returns:
        (report_path, obsidian_path)
    """
    ensure_dirs()
    
    # 生成统计
    stats = observer.summarize_squeeze_stats(df)
    
    # 生成报告内容
    report = generate_report(df, stats)
    
    # 保存
    filename = f"squeeze_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    
    # 项目目录
    if output_dir:
        project_path = Path(output_dir) / filename
        project_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        project_path = REPORTS_DIR / filename
    
    with open(project_path, 'w', encoding='utf-8') as f:
        f.write(report)
    logger.info(f"报告已保存: {project_path}")
    
    # Obsidian同步
    obsidian_path = None
    if obsidian_vault:
        obsidian_dir = Path(obsidian_vault)
        obsidian_dir.mkdir(parents=True, exist_ok=True)
        obsidian_path = obsidian_dir / filename
        with open(obsidian_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"已同步到Obsidian: {obsidian_path}")
    
    return str(project_path), str(obsidian_path) if obsidian_path else None


def save_report(content: str, filename: str = None, sync_obsidian: bool = False):
    """保存报告到项目目录和Obsidian"""
    ensure_dirs()
    
    if filename is None:
        filename = f"squeeze_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    
    # 保存到项目目录
    project_path = REPORTS_DIR / filename
    with open(project_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"报告已保存: {project_path}")
    
    # 同步到Obsidian
    if sync_obsidian:
        obsidian_path = OBSIDIAN_DIR / filename
        with open(obsidian_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"已同步到Obsidian: {obsidian_path}")
    
    return project_path


def main():
    parser = argparse.ArgumentParser(description="收缩观测报告生成器")
    parser.add_argument("--symbol", default=None, help="指定品种")
    parser.add_argument("--obsidian", action="store_true", help="同步到Obsidian")
    parser.add_argument("--output", default=None, help="输出文件名")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("开始生成收缩观测报告")
    logger.info("=" * 60)
    
    # 运行分析
    with SqueezeObserver() as observer:
        if args.symbol:
            logger.info(f"分析品种: {args.symbol}")
            df = observer.analyze_all(symbols=[args.symbol])
        else:
            logger.info("分析全部品种...")
            symbols = observer.get_all_symbols()
            logger.info(f"共 {len(symbols)} 个品种")
            df = observer.analyze_all(symbols=symbols[:5])  # 先测试5个品种
        
        if df.empty:
            logger.warning("无分析结果")
            return
        
        # 统计汇总
        logger.info("生成统计汇总...")
        stats = observer.summarize_squeeze_stats(df)
        
        # 生成报告
        logger.info("生成Markdown报告...")
        report = generate_report(df, stats)
        
        # 保存
        save_report(report, args.output, args.obsidian)
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("收缩观测报告摘要")
        print("=" * 60)
        print(f"品种数: {stats.get('total_symbols', 0)}")
        print(f"记录数: {stats.get('total_records', 0):,}")
        print(f"State=0占比: {stats.get('state_zero_pct', 0):.2f}%")
        print(f"BB收缩(20%)占比: {stats.get('bb_squeezed_20_pct', 0):.2f}%")
        print(f"枢轴收缩占比: {stats.get('pivot_squeezed_pct', 0):.2f}%")
        print(f"SR间距收缩占比: {stats.get('sr_squeezed_pct', 0):.2f}%")
        print(f"ADX<20占比: {stats.get('adx_lt_20_pct', 0):.2f}%")
        print(f"ADX<13占比: {stats.get('adx_lt_13_pct', 0):.2f}%")
        print(f"ADX<9占比: {stats.get('adx_lt_9_pct', 0):.2f}%")
        print(f"高收缩(≥3)占比: {stats.get('high_squeeze_pct', 0):.2f}%")
        print("=" * 60)
    
    logger.info("报告生成完成!")


if __name__ == "__main__":
    import pandas as pd
    main()
