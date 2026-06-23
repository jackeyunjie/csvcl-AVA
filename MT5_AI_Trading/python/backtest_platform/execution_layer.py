"""
执行层 (Execution Layer)

职责: 模拟真实交易执行，计算绩效指标。

模块:
- SimulationEngine: 模拟撮合引擎（点差/滑点/手续费/隔夜利息）
- PortfolioManager: 仓位管理器
- PerformanceAnalyzer: 绩效统计器（标准指标 + State-Regime专属指标）
- BacktestRunner: 回测运行器（整合数据→计算→策略→执行）

核心原则:
- 模拟MT5真实执行环境
- State-Regime统计：按W1|MN1状态组合分组分析
- 绩效指标标准化，可导出SQX格式
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_engine.state_hex_engine import StateHexTriplet
from backtest_platform.strategy_layer import Signal, PortfolioState

logger = logging.getLogger(__name__)


# ============================================================================
# 核心数据类
# ============================================================================

@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    executed_price: float
    requested_price: float
    slippage: float
    commission: float
    timestamp: datetime
    error: str = ""


@dataclass
class Position:
    """持仓"""
    symbol: str
    direction: str          # "long" | "short"
    entry_price: float
    volume: float
    entry_time: datetime
    stop_loss: Optional[float]
    take_profit: Optional[float]
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0

    # State Hex上下文
    entry_triplet: Optional[StateHexTriplet] = None
    entry_state_tags: List[str] = field(default_factory=list)
    entry_energy_label: Optional[str] = None


@dataclass
class Trade:
    """已平仓交易"""
    symbol: str
    direction: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    volume: float
    pnl: float
    pnl_pct: float
    commission: float
    slippage: float
    holding_bars: int
    exit_reason: str        # "sl", "tp", "signal_flip", "end_of_data", "manual"

    # State Hex上下文
    entry_triplet: Optional[StateHexTriplet] = None
    entry_state_tags: List[str] = field(default_factory=list)
    entry_energy_label: Optional[str] = None

    # 退出时状态
    exit_triplet: Optional[StateHexTriplet] = None


@dataclass
class DailyStats:
    """每日统计"""
    date: datetime
    balance: float
    equity: float
    unrealized_pnl: float
    open_positions: int
    daily_pnl: float
    daily_return_pct: float
    high_water_mark: float
    drawdown_pct: float

    # 状态上下文
    triplet: Optional[StateHexTriplet] = None


@dataclass
class StateRegimeMetrics:
    """状态组合绩效指标"""
    regime_id: str          # "W1:hex|MN1:hex"
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    max_consecutive_wins: int
    max_consecutive_losses: int


@dataclass
class PerformanceReport:
    """绩效报告"""
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_balance: float
    final_balance: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    max_drawdown_pct: float
    max_drawdown_duration: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    expectancy: float
    avg_trade_return: float

    # State-Regime专属
    state_regime_stats: Dict[str, StateRegimeMetrics] = field(default_factory=dict)

    # 原始数据
    trades: List[Trade] = field(default_factory=list)
    daily_stats: List[DailyStats] = field(default_factory=list)


# ============================================================================
# 模拟撮合引擎
# ============================================================================

class SimulationEngine:
    """
    模拟撮合引擎

    模拟MT5的真实执行环境:
    - 点差模型 (固定/浮动/基于波动率)
    - 滑点模型 (固定/正态分布/基于流动性)
    - 手续费模型 (按手数/按成交额)
    - 隔夜利息 (Swap)
    """

    def __init__(
        self,
        spread_pips: float = 1.0,
        pip_value: float = 0.0001,      # Forex标准pip
        slippage_pips: float = 0.0,
        commission_per_lot: float = 5.0,
        swap_long: float = 0.0,          # 每手多单隔夜利息
        swap_short: float = 0.0,         # 每手空单隔夜利息
    ):
        self.spread_pips = spread_pips
        self.pip_value = pip_value
        self.slippage_pips = slippage_pips
        self.commission_per_lot = commission_per_lot
        self.swap_long = swap_long
        self.swap_short = swap_short

    def execute_entry(
        self,
        signal: Signal,
        bar: Dict[str, float],
        timestamp: datetime,
    ) -> ExecutionResult:
        """
        执行入场订单

        Args:
            signal: 交易信号
            bar: 当前K线 {open, high, low, close}
            timestamp: 执行时间

        Returns:
            ExecutionResult
        """
        # 模拟次日开盘执行
        entry_price = bar['open']

        # 点差影响
        spread_cost = self.spread_pips * self.pip_value

        if signal.direction == "long":
            # 多头：买入价 = 开盘价 + 点差
            executed_price = entry_price + spread_cost
        else:
            # 空头：卖出价 = 开盘价 - 点差
            executed_price = entry_price - spread_cost

        # 滑点
        if self.slippage_pips > 0:
            slippage = np.random.normal(0, self.slippage_pips * self.pip_value)
            executed_price += slippage
        else:
            slippage = 0.0

        # 手续费
        commission = self.commission_per_lot * signal.size

        return ExecutionResult(
            success=True,
            executed_price=executed_price,
            requested_price=entry_price,
            slippage=slippage,
            commission=commission,
            timestamp=timestamp,
        )

    def execute_exit(
        self,
        position: Position,
        exit_price: float,
        timestamp: datetime,
        reason: str,
    ) -> ExecutionResult:
        """
        执行平仓订单

        Args:
            position: 持仓
            exit_price: 退出价格
            timestamp: 执行时间
            reason: 退出原因

        Returns:
            ExecutionResult
        """
        # 点差影响（反向）
        spread_cost = self.spread_pips * self.pip_value

        if position.direction == "long":
            # 多头平仓：卖出价 = 价格 - 点差
            executed_price = exit_price - spread_cost
        else:
            # 空头平仓：买入价 = 价格 + 点差
            executed_price = exit_price + spread_cost

        # 滑点
        if self.slippage_pips > 0:
            slippage = np.random.normal(0, self.slippage_pips * self.pip_value)
            executed_price += slippage
        else:
            slippage = 0.0

        # 手续费
        commission = self.commission_per_lot * position.volume

        return ExecutionResult(
            success=True,
            executed_price=executed_price,
            requested_price=exit_price,
            slippage=slippage,
            commission=commission,
            timestamp=timestamp,
        )

    def calculate_swap(
        self,
        position: Position,
        holding_days: int,
    ) -> float:
        """计算隔夜利息"""
        if position.direction == "long":
            return self.swap_long * position.volume * holding_days
        else:
            return self.swap_short * position.volume * holding_days


# ============================================================================
# 仓位管理器
# ============================================================================

class PortfolioManager:
    """
    仓位管理器

    跟踪所有持仓、可用保证金、已实现/未实现盈亏。
    """

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions: List[Position] = []
        self.closed_trades: List[Trade] = []
        self.daily_stats: List[DailyStats] = []
        self.high_water_mark = initial_balance

    def open_position(
        self,
        signal: Signal,
        execution: ExecutionResult,
        symbol: str,
    ) -> Position:
        """开新仓位"""
        position = Position(
            symbol=symbol,
            direction=signal.direction,
            entry_price=execution.executed_price,
            volume=signal.size,
            entry_time=signal.timestamp,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            entry_triplet=signal.triplet,
            entry_state_tags=signal.state_tags.copy() if signal.state_tags else [],
            entry_energy_label=signal.energy_label,
        )

        # 扣除手续费
        self.balance -= execution.commission

        self.positions.append(position)
        logger.debug(f"开仓: {signal.direction} {symbol} @ {execution.executed_price:.5f} x {signal.size}")

        return position

    def close_position(
        self,
        position: Position,
        execution: ExecutionResult,
        exit_price: float,
        timestamp: datetime,
        reason: str,
    ) -> Trade:
        """平仓"""
        # 计算盈亏
        if position.direction == "long":
            pnl = (execution.executed_price - position.entry_price) * position.volume * 100000
        else:
            pnl = (position.entry_price - execution.executed_price) * position.volume * 100000

        # 扣除手续费
        pnl -= execution.commission

        # 计算隔夜利息
        holding_days = (timestamp - position.entry_time).days
        if holding_days > 0:
            swap = self.calculate_swap(position, holding_days)
            pnl += swap

        pnl_pct = pnl / self.initial_balance * 100

        trade = Trade(
            symbol=position.symbol,
            direction=position.direction,
            entry_time=position.entry_time,
            exit_time=timestamp,
            entry_price=position.entry_price,
            exit_price=execution.executed_price,
            volume=position.volume,
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission=execution.commission,
            slippage=execution.slippage,
            holding_bars=holding_days,
            exit_reason=reason,
            entry_triplet=position.entry_triplet,
            entry_state_tags=position.entry_state_tags,
            entry_energy_label=position.entry_energy_label,
        )

        self.balance += pnl
        self.closed_trades.append(trade)
        self.positions.remove(position)

        logger.debug(f"平仓: {reason} {position.symbol} @ {execution.executed_price:.5f} | PnL:{pnl:.2f}")

        return trade

    def update_equity(self, current_price: float):
        """更新权益（按当前市价）"""
        unrealized = 0.0
        for pos in self.positions:
            if pos.direction == "long":
                pos.unrealized_pnl = (current_price - pos.entry_price) * pos.volume * 100000
            else:
                pos.unrealized_pnl = (pos.entry_price - current_price) * pos.volume * 100000
            pos.unrealized_pnl_pct = pos.unrealized_pnl / self.initial_balance * 100
            unrealized += pos.unrealized_pnl

        self.equity = self.balance + unrealized

        # 更新高水位
        if self.equity > self.high_water_mark:
            self.high_water_mark = self.equity

    def calculate_swap(self, position: Position, holding_days: int) -> float:
        """计算隔夜利息（简化）"""
        return 0.0  # 默认无隔夜利息

    def get_open_position_count(self) -> int:
        """获取持仓数量"""
        return len(self.positions)

    def record_daily_stats(self, date: datetime, triplet: Optional[StateHexTriplet] = None):
        """记录每日统计"""
        prev_equity = self.daily_stats[-1].equity if self.daily_stats else self.initial_balance
        daily_pnl = self.equity - prev_equity
        daily_return_pct = daily_pnl / prev_equity * 100 if prev_equity > 0 else 0

        drawdown_pct = (self.high_water_mark - self.equity) / self.high_water_mark * 100 if self.high_water_mark > 0 else 0

        stats = DailyStats(
            date=date,
            balance=self.balance,
            equity=self.equity,
            unrealized_pnl=self.equity - self.balance,
            open_positions=len(self.positions),
            daily_pnl=daily_pnl,
            daily_return_pct=daily_return_pct,
            high_water_mark=self.high_water_mark,
            drawdown_pct=drawdown_pct,
            triplet=triplet,
        )

        self.daily_stats.append(stats)


# ============================================================================
# 绩效分析器
# ============================================================================

class PerformanceAnalyzer:
    """
    绩效统计器

    计算标准回测指标 + State-Regime 专属指标
    """

    def analyze(
        self,
        trades: List[Trade],
        daily_stats: List[DailyStats],
        initial_balance: float,
        symbol: str,
    ) -> PerformanceReport:
        """
        生成绩效报告

        标准指标:
        - Total Return, Win Rate, Profit Factor
        - Sharpe Ratio, Sortino Ratio
        - Max Drawdown, Calmar Ratio
        - Average Trade, Expectancy

        State-Regime 专属指标:
        - 各状态组合(W1|MN1)下的胜率分布
        - 状态持续时间的盈亏相关性
        """
        if not trades:
            return self._empty_report(symbol, daily_stats, initial_balance)

        # 基础统计
        profits = [t.pnl for t in trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]

        total_trades = len(trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        avg_profit = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf')

        # 收益
        final_balance = daily_stats[-1].equity if daily_stats else initial_balance
        total_return_pct = (final_balance - initial_balance) / initial_balance * 100

        # 最大回撤
        max_dd, max_dd_duration = self._calc_max_drawdown(daily_stats)

        # 夏普比率
        sharpe = self._calc_sharpe(daily_stats)

        # Sortino比率
        sortino = self._calc_sortino(daily_stats)

        # Calmar比率
        calmar = (total_return_pct / 100) / (max_dd / 100) if max_dd > 0 else 0

        # 期望值
        expectancy = (win_rate * avg_profit + (1 - win_rate) * avg_loss) if total_trades > 0 else 0

        # 平均交易收益
        avg_trade_return = np.mean(profits) if profits else 0

        # State-Regime统计
        regime_stats = self._calc_state_regime_stats(trades)

        return PerformanceReport(
            symbol=symbol,
            start_date=daily_stats[0].date if daily_stats else datetime.now(),
            end_date=daily_stats[-1].date if daily_stats else datetime.now(),
            initial_balance=initial_balance,
            final_balance=final_balance,
            total_return_pct=total_return_pct,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown_pct=max_dd,
            max_drawdown_duration=max_dd_duration,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            expectancy=expectancy,
            avg_trade_return=avg_trade_return,
            state_regime_stats=regime_stats,
            trades=trades,
            daily_stats=daily_stats,
        )

    def _empty_report(
        self,
        symbol: str,
        daily_stats: List[DailyStats],
        initial_balance: float,
    ) -> PerformanceReport:
        """空报告"""
        return PerformanceReport(
            symbol=symbol,
            start_date=daily_stats[0].date if daily_stats else datetime.now(),
            end_date=daily_stats[-1].date if daily_stats else datetime.now(),
            initial_balance=initial_balance,
            final_balance=initial_balance,
            total_return_pct=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            avg_profit=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            max_drawdown_pct=0.0,
            max_drawdown_duration=0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            expectancy=0.0,
            avg_trade_return=0.0,
            daily_stats=daily_stats,
        )

    def _calc_max_drawdown(self, daily_stats: List[DailyStats]) -> Tuple[float, int]:
        """计算最大回撤和持续时间"""
        if not daily_stats:
            return 0.0, 0

        peak = daily_stats[0].equity
        max_dd = 0.0
        max_dd_duration = 0
        current_dd_duration = 0

        for stat in daily_stats:
            if stat.equity > peak:
                peak = stat.equity
                current_dd_duration = 0
            else:
                dd = (peak - stat.equity) / peak * 100 if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
                    max_dd_duration = current_dd_duration
                current_dd_duration += 1

        return max_dd, max_dd_duration

    def _calc_sharpe(self, daily_stats: List[DailyStats]) -> float:
        """计算夏普比率"""
        if len(daily_stats) < 2:
            return 0.0

        returns = []
        for i in range(1, len(daily_stats)):
            prev = daily_stats[i - 1].equity
            curr = daily_stats[i].equity
            if prev > 0:
                returns.append((curr - prev) / prev)

        if not returns or np.std(returns) == 0:
            return 0.0

        return np.mean(returns) / np.std(returns) * np.sqrt(252)

    def _calc_sortino(self, daily_stats: List[DailyStats]) -> float:
        """计算Sortino比率"""
        if len(daily_stats) < 2:
            return 0.0

        returns = []
        for i in range(1, len(daily_stats)):
            prev = daily_stats[i - 1].equity
            curr = daily_stats[i].equity
            if prev > 0:
                returns.append((curr - prev) / prev)

        if not returns:
            return 0.0

        downside_returns = [r for r in returns if r < 0]
        downside_std = np.std(downside_returns) if downside_returns else 0

        if downside_std == 0:
            return 0.0

        return np.mean(returns) / downside_std * np.sqrt(252)

    def _calc_state_regime_stats(self, trades: List[Trade]) -> Dict[str, StateRegimeMetrics]:
        """计算State-Regime专属统计"""
        regime_trades: Dict[str, List[Trade]] = defaultdict(list)

        for trade in trades:
            if trade.entry_triplet:
                regime_id = f"W1:{trade.entry_triplet.w1_hex}|MN1:{trade.entry_triplet.mn1_hex}"
                regime_trades[regime_id].append(trade)

        regime_stats = {}
        for regime_id, rt in regime_trades.items():
            profits = [t.pnl for t in rt]
            wins = [p for p in profits if p > 0]
            losses = [p for p in profits if p <= 0]

            # 连续盈亏
            consecutive_wins = 0
            consecutive_losses = 0
            max_wins = 0
            max_losses = 0
            for t in rt:
                if t.pnl > 0:
                    consecutive_wins += 1
                    consecutive_losses = 0
                    max_wins = max(max_wins, consecutive_wins)
                else:
                    consecutive_losses += 1
                    consecutive_wins = 0
                    max_losses = max(max_losses, consecutive_losses)

            regime_stats[regime_id] = StateRegimeMetrics(
                regime_id=regime_id,
                total_trades=len(rt),
                winning_trades=len(wins),
                losing_trades=len(losses),
                win_rate=len(wins) / len(rt) if rt else 0,
                total_pnl=sum(profits),
                avg_pnl=np.mean(profits) if profits else 0,
                avg_profit=np.mean(wins) if wins else 0,
                avg_loss=np.mean(losses) if losses else 0,
                profit_factor=abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
                max_consecutive_wins=max_wins,
                max_consecutive_losses=max_losses,
            )

        return regime_stats


# ============================================================================
# 回测运行器
# ============================================================================

class BacktestRunner:
    """
    回测运行器

    整合数据层 → 计算层 → 策略层 → 执行层
    提供一站式回测接口
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float = 10000.0,
        lot_size: float = 0.1,
        spread_pips: float = 1.0,
        commission_per_lot: float = 5.0,
        feature_pipeline: Optional[Any] = None,
    ):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.lot_size = lot_size

        # 初始化各层组件
        self.sim_engine = SimulationEngine(
            spread_pips=spread_pips,
            commission_per_lot=commission_per_lot,
        )
        self.portfolio = PortfolioManager(initial_balance=initial_balance)
        self.analyzer = PerformanceAnalyzer()

        # 策略（由外部设置）
        self.strategy = None

        # 回测状态
        self.current_position: Optional[Position] = None

        # 可选的共享FeaturePipeline（用于Regime挖掘等批量回测场景）
        self.feature_pipeline = feature_pipeline

    def set_strategy(self, strategy):
        """设置策略"""
        self.strategy = strategy

    def run(
        self,
        aligned_df: pd.DataFrame,
    ) -> PerformanceReport:
        """
        执行回测

        Args:
            aligned_df: 对齐后的多周期数据（含D1 OHLCV）

        Returns:
            PerformanceReport
        """
        from backtest_platform.compute_layer import FeaturePipeline

        if self.strategy is None:
            raise ValueError("未设置策略，请先调用set_strategy()")

        pipeline = self.feature_pipeline if self.feature_pipeline is not None else FeaturePipeline()

        logger.info(f"回测开始: {self.symbol} | 数据量: {len(aligned_df)}条")

        # 预计算：一次性计算完整数据的三元组，填充StateHexComputeEngine前缀缓存
        # 这样后续逐日调用compute_for_backtest_day时，前缀缓存始终命中
        try:
            pipeline.state_engine.compute_triplet_series(aligned_df)
            logger.info("预计算三元组完成，前缀缓存已填充")
        except Exception as e:
            logger.warning(f"预计算三元组失败: {e}")

        for i in range(len(aligned_df)):
            row = aligned_df.iloc[i]
            date = pd.to_datetime(row['timestamp'])

            # 1. 计算特征（Walk-Forward）
            try:
                features = pipeline.compute_for_backtest_day(aligned_df, i)
            except Exception as e:
                logger.debug(f"特征计算失败: {e}")
                continue

            # 2. 更新持仓市值
            current_price = row['close']
            self.portfolio.update_equity(current_price)

            # 3. 检查持仓是否需要平仓
            if self.current_position:
                exit_price, exit_reason = self._check_exit(
                    self.current_position, row, current_price
                )
                if exit_price:
                    execution = self.sim_engine.execute_exit(
                        self.current_position,
                        exit_price,
                        date,
                        exit_reason,
                    )
                    trade = self.portfolio.close_position(
                        self.current_position,
                        execution,
                        exit_price,
                        date,
                        exit_reason,
                    )
                    self.current_position = None

            # 4. 策略信号
            if self.current_position is None:
                portfolio_state = PortfolioState(
                    balance=self.portfolio.balance,
                    equity=self.portfolio.equity,
                    open_positions=[],
                )

                signal = self.strategy.on_daily_features(features, portfolio_state)

                if signal:
                    # 5. 执行入场
                    bar = {
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                    }
                    execution = self.sim_engine.execute_entry(signal, bar, date)

                    if execution.success:
                        signal.symbol = self.symbol
                        position = self.portfolio.open_position(
                            signal, execution, self.symbol
                        )
                        self.current_position = position

            # 6. 记录每日统计
            self.portfolio.record_daily_stats(date, features.triplet)

        # 强制平仓最后一笔
        if self.current_position and len(aligned_df) > 0:
            last_row = aligned_df.iloc[-1]
            last_date = pd.to_datetime(last_row['timestamp'])
            execution = self.sim_engine.execute_exit(
                self.current_position,
                last_row['close'],
                last_date,
                "end_of_data",
            )
            self.portfolio.close_position(
                self.current_position,
                execution,
                last_row['close'],
                last_date,
                "end_of_data",
            )
            self.current_position = None

        # 生成报告
        report = self.analyzer.analyze(
            trades=self.portfolio.closed_trades,
            daily_stats=self.portfolio.daily_stats,
            initial_balance=self.initial_balance,
            symbol=self.symbol,
        )

        logger.info(f"回测完成: {self.symbol} | 收益: {report.total_return_pct:+.2f}% | "
                   f"交易: {report.total_trades} | 胜率: {report.win_rate:.1%}")

        return report

    def _check_exit(
        self,
        position: Position,
        row: pd.Series,
        current_price: float,
    ) -> Tuple[Optional[float], str]:
        """检查是否需要平仓"""
        high = row['high']
        low = row['low']

        if position.direction == "long":
            # 止损
            if position.stop_loss and low <= position.stop_loss:
                return position.stop_loss, "sl"
            # 止盈
            if position.take_profit and high >= position.take_profit:
                return position.take_profit, "tp"
        else:  # short
            # 止损
            if position.stop_loss and high >= position.stop_loss:
                return position.stop_loss, "sl"
            # 止盈
            if position.take_profit and low <= position.take_profit:
                return position.take_profit, "tp"

        return None, ""


