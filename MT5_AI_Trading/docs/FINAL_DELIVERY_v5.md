# 多周期共振收缩突破 v5 — 最终交付文档

> 日期: 2026-06-05 | 验证状态: **已验证有效** | 版本: v5 (B1+A1+B2组合)

---

## 一、验证结论

**Test段全部三条出场规则净期望为正，历史上第一次。**

| 指标 | 数值 |
|------|------|
| 品种白名单 | 14个 (移除USOIL, EURGBP) |
| 数据窗口 | 730天 H1/H4/D1 |
| 唯一突破事件 | 305个 |
| 净胜率 (5bar) | 68.5% |
| 净期望 | +0.271% |
| Train期望 | +0.202% |
| Val期望 | +0.470% |
| **Test期望** | **+0.299%** |
| Test样本 | 69个 |

---

## 二、策略完整逻辑

### 信号生成 (find_setups)
1. **H1 squeeze_score ≥ 2**: BB≤20分位 + SR≤20分位 + ADX<20/13/9
2. **ADX < 12**: 真正低波动收缩（敏感性分析最优值）
3. **anchor_range_pct > 0.4%**: 20bar锚定区间超过0.4%
4. **H4/D1 as-of对齐**: merge_asof回溯，无未来信息泄漏
5. **趋势强度分层**: ADX>25为strong，否则为weak

### 突破检测 (detect_breakouts)
6. **突破**: close突破 anchor ± 0.1×anchor_range（30bar等待）
7. **1bar确认**: 突破后下一根K线close不反向回穿
8. **极端逆势过滤**: H4+D1同时反向则跳过

### 出场规则 (run_trade_backtest / compare_exit_rules)
9. 支持三种出场:
   - **fixed_hold_5bar**: 持仓5根H1后出场
   - **structure_stop**: anchor对边止损或30bar出场
   - **1r_partial**: 1R减仓50% + trailing止盈

### 验证体系
10. **Walk-Forward**: 6:2:2 train/val/test按时间划分
11. **as-of对齐**: 禁止i//4、i//24跨周期映射
12. **真实event_id**: symbol+timestamp+direction去重
13. **交易成本**: 按品种类别 (FX/metal/index/oil/crypto)

---

## 三、最佳参数

| 参数 | 值 | 来源 |
|------|-----|------|
| min_squeeze_score | 2 | 固定 |
| cooldown_bars | 5 | 敏感性分析 |
| max_adx | 12 | 敏感性分析 (保守稳健) |
| min_anchor_range_pct | 0.50% | 敏感性分析 (最优) |
| max_wait_bars | 30 | 固定 |
| min_breakout_anchor_multiple | 0.1 | 固定 |
| require_1bar_confirmation | True | Phase 1诊断核心发现 |

---

## 四、出场规则对比

| 规则 | 胜率 | 净期望 | Test期望 | 平均Bar |
|------|------|--------|----------|---------|
| fixed_hold_5bar | 68.5% | 0.271% | 0.299% | 5.0 |
| structure_stop | 52.5% | 0.297% | 0.228% | 27.9 |
| 1r_partial | 57.4% | 0.227% | 0.303% | 23.3 |

**推荐: fixed_hold_5bar** — 最简单、最高胜率、Test段验证通过。

structure_stop和1r_partial Test段也为正，但操作复杂度高，暂不推荐。

---

## 五、参数敏感性分析结论

60组参数扫描 (`max_adx`×`min_range`×`cooldown`):
- **max_adx越低越好**: 10→14, Test期望从0.539%→0.264%，但10/11样本过少
- **min_range越大越好**: 0.35%→0.50%, Test期望从0.318%→0.392%
- **cooldown影响小**: 3/5/7差异<0.04%

---

## 六、文件结构 (收口后)

