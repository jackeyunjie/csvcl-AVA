# 收缩观测长期任务文档

> 创建时间: 2026-06-04
> 更新频率: 每日
> 目标: 基于"收缩带来扩张"交易理念，建立多周期收缩观测系统，为强化学习提供数据基础

---

## 一、任务背景

### 1.1 核心理念

**"收缩带来扩张"** —— 当市场价格波动收窄、结构压缩时，往往预示着即将出现方向性突破。在收缩确认后及时入场，具有较好的盈亏比和先验概率。

### 1.2 观测目标

1. 识别各周期同步收缩的时机
2. 统计收缩→突破的完整过程
3. 量化各收缩指标的先验概率
4. 为强化学习提供标准化训练数据

---

## 二、观测指标体系

### 2.1 布林带宽收缩 (BB Width Squeeze)

**计算公式**:
```
BB Width = (上轨 - 下轨) / 中轨
         = (MA + 2σ - (MA - 2σ)) / MA
         = 4σ / MA
```

**收缩判定**:
- 当前BB Width低于过去30天历史数据的指定分位数
- 三档阈值: 20%分位（轻度收缩）、10%分位（中度收缩）、5%分位（极度收缩）

**含义**: 价格波动收窄，K线实体变小，即将选择方向

**实现文件**: `python/analytics/squeeze_observer.py::compute_bb_width()`

---

### 2.2 枢轴收缩 (Pivot Squeeze)

**计算公式**:
```
Pivot Range = (20周期最高 - 20周期最低) / 收盘价 × 100%
```

**收缩判定**:
- 当前Pivot Range低于过去30天最低20%分位

**含义**: 支撑阻力位间距收窄，市场结构压缩

**实现文件**: `python/analytics/squeeze_observer.py::compute_pivot_range()`

---

### 2.3 ADX极端低值

**参数**: ADX(14)

**计算公式**:
```
+DM = max(0, 当前高 - 前高)
-DM = max(0, 前低 - 当前低)
TR = max(高-低, |高-前收|, |低-前收|)
+DI = 100 × SMA(+DM) / SMA(TR)
-DI = 100 × SMA(-DM) / SMA(TR)
DX = 100 × |+DI - -DI| / (+DI + -DI)
ADX = SMA(DX, 14)
```

**关注阈值**:
- **ADX < 20**: 弱趋势，市场处于盘整
- **ADX < 13**: 极弱趋势，几乎无方向
- **ADX < 9**: 极端低值，强烈预示即将突破

**实现文件**: `python/analytics/squeeze_observer.py::compute_adx()`

---

### 2.4 State = 0 状态

**编码含义**:
```
state_hex = "0"
  → base = 0 (收缩底座)
  → volatility = 0 (不活跃)
  → position = 0 (中性)
  → trend = 0 (无趋势)
```

**含义**: 完全收缩状态，无任何方向性信号，是最纯粹的收缩底座

**统计方式**: 各周期state_hex为"0"的出现频率

---

### 2.5 SR支撑阻力位间距收缩

**计算公式**:
```
SR Range = (阻力位 - 支撑位) / 收盘价 × 100%
```

**收缩判定**:
- 当前SR Range低于该周期历史阈值（基于过去30天20%分位）

**与枢轴收缩的区别**:
- 枢轴收缩使用20周期高低点
- SR收缩使用更长期的支撑阻力位（可结合ACD枢轴系统）

---

## 三、观测维度

### 3.1 分品种

覆盖全部73个交易品种:
- **股指**: US_30, US_500, US_TECH100, HK_50, CHINA_A50, GER30, JP225, UK_100, FRANCE_40, EUROPE_50, SWISS_20, ITALY_40, GERMANY_TECH30, CHINA_INTERNET
- **外汇**: EURUSD, GBPUSD, USDJPY
- **大宗商品**: XAUUSD, USOIL, SILVER, BRENT_OIL, NATURAL_GAS
- **加密货币**: BTCUSD
- **美股**: #APPLE, #MICROSOFT, #NVIDIA, #TESLA, #AMAZON, #GOOGLE, #META, #NETFLIX, #AMD, ... (共50只)

### 3.2 分周期

五个结构周期全部覆盖:
- **MN1**: 月线视角，长期结构
- **W1**: 周线视角，中期结构
- **D1**: 日线视角，短期结构
- **H4**: 4小时视角，交易结构
- **H1**: 1小时视角，入场结构

### 3.3 多指标共振

**收缩分数**: 同时满足的收缩条件数量

| 分数 | 含义 | 交易意义 |
|------|------|----------|
| 0-1 | 无收缩或轻度收缩 | 观望 |
| 2 | 中度收缩 | 关注 |
| 3+ | 多指标共振 | 高概率突破，准备入场 |

---

## 四、数据更新流程

### 4.1 每日更新步骤

```bash
# 1. 更新H1 State数据
python update_all_data.py

# 2. 生成收缩观测报告
python squeeze_report.py --obsidian

# 3. 检查数据完整性
python check_current_state.py
```

