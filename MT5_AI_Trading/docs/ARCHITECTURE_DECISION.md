# MT5 AI 量化交易系统 - 架构决策记录

## 决策零：State 周期视角 Agent 契约

**结论**：周期（structure timeframe）和周期视角（viewpoint）是正交维度；每个周期视角都是独立 Agent。

项目内 State 架构以 [STATE_VIEWPOINT_AGENT_CONTRACT.md](STATE_VIEWPOINT_AGENT_CONTRACT.md) 为准：

```text
structure_tf = 结构来源周期
view_tf      = 观察基准周期
state_hex    = structure_tf 在 view_tf 视角下的状态
```

- 每个视角 Agent 使用自己的时间戳和 close 作为所有 `position` 的基准价。
- 每个 Agent 同时包含本周期及以上大周期的时间戳对齐状态。
- `base/trend/volatility` 来自各自结构周期，只有 `position` 随视角变化。
- 不能把各周期原生 state 简单拼接后称为 H1/M15 视角。

例如 H1 Agent 输出 `MN1/W1/D1/H4/H1 @ H1_view`；M15 Agent 输出 `MN1/W1/D1/H4/H1/M30/M15 @ M15_view`。

## 决策一：状态编码系统

**结论**：不统一新旧编码，建立三层抽象。

```
统一语义层          市场编码层            原始兼容层
TRENDING_UP  →  ForexEncoder(7)      LegacyDecoder(7→TRENDING_UP)
CONSOLIDATING → GenericEncoder(2)     保留旧回测结果不变
BREAKOUT      → GenericEncoder(10)
```

- 新系统继续用位运算（0/2/8/10），支持组合扩展
- 旧系统（6/7/14/15）冻结，通过适配器调用
- 多市场（A股/港股/美股）各自有独立编码器，共享统一语义层

## 决策二：技术栈分工

**结论**：Python为核心，MT5降级为外汇执行终端。

| 职能 | 归属 | 说明 |
|------|------|------|
| 数据获取 | Python | A股akshare、港股yfinance、外汇MT5API |
| 状态计算 | Python | D1/W1/MN1三元组，向量化计算 |
| 策略回测 | Python | vectorbt/backtrader，全市场统一 |
| 信号生成 | Python | 多策略聚合、评分、风控 |
| 外汇执行 | MT5 | 仅接收信号、下单、回报状态 |
| A股执行 | QMT/券商API | 直连，不经过MT5 |
| 图表查看 | MT5 | 交易员习惯，但非必需 |

## 决策三：MT5接入方式（已实施）

**结论**：默认使用官方MetaTrader5 Python API，ZeroMQ作为备选。

- `connect_mt5_api.py` 已完成连通验证
- `mt5_python_api.py` 封装完整（下单、平仓、改单、账户查询）
- 配置 `connection_mode: python_api` 为默认
- 安全开关：`live_trading: false` + `dry_run: true`

## 下一步实施路径

1. P0：状态编码抽象基类（`state_encoder.py`）
2. P1：D1→W1→MN1真实K线复合（`kvb_state_engine.py`）
3. P2：Python信号→MT5执行通道验证
4. P3：A股数据接入（akshare）
