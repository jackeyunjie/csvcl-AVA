# D1/H1/M15 周期视角评分 + SQX 指标共振交易框架

Date: 2026-06-10
Status: 研究框架 / 非实盘

## 核心哲学

**大周期定方向，中周期找位置，小周期找时机；State 做状态体检，SQX 做策略证据**

- D1：决定交易方向（做多头/做空头/观望）
- H1：确定支撑阻力位置（枢轴结构）
- M15：精确入场时机（RSIOMA信号）
- State Hex：各周期视角下的状态体检码，不是线性强弱分数，也不是单独的交易许可
- 周期视角评分：把 D1/H1/M15 Agent 输出、D1 Risk Officer、SQX 指标模块合成为策略评分
- SQX 指标模块：提供可交易证据，包括 ACD、Pivot、Kaufman Bands、RSIOMA、SR PercentRank、ADX、BB Width 等

---

## 第一层：D1 视角 — 趋势方向与结构

### 1.1 D1 分析要素

| 指标 | 作用 | 判断标准 |
|---|---|---|
| MA144/169/200 | 长期趋势结构 | 价格 vs MA 位置关系 |
| D1 State Hex | D1 视角状态体检码 | base/trend/position/volatility 组件组合 |
| D1 Risk Direction | 交易方向许可 | 由 MA 结构、State 方向语境、D1 Risk Officer 综合输出 long/short/neutral |
| D1 ADX | 趋势强度 | >25=趋势, <20=震荡 |
| D1 BB Width | 波动率 | 收缩=即将突破, 扩张=趋势运行 |

### 1.2 D1 趋势判定矩阵

| MA排列 | State 组件 | ADX | 趋势判定 | 交易许可 |
|---|---|---|---|---|
| 价格>MA144>169>200 | position/trend 为多向语境 | >25 | 强多头趋势 | 只做多 |
| 价格>MA144>169>200 | State 未充分确认但 MA 偏多 | >20 | 弱多头趋势 | 优先做多 |
| MA缠绕,价格居中 | State 无方向语境或冲突 | <20 | 震荡 | 观望或双向轻仓 |
| 价格<MA144<169<200 | position/trend 为空向语境 | >20 | 弱空头趋势 | 优先做空 |
| 价格<MA144<169<200 | State 与 MA 均为空向确认 | >25 | 强空头趋势 | 只做空 |

### 1.3 D1 关键规则

```
硬门槛：D1 Risk Officer
├── D1 Risk Direction = long → 禁止做空
├── D1 Risk Direction = short → 禁止做多
├── D1 Risk Direction = neutral → 观望或仅允许非方向性动作
├── State Hex 只能解释状态组件，不能单独决定方向
└── SQX 模块只做加权证据，不得绕过 D1 Risk Officer
```

### 1.4 D1 视角输出

```python
class D1View:
    def analyze(self, symbol):
        return {
            'trend_direction': 'long',      # long/short/neutral
            'trend_strength': 'strong',      # strong/moderate/weak
            'ma_structure': 'bullish',       # bullish/bearish/mixed
            'adx_value': 28.5,
            'adx_tier': 'trend',            # trend/transition/range
            'bb_width_status': 'contracting', # contracting/expanding/normal
            'trade_permission': 'long_only',  # long_only/short_only/both/none
            'd1_hex': '8',
            'confidence': 0.85
        }
```

---

## 第二层：H1 视角 — 支撑阻力与动量

### 2.1 H1 分析要素

| 指标 | 作用 | 信号类型 |
|---|---|---|
| 1D/3D/6D Pivot | 支撑阻力定位 | 价格相对Pivot位置 |
| RSIOMA | 动量确认 | 金叉/死叉/极端值 |
| Kaufman Bands | 自适应波动率 | 带宽收缩/扩张 |
| H1 State Hex | H1 视角状态体检码 | 与 D1 Risk、H1 Pivot/RSIOMA 共同解释 |
| H1 ADX | 中周期趋势强度 | >20=有方向 |
| ACD Opening Range | 日内关键区 | A-up/A-down/C-up/C-down |

### 2.2 H1 枢轴结构分析

```
6D Pivot Range: [6D_Bottom, 6D_Top]  ← 大周期边界
        ↑
3D Pivot Range: [3D_Bottom, 3D_Top]  ← 中周期边界
        ↑
1D Pivot Range: [1D_Bottom, 1D_Top]  ← 小周期边界
        ↑
    当前价格
```

