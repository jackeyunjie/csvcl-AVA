---
name: contraction-alert
description: 运行D1/H1/M15多周期收缩信号观察报警统计报告。当用户说"收缩报警"、"收缩统计"、"收缩信号"、"contraction alert"时触发。生成各周期收缩等级统计、跨周期同步收缩警报、优先品种收缩速览、突破方向统计和关键观察推荐。
---

# 收缩信号观察报警 Skill

## 功能

运行 `contraction_alert_report.py` 生成 D1/H1/M15 三个交易周期的收缩状态统计报告。

## 触发条件

- 用户说"收缩报警"
- 用户说"收缩统计"
- 用户说"收缩信号"
- 用户说"contraction alert"

## 执行命令

```bash
cd MT5_AI_Trading
python contraction_alert_report.py
```

## 报告内容

### 1. 各周期收缩统计
- D1 Agent: 日线级别收缩品种数及等级分布
- H1 Agent: 小时级别收缩品种数及等级分布
- M15 Agent: 15分钟级别收缩品种数及等级分布

### 2. 跨周期同步收缩
- 找出 D1↔H1↔M15 同时收缩的品种
- 标记突破方向冲突（如 D1 向上、H1 向下）

### 3. 优先品种收缩速览
- 25个主要交易品种的收缩状态表格
- 最高收缩等级和警报级别

### 4. 突破方向统计
- 向上突破预期品种数
- 向下突破预期品种数
- 整体多空偏向判断

### 5. 关键观察推荐
- Top 5 最值得关注的品种
- 跨周期同步突破概率

## 定时任务

可配置定时运行：
```bash
# 每4小时自动运行收缩报告
python contraction_scheduler.py --mode report

# 每4小时运行完整分析（交易机会+收缩报警）
python contraction_scheduler.py --mode full

# 立即执行一次测试
python contraction_scheduler.py --mode report --immediate
```

## 收缩等级定义

| 等级 | Hex | 阶段 | 突破概率 |
|------|-----|------|---------|
| 1 | C/-C | 早期 | 35% |
| 2 | D/-D | 发展 | 50% |
| 3 | E/-E | 成熟 | 70% |
| 4 | F/-F | 极端 | 85% |

## 警报级别

- ○ normal: 早期收缩，观察
- △ watch: 成熟收缩，关注
- ▲ alert: 极端收缩，准备
- 🔴 critical: 多周期同步，随时突破
