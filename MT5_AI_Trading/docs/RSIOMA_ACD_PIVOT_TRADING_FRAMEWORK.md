# RSIOMA + ACD 1D/3D/6D 枢轴交易框架

Date: 2026-06-10
Status: 研究框架 / 非实盘

## 1. RSIOMA_v2HHLSX 核心信号解析

### 1.1 指标架构

```
价格 → EMA(14) → RSI → EMA(RSI, 21) → 信号判断
```

### 1.2 关键阈值

| 阈值 | 值 | 含义 |
|---|---|---|
| MajorTrend | 50 | 多空分界线 |
| MainTrendLong | 70 | 主趋势多头确认 |
| MainTrendShort | 30 | 主趋势空头确认 |
| BuyTrigger | 80 | 超买/买入触发 |
| SellTrigger | 20 | 超卖/卖出触发 |

### 1.3 信号输出

| Buffer | 信号值 | 含义 |
|---|---|---|
| TrendUp | 6 | RSI > 50，多头趋势 |
| TrendUp | 12 | RSI > 70，强多头趋势 |
| TrendDn | -6 | RSI < 50，空头趋势 |
| TrendDn | -12 | RSI < 30，强空头趋势 |
| BuyTrigger | 5 | RSI 从 ≤20 反弹 |
| BuyTrigger | -3 | RSI < 20 且上升 |
| SellTrigger | -5 | RSI 从 ≥80 回落 |
| SellTrigger | 4 | RSI > 80 且下降 |
| Up/DnXsig | -8 | RSIOMA 上穿 MA（金叉） |
| Up/DnXsig | 8 | RSIOMA 下穿 MA（死叉） |

### 1.4 核心交易信号

**多头入场信号（需全部满足）**：
1. RSIOMA < 20（超卖区）
2. RSIOMA 开始上升（BuyTrigger = -3 或 5）
3. RSIOMA 上穿 MA（Up/DnXsig = -8，金叉）

**空头入场信号（需全部满足）**：
1. RSIOMA > 80（超买区）
2. RSIOMA 开始下降（SellTrigger = 4 或 -5）
3. RSIOMA 下穿 MA（Up/DnXsig = 8，死叉）

**趋势确认信号**：
- 强多头：RSIOMA > 70 且 TrendUp = 12
- 强空头：RSIOMA < 30 且 TrendDn = -12

---

## 2. ACD 1D/3D/6D 枢轴系统

### 2.1 枢轴计算

| 周期 | 计算方式 | 用途 |
|---|---|---|
| 1D Pivot | (H + L + C) / 3 | 日内支撑阻力 |
| 3D Pivot | rolling 3日 max(H), min(L), C | 短期支撑阻力 |
| 6D Pivot | rolling 6日 max(H), min(L), C | 中期支撑阻力 |

### 2.2 枢轴收缩判定

```
收缩条件：当前 width < 前31个窗口的某个分位值
- alert_1s = 1（1日收缩等级）
- alert_3s = 2（3日收缩等级）
- alert_6s = 3（6日收缩等级）
- alert_hs = 8（历史收缩等级）
```

### 2.3 枢轴突破方向

- 价格突破 Pivot Range Top → 多头突破
- 价格跌破 Pivot Range Bottom → 空头突破
- 价格在 Pivot Range 内 → 震荡/收缩

---

## 3. RSIOMA + 枢轴整合交易规则

### 3.1 交易层级架构

```
Layer 1: D1 Risk Officer（硬门槛）
    ↓ 必须通过
Layer 2: 枢轴结构（支撑阻力定位）
    ↓ 确认位置
Layer 3: RSIOMA 信号（入场时机）
    ↓ 触发执行
Layer 4: 风控（止损止盈）
```

### 3.2 多头交易规则

**前提条件（必须全部满足）**：
1. D1 Risk Officer 允许多头（D1 direction = long 或 neutral）
2. 价格位于 1D/3D/6D Pivot Range Bottom 附近或上方

**入场信号（RSIOMA 确认）**：
1. RSIOMA < 30（超卖或接近超卖）
2. RSIOMA 上穿 MA（金叉，Up/DnXsig = -8）
3. 或 RSIOMA 从 <20 反弹（BuyTrigger = 5）

**枢轴确认（增强信号）**：
- 1D Pivot 收缩后向上突破 → 强信号
- 3D Pivot 收缩后向上突破 → 中期趋势确认
- 6D Pivot 收缩后向上突破 → 大周期趋势确认

