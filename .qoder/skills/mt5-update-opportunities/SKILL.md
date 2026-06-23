---
name: mt5-update-opportunities
description: 连接 AVATRADE MT5 更新 H1 State 数据并分析交易机会。当用户说"更新数据"、"交易机会"、"分析市场"、"State数据"时触发。基于 State Hex 五元组编码和 Top 策略模式匹配生成交易信号报告。
---

# MT5 数据更新与交易机会分析

## 概述

连接 AVATRADE MT5 平台，获取最新 K 线数据，计算 State Hex 五元组状态，更新 DuckDB 数据库，并基于 Top 策略模式匹配输出交易机会报告。

## 工作流程

### 1. 检查 MT5 连接状态

```python
from python.core.mt5_bridge_dual import MT5Bridge
bridge = MT5Bridge()
connected = bridge.connect()
```

- 端口: PUB=5565, REQ=5566
- 如连接失败，提示用户启动 MT5 终端并运行 EA

### 2. 更新 H1 State 数据（如 MT5 已连接）

```bash
cd MT5_AI_Trading
python build_h1_state_real.py
```

或运行数据收集脚本：
```bash
python python/core/state_collector.py --source mt5_avatrade
```

### 3. 分析交易机会

```bash
python analyze_all_opportunities.py
```

## 数据库信息

- 路径: `MT5_AI_Trading/data/h1_state.duckdb`
- 表名: `h1_state_snapshot`
- 字段: `symbol, timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex`
- 品种数: 101 个

## State Hex 编码规则

| 值 | 含义 |
|----|------|
| C/D/E/F | 收缩状态（波动率压缩） |
| 6/7/8/9 | 趋势状态 |
| 1/2/3/4/5 | 震荡/过渡 |
| 负号 | 方向反转 |

## 交易信号判断

### Top 策略模式匹配

脚本内置历史统计的最优开仓条件，按品种分别查询最新状态后匹配：

```sql
SELECT symbol, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex, timestamp
FROM h1_state_snapshot s1
WHERE timestamp = (
    SELECT MAX(timestamp) 
    FROM h1_state_snapshot s2 
    WHERE s2.symbol = s1.symbol
)
ORDER BY symbol
```

### 收缩/突破/趋势分类

- **H1 = C/D/E/F**: 收缩状态，等待突破
- **H1 = 6/7/8/9**: 趋势状态，顺势交易
- **H1 = 1/2/3/4/5**: 震荡/过渡，观望

## 输出格式

报告包含：
1. **Top 策略匹配信号** — 评分/胜率/盈亏比排序
2. **主要品种状态速览** — MN1/W1/D1/H4/H1 五元组
3. **收缩/突破/趋势分析** — 分类统计
4. **重点机会提示** — 高评分信号汇总

## 注意事项

- MT5 终端需启动并运行 ZeroMQ EA（端口 5565/5566）
- 美股品种数据可能有延迟（收盘后无更新）
- 数据最新时间可通过 `MAX(timestamp)` 查询确认