# ============================================================================
# 报告输出
# ============================================================================

class ReportPrinter:
    """报告打印器"""

    @staticmethod
    def print_report(report: PerformanceReport):
        """打印回测报告"""
        print("\n" + "=" * 70)
        print("回测绩效报告")
        print("=" * 70)
        print(f"品种: {report.symbol}")
        print(f"回测区间: {report.start_date.date() if hasattr(report.start_date, 'date') else report.start_date} ~ "
              f"{report.end_date.date() if hasattr(report.end_date, 'date') else report.end_date}")
        print(f"初始资金: {report.initial_balance:,.2f}")
        print(f"最终资金: {report.final_balance:,.2f}")
        print(f"总收益率: {report.total_return_pct:+.2f}%")
        print(f"\n交易统计:")
        print(f"  总交易: {report.total_trades}")
        print(f"  盈利: {report.winning_trades} | 亏损: {report.losing_trades}")
        print(f"  胜率: {report.win_rate:.1%}")
        print(f"  平均盈利: {report.avg_profit:+.2f}")
        print(f"  平均亏损: {report.avg_loss:+.2f}")
        print(f"  盈亏比: {report.profit_factor:.2f}")
        print(f"\n风险指标:")
        print(f"  最大回撤: {report.max_drawdown_pct:.2f}%")
        print(f"  回撤持续: {report.max_drawdown_duration}天")
        print(f"  夏普比率: {report.sharpe_ratio:.2f}")
        print(f"  Sortino比率: {report.sortino_ratio:.2f}")
        print(f"  Calmar比率: {report.calmar_ratio:.2f}")
        print(f"\n其他指标:")
        print(f"  期望值: {report.expectancy:+.2f}")
        print(f"  平均交易收益: {report.avg_trade_return:+.2f}")

        if report.state_regime_stats:
            print(f"\nState-Regime 统计:")
            for regime_id, stats in sorted(report.state_regime_stats.items()):
                print(f"  {regime_id}:")
                print(f"    交易: {stats.total_trades} | 胜率: {stats.win_rate:.1%} | 总盈亏: {stats.total_pnl:+.2f}")
                print(f"    平均盈亏: {stats.avg_pnl:+.2f} | 盈亏比: {stats.profit_factor:.2f}")

        print("=" * 70)

    @staticmethod
    def to_dict(report: PerformanceReport) -> Dict[str, Any]:
        """转换为字典（JSON导出）"""
        return {
            "symbol": report.symbol,
            "start_date": report.start_date.isoformat() if isinstance(report.start_date, datetime) else str(report.start_date),
            "end_date": report.end_date.isoformat() if isinstance(report.end_date, datetime) else str(report.end_date),
            "initial_balance": report.initial_balance,
            "final_balance": report.final_balance,
            "total_return_pct": report.total_return_pct,
            "total_trades": report.total_trades,
            "winning_trades": report.winning_trades,
            "losing_trades": report.losing_trades,
            "win_rate": report.win_rate,
            "avg_profit": report.avg_profit,
            "avg_loss": report.avg_loss,
            "profit_factor": report.profit_factor,
            "max_drawdown_pct": report.max_drawdown_pct,
            "max_drawdown_duration": report.max_drawdown_duration,
            "sharpe_ratio": report.sharpe_ratio,
            "sortino_ratio": report.sortino_ratio,
            "calmar_ratio": report.calmar_ratio,
            "expectancy": report.expectancy,
            "avg_trade_return": report.avg_trade_return,
            "state_regime_stats": {
                k: {
                    "regime_id": v.regime_id,
                    "total_trades": v.total_trades,
                    "win_rate": v.win_rate,
                    "total_pnl": v.total_pnl,
                    "profit_factor": v.profit_factor,
                }
                for k, v in report.state_regime_stats.items()
            },
        }

    @staticmethod
    def export_sqx(report: PerformanceReport) -> Dict[str, Any]:
        """
        导出为SQX兼容格式

        字段映射:
        - NetProfit → total_pnl
        - ProfitFactor → profit_factor
        - SharpeRatio → sharpe_ratio
        - MaxDrawdown → max_drawdown_pct
        - TotalTrades → total_trades
        - WinPercent → win_rate
        """
        total_pnl = report.final_balance - report.initial_balance

        return {
            "NetProfit": round(total_pnl, 2),
            "ProfitFactor": round(report.profit_factor, 2) if report.profit_factor != float('inf') else 999.99,
            "SharpeRatio": round(report.sharpe_ratio, 2),
            "SortinoRatio": round(report.sortino_ratio, 2),
            "MaxDrawdown": round(report.max_drawdown_pct, 2),
            "MaxDrawdownDuration": report.max_drawdown_duration,
            "TotalTrades": report.total_trades,
            "WinningTrades": report.winning_trades,
            "LosingTrades": report.losing_trades,
            "WinPercent": round(report.win_rate * 100, 2),
            "AvgProfit": round(report.avg_profit, 2),
            "AvgLoss": round(report.avg_loss, 2),
            "Expectancy": round(report.expectancy, 2),
            "CalmarRatio": round(report.calmar_ratio, 2),
            "TotalReturn": round(report.total_return_pct, 2),
        }


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Execution Layer Test")
    print("=" * 70)

    # 1. 测试 SimulationEngine
    print("\n[1] SimulationEngine 测试")
    sim = SimulationEngine(spread_pips=1.0, commission_per_lot=5.0)

    mock_signal = Signal(
        direction="long", size=0.1, entry_price=1.0850,
        stop_loss=1.0800, take_profit=1.0950,
        confidence=0.7, timestamp=datetime.now(),
    )
    mock_bar = {"open": 1.0850, "high": 1.0860, "low": 1.0840, "close": 1.0855}

    result = sim.execute_entry(mock_signal, mock_bar, datetime.now())
    print(f"  入场执行: 价格={result.executed_price:.5f} | 滑点={result.slippage:.5f} | 手续费={result.commission:.2f}")

    # 2. 测试 PortfolioManager
    print("\n[2] PortfolioManager 测试")
    portfolio = PortfolioManager(initial_balance=10000.0)

    position = portfolio.open_position(
        signal=mock_signal,
        execution=result,
        symbol="EURUSD",
    )
    print(f"  开仓后余额: {portfolio.balance:.2f}")
    print(f"  持仓: {position.direction} {position.volume}手 @ {position.entry_price:.5f}")

    # 模拟价格变动
    portfolio.update_equity(1.0900)
    print(f"  价格涨至1.0900后权益: {portfolio.equity:.2f}")

    # 平仓
    exit_result = sim.execute_exit(position, 1.0900, datetime.now(), "tp")
    trade = portfolio.close_position(position, exit_result, 1.0900, datetime.now(), "tp")
    print(f"  平仓后余额: {portfolio.balance:.2f}")
    print(f"  交易盈亏: {trade.pnl:+.2f} ({trade.pnl_pct:+.2f}%)")

    # 3. 测试 PerformanceAnalyzer
    print("\n[3] PerformanceAnalyzer 测试")

    # 生成模拟交易数据
    np.random.seed(42)
    mock_trades = []
    for i in range(20):
        pnl = np.random.normal(50, 100)
        mock_trades.append(Trade(
            symbol="EURUSD",
            direction="long" if i % 2 == 0 else "short",
            entry_time=datetime(2025, 1, 1) + timedelta(days=i),
            exit_time=datetime(2025, 1, 1) + timedelta(days=i + 5),
            entry_price=1.0850,
            exit_price=1.0850 + pnl / 100000,
            volume=0.1,
            pnl=pnl,
            pnl_pct=pnl / 100,
            commission=5.0,
            slippage=0.0,
            holding_bars=5,
            exit_reason="tp" if pnl > 0 else "sl",
        ))

    # 生成每日统计
    mock_daily = []
    equity = 10000.0
    for i in range(100):
        daily_pnl = np.random.normal(10, 50)
        equity += daily_pnl
        mock_daily.append(DailyStats(
            date=datetime(2025, 1, 1) + timedelta(days=i),
            balance=equity,
            equity=equity,
            unrealized_pnl=0,
            open_positions=0,
            daily_pnl=daily_pnl,
            daily_return_pct=daily_pnl / 10000 * 100,
            high_water_mark=max(10000, equity),
            drawdown_pct=0,
        ))

    analyzer = PerformanceAnalyzer()
    report = analyzer.analyze(mock_trades, mock_daily, 10000.0, "EURUSD")

    print(f"  总收益: {report.total_return_pct:+.2f}%")
    print(f"  交易次数: {report.total_trades}")
    print(f"  胜率: {report.win_rate:.1%}")
    print(f"  夏普比率: {report.sharpe_ratio:.2f}")
    print(f"  最大回撤: {report.max_drawdown_pct:.2f}%")

    # 4. 测试完整回测流程
    print("\n[4] BacktestRunner 完整流程测试")

    # 生成测试数据
    n_days = 120
    dates = pd.date_range(start="2025-01-01", periods=n_days, freq="B")
    base_price = 1.0850
    trend = np.sin(np.linspace(0, 3 * np.pi, n_days)) * 0.015
    noise = np.cumsum(np.random.randn(n_days) * 0.003)
    prices = base_price + trend + noise

    test_df = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.randn(n_days) * 0.001,
        'high': prices + abs(np.random.randn(n_days)) * 0.005,
        'low': prices - abs(np.random.randn(n_days)) * 0.005,
        'close': prices,
        'volume': np.random.randint(10000, 100000, n_days),
    })

    # 设置策略
    from backtest_platform.strategy_layer import P107StateHexStrategy
    strategy = P107StateHexStrategy(
        min_confidence=0.6,
        state_alignment_mode="loose",
    )

    runner = BacktestRunner(
        symbol="EURUSD",
        initial_balance=10000.0,
        lot_size=0.1,
        spread_pips=1.0,
        commission_per_lot=5.0,
    )
    runner.set_strategy(strategy)

    report = runner.run(test_df)

    # 打印报告
    ReportPrinter.print_report(report)

    # 5. 测试 SQX 导出
    print("\n[5] SQX 导出测试")
    sqx_data = ReportPrinter.export_sqx(report)
    for key, value in sqx_data.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
