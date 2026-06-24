# 来源：YouTube 交易 SOP《Vegas 隧道交易系统》

## 一句话定义

YouTube 视频 [FxnBlJMD7Qw](https://www.youtube.com/watch?v=FxnBlJMD7Qw) 讲解了一套基于 **EMA 隧道（144/169）+ 大趋势均线（576/676）+ EMA12 过滤 + Volume Oscillator 量能确认** 的趋势跟踪交易系统。

## 为什么保留

- 该系统规则结构化程度高，适合转化为 SQX / MQL5 / MQL4 / Python 的量化模块。
- 止损逻辑分层（Volume Osc 确认 → 24 小时加速观察 → EMA676 硬止损），是处理“假突破”的典型案例。
- 与项目已有的 KVB/MT4 数据处理流程天然衔接：可用 MQL5/MQL4 输出状态 CSV，再经 `process_real_mt4_data.py` 着色后发送报告。

## 关键结论

### 核心观点 1：均线系统与趋势方向

- **Vegas 隧道**：EMA 144 / 169，视为中短期多空分水岭与动态支撑阻力。
- **大趋势线**：EMA 576 / 676，判断长期趋势方向。
- **过滤线**：EMA 12，用于过滤行情中的假突破信号。
- 交易方向必须与两组均线的趋势一致，否则放弃操作。

### 核心观点 2：入场与止损逻辑

- 多头入场：隧道在 576/676 之上形成多头排列，且 EMA12 在隧道上方，价格回踩隧道附近做多。
- 空头入场：隧道在 576/676 之下形成空头排列，且 EMA12 在隧道下方，价格回踩隧道附近做空。
- 止损分层：先看 Volume Osc 是否突破 144 确认；再观察 24 小时内是否加速；最终任何周期跌破 EMA676 必须止损。

### 核心数据 / 案例

| 项目 | 数值/说明 |
|------|-----------|
| 隧道均线 | EMA 144 / 169 |
| 大趋势均线 | EMA 576 / 676 |
| 过滤线 | EMA 12 |
| Volume Osc 短线 / 长线 | 1 / 14 |
| Volume Osc 零线 | 144（<1H 可用 89） |
| 案例品种 | BTC/USD（15M、1H、日线） |
| 案例收益 | 日线案例约 8 倍（8,000 → 64,000 USD） |

## 来源

- [[2026-06-23-youtube-trading-sop-16-transcript.txt]]（原始字幕转录，逐句保留）
- 视频地址：https://www.youtube.com/watch?v=FxnBlJMD7Qw

## 关联页面

- [[trading-sop-vegas-tunnel-system]]
- [[vegas-tunnel-system]]
- [[sqx-module-mapping-vegas-tunnel-system]]
- [[trading-process-umar-ashraf]]
- [[three-part-position-sizing]]
