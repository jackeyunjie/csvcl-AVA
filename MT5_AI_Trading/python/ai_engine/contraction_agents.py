"""
多周期收缩跟踪 Agent 系统
每个周期独立视角，跟踪收缩指标并提出观察
周期: MN1 / W1 / D1 / H4 / H1 / M15
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import duckdb


@dataclass
class ContractionObservation:
    """收缩观察记录"""
    symbol: str
    timeframe: str  # MN1/W1/D1/H4/H1/M15
    hex_value: str
    contraction_level: int  # 0-4, 0=无收缩, 4=最强收缩(F/-F)
    contraction_phase: str  # "early"/"developing"/"mature"/"extreme"
    duration_bars: int  # 收缩持续K线数
    breakout_probability: float  # 突破概率 0-1
    breakout_direction: str  # "up"/"down"/"unknown"
    observation: str  # Agent 观察结论
    alert_level: str  # "normal"/"watch"/"alert"/"critical"
    related_timeframes: List[str] = field(default_factory=list)  # 关联收缩周期


class ContractionAgent:
    """
    单个周期收缩跟踪 Agent
    独立分析该周期的收缩状态，不依赖其他周期
    """
    
    # 收缩等级映射
    CONTRACTION_MAP = {
        'C': (1, 'early'), '-C': (1, 'early'),
        'D': (2, 'developing'), '-D': (2, 'developing'),
        'E': (3, 'mature'), '-E': (3, 'mature'),
        'F': (4, 'extreme'), '-F': (4, 'extreme'),
    }
    
    # 突破概率表 (基于历史统计)
    BREAKOUT_PROB = {
        'C': 0.35, '-C': 0.35,
        'D': 0.50, '-D': 0.50,
        'E': 0.70, '-E': 0.70,
        'F': 0.85, '-F': 0.85,
    }
    
    def __init__(self, timeframe: str):
        """
        Args:
            timeframe: MN1/W1/D1/H4/H1/M15
        """
        self.timeframe = timeframe
        self.name = f"{timeframe}ContractionAgent"
        
    def analyze(self, symbol: str, hex_value: str, 
                prev_hex: Optional[str] = None,
                history: Optional[List[str]] = None) -> ContractionObservation:
        """
        分析单个品种的收缩状态
        
        Args:
            symbol: 品种名
            hex_value: 当前周期hex值
            prev_hex: 上一根K线hex值
            history: 最近N根K线hex历史
        """
        # 判断是否在收缩
        if hex_value not in self.CONTRACTION_MAP:
            return ContractionObservation(
                symbol=symbol,
                timeframe=self.timeframe,
                hex_value=hex_value,
                contraction_level=0,
                contraction_phase="none",
                duration_bars=0,
                breakout_probability=0.0,
                breakout_direction="unknown",
                observation=f"{self.timeframe} 非收缩状态 ({hex_value})",
                alert_level="normal"
            )
        
        level, phase = self.CONTRACTION_MAP[hex_value]
        prob = self.BREAKOUT_PROB[hex_value]
        
        # 计算收缩持续时间
        duration = self._calculate_duration(hex_value, history)
        
        # 判断突破方向
        direction = self._estimate_direction(hex_value, prev_hex, history)
        
        # 生成观察结论
        observation = self._generate_observation(
            symbol, hex_value, level, phase, duration, direction, prob
        )
        
        # 确定警戒级别
        alert = self._determine_alert(level, duration, prob)
        
        return ContractionObservation(
            symbol=symbol,
            timeframe=self.timeframe,
            hex_value=hex_value,
            contraction_level=level,
            contraction_phase=phase,
            duration_bars=duration,
            breakout_probability=prob,
            breakout_direction=direction,
            observation=observation,
            alert_level=alert
        )
    
    def _calculate_duration(self, hex_value: str, 
                           history: Optional[List[str]]) -> int:
        """计算收缩持续K线数"""
        if not history:
            return 1
        
        duration = 1
        for h in reversed(history):
            if h == hex_value or (h in self.CONTRACTION_MAP and 
                                  self.CONTRACTION_MAP[h][0] >= 
                                  self.CONTRACTION_MAP.get(hex_value, (0,))[0]):
                duration += 1
            else:
                break
        return duration
    
    def _estimate_direction(self, hex_value: str,
                           prev_hex: Optional[str],
                           history: Optional[List[str]]) -> str:
        """估计突破方向"""
        # 基于负号判断
        if hex_value.startswith('-'):
            # 负收缩通常向下突破
            return "down"
        else:
            # 正收缩通常向上突破
            return "up"
    
    def _generate_observation(self, symbol: str, hex_value: str,
                             level: int, phase: str, duration: int,
                             direction: str, prob: float) -> str:
        """生成观察结论"""
        dir_cn = "向下" if direction == "down" else "向上"
        
        if level == 4:
            return (f"{symbol} {self.timeframe} 极端收缩({hex_value})，"
                   f"持续{duration}根K线，{dir_cn}突破概率{prob:.0%}，"
                   f"随时可能爆发")
        elif level == 3:
            return (f"{symbol} {self.timeframe} 成熟收缩({hex_value})，"
                   f"持续{duration}根K线，{dir_cn}突破概率{prob:.0%}")
        elif level == 2:
            return (f"{symbol} {self.timeframe} 发展中收缩({hex_value})，"
                   f"持续{duration}根K线，观察是否加深")
        else:
            return (f"{symbol} {self.timeframe} 早期收缩({hex_value})，"
                   f"刚形成，持续观察")
    
    def _determine_alert(self, level: int, duration: int, prob: float) -> str:
        """确定警戒级别"""
        if level >= 4 and duration >= 2:
            return "critical"
        elif level >= 3 and duration >= 3:
            return "alert"
        elif level >= 3:
            return "watch"
        else:
            return "normal"


class MultiTimeframeContractionSystem:
    """
    多周期收缩跟踪系统
    管理6个独立Agent，汇总跨周期收缩观察
    """
    
    TIMEFRAMES = ['D1', 'H1', 'M15']
    
    def __init__(self, db_path: str = 'data/h1_state.duckdb'):
        self.db_path = db_path
        self.agents = {tf: ContractionAgent(tf) for tf in self.TIMEFRAMES}
        
    def analyze_all(self, symbol: str, 
                   state: Dict[str, str]) -> List[ContractionObservation]:
        """
        分析单个品种的所有周期收缩状态
        
        Args:
            symbol: 品种名
            state: {mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex, m15_hex}
        """
        observations = []
        
        for tf in self.TIMEFRAMES:
            hex_key = tf.lower() + '_hex'
            if hex_key in state and state[hex_key]:
                obs = self.agents[tf].analyze(
                    symbol=symbol,
                    hex_value=state[hex_key]
                )
                observations.append(obs)
        
        # 标记跨周期关联
        self._mark_cross_timeframe_relations(observations)
        
        return observations
    
    def _mark_cross_timeframe_relations(self, 
                                       observations: List[ContractionObservation]):
        """标记跨周期收缩关联"""
        # 找出正在收缩的周期
        contracting = [o for o in observations if o.contraction_level > 0]
        
        for obs in observations:
            if obs.contraction_level > 0:
                # 找出相邻周期的收缩状态
                tf_idx = self.TIMEFRAMES.index(obs.timeframe)
                related = []
                
                for other in contracting:
                    if other.timeframe == obs.timeframe:
                        continue
                    other_idx = self.TIMEFRAMES.index(other.timeframe)
                    
                    # 相邻周期或同等级收缩视为关联
                    if abs(other_idx - tf_idx) <= 1:
                        related.append(other.timeframe)
                    elif other.contraction_level >= 3 and obs.contraction_level >= 3:
                        related.append(other.timeframe)
                
                obs.related_timeframes = related
    
    def get_critical_alerts(self, observations: List[ContractionObservation]) -> List[ContractionObservation]:
        """获取关键警戒级别的观察"""
        return [o for o in observations 
                if o.alert_level in ['alert', 'critical']]
    
    def get_synchronized_contractions(self, 
                                     observations: List[ContractionObservation]) -> List[ContractionObservation]:
        """获取跨周期同步收缩（多周期同时收缩）"""
        return [o for o in observations 
                if o.contraction_level >= 3 and len(o.related_timeframes) >= 1]


def print_contraction_report(symbol: str, observations: List[ContractionObservation]):
    """打印单个品种的收缩观察报告"""
    print(f"\n{'='*60}")
    print(f"【{symbol}】多周期收缩观察报告")
    print(f"{'='*60}")
    
    # 按周期排序
    tf_order = {'MN1':0, 'W1':1, 'D1':2, 'H4':3, 'H1':4, 'M15':5}
    sorted_obs = sorted(observations, key=lambda x: tf_order.get(x.timeframe, 99))
    
    for obs in sorted_obs:
        if obs.contraction_level == 0:
            continue
            
        alert_icon = {
            'normal': '○',
            'watch': '△',
            'alert': '▲',
            'critical': '🔴'
        }.get(obs.alert_level, '○')
        
        print(f"\n{alert_icon} {obs.timeframe}: {obs.hex_value} "
              f"(等级{obs.contraction_level}/持续{obs.duration_bars}K)")
        print(f"   突破概率: {obs.breakout_probability:.0%} | "
              f"方向: {obs.breakout_direction}")
        print(f"   观察: {obs.observation}")
        
        if obs.related_timeframes:
            print(f"   ⚡ 跨周期同步: {', '.join(obs.related_timeframes)}")
    
    # 汇总
    critical = [o for o in observations if o.alert_level == 'critical']
    sync = [o for o in observations if o.contraction_level >= 3 and o.related_timeframes]
    
    if critical:
        print(f"\n🔴 关键警戒: {len(critical)} 个周期")
    if sync:
        print(f"⚡ 同步收缩: {len(sync)} 个周期联动")


# 便捷函数
def analyze_symbol_contraction(symbol: str, state: Dict[str, str]) -> List[ContractionObservation]:
    """分析单个品种的收缩状态"""
    system = MultiTimeframeContractionSystem()
    return system.analyze_all(symbol, state)


def analyze_all_symbols_contractions(db_path: str = 'data/h1_state.duckdb') -> Dict[str, List[ContractionObservation]]:
    """分析数据库中所有品种的收缩状态"""
    conn = duckdb.connect(db_path, read_only=True)
    
    # 获取最新状态
    rows = conn.execute('''
        SELECT symbol, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex
        FROM h1_state_snapshot s1
        WHERE timestamp = (
            SELECT MAX(timestamp) 
            FROM h1_state_snapshot s2 
            WHERE s2.symbol = s1.symbol
        )
    ''').fetchall()
    
    conn.close()
    
    system = MultiTimeframeContractionSystem(db_path)
    results = {}
    
    for row in rows:
        symbol = row[0]
        state = {
            'mn1_hex': row[1], 'w1_hex': row[2], 'd1_hex': row[3],
            'h4_hex': row[4], 'h1_hex': row[5]
        }
        results[symbol] = system.analyze_all(symbol, state)
    
    return results


if __name__ == '__main__':
    # 测试
    test_state = {
        'mn1_hex': '5', 'w1_hex': '-F', 'd1_hex': '-6',
        'h4_hex': '-6', 'h1_hex': '6', 'm15_hex': 'C'
    }
    
    obs = analyze_symbol_contraction('XAUUSD', test_state)
    print_contraction_report('XAUUSD', obs)
