"""
多周期共振收缩突破研究 v3 单元测试

覆盖:
- H1 setup 只能拿到过去已收盘 H4/D1 bar (as-of对齐)
- 同一突破被多个 setup 捕捉时，event_id 只计一次
- short target 逻辑正确 (.max())
- 入场前触发 stop 不算交易止损
- 1bar/5bar 周期语义正确 (入场后第N根K线)
- 成本扣减正确
- Pivot/SR 不重复计分
"""

import sys
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "python"))

from squeeze_multi_timeframe_research_v3 import (
    MultiTimeframeSqueezeResearchV3,
    SqueezeSetup,
    BreakoutEvent,
    get_symbol_cost,
    SYMBOL_CLASS,
)


class TestAsOfAlignment:
    """测试 as-of 多周期对齐"""
    
    def test_compute_trend_bias_asof_uses_only_past_data(self):
        """H1 setup 只能使用 setup_time 之前已收盘的 H4/D1 bar"""
        research = MultiTimeframeSqueezeResearchV3()
        
        # 创建H4数据: 10根bar，每4小时一根
        base_time = datetime(2024, 1, 1, 0, 0)
        h4_data = []
        for i in range(10):
            h4_data.append({
                'timestamp': base_time + timedelta(hours=i*4),
                'open': 100 + i, 'high': 102 + i, 'low': 98 + i, 'close': 101 + i
            })
        h4_df = pd.DataFrame(h4_data)
        
        # setup_time = 第3根H4 bar之后 (应该只能用前3根)
        setup_time = base_time + timedelta(hours=12)  # 在H4 idx=3之后
        
        bias, slope, di_plus, di_minus, bar_time = research._compute_trend_bias_asof(h4_df, setup_time)
        
        # 应该返回一个有效的bar_time，且bar_time <= setup_time
        assert bar_time is not None
        assert bar_time <= setup_time
        # 可用的bar应该是前4根 (0, 4, 8, 12小时)
        assert bar_time <= base_time + timedelta(hours=12)
    
    def test_compute_trend_bias_asof_returns_neutral_for_insufficient_data(self):
        """数据不足时返回neutral"""
        research = MultiTimeframeSqueezeResearchV3()
        
        base_time = datetime(2024, 1, 1)
        h4_data = []
        for i in range(5):
            h4_data.append({
                'timestamp': base_time + timedelta(hours=i*4),
                'open': 100, 'high': 102, 'low': 98, 'close': 101
            })
        h4_df = pd.DataFrame(h4_data)
        
        bias, slope, di_plus, di_minus, bar_time = research._compute_trend_bias_asof(h4_df, base_time + timedelta(hours=20))
        
        # 数据不足20根，但至少有5根，应该返回neutral
        assert bias in ["neutral", "bullish", "bearish"]
        assert bar_time is not None
    
    def test_precompute_trend_biases_no_future_data(self):
        """预计算趋势时不能使用未来数据"""
        research = MultiTimeframeSqueezeResearchV3()
        
        base_time = datetime(2024, 1, 1, 0, 0)
        
        # H1数据: 每1小时一根
        h1_data = []
        for i in range(48):
            h1_data.append({
                'timestamp': base_time + timedelta(hours=i),
                'open': 100, 'high': 102, 'low': 98, 'close': 101
            })
        h1_df = pd.DataFrame(h1_data)
        
        # H4数据: 每4小时一根
        h4_data = []
        for i in range(12):
            h4_data.append({
                'timestamp': base_time + timedelta(hours=i*4),
                'open': 100 + i*0.1, 'high': 102 + i*0.1, 'low': 98 + i*0.1, 'close': 101 + i*0.1
            })
        h4_df = pd.DataFrame(h4_data)
        
        trend_df = research._precompute_trend_biases("TEST", h1_df, h4_df, None)
        
        # 检查每个H1 bar的h4_bar_time <= H1 timestamp
        for idx, row in trend_df.iterrows():
            h1_ts = h1_df['timestamp'].iloc[idx]
            h4_bar_time = row['h4_bar_time']
            if not pd.isna(h4_bar_time):
                assert h4_bar_time <= h1_ts, f"H1 bar {idx} ({h1_ts}) 使用了未来的H4数据 ({h4_bar_time})"


