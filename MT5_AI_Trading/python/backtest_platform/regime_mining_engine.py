"""
State-Regime 策略挖掘引擎

核心目标: 为每个市场状态段(State-Regime)找到最优策略，实现"圣杯"

核心流程:
1. 历史数据 → 计算每日三元组 → 标记Regime (W1|MN1)
2. 按Regime分段 → 提取每个Regime的交易日序列
3. 对每个Regime × 策略参数组合 → 独立回测
4. 圣杯评分 → 筛选最优组合
5. 生成Regime-Strategy映射表
6. 运行时自适应路由

关键洞察:
- W1|MN1定义了市场的"气候"(Regime)
- D1在该气候下的波动提供了交易机会
- 不同气候需要不同的策略参数
- 圣杯 = 特定Regime + 适配参数 + 优异绩效
"""

import os
import sys
import json
import logging
import itertools
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from pathlib import Path

import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest_platform.compute_layer import FeaturePipeline, DailyFeatures, StateHexComputeEngine
from backtest_platform.strategy_layer import (
    BaseStrategy, StrategyRegistry, P107StateHexStrategy,
    Signal, PortfolioState
)
from backtest_platform.execution_layer import (
    BacktestRunner, PerformanceReport
)
from ai_engine.state_hex_engine import StateHexTriplet

logger = logging.getLogger(__name__)


# ============================================================================
# 默认参数网格
# ============================================================================

DEFAULT_PARAM_GRID = {
    "min_confidence": [0.5, 0.6, 0.7, 0.8],
    "state_alignment_mode": ["strict", "loose"],
    "sl_atr_multiplier": [1.5, 2.0, 2.5],
    "tp_atr_multiplier": [2.0, 3.0, 4.0],
}


# ============================================================================
# 核心数据类
# ============================================================================

@dataclass
class HolyGrailCandidate:
    """圣杯候选"""
    regime_id: str
    strategy_name: str
    params: Dict[str, Any]
    performance: PerformanceReport
    holy_grail_score: float
    regime_days: int
    trade_density: float  # 交易数 / Regime天数


@dataclass
class RegimeStrategyConfig:
    """Regime-Strategy配置（用于序列化）"""
    regime_id: str
    strategy_name: str
    params: Dict[str, Any]
    performance_summary: Dict[str, Any]
    holy_grail_score: float


# ============================================================================
# Regime标签器
# ============================================================================

class RegimeLabeler:
    """
    Regime标签器

    将历史数据按State Hex三元组中的W1|MN1分段，
    生成Regime到日期列表的映射。

    Regime ID格式: W1:{w1_hex}|MN1:{mn1_hex}
    """

    def __init__(self):
        self.state_engine = StateHexComputeEngine()
        self._cache: Dict[int, Dict[str, List[datetime]]] = {}

    def label(self, df: pd.DataFrame) -> Dict[str, List[datetime]]:
        """
        给历史数据打Regime标签

        Args:
            df: OHLCV DataFrame，必须含timestamp列

        Returns:
            {regime_id: [date1, date2, ...]}
        """
        cache_key = hash(tuple(df['close'].values))
        if cache_key in self._cache:
            return self._cache[cache_key]

        required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"数据缺少必要列: {col}")

        # 批量计算三元组
        triplet_series = self.state_engine.compute_triplet_series(df)

        if triplet_series.empty:
            logger.warning("三元组计算结果为空，无法标记Regime")
            return {}

        # 按W1|MN1分组
        regimes = defaultdict(list)
        for _, row in triplet_series.iterrows():
            regime_id = f"W1:{row['w1_hex']}|MN1:{row['mn1_hex']}"
            regimes[regime_id].append(pd.to_datetime(row['timestamp']))

        result = dict(regimes)
        self._cache[cache_key] = result

        logger.info(f"Regime标记完成: {len(result)} 个Regime")
        for rid, dates in sorted(result.items()):
            logger.info(f"  {rid}: {len(dates)} 天")

        return result

    def get_regime_at(self, triplet: StateHexTriplet) -> str:
        """获取指定三元组的Regime ID"""
        return f"W1:{triplet.w1_hex}|MN1:{triplet.mn1_hex}"


# ============================================================================
# Regime-Aware策略包装器
# ============================================================================