**止损设置**：
- 初始止损：1D Pivot Range Bottom 下方 1-2 ATR
- 移动止损：价格突破 3D Pivot Top 后，止损上移至 1D Pivot Bottom

**止盈目标**：
- 第一目标：1D Pivot Range Top
- 第二目标：3D Pivot Range Top
- 第三目标：6D Pivot Range Top

### 3.3 空头交易规则

**前提条件（必须全部满足）**：
1. D1 Risk Officer 允许空头（D1 direction = short 或 neutral）
2. 价格位于 1D/3D/6D Pivot Range Top 附近或下方

**入场信号（RSIOMA 确认）**：
1. RSIOMA > 70（超买或接近超买）
2. RSIOMA 下穿 MA（死叉，Up/DnXsig = 8）
3. 或 RSIOMA 从 >80 回落（SellTrigger = -5）

**枢轴确认（增强信号）**：
- 1D Pivot 收缩后向下突破 → 强信号
- 3D Pivot 收缩后向下突破 → 中期趋势确认
- 6D Pivot 收缩后向下突破 → 大周期趋势确认

**止损设置**：
- 初始止损：1D Pivot Range Top 上方 1-2 ATR
- 移动止损：价格跌破 3D Pivot Bottom 后，止损下移至 1D Pivot Top

**止盈目标**：
- 第一目标：1D Pivot Range Bottom
- 第二目标：3D Pivot Range Bottom
- 第三目标：6D Pivot Range Bottom

### 3.4 多周期共振评分

| 周期 | 多头共振条件 | 空头共振条件 | 权重 |
|---|---|---|---|
| D1 | D1 Risk 允许 long | D1 Risk 允许 short | 40% |
| 6D Pivot | 价格 > 6D Pivot | 价格 < 6D Pivot | 20% |
| 3D Pivot | 价格 > 3D Pivot | 价格 < 3D Pivot | 20% |
| RSIOMA | 金叉 + 超卖反弹 | 死叉 + 超买回落 | 20% |

**评分标准**：
- 80-100%：强信号，可考虑重仓
- 60-79%：中等信号，标准仓位
- 40-59%：弱信号，轻仓或观望
- <40%：不交易

---

## 4. 与 State Hex 五元组整合

### 4.1 State Hex 作为趋势背景

| State Hex | D1 方向 | RSIOMA 策略 |
|---|---|---|
| 8, E, F | 强多头 | 只做多，RSIOMA 金叉入场 |
| 6, 4, 2 | 弱多头 | 优先做多，RSIOMA 超卖反弹 |
| 0, C | 中性 | 双向，RSIOMA 极端值反转 |
| -2, -4, -6 | 弱空头 | 优先做空，RSIOMA 超买回落 |
| -8, -E, -F | 强空头 | 只做空，RSIOMA 死叉入场 |

### 4.2 入场过滤规则

```python
def can_enter_long(d1_hex, rsioma_signal, pivot_context):
    """多头入场判断"""
    officer = D1RiskOfficer()
    decision = officer.assess(d1_hex, "BUY", "H1")
    
    if not decision.allowed:
        return False, f"D1 blocked: {decision.reason}"
    
    if not rsioma_signal.is_oversold_bounce:
        return False, "RSIOMA not in oversold bounce"
    
    if not pivot_context.price_near_bottom:
        return False, "Price not near pivot bottom"
    
    return True, "All conditions met"

def can_enter_short(d1_hex, rsioma_signal, pivot_context):
    """空头入场判断"""
    officer = D1RiskOfficer()
    decision = officer.assess(d1_hex, "SELL", "H1")
    
    if not decision.allowed:
        return False, f"D1 blocked: {decision.reason}"
    
    if not rsioma_signal.is_overbought_fall:
        return False, "RSIOMA not in overbought fall"
    
    if not pivot_context.price_near_top:
        return False, "Price not near pivot top"
    
    return True, "All conditions met"
```

---

## 5. 具体交易场景示例

### 5.1 场景一：收缩后向上突破（多头）

**背景**：
- D1 State Hex = 8（强多头）
- 6D Pivot 收缩（alert_6s ≥ 3）
- 3D Pivot 收缩（alert_3s ≥ 2）
- 1D Pivot 收缩（alert_1s ≥ 1）

**触发**：
- 价格突破 1D Pivot Range Top
- RSIOMA 从 <30 区域金叉（Up/DnXsig = -8）

**操作**：
- 入场：突破后回踩确认做多
- 止损：1D Pivot Range Bottom
- 止盈：3D Pivot Range Top → 6D Pivot Range Top

