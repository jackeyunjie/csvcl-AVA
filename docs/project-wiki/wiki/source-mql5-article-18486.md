# 来源：MQL5 文章 18486 — 开盘区间突破工具

## 一句话定义

MQL5 官方文章 [18486](https://www.mql5.com/zh/articles/18486) 介绍了一款基于 **开盘区间突破（ORB, Opening Range Breakout）** 的 MT5 EA，通过“突破 → 回踩 → 二次突破”三步确认，过滤假突破并生成日内交易信号。

## 为什么保留

开盘区间突破与 ACD 交易逻辑在理念上高度相关：都依赖早盘（或特定时段）形成的高低边界，作为当日多空分水线。本文提供了一套可直接移植到 MQL5 的模块化实现，对项目研究日内突破策略、状态触发条件有参考价值。

## 关键结论

1. **两种开盘区间计算方法**
   - 双 K 线区间：取昨日最后一根 K 线 + 今日开盘第一根 K 线，取最大高、最小低
   - 固定分钟区间：开盘后 `RangeMinutes`（默认 15 分钟）内跟踪最高价/最低价

2. **核心组件**
   - `CRangeCapture`：区间捕捉类
   - `CATRModule`：ATR 滤波模块
   - `CRetestSignal`：突破-回踩-再突破信号类
   - `CDashboard`：图表仪表盘

3. **三步确认机制**
   - 第一步：价格收于区间外（Break）
   - 第二步：价格回踩至区间边界（Retest）
   - 第三步：收盘价再次突破边界（Confirmed Entry）

4. **默认参数**
   - `RangeMinutes` = 15
   - `ATRPeriod` = 14
   - `ATRMultiplier` = 1.5

5. **状态机设计**
   - `OnTick()` 内使用 `switch(state)` 分为 Capture / Break / Retest / Done 四阶段
   - 每日午夜自动重置，避免时区/夏令时问题

## 与 ACD 逻辑的关联

- ACD 逻辑中的 A 点（Opening Range High/Low）与本文的 `openingHigh` / `openingLow` 等价。
- 本文的“回踩确认”可视为 ACD 中 C 点确认的一种实现变体。
- 不同点：本文更强调 MQL5 程序化实现和回测验证，而非 ACD 原始规则中的特定加减点差。

## 来源

- [[2026-06-23-mql5-article-18486]]（原始资料）
- 在线地址：https://www.mql5.com/zh/articles/18486

## 关联页面

- [[opening-range-breakout]]
- [[acd-logic-trading]]
- [[candle-range-theory]]