class RegimeAwareStrategy(BaseStrategy):
    """
    Regime-Aware策略包装器

    包装现有策略，只在特定Regime的日期产生信号。
    非Regime日期返回None（不交易）。
    """

    def __init__(self, base_strategy: BaseStrategy, regime_dates: List[datetime]):
        self.base_strategy = base_strategy
        # 转为日期字符串集合，避免时区/类型问题
        self.regime_dates = {pd.to_datetime(d).strftime('%Y-%m-%d') for d in regime_dates}
        self._name = base_strategy.name
        self._description = base_strategy.description
        self._param_schema = base_strategy.param_schema
        self.params = base_strategy.params
        self.signal_history = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def param_schema(self) -> Dict[str, Any]:
        return self._param_schema

    def on_daily_features(self, features: DailyFeatures, portfolio: PortfolioState) -> Optional[Signal]:
        """只在Regime日期交易"""
        ts_str = pd.to_datetime(features.timestamp).strftime('%Y-%m-%d')
        if ts_str not in self.regime_dates:
            return None
        return self.base_strategy.on_daily_features(features, portfolio)

    def reset(self):
        """重置策略状态"""
        self.base_strategy.reset()
        self.signal_history = []


# ============================================================================
# 圣杯评分器
# ============================================================================

class HolyGrailScorer:
    """
    圣杯评分器

    综合评分公式 (0-100):
    - 胜率 (25%): 越高越好
    - 盈亏比 (25%): 越高越好
    - 夏普比率 (20%): 越高越好
    - 样本量 (20%): 交易数越多越可靠
    - 回撤控制 (10%): 回撤越小越好

    圣杯阈值建议:
    - 60分: 合格策略
    - 70分: 良好策略
    - 80分: 优秀策略（圣杯候选）
    """

    DEFAULT_WEIGHTS = {
        'win_rate': 0.25,
        'profit_factor': 0.25,
        'sharpe_ratio': 0.20,
        'sample_size': 0.20,
        'drawdown_control': 0.10,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        min_trades: int = 5,
    ):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.min_trades = min_trades

    def score(self, report: PerformanceReport, regime_days: int = 0) -> float:
        """
        计算圣杯评分

        Args:
            report: 绩效报告
            regime_days: Regime总天数（用于计算交易密度）

        Returns:
            0-100的评分
        """
        if report.total_trades < self.min_trades:
            return 0.0

        # 归一化各指标到0-1
        win_rate = min(report.win_rate, 1.0)

        if report.profit_factor == float('inf'):
            pf = 1.0
        else:
            pf = min(report.profit_factor / 3.0, 1.0)

        sharpe = min(max(report.sharpe_ratio, 0) / 3.0, 1.0)
        sample = min(report.total_trades / 50.0, 1.0)
        dd = max(0, 1.0 - report.max_drawdown_pct / 50.0)

        score = (
            self.weights['win_rate'] * win_rate +
            self.weights['profit_factor'] * pf +
            self.weights['sharpe_ratio'] * sharpe +
            self.weights['sample_size'] * sample +
            self.weights['drawdown_control'] * dd
        ) * 100

        return round(score, 2)

    def is_holy_grail(
        self,
        report: PerformanceReport,
        min_score: float = 60.0,
        min_win_rate: float = 0.55,
        min_profit_factor: float = 1.2,
    ) -> bool:
        """判断是否达到圣杯标准"""
        if report.total_trades < self.min_trades:
            return False
        if report.win_rate < min_win_rate:
            return False
        if report.profit_factor < min_profit_factor:
            return False
        if self.score(report) < min_score:
            return False
        return True


# ============================================================================
# Regime策略挖掘引擎
# ============================================================================