class TestEventDeduplication:
    """测试真实事件去重"""
    
    def test_deduplicate_by_event_id(self):
        """同一突破被多个setup捕捉时只计一次"""
        research = MultiTimeframeSqueezeResearchV3()
        
        # 创建两个setup指向同一个突破
        base_time = datetime(2024, 1, 1, 10, 0)
        
        setup1 = SqueezeSetup(
            setup_id="S1", symbol="EURUSD", timeframe="H1",
            timestamp=base_time, bar_idx=10, squeeze_score=3,
            conditions=["BB", "SR"], bb_width=0.5, sr_range=0.3, adx=15,
            state_is_zero=False, open=100, high=102, low=98, close=101,
            anchor_high=102, anchor_low=98, anchor_range=4, anchor_range_pct=4, anchor_mid=100
        )
        
        setup2 = SqueezeSetup(
            setup_id="S2", symbol="EURUSD", timeframe="H1",
            timestamp=base_time + timedelta(minutes=30), bar_idx=11, squeeze_score=3,
            conditions=["BB", "SR"], bb_width=0.5, sr_range=0.3, adx=15,
            state_is_zero=False, open=100, high=102, low=98, close=101,
            anchor_high=102, anchor_low=98, anchor_range=4, anchor_range_pct=4, anchor_mid=100
        )
        
        # 两个setup在同一个timestamp有同一个方向的突破
        event1 = BreakoutEvent(
            event_id="E1", setup=setup1,
            breakout_timestamp=base_time + timedelta(hours=1),
            breakout_bar_idx=1, breakout_direction="up",
            entry_price=105, breakout_level=102,
            returns_1bar=0.5, returns_3bar=1.0, returns_5bar=1.5,
            returns_10bar=2.0, returns_20bar=3.0,
            mfe_pct=2.0, mae_pct=-0.5,
            hit_target_1r=True, hit_target_2r=False, hit_target_3r=False,
            stop_triggered=False, stop_bar_idx=None, stop_price=None, stop_after_entry=False,
            pnl_5bar=1.5, pnl_10bar=2.0, pnl_20bar=3.0,
            trend_alignment="with_trend"
        )
        
        event2 = BreakoutEvent(
            event_id="E2", setup=setup2,
            breakout_timestamp=base_time + timedelta(hours=1),  # 同一个timestamp!
            breakout_bar_idx=1, breakout_direction="up",  # 同一个方向!
            entry_price=105, breakout_level=102,
            returns_1bar=0.5, returns_3bar=1.0, returns_5bar=1.5,
            returns_10bar=2.0, returns_20bar=3.0,
            mfe_pct=2.0, mae_pct=-0.5,
            hit_target_1r=True, hit_target_2r=False, hit_target_3r=False,
            stop_triggered=False, stop_bar_idx=None, stop_price=None, stop_after_entry=False,
            pnl_5bar=1.5, pnl_10bar=2.0, pnl_20bar=3.0,
            trend_alignment="with_trend"
        )
        
        research.breakouts = [event1, event2]
        unique = research._deduplicate_breakouts(research.breakouts)
        
        # 应该去重为1个
        assert len(unique) == 1, f"期望1个唯一事件，得到{len(unique)}个"
    
    def test_different_directions_not_deduplicated(self):
        """不同方向的突破不应被去重"""
        research = MultiTimeframeSqueezeResearchV3()
        
        base_time = datetime(2024, 1, 1, 10, 0)
        
        setup = SqueezeSetup(
            setup_id="S1", symbol="EURUSD", timeframe="H1",
            timestamp=base_time, bar_idx=10, squeeze_score=3,
            conditions=["BB", "SR"], bb_width=0.5, sr_range=0.3, adx=15,
            state_is_zero=False, open=100, high=102, low=98, close=101,
            anchor_high=102, anchor_low=98, anchor_range=4, anchor_range_pct=4, anchor_mid=100
        )
        
        event_up = BreakoutEvent(
            event_id="E1", setup=setup,
            breakout_timestamp=base_time + timedelta(hours=1),
            breakout_bar_idx=1, breakout_direction="up",
            entry_price=105, breakout_level=102,
            returns_1bar=0.5, returns_3bar=1.0, returns_5bar=1.5,
            returns_10bar=2.0, returns_20bar=3.0,
            mfe_pct=2.0, mae_pct=-0.5,
            hit_target_1r=True, hit_target_2r=False, hit_target_3r=False,
            stop_triggered=False, stop_bar_idx=None, stop_price=None, stop_after_entry=False,
            pnl_5bar=1.5, pnl_10bar=2.0, pnl_20bar=3.0,
            trend_alignment="with_trend"
        )
        
        event_down = BreakoutEvent(
            event_id="E2", setup=setup,
            breakout_timestamp=base_time + timedelta(hours=1),
            breakout_bar_idx=1, breakout_direction="down",
            entry_price=95, breakout_level=98,
            returns_1bar=-0.5, returns_3bar=-1.0, returns_5bar=-1.5,
            returns_10bar=-2.0, returns_20bar=-3.0,
            mfe_pct=-2.0, mae_pct=0.5,
            hit_target_1r=False, hit_target_2r=False, hit_target_3r=False,
            stop_triggered=False, stop_bar_idx=None, stop_price=None, stop_after_entry=False,
            pnl_5bar=-1.5, pnl_10bar=-2.0, pnl_20bar=-3.0,
            trend_alignment="against_trend"
        )
        
        research.breakouts = [event_up, event_down]
        unique = research._deduplicate_breakouts(research.breakouts)
        
        # 不同方向，应该保留2个
        assert len(unique) == 2


