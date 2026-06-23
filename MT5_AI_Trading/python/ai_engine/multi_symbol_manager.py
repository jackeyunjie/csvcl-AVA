"""
多品种策略管理器
功能：
1. 管理多个交易品种的独立策略实例
2. 聚合各品种信号，进行全局风控
3. 支持品种权重配置
4. 信号去重与优先级排序
5. 与SignalScorer集成进行信号质量评估
"""

import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from ai_engine.trading_strategy import TradingStrategy, TradingSignal, RiskParameters

logger = logging.getLogger(__name__)


@dataclass
class SymbolConfig:
    """品种配置"""
    symbol: str
    timeframe: str = "H1"
    weight: float = 1.0           # 品种权重（影响仓位分配）
    enabled: bool = True          # 是否启用
    min_confidence: float = 0.6   # 该品种最小信心度
    max_positions: int = 1        # 该品种最大持仓数
    strategy_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedSignal:
    """聚合后的信号"""
    signal: TradingSignal
    symbol_config: SymbolConfig
    score: float = 0.0            # 综合评分
    rank: int = 0                 # 优先级排名
    quality_score: float = 0.0    # SignalScorer提供的质量评分


def load_symbol_configs_from_dict(config_list: List[Dict[str, Any]]) -> List[SymbolConfig]:
    """
    从配置字典列表加载品种配置

    Args:
        config_list: YAML配置中的symbols列表

    Returns:
        SymbolConfig列表
    """
    configs = []
    for item in config_list:
        cfg = SymbolConfig(
            symbol=item["symbol"],
            timeframe=item.get("timeframe", "H1"),
            weight=float(item.get("weight", 1.0)),
            enabled=item.get("enabled", True),
            min_confidence=float(item.get("min_confidence", 0.6)),
            max_positions=int(item.get("max_positions", 1)),
            strategy_params=item.get("strategy_params", {})
        )
        configs.append(cfg)
    return configs