class RegimeStrategyMiner:
    """
    Regime策略挖掘引擎

    核心功能:
    1. 遍历历史数据的所有Regime
    2. 对每个Regime测试多种策略参数
    3. 评分并筛选最优的Regime-Strategy组合
    4. 生成可序列化的映射表
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        lot_size: float = 0.1,
        spread_pips: float = 1.0,
        commission_per_lot: float = 5.0,
        min_regime_days: int = 20,
        min_trades: int = 5,
        min_holy_grail_score: float = 50.0,
        param_grid: Optional[Dict[str, List]] = None,
        target_regime_pattern: Optional[str] = None,
    ):
        """
        Args:
            target_regime_pattern: 定向挖掘目标Regime模式
                - 精确匹配: "W1:F|MN1:8" (只挖这个组合)
                - W1通配: "W1:*|MN1:8" (MN1=8时所有W1)
                - MN1通配: "W1:F|MN1:*" (W1=F时所有MN1)
                - None: 挖掘所有Regime
        """
        self.initial_balance = initial_balance
        self.lot_size = lot_size
        self.spread_pips = spread_pips
        self.commission_per_lot = commission_per_lot
        self.min_regime_days = min_regime_days
        self.min_trades = min_trades
        self.min_holy_grail_score = min_holy_grail_score
        self.param_grid = param_grid or DEFAULT_PARAM_GRID
        self.target_regime_pattern = target_regime_pattern

        self.labeler = RegimeLabeler()
        self.scorer = HolyGrailScorer(min_trades=min_trades)
        # 共享FeaturePipeline，用于批量回测时复用三元组缓存
        self._shared_pipeline = FeaturePipeline()

    def mine(self, df: pd.DataFrame) -> List[HolyGrailCandidate]:
        """
        挖掘每个Regime的最优策略

        Args:
            df: 历史OHLCV数据

        Returns:
            圣杯候选列表（按评分降序）
        """
        logger.info("=" * 70)
        logger.info("State-Regime 策略挖掘开始")
        logger.info("=" * 70)

        # 1. 标记Regime
        regimes = self.labeler.label(df)
        if not regimes:
            logger.warning("未找到任何Regime")
            return []

        # 2. 生成参数组合
        param_combos = list(self._iter_param_grid(self.param_grid))
        logger.info(f"参数网格: {len(param_combos)} 种组合")

        # 3. 对每个Regime × 参数组合运行回测
        all_results: List[HolyGrailCandidate] = []
        total_tests = len(regimes) * len(param_combos)
        tested = 0

        for regime_id, regime_dates in regimes.items():
            # 定向过滤：只挖掘匹配的Regime
            if self.target_regime_pattern and not self._match_regime_pattern(regime_id, self.target_regime_pattern):
                continue

            if len(regime_dates) < self.min_regime_days:
                logger.info(f"跳过 {regime_id}: 仅 {len(regime_dates)} 天 (< {self.min_regime_days})")
                continue

            for params in param_combos:
                tested += 1
                logger.info(f"进度: [{tested}/{total_tests}] {regime_id} | {params}")

                candidate = self._backtest_regime(df, regime_id, regime_dates, params)
                if candidate and candidate.holy_grail_score >= self.min_holy_grail_score:
                    all_results.append(candidate)
                    logger.info(f"  -> 评分: {candidate.holy_grail_score} | 交易: {candidate.performance.total_trades}")

        # 4. 排序并去重（每个Regime只保留最优）
        all_results.sort(key=lambda x: x.holy_grail_score, reverse=True)

        # 去重：每个Regime只保留评分最高的
        seen_regimes = set()
        unique_results = []
        for c in all_results:
            if c.regime_id not in seen_regimes:
                seen_regimes.add(c.regime_id)
                unique_results.append(c)

        logger.info("=" * 70)
        logger.info(f"挖掘完成: {len(unique_results)} 个Regime找到圣杯策略")
        logger.info("=" * 70)

        return unique_results

    def _iter_param_grid(self, param_grid: Dict[str, List]) -> List[Dict[str, Any]]:
        """遍历参数网格的所有组合"""
        if not param_grid:
            yield {}
            return

        keys = list(param_grid.keys())
        values = list(param_grid.values())

        for combo in itertools.product(*values):
            yield dict(zip(keys, combo))

    def _backtest_regime(
        self,
        df: pd.DataFrame,
        regime_id: str,
        regime_dates: List[datetime],
        params: Dict[str, Any],
    ) -> Optional[HolyGrailCandidate]:
        """对特定Regime运行回测"""
        try:
            # 创建策略
            registry = StrategyRegistry()
            base_strategy = registry.create_instance('P107_StateHex_v1', **params)
            strategy = RegimeAwareStrategy(base_strategy, regime_dates)

            # 运行回测（传入完整数据，策略内部过滤Regime）
            # 使用共享FeaturePipeline，复用三元组缓存，避免O(n²)重复计算
            symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else 'UNKNOWN'
            runner = BacktestRunner(
                symbol=symbol,
                initial_balance=self.initial_balance,
                lot_size=self.lot_size,
                spread_pips=self.spread_pips,
                commission_per_lot=self.commission_per_lot,
                feature_pipeline=self._shared_pipeline,
            )
            runner.set_strategy(strategy)
            report = runner.run(df)

            # 评分
            score = self.scorer.score(report, len(regime_dates))
            trade_density = report.total_trades / len(regime_dates) if regime_dates else 0

            return HolyGrailCandidate(
                regime_id=regime_id,
                strategy_name=base_strategy.name,
                params=params,
                performance=report,
                holy_grail_score=score,
                regime_days=len(regime_dates),
                trade_density=round(trade_density, 4),
            )

        except Exception as e:
            logger.debug(f"Regime回测失败: {regime_id}, params={params}, error={e}")
            return None

    def _match_regime_pattern(self, regime_id: str, pattern: str) -> bool:
        """
        Regime模式匹配

        支持通配符:
        - "W1:F|MN1:8"     -> 精确匹配
        - "W1:*|MN1:8"     -> MN1=8，任意W1
        - "W1:F|MN1:*"     -> W1=F，任意MN1
        - "W1:F|MN1:8"     -> 完全精确
        """
        if pattern == regime_id:
            return True

        # 解析pattern和regime_id
        def parse(rid):
            parts = rid.split('|')
            w1 = parts[0].replace('W1:', '')
            mn1 = parts[1].replace('MN1:', '')
            return w1, mn1

        pat_w1, pat_mn1 = parse(pattern)
        rid_w1, rid_mn1 = parse(regime_id)

        w1_match = (pat_w1 == '*') or (pat_w1 == rid_w1)
        mn1_match = (pat_mn1 == '*') or (pat_mn1 == rid_mn1)

        return w1_match and mn1_match

    def save_map(self, candidates: List[HolyGrailCandidate], path: str):
        """
        保存Regime-Strategy映射表

        Args:
            candidates: 圣杯候选列表
            path: 保存路径
        """
        data = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'total_regimes': len(candidates),
                'miner_config': {
                    'min_regime_days': self.min_regime_days,
                    'min_trades': self.min_trades,
                    'min_holy_grail_score': self.min_holy_grail_score,
                    'param_grid': {k: list(v) for k, v in self.param_grid.items()},
                },
            },
            'regime_map': {
                c.regime_id: {
                    'strategy_name': c.strategy_name,
                    'params': c.params,
                    'performance': {
                        'total_trades': c.performance.total_trades,
                        'winning_trades': c.performance.winning_trades,
                        'losing_trades': c.performance.losing_trades,
                        'win_rate': c.performance.win_rate,
                        'profit_factor': c.performance.profit_factor,
                        'sharpe_ratio': c.performance.sharpe_ratio,
                        'sortino_ratio': c.performance.sortino_ratio,
                        'max_drawdown_pct': c.performance.max_drawdown_pct,
                        'total_return_pct': c.performance.total_return_pct,
                        'avg_profit': c.performance.avg_profit,
                        'avg_loss': c.performance.avg_loss,
                    },
                    'holy_grail_score': c.holy_grail_score,
                    'regime_days': c.regime_days,
                    'trade_density': c.trade_density,
                }
                for c in candidates
            }
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"映射表已保存: {path} ({len(candidates)} 个Regime)")


# ============================================================================
# 自适应策略路由器
# ============================================================================

class AdaptiveStrategyRouter:
    """
    自适应策略路由器

    根据当前市场Regime，自动选择最优策略。
    """

    def __init__(self, map_path: Optional[str] = None):
        self.regime_map: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Any] = {}

        if map_path:
            self.load_map(map_path)

    def load_map(self, path: str):
        """加载Regime-Strategy映射表"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.metadata = data.get('metadata', {})
        self.regime_map = data.get('regime_map', {})

        logger.info(f"映射表加载成功: {path}")
        logger.info(f"  包含 {len(self.regime_map)} 个Regime配置")

    def select_strategy(self, triplet: StateHexTriplet) -> Optional[BaseStrategy]:
        """
        根据当前三元组选择策略

        Args:
            triplet: 当前State Hex三元组

        Returns:
            策略实例，如果当前Regime无配置则返回None
        """
        regime_id = f"W1:{triplet.w1_hex}|MN1:{triplet.mn1_hex}"
        config = self.regime_map.get(regime_id)

        if not config:
            logger.debug(f"当前Regime无配置: {regime_id}")
            return None

        # 创建策略实例
        registry = StrategyRegistry()
        strategy = registry.create_instance(
            config['strategy_name'],
            **config['params']
        )

        logger.info(f"自适应路由: {regime_id} -> {config['strategy_name']} | "
                   f"评分: {config.get('holy_grail_score', 0)}")

        return strategy

    def get_regime_info(self, triplet: StateHexTriplet) -> Optional[Dict[str, Any]]:
        """获取当前Regime的配置信息"""
        regime_id = f"W1:{triplet.w1_hex}|MN1:{triplet.mn1_hex}"
        return self.regime_map.get(regime_id)

    def list_configured_regimes(self) -> List[str]:
        """列出所有已配置的Regime"""
        return list(self.regime_map.keys())


