# MQL5 K线形态识别模式

## 一句话定义

在 MQL5/MQL4 中，将单根或多根 K 线的价格关系抽象为布尔规则，通过数组索引访问历史数据，在收盘后输出稳定、无重绘的分类信号。

## 为什么重要

本项目大量处理 MT4/MT5 生成的 CSV 数据，核心字段多为状态码或指标值。理解 K 线形态如何在 MQL5 中被程序化识别，有助于：

1. 判断 CSV 数据中某些字段的生成逻辑
2. 将新的价格行为特征补充进数据处理流程
3. 与 `state_hex` 等状态体系形成互补

## 具体内容

### 数据访问方式

MQL5 中通过 `CopyOpen`、`CopyHigh`、`CopyLow`、`CopyClose` 获取价格数组，或直接在 `OnCalculate` 中接收数组参数：

```cpp
double open[], high[], low[], close[];
ArraySetAsSeries(open, true);
CopyOpen(_Symbol, PERIOD_CURRENT, 0, count, open);
```

### 单根 K 线分类示例（CRT 风格）

```cpp
bool IsLargeRange(const double &H[], const double &L[], const double &C[],
                  int shift, int atrPeriod, double largeMult)
{
    double atr = iATR(_Symbol, PERIOD_CURRENT, atrPeriod);
    double tr = MathMax(H[shift] - L[shift],
                   MathMax(MathAbs(H[shift] - C[shift + 1]),
                           MathAbs(C[shift + 1] - L[shift])));
    return tr >= largeMult * atr;
}
```

### 无重绘原则

- 只在 `shift = 1`（最新已收盘 K 线）上产生信号
- 不读取或修改 `shift = 0`（当前未收盘 K 线）
- 信号一旦形成，后续价格变动不会撤销该信号

### 与本项目的结合点

- 若 MT4/MT5 端输出 CRT 四类形态码，CSV 处理脚本可据此着色、统计频率、生成警报。
- 颜色规则可沿用本项目已有的红/绿/蓝等约定。

## 关联页面

- [[candle-range-theory]]
- [[source-mql5-article-18911]]
- [[trading-sop-normalized-macd-rsi-ma]]
- [[sqx-module-mapping]]

## 来源

- [[2026-06-23-mql5-article-18911]]
