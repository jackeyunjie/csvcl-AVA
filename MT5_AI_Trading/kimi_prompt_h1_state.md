# KIMI 提示词 — 构建 H1 视角 State 数据库

## 你的角色

你是数据工程师。任务：为14个外汇品种构建 H1 视角的五元组 State 数据库。

## 核心架构（必须遵守）

### 视角 Agent 契约

```
structure_tf = 结构周期（提供 base/trend/volatility）
view_tf      = 视角周期（提供 position 的基准收盘价）
state_hex    = structure_tf 的 state 在 view_tf 下的编码

H1 Agent 的含义：
  所有结构周期的 position 都用 H1 close 计算

  MN1@H1_view: MN1结构(base/trend/vol) + H1 close vs MN1 SR → mn1_hex
  W1@H1_view:  W1结构(base/trend/vol)  + H1 close vs W1 SR  → w1_hex
  D1@H1_view:  D1结构(base/trend/vol)  + H1 close vs D1 SR  → d1_hex
  H4@H1_view:  H4结构(base/trend/vol)  + H1 close vs H4 SR  → h4_hex
  H1@H1_view:  H1结构(base/trend/vol)  + H1 close vs H1 SR  → h1_hex
```

**关键：position 的基准价是 H1 close，不是各周期自己的 close。**

### 4-bit 编码公式

```
score = base(0/8) + trend_bit(0/4) + position_bit(0/2) + volatility_bit(0/1)
hex = 转为16进制（正数0-F，负数-1到-F）
sign 由 MN1 SR 的符号裁决决定
```

### 11 个不可变参数

| # | 参数 | 值 | 用途 |
|---|------|-----|------|
| 1 | BB 周期 | 20 | 布林带 |
| 2 | BB 标准差 | 2.0 | 带宽 |
| 3 | BB 分位窗口 | 20（不含当前bar） | base判定 |
| 4 | ATR 周期 | 14 | volatility_bit |
| 5 | ADX 周期 | 14 | trend_bit |
| 6 | ADX slope 窗口 | 3 bar | 趋势斜率 |
| 7 | 分形周期 k | 5（左右各2根） | SR识别 |
| 8 | 分形确认延迟 | 3 bar | SR确认 |
| 9 | 编码位数 | 4-bit | base+trend+pos+vol |
| 10 | base 值 | 仅 0 或 8 | 收缩/扩张 |
| 11 | 视角 | H1 | 所有position用H1 close |

**这些参数不可改、不可调、不可"优化"。**

## 数据源

从 MT5 拉取 K 线数据：

```
品种列表（14个外汇）：
EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCAD, USDCHF,
EURJPY, GBPJPY, AUDJPY, EURGBP, EURCHF, EURCAD, GBPCHF

时间框架：MN1, W1, D1, H4, H1
数据量：每个品种约 5000 根 D1 K线对应的各周期数据
```

**注意：MT5 的 `copy_rates_from_pos` 每次最多返回约 5000-10000 根 bar。H1 数据量大（1根D1=24根H1），可能需要分批拉取。**

## 输出格式

### DuckDB 表结构

```sql
CREATE TABLE h1_state_snapshots (
    symbol VARCHAR,           -- 品种名
    timestamp TIMESTAMP,      -- H1 bar 时间戳
    view_tf VARCHAR DEFAULT 'H1',  -- 视角周期
    mn1_hex VARCHAR,          -- MN1@H1_view
    w1_hex VARCHAR,           -- W1@H1_view
    d1_hex VARCHAR,           -- D1@H1_view
    h4_hex VARCHAR,           -- H4@H1_view
    h1_hex VARCHAR,           -- H1@H1_view
    mn1_score INTEGER,
    w1_score INTEGER,
    d1_score INTEGER,
    h4_score INTEGER,
    h1_score INTEGER,
    ef_count INTEGER,         -- 五元组中 E(14)/F(15) 的数量
    h1_close DOUBLE           -- H1 收盘价（用于后续收益率计算）
);
```

### 数据库路径

```
data/hermass_h1_state.db
```

## 实现步骤

### Step 1: 连接 MT5

```python
import MetaTrader5 as mt5
if not mt5.initialize():
    print("MT5 未运行"); exit()
```

### Step 2: 拉取各周期 K 线

```python
# 对每个品种：
# 1. 拉 D1 数据（5000根）→ 用于计算 MN1/W1/D1 结构
# 2. 拉 H4 数据（5000×6=30000根，分批）→ H4 结构
# 3. 拉 H1 数据（5000×24=120000根，分批）→ H1 结构 + 视角
# 4. 拉 W1/MN1 数据（少量）→ 大周期结构

# 分批拉取示例：
def fetch_rates(symbol, tf, total_bars, batch=5000):
    all_rates = []
    offset = 0
    while offset < total_bars:
        count = min(batch, total_bars - offset)
        r = mt5.copy_rates_from_pos(symbol, tf, offset, count)
        if r is None or len(r) == 0: break
        all_rates.extend(r)
        offset += len(r)
    return all_rates
```