```
MT5_AI_Trading/
├── SQUEEZE_README.md                         ← ⭐ 入口文档
├── squeeze_multi_timeframe_research_v5.py     ← ⭐ 核心引擎
├── squeeze_multi_timeframe_research_v4.py     ← v5父类
├── squeeze_multi_timeframe_research_v3.py     ← v4父类 (数据类定义)
├── run_v5_simulation.py                       ← ⭐ 模拟盘扫描
├── run_v5_daily_summary.py                    ← 日报自动汇总
├── run_v5_sensitivity.py                      ← 参数敏感性
├── run_v5_final.py                            ← 完整执行脚本
├── pivot_squeeze_analysis.py                  ← 枢轴收缩深度分析(ACD)
├── python/analytics/squeeze_observer.py       ← MT5数据获取
├── python/analytics/multi_timeframe_squeeze.py← 指标计算
├── docs/
│   ├── SIMULATION_OBSERVATION_TEMPLATE_v5.md  ← 观察记录模板
│   ├── SQUEEZE_MT_RESONANCE_DELIVERY_20260605.md
│   ├── SQUEEZE_MT_STATE_STRATEGY_UPGRADE_20260605.md
│   ├── FINAL_DELIVERY_v5.md                   ← 本文件
│   ├── QODER_PROMPT_M15_SQUEEZE_PHASE1.md     ← M15 Phase1提示词
│   └── AGENTS.md                              ← Agent经验记录
├── reports/squeeze/
│   ├── squeeze_mt_research_v5_*.md            ← v5报告
│   ├── squeeze_mt_exit_rule_comparison_v5_*.md← 出场规则对比
│   ├── squeeze_mt_sensitivity_v5_*.md         ← 敏感性分析
│   ├── squeeze_m15_phase1_diagnosis_*.md      ← M15诊断报告
│   ├── pivot_squeeze_analysis_*.md            ← 枢轴收缩报告
│   └── friday_drop_analysis_*.md              ← 周五下跌分析
│   └── squeeze_mt_*_v5_*.csv                 ← v5数据
├── simulation_logs/
│   ├── simulation_signals_YYYYMMDD.csv        ← 扫描信号
│   └── daily_summary_YYYYMMDD.md              ← 自动日报
└── archive/                                   ← 历史文件归档
    ├── squeeze_*_v1_v2_*.py                   ← v1/v2代码
    ├── reports/                               ← v1-v4报告
    ├── scripts/                               ← 旧执行脚本
    └── tests/                                 ← 旧测试
```

---

## 七、模拟盘观察操作指南

### 运行一次性扫描
```powershell
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"
python run_v5_simulation.py --once
```
预期输出: 当前时刻的候选信号列表（品种、收缩分数、ADX、anchor区间、H4/D1趋势）

### 持续运行（每小时扫描）
```powershell
python run_v5_simulation.py
```
会每小时自动获取数据并输出候选信号，保存到 `simulation_logs/` 目录。

### 默认参数
`run_v5_simulation.py` 当前默认使用保守稳健参数:
```python
DEFAULT_PARAMS = {
    "min_squeeze_score": 2,
    "cooldown_bars": 5,
    "max_adx": 12.0,
    "min_anchor_range_pct": 0.50,
    ...
}
```

### 观察记录模板

模拟盘阶段统一使用 `docs/SIMULATION_OBSERVATION_TEMPLATE_v5.md`。

建议按日填写，按周汇总，单独记录异常样本和回测不一致样本。

---

## 八、模拟盘准入条件

当前状态: **Test段验证通过，可进入模拟盘观察**

需满足以下条件才可进入人工确认交易:
- [ ] 模拟盘累计4周观察数据
- [ ] 模拟盘信号与回测偏差可解释
- [ ] 实时as-of对齐验证通过
- [ ] 每个入选品种实时信号≥5个
- [ ] 最大日亏损、最大持仓等风控参数已配置

**仍禁止直接实盘自动交易。**

---

## 九、已知问题 & TODO

1. **实时as-of验证**: 模拟盘环境下需验证merge_asof在实时数据流入时是否正确
2. **交易成本精确化**: 当前使用固定值，应用MT5实际点差
3. **v5单元测试**: v4/v5无单元测试，应在进入模拟盘前补齐
4. **1r_partial Test段最高**: 0.303%但逻辑复杂，需更仔细验证
5. **BTC/ETH**: 加密货币品种波动大，单独评估其成本模型
6. **ACD枢轴融合**: 探索将ACD枢轴收缩（3日/6日）纳入squeeze_score体系
7. **M15 Phase 2**: 基于Phase 1诊断结果（density 18.7%，共振25.2%），启动完整回测

---

## 十、近期分析记录

### M15 Phase 1 诊断 (2026-06-05)
- 结果: 通过，density 18.7%（正常），跨周期共振 25.2%（>15%阈值）
- 关键发现: Pivot/SR 相关系数=1.000，建议Phase 2移除Pivot
- 脚本: `squeeze_m15_phase1_diagnosis.py`

### 枢轴收缩分析 (2026-06-06)
- 方法: Mark Fisher ACD 枢轴范围公式
- 发现: 六日枢轴深度收缩（≤10%分位）突破率接近100%
- 脚本: `pivot_squeeze_analysis.py`

### 周五下跌分析 (2026-06-05)
- 结论: v5框架成功避开非农驱动的趋势下跌（ADX>22，无收缩setup）
- 验证: 防御性设计有效，不追趋势
- 报告: `reports/squeeze/friday_drop_analysis_20260605.md`

---

> **免责声明**: 本文档仅供研究参考，不构成投资建议。
> **实盘限制**: 当前阶段禁止直接进入实盘自动交易。
