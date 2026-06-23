"""
State Hex 交易策略引擎
基于 P107 State Hex 编码规则 与 P106 资金流应用框架

核心原则:
- price-first 主裁决
- state-first 状态主线
- 最小分析单元: 三元组(MN1, W1, D1)
- state_hex 是体检码, 不是线性分数, 不是买卖许可
- 资金流、换手率、筹码峰只做二级确认, 不替代价格状态

主线顺序:
1. D1/W1/MN1 状态对齐
2. 策略条件接近（价格行为验证）
3. 成交活跃度确认（预留, 需P106资金流）
4. 资金流增量证据（预留, 需P106资金流）
5. 筹码峰结构解释（预留, 需P106资金流）
6. 观察提醒或复盘卡片
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, time
from collections import Counter
import logging

try:
    from ai_engine.state_hex_encoding import StateHexEncoder
    from ai_engine.state_hex_engine import StateHexEngine, StateHexTriplet
except ImportError:
    from state_hex_encoding import StateHexEncoder
    from state_hex_engine import StateHexEngine, StateHexTriplet

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"


@dataclass
class RiskParameters:
    """风险参数"""
    max_risk_per_trade: float = 0.02
    max_risk_per_day: float = 0.06
    max_drawdown: float = 0.10
    max_positions: int = 5
    min_risk_reward: float = 1.5
    max_lot_size: float = 0.1


@dataclass
class TradingSignal:
    """交易信号（兼容旧接口，增加状态字段）"""
    signal_type: SignalType
    symbol: str
    confidence: float
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    position_size: float
    reasoning: str
    timestamp: str
    # State Hex 扩展字段
    state_tags: List[str] = field(default_factory=list)
    triplet: Optional[StateHexTriplet] = None
    state_alignment: str = ""


class D1BarAggregator:
    """
    Tick数据聚合成D1 Bar

    用于实时运行时从tick流构建D1数据。
    注意：tick_volume不是真实成交量，仅作流动性参考。
    """

    def __init__(self):
        self.current_bar: Optional[Dict] = None
        self.completed_bars: List[Dict] = []

    def add_tick(self, timestamp: datetime, price: float, volume: float = 0) -> Optional[Dict]:
        """
        添加tick数据

        Returns:
            如果完成了上一根D1 bar，返回该bar数据
        """
        tick_date = timestamp.date()

        if self.current_bar is None or self.current_bar['date'] != tick_date:
            completed = self.current_bar
            self.current_bar = {
                'date': tick_date,
                'timestamp': datetime.combine(tick_date, time(0, 0)),
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume
            }
            if completed:
                self.completed_bars.append(completed)
            return completed

        self.current_bar['high'] = max(self.current_bar['high'], price)
        self.current_bar['low'] = min(self.current_bar['low'], price)
        self.current_bar['close'] = price
        self.current_bar['volume'] += volume

        return None

    def get_current_bar(self) -> Optional[Dict]:
        """获取当前正在构建的bar"""
        return self.current_bar

    def get_completed_bars_df(self) -> pd.DataFrame:
        """获取已完成的bars作为DataFrame"""
        if not self.completed_bars:
            return pd.DataFrame()
        return pd.DataFrame(self.completed_bars)


class TradingStrategy:
    """
    State Hex 交易策略引擎

    基于P107规范，以三元组(MN1, W1, D1)为最小分析单元。
    禁止单周期分析，必须观察三周期共振状态。

    禁止:
    - 单独分析日线D1  # verify-exempt: 规则声明
    - 忽略MN1和W1只看D1  # verify-exempt: 规则声明
    - 将不同时间戳的数据混合分析

    必须:
    - 将(MN1, W1, D1)作为最小分析单元
    - 观察三元组随时间的连续演化
    - 关注三周期如何相互传导、转化
    """

    ALIGNMENT_THRESHOLD = 0.6

    def __init__(
        self,
        risk_params: Optional[RiskParameters] = None,
        min_confidence: float = 0.6,
        state_alignment_mode: str = "strict",
        d1_data: Optional[pd.DataFrame] = None
    ):
        self.risk_params = risk_params or RiskParameters()
        self.min_confidence = min_confidence
        self.state_alignment_mode = state_alignment_mode
        self.encoder = StateHexEncoder()
        self.state_engine: Optional[StateHexEngine] = None
        self.d1_aggregator = D1BarAggregator()
        self.signal_history: List[TradingSignal] = []

        if d1_data is not None and len(d1_data) > 0:
            self._init_state_engine(d1_data)

        logger.info(
            f"StateHexTradingStrategy初始化 | 模式: {state_alignment_mode} | "
            f"引擎就绪: {self.state_engine is not None}"
        )

    def _init_state_engine(self, d1_df: pd.DataFrame):
        """用D1历史数据初始化状态引擎"""
        self.state_engine = StateHexEngine()
        self.state_engine.add_d1_dataframe(d1_df)
        self.state_engine.compute_triplets()

        latest = self.state_engine.get_latest_triplet()
        if latest:
            logger.info(
                f"State引擎初始化完成 | 数据: {len(d1_df)}条 | "
                f"最新三元组: MN1={latest.mn1_hex} W1={latest.w1_hex} D1={latest.d1_hex}"
            )
        else:
            logger.warning("State引擎初始化后无三元组数据")

    def load_d1_data(self, d1_df: pd.DataFrame):
        """加载D1历史数据（用于初始化或更新）"""
        self._init_state_engine(d1_df)

    def update_with_tick(self, timestamp: datetime, price: float, volume: float = 0) -> bool:
        """
        用tick更新策略状态

        Returns:
            如果产生了新的D1 bar并更新了state_engine，返回True
        """
        completed = self.d1_aggregator.add_tick(timestamp, price, volume)

        if completed and self.state_engine:
            bar = completed
            self.state_engine.add_d1_bar(
                timestamp=bar['timestamp'],
                open_p=bar['open'],
                high=bar['high'],
                low=bar['low'],
                close=bar['close'],
                volume=bar['volume']
            )
            self.state_engine.compute_triplets()
            return True

        return False

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        current_price: float,
        account_balance: float,
        existing_positions: int = 0
    ) -> Optional[TradingSignal]:
        """
        生成交易信号

        Args:
            df: OHLCV DataFrame（用于价格行为验证，State Hex策略主要使用state_engine）
            symbol: 交易品种
            current_price: 当前价格
            account_balance: 账户余额
            existing_positions: 现有持仓数

        Returns:
            TradingSignal 或 None
        """
        if existing_positions >= self.risk_params.max_positions:
            logger.debug("已达到最大持仓限制")
            return None

        # 确保state_engine已初始化
        if self.state_engine is None or not self.state_engine.triplets:
            if len(df) >= 50:
                required = ['timestamp', 'open', 'high', 'low', 'close']
                if all(c in df.columns for c in required):
                    logger.info("State引擎未初始化，尝试用传入的df初始化")
                    self._init_state_engine(df)

            if self.state_engine is None or not self.state_engine.triplets:
                logger.warning("State引擎未初始化，无法生成信号")
                return None

        # 获取最新三元组 —— 最小分析单元
        triplet = self.state_engine.get_latest_triplet()
        if triplet is None:
            return None

        # 1. 状态门检查（核心：三周期对齐）
        alignment_score, alignment_reason = self._check_state_alignment(triplet)

        if alignment_score < self.ALIGNMENT_THRESHOLD:
            logger.debug(f"状态未对齐: {alignment_reason} | 评分: {alignment_score:.2f}")
            return None

        # 2. 价格行为验证（price-first）
        price_valid, price_reason = self._validate_price_action(df, triplet, current_price)

        # 3. 生成信号
        signal_type, confidence, reasoning, tags = self._analyze_state(
            triplet, current_price, alignment_score, alignment_reason, price_valid, price_reason
        )

        if signal_type == SignalType.HOLD or confidence < self.min_confidence:
            return None

        # 4. 计算止损止盈
        stop_loss, take_profit = self._calculate_levels(
            current_price, symbol, triplet, df
        )

        # 5. 检查风险回报比
        if stop_loss and take_profit:
            risk = abs(current_price - stop_loss)
            reward = abs(take_profit - current_price)
            if risk > 0 and reward / risk < self.risk_params.min_risk_reward:
                logger.info(f"风险回报比不足: {reward/risk:.2f}")
                return None

        # 6. 计算仓位
        position_size = self._calculate_position_size(
            account_balance, current_price, stop_loss
        )

        if position_size > self.risk_params.max_lot_size:
            position_size = self.risk_params.max_lot_size

        signal = TradingSignal(
            signal_type=signal_type,
            symbol=symbol,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=round(position_size, 2),
            reasoning=reasoning,
            timestamp=pd.Timestamp.now().isoformat(),
            state_tags=tags,
            triplet=triplet,
            state_alignment=alignment_reason
        )

        self.signal_history.append(signal)
        logger.info(
            f"信号生成: {signal_type.value} {symbol} | "
            f"信心度: {confidence:.2%} | "
            f"三元组: ({triplet.mn1_hex},{triplet.w1_hex},{triplet.d1_hex}) | "
            f"标签: {', '.join(tags)}"
        )

        return signal

    def _check_state_alignment(self, triplet: StateHexTriplet) -> Tuple[float, str]:
        """
        检查三周期状态对齐（P107核心）

        评分规则:
        - 1.0: 三周期严格同向（多向或空向）
        - 0.8: 高周期支撑低周期
        - 0.0: 状态分化或未对齐
        """
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
                if w1_bull:
                    score += 0.1
                if triplet.w1_duration >= 2:
                    score += 0.05
                if triplet.d1_duration >= 2:
                    score += 0.05
                return min(score, 1.0), f"高周期支撑多头 ({mn1},{w1},{d1})"
            elif mn1_bear and w1_score <= 0 and d1_bear:
                score = 0.8
                if w1_bear:
                    score += 0.1
                if triplet.w1_duration >= 2:
                    score += 0.05
                if triplet.d1_duration >= 2:
                    score += 0.05
                return min(score, 1.0), f"高周期支撑空头 ({mn1},{w1},{d1})"

            return 0.0, f"状态不支持 ({mn1},{w1},{d1})"

    def _validate_price_action(
        self,
        df: pd.DataFrame,
        triplet: StateHexTriplet,
        current_price: float
    ) -> Tuple[bool, str]:
        """价格行为验证（price-first）"""
        if len(df) < 20:
            return False, "数据不足"

        d1_score = self.encoder._from_signed_hex(triplet.d1_hex)
        recent = df['close'].tail(5)
        if recent.iloc[0] == 0:
            return True, "价格行为未验证"

        price_trend = (recent.iloc[-1] - recent.iloc[0]) / recent.iloc[0]

        if d1_score > 0 and price_trend < -0.005:
            return False, f"状态多向但价格趋势下跌{price_trend:.2%}"
        elif d1_score < 0 and price_trend > 0.005:
            return False, f"状态空向但价格趋势上涨{price_trend:.2%}"

        return True, "价格行为与状态一致"

    def _analyze_state(
        self,
        triplet: StateHexTriplet,
        current_price: float,
        alignment_score: float,
        alignment_reason: str,
        price_valid: bool,
        price_reason: str
    ) -> Tuple[SignalType, float, str, List[str]]:
        """
        分析状态生成信号

        遵循P107: 输出观察标签，不输出动作建议。
        策略层将观察条件转换为交易信号类型，但reasoning保持解释性语义。
        """
        mn1 = triplet.mn1_hex
        w1 = triplet.w1_hex
        d1 = triplet.d1_hex

        tags = []

        if alignment_score >= 1.0:
            tags.append("状态同向")
        elif alignment_score >= 0.8:
            tags.append("高周期支撑")

        d1_score, d1_contraction, d1_vol, d1_pos, d1_trend = self.encoder.decode(d1)

        if d1_contraction:
            tags.append("收缩底座")
        else:
            tags.append("非收缩底座")

        if d1_vol:
            tags.append("幅动活跃")
        if d1_pos:
            tags.append("位置触发")
        if d1_trend:
            tags.append("趋势触发")

        if triplet.d1_duration >= 3:
            tags.append(f"D1持续{triplet.d1_duration}天")
        if triplet.w1_duration >= 3:
            tags.append(f"W1持续{triplet.w1_duration}周")

        if not price_valid:
            tags.append("价格分化")

        confidence = alignment_score
        if d1_trend:
            confidence += 0.08
        if d1_pos:
            confidence += 0.07
        if d1_vol:
            confidence += 0.05
        if triplet.d1_duration >= 3:
            confidence += 0.03
        if triplet.w1_duration >= 2:
            confidence += 0.02
        if not price_valid:
            confidence -= 0.15

        confidence = max(0.0, min(confidence, 1.0))

        if d1_score > 0:
            signal_type = SignalType.BUY
            direction_desc = "多头观察环境"
        elif d1_score < 0:
            signal_type = SignalType.SELL
            direction_desc = "空头观察环境"
        else:
            signal_type = SignalType.HOLD
            direction_desc = "方向中性"

        reasoning = (
            f"状态观察 | 三元组({mn1},{w1},{d1}) | "
            f"{alignment_reason} | {direction_desc}"
        )
        if not price_valid:
            reasoning += f" | 注意: {price_reason}"

        return signal_type, confidence, reasoning, tags

    def _calculate_levels(
        self,
        current_price: float,
        symbol: str,
        triplet: StateHexTriplet,
        df: pd.DataFrame
    ) -> Tuple[Optional[float], Optional[float]]:
        """计算止损止盈水平"""
        atr = self._calculate_atr(df)

        if atr is None or atr <= 0:
            atr = current_price * 0.005

        d1_score, _, _, _, d1_trend = self.encoder.decode(triplet.d1_hex)

        sl_multiplier = 2.5 if d1_trend else 2.0
        tp_multiplier = 4.0 if d1_trend else 3.0

        if d1_score > 0:
            stop_loss = current_price - atr * sl_multiplier
            take_profit = current_price + atr * tp_multiplier
        else:
            stop_loss = current_price + atr * sl_multiplier
            take_profit = current_price - atr * tp_multiplier

        return stop_loss, take_profit

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """计算最新ATR"""
        if len(df) < period + 1:
            return None

        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]

        return atr if not pd.isna(atr) else None

    def _calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: Optional[float]
    ) -> float:
        """计算仓位大小"""
        if not stop_loss or stop_loss <= 0 or entry_price <= 0:
            return 0.01

        risk_amount = account_balance * self.risk_params.max_risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit <= 0:
            return 0.01

        position_size = risk_amount / risk_per_unit
        return min(position_size, self.risk_params.max_lot_size)

    def get_signal_summary(self) -> Dict[str, Any]:
        """获取信号统计摘要"""
        if not self.signal_history:
            return {"total_signals": 0}

        signals = self.signal_history
        return {
            "total_signals": len(signals),
            "buy_signals": len([s for s in signals if s.signal_type == SignalType.BUY]),
            "sell_signals": len([s for s in signals if s.signal_type == SignalType.SELL]),
            "avg_confidence": np.mean([s.confidence for s in signals]),
            "last_signal": signals[-1].signal_type.value if signals else None,
            "last_triplet": (
                f"({signals[-1].triplet.mn1_hex},{signals[-1].triplet.w1_hex},{signals[-1].triplet.d1_hex})"
                if signals and signals[-1].triplet else None
            ),
            "state_tag_distribution": self._tag_distribution()
        }

    def _tag_distribution(self) -> Dict[str, int]:
        """状态标签分布统计"""
        all_tags = []
        for s in self.signal_history:
            all_tags.extend(s.state_tags)
        return dict(Counter(all_tags))

    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """获取当前状态摘要"""
        if not self.state_engine:
            return None

        triplet = self.state_engine.get_latest_triplet()
        if not triplet:
            return None

        return {
            "timestamp": triplet.timestamp.isoformat(),
            "mn1_hex": triplet.mn1_hex,
            "w1_hex": triplet.w1_hex,
            "d1_hex": triplet.d1_hex,
            "mn1_duration": triplet.mn1_duration,
            "w1_duration": triplet.w1_duration,
            "d1_duration": triplet.d1_duration,
            "mn1_desc": self.encoder.describe(triplet.mn1_hex),
            "w1_desc": self.encoder.describe(triplet.w1_hex),
            "d1_desc": self.encoder.describe(triplet.d1_hex),
        }


if __name__ == "__main__":
    print("=" * 70)
    print("State Hex Trading Strategy Test")
    print("=" * 70)

    np.random.seed(42)
    n_days = 120
    base_price = 1.0850

    trend = np.sin(np.linspace(0, 3 * np.pi, n_days)) * 0.015
    noise = np.cumsum(np.random.randn(n_days) * 0.003)
    prices = base_price + trend + noise

    data = []
    start_date = datetime(2025, 1, 1)
    for i in range(n_days):
        date = start_date + pd.Timedelta(days=i)
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

    strategy = TradingStrategy(d1_data=df, state_alignment_mode="loose")

    signal = strategy.generate_signal(
        df=df,
        symbol="EURUSD",
        current_price=df['close'].iloc[-1],
        account_balance=10000,
        existing_positions=0
    )

    if signal:
        print(f"\n信号: {signal.signal_type.value}")
        print(f"信心度: {signal.confidence:.2%}")
        print(f"三元组: MN1={signal.triplet.mn1_hex} W1={signal.triplet.w1_hex} D1={signal.triplet.d1_hex}")
        print(f"状态标签: {', '.join(signal.state_tags)}")
        print(f"理由: {signal.reasoning}")
        print(f"入场: {signal.entry_price:.5f}")
        print(f"止损: {signal.stop_loss:.5f}")
        print(f"止盈: {signal.take_profit:.5f}")
        print(f"仓位: {signal.position_size:.2f}")
    else:
        print("\n无信号")

    print("\n当前状态:")
    state = strategy.get_current_state()
    if state:
        print(f"  D1: {state['d1_desc']}")
        print(f"  W1: {state['w1_desc']}")
        print(f"  MN1: {state['mn1_desc']}")

    print("\n信号摘要:")
    summary = strategy.get_signal_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
