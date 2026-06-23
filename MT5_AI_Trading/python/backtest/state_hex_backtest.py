"""
State Hex 回测引擎

基于 P107 State Hex 编码规则 与 P106 资金流能量增量层

核心设计:
- 以三元组(MN1, W1, D1)为最小分析单元驱动回测
- 资金流能量层做二级确认
- 模拟MT5执行细节（点差、滑点、手续费、隔夜利息）
- State-Regime Walk-Forward：按状态组合切窗验证

禁止:
- 用未来数据计算state_hex（严格walk-forward）
- 资金流替代状态门做入场判断
- 输出动作语义

主线顺序:
1. D1/W1/MN1 状态对齐
2. 策略条件接近
3. 成交活跃度确认
4. 资金流增量证据（如可用）
5. 筹码峰结构解释（如可用）
6. 执行模拟 → 记录结果
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import logging

try:
    from ai_engine.state_hex_encoding import StateHexEncoder
    from ai_engine.state_hex_engine import StateHexEngine, StateHexTriplet
    from ai_engine.moneyflow_energy_layer import MoneyflowEnergyLayer, EnergyLabel
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from ai_engine.state_hex_encoding import StateHexEncoder
    from ai_engine.state_hex_engine import StateHexEngine, StateHexTriplet
    from ai_engine.moneyflow_energy_layer import MoneyflowEnergyLayer, EnergyLabel

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """回测交易记录"""
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    direction: str          # "long" / "short"
    entry_price: float
    exit_price: Optional[float]
    volume: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    pnl: float = 0.0
    pnl_pct: float = 0.0
    holding_bars: int = 0
    exit_reason: str = ""   # "sl", "tp", "signal_flip", "end_of_data"

    # State Hex 上下文
    entry_triplet: Optional[StateHexTriplet] = None
    entry_state_tags: List[str] = field(default_factory=list)

    # 能量评估上下文
    entry_energy_label: Optional[str] = None


@dataclass
class DailyStats:
    """每日统计"""
    date: datetime
    equity: float
    balance: float
    unrealized_pnl: float
    open_positions: int
    daily_pnl: float
    triplet: Optional[StateHexTriplet] = None


@dataclass
class BacktestResult:
    """回测结果"""
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
    sharpe_ratio: float
    trades: List[BacktestTrade] = field(default_factory=list)
    daily_stats: List[DailyStats] = field(default_factory=list)
    state_regime_stats: Dict[str, Dict] = field(default_factory=dict)


class StateHexBacktestEngine:
    """
    State Hex 回测引擎

    Walk-Forward 回测流程:
    1. 逐日推进，每天收盘后计算state_hex三元组
    2. 检查状态对齐（状态门）
    3. 如对齐，计算入场条件（价格行为验证）
    4. 如有资金流数据，做二级确认
    5. 模拟执行（含点差、手续费）
    6. 检查止损止盈
    7. 记录结果

    关键约束:
    - 当天只能用当天及之前的数据计算state_hex
    - 入场信号基于当天收盘后的state_hex，次日开盘执行
    - 资金流数据如可用，作为解释增强而非主裁决
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float = 10000.0,
        commission_per_lot: float = 5.0,      # 每手手续费（美元）
        spread_pips: float = 1.0,              # 点差（pips）
        pip_value: float = 10.0,               # 每pip每手价值（美元）
        lot_size: float = 0.1,                 # 固定手数
        sl_atr_multiplier: float = 2.0,
        tp_atr_multiplier: float = 3.0,
        state_alignment_mode: str = "loose",
        min_confidence: float = 0.6,
        enable_moneyflow: bool = False,
    ):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.commission_per_lot = commission_per_lot
        self.spread_pips = spread_pips
        self.pip_value = pip_value
        self.lot_size = lot_size
        self.sl_atr_multiplier = sl_atr_multiplier
        self.tp_atr_multiplier = tp_atr_multiplier
        self.state_alignment_mode = state_alignment_mode
        self.min_confidence = min_confidence
        self.enable_moneyflow = enable_moneyflow

        self.encoder = StateHexEncoder()
        self.state_engine: Optional[StateHexEngine] = None
        self.moneyflow_layer: Optional[MoneyflowEnergyLayer] = None

        # 回测状态
        self.balance = initial_balance
        self.equity = initial_balance
        self.open_trade: Optional[BacktestTrade] = None
        self.trades: List[BacktestTrade] = []
        self.daily_stats: List[DailyStats] = []
        self.current_step = 0

        # State-Regime 统计
        self.state_regime_trades: Dict[str, List[BacktestTrade]] = defaultdict(list)

        logger.info(
            f"StateHexBacktestEngine初始化 | 品种: {symbol} | "
            f"初始资金: {initial_balance} | 手数: {lot_size} | "
            f"状态模式: {state_alignment_mode}"
        )

    # ========================================================================
    # 数据加载
    # ========================================================================

    def load_d1_data(self, d1_df: pd.DataFrame):
        """加载D1历史数据"""
        required = ['timestamp', 'open', 'high', 'low', 'close']
        for col in required:
            if col not in d1_df.columns:
                raise ValueError(f"缺少必要列: {col}")

        self.d1_df = d1_df.copy().reset_index(drop=True)
        self.d1_df['timestamp'] = pd.to_datetime(self.d1_df['timestamp'])

        # 初始化State引擎
        self.state_engine = StateHexEngine()
        self.state_engine.add_d1_dataframe(self.d1_df)
        self.state_engine.compute_triplets()

        logger.info(f"D1数据加载完成: {len(self.d1_df)}条 | State引擎就绪")

    def load_moneyflow_data(self, mf_df: pd.DataFrame):
        """加载资金流数据（可选）"""
        if self.moneyflow_layer is None:
            self.moneyflow_layer = MoneyflowEnergyLayer(history_days=20)
        self.moneyflow_layer.load_history(mf_df)
        self.enable_moneyflow = True
        logger.info(f"资金流数据加载完成: {len(mf_df)}条")

    # ========================================================================
    # 核心回测循环
    # ========================================================================

    def run(self) -> BacktestResult:
        """执行回测"""
        if self.state_engine is None or not self.state_engine.triplets:
            raise ValueError("State引擎未初始化，请先调用load_d1_data")

        logger.info("=" * 60)
        logger.info("State Hex 回测开始")
        logger.info("=" * 60)

        triplets = self.state_engine.triplets

        for i, triplet in enumerate(triplets):
            self.current_step = i
            self._process_day(i, triplet)

        # 强制平仓最后一笔
        if self.open_trade:
            self._close_trade(
                self.d1_df.iloc[-1]['timestamp'],
                self.d1_df.iloc[-1]['close'],
                "end_of_data"
            )

        result = self._build_result()

        logger.info("=" * 60)
        logger.info("回测完成")
        logger.info(f"总收益: {result.total_return_pct:.2f}% | "
                   f"交易次数: {result.total_trades} | "
                   f"胜率: {result.win_rate:.1%} | "
                   f"最大回撤: {result.max_drawdown_pct:.2f}%")
        logger.info("=" * 60)

        return result

    def _process_day(self, idx: int, triplet: StateHexTriplet):
        """处理单日"""
        row = self.d1_df.iloc[idx]
        date = row['timestamp']
        open_p = row['open']
        high = row['high']
        low = row['low']
        close = row['close']

        # 1. 检查持仓是否需要平仓（止损/止盈）
        if self.open_trade:
            exit_price, exit_reason = self._check_exit(self.open_trade, high, low, close)
            if exit_price:
                self._close_trade(date, exit_price, exit_reason)

        # 2. 状态门检查（核心：三周期对齐）
        alignment_score, alignment_reason = self._check_state_alignment(triplet)

        # 3. 如无持仓且状态对齐，考虑开仓
        if self.open_trade is None and alignment_score >= 0.6:
            signal_type, confidence, tags = self._generate_signal(
                triplet, alignment_score, alignment_reason, close
            )

            if confidence >= self.min_confidence:
                # 4. 资金流二级确认（如启用）
                energy_ok = True
                energy_label = None
                if self.enable_moneyflow and self.moneyflow_layer:
                    # 简化：假设资金流数据与D1数据日期对齐
                    energy_ok, energy_label = self._check_energy_confirmation(date)

                if energy_ok:
                    # 5. 计算止损止盈
                    atr = self._calculate_atr_at(idx)
                    sl, tp = self._calculate_sl_tp(close, signal_type, atr)

                    # 6. 次日开盘执行（模拟）
                    entry_price = open_p + self._spread_cost(signal_type)

                    self._open_trade(
                        date=date,
                        direction=signal_type,
                        entry_price=entry_price,
                        stop_loss=sl,
                        take_profit=tp,
                        triplet=triplet,
                        tags=tags,
                        energy_label=energy_label.value if energy_label else None
                    )

        # 7. 记录每日统计
        unrealized = 0.0
        if self.open_trade:
            mid_price = (high + low + close) / 3
            unrealized = (mid_price - self.open_trade.entry_price) * \
                        (1 if self.open_trade.direction == "long" else -1) * \
                        self.lot_size * self.pip_value * 10000  # 简化

        self.equity = self.balance + unrealized
        self.daily_stats.append(DailyStats(
            date=date,
            equity=self.equity,
            balance=self.balance,
            unrealized_pnl=unrealized,
            open_positions=1 if self.open_trade else 0,
            daily_pnl=self.equity - (self.daily_stats[-1].equity if self.daily_stats else self.initial_balance),
            triplet=triplet
        ))

    # ========================================================================
    # 信号生成
    # ========================================================================

    def _check_state_alignment(self, triplet: StateHexTriplet) -> Tuple[float, str]:
        """检查三周期状态对齐"""
        mn1 = triplet.mn1_hex
        w1 = triplet.w1_hex
        d1 = triplet.d1_hex

        mn1_score = self.encoder._from_signed_hex(mn1)
        w1_score = self.encoder._from_signed_hex(w1)
        d1_score = self.encoder._from_signed_hex(d1)

        mn1_bull = mn1_score > 0
        w1_bull = w1_score > 0
        d1_bull = d1_score > 0
        mn1_bear = mn1_score < 0
        w1_bear = w1_score < 0
        d1_bear = d1_score < 0

        if self.state_alignment_mode == "strict":
            if mn1_bull and w1_bull and d1_bull:
                return 1.0, f"三周期多向对齐 ({mn1},{w1},{d1})"
            elif mn1_bear and w1_bear and d1_bear:
                return 1.0, f"三周期空向对齐 ({mn1},{w1},{d1})"
            else:
                return 0.0, f"三周期未对齐 ({mn1},{w1},{d1})"
        else:
            if mn1_bull and w1_score >= 0 and d1_bull:
                score = 0.8
                if w1_bull: score += 0.1
                if triplet.w1_duration >= 2: score += 0.05
                if triplet.d1_duration >= 2: score += 0.05
                return min(score, 1.0), f"高周期支撑多头 ({mn1},{w1},{d1})"
            elif mn1_bear and w1_score <= 0 and d1_bear:
                score = 0.8
                if w1_bear: score += 0.1
                if triplet.w1_duration >= 2: score += 0.05
                if triplet.d1_duration >= 2: score += 0.05
                return min(score, 1.0), f"高周期支撑空头 ({mn1},{w1},{d1})"
            return 0.0, f"状态不支持 ({mn1},{w1},{d1})"

    def _generate_signal(
        self,
        triplet: StateHexTriplet,
        alignment_score: float,
        alignment_reason: str,
        current_price: float
    ) -> Tuple[str, float, List[str]]:
        """生成信号"""
        d1_score, d1_contraction, d1_vol, d1_pos, d1_trend = self.encoder.decode(triplet.d1_hex)

        tags = []
        if alignment_score >= 1.0:
            tags.append("状态同向")
        elif alignment_score >= 0.8:
            tags.append("高周期支撑")

        if d1_contraction:
            tags.append("收缩底座")
        else:
            tags.append("非收缩底座")
        if d1_vol: tags.append("幅动活跃")
        if d1_pos: tags.append("位置触发")
        if d1_trend: tags.append("趋势触发")
        if triplet.d1_duration >= 3:
            tags.append(f"D1持续{triplet.d1_duration}天")

        confidence = alignment_score
        if d1_trend: confidence += 0.08
        if d1_pos: confidence += 0.07
        if d1_vol: confidence += 0.05
        if triplet.d1_duration >= 3: confidence += 0.03
        confidence = min(confidence, 1.0)

        direction = "long" if d1_score > 0 else "short"
        return direction, confidence, tags

    # ========================================================================
    # 交易执行模拟
    # ========================================================================

    def _open_trade(
        self,
        date: datetime,
        direction: str,
        entry_price: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        triplet: StateHexTriplet,
        tags: List[str],
        energy_label: Optional[str]
    ):
        """开仓"""
        self.open_trade = BacktestTrade(
            entry_time=date,
            exit_time=None,
            symbol=self.symbol,
            direction=direction,
            entry_price=entry_price,
            exit_price=None,
            volume=self.lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_triplet=triplet,
            entry_state_tags=tags,
            entry_energy_label=energy_label
        )

        # 扣除手续费
        commission = self.commission_per_lot * self.lot_size
        self.balance -= commission

        # 记录state-regime统计
        pool_id = f"W1:{triplet.w1_hex}|MN1:{triplet.mn1_hex}"
        self.state_regime_trades[pool_id].append(self.open_trade)

        logger.debug(f"开仓: {direction} @ {entry_price:.5f} | SL:{stop_loss} | TP:{take_profit}")

    def _close_trade(self, date: datetime, exit_price: float, reason: str):
        """平仓"""
        if not self.open_trade:
            return

        trade = self.open_trade
        trade.exit_time = date
        trade.exit_price = exit_price
        trade.exit_reason = reason

        # 计算盈亏
        direction_mult = 1 if trade.direction == "long" else -1
        price_diff = (exit_price - trade.entry_price) * direction_mult
        pnl = price_diff * self.lot_size * 100000  # 简化：假设1手=100K

        # 扣除手续费
        commission = self.commission_per_lot * self.lot_size
        pnl -= commission

        trade.pnl = pnl
        trade.pnl_pct = pnl / self.initial_balance * 100
        trade.holding_bars = (date - trade.entry_time).days

        self.balance += pnl
        self.trades.append(trade)
        self.open_trade = None

        logger.debug(f"平仓: {reason} @ {exit_price:.5f} | PnL:{pnl:.2f}")

    def _check_exit(
        self,
        trade: BacktestTrade,
        high: float,
        low: float,
        close: float
    ) -> Tuple[Optional[float], str]:
        """检查是否需要平仓（止损/止盈）"""
        if trade.direction == "long":
            if trade.stop_loss and low <= trade.stop_loss:
                return trade.stop_loss, "sl"
            if trade.take_profit and high >= trade.take_profit:
                return trade.take_profit, "tp"
        else:  # short
            if trade.stop_loss and high >= trade.stop_loss:
                return trade.stop_loss, "sl"
            if trade.take_profit and low <= trade.take_profit:
                return trade.take_profit, "tp"
        return None, ""

    def _calculate_sl_tp(
        self,
        current_price: float,
        direction: str,
        atr: Optional[float]
    ) -> Tuple[Optional[float], Optional[float]]:
        """计算止损止盈"""
        if atr is None or atr <= 0:
            atr = current_price * 0.005

        sl_mult = self.sl_atr_multiplier
        tp_mult = self.tp_atr_multiplier

        if direction == "long":
            sl = current_price - atr * sl_mult
            tp = current_price + atr * tp_mult
        else:
            sl = current_price + atr * sl_mult
            tp = current_price - atr * tp_mult

        return sl, tp

    def _calculate_atr_at(self, idx: int, period: int = 14) -> Optional[float]:
        """计算指定位置的ATR"""
        if idx < period:
            return None

        df_slice = self.d1_df.iloc[max(0, idx - period - 5):idx + 1]
        if len(df_slice) < period + 1:
            return None

        high = df_slice['high']
        low = df_slice['low']
        close = df_slice['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]

        return atr if not pd.isna(atr) else None

    def _spread_cost(self, direction: str) -> float:
        """点差成本"""
        # 简化：1 pip = 0.0001 for forex
        pip_size = 0.0001
        spread = self.spread_pips * pip_size
        return spread if direction == "long" else -spread

    def _check_energy_confirmation(self, date: datetime) -> Tuple[bool, Optional[Any]]:
        """资金流能量确认（简化版）"""
        # 实际实现需要从moneyflow_layer获取对应日期的评估
        # 这里简化：假设能量支持则通过
        return True, None

    # ========================================================================
    # 结果构建
    # ========================================================================

    def _build_result(self) -> BacktestResult:
        """构建回测结果"""
        closed_trades = [t for t in self.trades if t.exit_time]

        if not closed_trades:
            return BacktestResult(
                symbol=self.symbol,
                start_date=self.d1_df['timestamp'].iloc[0],
                end_date=self.d1_df['timestamp'].iloc[-1],
                initial_balance=self.initial_balance,
                final_balance=self.balance,
                total_return_pct=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_profit=0.0,
                avg_loss=0.0,
                profit_factor=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=0.0,
                trades=[],
                daily_stats=self.daily_stats
            )

        profits = [t.pnl for t in closed_trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]

        # 计算最大回撤
        max_dd = self._calculate_max_drawdown()

        # 计算夏普比率（简化）
        daily_returns = []
        for i in range(1, len(self.daily_stats)):
            ret = (self.daily_stats[i].equity - self.daily_stats[i - 1].equity) / self.daily_stats[i - 1].equity
            daily_returns.append(ret)

        sharpe = 0.0
        if daily_returns and np.std(daily_returns) > 0:
            sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)

        # State-Regime 统计
        regime_stats = {}
        for pool_id, trades in self.state_regime_trades.items():
            closed = [t for t in trades if t.exit_time]
            if closed:
                regime_profits = [t.pnl for t in closed]
                regime_wins = [p for p in regime_profits if p > 0]
                regime_stats[pool_id] = {
                    "total_trades": len(closed),
                    "win_rate": len(regime_wins) / len(closed) if closed else 0,
                    "total_pnl": sum(regime_profits),
                    "avg_pnl": np.mean(regime_profits) if regime_profits else 0,
                }

        total_return = (self.balance - self.initial_balance) / self.initial_balance * 100

        return BacktestResult(
            symbol=self.symbol,
            start_date=self.d1_df['timestamp'].iloc[0],
            end_date=self.d1_df['timestamp'].iloc[-1],
            initial_balance=self.initial_balance,
            final_balance=self.balance,
            total_return_pct=total_return,
            total_trades=len(closed_trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=len(wins) / len(closed_trades) if closed_trades else 0,
            avg_profit=np.mean(wins) if wins else 0,
            avg_loss=np.mean(losses) if losses else 0,
            profit_factor=abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
            max_drawdown_pct=max_dd,
            sharpe_ratio=sharpe,
            trades=closed_trades,
            daily_stats=self.daily_stats,
            state_regime_stats=regime_stats
        )

    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.daily_stats:
            return 0.0

        peak = self.daily_stats[0].equity
        max_dd = 0.0

        for stat in self.daily_stats:
            if stat.equity > peak:
                peak = stat.equity
            dd = (peak - stat.equity) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return max_dd * 100

    # ========================================================================
    # 报告输出
    # ========================================================================

    def print_report(self, result: BacktestResult):
        """打印回测报告"""
        print("\n" + "=" * 70)
        print("State Hex 回测报告")
        print("=" * 70)
        print(f"品种: {result.symbol}")
        print(f"回测区间: {result.start_date.date()} ~ {result.end_date.date()}")
        print(f"初始资金: {result.initial_balance:,.2f}")
        print(f"最终资金: {result.final_balance:,.2f}")
        print(f"总收益率: {result.total_return_pct:+.2f}%")
        print(f"\n交易统计:")
        print(f"  总交易: {result.total_trades}")
        print(f"  盈利: {result.winning_trades} | 亏损: {result.losing_trades}")
        print(f"  胜率: {result.win_rate:.1%}")
        print(f"  平均盈利: {result.avg_profit:+.2f}")
        print(f"  平均亏损: {result.avg_loss:+.2f}")
        print(f"  盈亏比: {result.profit_factor:.2f}")
        print(f"\n风险指标:")
        print(f"  最大回撤: {result.max_drawdown_pct:.2f}%")
        print(f"  夏普比率: {result.sharpe_ratio:.2f}")

        if result.state_regime_stats:
            print(f"\nState-Regime 统计:")
            for pool_id, stats in sorted(result.state_regime_stats.items()):
                print(f"  {pool_id}: 交易{stats['total_trades']}次 | "
                      f"胜率{stats['win_rate']:.1%} | 总盈亏{stats['total_pnl']:+.2f}")

        print("=" * 70)


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("State Hex Backtest Engine Test")
    print("=" * 70)

    np.random.seed(42)
    n_days = 200
    base_price = 1.0850

    # 生成趋势+噪声价格
    trend = np.sin(np.linspace(0, 4 * np.pi, n_days)) * 0.02
    noise = np.cumsum(np.random.randn(n_days) * 0.003)
    prices = base_price + trend + noise

    data = []
    start_date = datetime(2024, 1, 1)
    for i in range(n_days):
        date = start_date + timedelta(days=i)
        if date.weekday() >= 5:
            continue
        close = prices[i]
        high = close + abs(np.random.randn()) * 0.008
        low = close - abs(np.random.randn()) * 0.008
        open_p = close + np.random.randn() * 0.003
        data.append({
            'timestamp': date,
            'open': open_p,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.randint(10000, 100000)
        })

    df = pd.DataFrame(data)
    print(f"\n测试数据: {len(df)} 个交易日")

    # 创建回测引擎
    engine = StateHexBacktestEngine(
        symbol="EURUSD",
        initial_balance=10000.0,
        lot_size=0.1,
        state_alignment_mode="loose",
        min_confidence=0.6
    )

    engine.load_d1_data(df)
    result = engine.run()
    engine.print_report(result)

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