**位置判定**：
- 价格 > 6D_Top → 超强多头，突破大周期阻力
- 3D_Top < 价格 < 6D_Top → 多头，测试大周期阻力
- 1D_Top < 价格 < 3D_Top → 弱多头，测试中周期阻力
- 1D_Bottom < 价格 < 1D_Top → 震荡，在日内区间内
- 3D_Bottom < 价格 < 1D_Bottom → 弱空头，测试中周期支撑
- 1D_Bottom < 价格 < 3D_Bottom → 空头，测试大周期支撑
- 价格 < 6D_Bottom → 超强空头，跌破大周期支撑

### 2.3 H1 RSIOMA 动量信号

| RSIOMA 状态 | 值范围 | H1 信号 | 与枢轴结合 |
|---|---|---|---|
| 超卖区反弹 | <20 → 上升 | 多头触发 | + 价格 near 1D/3D Bottom = 强多 |
| 金叉 | 上穿 MA | 多头确认 | + 突破 1D Top = 入场 |
| 多头趋势 | 50-70 | 趋势延续 | + 价格 > 3D Top = 持仓 |
| 强多头 | >70 | 超买警示 | + 价格 near 6D Top = 止盈 |
| 超买回落 | >80 → 下降 | 空头触发 | + 价格 near 1D/3D Top = 强空 |
| 死叉 | 下穿 MA | 空头确认 | + 跌破 1D Bottom = 入场 |
| 空头趋势 | 30-50 | 趋势延续 | + 价格 < 3D Bottom = 持仓 |
| 强空头 | <30 | 超卖警示 | + 价格 near 6D Bottom = 止盈 |

### 2.4 H1 与 D1 方向一致性检查

```
H1方向 vs D1方向:
├── 同向 → 高置信度，标准仓位
│   ├── D1=long, H1=long → 多头共振
│   └── D1=short, H1=short → 空头共振
├── 反向 → 低置信度，减仓或观望
│   ├── D1=long, H1=short → 反弹/回调，不逆D1
│   └── D1=short, H1=long → 反弹/回调，不逆D1
└── H1=neutral → 等待H1方向确认
```

### 2.5 H1 视角输出

```python
class H1View:
    def analyze(self, symbol):
        return {
            'pivot_context': {
                'position': 'near_1d_bottom',  # relative to pivots
                '1d_contraction': True,
                '3d_contraction': False,
                '6d_contraction': True,
            },
            'rsioma': {
                'value': 18.5,
                'trend': 'rising',
                'signal': 'oversold_bounce',  # oversold_bounce/golden_cross/dead_cross/overbought_fall
                'ma_cross': 'golden_cross_pending',
            },
            'kaufman': {
                'bandwidth_status': 'contracting',
                'price_position': 'near_lower_band',
            },
            'h1_hex': '6',
            'h1_direction': 'long',
            'd1_alignment': 'aligned',  # aligned/against/neutral
            'confidence': 0.75
        }
```

---

## 第三层：M15 视角 — 精确入场时机

### 3.1 M15 分析要素

| 指标 | 作用 | 精确度 |
|---|---|---|
| M15 RSIOMA | 精确入场点 | 金叉/死叉确认 |
| M15 ACD | 开盘区间突破 | A-up/A-down突破 |
| M15 State Hex | M15 视角状态体检码 | 与 H1 位置、M15 触发信号共同解释 |
| M15 ADX | 短周期动能 | >15=有微趋势 |
| M15 BB Width | 微观波动率 | 收缩=即将微突破 |
| SR Breakout | 支撑阻力突破 | 确认方向 |

### 3.2 M15 入场信号分级

**A级信号（最强，重仓）**：
- D1=long, H1=long, M15=long
- M15 RSIOMA 金叉 + 价格突破 ACD A-up
- 1D Pivot 收缩后向上突破

**B级信号（中等，标准仓）**：
- D1=long, H1=long, M15=neutral→long
- M15 RSIOMA 超卖反弹 + 价格 near 1D Bottom
- 3D Pivot 支撑确认

**C级信号（较弱，轻仓）**：
- D1=long, H1=neutral, M15=long
- M15 RSIOMA 金叉但 H1 方向不明
- 需等待H1确认

**禁止交易**：
- D1=long, M15=short（逆大周期）
- M15 RSIOMA 信号与 H1 枢轴突破方向相反

