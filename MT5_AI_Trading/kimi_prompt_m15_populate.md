# KIMI 提示词 - 填充 M15 State 数据库

## 你的角色
数据工程师，负责从 MT5 拉取数据并填充 M15 State 数据库。

## 前置条件
- M15 State 系统已创建: `python/data/m15_state_db.py`
- MT5 连接正常: 账户 89467841, 终端 `D:\Program Files\Ava Trade MT5 Terminal\terminal64.exe`
- H1 State 数据库已有 37 个品种数据

## 任务清单

### 任务1: 创建 M15 数据填充脚本
创建 `build_m15_state.py`：

```python
"""
从 MT5 拉取 7 个周期的 OHLCV 数据，计算 M15 State 并存入数据库

用法:
  python build_m15_state.py --symbols US_30 US_500 US_TECH100 --days 30
  python build_m15_state.py --terminal "D:\Program Files\Ava Trade MT5 Terminal\terminal64.exe"
"""
```

核心逻辑：
1. 连接 MT5（指定终端路径）
2. 对每个品种，拉取 7 个周期的 OHLCV 数据
3. 调用 M15StateManager.process_symbol() 计算 state
4. 结果存入 data/m15_state.duckdb

### 任务2: 修复 M15StateDB 缺少的 get_summary 方法
在 `python/data/m15_state_db.py` 中添加：

```python
def get_summary(self, symbol: str) -> Dict:
    conn = self._get_conn()
    result = conn.execute(
        "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM m15_state_snapshot WHERE symbol = ?",
        [symbol]
    ).fetchone()
    return {
        "symbol": symbol,
        "total_rows": result[0],
        "earliest": str(result[1]) if result[1] else None,
        "latest": str(result[2]) if result[2] else None,
    }
```

### 任务3: 填充 3 个股指的 M15 数据
```bash
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"
python build_m15_state.py --symbols US_30 US_500 US_TECH100 --days 30 --terminal "D:\Program Files\Ava Trade MT5 Terminal\terminal64.exe"
```

### 任务4: 验证数据完整性
```python
from python.data.m15_state_db import M15StateDB
db = M15StateDB()
for sym in ['US_30', 'US_500', 'US_TECH100']:
    s = db.get_summary(sym)
    print(f"{sym}: {s['total_rows']} rows, {s['earliest']} ~ {s['latest']}")
    latest = db.get_latest(sym)
    if latest:
        print(f"  最新: M15={latest.get('m15_hex')}, SR突破={latest.get('sr_breakout')}")
db.close()
```

### 任务5: 生成 SR 突破统计报告
```python
# 统计各品种的 SR 突破频率
# 按 timeframe 分组统计 break_up / break_down / none
```

## 成功标准
- [ ] build_m15_state.py 可运行
- [ ] 3 个股指各有 1000+ 条 M15 State
- [ ] SR 突破标志正确（break_up/break_down/none）
- [ ] get_summary 方法可调用

## 参考文件
- `python/data/m15_state_db.py` — M15 State 数据库（已有）
- `build_h1_state_real.py` — H1 构建脚本（参考结构）
- `python/backtest_platform/data_layer.py` — MT5 数据桥接

## 注意事项
- M15 数据量大：30天 × 96根/天 = 2880条/品种
- 7 个周期需要分别拉取，总数据量约 20000 条/品种
- 构建可能需要 15-30 分钟/品种
- 使用 count 方式拉取（更可靠）：`fetch_ohlcv_from_pos`
