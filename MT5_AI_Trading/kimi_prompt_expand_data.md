# KIMI 提示词 - 扩展 H1 State 数据库品种

## 你的角色
数据工程师，负责扩展 H1 State 数据库的品种覆盖。

## 优先级
**现货/商品 > 股票 > 股指 > 外汇**（少拉外汇，多拉现货和股票）

## 当前状态
已有 11 个品种。目标：加 7 个新品种（现货+股票），总计 18 个。

## 品种清单

### 已有（11个）
| 品种 | MT5 符号 | 类型 |
|------|---------|------|
| US_30 | US_30 | 股指 |
| US_500 | US_500 | 股指 |
| US_TECH100 | US_TECH100 | 股指 |
| EURUSD | EURUSD | 外汇 |
| XAUUSD | GOLD | 现货 |
| USOIL | CrudeOIL | 现货 |
| BTCUSD | BTCUSD | 加密 |
| HK_50 | HK_50 | 股指 |
| CHINA_A50 | CHINA_A50 | 股指 |
| GER30 | GERMANY_40 | 股指 |
| JP225 | JAPAN_225 | 股指 |

### 新增 - 现货/商品（3个）
| 品种 | MT5 符号 | 说明 |
|------|---------|------|
| 白银 | SILVER | 贵金属 |
| 布伦特原油 | BRENT_OIL | 能源 |
| 天然气 | NATURAL_GAS | 能源 |

### 新增 - 股票（4个，大盘蓝筹）
| 品种 | MT5 符号 | 说明 |
|------|---------|------|
| 苹果 | #APPLE | 科技 |
| 微软 | #MICROSOFT | 科技 |
| 英伟达 | #NVIDIA | 科技/AI |
| 特斯拉 | #TESLA | 新能源 |

## 执行步骤

### Step 1: 拉取现货/商品数据
```bash
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"
python build_h1_state_real.py --symbols SILVER BRENT_OIL NATURAL_GAS --days 90
```

### Step 2: 拉取股票数据
```bash
python build_h1_state_real.py --symbols "#APPLE" "#MICROSOFT" "#NVIDIA" "#TESLA" --days 90
```

### Step 3: 验证所有品种
```python
from python.data.h1_state_db import H1StateDB
h1db = H1StateDB("data/h1_state.duckdb")
all_symbols = [
    "US_30", "US_500", "US_TECH100", "EURUSD", "XAUUSD", "USOIL", "BTCUSD",
    "HK_50", "CHINA_A50", "GER30", "JP225",
    "SILVER", "BRENT_OIL", "NATURAL_GAS",
    "#APPLE", "#MICROSOFT", "#NVIDIA", "#TESLA"
]
for sym in all_symbols:
    s = h1db.get_summary(sym)
    status = "OK" if s["total_rows"] > 0 else "EMPTY"
    print(f"  {sym:20s} {s['total_rows']:>6} rows  [{status}]")
h1db.close()
```

### Step 4: 重新运行策略扫描
```bash
python strategy_miner.py --scan-all --top 20
```

## 成功标准
- [ ] 18 个品种全部有数据
- [ ] 现货/商品 3 个品种 2000+ 条
- [ ] 股票 4 个品种 2000+ 条
- [ ] 策略扫描完成，报告更新
- [ ] 对比现货/股票 vs 股指的策略表现差异

## 参考文件
- `build_h1_state_real.py` — 构建脚本
- `python/data/h1_state_db.py` — 数据库
- `strategy_miner.py` — 策略搜索引擎

## MT5 配置
- 终端: `D:\Program Files\Ava Trade MT5 Terminal\terminal64.exe`
- 账户: 89467841 (AVATRADE)