### 3.3 M15 精确入场条件

**多头精确入场（需全部满足）**：
1. D1 Risk 允许 long
2. H1 RSIOMA 处于超卖区或刚金叉
3. H1 价格 near 1D/3D Pivot Bottom
4. M15 RSIOMA 金叉（Up/DnXsig = -8）
5. M15 价格突破 ACD A-up 或 1D Pivot Top
6. M15 ADX > 15（确认有动能）

**空头精确入场（需全部满足）**：
1. D1 Risk 允许 short
2. H1 RSIOMA 处于超买区或刚死叉
3. H1 价格 near 1D/3D Pivot Top
4. M15 RSIOMA 死叉（Up/DnXsig = 8）
5. M15 价格跌破 ACD A-down 或 1D Pivot Bottom
6. M15 ADX > 15（确认有动能）

### 3.4 M15 视角输出

```python
class M15View:
    def analyze(self, symbol):
        return {
            'rsioma': {
                'value': 22.3,
                'signal': 'golden_cross',  # golden_cross/dead_cross
                'bars_since_cross': 2,
            },
            'acd': {
                'or_high': 1.0850,
                'or_low': 1.0840,
                'a_up': 1.0855,
                'a_down': 1.0835,
                'breakout': 'a_up',  # a_up/a_down/none
            },
            'm15_hex': '4',
            'm15_direction': 'long',
            'sr_breakout': True,
            'breakout_direction': 'up',
            'adx': 18.5,
            'confidence': 0.80
        }
```

---

## 第四层：三周期视角评分 + SQX 共振评分

### 4.1 共振矩阵

| D1 Risk | H1 位置/动量 | M15 触发 | 共振等级 | 仓位建议 | 置信度 |
|---|---|---|---|---|---|
| long | 多头位置确认 | 多头触发确认 | 完美共振 | 100%仓位 | 90-100% |
| long | 多头位置确认 | 等待 M15 触发 | 强共振 | 80%仓位 | 75-89% |
| long | 中性位置 | 多头触发确认 | 中等共振 | 60%仓位 | 60-74% |
| long | 多头位置确认 | 空头触发 | 冲突 | 观望 | <50% |
| long | 空头位置/动量 | any | 逆周期 | 禁止或等待回调完成 | 0% |
| neutral | 多头位置确认 | 多头触发确认 | 弱共振 | 50%仓位 | 55-69% |
| neutral | 中性位置 | 多头触发确认 | 微共振 | 30%仓位 | 40-54% |
| short | 空头位置确认 | 空头触发确认 | 完美共振 | 100%仓位 | 90-100% |
| short | 空头位置确认 | 等待 M15 触发 | 强共振 | 80%仓位 | 75-89% |
| short | 中性位置 | 空头触发确认 | 中等共振 | 60%仓位 | 60-74% |

### 4.2 共振评分计算

```python
def calculate_resonance(d1_view, h1_view, m15_view, sqx_view):
    """
    三周期视角评分 + SQX 指标证据算法
    """
    score = 0
    max_score = 100
    
    # D1 Risk 权重 35%：方向许可来自 D1 Risk Officer，不直接来自 state_hex 数值
    if d1_view['trade_permission'] == 'long_only':
        if d1_view['trend_strength'] == 'strong':
            score += 35
        else:
            score += 25
    elif d1_view['trade_permission'] == 'short_only':
        if d1_view['trend_strength'] == 'strong':
            score += 35
        else:
            score += 25
    elif d1_view['trade_permission'] == 'both':
        score += 15
    else:
        score += 0
    
    # H1 位置/动量权重 30%
    if h1_view['d1_alignment'] == 'aligned':
        if h1_view['rsioma']['signal'] in ['oversold_bounce', 'golden_cross']:
            score += 30
        elif h1_view['rsioma']['signal'] in ['overbought_fall', 'dead_cross']:
            score += 30
        else:
            score += 20
    elif h1_view['d1_alignment'] == 'neutral':
        score += 10
    else:
        score += 0
    
    # M15 触发权重 20%
    if m15_view['rsioma']['signal'] == 'golden_cross':
        if m15_view['breakout_direction'] == 'up':
            score += 20
        else:
            score += 12
    elif m15_view['rsioma']['signal'] == 'dead_cross':
        if m15_view['breakout_direction'] == 'down':
            score += 20
        else:
            score += 12
    else:
        score += 8
    
    # SQX 指标模块权重 15%
    if sqx_view['pivot_contraction'] and sqx_view['sr_breakout']:
        score += 8
    if sqx_view['kaufman_band_signal'] == 'aligned':
        score += 4
    if sqx_view['adx_tier'] in ['trend', 'micro_trend']:
        score += 3
    
    return min(score, max_score)
```

