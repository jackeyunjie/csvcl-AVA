# KIMI 任务：扩展 State 数据下载

## 任务目标

为 Strategy Miner 提供多品种、多周期的 State 数据，支持策略挖掘覆盖更多市场。

## 数据需求

### 品种列表（9个）

| 类别 | 品种 | MT5名称 | 说明 |
|------|------|---------|------|
| 美股股指 | US_30 | US30 | 道琼斯 |
| 美股股指 | US_500 | US500 | 标普500 |
| 美股股指 | US_TECH100 | USTEC | 纳斯达克100 |
| 亚洲股指 | HK_50 | HK50 | 恒生指数 |
| 亚洲股指 | CHINA_A50 | CHINA50 | 富时A50 |
| 商品 | XAUUSD | XAUUSD | 黄金 |
| 商品 | USOIL | USOIL | 原油 |
| 加密货币 | BTCUSD | BTCUSD | 比特币 |
| 外汇 | EURUSD | EURUSD | 欧元美元 |

### 周期列表（6个）

MN1, W1, D1, H4, H1, M15

### 数据量

- 每个品种 × 每个周期 = 90天历史数据
- 预计总记录数：9品种 × 6周期 × 90天 ≈ 4860条（H1基准）

## 执行步骤

### Step 1: 确认MT5可交易品种

在 AVATRADE MT5 中检查以下品种是否可交易：
1. 打开市场报价窗口
2. 搜索：US30, US500, USTEC, HK50, CHINA50, XAUUSD, USOIL, BTCUSD
3. 确认每个品种都有数据

### Step 2: 运行数据下载

```bash
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"

# 下载所有新品种
python fetch_extended_states.py --symbols HK_50 CHINA_A50 XAUUSD USOIL BTCUSD

# 或下载全部
python fetch_extended_states.py
```

### Step 3: 验证数据

```bash
# 检查数据库
python -c "
import duckdb
c = duckdb.connect('data/h1_state.duckdb')
print('品种:', c.execute('SELECT DISTINCT symbol FROM h1_state_snapshot').fetchall())
print('总记录:', c.execute('SELECT COUNT(*) FROM h1_state_snapshot').fetchone())
print('周期样本:', c.execute('SELECT symbol, COUNT(*) FROM h1_state_snapshot GROUP BY symbol').fetchall())
"
```

### Step 4: 运行Strategy Miner

```bash
# 重新挖掘含新品种的策略
python python/ai_engine/strategy_miner.py
```

## 注意事项

1. **AVATRADE MT5必须运行** 且 EA 已加载
2. **品种名称映射**：使用 SYMBOL_MAP 中的 MT5 名称
3. **M15数据**：需要更多存储空间（H1的4倍）
4. **加密货币**：BTCUSD 可能24小时交易，注意时间对齐

## 交付标准

- [ ] 9个品种全部有数据
- [ ] 每个品种至少6个周期
- [ ] 90天历史数据完整
- [ ] Strategy Miner 能正常跑出新结果

## 当前状态

- 已有数据：US_30, US_500, US_TECH100（6480条）
- 待下载：HK_50, CHINA_A50, XAUUSD, USOIL, BTCUSD, EURUSD
- 待扩展：M15周期
