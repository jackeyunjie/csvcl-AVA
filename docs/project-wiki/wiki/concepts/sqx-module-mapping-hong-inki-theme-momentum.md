# SQX 模块映射：Hong Inki 主题龙头动量突破

## 一句话定义

将 YouTube 第 15 个视频中的 **Hong Inki 主题龙头动量突破策略** 拆解为 **StrategyQuant X (SQX)** 的指标、条件、入场、出场模块组合，实现可回测、可优化的程序化策略。

## 策略流程

```text
主题识别（外部扫描） → 龙头筛选 → 突破信号确认 → 入场 → 短线出场
```

> 主题识别和龙头筛选更适合在 SQX 外部用 Python 完成（多标的横向比较），SQX 负责单个标的的突破条件、入场和出场逻辑。

## 1. 外部预处理模块（Python / 数据源）

### 输入

| 字段 | 说明 |
|------|------|
| Symbol | 标的代码 |
| Volume | 当日成交额 |
| Change % | 当日涨跌幅 |
| Sector / Theme | 所属主题或板块 |
| 6M High | 过去 6 个月最高价 |
| All-Time High | 历史最高价 |

### 输出

- 每日生成一份候选龙头列表：
  - 成交额排名前 30
  - 涨幅 > 5%
  - 同一主题出现多只标的
  - 每个主题只保留涨幅最大的一只作为一等龙头

### Python 伪代码

```python
df['rank_volume'] = df['volume'].rank(ascending=False)
df_leader = df[
    (df['rank_volume'] <= 30) &
    (df['change_pct'] > 0.05)
].sort_values(['theme', 'change_pct'], ascending=[True, False])
leaders = df_leader.groupby('theme').first().reset_index()
```

## 2. SQX 指标模块（Indicators）

| SQX 指标 | 参数 | 说明 |
|----------|------|------|
| Highest High | Period = 126（约 6 个月日线） | 六个月高点 |
| Volume SMA | Period = 20 | 近期均量 |
| ATR | Period = 14 | 用于动态止损 |

## 3. SQX 入场条件模块（Entry Conditions）

### 多头入场

```text
Close > Highest High(126)            // 突破六个月高点
AND Close > Open * 1.10              // 单日涨幅超过 10%
AND Volume > Volume SMA(20) * 1.5    // 显著放量
AND Symbol in Leaders List           // 属于外部预处理输出的一等龙头
```

### 入场动作模块（Entry Order）

| 设置 | 建议值 |
|------|--------|
| 入场类型 | Market at Close of Signal Candle 或 Next Bar Open |
| 方向 | Long |
| 最大持仓时间 | 2-3 个交易日 |

## 4. 出场模块（Exit Conditions）

### 止损（Stop Loss）

| 方案 | SQX 设置 |
|------|----------|
| 固定百分比止损 | Stop Loss = 3% below entry price |
| 关键 K 线低点 | Stop below signal candle low |
| ATR 动态止损 | Stop = Entry - 1.5 * ATR(14) |

### 止盈（Take Profit）

| 方案 | SQX 设置 |
|------|----------|
| 固定百分比止盈 | Take Profit = 5% above entry price |
| 时间止盈 | Exit after 2 bars if not stopped |

### 开盘保护退出（Day 3+）

```text
If Bars Since Entry >= 3 AND Close < Open * 0.99 then Exit at Market
```

### K 线形态过滤（Day 3+）

- 十字星：实体极小（Close ≈ Open）
- 倒锤子线：上影线长、实体小
- 阴线：Close < Open

在 SQX 中可用自定义条件实现：

```text
If Bars Since Entry >= 3 AND (Doji OR InvertedHammer OR Close < Open) then Exit
```

## 5. 过滤模块（Filters）

- **主题过滤**：只在预处理输出的龙头列表中交易。
- **成交量过滤**：排除无量突破。
- **大盘过滤**：可加入大盘指数趋势条件，仅在大盘非极端下跌时交易。
- **时间过滤**：股票市场可限定交易时段；加密货币可 24 小时交易。

## 6. 参数优化建议

| 参数 | 优化范围 | 说明 |
|------|----------|------|
| 突破涨幅阈值 | 8% - 15% | 10% 为视频中默认值 |
| 成交量倍数 | 1.2 - 2.5 | 1.5 为建议起点 |
| 止损百分比 | 2% - 5% | 3% 为视频中默认值 |
| 止盈百分比 | 4% - 8% | 5% 为视频中默认值 |
| 最大持仓 bars | 2 - 5 | 短线策略不宜过长 |

## 与本项目 CSV/Excel 流程的结合

1. Python 脚本每日扫描市场数据，输出候选龙头 CSV。
2. SQX 导入龙头列表作为交易池，生成 MQL5/MQL4 EA。
3. MT5/MT4 运行时输出信号状态 CSV。
4. 本项目 `process_real_mt4_data.py` 扫描 CSV，对突破信号、持仓天数、止损止盈状态着色。
5. 生成邮件报告与截图。

## 生成代码方向

- **MQL5 EA**：用于 MT5 实盘或回测。
- **MQL4 EA**：用于 MT4 实盘或回测。
- **Python 脚本**：用于每日主题扫描、龙头筛选、CSV 输出。

## 关联页面

- [[trading-sop-hong-inki-theme-momentum]]
- [[theme-leader-momentum-breakout]]
- [[source-youtube-trading-sop-15]]
- [[sqx-module-mapping]]
- [[sqx-module-mapping-impulse-macd]]
- [[sqx-module-mapping-ema200-adx-stochrsi]]