### 5.2 场景二：收缩后向下突破（空头）

**背景**：
- D1 State Hex = -8（强空头）
- 6D Pivot 收缩
- 3D Pivot 收缩
- 1D Pivot 收缩

**触发**：
- 价格跌破 1D Pivot Range Bottom
- RSIOMA 从 >70 区域死叉（Up/DnXsig = 8）

**操作**：
- 入场：跌破后回抽确认做空
- 止损：1D Pivot Range Top
- 止盈：3D Pivot Range Bottom → 6D Pivot Range Bottom

### 5.3 场景三：RSIOMA 极端反转（震荡市）

**背景**：
- D1 State Hex = 0 或 C（中性）
- 价格在 1D Pivot Range 内震荡
- 3D/6D Pivot 宽度正常（未收缩）

**触发**：
- RSIOMA < 20 后反弹（BuyTrigger = 5）
- 价格接近 1D Pivot Range Bottom

**操作**：
- 入场：RSIOMA 金叉 + 价格触及 Pivot Bottom
- 止损：Pivot Bottom 下方 1 ATR
- 止盈：Pivot Top（震荡市不恋战）

---

## 6. 风控规则

### 6.1 硬止损

- 每笔交易最大亏损：账户余额 2%
- 单笔止损距离：根据 Pivot Range 宽度动态调整

### 6.2 时间止损

- 如果 4 小时内未按预期方向移动，平仓观望
- 周五下午不新开仓（避免周末跳空）

### 6.3 连续亏损限制

- 连续 3 笔亏损后，暂停交易 24 小时
- 连续 5 笔亏损后，重新检查策略参数

### 6.4 D1 Risk Officer 覆盖

- 任何交易信号如果违反 D1 方向，自动阻止
- D1 方向变化时，平仓所有逆势头寸

---

## 7. 监控指标

### 7.1 每日检查清单

- [ ] D1 State Hex 更新
- [ ] 1D/3D/6D Pivot 收缩状态
- [ ] RSIOMA 当前值和趋势
- [ ] 持仓盈亏和止损距离
- [ ] 当日交易次数和胜率

### 7.2 每周复盘

- RSIOMA 信号胜率统计
- Pivot 突破成功率
- D1 Risk Officer 阻止次数和原因
- 最大回撤和夏普比率

---

## 8. 技术实现建议

### 8.1 MT5 EA 架构

```
EA_Main.mq5
├── D1_Risk_Gate.mqh      # D1 Risk Officer 接口
├── RSIOMA_Signal.mqh     # RSIOMA 信号读取
├── ACD_Pivot.mqh         # 1D/3D/6D Pivot 计算
├── State_Hex_Client.mqh  # State Hex 五元组读取
├── Trade_Manager.mqh     # 订单管理
└── Risk_Manager.mqh      # 风控管理
```

### 8.2 Python 分析脚本

```python
# rsioma_pivot_analyzer.py
class RSIOMAPivotAnalyzer:
    def __init__(self, symbol, timeframe):
        self.symbol = symbol
        self.tf = timeframe
        self.officer = D1RiskOfficer()
    
    def analyze(self):
        d1_hex = self.get_latest_d1_hex()
        rsioma = self.get_rsioma_signals()
        pivots = self.get_pivot_context()
        
        score = self.calculate_resonance(d1_hex, rsioma, pivots)
        
        return {
            'symbol': self.symbol,
            'd1_direction': self.officer.direction_from_hex(d1_hex),
            'rsioma_signal': rsioma,
            'pivot_context': pivots,
            'resonance_score': score,
            'recommendation': self.get_recommendation(score)
        }
```

---

## 9. 注意事项

1. **RSIOMA 是震荡指标**：在强趋势中可能持续超买/超卖，需结合 Pivot 突破确认
2. **Pivot 收缩不是必然突破**：收缩后可能继续震荡，需等待明确突破
3. **D1 Risk Officer 是底线**：任何信号都不能违反 D1 方向
4. **回测验证**：实盘前需在至少 6 个月数据上回测
5. **参数优化**：RSIOMA 周期（14, 21）可根据品种波动率微调

---

## 10. 参考文件

- `MT5_AI_Trading/skills/hermass-mt5-state/references/MT5_ACD_KAUFMAN_INDICATORS.md`
- `MT5_AI_Trading/python/ai_engine/d1_risk_officer.py`
- `MT5_AI_Trading/MT5/Indicators/RSIOMA_v2HHLSX.mq5`
- `MT5_AI_Trading/MT5/Indicators/ACD_枢轴.mq5`
