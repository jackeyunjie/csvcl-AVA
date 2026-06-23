"""
信号评分与绩效归因系统
功能：
1. 追踪每个信号的历史表现
2. 计算策略绩效指标（胜率、盈亏比、夏普比率等）
3. 提供信号质量评分
4. 绩效归因分析（品种、策略类型、时间维度）
"""

import json
import logging
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class SignalOutcome(Enum):
    """信号结果"""
    WIN = "win"
    LOSS = "loss"
    BREAK_EVEN = "break_even"
    PENDING = "pending"
    EXPIRED = "expired"


@dataclass
class SignalRecord:
    """信号记录（用于追踪后续表现）"""
    signal_id: str
    symbol: str
    signal_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    confidence: float
    timestamp: datetime
    outcome: SignalOutcome = SignalOutcome.PENDING
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    profit_pips: float = 0.0
    profit_amount: float = 0.0
    max_favorable_excursion: float = 0.0  # 最大有利偏移
    max_adverse_excursion: float = 0.0     # 最大不利偏移
    holding_bars: int = 0


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    total_signals: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    break_even_trades: int = 0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_holding_bars: float = 0.0
    avg_confidence_win: float = 0.0
    avg_confidence_loss: float = 0.0
    expectancy: float = 0.0  # 期望值


@dataclass
class AttributionReport:
    """归因报告"""
    by_symbol: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_signal_type: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_hour: Dict[int, PerformanceMetrics] = field(default_factory=dict)
    by_day_of_week: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_confidence_bucket: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    overall: PerformanceMetrics = field(default_factory=PerformanceMetrics)


