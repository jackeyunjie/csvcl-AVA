# KIMI2 提示词 - Walk-forward 验证 + 跨市场分析

## 你的角色
量化验证工程师，负责验证策略的统计显著性和跨市场稳健性。

## 与 KIMI 的分工
- **KIMI**: 数据拉取、品种扩展、策略扫描（已完成）
- **KIMI2**: Walk-forward 验证、跨市场分析、最终报告（你做）

## 当前状态
- 13品种 H1 State 数据已就绪（28,081条）
- 720次实验已完成，Top 5 策略已发现
- `walk_forward.py` 和 `query_experiments.py` 已创建

## Top 5 策略（待验证）

| # | 模式 | 方向 | 持仓 | 胜率 | PF | Q |
|---|------|------|------|------|-----|---|
| 1 | D1=8,H4=8,H1=-F | short | 12h | 92% | 20 | 76.5 |
| 2 | D1=E,H4=6,H1=6 | long | 48h | 88% | 2.7 | 71.7 |
| 3 | D1=6,H4=6,H1=6 | long | 12h | 82.5% | 2.6 | 69.6 |
| 4 | D1=8,H4=8,H1=-D | short | 24h | 80% | 2.0 | 65.5 |
| 5 | D1=8,H4=-F,H1=-F | short | 12h | 88.5% | 1.5 | 64.3 |

## 任务清单

### 任务1: Walk-forward 验证 Top 3 策略

对每个 Top 策略运行 Walk-forward 验证：

```bash
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"

# 策略1: D1=8,H4=8,H1=-F (short, 最高胜率)
python walk_forward.py --pattern "D1=8,H4=8,H1=-F" --splits 3 --train-ratio 0.7

# 策略2: D1=E,H4=6,H1=6 (long)
python walk_forward.py --pattern "D1=E,H4=6,H1=6" --splits 3 --train-ratio 0.7

# 策略3: D1=6,H4=6,H1=6 (long)
python walk_forward.py --pattern "D1=6,H4=6,H1=6" --splits 3 --train-ratio 0.7
```

**关注指标**：
- OOS (Out-of-Sample) 胜率是否稳定？
- 各段的 Sharpe 是否一致？
- 训练段最优参数在测试段是否依然有效？

### 任务2: 跨市场分析

将 13 个品种分为 4 类，分析策略在各类上的表现：

| 类别 | 品种 |
|------|------|
| 美股股指 | US_30, US_500, US_TECH100 |
| 亚太股指 | HK_50, CHINA_A50, JP225 |
| 欧洲股指 | GER30, EUROPE_50, UK_100 |
| 商品/加密 | XAUUSD, USOIL, BTCUSD |
| 外汇 | EURUSD, GBPUSD, USDJPY |

分析方法：
```python
# 从 experiments.db 按品种分组统计
import duckdb
conn = duckdb.connect("data/experiments.duckdb", read_only=True)

# 查询各品种的最佳策略
df = conn.execute("""
    SELECT pattern, direction, hold_bars, win_rate, quality_score, symbols
    FROM experiments
    WHERE quality_score > 60
    ORDER BY quality_score DESC
    LIMIT 50
""").fetchdf()

# 按品种类别分组分析
# ...
```

**输出**: 哪些策略在哪些市场类别上最有效？

### 任务3: 参数敏感性分析

对 Top 1 策略（D1=8,H4=8,H1=-F）做参数敏感性测试：

```python
# 固定模式，变化参数
hold_options = [6, 12, 18, 24, 36, 48]
sl_options = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
tp_options = [1.0, 2.0, 3.0, 5.0, 8.0, 10.0]

# 对每个参数组合运行回测
# 输出: 参数敏感性热力图数据
```

**关注**：参数变化时胜率是否稳定？还是只有特定参数组合才有效（过拟合风险）？

### 任务4: 生成最终验证报告

输出文件: `data/walkforward_report.md`

报告内容：
```markdown
# 策略验证报告

## Walk-forward 结果
| 策略 | 段1 OOS | 段2 OOS | 段3 OOS | 平均 | 稳定性 |
|------|---------|---------|---------|------|--------|

## 跨市场表现
| 策略 | 美股 | 亚太 | 欧洲 | 商品 | 外汇 |
|------|------|------|------|------|------|

## 参数敏感性
| 参数组合 | 胜率 | Sharpe | 是否过拟合 |
|----------|------|--------|-----------|

## 最终推荐
- 可实盘策略: [列表]
- 需进一步观察: [列表]
- 淘汰: [列表]
```

## 成功标准
- [ ] 3 个 Top 策略 Walk-forward 验证完成
- [ ] 跨市场分析完成（5个市场类别）
- [ ] 参数敏感性分析完成
- [ ] 最终验证报告生成 (`data/walkforward_report.md`)
- [ ] 明确哪些策略可实盘，哪些需淘汰

## 参考文件
- `walk_forward.py` — Walk-forward 验证框架
- `query_experiments.py` — 实验查询工具
- `strategy_miner.py` — 策略搜索引擎
- `data/experiments.duckdb` — 实验数据库
- `data/h1_state.duckdb` — State 数据库
- `data/strategy_report.md` — 当前策略报告

## 注意事项
- DuckDB 单写多读，如果 `h1_state.duckdb` 被占用，用 read_only 模式连接
- Walk-forward 运行时间可能较长（每策略约 5-10 分钟）
- 如果 walk_forward.py 有 bug，直接修复后再运行
- 所有输出保存到 `data/` 目录
