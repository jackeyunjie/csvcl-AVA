# KIMI 提示词 - 建立 M15 State 数据库

## 你的角色
你是数据工程师，负责为股指建立 M15（15分钟）级别的 State 数据库。

## 背景
当前系统已有 H1 State 数据库（US_30, US_500, US_TECH100，各2160条）。
现在需要建立 M15 数据库，用于更精细的入场时机判断。

## 核心架构

### M15 独立视角 Agent（多个结构周期）
```
MN1 structure + M15 close → mn1_hex
W1  structure + M15 close → w1_hex
D1  structure + M15 close → d1_hex
H1  structure + M15 close → h1_hex
M15 structure + M15 close → m15_hex
```

### 数据对齐
每行 = 1根 M15 K线，同时记录5个周期的 state_hex：
```
timestamp(M15) | MN1_hex | W1_hex | D1_hex | H1_hex | M15_hex | durations
```

## 任务清单

### 任务1: 修改数据拉取脚本
修改 `build_h1_state_real.py`，添加 M15 支持：

```python
# 在 build_h1_state_real.py 中修改：
# 1. 添加 M15 到时间框架列表
timeframes = ["MN1", "W1", "D1", "H1", "M15"]

# 2. 调整 bar 数量（M15 数据量大）
bar_counts = {
    "MN1": 60,
    "W1": 260,
    "D1": days,
    "H1": days * 24,
    "M15": days * 24 * 4,  # 每天96根M15
}

# 3. 修改引擎调用，添加 M15 数据
engine.add_m15_dataframe(m15_df)  # 新增
```

### 任务2: 修改 KVBStateHexEngine
在 `python/ai_engine/kvb_state_hex_engine.py` 中添加 M15 支持：

```python
# 1. 添加 M15 数据存储
self.m15_data: List[KLine] = []

# 2. 添加 M15 数据输入方法
def add_m15_dataframe(self, df: pd.DataFrame):
    """批量添加M15数据（独立计算）"""
    required = ['timestamp', 'open', 'high', 'low', 'close']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"缺少必要列: {col}")
    for _, row in df.iterrows():
        ts = row['timestamp']
        if isinstance(ts, str):
            ts = pd.to_datetime(ts)
        self.m15_data.append(KLine(ts, row['open'], row['high'],
                                   row['low'], row['close'],
                                   row.get('volume', 0.0)))
    self.m15_data.sort(key=lambda k: k.timestamp)

# 3. 修改 compute_quintuplets() → compute_sextuplets()
# 添加 M15 Agent 计算
```

### 任务3: 修改 h1_state_db.py
在 `python/data/h1_state_db.py` 中扩展数据库表：

```python
# 1. 添加 M15 到表结构
conn.execute("""
    CREATE TABLE IF NOT EXISTS m15_state_snapshot (
        symbol VARCHAR NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        mn1_hex VARCHAR,
        w1_hex VARCHAR,
        d1_hex VARCHAR,
        h1_hex VARCHAR,
        m15_hex VARCHAR,
        mn1_duration INTEGER DEFAULT 0,
        w1_duration INTEGER DEFAULT 0,
        d1_duration INTEGER DEFAULT 0,
        h1_duration INTEGER DEFAULT 0,
        m15_duration INTEGER DEFAULT 0,
        PRIMARY KEY (symbol, timestamp)
    )
""")

# 2. 添加 save_sextuplets() 方法
# 3. 添加 query_m15() 方法
```

### 任务4: 创建独立的 M15 构建脚本
创建 `build_m15_state.py`：

