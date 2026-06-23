# Hermass State 与指标计算公式包

日期：2026-05-17

## 用途

本压缩包用于统一说明 Hermass / 弘运系统当前涉及的状态编码与指标计算口径。

内容包括：

1. `state_hex` 编码规则。
2. 价格类基础指标。
3. 趋势、波动、布林、ATR、支撑阻力指标。
4. 策略原语指标：布林强盗、海龟、VCP、25/60、3 Pivot、6-day / 6-session Axis。
5. 资金流、换手率、筹码峰指标。
6. 多周期 as-of 与 State-Regime Walk-Forward 的数据使用边界。

## 边界

本包只包含公式和说明，不包含：

- 全量行情数据。
- DuckDB 数据库。
- API key。
- 账户信息。
- 实盘交易规则。
- 买卖建议。

## 核心原则

```text
price-first 价格优先
state-first 状态优先
base-timeframe native 基准周期原生系统
state-regime walk-forward 状态组合窗口验证
```

资金流、换手率、筹码峰属于增量解释层，不替代价格状态主裁决。

