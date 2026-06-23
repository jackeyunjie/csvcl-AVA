# K线区间理论（Candle Range Theory, CRT）

## 一句话定义

K线区间理论（CRT）是一种将每根已收盘 K 线按真实波幅与相对位置划分为 **LR / SR / IB / OB** 四类之一的分析框架，用于识别波动率扩张、压缩、犹豫与突破。

## 为什么重要

波动率是价格行为的本质体现。在震荡指标或趋势滤波器给出信号之前，单根 K 线的波幅往往已经泄露了市场参与者的意图：

- 波幅突然扩张 → 大资金介入或重大事件冲击
- 波幅持续收缩 → 流动性下降、盘整、突破前兆
- 完全内包于前一根 K 线 → 多空犹豫
- 完全吞没前一根 K 线 → 订单流方向明确

CRT 把这些直观经验转化为**可程序化识别的规则**，适合主观分析、自动化交易和策略研究。

## 具体内容

### 四类形态定义

| 形态 | 英文 | 判定条件 | 市场含义 |
|------|------|----------|----------|
| 大区间 K 线 | LR (Large-Range) | `TR ≥ largeMult × ATR` | 资金积极入场，可能启动趋势或趋势竭尽 |
| 小区间 K 线 | SR (Small-Range) | `TR ≤ smallMult × ATR` | 波动压缩，流动性下降，突破前休整 |
| 内包 K 线 | IB (Inside-Bar) | `High[1] < High[2]` 且 `Low[1] > Low[2]` | 区间收敛，多空犹豫 |
| 外包 K 线 | OB (Outside-Bar) | `High[1] > High[2]` 且 `Low[1] < Low[2]` | 同时击穿前高前低，订单流冲击强烈 |

> 注：判定顺序具有层级性。先判断 LR/SR，再判断 IB，最后判断 OB，确保每根 K 线只属于一个分类。

### 真实波幅（TR）

```text
TR = max(
    High[t] - Low[t],
    |High[t] - Close[t-1]|,
    |Low[t] - Close[t-1]|
)
```

使用 TR 而非单纯高低点跨度，可捕捉隔夜跳空缺口。

### 平均真实波幅（ATR）

CRT 采用简单算术平均 ATR（非 Wilder 指数平滑），默认周期 14：

```text
ATR = Σ TR[i] / 14
```

### 默认参数

- `atrPeriod` = 14
- `largeMult` = 1.5
- `smallMult` = 0.5

### 无重绘时序规则

- 仅处理最新已收盘 K 线（shift = 1）
- 忽略正在形成中的当前 K 线（shift = 0）
- 保证实盘与回测信号一致

## 关联页面

- [[source-mql5-article-18911]]
- [[mql5-kline-patterns]]
- [[opening-range-breakout]]
- [[acd-logic-trading]]
- [[dual-ema-fractal-breakout]]
- [[state-hex]]（待创建）

## 来源

- [[2026-06-23-mql5-article-18911]]