### 4.3 交易决策矩阵

| 共振评分 | 等级 | 仓位比例 | 止损距离 | 止盈目标 |
|---|---|---|---|---|
| 90-100 | 完美 | 100% | 1x ATR | 3:1 盈亏比 |
| 75-89 | 强 | 80% | 1.5x ATR | 2.5:1 盈亏比 |
| 60-74 | 中等 | 60% | 2x ATR | 2:1 盈亏比 |
| 45-59 | 弱 | 40% | 2.5x ATR | 1.5:1 盈亏比 |
| <45 | 观望 | 0% | - | - |

---

## 第五层：完整交易流程

### 5.1 交易前分析流程

```
Step 1: D1 分析（每日开盘前）
├── 读取 D1 State Hex
├── 检查 MA144/169/200 结构
├── 确定 D1 Risk Direction
└── 输出：trade_permission

Step 2: H1 分析（每小时或关键位置）
├── 读取 H1 State Hex
├── 分析 1D/3D/6D Pivot 结构
├── 读取 RSIOMA 值和趋势
├── 检查与 D1 方向一致性
└── 输出：h1_direction, pivot_context

Step 3: M15 分析（入场前）
├── 读取 M15 State Hex
├── 读取 M15 RSIOMA 信号
├── 检查 ACD 开盘区间突破
├── 确认 ADX > 15
└── 输出：entry_signal

Step 4: 共振评分
├── 计算三周期共振分数
├── 确定仓位比例
└── 输出：trade_decision
```

### 5.2 入场执行流程

```
多头入场检查清单：
□ D1 Risk 允许 long
□ H1 价格 near 1D/3D Pivot Bottom 或突破 1D Top
□ H1 RSIOMA < 30 或刚金叉
□ M15 RSIOMA 金叉确认
□ M15 价格突破 A-up 或 1D Top
□ M15 ADX > 15
□ 共振评分 >= 60

空头入场检查清单：
□ D1 Risk 允许 short
□ H1 价格 near 1D/3D Pivot Top 或跌破 1D Bottom
□ H1 RSIOMA > 70 或刚死叉
□ M15 RSIOMA 死叉确认
□ M15 价格跌破 A-down 或 1D Bottom
□ M15 ADX > 15
□ 共振评分 >= 60
```

### 5.3 持仓管理流程

```
持仓中监控（每15分钟）：
├── M15 RSIOMA 是否反向交叉？
│   ├── 是 → 检查 H1 方向是否改变
│   │   ├── H1 也反向 → 平仓
│   │   └── H1 未变 → 减仓50%
│   └── 否 → 继续持仓
├── 价格是否到达 Pivot 目标位？
│   ├── 到达 1D Top/Bottom → 减仓30%
│   ├── 到达 3D Top/Bottom → 减仓50%
│   └── 到达 6D Top/Bottom → 平仓80%
├── D1 Risk Direction 是否改变？
│   └── 是 → 立即平仓
└── 止损是否触发？
    └── 是 → 平仓
```

### 5.4 出场流程

```
止盈出场：
├── 第一目标（1D Pivot边界）→ 减仓30%，移动止损至成本
├── 第二目标（3D Pivot边界）→ 再减仓30%
├── 第三目标（6D Pivot边界）→ 平仓剩余
└── 追踪止损：价格每突破一个Pivot，止损上移一级

止损出场：
├── 初始止损：入场价 ± (1-2) x ATR
├── 时间止损：4小时未按预期移动 → 平仓
├── D1方向反转 → 立即平仓
└── 连续3笔亏损 → 暂停24小时
```

---

## 第六层：多周期 Agent 架构

### 6.1 Agent 分工

