# SQX × State 整合指南

## 概述

将 State 系统的市场分类数据导入 SQX，让 SQX 在每个 State 类内搜索策略。

**核心思路**：不是在所有数据上搜索，而是在"月线突破+日线看涨"这样的特定市场环境中搜索。

---

## Step 1: 导入 State 数据到 SQX

### 1.1 打开 SQX
运行 `D:\SQX136\StrategyQuantX.exe`

### 1.2 导入自定义数据
1. 菜单: **Data** → **Custom Data** → **Import**
2. 选择文件: `D:\SQX136\data\processed\US_30_state_sqx.csv`
3. 设置:
   - Date format: `yyyy.MM.dd`
   - Time format: `HH:mm`
   - Separator: `,`
   - Skip first row: Yes (header)

### 1.3 验证导入
导入后检查 SQX 数据管理器中是否出现 State 相关列:
- `State_D1`, `State_H4`, `State_H1` (hex 值)
- `D1_dir`, `H1_trend`, `Squeeze_count` (数值)
- `Multi_bull`, `Multi_bear`, `Breakout_up` (信号)

---

## Step 2: 创建 State 过滤策略

### 2.1 在 AlgoWizard 中创建策略

**策略名称**: `State_Breakout_Buy`

**入场条件 (BUY)**:
```
Condition 1: D1_dir == 1          (日线看涨)
Condition 2: H1_trend == 1        (H1 有趋势触发)
Condition 3: H4_dir == 1          (H4 确认看涨)
  OR:       H4_breakout == 1      (H4 突破)
Condition 4: RSI(14) > 50         (动量确认，SQX内置)
Condition 5: Close > EMA(20)      (趋势确认，SQX内置)
```

**入场条件 (SELL)**:
```
Condition 1: D1_dir == -1         (日线看跌)
Condition 2: H1_trend == 1        (H1 有趋势触发)
Condition 3: H4_dir == -1         (H4 确认看跌)
  OR:       H4_breakout == 1      (H4 突破)
Condition 4: RSI(14) < 50         (动量确认)
Condition 5: Close < EMA(20)      (趋势确认)
```

**出场**:
```
Stop Loss: ATR(14) * 1.5
Take Profit: ATR(14) * 3.0
Time Exit: 12 bars (12小时)
```

### 2.2 Squeeze 突破策略

**策略名称**: `State_Squeeze_Breakout`

**入场条件 (BUY)**:
```
Condition 1: Squeeze_count >= 2   (多周期收缩)
Condition 2: Breakout_up == 1     (向上突破)
Condition 3: Multi_bull >= 3      (多周期看涨)
```

**入场条件 (SELL)**:
```
Condition 1: Squeeze_count >= 2   (多周期收缩)
Condition 2: Breakout_down == 1   (向下突破)
Condition 3: Multi_bear >= 3      (多周期看跌)
```

---

## Step 3: 使用 SQX 遗传算法搜索

### 3.1 设置搜索空间
1. 菜单: **Strategy** → **Search** → **New Search**
2. 选择数据: US_30 (或其他品种)
3. 设置搜索参数:
   - Population: 100
   - Generations: 50
   - Fitness: Net Profit + Sharpe Ratio

### 3.2 添加 State 条件到搜索
在搜索条件中添加:
- `D1_dir` 作为过滤条件
- `H1_trend` 作为入场触发
- `Squeeze_count` 作为前置条件

### 3.3 Walk-forward 设置
1. 菜单: **Validation** → **Walk-Forward**
2. 设置:
   - Number of segments: 5
   - Training ratio: 70%
   - Minimum trades: 30

### 3.4 Monte Carlo 设置
1. 菜单: **Validation** → **Monte Carlo**
2. 设置:
   - Simulations: 1000
   - Shuffle trades: Yes
   - Confidence level: 95%

---

## Step 4: 按 State 模式分段回测

### 4.1 使用分段数据
SQX 的 `data/processed/` 目录中有按 State 模式分段的文件:
- `US_30_6_6_6_60bars.csv` — D1=6,H4=6,H1=6 模式 (60根K线)
- `US_30_8_8_-F_27bars.csv` — D1=8,H4=8,H1=-F 模式 (27根K线)

### 4.2 对每个分段运行策略搜索
1. 导入分段数据
2. 运行遗传算法搜索
3. 记录每个模式的最优策略

### 4.3 跨模式验证
找到的策略在其他模式上是否有效？
- 在 `D1=6,H4=6,H1=6` 上找到的策略
- 在 `D1=8,H4=8,H1=-F` 上是否也有效？

---

## Step 5: 导出 SQX 策略到 MT5 EA

### 5.1 SQX 导出
1. 菜单: **Strategy** → **Export** → **MetaTrader 5**
2. 选择导出格式: `.mq5`
3. 保存到: `D:\qoder\csvcl - AVA\MT5_AI_Trading\mql5\Experts\`

### 5.2 集成到 AI_Trading_Bridge
将 SQX 生成的策略逻辑集成到现有的 `AI_Trading_Bridge.mq5` 中:
- 添加 State 过滤条件
- 添加 SQX 策略的入场/出场逻辑
- 通过 ZeroMQ 接收 Python 端的 State 数据

---

## 数据文件说明

### 完整 State 文件 (每品种一个)
| 文件 | 内容 |
|------|------|
| `US_30_state_sqx.csv` | US_30 的完整 H1 State 数据 |
| `XAUUSD_state_sqx.csv` | 黄金的完整 H1 State 数据 |
| ... | ... |

### 分段文件 (按 State 模式)
| 文件名格式 | 说明 |
|------------|------|
| `US_30_6_6_6_60bars.csv` | D1=6,H4=6,H1=6 模式，60根K线 |
| `US_30_8_-F_-F_40bars.csv` | D1=8,H4=-F,H1=-F 模式，40根K线 |

### CSV 列说明
| 列名 | 类型 | 说明 |
|------|------|------|
| Date | string | 日期 (yyyy.MM.dd) |
| Time | string | 时间 (HH:mm) |
| State_D1 | string | D1 的 state_hex |
| D1_dir | int | D1 方向 (-1/0/1) |
| D1_trend | int | D1 趋势触发 (0/1) |
| D1_squeeze | int | D1 收缩 (0/1) |
| Multi_bull | int | 多周期看涨数 (0-5) |
| Multi_bear | int | 多周期看跌数 (0-5) |
| Squeeze_count | int | 收缩周期数 (0-5) |
| Breakout_up | int | 向上突破 (0/1) |
| Breakout_down | int | 向下突破 (0/1) |

---

## 下一步

1. **在 SQX 中导入 US_30 数据**
2. **创建 State_Breakout_Buy 策略**
3. **运行遗传算法搜索**
4. **Walk-forward + Monte Carlo 验证**
5. **导出有效策略到 MT5 EA**
