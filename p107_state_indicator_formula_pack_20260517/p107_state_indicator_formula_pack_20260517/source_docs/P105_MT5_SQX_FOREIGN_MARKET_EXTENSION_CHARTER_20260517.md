# P105 MT5 / SQX 外国市场拓展章程

日期：2026-05-17

## 1. 总裁决

可以开展，但必须作为独立试验线：

```text
MT5 / SQX 外国市场拓展线
```

它不替代 A 股、港股、美股股票主线，也不替代 Hermass 的 state-first 主裁决。

推荐定位：

```text
MT5 负责外国市场原始行情候选
SQX 负责外部策略回测执行
Hermass 负责状态定义、状态池切分、审计和最终研究裁决
```

这条线适合先做：

1. 外汇。
2. 黄金。
3. 原油。
4. 股指 CFD。
5. CME 期货。
6. 海外股票小样本。

暂不适合：

1. 作为 A 股主数据源。
2. 作为港股/美股官方股票主源。
3. 未经审计直接进入 P17/P35/P34。
4. 用券商 CFD 数据直接替代交易所真实成交数据。

## 2. 为什么值得做

这条线有三个价值：

### 2.1 拓展外国市场

MT5 和 SQX 都天然更适合外汇、黄金、原油、指数和期货。  
这些市场是全球化资产，交易时间长，适合 H1/M15/M5 独立系统验证。

### 2.2 验证小周期系统

Hermass 已确立：

```text
D1 / H1 / M15 / M5 都是独立系统
```

MT5/SQX 可以提供 M1/M5/H1 数据，适合验证：

- H1-native。
- M15-native。
- M5-native。
- 高周期 context strict-prior as-of。

### 2.3 借用 SQX 的回测执行能力

SQX 擅长：

- 策略执行回测。
- 参数优化。
- Monte Carlo。
- Walk-Forward Matrix 展示。
- 多市场批量测试。

Hermass 可以把状态池导给 SQX，让 SQX 跑策略，再把结果导回 Hermass 做状态主裁决。

## 3. 最大风险

### 3.1 MT5 是 broker-specific

broker-specific 的中文含义是“券商服务器口径”。  
同一个品种，不同券商的报价、点差、交易时间、合约规格可能不完全一致。

因此，MT5 数据必须标记：

```text
BROKER_DATA_AUDIT_REQUIRED
```

### 3.2 CFD 不是交易所股票

CFD 的中文含义是“差价合约”。  
它不是交易所真实股票成交数据，而是券商提供的合约报价。

因此：

```text
CFD 数据不能直接替代股票交易所数据
```

### 3.3 tick volume 不是真实成交量

MT5 外汇/CFD 常见的 volume 是 tick volume。  
tick volume 中文含义是“报价跳动次数”，不是股票市场的真实成交量。

所以 MT5 的 volume 只能作为：

```text
quote_activity（报价活跃度）
```

不能直接解释成成交额或真实资金流。

### 3.4 时间戳必须审计

MT5 使用 broker server time。  
SQX 有 Start of bar / End of bar。

两者都必须审：

```text
timezone_audit
bar_type_audit
session_calendar_audit
asof_audit
```

否则 H1/M15/M5 会发生未来函数或错位。

## 4. 底层方法论如何对齐

无论数据来自 MT5、SQX、Futu、黑狼还是 Tushare，Hermass 底层方法论不变。

### 4.1 price-first

price-first 中文含义是“价格优先”。  
先用 OHLC 建立状态。

最小字段：

```text
datetime
open
high
low
close
```

volume、moneyflow、tick volume 是增量证据，不是主裁决。

### 4.2 state-first

state-first 中文含义是“状态优先”。  
先定义市场状态，再验证策略是否只在某类状态里具备研究价值。

不允许直接从指标跳到策略结论。

### 4.3 base-timeframe native

base-timeframe native 在本项目中解释为“周期视角 Agent”。  
D1、H1、M15、M5 必须各自作为独立视角 Agent。

例如：