```
D1 Agent（趋势分析师）
├── 输入：D1 K线, MA144/169/200, D1 State Hex
├── 输出：trend_direction, trade_permission, confidence
├── 更新频率：每日一次（纽约收盘后）
└── 职责：决定交易大方向

H1 Agent（位置分析师）
├── 输入：H1 K线, 1D/3D/6D Pivot, H1 RSIOMA, H1 State Hex
├── 输出：pivot_context, h1_direction, entry_zone
├── 更新频率：每小时或价格到达关键位
└── 职责：确定入场区域和支撑阻力

M15 Agent（时机分析师）
├── 输入：M15 K线, M15 RSIOMA, M15 ACD, M15 State Hex
├── 输出：entry_signal, exact_price, stop_loss, take_profit
├── 更新频率：每15分钟或信号触发
└── 职责：精确入场点和风控参数

Resonance Agent（共振评分师）
├── 输入：D1/H1/M15 Agent 输出
├── 输出：resonance_score, position_size, risk_amount
├── 更新频率：每次分析周期
└── 职责：综合评分和仓位管理
```

### 6.2 Agent 通信协议

```json
{
  "d1_view": {
    "symbol": "EURUSD",
    "timestamp": "2026-06-10T00:00:00Z",
    "trend_direction": "long",
    "trade_permission": "long_only",
    "confidence": 0.85
  },
  "h1_view": {
    "symbol": "EURUSD",
    "timestamp": "2026-06-10T16:00:00Z",
    "h1_direction": "long",
    "pivot_context": {
      "position": "near_1d_bottom",
      "1d_contraction": true
    },
    "rsioma_signal": "oversold_bounce",
    "confidence": 0.75
  },
  "m15_view": {
    "symbol": "EURUSD",
    "timestamp": "2026-06-10T16:15:00Z",
    "m15_direction": "long",
    "rsioma_signal": "golden_cross",
    "breakout": "a_up",
    "confidence": 0.80
  },
  "resonance": {
    "score": 95,
    "grade": "perfect",
    "position_size_pct": 100,
    "recommendation": "enter_long"
  }
}
```

---

## 第七层：与现有系统集成

### 7.1 与 State Hex 系统整合

```python
class MultiTimeframeAnalyzer:
    def __init__(self, symbol):
        self.symbol = symbol
        self.d1_officer = D1RiskOfficer()
        self.state_db = StateDatabase()
    
    def analyze(self):
        # D1 视角
        d1_hex = self.state_db.get_latest_hex(symbol, 'D1')
        d1_view = self.analyze_d1(d1_hex)
        
        # H1 视角
        h1_hex = self.state_db.get_latest_hex(symbol, 'H1')
        h1_view = self.analyze_h1(h1_hex, d1_view)
        
        # M15 视角
        m15_hex = self.state_db.get_latest_hex(symbol, 'M15')
        m15_view = self.analyze_m15(m15_hex, h1_view)
        
        # SQX 指标模块
        sqx_view = self.analyze_sqx_indicators(d1_view, h1_view, m15_view)
        
        # 共振评分
        resonance = self.calculate_resonance(d1_view, h1_view, m15_view, sqx_view)
        
        return {
            'd1': d1_view,
            'h1': h1_view,
            'm15': m15_view,
            'sqx': sqx_view,
            'resonance': resonance
        }
```

### 7.2 与 D1 Risk Officer 整合

```python
def gate_trade_signal(self, signal, d1_hex):
    """
    D1 Risk Officer 作为最终门槛
    """
    decision = self.d1_officer.assess_signal(signal, d1_hex)
    
    if not decision.allowed:
        return {
            'allowed': False,
            'reason': decision.reason,
            'action': 'BLOCKED'
        }
    
    # 通过 D1 门槛后，检查共振评分
    if self.resonance_score < 60:
        return {
            'allowed': False,
            'reason': f'Resonance too low: {self.resonance_score}',
            'action': 'WAIT'
        }
    
    return {
        'allowed': True,
        'reason': 'All conditions met',
        'action': 'ENTER',
        'position_size': self.calculate_position_size()
    }
```

---

## 第八层：实战示例

### 8.1 示例：EURUSD 多头完美共振

**D1 视角（2026-06-10）**：
- D1 Hex = C/E/F 一类多向语境状态，或 D1 Hex = 8 但 MA/Risk Officer 另行确认多头
- 注意：D1 Hex = 8 本身只表示非收缩/扩张底座，不能单独解释为强多头
- MA144 > MA169 > MA200，价格在MA上方
- ADX = 28（趋势）
- D1 Risk: long_only
- 置信度：85%

**H1 视角（16:00）**：
- H1 Hex = 6（弱多头）
- 1D Pivot 收缩（alert_1s = 2）
- 3D Pivot 收缩（alert_3s = 3）
- RSIOMA = 25（接近超卖，开始上升）
- 价格 near 1D Pivot Bottom
- 与 D1 方向一致
- 置信度：75%