class MultiSymbolStrategyManager:
    """
    多品种策略管理器

    管理多个品种的独立策略，提供：
    - 按品种独立计算指标和信号
    - 全局持仓限制检查
    - 信号评分与排序
    - 品种权重应用
    """

    def __init__(
        self,
        symbol_configs: List[SymbolConfig],
        risk_params: Optional[RiskParameters] = None,
        global_max_positions: int = 5,
        signal_scorer=None
    ):
        self.symbol_configs: Dict[str, SymbolConfig] = {
            cfg.symbol: cfg for cfg in symbol_configs
        }
        self.risk_params = risk_params or RiskParameters()
        self.global_max_positions = global_max_positions
        self.signal_scorer = signal_scorer  # SignalScorer实例（可选）

        # 每个品种独立的策略实例
        self.strategies: Dict[str, TradingStrategy] = {}
        self._init_strategies()

        # 品种价格历史（独立存储）
        self.price_history: Dict[str, List[Dict]] = defaultdict(list)
        self._history_lock = threading.Lock()

        # 信号历史（用于评分）
        self.signal_history: Dict[str, List[TradingSignal]] = defaultdict(list)

        logger.info(f"MultiSymbolStrategyManager初始化完成 | 品种数: {len(symbol_configs)}")

    def _init_strategies(self):
        """为每个启用的品种初始化策略实例"""
        for symbol, cfg in self.symbol_configs.items():
            if not cfg.enabled:
                continue
            self.strategies[symbol] = TradingStrategy(
                risk_params=self.risk_params,
                min_confidence=cfg.min_confidence
            )
            logger.info(f"策略初始化: {symbol} | 权重: {cfg.weight} | 周期: {cfg.timeframe}")

    def update_price(self, symbol: str, tick_data: Dict[str, Any]):
        """
        更新品种价格数据

        Args:
            symbol: 品种名
            tick_data: 包含 timestamp, bid, ask, volume 的字典
        """
        if symbol not in self.symbol_configs or not self.symbol_configs[symbol].enabled:
            return

        with self._history_lock:
            self.price_history[symbol].append(tick_data)
            # 保持最多500条
            if len(self.price_history[symbol]) > 500:
                self.price_history[symbol] = self.price_history[symbol][-500:]

    def generate_all_signals(
        self,
        account_balance: float,
        current_positions: Dict[str, int]
    ) -> List[AggregatedSignal]:
        """
        为所有品种生成信号并聚合评分

        Args:
            account_balance: 账户余额
            current_positions: 各品种当前持仓数 {symbol: count}

        Returns:
            按评分排序的聚合信号列表
        """
        import pandas as pd

        all_signals: List[AggregatedSignal] = []

        for symbol, strategy in self.strategies.items():
            cfg = self.symbol_configs[symbol]

            # 检查该品种持仓限制
            pos_count = current_positions.get(symbol, 0)
            if pos_count >= cfg.max_positions:
                continue

            # 获取该品种价格历史
            with self._history_lock:
                history = list(self.price_history[symbol])

            if len(history) < 50:
                continue

            # 转换为DataFrame
            df = pd.DataFrame(history)
            if 'mid' not in df.columns and 'bid' in df.columns and 'ask' in df.columns:
                df['mid'] = (df['bid'] + df['ask']) / 2

            # 确保必要的OHLCV列存在
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    if col == 'close' and 'mid' in df.columns:
                        df['close'] = df['mid']
                    elif col in ['open', 'high', 'low'] and 'mid' in df.columns:
                        df[col] = df['mid']
                    elif col == 'volume':
                        df[col] = 0

            current_price = df['close'].iloc[-1] if 'close' in df.columns else 0

            # 生成信号
            signal = strategy.generate_signal(
                df=df,
                symbol=symbol,
                current_price=current_price,
                account_balance=account_balance,
                existing_positions=pos_count
            )

            if signal:
                # 应用品种权重调整仓位
                signal.position_size = round(signal.position_size * cfg.weight, 2)

                all_signals.append(AggregatedSignal(
                    signal=signal,
                    symbol_config=cfg,
                    score=0.0
                ))

                # 记录信号历史
                self.signal_history[symbol].append(signal)

        # 评分与排序
        scored_signals = self._score_signals(all_signals)

        return scored_signals

    def _score_signals(self, signals: List[AggregatedSignal]) -> List[AggregatedSignal]:
        """
        对信号进行综合评分

        评分维度：
        1. 信号信心度 (35%)
        2. 品种权重 (15%)
        3. 历史胜率加成 (15%)
        4. 风险回报比 (15%)
        5. SignalScorer质量评分 (20%) - 如有
        """
        for agg in signals:
            sig = agg.signal
            cfg = agg.symbol_config

            # 1. 信心度 (0-1)
            confidence_score = sig.confidence

            # 2. 品种权重 (0-1，已归一化)
            weight_score = min(cfg.weight, 1.0)

            # 3. 历史胜率加成
            win_rate_score = self._calculate_win_rate_score(sig.symbol)

            # 4. 风险回报比
            risk = abs(sig.entry_price - sig.stop_loss) if sig.stop_loss else 1
            reward = abs(sig.take_profit - sig.entry_price) if sig.take_profit else 0
            rr_ratio = reward / risk if risk > 0 else 0
            rr_score = min(rr_ratio / 3.0, 1.0)  # 3:1 为满分

            # 5. SignalScorer质量评分（如果可用）
            quality_score = 0.5  # 默认值
            if self.signal_scorer:
                try:
                    quality_score = self.signal_scorer.get_signal_quality_score(
                        symbol=sig.symbol,
                        signal_type=sig.signal_type.value,
                        confidence=sig.confidence
                    )
                    agg.quality_score = quality_score
                except Exception as e:
                    logger.debug(f"获取信号质量评分失败: {e}")

            # 综合评分
            agg.score = (
                confidence_score * 0.35 +
                weight_score * 0.15 +
                win_rate_score * 0.15 +
                rr_score * 0.15 +
                quality_score * 0.20
            )

        # 按评分降序排列
        signals.sort(key=lambda x: x.score, reverse=True)

        # 设置排名
        for i, agg in enumerate(signals):
            agg.rank = i + 1

        return signals

    def _calculate_win_rate_score(self, symbol: str) -> float:
        """
        计算品种的历史胜率评分

        Args:
            symbol: 品种名

        Returns:
            0-1 的评分
        """
        history = self.signal_history.get(symbol, [])
        if len(history) < 5:
            return 0.5  # 数据不足，给中等评分

        # 简化：基于信号信心度和历史信号数量估算
        # 实际应追踪每个信号的后续盈亏
        recent = history[-20:]
        avg_confidence = sum(s.confidence for s in recent) / len(recent)

        # 信号越频繁且信心度越高，评分越高
        frequency_score = min(len(history) / 50, 1.0)
        return (avg_confidence * 0.6 + frequency_score * 0.4)

    def check_global_position_limit(
        self,
        current_positions: Dict[str, int],
        new_signals: List[AggregatedSignal]
    ) -> List[AggregatedSignal]:
        """
        检查全局持仓限制，过滤超限信号

        Args:
            current_positions: 当前各品种持仓数
            new_signals: 待执行信号列表（已排序）

        Returns:
            符合全局限制的信号列表
        """
        total_positions = sum(current_positions.values())
        available_slots = self.global_max_positions - total_positions

        if available_slots <= 0:
            logger.info(f"全局持仓已满 ({total_positions}/{self.global_max_positions})")
            return []

        filtered = new_signals[:available_slots]
        logger.info(f"全局持仓检查: 当前{total_positions} | 可用{available_slots} | 通过{len(filtered)}个信号")

        return filtered

    def get_symbol_status(self, symbol: str) -> Dict[str, Any]:
        """获取品种状态摘要"""
        cfg = self.symbol_configs.get(symbol)
        if not cfg:
            return {"error": "品种未配置"}

        history = self.price_history.get(symbol, [])
        signals = self.signal_history.get(symbol, [])

        return {
            "symbol": symbol,
            "enabled": cfg.enabled,
            "weight": cfg.weight,
            "timeframe": cfg.timeframe,
            "data_points": len(history),
            "signal_count": len(signals),
            "last_signal": signals[-1].signal_type.value if signals else None
        }

    def get_all_status(self) -> Dict[str, Any]:
        """获取所有品种状态"""
        return {
            symbol: self.get_symbol_status(symbol)
            for symbol in self.symbol_configs
        }
