# 来源：MQL5 文章 18911 — K线区间理论工具

## 一句话定义

MQL5 官方文章 [18911](https://www.mql5.com/zh/articles/18911) 介绍了 **Candle Range Theory（CRT，K线区间理论）** 的完整 MT5 实现，包括一个纯头文件分类类、一个图表指标和一个无重绘警报 EA。

## 为什么保留

本项目核心围绕 MT4/MT5 数据处理、状态码着色与信号识别。该文章提供了一套**定义清晰、可直接移植到 MQL5/MQL4 的 K 线分类框架**，对理解波动率、突破/盘整形态以及如何将原始价格行为转化为可程序化的交易信号具有直接参考价值。

## 关键结论

1. **四类互斥 K 线形态**
   - 大区间 K 线（LR）：真实波幅 ≥ `largeMult × ATR`
   - 小区间 K 线（SR）：真实波幅 ≤ `smallMult × ATR`
   - 内包 K 线（IB）：完全包含在前一根 K 线高低点之间
   - 外包 K 线（OB）：同时突破前一根 K 线的高点和低点

2. **无重绘设计**
   - 只在最新已收盘 K 线（shift=1）上计算，忽略正在形成中的当前 K 线（shift=0）。
   - 实盘、回测、优化器中的信号保持一致。

3. **模块化实现**
   - `CRangePattern.mqh`：分类引擎，零动态内存分配。
   - `CRT Indicator.mq5`：通过图表对象（而非缓冲区）绘制彩色矩形/箭头。
   - `CRT Expert Advisor.mq5`：警报引擎，可弹窗、声音、推送通知。

4. **默认参数**
   - ATR 周期：14
   - 大区间倍数 `largeMult`：1.5
   - 小区间倍数 `smallMult`：0.5

## 与项目的关联

- 可与本项目的 `state_hex` / 状态码体系互补：CRT 提供价格行为层面的信号，state_hex 提供多周期状态层面的信号。
- 其**无重绘、仅收盘后计算**的设计原则与本项目强调的信号稳定性一致。

## 来源

- [[2026-06-23-mql5-article-18911]]（原始资料）
- 在线地址：https://www.mql5.com/zh/articles/18911

## 关联页面

- [[candle-range-theory]]
- [[mql5-kline-patterns]]
- [[opening-range-breakout]]
- [[acd-logic-trading]]
