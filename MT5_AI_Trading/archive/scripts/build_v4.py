#!/usr/bin/env python3
"""构建v4模块 - 追加报告生成和main"""
from pathlib import Path

v4_path = Path("squeeze_multi_timeframe_research_v4.py")

append_code = '''
    def generate_report(self, result: ResearchResult, param_analysis: Dict = None,
                        output_dir: str = "reports/squeeze") -> Tuple[str, str, str, str]:
        """生成v4研究报告和CSV"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        lines = []
        lines.append("# 多周期共振收缩→突破统计验证研究报告 v4")
        lines.append(f"\\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"\\n## 验证状态: {result.validation_status}")
        
        if result.warnings:
            lines.append("\\n### 警告")
            for w in result.warnings:
                lines.append(f"- {w}")
        
        lines.append("\\n---")
        lines.append("\\n## 一、样本概览")
        lines.append("\\n| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 总Setup数 | {result.total_setups} |")
        lines.append(f"| 突破事件数(原始) | {result.total_breakouts} |")
        lines.append(f"| 唯一突破事件数 | {result.unique_breakouts} |")
        lines.append(f"| 突破率 | {result.breakout_rate*100:.1f}% |")
        lines.append(f"| 未突破数 | {result.no_breakout_count} |")
        lines.append(f"| 向上突破 | {result.up_breakouts} |")
        lines.append(f"| 向下突破 | {result.down_breakouts} |")
        lines.append(f"| 方向平衡 | {result.direction_balance*100:.1f}% |")
        
        lines.append("\\n## 二、收益统计")
        lines.append("\\n| 持有周期 | 均值 | 中位数 |")
        lines.append("|----------|------|--------|")
        lines.append(f"| 5bar | {result.returns_5bar_all_mean:.3f}% | {result.returns_5bar_all_median:.3f}% |")
        lines.append(f"| 10bar | {result.returns_10bar_all_mean:.3f}% | - |")
        lines.append(f"| 20bar | {result.returns_20bar_all_mean:.3f}% | - |")
        
        lines.append("\\n## 三、交易绩效（原始样本）")
        lines.append("\\n| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 5bar胜率 | {result.raw_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 平均盈利 | {result.avg_win_5bar:.3f}% |")
        lines.append(f"| 平均亏损 | {result.avg_loss_5bar:.3f}% |")
        lines.append(f"| 盈亏比 | {result.raw_win_loss_ratio:.2f} |")
        lines.append(f"| 期望值 | {result.raw_expectancy_5bar:.3f}% |")
        
        lines.append("\\n## 四、交易绩效（真实唯一事件）")
        lines.append("\\n| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 唯一突破数 | {result.unique_breakouts} |")
        lines.append(f"| 5bar胜率 | {result.unique_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 盈亏比 | {result.unique_win_loss_ratio:.2f} |")
        lines.append(f"| 期望值 | {result.unique_expectancy_5bar:.3f}% |")
        lines.append(f"| 1R达成率 | {result.hit_1r_rate*100:.1f}% |")
        lines.append(f"| 2R达成率 | {result.hit_2r_rate*100:.1f}% |")
        lines.append(f"| 3R达成率 | {result.hit_3r_rate*100:.1f}% |")
        lines.append(f"| 止损触发率 | {result.stop_rate*100:.1f}% |")
        lines.append(f"| 入场后止损率 | {result.stop_after_entry_rate*100:.1f}% |")
        
        lines.append("\\n## 五、交易成本后指标")
        lines.append("\\n| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 净5bar胜率 | {result.net_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 净期望值 | {result.net_expectancy_5bar:.3f}% |")
        
        lines.append("\\n## 六、多周期趋势共振分析")
        lines.append("\\n| 类型 | 数量 | 胜率 | 平均PNL |")
        lines.append("|------|------|------|---------|")
        for key, d in result.by_trend_alignment.items():
            lines.append(f"| {key} | {d['count']} | {d['win_rate']*100:.1f}% | {d['avg_pnl']:.3f}% |")
        
        lines.append("\\n## 七、Walk-Forward分析")
        lines.append("\\n| 分区 | 交易数 | 胜率 | 平均Gross | 平均Net | 期望 |")
        lines.append("|------|--------|------|-----------|---------|------|")
        for fold_name, metrics in [("Train", result.train_metrics), ("Validation", result.validation_metrics), ("Test", result.test_metrics)]:
            lines.append(f"| {fold_name} | {metrics['count']} | {metrics['win_rate']*100:.1f}% | {metrics['avg_gross']:.3f}% | {metrics['avg_net']:.3f}% | {metrics['expectancy']:.3f}% |")
        
        lines.append("\\n## 八、按Squeeze Score分组")
        lines.append("\\n| Score | Setup数 | 突破数 | 胜率 | 平均PNL |")
        lines.append("|-------|---------|--------|------|---------|")
        for score in sorted(result.by_score.keys()):
            d = result.by_score[score]
            lines.append(f"| {score} | {d['count']} | {d['breakouts']} | {d['win_rate']*100:.1f}% | {d['avg_pnl']:.3f}% |")
        
        lines.append("\\n## 九、按品种分组")
        lines.append("\\n| 品种 | Setup数 | 突破数 | 平均GrossPNL | 平均NetPNL |")
        lines.append("|------|---------|--------|--------------|------------|")
        for sym in sorted(result.by_symbol.keys()):
            d = result.by_symbol[sym]
            lines.append(f"| {sym} | {d['setups']} | {d['breakouts']} | {d['avg_pnl']:.3f}% | {d.get('avg_net_pnl', 0):.3f}% |")
        
        lines.append("\\n## 十、v3 vs v4 差异")
        lines.append("\\n| 维度 | v3 | v4 |")
        lines.append("|------|-----|-----|")
        lines.append("| 品种过滤 | 24个全部 | 16个白名单 |")
        lines.append("| ADX过滤 | 无 | <12 |")
        lines.append("| Range过滤 | 无 | >0.4% |")
        lines.append("| 突破确认 | 无 | 1bar确认 |")
        lines.append("| 趋势强度 | bullish/bearish | strong/weak/neutral |")
        
        lines.append("\\n## 十一、结论")
        lines.append(f"\\n**验证状态**: {result.validation_status}")
        lines.append(f"\\n**多周期共振效果**: 顺势{result.with_trend_win_rate*100:.1f}% vs 逆势{result.against_trend_win_rate*100:.1f}% vs 中性{result.neutral_win_rate*100:.1f}%")
        lines.append(f"\\n**Walk-Forward测试段**: 净期望{result.test_metrics.get('expectancy', 0):.3f}%, 样本{result.test_metrics.get('count', 0)}")
        
        if result.test_metrics.get('expectancy', 0) > 0 and result.test_metrics.get('count', 0) >= 100:
            lines.append("\\n**模拟盘观察**: 测试段净期望为正，可考虑搭建模拟盘观察系统（只观察，不下单）")
        else:
            lines.append("\\n**模拟盘观察**: 测试段数据不支持，暂不进入模拟盘观察")
        
        lines.append("\\n---")
        lines.append("\\n> **免责声明**：本报告仅供研究参考，不构成投资建议。")
        lines.append("> **实盘限制**：当前阶段禁止直接进入实盘自动交易。")
        
        report_path = Path(output_dir) / f"squeeze_mt_research_v4_{timestamp}.md"
        report_path.write_text("\\n".join(lines), encoding="utf-8")
        logger.info(f"报告已保存: {report_path}")
        
        # setups CSV
        setups_records = []
        for s in self.setups:
            setups_records.append({
                'setup_id': s.setup_id, 'symbol': s.symbol, 'timestamp': s.timestamp,
                'squeeze_score': s.squeeze_score, 'conditions': '+'.join(s.conditions),
                'adx': s.adx, 'h4_trend_bias': s.h4_trend_bias, 'd1_trend_bias': s.d1_trend_bias,
                'h4_bar_time': s.h4_bar_time, 'd1_bar_time': s.d1_bar_time,
                'data_warning': s.data_warning, 'anchor_range_pct': s.anchor_range_pct,
                'cluster_id': s.cluster_id,
            })
        setups_df = pd.DataFrame(setups_records)
        setups_path = Path(output_dir) / f"squeeze_mt_setups_v4_{timestamp}.csv"
        setups_df.to_csv(setups_path, index=False)
        logger.info(f"Setup CSV已保存: {setups_path}")
        
        # events CSV
        unique_events = self._deduplicate_breakouts(self.breakouts)
        events_records = []
        for b in unique_events:
            events_records.append({
                'event_id': b.event_id, 'setup_id': b.setup.setup_id, 'symbol': b.setup.symbol,
                'breakout_timestamp': b.breakout_timestamp, 'breakout_direction': b.breakout_direction,
                'entry_price': b.entry_price, 'trend_alignment': b.trend_alignment,
                'h4_trend_bias': b.setup.h4_trend_bias, 'd1_trend_bias': b.setup.d1_trend_bias,
                'returns_1bar': b.returns_1bar, 'returns_5bar': b.returns_5bar,
                'returns_10bar': b.returns_10bar, 'returns_20bar': b.returns_20bar,
                'mfe_pct': b.mfe_pct, 'mae_pct': b.mae_pct,
                'hit_1r': b.hit_target_1r, 'hit_2r': b.hit_target_2r, 'hit_3r': b.hit_target_3r,
                'stop_triggered': b.stop_triggered, 'stop_after_entry': b.stop_after_entry,
                'pnl_5bar': b.pnl_5bar, 'pnl_10bar': b.pnl_10bar, 'pnl_20bar': b.pnl_20bar,
            })
        events_df = pd.DataFrame(events_records)
        events_path = Path(output_dir) / f"squeeze_mt_events_v4_{timestamp}.csv"
        events_df.to_csv(events_path, index=False)
        logger.info(f"Events CSV已保存: {events_path}")
        
        # trades CSV
        trades_records = []
        for t in self.trades:
            trades_records.append({
                'trade_id': t.trade_id, 'event_id': t.event_id, 'symbol': t.symbol,
                'direction': t.direction, 'entry_time': t.entry_time, 'entry_price': t.entry_price,
                'exit_time': t.exit_time, 'exit_price': t.exit_price, 'exit_rule': t.exit_rule,
                'gross_pnl_pct': t.gross_pnl_pct, 'cost_pct': t.cost_pct, 'net_pnl_pct': t.net_pnl_pct,
                'mfe_pct': t.mfe_pct, 'mae_pct': t.mae_pct, 'bars_held': t.bars_held, 'fold': t.fold,
            })
        trades_df = pd.DataFrame(trades_records)
        trades_path = Path(output_dir) / f"squeeze_mt_trades_v4_{timestamp}.csv"
        trades_df.to_csv(trades_path, index=False)
        logger.info(f"Trades CSV已保存: {trades_path}")
        
        return str(report_path), str(setups_path), str(events_path), str(trades_path)


def main():
    print("=" * 70)
    print("多周期共振收缩→突破统计验证研究 v4")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\\n")
    
    research = MultiTimeframeSqueezeResearchV4()
    
    # 获取数据
    data = research.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=365)
    
    if not data:
        print("错误: 未能获取数据")
        return
    
    # v4参数
    research.find_setups(
        min_squeeze_score=2,
        cooldown_bars=5,
        require_structural=False,
        use_whitelist=True,
        max_adx=12.0,
        min_anchor_range_pct=0.4
    )
    
    research.detect_breakouts(
        max_wait_bars=30,
        min_breakout_anchor_multiple=0.1,
        require_1bar_confirmation=True
    )
    
    unique_events = research._deduplicate_breakouts(research.breakouts)
    research.run_trade_backtest(unique_events)
    
    result = research.analyze(deduplicate=True)
    
    if result:
        print("\\n" + "=" * 60)
        print("分析结果摘要")
        print("=" * 60)
        print(f"Setup总数: {result.total_setups}")
        print(f"突破事件(原始): {result.total_breakouts}")
        print(f"唯一突破事件: {result.unique_breakouts}")
        print(f"突破率: {result.breakout_rate*100:.1f}%")
        print(f"5bar胜率(原始): {result.raw_win_rate_5bar*100:.1f}%")
        print(f"5bar胜率(唯一事件): {result.unique_win_rate_5bar*100:.1f}%")
        print(f"盈亏比(唯一事件): {result.unique_win_loss_ratio:.2f}")
        print(f"期望值(唯一事件): {result.unique_expectancy_5bar:.3f}%")
        print(f"净5bar胜率: {result.net_win_rate_5bar*100:.1f}%")
        print(f"净期望值: {result.net_expectancy_5bar:.3f}%")
        print(f"顺势突破胜率: {result.with_trend_win_rate*100:.1f}%")
        print(f"逆势突破胜率: {result.against_trend_win_rate*100:.1f}%")
        print(f"验证状态: {result.validation_status}")
        
        print(f"\\nWalk-Forward:")
        print(f"  Train: {result.train_metrics['count']}笔, 净期望{result.train_metrics['expectancy']:.3f}%")
        print(f"  Validation: {result.validation_metrics['count']}笔, 净期望{result.validation_metrics['expectancy']:.3f}%")
        print(f"  Test: {result.test_metrics['count']}笔, 净期望{result.test_metrics['expectancy']:.3f}%")
        
        report_path, setups_path, events_path, trades_path = research.generate_report(result)
        print(f"\\n报告: {report_path}")
        print(f"Setups: {setups_path}")
        if events_path:
            print(f"Events: {events_path}")
        if trades_path:
            print(f"Trades: {trades_path}")
    
    print("\\n" + "=" * 70)
    print("研究完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
'''

with open(v4_path, 'a', encoding='utf-8') as f:
    f.write(append_code)

print("Appended main to v4")
