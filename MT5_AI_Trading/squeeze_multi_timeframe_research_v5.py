"""
多周期共振收缩→突破统计验证研究 v5 (最终优化版)

整合四条路线最优结果:
- B1: 移除USOIL+EURGBP → 14品种白名单
- A1: 数据窗口扩展到730天
- A2: 不采用(放宽过滤降低了质量)
- B2: 出场规则对比(修复_calc_fold_metrics支持任意exit_rule)

核心修正(vs v4):
1. analyze方法支持按exit_rule过滤计算结果
2. 内置出场规则对比方法 compare_exit_rules
3. 默认使用14品种白名单 + 730天窗口
4. v4的所有优化保留: 1bar确认、ADX<12、range>0.4%、趋势强度分层

注意: 不构成投资建议, 禁止直接实盘自动交易
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from squeeze_multi_timeframe_research_v4 import (
    MultiTimeframeSqueezeResearchV4, 
    SYMBOL_MAP, SYMBOL_WHITELIST, get_symbol_cost
)
from squeeze_multi_timeframe_research_v3 import (
    SqueezeSetup, BreakoutEvent, Trade, ResearchResult
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("squeeze_mt_research_v5")

# v5: 14品种白名单 (移除USOIL, EURGBP)
SYMBOL_WHITELIST_V5 = {
    "XAGUSD", "UKOIL", "US30", "ETHUSD", "XAUUSD", 
    "UK100", "EURUSD", "AUDUSD", "US500", "GBPUSD",
    "USDJPY", "CADJPY", "GER40", "CHFJPY"
}


class MultiTimeframeSqueezeResearchV5(MultiTimeframeSqueezeResearchV4):
    """多周期共振收缩→突破统计验证引擎 v5
    
    继承v4所有方法, 修正analyze中的_calc_fold_metrics,
    新增出场规则对比方法。
    """
    
    def analyze(self, deduplicate: bool = True, 
                exit_rule_filter: str = None) -> Optional[ResearchResult]:
        """
        v5修正版analyze: 
        - exit_rule_filter: 指定分析的出场规则, None=所有规则
        - 修正了_calc_fold_metrics中硬编码"fixed_hold_5bar"的问题
        """
        if not self.breakouts:
            logger.warning("无突破事件可分析")
            return None
        
        events = self._deduplicate_breakouts(self.breakouts) if deduplicate else self.breakouts
        
        total_setups = len(self.setups)
        total_breakouts = len(self.breakouts)
        unique_breakouts = len(events)
        breakout_rate = unique_breakouts / total_setups if total_setups > 0 else 0
        
        up_breakouts = sum(1 for e in events if e.breakout_direction == "up")
        down_breakouts = sum(1 for e in events if e.breakout_direction == "down")
        direction_balance = up_breakouts / unique_breakouts if unique_breakouts > 0 else 0
        
        # 收益统计
        returns_5bar_all = [e.returns_5bar for e in events]
        returns_5bar_bo = [e.returns_5bar for e in events]
        
        raw_win_rate = sum(1 for r in returns_5bar_all if r > 0) / len(returns_5bar_all) if returns_5bar_all else 0
        
        wins = [r for r in returns_5bar_all if r > 0]
        losses = [r for r in returns_5bar_all if r < 0]
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        raw_expectancy = raw_win_rate * avg_win + (1 - raw_win_rate) * avg_loss
        
        unique_win_rate = raw_win_rate
        unique_expectancy = raw_expectancy
        
        # 1R/2R/3R
        hit_1r = sum(1 for e in events if e.hit_target_1r) / len(events) if events else 0
        hit_2r = sum(1 for e in events if e.hit_target_2r) / len(events) if events else 0
        hit_3r = sum(1 for e in events if e.hit_target_3r) / len(events) if events else 0
        stop_rate = sum(1 for e in events if e.stop_triggered) / len(events) if events else 0
        stop_after_entry_rate = sum(1 for e in events if e.stop_after_entry) / len(events) if events else 0
        
        # v5修正: 交易成本后指标支持任意exit_rule (含前缀匹配)
        if self.trades:
            if exit_rule_filter:
                # 支持前缀匹配: "structure_stop" 匹配 "structure_stop" 和 "structure_stop_time"
                # "1r_partial" 匹配 "1r_partial_trail", "1r_partial_stop", "1r_partial_time"
                filtered_trades = [t for t in self.trades 
                                   if t.exit_rule == exit_rule_filter 
                                   or t.exit_rule.startswith(exit_rule_filter + "_")]
            else:
                filtered_trades = [t for t in self.trades if t.exit_rule == "fixed_hold_5bar"]
            net_pnls = [t.net_pnl_pct for t in filtered_trades]
            net_win_rate = sum(1 for p in net_pnls if p > 0) / len(net_pnls) if net_pnls else 0
            net_expectancy = np.mean(net_pnls) if net_pnls else 0
        else:
            net_win_rate = 0
            net_expectancy = 0
        
        # 趋势共振
        by_trend = defaultdict(lambda: {"count": 0, "wins": 0, "pnls": []})
        for e in events:
            ta = e.trend_alignment
            by_trend[ta]["count"] += 1
            by_trend[ta]["pnls"].append(e.returns_5bar)
            if e.returns_5bar > 0:
                by_trend[ta]["wins"] += 1
        
        by_trend_alignment = {}
        for ta, d in by_trend.items():
            by_trend_alignment[ta] = {
                "count": d["count"],
                "win_rate": d["wins"] / d["count"] if d["count"] > 0 else 0,
                "avg_pnl": np.mean(d["pnls"]) if d["pnls"] else 0
            }
        
        # v5修正: _calc_fold_metrics_v5支持前缀匹配exit_rule
        def _calc_fold_metrics_v5(trades_sublist, rule_filter=None):
            """支持按exit_rule过滤(含前缀匹配)的fold指标计算"""
            if rule_filter:
                valid = [t for t in trades_sublist 
                        if t.exit_rule == rule_filter 
                        or t.exit_rule.startswith(rule_filter + "_")]
            else:
                valid = [t for t in trades_sublist if t.exit_rule == "fixed_hold_5bar"]
            
            if not valid:
                return {"count": 0, "win_rate": 0, "avg_gross": 0, "avg_net": 0, "expectancy": 0}
            
            pnls = [t.net_pnl_pct for t in valid]
            gross = [t.gross_pnl_pct for t in valid]
            return {
                "count": len(pnls),
                "win_rate": sum(1 for p in pnls if p > 0) / len(pnls),
                "avg_gross": np.mean(gross),
                "avg_net": np.mean(pnls),
                "expectancy": np.mean(pnls)
            }
        
        target_rule = exit_rule_filter if exit_rule_filter else "fixed_hold_5bar"
        
        train_metrics = _calc_fold_metrics_v5(
            [t for t in self.trades if t.fold == "train"], target_rule)
        validation_metrics = _calc_fold_metrics_v5(
            [t for t in self.trades if t.fold == "validation"], target_rule)
        test_metrics = _calc_fold_metrics_v5(
            [t for t in self.trades if t.fold == "test"], target_rule)
        
        # Score分组
        by_score = {}
        for e in events:
            score = e.setup.squeeze_score
            if score not in by_score:
                by_score[score] = {"count": 0, "breakouts": 0, "wins": 0, "pnls": []}
            by_score[score]["count"] += 1
            by_score[score]["breakouts"] += 1
            by_score[score]["pnls"].append(e.returns_5bar)
            if e.returns_5bar > 0:
                by_score[score]["wins"] += 1
        
        for score in by_score:
            d = by_score[score]
            d["win_rate"] = d["wins"] / d["count"] if d["count"] > 0 else 0
            d["avg_pnl"] = np.mean(d["pnls"]) if d["pnls"] else 0
        
        # 品种分组
        by_symbol = {}
        for e in events:
            sym = e.setup.symbol
            if sym not in by_symbol:
                by_symbol[sym] = {"setups": 0, "breakouts": 0, "pnls": [], "net_pnls": []}
            by_symbol[sym]["breakouts"] += 1
            by_symbol[sym]["pnls"].append(e.returns_5bar)
        
        for s in self.setups:
            sym = s.symbol
            if sym in by_symbol:
                by_symbol[sym]["setups"] += 1
        
        for sym in by_symbol:
            d = by_symbol[sym]
            d["avg_pnl"] = np.mean(d["pnls"]) if d["pnls"] else 0
            sym_net = [t.net_pnl_pct for t in self.trades 
                      if t.symbol == sym and t.exit_rule == target_rule]
            d["avg_net_pnl"] = np.mean(sym_net) if sym_net else 0
        
        # 验证状态
        if unique_breakouts < 50:
            validation_status = "样本不足"
        elif unique_win_rate > 0.55 and unique_expectancy > 0:
            validation_status = "已验证有效"
        elif net_expectancy > 0:
            validation_status = "逻辑需要调整"
        else:
            validation_status = "暂不建议进入实盘"
        
        warnings_list = []
        if direction_balance > 0.7 or direction_balance < 0.3:
            warnings_list.append(f"方向严重失衡: {direction_balance*100:.1f}%向上")
        
        result = ResearchResult(
            total_setups=total_setups,
            total_breakouts=total_breakouts,
            unique_breakouts=unique_breakouts,
            breakout_rate=breakout_rate,
            no_breakout_count=total_setups - unique_breakouts,
            up_breakouts=up_breakouts,
            down_breakouts=down_breakouts,
            direction_balance=direction_balance,
            raw_win_rate_5bar=raw_win_rate,
            raw_expectancy_5bar=raw_expectancy,
            raw_win_loss_ratio=win_loss_ratio,
            unique_win_rate_5bar=unique_win_rate,
            unique_expectancy_5bar=unique_expectancy,
            unique_win_loss_ratio=win_loss_ratio,
            returns_5bar_all_mean=np.mean(returns_5bar_all) if returns_5bar_all else 0,
            returns_5bar_all_median=np.median(returns_5bar_all) if returns_5bar_all else 0,
            returns_10bar_all_mean=np.mean([e.returns_10bar for e in events]) if events else 0,
            returns_20bar_all_mean=np.mean([e.returns_20bar for e in events]) if events else 0,
            returns_5bar_bo_mean=np.mean(returns_5bar_bo) if returns_5bar_bo else 0,
            returns_10bar_bo_mean=np.mean([e.returns_10bar for e in events]) if events else 0,
            hit_1r_rate=hit_1r,
            hit_2r_rate=hit_2r,
            hit_3r_rate=hit_3r,
            stop_rate=stop_rate,
            stop_after_entry_rate=stop_after_entry_rate,
            avg_win_5bar=avg_win,
            avg_loss_5bar=avg_loss,
            with_trend_breakouts=by_trend_alignment.get("with_trend", {}).get("count", 0),
            against_trend_breakouts=by_trend_alignment.get("against_trend", {}).get("count", 0),
            neutral_breakouts=by_trend_alignment.get("neutral", {}).get("count", 0),
            with_trend_win_rate=by_trend_alignment.get("with_trend", {}).get("win_rate", 0),
            against_trend_win_rate=by_trend_alignment.get("against_trend", {}).get("win_rate", 0),
            neutral_win_rate=by_trend_alignment.get("neutral", {}).get("win_rate", 0),
            net_win_rate_5bar=net_win_rate,
            net_expectancy_5bar=net_expectancy,
            by_score=by_score,
            by_symbol=by_symbol,
            by_trend_alignment=by_trend_alignment,
            train_metrics=train_metrics,
            validation_metrics=validation_metrics,
            test_metrics=test_metrics,
            recommendations=[],
            validation_status=validation_status,
            warnings=warnings_list
        )
        
        return result
    
    def compare_exit_rules(self, unique_events: List[BreakoutEvent]) -> Dict:
        """
        v5新增: 出场规则对比分析
        
        对比三种出场规则:
        1. fixed_hold_5bar - 固定持有5根K线
        2. structure_stop - 结构止损(anchor对边)
        3. 1r_partial - 1R减仓50% + 剩余trailing stop
        
        Returns:
            {rule_name: {
                'trades': int, 'win_rate': float, 'net_expectancy': float,
                'avg_bars': float, 'mf_hit_1r_rate': float,
                'train_metrics': {}, 'val_metrics': {}, 'test_metrics': {}
            }}
        """
        comparison = {}
        
        for rule_name in ["fixed_hold_5bar", "structure_stop", "1r_partial"]:
            logger.info(f"\n=== 出场规则: {rule_name} ===")
            
            # 对每个唯一事件运行该出场规则的回测
            trades = self._simulate_exit_rule(unique_events, rule_name)
            self.trades = trades
            
            # 用修正版analyze分析
            result = self.analyze(deduplicate=False, exit_rule_filter=rule_name)
            
            if result:
                # 计算该规则的额外指标 (使用前缀匹配)
                rule_trades = [t for t in trades 
                              if t.exit_rule == rule_name 
                              or t.exit_rule.startswith(rule_name + "_")]
                
                avg_bars = np.mean([t.bars_held for t in rule_trades]) if rule_trades else 0
                avg_mfe = np.mean([t.mfe_pct for t in rule_trades]) if rule_trades else 0
                avg_mae = np.mean([t.mae_pct for t in rule_trades]) if rule_trades else 0
                
                comparison[rule_name] = {
                    "trades": len(rule_trades),
                    "win_rate": result.net_win_rate_5bar,
                    "net_expectancy": result.net_expectancy_5bar,
                    "avg_bars": avg_bars,
                    "avg_mfe": avg_mfe,
                    "avg_mae": avg_mae,
                    "train_metrics": result.train_metrics,
                    "validation_metrics": result.validation_metrics,
                    "test_metrics": result.test_metrics,
                    "by_symbol": result.by_symbol,
                    "by_trend_alignment": result.by_trend_alignment,
                }
        
        return comparison
    
    def _simulate_exit_rule(self, unique_events: List[BreakoutEvent], 
                             rule_name: str) -> List[Trade]:
        """
        v5: 按指定出场规则模拟交易
        
        规则:
        - fixed_hold_5bar: 入场后持有5根K线
        - structure_stop: 触发anchor对边止损 或 持有30bar出场
        - 1r_partial: 1R减仓50%, 剩余移到盈亏平衡, trailing max
        """
        trades = []
        trade_counter = 0
        
        # walk-forward分区边界
        all_times = [e.breakout_timestamp for e in unique_events]
        min_ts, max_ts = min(all_times), max(all_times)
        duration = max_ts - min_ts
        train_end = min_ts + duration * 0.6
        validation_end = min_ts + duration * 0.8
        
        for event in unique_events:
            symbol_data = self.raw_data.get(event.setup.symbol)
            if symbol_data is None:
                continue
            
            df = symbol_data.get("H1")
            if df is None:
                continue
            
            entry_idx = event.setup.bar_idx + event.breakout_bar_idx
            if entry_idx >= len(df):
                continue
            
            entry_price = event.entry_price
            direction = event.breakout_direction
            symbol = event.setup.symbol
            
            # 成本
            cost_dict = get_symbol_cost(symbol)
            total_cost = cost_dict['spread_pct'] + cost_dict['commission_pct']
            
            # 分区
            fold = "train"
            if event.breakout_timestamp > train_end:
                if event.breakout_timestamp > validation_end:
                    fold = "test"
                else:
                    fold = "validation"
            
            # 止损价格
            stop_price = event.setup.anchor_low if direction == "up" else event.setup.anchor_high
            if stop_price is None:
                continue
            
            risk_pct = abs(entry_price - stop_price) / entry_price * 100
            if risk_pct <= 0:
                continue
            
            # 获取未来价格
            future = df.iloc[entry_idx:entry_idx + 31]
            if len(future) < 2:
                continue
            
            mfe = 0.0
            mae = 0.0
            exit_price = None
            exit_time = None
            exit_rule = rule_name
            bars_held = 0
            
            if rule_name == "fixed_hold_5bar":
                # 固定持有5bar
                hold = min(5, len(future) - 1)
                exit_price = future.iloc[hold]['close']
                exit_time = future.iloc[hold]['timestamp']
                bars_held = hold
                
                for j in range(1, hold + 1):
                    bar = future.iloc[j]
                    if direction == "up":
                        mfe = max(mfe, (bar['high'] - entry_price) / entry_price * 100)
                        mae = min(mae, (bar['low'] - entry_price) / entry_price * 100)
                    else:
                        mfe = max(mfe, (entry_price - bar['low']) / entry_price * 100)
                        mae = min(mae, (entry_price - bar['high']) / entry_price * 100)
            
            elif rule_name == "structure_stop":
                # 结构止损: 触发anchor对边或30bar出场
                max_bars_to_check = min(30, len(future) - 1)
                stopped = False
                
                for j in range(1, max_bars_to_check + 1):
                    bar = future.iloc[j]
                    bars_held = j
                    
                    if direction == "up":
                        mfe = max(mfe, (bar['high'] - entry_price) / entry_price * 100)
                        mae = min(mae, (bar['low'] - entry_price) / entry_price * 100)
                        if bar['low'] <= stop_price:
                            exit_price = stop_price
                            exit_time = bar['timestamp']
                            stopped = True
                            break
                    else:
                        mfe = max(mfe, (entry_price - bar['low']) / entry_price * 100)
                        mae = min(mae, (entry_price - bar['high']) / entry_price * 100)
                        if bar['high'] >= stop_price:
                            exit_price = stop_price
                            exit_time = bar['timestamp']
                            stopped = True
                            break
                
                if not stopped:
                    last = future.iloc[max_bars_to_check]
                    exit_price = last['close']
                    exit_time = last['timestamp']
                    exit_rule = "structure_stop_time"
            
            elif rule_name == "1r_partial":
                # 1R减仓50% + 剩余移到盈亏平衡, trailing max
                max_bars_to_check = min(30, len(future) - 1)
                partial_done = False
                trailing_stop = stop_price
                
                for j in range(1, max_bars_to_check + 1):
                    bar = future.iloc[j]
                    bars_held = j
                    
                    if direction == "up":
                        mfe = max(mfe, (bar['high'] - entry_price) / entry_price * 100)
                        mae = min(mae, (bar['low'] - entry_price) / entry_price * 100)
                        
                        # 检查是否到达1R
                        if not partial_done:
                            r1_price = entry_price + (entry_price * risk_pct / 100)
                            if bar['high'] >= r1_price:
                                partial_done = True
                                trailing_stop = entry_price  # 剩余移到盈亏平衡
                        
                        # 检查是否触发trailing stop
                        if partial_done:
                            # 更新trailing (使用入场后最高价)
                            latest_high = future.iloc[1:j+1]['high'].max()
                            new_trail = latest_high - (entry_price * risk_pct / 100) * 0.5
                            trailing_stop = max(trailing_stop, new_trail)
                            
                            if bar['low'] <= trailing_stop:
                                exit_price = trailing_stop
                                exit_time = bar['timestamp']
                                exit_rule = "1r_partial_trail"
                                break
                        else:
                            # 尚未到1R, 检查原始止损
                            if bar['low'] <= stop_price:
                                exit_price = stop_price
                                exit_time = bar['timestamp']
                                exit_rule = "1r_partial_stop"
                                break
                    else:
                        mfe = max(mfe, (entry_price - bar['low']) / entry_price * 100)
                        mae = min(mae, (entry_price - bar['high']) / entry_price * 100)
                        
                        if not partial_done:
                            r1_price = entry_price - (entry_price * risk_pct / 100)
                            if bar['low'] <= r1_price:
                                partial_done = True
                                trailing_stop = entry_price
                        
                        if partial_done:
                            latest_low = future.iloc[1:j+1]['low'].min()
                            new_trail = latest_low + (entry_price * risk_pct / 100) * 0.5
                            trailing_stop = min(trailing_stop, new_trail)
                            
                            if bar['high'] >= trailing_stop:
                                exit_price = trailing_stop
                                exit_time = bar['timestamp']
                                exit_rule = "1r_partial_trail"
                                break
                        else:
                            if bar['high'] >= stop_price:
                                exit_price = stop_price
                                exit_time = bar['timestamp']
                                exit_rule = "1r_partial_stop"
                                break
                
                if exit_price is None:
                    last = future.iloc[min(max_bars_to_check, len(future) - 1)]
                    exit_price = last['close']
                    exit_time = last['timestamp']
                    exit_rule = "1r_partial_time"
            
            if exit_price is None:
                continue
            
            # 计算PnL
            if rule_name == "1r_partial" and partial_done:
                # 50%在1R止盈 + 50%在退出价
                r_pnl = risk_pct  # 1R部分
                if direction == "up":
                    remaining_pnl = (exit_price - entry_price) / entry_price * 100
                else:
                    remaining_pnl = (entry_price - exit_price) / entry_price * 100
                gross_pnl = 0.5 * r_pnl + 0.5 * remaining_pnl
            else:
                if direction == "up":
                    gross_pnl = (exit_price - entry_price) / entry_price * 100
                else:
                    gross_pnl = (entry_price - exit_price) / entry_price * 100
            
            net_pnl = gross_pnl - total_cost
            
            trade_counter += 1
            trade = Trade(
                trade_id=f"T{trade_counter:06d}",
                event_id=event.event_id,
                symbol=symbol,
                direction=direction,
                entry_time=event.breakout_timestamp,
                entry_price=entry_price,
                exit_time=exit_time,
                exit_price=exit_price,
                exit_rule=exit_rule,
                gross_pnl_pct=gross_pnl,
                cost_pct=total_cost,
                net_pnl_pct=net_pnl,
                mfe_pct=mfe,
                mae_pct=mae,
                bars_held=bars_held,
                fold=fold
            )
            trades.append(trade)
        
        logger.info(f"  规则 {rule_name}: 生成 {len(trades)} 笔交易")
        return trades
    
    def generate_report(self, result: ResearchResult, 
                        exit_rule_name: str = "fixed_hold_5bar",
                        param_analysis: Dict = None,
                        output_dir: str = "reports/squeeze") -> Tuple[str, str, str, str]:
        """v5: 生成研究报告和CSV (继承v4格式)"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        lines = []
        lines.append("# 多周期共振收缩→突破统计验证研究报告 v5")
        lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"\n## 验证状态: {result.validation_status}")
        lines.append(f"\n## 出场规则: {exit_rule_name}")
        
        if result.warnings:
            lines.append("\n### 警告")
            for w in result.warnings:
                lines.append(f"- {w}")
        
        # 样本概览
        lines.append("\n---\n")
        lines.append("\n## 一、样本概览\n")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 总Setup数 | {result.total_setups} |")
        lines.append(f"| 突破事件数(原始) | {result.total_breakouts} |")
        lines.append(f"| 唯一突破事件数 | {result.unique_breakouts} |")
        lines.append(f"| 突破率 | {result.breakout_rate*100:.1f}% |")
        lines.append(f"| 未突破数 | {result.no_breakout_count} |")
        lines.append(f"| 向上突破 | {result.up_breakouts} |")
        lines.append(f"| 向下突破 | {result.down_breakouts} |")
        lines.append(f"| 方向平衡 | {result.direction_balance*100:.1f}% |")
        
        # 收益统计
        lines.append("\n## 二、收益统计\n")
        lines.append("| 持有周期 | 均值 | 中位数 |")
        lines.append("|----------|------|--------|")
        lines.append(f"| 5bar | {result.returns_5bar_all_mean:.3f}% | {result.returns_5bar_all_median:.3f}% |")
        lines.append(f"| 10bar | {result.returns_10bar_all_mean:.3f}% | - |")
        lines.append(f"| 20bar | {result.returns_20bar_all_mean:.3f}% | - |")
        
        # 交易绩效
        lines.append("\n## 三、交易绩效\n")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 5bar胜率 | {result.unique_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 平均盈利 | {result.avg_win_5bar:.3f}% |")
        lines.append(f"| 平均亏损 | {result.avg_loss_5bar:.3f}% |")
        lines.append(f"| 盈亏比 | {result.unique_win_loss_ratio:.2f} |")
        lines.append(f"| 期望值 | {result.unique_expectancy_5bar:.3f}% |")
        
        # 交易成本后
        lines.append("\n## 四、交易成本后指标\n")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 净5bar胜率 | {result.net_win_rate_5bar*100:.1f}% |")
        lines.append(f"| 净期望值 | {result.net_expectancy_5bar:.3f}% |")
        lines.append(f"| 1R达成率 | {result.hit_1r_rate*100:.1f}% |")
        lines.append(f"| 2R达成率 | {result.hit_2r_rate*100:.1f}% |")
        lines.append(f"| 3R达成率 | {result.hit_3r_rate*100:.1f}% |")
        lines.append(f"| 止损触发率 | {result.stop_rate*100:.1f}% |")
        
        # 多周期趋势共振
        lines.append("\n## 五、多周期趋势共振分析\n")
        lines.append("| 类型 | 数量 | 胜率 | 平均PNL |")
        lines.append("|------|------|------|---------|")
        for ta in ["with_trend", "against_trend", "neutral"]:
            d = result.by_trend_alignment.get(ta, {"count": 0, "win_rate": 0, "avg_pnl": 0})
            lines.append(f"| {ta} | {d['count']} | {d['win_rate']*100:.1f}% | {d['avg_pnl']:.3f}% |")
        
        # Walk-Forward
        lines.append("\n## 六、Walk-Forward分析\n")
        lines.append("| 分区 | 交易数 | 胜率 | 平均Gross | 平均Net | 期望 |")
        lines.append("|------|--------|------|-----------|---------|------|")
        for fold_name, metrics in [("Train", result.train_metrics), 
                                    ("Validation", result.validation_metrics),
                                    ("Test", result.test_metrics)]:
            lines.append(f"| {fold_name} | {metrics['count']} | "
                        f"{metrics['win_rate']*100:.1f}% | "
                        f"{metrics['avg_gross']:.3f}% | "
                        f"{metrics['avg_net']:.3f}% | "
                        f"{metrics['expectancy']:.3f}% |")
        
        # 按品种
        lines.append("\n## 七、按品种分组\n")
        lines.append("| 品种 | Setup数 | 突破数 | 平均GrossPNL | 平均NetPNL |")
        lines.append("|------|---------|--------|--------------|------------|")
        for sym in sorted(result.by_symbol.keys()):
            d = result.by_symbol[sym]
            lines.append(f"| {sym} | {d['setups']} | {d['breakouts']} | "
                        f"{d['avg_pnl']:.3f}% | {d.get('avg_net_pnl', 0):.3f}% |")
        
        # 结论
        lines.append("\n## 八、结论\n")
        lines.append(f"**验证状态**: {result.validation_status}")
        lines.append(f"**出场规则**: {exit_rule_name}")
        
        test_exp = result.test_metrics.get('expectancy', 0)
        test_count = result.test_metrics.get('count', 0)
        if test_exp > 0 and test_count >= 30:
            lines.append(f"**Walk-Forward测试段**: 净期望{test_exp:.3f}%, 样本{test_count}")
            lines.append("**模拟盘观察**: 测试段净期望为正, 建议进入模拟盘观察")
        elif test_count < 30:
            lines.append(f"**Walk-Forward测试段**: 净期望{test_exp:.3f}%, 样本{test_count}(不足)")
            lines.append("**建议**: Test段样本不足, 建议扩大数据窗口或适度放宽过滤条件")
        else:
            lines.append(f"**Walk-Forward测试段**: 净期望{test_exp:.3f}%, 样本{test_count}")
            lines.append("**模拟盘观察**: 测试段数据不支持, 暂不进入模拟盘观察")
        
        lines.append("\n---\n")
        lines.append("> **免责声明**: 本报告仅供研究参考, 不构成投资建议。")
        lines.append("> **实盘限制**: 当前阶段禁止直接进入实盘自动交易。")
        
        # 写入报告 (v5: 文件名含出场规则名避免覆盖)
        rule_tag = exit_rule_name.replace("_", "-")[:20]
        base_name = f"squeeze_mt_research_v5_{rule_tag}_{timestamp}"
        report_path = Path(output_dir) / f"{base_name}.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"报告已生成: {report_path}")
        
        # 导出CSV
        setups_path = Path(output_dir) / f"squeeze_mt_setups_v5_{timestamp}.csv"
        events_path = Path(output_dir) / f"squeeze_mt_events_v5_{timestamp}.csv"
        trades_path = Path(output_dir) / f"squeeze_mt_trades_v5_{timestamp}.csv"
        
        self._export_csv(setups_path, events_path, trades_path)
        
        return str(report_path), str(setups_path), str(events_path), str(trades_path)
    
    def _export_csv(self, setups_path, events_path, trades_path):
        """导出CSV"""
        if self.setups:
            s_data = []
            for s in self.setups:
                s_data.append({
                    "symbol": s.symbol, "timestamp": s.timestamp,
                    "squeeze_score": s.squeeze_score,
                    "bb_width": s.bb_width, "sr_range": s.sr_range, "adx": s.adx,
                    "anchor_range_pct": s.anchor_range_pct,
                    "h4_trend_bias": s.h4_trend_bias, "d1_trend_bias": s.d1_trend_bias,
                    "conditions": ";".join(s.conditions),
                })
            pd.DataFrame(s_data).to_csv(setups_path, index=False, encoding="utf-8-sig")
        
        if self.setups and self.breakouts:
            s_dict = {s.setup_id: s for s in self.setups}
            e_data = []
            for e in self.breakouts:
                s = e.setup
                e_data.append({
                    "event_id": e.event_id, "symbol": s.symbol,
                    "breakout_timestamp": e.breakout_timestamp,
                    "direction": e.breakout_direction,
                    "entry_price": e.entry_price,
                    "returns_5bar": e.returns_5bar, "returns_10bar": e.returns_10bar,
                    "pnl_5bar": e.pnl_5bar,
                    "trend_alignment": e.trend_alignment,
                    "stopped": e.stop_triggered,
                })
            pd.DataFrame(e_data).to_csv(events_path, index=False, encoding="utf-8-sig")
        
        if self.trades:
            t_data = [{
                "trade_id": t.trade_id, "symbol": t.symbol, "direction": t.direction,
                "entry_time": t.entry_time, "exit_time": t.exit_time,
                "exit_rule": t.exit_rule,
                "gross_pnl_pct": t.gross_pnl_pct, "net_pnl_pct": t.net_pnl_pct,
                "bars_held": t.bars_held, "fold": t.fold,
            } for t in self.trades]
            pd.DataFrame(t_data).to_csv(trades_path, index=False, encoding="utf-8-sig")
        
        logger.info(f"CSV已导出: setups={setups_path}, events={events_path}, trades={trades_path}")


def print_comparison_table(results: Dict, title: str = "结果对比"):
    """打印对比表"""
    print(f"\n{'='*100}")
    print(f"  {title}")
    print(f"{'='*100}")
    
    header = f"{'路线':<20} {'Setup':>8} {'唯一':>8} {'突破率':>8} {'净胜率':>8} {'净期望':>10} {'Train':>8} {'Val':>8} {'Test':>8}"
    print(header)
    print("-" * 100)
    
    for name, data in results.items():
        if isinstance(data, dict):
            # 出场规则子对比
            for sub_name, sub_data in data.items():
                if isinstance(sub_data, dict) and "trades" in sub_data:
                    print(f"{name}-{sub_name:<15} "
                          f"{sub_data['trades']:>8} "
                          f"{sub_data['trades']:>8} "
                          f"{'-':>8} "
                          f"{sub_data['win_rate']*100:>7.1f}% "
                          f"{sub_data['net_expectancy']:>9.3f}% "
                          f"{sub_data['train_metrics']['expectancy']:>7.3f}% "
                          f"{sub_data['validation_metrics']['expectancy']:>7.3f}% "
                          f"{sub_data['test_metrics']['expectancy']:>7.3f}%")
        elif hasattr(data, 'total_setups'):
            print(f"{name:<20} "
                  f"{data.total_setups:>8} "
                  f"{data.unique_breakouts:>8} "
                  f"{data.breakout_rate*100:>7.1f}% "
                  f"{data.net_win_rate_5bar*100:>7.1f}% "
                  f"{data.net_expectancy_5bar:>9.3f}% "
                  f"{data.train_metrics['expectancy']:>7.3f}% "
                  f"{data.validation_metrics['expectancy']:>7.3f}% "
                  f"{data.test_metrics['expectancy']:>7.3f}%")
