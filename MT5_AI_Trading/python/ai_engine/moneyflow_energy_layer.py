"""
P106 资金流能量增量层

定位：二级确认和解释增强，不替代价格状态主裁决。

核心原则:
- 价格状态决定是否进入观察环境
- 策略条件决定是否进入策略适配候选
- 资金流、换手率、筹码峰只做二级确认

主线顺序:
1. D1/W1/MN1 状态对齐
2. 策略条件接近
3. 成交活跃度确认
4. 资金流增量证据  ← 本模块
5. 筹码峰结构解释  ← 本模块
6. 观察提醒或复盘卡片

禁止:
- 资金流替代state_hex做状态门
- 输出动作语义（如"主力买入，应该跟进"）  # verify-exempt: 反面示例
- 将资金流合成单一"买入分"

必须:
- 拆成4个子维度评分
- 只输出研究标签（energy_supportive等）
- 每个标签必须有解释
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class EnergyLabel(Enum):
    """能量研究标签"""
    ENERGY_SUPPORTIVE = "energy_supportive"      # 能量支持
    ENERGY_DIVERGENT = "energy_divergent"        # 能量分化
    ENERGY_OVERHEATED = "energy_overheated"      # 能量过热
    ENERGY_INSUFFICIENT = "energy_insufficient"  # 能量不足
    ENERGY_UNAVAILABLE = "energy_unavailable"    # 能量不可用


class FlowDirection(Enum):
    """资金方向判断"""
    STRONG_INFLOW = "strong_inflow"          # 强流入
    MODERATE_INFLOW = "moderate_inflow"      # 温和流入
    NEUTRAL = "neutral"                      # 中性
    MODERATE_OUTFLOW = "moderate_outflow"    # 温和流出
    STRONG_OUTFLOW = "strong_outflow"        # 强流出


class FlowStructure(Enum):
    """大小单结构判断"""
    LARGE_ABSORPTION = "large_absorption"          # 大单承接
    SMALL_CHASING = "small_chasing"                # 小单追逐
    DISTRIBUTION_PRESSURE = "distribution_pressure" # 派发压力
    BALANCED = "balanced"                          # 结构平衡
    UNCLEAR = "unclear"                            # 结构不明


@dataclass
class MoneyflowSnapshot:
    """单日本地资金流快照"""
    symbol: str
    trade_date: str

    # 订单规模维度
    super_large_net: float = 0.0
    large_net: float = 0.0
    medium_net: float = 0.0
    small_net: float = 0.0
    main_net: float = 0.0          # 主力 = 超大单 + 大单

    # 主动/被动维度
    active_buy: float = 0.0
    active_sell: float = 0.0
    passive_buy: float = 0.0
    passive_sell: float = 0.0
    active_net: float = 0.0

    # 成交与流动性
    amount: float = 0.0            # 成交额
    turnover_rate: float = 0.0     # 换手率

    # 筹码峰
    chip_peak_price: Optional[float] = None
    chip_peak_concentration: Optional[float] = None
    chip_cost_90: Optional[float] = None
    chip_cost_70: Optional[float] = None
    profit_chips_ratio: Optional[float] = None

    # 元数据
    source_name: str = ""


@dataclass
class EnergyAssessment:
    """能量评估结果"""
    symbol: str
    trade_date: str

    # 4个子维度评分 (0-1)
    flow_direction_score: float = 0.0
    flow_persistence_score: float = 0.0
    flow_structure_score: float = 0.0
    chip_structure_score: float = 0.0

    # 综合能量标签
    primary_label: EnergyLabel = EnergyLabel.ENERGY_UNAVAILABLE
    secondary_labels: List[EnergyLabel] = field(default_factory=list)

    # 研究标签（用于页面展示）
    research_tags: List[str] = field(default_factory=list)

    # 解释文本
    explanation: str = ""

    # 原始数据引用
    snapshot: Optional[MoneyflowSnapshot] = None


class MoneyflowEnergyLayer:
    """
    P106 资金流能量增量层

    输入: 黑狼资金流原始数据（或兼容格式）
    输出: EnergyAssessment（4维度评分 + 研究标签 + 解释）

    使用方式:
        layer = MoneyflowEnergyLayer(history_days=20)
        layer.load_history(df)          # 加载历史数据
        assessment = layer.assess(snapshot)  # 评估单日
    """

    def __init__(self, history_days: int = 20):
        self.history_days = history_days
        self.history: deque = deque(maxlen=history_days)
        self.symbol: Optional[str] = None

        logger.info(f"MoneyflowEnergyLayer初始化 | 历史窗口: {history_days}天")

    # ========================================================================
    # 数据加载
    # ========================================================================

    def load_history(self, df: pd.DataFrame):
        """
        批量加载历史资金流数据

        期望字段（黑狼原始字段）:
        - symbol, trade_date
        - main_net_inflow, super_large_net_inflow, large_net_inflow,
          medium_net_inflow, small_net_inflow
        - active_buy_amount, active_sell_amount, passive_buy_amount, passive_sell_amount
        - amount, turnover_rate
        - chip_peak_price, chip_peak_concentration, chip_cost_90, chip_cost_70, profit_chips_ratio
        """
        required_min = ['symbol', 'trade_date']
        for col in required_min:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")

        self.symbol = df['symbol'].iloc[0] if len(df) > 0 else None

        for _, row in df.iterrows():
            snap = self._row_to_snapshot(row)
            self.history.append(snap)

        logger.info(f"历史数据加载完成: {len(self.history)}条 | 品种: {self.symbol}")

    def add_snapshot(self, snapshot: MoneyflowSnapshot):
        """添加单日快照"""
        if self.symbol is None:
            self.symbol = snapshot.symbol
        self.history.append(snapshot)

    @staticmethod
    def _row_to_snapshot(row: pd.Series) -> MoneyflowSnapshot:
        """DataFrame行转快照"""
        return MoneyflowSnapshot(
            symbol=str(row.get('symbol', '')),
            trade_date=str(row.get('trade_date', '')),
            super_large_net=float(row.get('super_large_net_inflow', 0) or 0),
            large_net=float(row.get('large_net_inflow', 0) or 0),
            medium_net=float(row.get('medium_net_inflow', 0) or 0),
            small_net=float(row.get('small_net_inflow', 0) or 0),
            main_net=float(row.get('main_net_inflow', 0) or 0),
            active_buy=float(row.get('active_buy_amount', 0) or 0),
            active_sell=float(row.get('active_sell_amount', 0) or 0),
            passive_buy=float(row.get('passive_buy_amount', 0) or 0),
            passive_sell=float(row.get('passive_sell_amount', 0) or 0),
            amount=float(row.get('amount', 0) or 0),
            turnover_rate=float(row.get('turnover_rate', 0) or 0),
            chip_peak_price=row.get('chip_peak_price'),
            chip_peak_concentration=row.get('chip_peak_concentration'),
            chip_cost_90=row.get('chip_cost_90'),
            chip_cost_70=row.get('chip_cost_70'),
            profit_chips_ratio=row.get('profit_chips_ratio'),
            source_name=str(row.get('source_name', '')),
        )

    # ========================================================================
    # 核心评估
    # ========================================================================

    def assess(self, snapshot: MoneyflowSnapshot) -> EnergyAssessment:
        """
        评估单日能量状态

        返回4个子维度评分 + 研究标签 + 解释
        """
        # 添加当前快照到历史（用于计算持续性）
        self.add_snapshot(snapshot)

        # 计算4个子维度
        direction_score, direction_detail = self._score_flow_direction(snapshot)
        persistence_score, persistence_detail = self._score_flow_persistence()
        structure_score, structure_detail = self._score_flow_structure(snapshot)
        chip_score, chip_detail = self._score_chip_structure(snapshot)

        # 综合标签判定
        primary_label, secondary_labels = self._determine_labels(
            direction_score, persistence_score, structure_score, chip_score,
            direction_detail, structure_detail
        )

        # 研究标签
        research_tags = self._generate_research_tags(
            snapshot, direction_detail, structure_detail, chip_detail
        )

        # 构建解释
        explanation = self._build_explanation(
            snapshot, direction_score, persistence_score,
            structure_score, chip_score,
            direction_detail, structure_detail, chip_detail,
            primary_label
        )

        return EnergyAssessment(
            symbol=snapshot.symbol,
            trade_date=snapshot.trade_date,
            flow_direction_score=direction_score,
            flow_persistence_score=persistence_score,
            flow_structure_score=structure_score,
            chip_structure_score=chip_score,
            primary_label=primary_label,
            secondary_labels=secondary_labels,
            research_tags=research_tags,
            explanation=explanation,
            snapshot=snapshot
        )

    # ========================================================================
    # 子维度1: 资金方向 (flow_direction_score)
    # ========================================================================

    def _score_flow_direction(self, snap: MoneyflowSnapshot) -> Tuple[float, Dict]:
        """
        资金方向评分

        评分依据:
        - 主力净流入方向与强度
        - 主动买入 vs 主动卖出
        - 成交额相对历史水平
        """
        detail = {
            'main_net_direction': 'neutral',
            'active_direction': 'neutral',
            'amount_vs_avg': 1.0,
            'notes': []
        }

        if len(self.history) < 3:
            return 0.0, detail

        # 主力净流入判断
        main_net = snap.main_net
        amount = snap.amount

        if amount > 0:
            main_net_ratio = main_net / amount
        else:
            main_net_ratio = 0

        if main_net_ratio > 0.15:
            detail['main_net_direction'] = 'strong_inflow'
            base_score = 0.9
        elif main_net_ratio > 0.05:
            detail['main_net_direction'] = 'moderate_inflow'
            base_score = 0.7
        elif main_net_ratio > -0.05:
            detail['main_net_direction'] = 'neutral'
            base_score = 0.5
        elif main_net_ratio > -0.15:
            detail['main_net_direction'] = 'moderate_outflow'
            base_score = 0.3
        else:
            detail['main_net_direction'] = 'strong_outflow'
            base_score = 0.1

        # 主动买卖判断
        total_active = snap.active_buy + snap.active_sell
        if total_active > 0:
            active_buy_ratio = snap.active_buy / total_active
            if active_buy_ratio > 0.6:
                detail['active_direction'] = 'active_buy_dominant'
                base_score += 0.05
            elif active_buy_ratio < 0.4:
                detail['active_direction'] = 'active_sell_dominant'
                base_score -= 0.05

        # 成交额相对历史
        hist_amounts = [h.amount for h in self.history if h.amount > 0]
        if hist_amounts:
            avg_amount = np.mean(hist_amounts[-10:])
            if avg_amount > 0:
                detail['amount_vs_avg'] = amount / avg_amount
                if detail['amount_vs_avg'] > 1.5:
                    base_score += 0.05
                    detail['notes'].append("成交额显著放大")
                elif detail['amount_vs_avg'] < 0.5:
                    base_score -= 0.05
                    detail['notes'].append("成交额萎缩")

        score = max(0.0, min(1.0, base_score))
        return score, detail

    # ========================================================================
    # 子维度2: 资金持续性 (flow_persistence_score)
    # ========================================================================

    def _score_flow_persistence(self) -> Tuple[float, Dict]:
        """
        资金持续性评分

        评分依据:
        - 主力净流入连续天数
        - 主动买入连续天数
        - 成交额持续性
        """
        detail = {
            'main_persistence_days': 0,
            'active_persistence_days': 0,
            'notes': []
        }

        if len(self.history) < 3:
            return 0.0, detail

        hist = list(self.history)

        # 主力净流入持续性
        main_persist = 0
        for snap in reversed(hist):
            if snap.main_net > 0:
                main_persist += 1
            else:
                break
        detail['main_persistence_days'] = main_persist

        # 主动买入持续性
        active_persist = 0
        for snap in reversed(hist):
            if snap.active_buy > snap.active_sell:
                active_persist += 1
            else:
                break
        detail['active_persistence_days'] = active_persist

        # 评分
        if main_persist >= 5 and active_persist >= 3:
            score = 0.95
            detail['notes'].append("主力流入持续5天+，主动买入持续3天+")
        elif main_persist >= 3 and active_persist >= 2:
            score = 0.8
            detail['notes'].append("主力流入持续3天+，主动买入持续2天+")
        elif main_persist >= 2:
            score = 0.6
            detail['notes'].append("主力流入持续2天")
        elif main_persist >= 1:
            score = 0.4
        else:
            score = 0.2

        return score, detail

    # ========================================================================
    # 子维度3: 大小单结构 (flow_structure_score)
    # ========================================================================

    def _score_flow_structure(self, snap: MoneyflowSnapshot) -> Tuple[float, Dict]:
        """
        大小单结构评分

        评分依据:
        - 大单承接候选：大单净流入 + 小单净流出 + 价格不大涨
        - 小单追逐候选：小单净流入强 + 主力净流出 + 价格冲高
        - 派发压力候选：主力净流出连续 + 价格高位
        """
        detail = {
            'structure_type': FlowStructure.UNCLEAR,
            'large_small_divergence': 0.0,
            'notes': []
        }

        if len(self.history) < 3:
            return 0.5, detail

        # 大小单 divergence
        main_net = snap.main_net
        small_net = snap.small_net

        if abs(small_net) > 0:
            detail['large_small_divergence'] = main_net / abs(small_net)
        else:
            detail['large_small_divergence'] = 0

        # 判断结构类型
        if main_net > 0 and small_net < 0:
            detail['structure_type'] = FlowStructure.LARGE_ABSORPTION
            detail['notes'].append("大单净流入，小单净流出，可能承接")
            score = 0.85
        elif main_net < 0 and small_net > 0:
            detail['structure_type'] = FlowStructure.SMALL_CHASING
            detail['notes'].append("小单净流入，主力净流出，可能追逐")
            score = 0.3
        elif main_net < 0 and small_net < 0:
            detail['structure_type'] = FlowStructure.DISTRIBUTION_PRESSURE
            detail['notes'].append("大小单同步净流出，派发压力")
            score = 0.15
        else:
            detail['structure_type'] = FlowStructure.BALANCED
            detail['notes'].append("大小单同向流入，结构平衡")
            score = 0.6

        # 检查历史持续性
        hist = list(self.history)
        recent_main = [h.main_net for h in hist[-5:]]
        if len(recent_main) >= 3 and all(m < 0 for m in recent_main):
            if detail['structure_type'] != FlowStructure.DISTRIBUTION_PRESSURE:
                detail['structure_type'] = FlowStructure.DISTRIBUTION_PRESSURE
                detail['notes'].append("主力连续净流出，动能衰减")
                score = 0.1

        return score, detail

    # ========================================================================
    # 子维度4: 筹码结构 (chip_structure_score)
    # ========================================================================

    def _score_chip_structure(self, snap: MoneyflowSnapshot) -> Tuple[float, Dict]:
        """
        筹码结构评分

        评分依据:
        - 筹码集中度
        - 获利盘比例
        - 筹码峰位置（需要当前价格对比）
        """
        detail = {
            'concentration': None,
            'profit_ratio': None,
            'notes': []
        }

        # 如果没有筹码数据，返回中性评分
        if snap.chip_peak_concentration is None and snap.profit_chips_ratio is None:
            return 0.5, detail

        score = 0.5

        # 筹码集中度（越高越集中）
        if snap.chip_peak_concentration is not None:
            conc = float(snap.chip_peak_concentration)
            detail['concentration'] = conc
            if conc > 0.5:
                detail['notes'].append("筹码高度集中")
                score += 0.15
            elif conc > 0.3:
                detail['notes'].append("筹码中度集中")
                score += 0.05
            else:
                detail['notes'].append("筹码分散")
                score -= 0.1

        # 获利盘比例
        if snap.profit_chips_ratio is not None:
            profit = float(snap.profit_chips_ratio)
            detail['profit_ratio'] = profit
            if profit > 0.8:
                detail['notes'].append("获利盘比例高，注意回吐压力")
                score -= 0.1
            elif profit > 0.5:
                detail['notes'].append("获利盘比例适中")
                score += 0.05
            elif profit > 0.2:
                detail['notes'].append("获利盘比例较低")
                score += 0.1
            else:
                detail['notes'].append("多数筹码套牢")
                score -= 0.05

        return max(0.0, min(1.0, score)), detail

    # ========================================================================
    # 标签判定
    # ========================================================================

    def _determine_labels(
        self,
        direction_score: float,
        persistence_score: float,
        structure_score: float,
        chip_score: float,
        direction_detail: Dict,
        structure_detail: Dict
    ) -> Tuple[EnergyLabel, List[EnergyLabel]]:
        """判定能量标签"""

        secondary = []

        # 能量不可用：数据不足或方向极弱
        if direction_score < 0.2:
            return EnergyLabel.ENERGY_INSUFFICIENT, secondary

        # 能量过热：方向强 + 结构显示小单追逐
        if (direction_score > 0.8 and
            structure_detail.get('structure_type') == FlowStructure.SMALL_CHASING):
            secondary.append(EnergyLabel.ENERGY_DIVERGENT)
            return EnergyLabel.ENERGY_OVERHEATED, secondary

        # 能量分化：方向与结构矛盾
        if direction_score > 0.6 and structure_score < 0.3:
            secondary.append(EnergyLabel.ENERGY_INSUFFICIENT)
            return EnergyLabel.ENERGY_DIVERGENT, secondary

        # 能量支持：方向正向 + 持续性良好 + 结构健康
        if (direction_score > 0.5 and
            persistence_score > 0.5 and
            structure_score > 0.5):
            if chip_score > 0.6:
                return EnergyLabel.ENERGY_SUPPORTIVE, secondary
            else:
                secondary.append(EnergyLabel.ENERGY_DIVERGENT)
                return EnergyLabel.ENERGY_SUPPORTIVE, secondary

        # 能量不足：方向弱或持续性差
        if direction_score < 0.4 or persistence_score < 0.3:
            return EnergyLabel.ENERGY_INSUFFICIENT, secondary

        # 默认
        return EnergyLabel.ENERGY_UNAVAILABLE, secondary

    # ========================================================================
    # 研究标签生成
    # ========================================================================

    def _generate_research_tags(
        self,
        snap: MoneyflowSnapshot,
        direction_detail: Dict,
        structure_detail: Dict,
        chip_detail: Dict
    ) -> List[str]:
        """生成研究标签（用于页面展示）"""
        tags = []

        # 资金关注标签
        main_dir = direction_detail.get('main_net_direction', 'neutral')
        if main_dir in ('strong_inflow', 'moderate_inflow'):
            tags.append("资金关注增强")
        elif main_dir == 'neutral':
            tags.append("资金关注一般")
        else:
            tags.append("资金关注不足")

        # 主动买卖标签
        active_dir = direction_detail.get('active_direction', 'neutral')
        if active_dir == 'active_buy_dominant':
            tags.append("主动买入增强")
        elif active_dir == 'active_sell_dominant':
            tags.append("主动卖出增强")

        # 成交活跃标签
        amount_ratio = direction_detail.get('amount_vs_avg', 1.0)
        if amount_ratio > 1.5:
            tags.append("成交活跃放大")
        elif amount_ratio < 0.5:
            tags.append("成交活跃度低")
        else:
            tags.append("成交活跃度正常")

        # 大小单结构标签
        struct_type = structure_detail.get('structure_type', FlowStructure.UNCLEAR)
        if struct_type == FlowStructure.LARGE_ABSORPTION:
            tags.append("大单承接候选")
        elif struct_type == FlowStructure.SMALL_CHASING:
            tags.append("小单追逐候选")
        elif struct_type == FlowStructure.DISTRIBUTION_PRESSURE:
            tags.append("派发压力候选")

        # 筹码结构标签
        if chip_detail.get('concentration') is not None:
            conc = chip_detail['concentration']
            if conc > 0.5:
                tags.append("筹码高度集中")
            elif conc > 0.3:
                tags.append("筹码中度集中")

        if chip_detail.get('profit_ratio') is not None:
            profit = chip_detail['profit_ratio']
            if profit > 0.8:
                tags.append("获利盘比例高")
            elif profit < 0.2:
                tags.append("多数筹码套牢")

        # 资金流与价格分化（需要外部传入价格状态，这里简化）
        if struct_type == FlowStructure.SMALL_CHASING and direction_detail.get('main_net_direction') == 'strong_outflow':
            tags.append("资金流与价格状态分化")

        return tags

    # ========================================================================
    # 解释构建
    # ========================================================================

    def _build_explanation(
        self,
        snap: MoneyflowSnapshot,
        direction_score: float,
        persistence_score: float,
        structure_score: float,
        chip_score: float,
        direction_detail: Dict,
        structure_detail: Dict,
        chip_detail: Dict,
        primary_label: EnergyLabel
    ) -> str:
        """构建解释文本（P106规范：解释，不建议）"""
        parts = []

        # 总体定性
        label_desc = {
            EnergyLabel.ENERGY_SUPPORTIVE: "能量状态支持观察",
            EnergyLabel.ENERGY_DIVERGENT: "能量状态出现分化",
            EnergyLabel.ENERGY_OVERHEATED: "能量状态过热，需警惕",
            EnergyLabel.ENERGY_INSUFFICIENT: "能量状态不足",
            EnergyLabel.ENERGY_UNAVAILABLE: "能量数据不可用",
        }
        parts.append(label_desc.get(primary_label, "能量状态未知"))

        # 四维度简述
        parts.append(
            f"方向{direction_score:.0%} | 持续{persistence_score:.0%} | "
            f"结构{structure_score:.0%} | 筹码{chip_score:.0%}"
        )

        # 主力流向
        main_dir = direction_detail.get('main_net_direction', 'neutral')
        main_desc = {
            'strong_inflow': '主力净流入强劲',
            'moderate_inflow': '主力净流入温和',
            'neutral': '主力流向中性',
            'moderate_outflow': '主力净流出温和',
            'strong_outflow': '主力净流出强劲',
        }
        parts.append(main_desc.get(main_dir, ''))

        # 结构说明
        struct_type = structure_detail.get('structure_type', FlowStructure.UNCLEAR)
        struct_desc = {
            FlowStructure.LARGE_ABSORPTION: '大单承接特征明显',
            FlowStructure.SMALL_CHASING: '小单追逐特征明显',
            FlowStructure.DISTRIBUTION_PRESSURE: '存在派发压力',
            FlowStructure.BALANCED: '大小单结构平衡',
            FlowStructure.UNCLEAR: '大小单结构不明',
        }
        parts.append(struct_desc.get(struct_type, ''))

        # 备注
        all_notes = []
        all_notes.extend(direction_detail.get('notes', []))
        all_notes.extend(structure_detail.get('notes', []))
        all_notes.extend(chip_detail.get('notes', []))
        if all_notes:
            parts.append("；".join(all_notes))

        # 边界声明
        parts.append("注意：资金流仅反映订单行为，不等于真实持仓变化")

        return " | ".join([p for p in parts if p])

    # ========================================================================
    # 便捷接口
    # ========================================================================

    def assess_from_row(self, row: pd.Series) -> EnergyAssessment:
        """从DataFrame单行直接评估"""
        snap = self._row_to_snapshot(row)
        return self.assess(snap)

    def get_summary(self) -> Dict[str, Any]:
        """获取历史摘要"""
        if not self.history:
            return {"status": "no_data"}

        hist = list(self.history)
        return {
            "symbol": self.symbol,
            "history_days": len(hist),
            "latest_date": hist[-1].trade_date,
            "avg_main_net": np.mean([h.main_net for h in hist]),
            "avg_turnover_rate": np.mean([h.turnover_rate for h in hist]),
            "main_net_positive_days": sum(1 for h in hist if h.main_net > 0),
        }


# ============================================================================
# 与 State Hex 策略的集成接口
# ============================================================================

def attach_energy_to_signal(
    strategy_signal: Any,
    energy_assessment: EnergyAssessment
) -> Any:
    """
    将能量评估附加到策略信号

    用于主线顺序第4步：资金流增量证据附加到已生成的状态信号
    """
    if strategy_signal is None:
        return None

    # 添加能量标签到state_tags
    if hasattr(strategy_signal, 'state_tags'):
        strategy_signal.state_tags.extend(energy_assessment.research_tags)
        strategy_signal.state_tags.append(f"能量:{energy_assessment.primary_label.value}")

    # 扩展reasoning
    if hasattr(strategy_signal, 'reasoning'):
        strategy_signal.reasoning += f" | 能量评估: {energy_assessment.explanation}"

    # 调整信心度（能量支持加分，能量分化/过热扣分）
    if hasattr(strategy_signal, 'confidence'):
        if energy_assessment.primary_label == EnergyLabel.ENERGY_SUPPORTIVE:
            strategy_signal.confidence = min(1.0, strategy_signal.confidence + 0.05)
        elif energy_assessment.primary_label == EnergyLabel.ENERGY_DIVERGENT:
            strategy_signal.confidence = max(0.0, strategy_signal.confidence - 0.08)
        elif energy_assessment.primary_label == EnergyLabel.ENERGY_OVERHEATED:
            strategy_signal.confidence = max(0.0, strategy_signal.confidence - 0.1)
        elif energy_assessment.primary_label == EnergyLabel.ENERGY_INSUFFICIENT:
            strategy_signal.confidence = max(0.0, strategy_signal.confidence - 0.05)

    return strategy_signal


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("P106 Moneyflow Energy Layer Test")
    print("=" * 70)

    # 构造测试数据
    np.random.seed(42)
    n_days = 20

    test_data = []
    for i in range(n_days):
        # 模拟主力净流入连续为正
        main_net = np.random.uniform(1000, 5000) if i > 5 else np.random.uniform(-2000, 2000)
        super_large = main_net * 0.4
        large = main_net * 0.35
        medium = np.random.uniform(-500, 500)
        small = -(super_large + large + medium) + np.random.uniform(-200, 200)

        active_buy = np.random.uniform(8000, 12000)
        active_sell = active_buy * np.random.uniform(0.5, 0.9)

        test_data.append({
            'symbol': 'TEST',
            'trade_date': f'2025-01-{i+1:02d}',
            'main_net_inflow': main_net,
            'super_large_net_inflow': super_large,
            'large_net_inflow': large,
            'medium_net_inflow': medium,
            'small_net_inflow': small,
            'active_buy_amount': active_buy,
            'active_sell_amount': active_sell,
            'passive_buy_amount': np.random.uniform(5000, 8000),
            'passive_sell_amount': np.random.uniform(5000, 8000),
            'amount': np.random.uniform(50000, 100000),
            'turnover_rate': np.random.uniform(0.02, 0.08),
            'chip_peak_price': 10.5,
            'chip_peak_concentration': np.random.uniform(0.2, 0.6),
            'chip_cost_90': (9.0, 12.0),
            'chip_cost_70': (10.0, 11.0),
            'profit_chips_ratio': np.random.uniform(0.3, 0.7),
            'source_name': 'TEST',
        })

    df = pd.DataFrame(test_data)
    print(f"\n测试数据: {len(df)}天")

    # 初始化能量层
    layer = MoneyflowEnergyLayer(history_days=20)
    layer.load_history(df)

    # 评估最新一天
    latest = test_data[-1]
    snap = MoneyflowSnapshot(
        symbol=latest['symbol'],
        trade_date=latest['trade_date'],
        main_net=latest['main_net_inflow'],
        super_large_net=latest['super_large_net_inflow'],
        large_net=latest['large_net_inflow'],
        medium_net=latest['medium_net_inflow'],
        small_net=latest['small_net_inflow'],
        active_buy=latest['active_buy_amount'],
        active_sell=latest['active_sell_amount'],
        amount=latest['amount'],
        turnover_rate=latest['turnover_rate'],
        chip_peak_concentration=latest['chip_peak_concentration'],
        profit_chips_ratio=latest['profit_chips_ratio'],
    )

    assessment = layer.assess(snap)

    print(f"\n评估结果:")
    print(f"  品种: {assessment.symbol} | 日期: {assessment.trade_date}")
    print(f"  资金方向评分: {assessment.flow_direction_score:.2f}")
    print(f"  资金持续性评分: {assessment.flow_persistence_score:.2f}")
    print(f"  大小单结构评分: {assessment.flow_structure_score:.2f}")
    print(f"  筹码结构评分: {assessment.chip_structure_score:.2f}")
    print(f"  主标签: {assessment.primary_label.value}")
    print(f"  研究标签: {', '.join(assessment.research_tags)}")
    print(f"  解释: {assessment.explanation}")

    print("\n历史摘要:")
    print(f"  {layer.get_summary()}")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