**M15 视角（16:15）**：
- M15 Hex = 4（多头）
- RSIOMA 金叉（Up/DnXsig = -8）
- 价格突破 ACD A-up
- ADX = 19（有动能）
- 置信度：80%

**共振评分**：
- D1 Risk long_only + 趋势强：35分
- H1 一致 + 超卖反弹：30分
- M15 金叉 + 突破：20分
- SQX Pivot 收缩 + SR 突破 + Kaufman/ADX 对齐：15分
- **总分：100分（完美共振）**

**交易决策**：
- 方向：做多
- 仓位：100%
- 入场：1.0845（A-up突破点）
- 止损：1.0830（1D Bottom下方15点）
- 止盈1：1.0860（1D Top）
- 止盈2：1.0880（3D Top）
- 止盈3：1.0900（6D Top）

### 8.2 示例：XAUUSD 空头冲突（不交易）

**D1 视角**：
- D1 Risk: short_only
- D1 Hex = -C/-E/-F 一类空向语境状态，或 D1 Hex 仅作为状态组件输入

**H1 视角**：
- H1 Hex = 6（弱多头）
- RSIOMA 金叉
- 与 D1 方向冲突

**M15 视角**：
- M15 Hex = 4（多头）
- RSIOMA 金叉

**共振评分**：
- D1 强空头但信号是多头：0分（方向冲突）
- **决策：BLOCKED - 禁止逆D1交易**

---

## 第九层：风险控制

### 9.1 多层风控体系

```
第一层：D1 Risk Officer（方向风控）
├── 禁止逆D1方向交易
├── D1方向变化时平仓
└── 每日开盘前更新

第二层：共振评分（仓位风控）
├── 评分<60：不交易
├── 评分60-74：60%仓位
├── 评分75-89：80%仓位
└── 评分90-100：100%仓位

第三层：Pivot 止损（技术风控）
├── 初始止损：1D Pivot边界 ± ATR
├── 移动止损：随Pivot突破上移
└── 时间止损：4小时未动平仓

第四层：资金风控（账户风控）
├── 单笔亏损 ≤ 账户2%
├── 连续3亏暂停24小时
├── 日亏损 ≥ 5% 当日停止
└── 周亏损 ≥ 10% 当周停止
```

### 9.2 特殊情况处理

**数据缺失**：
- M15 数据缺失 → 降级为 H1 信号，仓位减半
- H1 数据缺失 → 只使用 D1 + M15，仓位减至40%
- D1 数据缺失 → 禁止交易

**极端行情**：
- 价格跳空越过止损 → 市价平仓
- 连续单边行情 → 追踪止损保护利润
- 重大新闻事件 → 提前平仓，事件后重新分析

---

## 第十层：监控与复盘

### 10.1 实时监控指标

| 指标 | 频率 | 阈值 | 动作 |
|---|---|---|---|
| D1 Risk Direction | 每日 | 变化 | 平仓逆势头寸 |
| 共振评分 | 每15分钟 | <60 | 减仓或平仓 |
| RSIOMA 交叉 | 实时 | 反向交叉 | 检查是否平仓 |
| Pivot 突破 | 实时 | 反向突破 | 移动止损 |
| 账户回撤 | 实时 | >5%日/10%周 | 停止交易 |

### 10.2 每日复盘清单

- [ ] D1 方向判断是否正确？
- [ ] H1 枢轴定位是否准确？
- [ ] M15 入场时机是否最优？
- [ ] 共振评分与实际结果是否一致？
- [ ] 止损止盈设置是否合理？
- [ ] 仓位管理是否执行到位？

### 10.3 每周优化

- 统计各周期信号胜率
- 优化共振评分权重
- 调整 Pivot 参数（如需要）
- 更新品种特性参数

---

## 参考文件

- `MT5_AI_Trading/docs/RSIOMA_ACD_PIVOT_TRADING_FRAMEWORK.md`
- `MT5_AI_Trading/python/ai_engine/d1_risk_officer.py`
- `MT5_AI_Trading/skills/hermass-mt5-state/references/MT5_ACD_KAUFMAN_INDICATORS.md`
- `MT5_AI_Trading/docs/HERMASS_MT5_STATE_RUNBOOK_20260609.md`