```python
"""
构建 M15 State 数据库

用法:
  python build_m15_state.py --symbols US_30 US_500 US_TECH100 --days 30
  python build_m15_state.py --terminal "D:\Program Files\Ava Trade MT5 Terminal\terminal64.exe"
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from backtest_platform.data_layer import MT5DataBridge
from ai_engine.kvb_state_hex_engine import KVBStateHexEngine
from data.h1_state_db import H1StateDB

def build_m15_state(symbols, days, terminal_path):
    """构建 M15 State 数据库"""
    bridge = MT5DataBridge(terminal_path=terminal_path)
    if not bridge.connect():
        print("MT5 连接失败")
        return

    timeframes = ["MN1", "W1", "D1", "H1", "M15"]
    bar_counts = {
        "MN1": 60,
        "W1": 260,
        "D1": days,
        "H1": days * 24,
        "M15": days * 24 * 4,
    }

    h1db = H1StateDB("data/m15_state.duckdb")  # 新数据库

    for symbol in symbols:
        print(f"\n{'='*50}")
        print(f"构建 {symbol} M15 State")
        print(f"{'='*50}")

        # 拉取数据
        multi = {}
        for tf in timeframes:
            try:
                multi[tf] = bridge.fetch_ohlcv_from_pos(symbol, tf, bar_counts[tf])
                print(f"  {tf}: {len(multi[tf]) if multi[tf] is not None else 0} 条")
            except Exception as e:
                print(f"  {tf}: 失败 {e}")
                multi[tf] = None

        # 初始化引擎
        engine = KVBStateHexEngine()

        # 加载结构周期数据，共同服务于 M15 视角 Agent
        if multi.get("MN1") is not None:
            engine.add_mn1_dataframe(multi["MN1"])
        if multi.get("W1") is not None:
            engine.add_w1_dataframe(multi["W1"])
        if multi.get("D1") is not None:
            engine.add_d1_dataframe(multi["D1"])
        if multi.get("H1") is not None:
            engine.add_h1_dataframe(multi["H1"])
        if multi.get("M15") is not None:
            engine.add_m15_dataframe(multi["M15"])

        # 计算六元组
        sextuplets = engine.compute_sextuplets()
        print(f"  六元组: {len(sextuplets)} 条")

        # 存入数据库
        saved = h1db.save_sextuplets(symbol, sextuplets)
        print(f"  已保存: {saved} 条")

    h1db.close()
    bridge.disconnect()
    print("\n构建完成！")
```

### 任务5: 验证数据
```python
# 查询 M15 数据
from python.data.h1_state_db import H1StateDB
h1db = H1StateDB("data/m15_state.duckdb")
df = h1db.query_m15("US_30", limit=10)
print(df[['timestamp', 'mn1_hex', 'w1_hex', 'd1_hex', 'h1_hex', 'm15_hex']].to_string(index=False))
h1db.close()
```

## 关键要点

1. **M15 是独立视角 Agent** — 不从 H1 下沉 state；使用 M15 timestamp/M15 close 观察各结构周期
2. **数据量大** — 90天 × 96根/天 = 8640条 M15 K线/品种
3. **对齐基准** — 每行以 M15 时间戳为基准，其他周期查找对应状态
4. **存储独立** — 使用 `m15_state.duckdb`（不污染 H1 数据库）

## 成功标准
- [ ] M15 数据拉取成功（每品种 8000+ 条）
- [ ] 六元组计算正确（M15 hex 是标准十六进制）
- [ ] 数据库查询正常
- [ ] 各品种数据完整（US_30, US_500, US_TECH100）

## 参考文件
- `build_h1_state_real.py` — H1 构建脚本（参考结构）
- `python/ai_engine/kvb_state_hex_engine.py` — State 引擎（需修改）
- `python/data/h1_state_db.py` — 数据库模块（需扩展）
- `python/backtest_platform/data_layer.py` — MT5 数据桥接

## 注意事项
- MT5 终端路径：`D:\Program Files\Ava Trade MT5 Terminal\terminal64.exe`
- 账户：89467841 (AVATRADE)
- M15 数据量大，构建可能需要 10-20 分钟/品种
- 如果内存不足，可以分批构建（每次1个品种）