```text
H1 Agent 必须用 H1 timestamp / H1 close 生成 MN1/W1/D1/H4/H1 @ H1_view
M15 Agent 必须用 M15 timestamp / M15 close 生成 MN1/W1/D1/H4/H1/M30/M15 @ M15_view
M5 Agent 必须用 M5 timestamp / M5 close 生成 M15/H1/D1/W1/MN1 context @ M5_view
```

不能把 D1 结论直接下沉给 H1/M15/M5。

### 4.4 state-regime walk-forward

State-Regime Walk-Forward 中文含义是“状态组合窗口验证”。  
主裁决按大周期状态组合切窗。

Time-Drift Audit 中文含义是“时间漂移审计”，只做旁路，不替代状态窗主裁决。

## 5. MT5 数据接入层级

MT5 数据进入 Hermass 的层级：

```text
L0_MT5_RAW
  -> L1_MT5_INDICATOR_COMPATIBLE
  -> L2_MT5_STATE_OBSERVATION
  -> L2_5_MT5_PRIMITIVE_DRY_RUN
  -> L3_MT5_STATE_REGIME_PREP
```

进入 L3 前必须通过：

1. broker profile audit。
2. timezone audit。
3. session calendar audit。
4. spread audit。
5. contract spec audit。
6. tick volume semantics audit。
7. as-of audit。

## 6. SQX 数据接入层级

SQX 数据进入 Hermass 的层级：

```text
L0_SQX_RAW
  -> L1_SQX_INDICATOR_COMPATIBLE
  -> L2_SQX_STATE_OBSERVATION
  -> L2_5_SQX_PRIMITIVE_DRY_RUN
```

SQX 回测结果进入 Hermass 的层级：

```text
SQX_BACKTEST_EXECUTION_OUTPUT
  -> Hermass state-regime summary
  -> Hermass time-drift audit
  -> Hermass robustness audit
```

SQX 不做 Hermass 最终主裁决。

## 7. 第一批建议实验

### 实验 A：黄金 H1

```text
数据源：MT5 或 SQX
品种：XAUUSD
周期：H1
策略：Turtle / Bollinger Pirate / 25-60
目标：验证 H1-native 状态池链路
```

### 实验 B：标普指数 H1

```text
数据源：MT5 CFD 或 SQX futures
品种：US500 / ES / @ES / @EW
周期：H1
策略：Turtle / Donchian / Bollinger
目标：验证股指短线状态系统
```

### 实验 C：EURUSD M15

```text
数据源：MT5
品种：EURUSD
周期：M15
策略：Bollinger / 25-60 / 3 Pivot
目标：验证 M15-native 系统
```

## 8. 不建议一开始做什么

不建议一开始做：

1. 全市场全品种全周期。
2. 自动实盘。
3. 多券商混合。
4. Tick 级别逐笔建模。
5. 直接把 MT5/SQX 结果对外展示成收益能力。

第一阶段只做：

```text
小样本
单品种
单周期
单策略族
全链路审计
```

## 9. Windows 侧最小交付

Windows 电脑先导出：

```text
MT5_XAUUSD_H1_sample.csv
MT5_US500_H1_sample.csv
SQX_AAPL_M1_sample.csv
SQX_EW_M1_sample.csv
mt5_manifest_20260517.json
sqx_manifest_20260517.json
```

每个 CSV 必须至少有：

```text
symbol
datetime
open
high
low
close
tick_volume 或 volume
spread，如有
source_name
broker_name
timezone
bar_type
```

## 10. 产品层怎么讲

对外不要讲：

```text
我们用 MT5/SQX 找赚钱策略
```

应该讲：

```text
我们正在用 MT5/SQX 建立海外市场的小周期状态验证沙盒，用来检验经典策略是否只在特定市场状态里具备进一步研究价值。
```

## 11. 最终结论

MT5/SQX 值得开展，但必须有限制：

```text
小样本先行
单独数据域
严格时间戳审计
不替代主数据源
不替代 Hermass 状态裁决
不直接进入实盘或对外收益展示
```

它的最佳定位是：

```text
外国市场小周期状态验证沙盒
```