### Step 3: 构建各周期 KLine 序列

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class KLine:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

def rates_to_klines(rates):
    from datetime import datetime
    return [KLine(
        timestamp=datetime.fromtimestamp(r[0]),
        open=r[1], high=r[2], low=r[3], close=r[4], volume=r[5]
    ) for r in rates]
```

### Step 4: 计算 State（核心逻辑）

对每个结构周期，计算 4 个 bit：

```python
def calc_state_for_structure(structure_klines, view_close, params):
    """
    structure_klines: 结构周期的 KLine 序列
    view_close: 当前 H1 bar 的收盘价（视角基准价）
    params: 11个不可变参数

    返回: (score, hex_code)
    """
    # 1. base: BB带宽分位
    base = calc_base(structure_klines, params)

    # 2. trend: ADX/DI 判定
    trend = calc_trend(structure_klines, params)

    # 3. position: view_close vs 结构周期 SR（用 view_close，不用结构周期 close！）
    position = calc_position(view_close, structure_klines, params)

    # 4. volatility: ATR 扩张
    volatility = calc_volatility(structure_klines, params)

    magnitude = base + trend * 4 + position + volatility
    sign = calc_sign(view_close, structure_klines, params)  # MN1 SR 优先
    score = sign * magnitude
    hex_code = score_to_hex(score)

    return score, hex_code
```

### Step 5: 遍历每根 H1 bar，输出五元组

```python
for h1_bar in h1_klines:
    view_close = h1_bar.close
    ts = h1_bar.timestamp

    mn1_score, mn1_hex = calc_state_for_structure(mn1_klines, view_close, params)
    w1_score, w1_hex = calc_state_for_structure(w1_klines, view_close, params)
    d1_score, d1_hex = calc_state_for_structure(d1_klines, view_close, params)
    h4_score, h4_hex = calc_state_for_structure(h4_klines, view_close, params)
    h1_score, h1_hex = calc_state_for_structure(h1_klines, view_close, params)

    ef_count = sum(1 for s in [mn1_score, w1_score, d1_score, h4_score, h1_score]
                   if s in (14, 15))

    # 写入 DuckDB
    conn.execute("INSERT INTO h1_state_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (symbol, ts, 'H1', mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex,
         mn1_score, w1_score, d1_score, h4_score, h1_score, ef_count, view_close))
```

### Step 6: 添加向前收益率

```python
# 对每个品种，按时间排序，计算 H1 bar 后的收益率
# fwd_4h = 4根H1 bar后的收益率（约4小时）
# fwd_24h = 24根H1 bar后的收益率（约1天）
# fwd_120h = 120根H1 bar后的收益率（约5天）
```

### Step 7: 验证

```python
# 验证1: 数据量检查
# 14品种 × ~100000根H1 = ~1,400,000 条（预期）

# 验证2: 与 D1 Agent 交叉验证
# 取某一天的 D1 bar close 时间点，H1 Agent 的五元组应该和 D1 Agent 的三元组一致
# （因为在 D1 bar close 时刻，H1 close ≈ D1 close）

# 验证3: EF 分布
# H1 视角的 EF 分布应比 D1 视角更分散（H1 更灵敏）

# 验证4: 符号裁决一致性
# 同一时刻，H1 Agent 和 D1 Agent 的 sign 应一致（因为都用 MN1 SR）
```

## 执行命令

```powershell
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"
python build_h1_state_db.py
```

## 注意事项

1. **H1 数据量大**：14品种 × 100000根 ≈ 140万条。预计运行 10-30 分钟。
2. **MT5 拉取可能超时**：用分批拉取，每批 5000 根。
3. **position 用 H1 close**：这是最容易犯的错。不要用 D1/W1/MN1 的 close。
4. **base/trend/volatility 用结构周期数据**：不要用 H1 数据计算 MN1 的 base。
5. **负值 State**：sign 由 MN1 SR 决定，和 D1 Agent 用同一套规则。
6. **DuckDB 写入**：用批量 INSERT，不要每条 commit。
7. **完成后运行 `python validate_h1_state.py`** 验证数据质量。

## 产出

```
data/hermass_h1_state.db
├── h1_state_snapshots  (~1,400,000条)
├── h1_fwd              (向前收益率)
└── h1_slices           (State组合频率)
```