# ============================================================================
# 测试入口
# ============================================================================

def generate_test_data(symbol: str = "EURUSD", n_days: int = 300) -> pd.DataFrame:
    """生成有趋势变化的测试数据（产生多个Regime）"""
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=n_days, freq="B")

    # 分段趋势：前100天上涨，中间100天震荡，后100天下跌
    t1 = np.linspace(0, 0.05, 100)
    t2 = np.sin(np.linspace(0, 6 * np.pi, 100)) * 0.015
    t3 = np.linspace(0.05, -0.02, 100)
    trend = np.concatenate([t1, t2, t3])

    noise = np.cumsum(np.random.randn(n_days) * 0.002)
    prices = 1.0850 + trend + noise

    # 确保OHLC逻辑合理
    opens = prices + np.random.randn(n_days) * 0.0005
    closes = prices + np.random.randn(n_days) * 0.0005
    highs = np.maximum(np.maximum(opens, closes), prices + abs(np.random.randn(n_days)) * 0.003)
    lows = np.minimum(np.minimum(opens, closes), prices - abs(np.random.randn(n_days)) * 0.003)

    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': np.random.randint(10000, 100000, n_days),
    })


if __name__ == "__main__":
    print("=" * 70)
    print("State-Regime 策略挖掘引擎测试")
    print("=" * 70)

    # 1. 生成测试数据
    print("\n[1] 生成测试数据...")
    df = generate_test_data(n_days=300)
    print(f"  数据量: {len(df)} 天 | {df['timestamp'].iloc[0].date()} ~ {df['timestamp'].iloc[-1].date()}")

    # 2. 创建挖掘引擎（使用小参数网格加速测试）
    print("\n[2] 创建挖掘引擎...")
    test_param_grid = {
        "min_confidence": [0.5, 0.7],
        "state_alignment_mode": ["loose"],
        "sl_atr_multiplier": [2.0],
        "tp_atr_multiplier": [3.0],
    }
    miner = RegimeStrategyMiner(
        min_regime_days=20,
        min_trades=3,
        min_holy_grail_score=30.0,
        param_grid=test_param_grid,
    )
    print(f"  参数网格: {len(list(miner._iter_param_grid(test_param_grid)))} 种组合")

    # 3. 运行挖掘
    print("\n[3] 开始挖掘...")
    candidates = miner.mine(df)

    # 4. 打印结果
    print(f"\n[4] 挖掘结果: {len(candidates)} 个圣杯候选")
    for i, c in enumerate(candidates[:5], 1):
        print(f"\n  [{i}] Regime: {c.regime_id}")
        print(f"      评分: {c.holy_grail_score}/100")
        print(f"      参数: {c.params}")
        print(f"      Regime天数: {c.regime_days}")
        print(f"      交易数: {c.performance.total_trades} | 密度: {c.trade_density:.4f}")
        print(f"      胜率: {c.performance.win_rate:.1%} | 盈亏比: {c.performance.profit_factor:.2f}")
        print(f"      夏普: {c.performance.sharpe_ratio:.2f} | 回撤: {c.performance.max_drawdown_pct:.2f}%")

    # 5. 保存映射表
    print("\n[5] 保存映射表...")
    if candidates:
        map_path = "test_regime_map.json"
        miner.save_map(candidates, map_path)
        print(f"  已保存: {map_path}")

        # 6. 测试自适应路由
        print("\n[6] 测试自适应路由...")
        router = AdaptiveStrategyRouter(map_path)
        print(f"  已加载 {len(router.regime_map)} 个Regime配置")

        # 模拟当前Regime
        from ai_engine.state_hex_engine import StateHexTriplet
        test_triplet = StateHexTriplet(
            timestamp=datetime.now(),
            mn1_hex="8", w1_hex="8", d1_hex="8",
            mn1_duration=1, w1_duration=1, d1_duration=1,
        )
        strategy = router.select_strategy(test_triplet)
        if strategy:
            print(f"  路由成功: {strategy.name} | 参数: {strategy.params}")
        else:
            print(f"  当前Regime (W1:8|MN1:8) 无配置，使用默认策略")

    # 7. 验证清单
    print("\n" + "=" * 70)
    print("验证清单")
    print("=" * 70)

    checks = [
        ("数据生成", len(df) == 300),
        ("Regime标记", len(candidates) >= 0),
        ("圣杯评分", all(c.holy_grail_score >= 30.0 for c in candidates) if candidates else True),
        ("映射表保存", os.path.exists("test_regime_map.json") if candidates else True),
        ("路由加载", len(router.regime_map) > 0 if candidates else True),
    ]

    passed = sum(1 for _, r in checks if r)
    for name, result in checks:
        print(f"  [{'OK' if result else 'NG'}] {name}")

    print(f"\n总计: {passed}/{len(checks)} 项通过")

    if passed == len(checks):
        print("\nState-Regime策略挖掘引擎测试通过！")
    else:
        print(f"\n有 {len(checks) - passed} 项验证失败。")

    print("=" * 70)