### 4.2 数据存储

- **原始数据**: `data/h1_state.duckdb`
- **分析报告**: `reports/squeeze/squeeze_report_YYYYMMDD_HHMM.md`
- **Obsidian同步**: `C:/Users/MECHREVO/Documents/Obsidian Vault/Trading/SqueezeObserver/`

---

## 五、强化学习应用

### 5.1 状态空间 (State)

```python
state = {
    # 布林带宽
    'bb_width_percentile': float,  # 当前BB Width在历史中的分位数
    'bb_squeezed_20': bool,
    'bb_squeezed_10': bool,
    'bb_squeezed_5': bool,
    
    # 枢轴
    'pivot_range_percentile': float,
    'pivot_squeezed': bool,
    
    # ADX
    'adx': float,
    'adx_lt_20': bool,
    'adx_lt_13': bool,
    'adx_lt_9': bool,
    
    # State
    'state_hex': str,
    'state_is_zero': bool,
    
    # 多周期同步
    'multi_squeeze_count': int,  # 多少周期同时收缩
    'squeeze_score': int,  # 综合收缩分数
}
```

### 5.2 动作空间 (Action)

```python
action = {
    0: '观望',      # 不操作
    1: '做多',      # 预期向上突破
    2: '做空',      # 预期向下突破
}
```

### 5.3 奖励函数 (Reward)

```python
def reward(squeeze_state, action, future_returns):
    """
    奖励设计原则:
    1. 方向正确: +收益率
    2. 方向错误: -收益率
    3. 考虑最大回撤: 回撤大则惩罚
    4. 持仓时间: 鼓励快速获利
    """
    if action == 0:  # 观望
        return 0
    
    returns = future_returns['returns_5bar']
    max_dd = future_returns['max_drawdown']
    
    if action == 1:  # 做多
        r = returns
    else:  # 做空
        r = -returns
    
    # 回撤惩罚
    dd_penalty = max_dd * 0.5
    
    return r - dd_penalty
```

### 5.4 样本格式

```python
{
    'symbol': 'EURUSD',
    'timeframe': 'H1',
    'squeeze_timestamp': '2026-06-01 10:00',
    'breakout_timestamp': '2026-06-01 11:00',
    'breakout_direction': 'up',
    'state': {...},  # 收缩时刻完整状态
    'action': 1,  # 做多
    'reward': 0.35,  # 5根K线后收益0.35%
    'next_state': {...},  # 突破后状态
    'done': False,  # 是否结束
}
```

---

## 六、报告解读指南

### 6.1 当前市场收缩状态表

| 列 | 含义 |
|----|------|
| BB收缩20 | 布林带宽低于20%分位 |
| 枢轴收缩 | 枢轴范围低于20%分位 |
| ADX | 当前ADX值 |
| ADX<20/13/9 | ADX低于各阈值 |
| State=0 | state_hex是否为0 |
| 收缩分数 | 同时满足的条件数 |
| 条件 | 具体满足的收缩条件 |

### 6.2 交易机会识别

**高概率突破信号**:
1. 收缩分数 ≥ 3
2. 多周期同步收缩（如D1+H4+H1同时收缩）
3. ADX < 9（极端低值）
4. State=0 + BB收缩 + 枢轴收缩

**入场时机**:
- 收缩确认后，等待第一根突破K线收盘
- 突破方向由 State_hex 的 trend/position 组件判断
- 止损设在收缩区间外

---

## 七、长期优化方向

### 7.1 指标扩展

- [ ] 加入成交量收缩指标（Volume Squeeze）
- [ ] 加入波动率指数（VIX类指标）
- [ ] 加入市场情绪指标
- [ ] 加入相关性矩阵（跨品种收缩同步性）

### 7.2 模型优化

- [ ] 训练LSTM预测突破方向
- [ ] 强化学习策略优化（PPO/DQN）
- [ ] 多智能体协作（分品种分周期独立决策）

### 7.3 实盘集成

- [ ] 将收缩信号接入AI_Trading_Bridge.mq5
- [ ] 实现自动突破确认检测
- [ ] 集成风控模块（止损/止盈自动计算）

---

## 八、相关文件

| 文件 | 功能 |
|------|------|
| `python/analytics/squeeze_observer.py` | 收缩观测核心模块 |
| `squeeze_report.py` | 报告生成器 |
| `update_all_data.py` | 数据更新脚本 |
| `python/ai_engine/kvb_state_hex_engine.py` | State计算引擎 |
| `docs/squeeze_observation_task.md` | 本文档 |

---

## 九、注意事项

1. **数据质量**: 确保MT5数据完整，特别是个股品种
2. **计算性能**: 全品种分析较耗时，建议增量更新
3. **阈值调优**: 根据回测结果动态调整收缩阈值
4. **过拟合风险**: 强化学习需在多个品种上验证泛化能力

---

> 最后更新: 2026-06-04
> 下次更新: 每日数据更新后自动生成