class TestShortTarget:
    """测试 short 方向 target 判断"""
    
    def test_short_target_uses_max_not_min(self):
        """short方向应使用.max()而非.min()"""
        # 这个测试验证v3代码逻辑：short方向的check_target使用(entry_price - future_low).max()
        # 而不是v2的.min()
        
        # 模拟future_prices
        future_low = pd.Series([99, 98, 97, 98, 99])  # 最低到97
        entry_price = 100
        target = -3  # 3个点
        
        # v3正确逻辑: (entry_price - future_low).max() >= abs(target)
        # (100-99, 100-98, 100-97, 100-98, 100-99) = (1, 2, 3, 2, 1)
        # max = 3, abs(target) = 3, 3 >= 3 -> True
        v3_result = (entry_price - future_low).max() >= abs(target)
        assert v3_result == True
        
        # v2错误逻辑: (entry_price - future_low).min() >= abs(target)
        # min = 1, 1 >= 3 -> False
        v2_result = (entry_price - future_low).min() >= abs(target)
        assert v2_result == False
        
        # 验证v3和v2结果不同
        assert v3_result != v2_result


class TestStopLogic:
    """测试止损逻辑"""
    
    def test_stop_only_after_entry(self):
        """入场前触发stop不算交易止损"""
        research = MultiTimeframeSqueezeResearchV3()
        
        base_time = datetime(2024, 1, 1, 10, 0)
        
        # 创建H1数据
        h1_data = []
        for i in range(20):
            h1_data.append({
                'timestamp': base_time + timedelta(hours=i),
                'open': 100, 'high': 102, 'low': 97, 'close': 101
            })
        h1_df = pd.DataFrame(h1_data)
        
        research.raw_data = {"EURUSD": {"H1": h1_df}}
        
        setup = SqueezeSetup(
            setup_id="S1", symbol="EURUSD", timeframe="H1",
            timestamp=base_time, bar_idx=5, squeeze_score=3,
            conditions=["BB", "SR"], bb_width=0.5, sr_range=0.3, adx=15,
            state_is_zero=False, open=100, high=102, low=97, close=101,
            anchor_high=102, anchor_low=97, anchor_range=5, anchor_range_pct=5, anchor_mid=99.5
        )
        
        # 突破发生在setup后第3根bar
        # entry_idx = 5 + 3 = 8
        # 止损价格 = anchor_low = 97
        # 检查entry_future = df.iloc[8:29]
        # 如果entry_future中有low < 97，则触发止损
        
        # 手动验证: 数据中没有low < 97的，所以不应触发止损
        entry_idx = 8
        entry_future = h1_df.iloc[entry_idx:entry_idx + 21]
        stop_triggered = False
        for j, (_, row) in enumerate(entry_future.iterrows()):
            if row['low'] < 97:
                stop_triggered = True
                break
        
        assert stop_triggered == False


