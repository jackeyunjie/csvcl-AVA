# 团队任务分配

## 扫描结果摘要

Top 5 策略已验证（10模式 × 72参数 = 720实验）：

| # | 模式 | 方向 | 持仓 | 胜率 | PF | Q |
|---|------|------|------|------|-----|---|
| 1 | D1=8,H4=8,H1=-F | short | 12h | 92% | 20 | 76.5 |
| 2 | D1=E,H4=6,H1=6 | long | 48h | 88% | 2.7 | 71.7 |
| 3 | D1=6,H4=6,H1=6 | long | 12h | 82.5% | 2.6 | 69.6 |
| 4 | D1=8,H4=8,H1=-D | short | 24h | 80% | 2.0 | 65.5 |
| 5 | D1=8,H4=-F,H1=-F | short | 12h | 88.5% | 1.5 | 64.3 |

---

## KIMI 任务：扩展数据源

**目标**：扩大策略搜索引擎的数据基础

### 任务1: 拉取更多品种
```bash
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"
python build_h1_state_real.py --symbols HK_50 CHINA_A50 EURUSD GBPUSD USDJPY --days 90 --terminal "D:\Program Files\Ava Trade MT5 Terminal\terminal64.exe"
```

### 任务2: 验证数据完整性
```python
from python.data.h1_state_db import H1StateDB
h1db = H1StateDB("data/h1_state.duckdb")
for sym in ['US_30', 'US_500', 'US_TECH100', 'HK_50', 'CHINA_A50', 'EURUSD', 'GBPUSD', 'USDJPY']:
    s = h1db.get_summary(sym)
    print(f"{sym}: {s['total_rows']} rows, {s['earliest']} ~ {s['latest']}")
h1db.close()
```

### 任务3: 重新运行全量扫描
```bash
python strategy_miner.py --scan-all --top 20
```

**成功标准**：
- [ ] 8+ 品种有数据
- [ ] 每品种 2000+ 条
- [ ] 扫描报告更新

---

## Codex 任务：实验管理系统

**目标**：让实验可查询、可对比、可追溯

### 任务1: 创建实验查询工具
创建 `query_experiments.py`：
```python
"""
实验查询工具
用法:
  python query_experiments.py --top 20           # Top 20 策略
  python query_experiments.py --pattern "D1=8"   # 按模式查
  python query_experiments.py --quality 70       # 质量分>70
  python query_experiments.py --compare          # 交叉对比
"""
```

### 任务2: 生成 Strategy-State 适配矩阵
```python
# 从 experiments.db 生成矩阵
# 行: State 模式
# 列: 策略参数 (hold/sl/tp)
# 值: 质量分
# 输出: CSV + 热力图
```

### 任务3: 实验报告增强
在 `data/strategy_report.md` 中添加：
- 每个 Top 策略的详细交易记录
- 按品种分解的胜率
- 按月份分解的稳定性
- 与基准（买入持有）的对比

**成功标准**：
- [ ] query_experiments.py 可运行
- [ ] Strategy-State 矩阵 CSV 生成
- [ ] 报告包含品种/月份分解

---

## DeepSeek 任务：策略组合引擎设计

**目标**：从"单策略"升级到"策略池"

### 设计要求
1. **多策略并行**：5个Top策略同时运行
2. **仓位分配**：按质量分加权
3. **风险预算**：总风险不超过账户的X%
4. **去相关性**：避免同向策略重叠

### 设计输出
```markdown
# 策略组合引擎设计文档

## 架构
- 策略池管理器
- 信号聚合器
- 仓位计算器
- 风险管理器

## 仓位分配公式
weight_i = quality_i / sum(quality)
position_i = weight_i * risk_budget / stop_loss_i

## 风险控制
- 单策略最大仓位: 20%
- 同向最大仓位: 60%
- 总风险上限: 5% 账户
- 相关性过滤: corr > 0.7 的策略合并
```

**成功标准**：
- [ ] 设计文档完成
- [ ] 仓位分配公式验证
- [ ] Python 原型代码

---

## Claude（总参谋长）职责

1. **质量审查**：验证扫描结果的统计显著性
2. **架构决策**：审批组合引擎设计
3. **任务协调**：确保三方输出可集成
4. **风险评估**：识别过拟合/数据泄露风险

---

## 时间线

| 阶段 | 任务 | 负责人 | 优先级 |
|------|------|--------|--------|
| 本周 | 扩展数据源 | KIMI | P1 |
| 本周 | 实验查询工具 | Codex | P1 |
| 下周 | 组合引擎设计 | DeepSeek | P2 |
| 下周 | Walk-forward 验证 | KIMI+Codex | P1 |
| 第三周 | Paper Trading | 全员 | P1 |
