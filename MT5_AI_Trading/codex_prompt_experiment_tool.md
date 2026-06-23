# Codex 提示词 - 实验查询工具 + Strategy-State 矩阵

## 你的角色
量化工程师，负责构建实验管理和策略发现工具。

## 当前状态
- `strategy_miner.py` 已运行 720 次实验，结果存入 `data/experiments.duckdb`
- Top 5 策略已发现（最高胜率 92.0%）
- 需要：查询工具 + 可视化矩阵 + 增强报告

## 任务清单

### 任务1: 创建实验查询工具 `query_experiments.py`

功能：
```bash
python query_experiments.py --top 20              # Top 20 策略
python query_experiments.py --pattern "D1=8"      # 按模式查
python query_experiments.py --quality 70          # 质量分 > 70
python query_experiments.py --direction long      # 只看做多
python query_experiments.py --direction short     # 只看做空
python query_experiments.py --symbol US_30        # 按品种查
python query_experiments.py --compare             # H1 vs M30 对比
python query_experiments.py --export csv          # 导出 CSV
python query_experiments.py --export md           # 导出 Markdown
```

数据库结构（`data/experiments.duckdb`）：
```sql
-- experiments 表
experiment_id VARCHAR PRIMARY KEY
pattern VARCHAR           -- 如 "D1=6,H4=6,H1=6"
pattern_desc VARCHAR      -- 如 "D1=6(trend,breakout) + H1=6(trend,breakout)"
direction VARCHAR          -- "long" / "short"
hold_bars INTEGER          -- 持仓 H1 K线数
stop_loss_pct DOUBLE
take_profit_pct_pct DOUBLE
symbols VARCHAR            -- 逗号分隔
total_trades INTEGER
win_rate DOUBLE            -- 0-1
avg_pnl DOUBLE             -- 平均收益 %
total_pnl DOUBLE           -- 总收益 %
sharpe_ratio DOUBLE
max_drawdown DOUBLE        -- 最大回撤 %
profit_factor DOUBLE       -- 盈亏比
quality_score DOUBLE       -- 0-100 综合质量分
year_stability DOUBLE      -- 年份稳定性
symbol_stability DOUBLE    -- 品种稳定性
created_at TIMESTAMP
status VARCHAR             -- "candidate" / "validated" / "live"

-- experiment_trades 表
experiment_id VARCHAR
symbol VARCHAR
direction VARCHAR
entry_time TIMESTAMP
exit_time TIMESTAMP
hold_bars INTEGER
pnl_pct DOUBLE
exit_reason VARCHAR        -- "stop_loss" / "take_profit" / "time_exit"

-- strategy_state_matrix 表
state_pattern VARCHAR
experiment_id VARCHAR
quality_score DOUBLE
win_rate DOUBLE
direction VARCHAR
```

### 任务2: 生成 Strategy-State 适配矩阵

从 experiments.db 生成 CSV 矩阵：

```
行: State 模式 (如 D1=6,H4=6,H1=6)
列: 策略参数组合 (hold=12/sl=2/tp=3)
值: 质量分 (0-100)
```

输出: `data/strategy_state_matrix.csv`

```python
# 伪代码
matrix = {}
for exp in experiments:
    pattern = exp.pattern
    params = f"hold={exp.hold_bars}/sl={exp.stop_loss_pct}/tp={exp.take_profit_pct}"
    matrix[(pattern, params)] = exp.quality_score

# 保存为 CSV
df = pd.DataFrame(matrix).T.unstack()
df.to_csv("data/strategy_state_matrix.csv")
```

### 任务3: 增强策略报告

在 `data/strategy_report.md` 中添加：

1. **品种分解**：每个 Top 策略在各品种上的胜率
2. **月份分解**：按季度统计胜率稳定性
3. **做多 vs 做空**：分别统计
4. **止损/止盈分析**：各参数组合的表现
5. **与基准对比**：策略收益 vs 买入持有

### 任务4: 创建 Walk-forward 验证框架

```python
"""
Walk-forward 验证

将数据分为 N 段：
- 训练段: 前 70% 数据
- 测试段: 后 30% 数据

对每个训练段找到最优参数，在测试段验证
"""
class WalkForwardValidator:
    def __init__(self, n_splits=3, train_ratio=0.7):
        self.n_splits = n_splits
        self.train_ratio = train_ratio

    def validate(self, pattern, data):
        # 1. 将数据按时间分为 n_splits 段
        # 2. 每段: 训练70% + 测试30%
        # 3. 训练段找最优参数
        # 4. 测试段验证
        # 5. 返回各段的 OOS (Out-of-Sample) 结果
        pass
```

## 成功标准
- [ ] query_experiments.py 可运行，支持所有查询模式
- [ ] strategy_state_matrix.csv 生成
- [ ] 报告包含品种/月份分解
- [ ] Walk-forward 框架代码完成

## 参考文件
- `strategy_miner.py` — 策略搜索引擎（已完成）
- `data/experiments.duckdb` — 实验数据库（已有数据）
- `data/strategy_report.md` — 当前报告
- `python/ai_engine/state_hex_encoding.py` — State 编码系统

## 输出文件
| 文件 | 用途 |
|------|------|
| `query_experiments.py` | 实验查询 CLI |
| `data/strategy_state_matrix.csv` | 适配矩阵 |
| `data/strategy_report.md` | 增强报告 |
| `walk_forward.py` | Walk-forward 验证框架 |