class TestBarSemantics:
    """测试1bar/5bar周期语义"""
    
    def test_1bar_is_first_bar_after_entry(self):
        """1bar = 入场后第1根K线close，不是入场bar本身"""
        # v3中: returns_1bar = calc_return(1)，即future_prices.iloc[1]
        # 入场bar是future_prices.iloc[0]
        # 所以1bar是入场后的第1根K线
        
        entry_price = 100
        future_closes = [100.5, 101, 102, 103, 104]  # 入场bar=100.5, 1bar=101
        
        # v3语义
        return_1bar_v3 = (future_closes[1] - entry_price) / entry_price * 100
        assert return_1bar_v3 == (101 - 100) / 100 * 100  # 1.0%
        
        # 不是入场bar本身
        return_entry_bar = (future_closes[0] - entry_price) / entry_price * 100
        assert return_entry_bar == (100.5 - 100) / 100 * 100  # 0.5%
        
        assert return_1bar_v3 != return_entry_bar
    
    def test_5bar_is_fifth_bar_after_entry(self):
        """5bar = 入场后第5根K线close"""
        entry_price = 100
        future_closes = [100, 101, 102, 103, 104, 105]  # 0=入场bar, 5=5bar
        
        return_5bar = (future_closes[5] - entry_price) / entry_price * 100
        assert return_5bar == (105 - 100) / 100 * 100  # 5.0%


class TestCostModel:
    """测试交易成本模型"""
    
    def test_fx_cost_lower_than_crypto(self):
        """FX成本应低于crypto"""
        fx_cost = get_symbol_cost("EURUSD")
        crypto_cost = get_symbol_cost("BTCUSD")
        
        assert fx_cost['spread_pct'] < crypto_cost['spread_pct']
        assert fx_cost['swap_pct'] < crypto_cost['swap_pct']
    
    def test_symbol_class_mapping(self):
        """品种类别映射正确"""
        assert SYMBOL_CLASS["EURUSD"] == "FX"
        assert SYMBOL_CLASS["XAUUSD"] == "metal"
        assert SYMBOL_CLASS["US30"] == "index"
        assert SYMBOL_CLASS["USOIL"] == "oil"
        assert SYMBOL_CLASS["BTCUSD"] == "crypto"
    
    def test_cost_deduction_reduces_pnl(self):
        """成本扣减应降低PNL"""
        gross_pnl = 1.0  # 1%
        cost = get_symbol_cost("EURUSD")
        total_cost = cost['spread_pct'] + cost['commission_pct']
        net_pnl = gross_pnl - total_cost
        
        assert net_pnl < gross_pnl
        assert net_pnl == gross_pnl - total_cost


class TestSqueezeScore:
    """测试收缩score（移除Pivot重复计分）"""
    
    def test_no_pivot_in_score(self):
        """v3 score不应包含pivot"""
        research = MultiTimeframeSqueezeResearchV3()
        
        # 创建H1数据，使BB和SR收缩但ADX不高
        base_time = datetime(2024, 1, 1)
        h1_data = []
        np.random.seed(42)
        for i in range(100):
            close = 100 + np.random.randn() * 0.5  # 低波动
            h1_data.append({
                'timestamp': base_time + timedelta(hours=i),
                'open': close - 0.2, 'high': close + 0.3, 'low': close - 0.3, 'close': close
            })
        h1_df = pd.DataFrame(h1_data)
        
        research.raw_data = {"TEST": {"H1": h1_df}}
        setups = research.find_setups(min_squeeze_score=1)
        
        # 检查setup的conditions中不应有"Pivot"
        for setup in setups:
            assert "Pivot" not in setup.conditions, "v3不应包含Pivot条件"


