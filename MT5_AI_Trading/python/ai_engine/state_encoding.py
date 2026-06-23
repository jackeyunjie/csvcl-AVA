"""
状态编码系统 - 三层架构
功能：
1. 统一语义层：市场无关的状态定义
2. 市场编码层：各市场独立的编码实现
3. 原始兼容层：新旧系统映射适配
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, Optional, List, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 第一层：统一语义层（市场无关）
# ============================================================================

class MarketStateSemantic(Enum):
    """统一市场状态语义

    所有市场的状态都必须映射到这些语义上，
    这是跨市场策略回测和对比的基础。
    """
    UNKNOWN = auto()              # 未知/数据不足
    NO_CONTRACTION = auto()       # 无收缩状态
    CONTRACTION = auto()          # 有收缩状态
    BREAKOUT_TREND = auto()       # 突破趋势（无收缩）
    BREAKOUT_CONTRACTION = auto() # 突破+收缩
    STRONG_TREND = auto()         # 强趋势（旧系统6/7语义）
    STRONG_TREND_CONTRACTION = auto()  # 强趋势+收缩（旧系统14/15语义）


@dataclass(frozen=True)
class StateSemantic:
    """状态语义描述"""
    semantic: MarketStateSemantic
    trend_strength: int = 0       # 趋势强度 0-10
    contraction: bool = False     # 是否有收缩
    breakout: bool = False        # 是否突破
    description: str = ""


# 语义定义表
SEMANTIC_DEFINITIONS: Dict[MarketStateSemantic, StateSemantic] = {
    MarketStateSemantic.UNKNOWN: StateSemantic(
        semantic=MarketStateSemantic.UNKNOWN,
        trend_strength=0,
        contraction=False,
        breakout=False,
        description="未知状态，数据不足或无法判断"
    ),
    MarketStateSemantic.NO_CONTRACTION: StateSemantic(
        semantic=MarketStateSemantic.NO_CONTRACTION,
        trend_strength=3,
        contraction=False,
        breakout=False,
        description="无收缩状态，市场处于常规波动"
    ),
    MarketStateSemantic.CONTRACTION: StateSemantic(
        semantic=MarketStateSemantic.CONTRACTION,
        trend_strength=2,
        contraction=True,
        breakout=False,
        description="有收缩状态，波动率压缩，可能即将变盘"
    ),
    MarketStateSemantic.BREAKOUT_TREND: StateSemantic(
        semantic=MarketStateSemantic.BREAKOUT_TREND,
        trend_strength=6,
        contraction=False,
        breakout=True,
        description="突破趋势，价格突破关键位但无收缩"
    ),
    MarketStateSemantic.BREAKOUT_CONTRACTION: StateSemantic(
        semantic=MarketStateSemantic.BREAKOUT_CONTRACTION,
        trend_strength=7,
        contraction=True,
        breakout=True,
        description="突破+收缩，高概率延续趋势"
    ),
    MarketStateSemantic.STRONG_TREND: StateSemantic(
        semantic=MarketStateSemantic.STRONG_TREND,
        trend_strength=8,
        contraction=False,
        breakout=False,
        description="强趋势状态（旧系统6/7级别）"
    ),
    MarketStateSemantic.STRONG_TREND_CONTRACTION: StateSemantic(
        semantic=MarketStateSemantic.STRONG_TREND_CONTRACTION,
        trend_strength=9,
        contraction=True,
        breakout=False,
        description="强趋势+收缩（旧系统14/15级别）"
    ),
}


# ============================================================================
# 第二层：市场编码抽象基类
# ============================================================================

class StateEncoder(ABC):
    """状态编码器抽象基类

    每个市场（外汇/A股/港股/美股）实现各自的编码器，
    但对外暴露统一的语义接口。
    """

    def __init__(self, market_name: str):
        self.market_name = market_name
        self._semantic_to_code: Dict[MarketStateSemantic, int] = {}
        self._code_to_semantic: Dict[int, MarketStateSemantic] = {}
        self._build_maps()
        logger.info(f"{market_name}编码器初始化完成")

    @abstractmethod
    def _build_maps(self):
        """构建语义↔编码映射表，子类必须实现"""
        pass

    @abstractmethod
    def encode(self, semantic: MarketStateSemantic) -> int:
        """将语义编码为市场特定数字"""
        pass

    @abstractmethod
    def decode(self, code: int) -> MarketStateSemantic:
        """将市场特定数字解码为语义"""
        pass

    @abstractmethod
    def get_trend_strength(self, code: int) -> int:
        """获取编码对应的趋势强度（0-10）"""
        pass

    @abstractmethod
    def is_contraction(self, code: int) -> bool:
        """判断编码是否表示收缩状态"""
        pass

    @abstractmethod
    def is_breakout(self, code: int) -> bool:
        """判断编码是否表示突破状态"""
        pass

    def semantic_to_description(self, semantic: MarketStateSemantic) -> str:
        """获取语义描述"""
        return SEMANTIC_DEFINITIONS.get(semantic, SEMANTIC_DEFINITIONS[MarketStateSemantic.UNKNOWN]).description

    def code_to_description(self, code: int) -> str:
        """获取编码描述"""
        semantic = self.decode(code)
        return self.semantic_to_description(semantic)

    def get_all_codes(self) -> List[int]:
        """获取该市场所有有效编码"""
        return sorted(self._code_to_semantic.keys())

    def get_all_semantics(self) -> List[MarketStateSemantic]:
        """获取该市场支持的所有语义"""
        return list(self._semantic_to_code.keys())


# ============================================================================
# 第三层：具体市场编码器实现
# ============================================================================

class GenericEncoder(StateEncoder):
    """通用编码器（新系统）

    位运算语义：
    - bit0: 收缩标志 (0=无, 1=有) → +2
    - bit3: 突破标志 (0=无, 1=有) → +8
    - 基础值: 0 = 无收缩无突破

    编码值：
    0  = 无收缩 + 无突破
    2  = 有收缩 + 无突破
    8  = 无收缩 + 突破
    10 = 有收缩 + 突破
    """

    def __init__(self):
        super().__init__("Generic")

    def _build_maps(self):
        self._semantic_to_code = {
            MarketStateSemantic.NO_CONTRACTION: 0,
            MarketStateSemantic.CONTRACTION: 2,
            MarketStateSemantic.BREAKOUT_TREND: 8,
            MarketStateSemantic.BREAKOUT_CONTRACTION: 10,
        }
        self._code_to_semantic = {v: k for k, v in self._semantic_to_code.items()}

    def encode(self, semantic: MarketStateSemantic) -> int:
        if semantic not in self._semantic_to_code:
            logger.warning(f"通用编码器不支持语义: {semantic}")
            return 0
        return self._semantic_to_code[semantic]

    def decode(self, code: int) -> MarketStateSemantic:
        return self._code_to_semantic.get(code, MarketStateSemantic.UNKNOWN)

    def get_trend_strength(self, code: int) -> int:
        semantic = self.decode(code)
        return SEMANTIC_DEFINITIONS.get(semantic, SEMANTIC_DEFINITIONS[MarketStateSemantic.UNKNOWN]).trend_strength

    def is_contraction(self, code: int) -> bool:
        return bool(code & 0b0010)  # bit1

    def is_breakout(self, code: int) -> bool:
        return bool(code & 0b1000)  # bit3


class ForexLegacyEncoder(StateEncoder):
    """外汇旧系统编码器（兼容MT4/MT5）

    旧系统编码：
    6  = 强趋势（无收缩）
    7  = 强趋势（轻微收缩）
    14 = 强趋势+收缩（过渡态）
    15 = 强趋势+强收缩（最强信号）

    映射到语义：
    6  → STRONG_TREND
    7  → STRONG_TREND（带轻微收缩标记）
    14 → STRONG_TREND_CONTRACTION
    15 → STRONG_TREND_CONTRACTION（最强）
    """

    def __init__(self):
        super().__init__("ForexLegacy")

    def _build_maps(self):
        self._semantic_to_code = {
            MarketStateSemantic.STRONG_TREND: 6,
            MarketStateSemantic.STRONG_TREND_CONTRACTION: 14,
        }
        self._code_to_semantic = {
            6: MarketStateSemantic.STRONG_TREND,
            7: MarketStateSemantic.STRONG_TREND,  # 7映射到STRONG_TREND
            14: MarketStateSemantic.STRONG_TREND_CONTRACTION,
            15: MarketStateSemantic.STRONG_TREND_CONTRACTION,  # 15映射到STRONG_TREND_CONTRACTION
        }

    def encode(self, semantic: MarketStateSemantic) -> int:
        if semantic not in self._semantic_to_code:
            logger.warning(f"外汇旧编码器不支持语义: {semantic}")
            return 6
        return self._semantic_to_code[semantic]

    def decode(self, code: int) -> MarketStateSemantic:
        return self._code_to_semantic.get(code, MarketStateSemantic.UNKNOWN)

    def get_trend_strength(self, code: int) -> int:
        mapping = {
            6: 8,
            7: 8,
            14: 9,
            15: 10,
        }
        return mapping.get(code, 0)

    def is_contraction(self, code: int) -> bool:
        return code in (7, 14, 15)

    def is_breakout(self, code: int) -> bool:
        return False  # 旧系统没有独立的breakout概念


class AShareEncoder(StateEncoder):
    """A股编码器

    A股特性：
    - 涨跌停限制（10%/20%）
    - T+1交易
    - 需要区分主板/创业板/科创板

    编码设计（扩展通用编码）：
    0  = 无收缩 + 无突破
    2  = 有收缩 + 无突破
    8  = 无收缩 + 突破
    10 = 有收缩 + 突破
    16 = 涨停状态（特殊标记）
    18 = 涨停+收缩
    """

    def __init__(self):
        super().__init__("AShare")

    def _build_maps(self):
        self._semantic_to_code = {
            MarketStateSemantic.NO_CONTRACTION: 0,
            MarketStateSemantic.CONTRACTION: 2,
            MarketStateSemantic.BREAKOUT_TREND: 8,
            MarketStateSemantic.BREAKOUT_CONTRACTION: 10,
        }
        self._code_to_semantic = {v: k for k, v in self._semantic_to_code.items()}
        # 补充涨停状态
        self._code_to_semantic[16] = MarketStateSemantic.BREAKOUT_TREND
        self._code_to_semantic[18] = MarketStateSemantic.BREAKOUT_CONTRACTION

    def encode(self, semantic: MarketStateSemantic) -> int:
        return self._semantic_to_code.get(semantic, 0)

    def decode(self, code: int) -> MarketStateSemantic:
        return self._code_to_semantic.get(code, MarketStateSemantic.UNKNOWN)

    def get_trend_strength(self, code: int) -> int:
        mapping = {
            0: 3, 2: 2, 8: 6, 10: 7, 16: 8, 18: 9
        }
        return mapping.get(code, 0)

    def is_contraction(self, code: int) -> bool:
        return bool(code & 0b0010)

    def is_breakout(self, code: int) -> bool:
        return bool(code & 0b1000) or code in (16, 18)

    def is_limit_up(self, code: int) -> bool:
        """A股特有：判断是否涨停"""
        return code in (16, 18)


# ============================================================================
# 编码器工厂与适配器
# ============================================================================

class StateEncoderFactory:
    """编码器工厂"""

    _encoders: Dict[str, type] = {
        "generic": GenericEncoder,
        "forex_legacy": ForexLegacyEncoder,
        "a_share": AShareEncoder,
    }

    @classmethod
    def create(cls, market_type: str) -> StateEncoder:
        """创建编码器实例"""
        encoder_class = cls._encoders.get(market_type.lower())
        if not encoder_class:
            raise ValueError(f"未知市场类型: {market_type}，可用: {list(cls._encoders.keys())}")
        return encoder_class()

    @classmethod
    def register(cls, market_type: str, encoder_class: type):
        """注册新编码器"""
        cls._encoders[market_type.lower()] = encoder_class

    @classmethod
    def list_markets(cls) -> List[str]:
        """列出所有支持的市场"""
        return list(cls._encoders.keys())


class StateAdapter:
    """跨市场状态适配器

    核心功能：将A市场的编码转换为B市场的编码，
    中间经过统一语义层，确保转换的语义一致性。
    """

    def __init__(self, source_market: str, target_market: str):
        self.source_encoder = StateEncoderFactory.create(source_market)
        self.target_encoder = StateEncoderFactory.create(target_market)
        logger.info(f"适配器创建: {source_market} → {target_market}")

    def convert(self, source_code: int) -> int:
        """将源市场编码转换为目标市场编码"""
        semantic = self.source_encoder.decode(source_code)
        if semantic == MarketStateSemantic.UNKNOWN:
            logger.warning(f"无法识别的源编码: {source_code}")
            return self.target_encoder.encode(MarketStateSemantic.NO_CONTRACTION)
        return self.target_encoder.encode(semantic)

    def convert_batch(self, source_codes: List[int]) -> List[int]:
        """批量转换"""
        return [self.convert(c) for c in source_codes]

    def compare_trend_strength(self, code_a: int, code_b: int) -> int:
        """比较两个编码的趋势强度

        Returns:
            -1: code_a 弱于 code_b
             0: 相等
             1: code_a 强于 code_b
        """
        strength_a = self.source_encoder.get_trend_strength(code_a)
        # 统一语义后比较
        semantic_a = self.source_encoder.decode(code_a)
        # 找到目标编码器中相同语义的编码
        target_codes = [c for c, s in self.target_encoder._code_to_semantic.items() if s == semantic_a]
        if not target_codes:
            return 0
        strength_b = self.target_encoder.get_trend_strength(code_b)
        if strength_a < strength_b:
            return -1
        elif strength_a > strength_b:
            return 1
        return 0


# ============================================================================
# 便捷函数
# ============================================================================

def get_encoder(market_type: str) -> StateEncoder:
    """获取编码器实例"""
    return StateEncoderFactory.create(market_type)


def convert_state(source_code: int, from_market: str, to_market: str) -> int:
    """一键转换状态编码"""
    adapter = StateAdapter(from_market, to_market)
    return adapter.convert(source_code)


def describe_state(code: int, market_type: str = "generic") -> str:
    """获取状态描述"""
    encoder = get_encoder(market_type)
    return encoder.code_to_description(code)


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("状态编码系统测试")
    print("=" * 60)

    # 1. 测试通用编码器
    print("\n[通用编码器]")
    generic = GenericEncoder()
    for code in [0, 2, 8, 10]:
        sem = generic.decode(code)
        desc = generic.code_to_description(code)
        print(f"  编码{code:2d} → {sem.name:25s} | 收缩:{generic.is_contraction(code)} | 突破:{generic.is_breakout(code)} | {desc}")

    # 2. 测试外汇旧编码器
    print("\n[外汇旧编码器]")
    forex = ForexLegacyEncoder()
    for code in [6, 7, 14, 15]:
        sem = forex.decode(code)
        desc = forex.code_to_description(code)
        strength = forex.get_trend_strength(code)
        print(f"  编码{code:2d} → {sem.name:25s} | 强度:{strength} | 收缩:{forex.is_contraction(code)} | {desc}")

    # 3. 测试跨市场转换
    print("\n[跨市场转换: 外汇旧 → 通用新]")
    adapter = StateAdapter("forex_legacy", "generic")
    for old_code in [6, 7, 14, 15]:
        new_code = adapter.convert(old_code)
        print(f"  旧{old_code:2d} → 新{new_code:2d} | {describe_state(new_code, 'generic')}")

    # 4. 测试A股编码器
    print("\n[A股编码器]")
    a_share = AShareEncoder()
    for code in [0, 2, 8, 10, 16, 18]:
        sem = a_share.decode(code)
        print(f"  编码{code:2d} → {sem.name:25s} | 涨停:{a_share.is_limit_up(code)}")

    # 5. 测试工厂
    print("\n[编码器工厂]")
    print(f"  支持市场: {StateEncoderFactory.list_markets()}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
