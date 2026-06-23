# 多周期共振收缩→突破 量化研究系统

> 验证状态: **已验证有效** | 最后更新: 2026-06-05

## 一句话说明

H1 BB收缩 + SR收缩 + ADX低谷 + 突破后1bar确认 → 14个品种白名单 → 5bar固定持有 = 净胜率68.5%，净期望+0.271%，Test段+0.299%。

**不构成投资建议，当前阶段禁止直接实盘自动交易。**

---

## 快速上手

### 运行一次模拟盘扫描
```powershell
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"
python run_v5_simulation.py --once
```

### 运行完整研究（参数敏感性+报告生成）
```powershell
python run_v5_sensitivity.py
```

---

## 活跃文件

| 文件 | 作用 |
|------|------|
| `squeeze_multi_timeframe_research_v5.py` | ⭐ 核心引擎 (继承v4，修正analyze，支持出场规则对比) |
| `squeeze_multi_timeframe_research_v4.py` | 依赖 (被v5继承，含find_setups/detect_breakouts) |
| `squeeze_multi_timeframe_research_v3.py` | 依赖 (被v4继承，含数据类定义和基础方法) |
| `run_v5_simulation.py` | ⭐ 模拟盘每小时扫描脚本 |
| `run_v5_daily_summary.py` | 日报自动汇总（与观察模板对齐） |
| `run_v5_sensitivity.py` | 参数敏感性分析 |
| `run_v5_final.py` | 完整v5执行脚本 (基线+出场规则+历史对比) |
| `pivot_squeeze_analysis.py` | 枢轴收缩深度分析（3/6/10/20周期，ACD方法） |
| `docs/SQUEEZE_MT_RESONANCE_DELIVERY_20260605.md` | 交付文档 |
| `docs/SQUEEZE_MT_STATE_STRATEGY_UPGRADE_20260605.md` | 策略升级文档 |
| `docs/AGENTS.md` | Agent执行经验记录（含踩坑、最佳实践） |

## 报告文件

| 文件 | 说明 |
|------|------|
| `reports/squeeze/squeeze_mt_research_v5_20260605_1505.md` | v5基线研究报告 |
| `reports/squeeze/squeeze_mt_exit_rule_comparison_v5_20260605_1505.md` | 出场规则对比报告 |
| `reports/squeeze/squeeze_mt_sensitivity_v5_20260605_1556.md` | 参数敏感性分析 (60组) |
| `docs/SIMULATION_OBSERVATION_TEMPLATE_v5.md` | 模拟盘观察记录模板 |
| `simulation_logs/daily_summary_YYYYMMDD.md` | 自动生成的日报 |

---

## 最佳参数

| 场景 | max_adx | min_range | cooldown | Test期望 | 样本 |
|------|---------|-----------|----------|----------|------|
| ⭐ **保守稳健** | 12 | 0.50% | 5 | 0.377% | 54 |
| 激进优化 | 11 | 0.50% | 5 | 0.468% | 32 |
| 当前模拟盘 | 12 | 0.50% | 5 | 0.377% | 54 |

---

## 策略核心逻辑

```
扫描14品种白名单 H1 K线
  ↓
条件1: squeeze_score ≥ 2 (BB≤20分位 + SR≤20分位 + ADX低值)
  ↓
条件2: ADX < 12 (真正低波动收缩)
  ↓
条件3: anchor_range > 0.4% (区间够大)
  ↓
条件4: H4/D1 as-of趋势对齐 (无未来信息泄漏)
  ↓
突破检测: close突破 anchor ± 0.1×anchor_range
  ↓
条件5: 突破后1bar确认 (下一根不反向回穿)
  ↓
入场 → fixed_hold_5bar 固定持有5根H1 K线
```

## 品种白名单 (14个)

XAGUSD, UKOIL, US30, ETHUSD, XAUUSD, UK100, EURUSD, AUDUSD, US500, GBPUSD, USDJPY, CADJPY, GER40, CHFJPY

**已移除**: USOIL (净-0.9%), EURGBP (净负, 样本少)

---

## 版本演进

| 版本 | 核心改进 | 净期望 | Test段 |
|------|----------|--------|--------|
| v3 | as-of对齐 + 真实event_id + 交易成本 + walk-forward | -0.005% | -0.026% |
| v4 | 1bar确认 + 品种白名单 + ADX<12 + range>0.4% + 趋势强度 | +0.227% | -0.107% |
| v4_B1 | 移除USOIL+EURGBP | +0.305% | +0.168% |
| v4_A1 | 730天数据窗口 | +0.233% | +0.155% |
| **v5** | **B1+A1+B2组合** | **+0.271%** | **+0.299%** |

---

## 枢轴收缩分析 (ACD方法)

### ACD枢轴范围公式 (Mark Fisher)

| 计算步骤 | 公式 |
|---------|------|
| 日枢轴价格 | `(High + Low + Close) / 3` |
| 第二数值 | `(High + Low) / 2` |
| 枢轴差值 | `日枢轴价格 - 第二数值` |
| 枢轴范围 | `±枢轴差值` |

### 枢轴收缩定义

- **深度收缩**: 枢轴范围 ≤ 历史10%分位数
- **中度收缩**: 枢轴范围 ≤ 历史20%分位数
- **核心洞察**: 六日枢轴深度收缩是低概率事件（<20%），但突破率接近100%

### 运行枢轴分析

```powershell
python pivot_squeeze_analysis.py
```

---

## 下一步

1. 持续运行模拟盘扫描，累积实时观察数据
2. 至少4周观察后对比回测与实盘偏差
3. 满足准入条件后可考虑人工确认交易
4. 探索ACD枢轴收缩与现有squeeze_score的融合

---

## 历史归档

## 模拟盘记录

建议统一使用 `docs/SIMULATION_OBSERVATION_TEMPLATE_v5.md` 记录：

- 每日扫描执行情况
- 候选信号与确认信号
- 异常样本与回测不一致样本
- 周度汇总与准入评估

`v1-v4` 的历史代码和报告已移至 `archive/` 目录。