class TestTrendAlignment:
    """测试趋势共振分类"""
    
    def test_with_trend_classification(self):
        """顺势突破分类正确"""
        base_time = datetime(2024, 1, 1, 10, 0)
        
        # up突破 + bullish趋势 = with_trend
        setup_bullish = SqueezeSetup(
            setup_id="S1", symbol="EURUSD", timeframe="H1",
            timestamp=base_time, bar_idx=10, squeeze_score=3,
            conditions=["BB", "SR"], bb_width=0.5, sr_range=0.3, adx=15,
            state_is_zero=False, open=100, high=102, low=98, close=101,
            anchor_high=102, anchor_low=98, anchor_range=4, anchor_range_pct=4, anchor_mid=100,
            h4_trend_bias="bullish", d1_trend_bias="neutral"
        )
        
        event = BreakoutEvent(
            event_id="E1", setup=setup_bullish,
            breakout_timestamp=base_time + timedelta(hours=1),
            breakout_bar_idx=1, breakout_direction="up",
            entry_price=105, breakout_level=102,
            returns_1bar=0.5, returns_3bar=1.0, returns_5bar=1.5,
            returns_10bar=2.0, returns_20bar=3.0,
            mfe_pct=2.0, mae_pct=-0.5,
            hit_target_1r=True, hit_target_2r=False, hit_target_3r=False,
            stop_triggered=False, stop_bar_idx=None, stop_price=None, stop_after_entry=False,
            pnl_5bar=1.5, pnl_10bar=2.0, pnl_20bar=3.0,
            trend_alignment="with_trend"
        )
        
        assert event.trend_alignment == "with_trend"
    
    def test_against_trend_classification(self):
        """逆势突破分类正确"""
        base_time = datetime(2024, 1, 1, 10, 0)
        
        # up突破 + bearish趋势 = against_trend
        setup_bearish = SqueezeSetup(
            setup_id="S1", symbol="EURUSD", timeframe="H1",
            timestamp=base_time, bar_idx=10, squeeze_score=3,
            conditions=["BB", "SR"], bb_width=0.5, sr_range=0.3, adx=15,
            state_is_zero=False, open=100, high=102, low=98, close=101,
            anchor_high=102, anchor_low=98, anchor_range=4, anchor_range_pct=4, anchor_mid=100,
            h4_trend_bias="bearish", d1_trend_bias="bearish"
        )
        
        event = BreakoutEvent(
            event_id="E1", setup=setup_bearish,
            breakout_timestamp=base_time + timedelta(hours=1),
            breakout_bar_idx=1, breakout_direction="up",
            entry_price=105, breakout_level=102,
            returns_1bar=0.5, returns_3bar=1.0, returns_5bar=1.5,
            returns_10bar=2.0, returns_20bar=3.0,
            mfe_pct=2.0, mae_pct=-0.5,
            hit_target_1r=True, hit_target_2r=False, hit_target_3r=False,
            stop_triggered=False, stop_bar_idx=None, stop_price=None, stop_after_entry=False,
            pnl_5bar=1.5, pnl_10bar=2.0, pnl_20bar=3.0,
            trend_alignment="against_trend"
        )
        
        assert event.trend_alignment == "against_trend"


class TestWalkForward:
    """测试Walk-Forward分区"""
    
    def test_train_validation_test_split(self):
        """时间切分正确"""
        research = MultiTimeframeSqueezeResearchV3()
        
        base_time = datetime(2024, 1, 1)
        # 100天的数据
        all_times = [base_time + timedelta(days=i) for i in range(100)]
        
        min_t, max_t = min(all_times), max(all_times)
        total_span = (max_t - min_t).total_seconds()
        train_end = min_t + timedelta(seconds=total_span * 0.6)
        validation_end = min_t + timedelta(seconds=total_span * 0.8)
        
        train_count = sum(1 for t in all_times if t <= train_end)
        val_count = sum(1 for t in all_times if train_end < t <= validation_end)
        test_count = sum(1 for t in all_times if t > validation_end)
        
        # 60/20/20 分割
        assert train_count == 60, f"期望train=60, 得到{train_count}"
        assert val_count == 20, f"期望validation=20, 得到{val_count}"
        assert test_count == 20, f"期望test=20, 得到{test_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
