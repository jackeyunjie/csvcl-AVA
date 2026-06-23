# M15 State 视角 Agent 使用指南

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    M15 State 独立视角 Agent                    │
├─────────────────────────────────────────────────────────────┤
│  视角基准: M15 timestamp / M15 close                         │
│  结构周期: MN1 | W1 | D1 | H4 | H1 | M30 | M15 (7个)        │
│  数据库:   data/m15_state.duckdb                             │
│  核心特性: SR突破检测 (M15 close vs 多结构周期支撑阻力位)     │
└─────────────────────────────────────────────────────────────┘
```

项目口径：周期和周期视角是正交维度。M15 Agent 是完整的 M15 视角系统，不是给 H1 系统简单增加 `m15_hex` 一列。详见 `docs/STATE_VIEWPOINT_AGENT_CONTRACT.md`。

## 与 H1 系统对比

| 特性 | H1 State | M15 State |
|------|----------|-----------|
| 视角基准 | H1 timestamp / H1 close | **M15 timestamp / M15 close** |
| 结构周期数 | 5 | **7** (+M30/M15) |
| position 基准 | H1 close vs 结构周期 SR | **M15 close vs 结构周期 SR** |
| SR突破 | 非专属 | **M15 close 突破检测** |
| 数据库 | h1_state.duckdb | **m15_state.duckdb** |
| 用途 | 日线趋势 | **短线/剥头皮** |

## 快速开始

### 1. 下载 M15 数据

```bash
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"

# 下载默认品种 (EURUSD, XAUUSD)
python fetch_m15_states.py

# 下载所有品种
python fetch_m15_states.py --all

# 下载指定品种
python fetch_m15_states.py --symbols EURUSD XAUUSD USOIL

# 下载更多天数
python fetch_m15_states.py --days 60
```

### 2. 运行 M15 Strategy Miner

```bash
# M15模式挖掘
python python/ai_engine/strategy_miner.py --mode m15

# H1模式挖掘 (默认)
python python/ai_engine/strategy_miner.py --mode h1
```

### 3. 查看结果

```bash
# 检查数据库
python -c "
import duckdb
c = duckdb.connect('data/m15_state.duckdb')
print('品种:', c.execute('SELECT DISTINCT symbol FROM m15_state_snapshot').fetchall())
print('总记录:', c.execute('SELECT COUNT(*) FROM m15_state_snapshot').fetchone())
print('SR突破:', c.execute('SELECT COUNT(*) FROM m15_state_snapshot WHERE sr_breakout=TRUE').fetchone())
"
```

## M15 专属 State Pattern

| Pattern | 说明 | 场景 |
|---------|------|------|
| `M15=6` | M15趋势+突破 | 短线趋势跟踪 |
| `M15=4` | M15单纯趋势 | 趋势确认 |
| `sr_breakout_up` | SR向上突破 | 突破做多 |
| `sr_breakout_down` | SR向下突破 | 突破做空 |
| `M15=6,sr_breakout_up` | 趋势+突破共振 | 强做多信号 |
| `multi_bull_m15(4+)` | 4+周期看涨 | 多周期共振 |
| `M15+H1 squeeze` | M15+H1收缩 | 收缩突破前 |
| `D1_resistance_break` | D1阻力位突破 | 大级别突破 |

## 编程接口

### 获取最新 M15 State

```python
from python.data.m15_state_db import M15StateDB

db = M15StateDB()

# 最新State
state = db.get_latest("EURUSD")
print(f"M15={state['m15_hex']}, SR突破={state['sr_breakout']}")

# 获取SR位
sr_levels = db.get_sr_levels("EURUSD", state['timestamp'])
for sr in sr_levels:
    print(f"{sr.timeframe} {sr.level_type}: {sr.price} (强度{sr.strength})")
```

### 运行 M15 实验

```python
from python.ai_engine.strategy_miner import StrategyMiner, ExperimentConfig

# M15模式
miner = StrategyMiner(mode="m15")

config = ExperimentConfig(
    name="m15_breakout_test",
    state_pattern="M15=6,sr_breakout_up",
    direction="long",
    hold_bars=5,
    markets=["EURUSD", "XAUUSD"],
)

result = miner.run_experiment(config)
print(f"胜率={result.win_rate:.1%}, 评分={result.score():.1f}")
```

## 文件清单

| 文件 | 说明 |
|------|------|
| `python/data/m15_state_db.py` | M15数据库+State计算引擎 |
| `fetch_m15_states.py` | M15数据下载脚本 |
| `python/ai_engine/strategy_miner.py` | 双模式Strategy Miner |
| `data/m15_state.duckdb` | M15数据库文件 |

## 注意事项

1. **MT5必须运行** 且 EA 已加载 (端口5565/5566)
2. **M15数据量大**: 30天 ≈ 2880条/品种，注意磁盘空间
3. **SR计算需要历史数据**: 至少20根K线才能计算有效SR位
4. **品种名称**: 使用 SYMBOL_MAP 映射到MT5实际名称