class SignalScorer:
    """
    信号评分系统

    追踪每个信号从生成到结束的完整生命周期，
    计算多维度绩效指标，为策略优化提供数据支持。
    """

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.records: Dict[str, SignalRecord] = {}
        self.symbol_records: Dict[str, List[str]] = defaultdict(list)
        self._record_counter = 0

        logger.info(f"SignalScorer初始化完成 | 最大历史: {max_history}")

    def register_signal(
        self,
        symbol: str,
        signal_type: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        position_size: float,
        confidence: float
    ) -> str:
        """
        注册一个新信号，开始追踪

        Returns:
            signal_id: 信号唯一标识
        """
        self._record_counter += 1
        signal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._record_counter}"

        record = SignalRecord(
            signal_id=signal_id,
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            confidence=confidence,
            timestamp=datetime.now()
        )

        self.records[signal_id] = record
        self.symbol_records[symbol].append(signal_id)

        # 清理旧记录
        if len(self.records) > self.max_history:
            self._cleanup_old_records()

        logger.debug(f"信号注册: {signal_id} | {symbol} {signal_type} @ {entry_price}")
        return signal_id

    def update_signal_outcome(
        self,
        signal_id: str,
        outcome: SignalOutcome,
        exit_price: Optional[float] = None,
        profit_pips: float = 0.0,
        profit_amount: float = 0.0,
        holding_bars: int = 0
    ):
        """
        更新信号结果

        Args:
            signal_id: 信号ID
            outcome: 结果类型
            exit_price: 出场价格
            profit_pips: 盈亏点数
            profit_amount: 盈亏金额
            holding_bars: 持仓K线数
        """
        if signal_id not in self.records:
            logger.warning(f"信号未找到: {signal_id}")
            return

        record = self.records[signal_id]
        record.outcome = outcome
        record.exit_price = exit_price
        record.exit_time = datetime.now()
        record.profit_pips = profit_pips
        record.profit_amount = profit_amount
        record.holding_bars = holding_bars

        logger.info(f"信号结果: {signal_id} | {outcome.value} | 盈亏: {profit_amount:.2f}")

    def update_price_observation(self, signal_id: str, current_price: float):
        """
        更新价格观察（用于计算最大偏移）

        Args:
            signal_id: 信号ID
            current_price: 当前价格
        """
        if signal_id not in self.records:
            return

        record = self.records[signal_id]
        if record.outcome != SignalOutcome.PENDING:
            return

        # 计算偏移（假设long方向，short取反）  # verify-exempt: 技术术语非建议
        if record.signal_type == "BUY":
            excursion = current_price - record.entry_price
        else:
            excursion = record.entry_price - current_price

        if excursion > 0:
            record.max_favorable_excursion = max(record.max_favorable_excursion, excursion)
        else:
            record.max_adverse_excursion = max(record.max_adverse_excursion, abs(excursion))

    def calculate_metrics(
        self,
        symbol: Optional[str] = None,
        days: Optional[int] = None
    ) -> PerformanceMetrics:
        """
        计算绩效指标

        Args:
            symbol: 指定品种（None则计算全部）
            days: 最近N天（None则全部）

        Returns:
            PerformanceMetrics
        """
        records = self._get_filtered_records(symbol, days)
        return self._compute_metrics(records)

    def generate_attribution_report(self, days: Optional[int] = None) -> AttributionReport:
        """
        生成绩效归因报告

        Args:
            days: 最近N天

        Returns:
            AttributionReport
        """
        report = AttributionReport()
        records = self._get_filtered_records(None, days)

        # 总体指标
        report.overall = self._compute_metrics(records)

        # 按品种归因
        symbol_groups = defaultdict(list)
        for r in records:
            symbol_groups[r.symbol].append(r)
        for sym, recs in symbol_groups.items():
            report.by_symbol[sym] = self._compute_metrics(recs)

        # 按信号类型归因
        type_groups = defaultdict(list)
        for r in records:
            type_groups[r.signal_type].append(r)
        for typ, recs in type_groups.items():
            report.by_signal_type[typ] = self._compute_metrics(recs)

        # 按小时归因
        hour_groups = defaultdict(list)
        for r in records:
            hour_groups[r.timestamp.hour].append(r)
        for hr, recs in hour_groups.items():
            report.by_hour[hr] = self._compute_metrics(recs)

        # 按星期归因
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        dow_groups = defaultdict(list)
        for r in records:
            dow_groups[day_names[r.timestamp.weekday()]].append(r)
        for day, recs in dow_groups.items():
            report.by_day_of_week[day] = self._compute_metrics(recs)

        # 按信心度分桶归因
        bucket_groups = defaultdict(list)
        for r in records:
            if r.confidence >= 0.8:
                bucket_groups["高(>=0.8)"].append(r)
            elif r.confidence >= 0.6:
                bucket_groups["中(0.6-0.8)"].append(r)
            else:
                bucket_groups["低(<0.6)"].append(r)
        for bucket, recs in bucket_groups.items():
            report.by_confidence_bucket[bucket] = self._compute_metrics(recs)

        return report

    def get_signal_quality_score(self, symbol: str, signal_type: str, confidence: float) -> float:
        """
        获取信号质量评分（基于历史表现）

        Returns:
            0-1 的质量评分
        """
        records = [
            r for r in self.records.values()
            if r.symbol == symbol and r.signal_type == signal_type and r.outcome != SignalOutcome.PENDING
        ]

        if len(records) < 3:
            return 0.5  # 数据不足

        # 计算该品种+信号类型的历史胜率
        wins = sum(1 for r in records if r.outcome == SignalOutcome.WIN)
        win_rate = wins / len(records)

        # 计算平均盈亏比
        profits = [r.profit_amount for r in records if r.profit_amount > 0]
        losses = [abs(r.profit_amount) for r in records if r.profit_amount < 0]
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 1
        profit_ratio = avg_profit / avg_loss if avg_loss > 0 else 0

        # 计算信心度校准度（高信心度是否对应高胜率）
        high_conf = [r for r in records if r.confidence >= 0.7]
        if high_conf:
            high_conf_win_rate = sum(1 for r in high_conf if r.outcome == SignalOutcome.WIN) / len(high_conf)
            calibration = high_conf_win_rate
        else:
            calibration = 0.5

        # 综合质量评分
        score = (
            win_rate * 0.35 +
            min(profit_ratio / 2, 1.0) * 0.25 +
            calibration * 0.25 +
            min(len(records) / 20, 1.0) * 0.15  # 样本量加成
        )

        return round(score, 3)

    def register_signal_from_trading_signal(self, signal) -> str:
        """
        从TradingSignal对象注册信号（与MultiSymbolManager集成）

        Args:
            signal: TradingSignal对象

        Returns:
            signal_id: 信号唯一标识
        """
        return self.register_signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type.value,
            entry_price=signal.entry_price or 0,
            stop_loss=signal.stop_loss or 0,
            take_profit=signal.take_profit or 0,
            position_size=signal.position_size,
            confidence=signal.confidence
        )

    def batch_update_outcomes_from_positions(
        self,
        positions: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        批量更新信号结果（从MT5持仓数据）

        Args:
            positions: MT5持仓列表，每项包含ticket, symbol, profit等

        Returns:
            更新的signal_id映射 {ticket: outcome}
        """
        updated = {}
        for pos in positions:
            ticket = pos.get('ticket')
            profit = pos.get('profit', 0)

            # 查找对应的signal记录（通过symbol匹配最近的一个）
            matching = [
                r for r in self.records.values()
                if r.symbol == pos.get('symbol') and r.outcome == SignalOutcome.PENDING
            ]

            if matching:
                # 取最近的一个pending信号
                record = max(matching, key=lambda r: r.timestamp)

                if profit > 0:
                    outcome = SignalOutcome.WIN
                elif profit < 0:
                    outcome = SignalOutcome.LOSS
                else:
                    outcome = SignalOutcome.BREAK_EVEN

                self.update_signal_outcome(
                    signal_id=record.signal_id,
                    outcome=outcome,
                    exit_price=pos.get('price_current'),
                    profit_amount=profit
                )
                updated[ticket] = record.signal_id

        return updated

    def _get_filtered_records(
        self,
        symbol: Optional[str],
        days: Optional[int]
    ) -> List[SignalRecord]:
        """获取过滤后的记录"""
        cutoff = datetime.now() - timedelta(days=days) if days else None

        records = []
        for r in self.records.values():
            if r.outcome == SignalOutcome.PENDING:
                continue
            if symbol and r.symbol != symbol:
                continue
            if cutoff and r.timestamp < cutoff:
                continue
            records.append(r)

        return records

    def _compute_metrics(self, records: List[SignalRecord]) -> PerformanceMetrics:
        """计算绩效指标"""
        metrics = PerformanceMetrics()

        if not records:
            return metrics

        metrics.total_signals = len(records)

        wins = [r for r in records if r.outcome == SignalOutcome.WIN]
        losses = [r for r in records if r.outcome == SignalOutcome.LOSS]
        be = [r for r in records if r.outcome == SignalOutcome.BREAK_EVEN]

        metrics.winning_trades = len(wins)
        metrics.losing_trades = len(losses)
        metrics.break_even_trades = len(be)
        metrics.win_rate = len(wins) / len(records) if records else 0

        profits = [r.profit_amount for r in wins]
        loss_amounts = [abs(r.profit_amount) for r in losses]

        metrics.avg_profit = np.mean(profits) if profits else 0
        metrics.avg_loss = np.mean(loss_amounts) if loss_amounts else 0

        total_profit = sum(profits)
        total_loss = sum(loss_amounts)
        metrics.profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        # 夏普比率（简化版）
        all_returns = [r.profit_amount for r in records]
        if len(all_returns) > 1 and np.std(all_returns) > 0:
            metrics.sharpe_ratio = np.mean(all_returns) / np.std(all_returns) * np.sqrt(len(all_returns))

        # 索提诺比率
        downside = [abs(r) for r in all_returns if r < 0]
        if downside and np.mean(downside) > 0:
            metrics.sortino_ratio = np.mean(all_returns) / np.mean(downside) * np.sqrt(len(all_returns))

        # 最大回撤
        metrics.max_drawdown = self._calculate_max_drawdown(all_returns)

        # 平均持仓时间
        metrics.avg_holding_bars = np.mean([r.holding_bars for r in records]) if records else 0

        # 信心度分析
        metrics.avg_confidence_win = np.mean([r.confidence for r in wins]) if wins else 0
        metrics.avg_confidence_loss = np.mean([r.confidence for r in losses]) if losses else 0

        # 期望值 = 胜率 * 平均盈利 - 败率 * 平均亏损
        metrics.expectancy = (
            metrics.win_rate * metrics.avg_profit -
            (1 - metrics.win_rate) * metrics.avg_loss
        )

        return metrics

    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """计算最大回撤"""
        if not returns:
            return 0.0

        equity = [0]
        for r in returns:
            equity.append(equity[-1] + r)

        peak = equity[0]
        max_dd = 0.0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak if peak != 0 else 0
            max_dd = max(max_dd, dd)

        return max_dd

    def _cleanup_old_records(self):
        """清理旧记录"""
        sorted_ids = sorted(
            self.records.keys(),
            key=lambda k: self.records[k].timestamp
        )
        to_remove = len(self.records) - self.max_history
        for sid in sorted_ids[:to_remove]:
            del self.records[sid]

    def export_report(self, filepath: str, days: Optional[int] = None):
        """导出报告到JSON文件"""
        report = self.generate_attribution_report(days)

        def metrics_to_dict(m: PerformanceMetrics) -> Dict:
            return {
                k: (float(v) if isinstance(v, (np.floating, float)) else v)
                for k, v in m.__dict__.items()
            }

        data = {
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "overall": metrics_to_dict(report.overall),
            "by_symbol": {k: metrics_to_dict(v) for k, v in report.by_symbol.items()},
            "by_signal_type": {k: metrics_to_dict(v) for k, v in report.by_signal_type.items()},
            "by_hour": {str(k): metrics_to_dict(v) for k, v in report.by_hour.items()},
            "by_day_of_week": {k: metrics_to_dict(v) for k, v in report.by_day_of_week.items()},
            "by_confidence_bucket": {k: metrics_to_dict(v) for k, v in report.by_confidence_bucket.items()},
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"报告已导出: {filepath}")
