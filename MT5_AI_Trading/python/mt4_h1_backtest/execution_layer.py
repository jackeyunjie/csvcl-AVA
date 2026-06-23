"""
MT4-H1 执行层

职责: H1级别回测执行、模拟撮合、绩效统计。

核心设计:
- 复用现有PortfolioManager和PerformanceAnalyzer
- BacktestRunner改为逐H1推进
- 支持H1级别开平仓（一天内可多次交易）
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest_platform.execution_layer import (
    SimulationEngine, PortfolioManager, PerformanceAnalyzer,
    BacktestRunner, PerformanceReport,
    Position, Trade, DailyStats,
)
from backtest_platform.strategy_layer import Signal, PortfolioState
from mt4_h1_backtest.compute_layer import H1FeaturePipeline, H1Features

logger = logging.getLogger(__name__)


# ============================================================================
# H1 回测运行器
# ============================================================================

class H1BacktestRunner:
    """
    H1回测运行器

    逐H1推进回测，支持:
    - H1级别开平仓
    - 日内多次交易
    - D1收盘强制平仓（可选）
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float = 10000.0,
        lot_size: float = 0.1,
        spread_pips: float = 1.0,
        commission_per_lot: float = 5.0,
        close_at_daily_end: bool = False,  # D1收盘是否强制平仓
        feature_pipeline: Optional[H1FeaturePipeline] = None,
    ):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.lot_size = lot_size
        self.close_at_daily_end = close_at_daily_end

        self.sim_engine = SimulationEngine(
            spread_pips=spread_pips,
            commission_per_lot=commission_per_lot,
        )
        self.portfolio = PortfolioManager(initial_balance=initial_balance)
        self.analyzer = PerformanceAnalyzer()

        self.strategy = None
        self.feature_pipeline = feature_pipeline or H1FeaturePipeline()
        self.current_position: Optional[Position] = None

    def set_strategy(self, strategy):
        """设置策略"""
        self.strategy = strategy

    def run(
        self,
        aligned_h1_df: pd.DataFrame,
    ) -> PerformanceReport:
        """
        执行H1回测

        Args:
            aligned_h1_df: 四周期对齐后的H1数据

        Returns:
            PerformanceReport
        """
        if self.strategy is None:
            raise ValueError("未设置策略")

        logger.info(f"H1回测开始: {self.symbol} | 数据量: {len(aligned_h1_df)}条H1")

        # 预计算：填充StateHexComputeEngine前缀缓存
        try:
            self.feature_pipeline.h1_engine.state_engine.compute_triplet_series(
                self.feature_pipeline.h1_engine._aggregate_h1_to_d1(aligned_h1_df)
            )
        except Exception:
            pass

        prev_date = None

        for i in range(len(aligned_h1_df)):
            row = aligned_h1_df.iloc[i]
            timestamp = pd.to_datetime(row['timestamp'])
            current_date = timestamp.date()

            # 1. 计算H1特征
            try:
                features = self.feature_pipeline.compute_for_backtest_bar(aligned_h1_df, i)
            except Exception as e:
                logger.debug(f"特征计算失败: {e}")
                continue

            # 2. 更新持仓市值
            current_price = row['close']
            self.portfolio.update_equity(current_price)

            # 3. 检查D1收盘强制平仓
            if self.close_at_daily_end and prev_date is not None and current_date != prev_date:
                if self.current_position:
                    self._close_position(
                        self.current_position, current_price, timestamp, "daily_close"
                    )

            prev_date = current_date

            # 4. 检查持仓是否需要平仓（止损/止盈）
            if self.current_position:
                exit_price, exit_reason = self._check_exit(
                    self.current_position, row, current_price
                )
                if exit_price:
                    self._close_position(self.current_position, exit_price, timestamp, exit_reason)

            # 5. 策略信号
            if self.current_position is None:
                portfolio_state = PortfolioState(
                    balance=self.portfolio.balance,
                    equity=self.portfolio.equity,
                    open_positions=[],
                )

                signal = self.strategy.on_h1_features(features, portfolio_state)

                if signal:
                    bar = {
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                    }
                    execution = self.sim_engine.execute_entry(signal, bar, timestamp)

                    if execution.success:
                        position = self.portfolio.open_position(
                            signal=signal,
                            execution=execution,
                            symbol=self.symbol,
                        )
                        self.current_position = position

            # 6. 记录H1统计
            self._record_h1_stats(timestamp, features)

        # 回测结束，平掉所有持仓
        if self.current_position:
            final_price = aligned_h1_df['close'].iloc[-1]
            final_ts = pd.to_datetime(aligned_h1_df['timestamp'].iloc[-1])
            self._close_position(self.current_position, final_price, final_ts, "end_of_test")

        # 生成绩效报告
        report = self.analyzer.analyze(
            trades=self.portfolio.closed_trades,
            daily_stats=self.portfolio.daily_stats,
            initial_balance=self.initial_balance,
            symbol=self.symbol,
        )

        logger.info(f"H1回测完成: {self.symbol} | 交易: {report.total_trades} | 收益: {report.total_return_pct:.1f}%")
        return report

    def _check_exit(
        self,
        position: Position,
        row: pd.Series,
        current_price: float,
    ) -> Tuple[Optional[float], Optional[str]]:
        """检查是否需要平仓"""
        bar = {
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
        }

        if position.direction == "long":
            if bar['low'] <= position.stop_loss:
                return position.stop_loss, "stop_loss"
            if bar['high'] >= position.take_profit:
                return position.take_profit, "take_profit"
        else:
            if bar['high'] >= position.stop_loss:
                return position.stop_loss, "stop_loss"
            if bar['low'] <= position.take_profit:
                return position.take_profit, "take_profit"

        return None, None

    def _close_position(
        self,
        position: Position,
        exit_price: float,
        timestamp: datetime,
        reason: str,
    ):
        """平仓"""
        execution = self.sim_engine.execute_exit(
            position, exit_price, timestamp, reason
        )
        trade = self.portfolio.close_position(
            position, execution, exit_price, timestamp, reason
        )
        self.current_position = None

    def _record_h1_stats(self, timestamp: datetime, features: H1Features):
        """记录H1统计"""
        # 复用DailyStats（按H1粒度）
        self.portfolio.record_daily_stats(timestamp, features.d1_triplet)
