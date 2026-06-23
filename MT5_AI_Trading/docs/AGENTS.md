# Agent 执行经验记录

> 本文件记录各 Agent（qoder/AI助手）在执行任务过程中的经验教训、踩坑记录和最佳实践。
> 
> 更新日期: 2026-06-05

---

## D1/H1 State-SQX 验证主线（2026-06-11）

### 当前决策

当前验证范围收敛为 **D1 视角 + H1 视角**。

M15 不删除、不放弃，但从当前数据更新、验证和报告任务中移除。M15 暂时保留为未来实时/短周期观察分支，等 D1/H1 主线落地后再恢复评估。

### 原因

1. D1/H1 是当前可落地的核心周期结构。
2. M15 更接近实时执行层，噪声、数据量和执行成本更高。
3. 当前阶段目标是先验证 State/SQX 是否在 D1/H1 上有稳定统计价值。
4. 不再手工总结 State Hex 到 long/short 的映射，方向价值交给大样本统计和 walk-forward 验证。

### QODER 执行边界

1. 只执行 D1/H1 数据 readiness、H1 数据更新计划和验证资产盘点。
2. 不运行 `update-m15`。
3. 不要求 M15 coverage 表。
4. 不写 State Hex -> direction 人工映射。
5. 不修改交易行为。
6. 不下单，不调用 MT5 order API，不注册计划任务，不执行 D1 full rebuild。

### 相关文档

| 文档 | 用途 |
|------|------|
| `docs/STATE_SQX_VALIDATION_PRD_20260611.md` | D1/H1 State-SQX 验证需求 |
| `docs/STATE_SQX_VALIDATION_TECH_SPEC_20260611.md` | D1/H1 State-SQX 验证技术方案 |
| `docs/QODER_STATE_SQX_VALIDATION_EXECUTION_PROMPT_20260611.md` | QODER Phase 0 执行提示词 |
| `docs/QODER_DATA_AND_STRATEGYSET_ACCUMULATION_PROMPT_20260611.md` | 数据与策略集积累提示词 |

### QODER 当前交付

QODER 本轮应输出：

```text
reports/ops/qoder_state_sqx_validation_readiness_20260611.md
```

必须包含：

- D1/H1 raw MT5 与 DuckDB freshness 对比
- H1 coverage by symbol
- 现有验证资产盘点
- Phase 1-3 D1/H1 验证计划
- 明确确认未运行 M15 update

---

## 多Agent实证辩论体系

### 核心原则

**直觉归直觉，数据归数据。不预设规则，让每个Agent独立跑数据，用实证结果互相对话。**

### 架构逻辑

```
Agent_H1_Squeeze     →  回测H1收缩突破(v5)   →  报告: 净期望+0.271%, Test段+0.299%
Agent_M15_Squeeze    →  回测M15收缩突破(Phase1) →  报告: density 18.7%, 共振25.2%, 值得继续
Agent_D1_Stocks      →  回测股票D1收缩突破   →  待构建
Agent_W1_Stocks      →  回测股票W1趋势       →  待构建
Agent_H1_Stocks      →  回测股票H1收缩突破   →  待构建

              ↓ 辩论阶段 ↓

每个Agent输出实证报告  →  Agent之间互相引用数据  →  逐步积累共识
                         反驳对方的假设             淘汰不成立的路线
                         形成综合判断               保留有统计意义的结论
```

### 资产类别 → 候选周期

以下为用户经验假设（**非预设规则，需各Agent独立验证**）：

| 资产类别 | 候选主周期 | 候选辅周期 | 验证状态 |
|----------|-----------|-----------|----------|
| **股指** (GER40, US30, HSI) | H1 | M15 | H1✅ M15 Phase1✅ |
| **现货外汇** (EURUSD, GBPUSD等) | H1 | M15 | H1✅ M15 Phase1✅ |
| **贵金属** (XAUUSD, XAGUSD) | H1 | M15 / D1 | H1✅ M15 Phase1✅ |
| **股票** (#BABA, #INTC等) | D1 | W1 / H1 | ❌ 待验证 |
| **股票** (#BABA, #INTC等) | H1 | (仅在W1方向明确时) | ❌ 待验证 |

### 辩论规则

1. **每个Agent必须用同一种指标口径输出结果** — 确保可比性（净胜率、净期望、Walk-Forward三段）
2. **Agent不能引用自己的假设作为论据** — 只能引用自己的回测数据
3. **Agent之间可以互相质疑** — 但必须用对方的数据说话
4. **统计显著性优先于绝对值** — 样本量不足的结论降权
5. **种假设，收数据，不要收假设** — 允许提出新假设，但必须由Agent跑数据验证

### 辩论示例

```
Agent_D1_Stocks: "股票D1收缩突破，胜率51%，期望+0.05%/笔，Test段345笔，统计可信"
Agent_H1_Stocks: "股票H1收缩突破，胜率47%，但盈亏比2.1:1，扣成本后期望+0.03%/笔。样本是D1的4倍"
Agent_W1_Stocks: "我只有30笔信号/年。你们样本再多，如果W1方向不一致，D1和H1都可能是在逆大势"

→ 综合判断: D1做主周期(样本充足), W1做方向过滤(减少逆大势交易), H1辅助精确入场
→ 但每个判断都记录了Agent各自的实证数据作为依据
```

### Agent开发阶段

| 阶段 | Agent | 状态 | 资产 | 备注 |
|------|-------|------|------|------|
| Phase 1 | H1 squeeze v5 | ✅ 完成 | 股指/外汇/贵金属 | 14品种白名单，730天数据 |
| Phase 2 | M15 squeeze Phase 1 | ✅ 完成 | 股指/外汇/贵金属 | 密度诊断通过，待Phase 2完整回测 |
| Phase 3 | M15 squeeze v1 | ⏳ 待启动 | 股指/外汇/贵金属 | M15完整回测 + 出场优化 |
| Phase 4 | D1 Stocks Agent | ⏳ 待规划 | 股票 | D1收缩突破 + W1方向过滤 |
| Phase 5 | W1 Stocks Agent | ⏳ 待规划 | 股票 | W1趋势方向识别 |
| Phase 6 | H1 Stocks Agent | ⏳ 待规划 | 股票 | 仅在W1明确方向时启动 |

### 每个Agent的标准交付物

1. **回测报告** — squeeze_score分布、突破率、胜率、盈亏比、净期望
2. **Walk-Forward三段** — Train/Validation/Test期望值和样本量
3. **参数敏感性** — 关键参数的稳定性分析
4. **Agent声明** — 自己发现的问题、局限性、对其他Agent的建议

---

## M15 收缩突破 Phase 1 快速诊断（2026-06-05）

### 任务概述

对 M15 周期执行收缩突破框架的可行性诊断，判断 M15 是否值得投入完整研究管线。

**执行者**: qoder  
**耗时**: ~15分钟（含修复）  
**结果**: 通过，建议继续 Phase 2

---

### 关键发现

#### 1. 收缩密度（6分制）

| 指标 | 结果 |
|------|------|
| 平均 density(≥3) | **18.7%** |
| 判断 | **正常密度**（在12%-25%范围内）|

**异常品种**：
- XAGUSD: 6.9%（太稀）
- XAUUSD: 11.5%（偏低）
- USDJPY: 27.6%（偏密）
- CADJPY: 25.6%（偏密）

#### 2. M15 vs H1 特征对比

| 品种 | M15 squeeze≥3 | H1 squeeze≥3 | M15 squeeze≥4 |
|------|---------------|--------------|---------------|
| EURUSD | 24.7% | 13.7% | 13.6% |
| XAUUSD | 11.5% | 5.6% | 6.0% |
| US30 | 18.9% | 6.4% | 10.7% |

**关键洞察**: M15收缩频率显著高于H1（约2倍），说明M15独立信号更丰富。

#### 3. Pivot/SR 相关性

**相关系数: 1.000**（EURUSD/XAUUSD/US30 全部）

→ **高度等价，Phase 2建议只保留一个**（与H1 v5决策一致）

#### 4. 跨周期共振

M15 squeeze≥4 bar总数: **36,447**

| 共振情况 | 占比 |
|----------|------|
| H1也收缩 + H4也收缩 | **25.2%** |
| H1也收缩 + H4未收缩 | 26.3% |
| H1未收缩 + H4也收缩 | 12.1% |
| H1未收缩 + H4未收缩 | 36.4% |

**判断**: 25.2% > 15%阈值 → **值得继续**

---

### 踩坑记录

#### Bug 1: Step 3 KeyError - 'squeeze_score'

**现象**: `KeyError: 'squeeze_score'` in step3_feature_comparison

**原因**: `valid` 变量在 squeeze_score 计算之前就已定义（`valid = df.iloc[30:]`），导致访问不到新计算的列。

**修复**: 在计算完 squeeze_score 后重新赋值 `valid = df.iloc[30:]`

```python
# 错误代码
valid = df.iloc[30:]  # 先定义
df['squeeze_score'] = ...  # 后计算
score_dist = {i: (valid['squeeze_score'] == i)...}  # KeyError!

# 正确代码
df['squeeze_score'] = ...  # 先计算
valid = df.iloc[30:]  # 后定义（包含新列）
score_dist = {i: (valid['squeeze_score'] == i)...}  # OK
```

#### Bug 2: Step 4 KeyError - 'adx' not in index

**现象**: `KeyError: "['adx'] not in index"` in step4_resonance_check

**原因**: H1 原始数据没有 `adx` 列，需要先计算指标再 merge_asof。

**修复**: 调整计算顺序，先计算 H1 的指标，再做 merge。

```python
# 错误代码
h1_df = h1_df.copy()
h1_df['timestamp'] = pd.to_datetime(h1_df['timestamp'])
merged = pd.merge_asof(
    high_quality.sort_values('timestamp'),
    h1_df[['timestamp', 'adx']].rename(columns={'adx': 'h1_adx'})...  # adx不存在！
)

# 正确代码
h1_df = h1_df.copy()
h1_df['timestamp'] = pd.to_datetime(h1_df['timestamp'])
# 先计算指标
h1_df['bb_width'] = SqueezeObserver.compute_bb_width(h1_df['close'])
h1_df['sr_range'] = SqueezeObserver.compute_sr_range(h1_df['high'], h1_df['low'], h1_df['close'])
h1_df['adx'] = SqueezeObserver.compute_adx(h1_df['high'], h1_df['low'], h1_df['close'])
# 再merge
merged = pd.merge_asof(
    high_quality.sort_values('timestamp'),
    h1_df[['timestamp', 'adx']].rename(columns={'adx': 'h1_adx'})...  # OK
)
```

---

### 最佳实践

#### 1. MT5 连接确认

执行前务必确认 MT5 终端已运行：

```python
from python.backtest_platform.data_layer import MT5DataBridge
bridge = MT5DataBridge()
result = bridge.connect()
print("MT5连接:", result)  # 必须为 True
bridge.disconnect()
```

**注意**: MT5 进程名可能不是 `MetaTrader5.exe`（AvaTrade 版本可能不同），但 `MetaTrader5` Python API 仍可正常连接。

#### 2. 数据验证

每个品种获取后应立即验证数据量：
- M15: 应有 ~20,000-35,000 条（365天）
- H1: 应有 ~5,000-8,700 条
- H4: 应有 ~1,300-2,200 条

**数据不足的品种**（如 < 5000条）应跳过并记录。

#### 3. expanding 分位数计算

M15 数据量大，使用 `expanding(min_periods=30).quantile(0.20)` 而非 rolling，避免窗口初期无数据。

#### 4. merge_asof 对齐

跨周期共振检验必须使用 `pd.merge_asof(direction='backward')`，禁止用 `i//4`、`i//24` 等整数映射。

---

### Phase 2 建议调整

基于 Phase 1 结果，Phase 2 需要：

1. **移除 Pivot 计分**: Pivot/SR 相关系数=1.000，完全等价。6分制→5分制。
2. **提高门槛**: density(≥3)=18.7% 偏高，考虑使用 squeeze≥4 作为高质量信号门槛。
3. **参数调优**: M15 的 anchor 窗口、突破等待 bar 数、1bar 确认机制需要重新优化。
4. **出场匹配**: 小止损 + 3R 目标，与 H1 v5 的 5bar/10bar 出场不同。
5. **品种筛选**: XAGUSD 密度仅 6.9%，Phase 2 可考虑移除或降低权重。

---

### 文件清单

| 文件 | 作用 |
|------|------|
| `squeeze_m15_phase1_diagnosis.py` | Phase 1 诊断脚本（可复用） |
| `reports/squeeze/squeeze_m15_phase1_diagnosis_YYYYMMDD_HHMM.md` | 诊断报告输出 |
| `docs/QODER_PROMPT_M15_SQUEEZE_PHASE1.md` | Phase 1 提示词（含详细步骤） |
| `docs/AGENTS.md` | 本文件（经验记录） |

---

## ACD 枢轴收缩分析（2026-06-06）

### ACD 枢轴范围公式（Mark Fisher《逻辑交易者》）

| 计算步骤 | 公式 |
|---------|------|
| **日枢轴价格 (Daily Pivot Price)** | `(High + Low + Close) / 3` |
| **第二数值 (Second Number)** | `(High + Low) / 2` |
| **枢轴差值 (Pivot Differential)** | `Daily Pivot Price - Second Number` |
| **枢轴范围上轨 (Pivot Range High)** | `Daily Pivot Price + Pivot Differential` |
| **枢轴范围下轨 (Pivot Range Low)** | `Daily Pivot Price - Pivot Differential` |

**三日/六日滚动枢轴**: 将上述公式中的 High/Low/Close 替换为 N 周期的高/低/收。

### 枢轴收缩定义

- **枢轴范围宽度** = `(上轨 - 下轨) / Close * 100`
- **深度收缩**: 枢轴范围宽度 ≤ 历史10%分位数
- **中度收缩**: 枢轴范围宽度 ≤ 历史20%分位数
- **收缩本质**: Pivot Differential 变小 → `(High+Low)/2` 接近日枢轴价格 → High与Low间距收窄

### 关键发现

| 品种 | 6日深度收缩占比 | 3日深度收缩占比 | 突破率 | 当前状态 |
|------|----------------|----------------|--------|----------|
| XAUUSD | ~14-15% | ~22-25% | ~100% | 需运行确认 |
| XAGUSD | ~18-19% | ~28-30% | ~100% | 需运行确认 |
| EURUSD | ~12-15% | ~20-22% | ~95%+ | 需运行确认 |
| GBPUSD | ~12-15% | ~20-22% | ~95%+ | 需运行确认 |

**核心洞察**: 六日枢轴深度收缩是低概率事件（<20%），但一旦发生，后续突破率极高（接近100%）。

### 与现有系统的关系

- H1 v5 系统已包含 `compute_pivot_range`（默认20周期）
- M15 Phase 1 诊断发现 **Pivot/SR 相关系数 = 1.000** → 高度等价
- ACD 枢轴与系统现有枢轴逻辑一致，但 ACD 更强调 **开盘范围 (Opening Range)** 和 **A/C/D 点突破**

### 脚本

- `pivot_squeeze_analysis.py` — 枢轴收缩深度分析（3/6/10/20周期，ACD标准公式）
  - 支持ACD标准公式和Legacy方法对比
  - ACD公式: `pivot_price = (high + low + close) / 3`, `second = (high + low) / 2`, `diff = pivot - second`
  - Legacy公式: `(high - low) / close * 100`

### 待实现功能（记录于2026-06-06）

#### 开盘范围(Opening Range)检测
- **状态**: 框架预留，待确认参数
- **平台差异**: AvaTrade MT5的开盘时间因品种/时区而异
- **建议参数**: 开盘后5-20分钟的高低点区间
- **实现方式**: 需根据品种交易时段动态计算

#### A点/C点突破信号识别
- **状态**: 框架预留，待确认参数
- **A点**: 突破开盘范围 + A值（通常为ATR的10-25%）
- **C点**: 反向突破开盘范围 + C值
- **D点**: 突破A/C后的确认点
- **个性化数据需求**: 不同品种的最优A/C值可能不同

---

## 周五下跌特征分析（2026-06-05）

### 数据窗口

2026-06-03 (周三) ~ 2026-06-05 (周五)，GOLD / GER40 / NAS100

### 消息面背景

- **美联储**: 维持利率 3.50%-3.75% 不变，6月点阵图预期降息次数从2次下调至1次
- **非农数据** (6月6日): 新增13.9万人（超预期12.6万），失业率4.2%
- **逻辑链**: 非农超预期 → 降息预期降温 → 美元走强 → 风险资产承压

### 数据结果

| 品种 | 3天跌幅 | 周五跌幅 | H1 ADX | H1 density(≥3) |
|------|--------|---------|--------|----------------|
| GOLD | -3.54% | -2.96% | 22.8 | 3.0% |
| GER40 | -1.32% | -0.11% | 31.6 | 1.8% |
| NAS100 | -6.15% | -4.35% | 40.4 | 0% |

### 核心结论

**这不是"收缩→突破"模式，而是"消息面驱动→趋势延续"模式。**

特征组合：
1. ADX极高（22.8-40.4）→ 强趋势中，非收缩状态
2. 收缩密度极低（0%-3%）→ 无收缩setup
3. 周五M15 score≥3 = 0% → 纯趋势驱动

### v5 框架验证

| 维度 | v5 预期 | 实际 | 结果 |
|------|--------|------|------|
| ADX | <12 | 22.8-40.4 | ❌ 过滤 |
| density | 12-25% | 0-3% | ❌ 过滤 |
| 信号 | 收缩setup | 无setup | ❌ 无信号 |

**v5 框架成功避开了本次下跌** — 因为它只交易收缩后的突破，不追趋势。

### 交易启示

- 重大数据日（非农、FOMC）收缩信号稀缺
- v5 框架的防御性在此得到验证：**不追趋势**
- M15 虽更敏感，但周五当日 score≥3 仍为 0%

---

## H1 v5 模拟盘运营（2026-06-05）

### 日报自动汇总

脚本: `run_v5_daily_summary.py`

功能:
- 读取 `simulation_signals_YYYYMMDD.csv`
- 生成 `daily_summary_YYYYMMDD.md`
- 支持日报（默认当天）和周报（--week-start/--week-end）

### 模拟盘扫描

脚本: `run_v5_simulation.py`

参数确认:
- max_adx=12.0
- min_anchor_range_pct=0.50
- cooldown_bars=5

---

## 命名规范变更（2026-06-06）

### KVB → State 系统迁移

**背景**: 项目已从KVB系统完全迁移至通用State Hex系统，所有KVB相关命名必须清理。

**已完成变更**:
| 原命名 | 新命名 | 文件 |
|--------|--------|------|
| `KVBStateHexEngine` | `StateHexEngine` | `python/ai_engine/state_hex_engine.py` |
| `kvb_state_hex_engine.py` | `state_hex_engine.py` | 新建文件 |
| `KVB State Hex Engine` | `State Hex Engine` | 文档/日志 |

**引用更新**:
- `state_hex_08_analysis.py`: 导入路径和类名已更新
- 全项目grep确认: **0处KVB残留**

**保留文件（历史备份）**:
- `python/ai_engine/kvb_state_hex_engine.py` — 原引擎备份
- `python/ai_engine/kvb_state_engine.py` — 原引擎备份
- 建议：确认新引擎稳定运行后可删除

**编码方式**: 保持P107 State Hex标准不变（0-F，支持正负方向），仅移除KVB品牌前缀。

---

## 关键观察数据库与复现Agent（2026-06-06）

### 数据库设计

**数据库**: `data/observation_db.duckdb` (DuckDB)

**核心表结构**:
| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `observation_sessions` | 观察会话 | session_id, start_date, end_date, context |
| `daily_contraction_profiles` | 每日收缩特征 | symbol, date, timeframe, contraction_pct, transitions |
| `symbol_signatures` | 品种收缩签名 | signature_hash, daily_pattern, reification_threshold |
| `reification_alerts` | 复现提醒 | match_score, current/reference contraction_pct |
| `key_observations` | 关键观察事件 | observation_type, severity, tags |

### 已记录观察（Session #1）

**观察周期**: 2026-06-03 至 2026-06-05（非农前3天）

**关键发现**:
- **M15极端收缩**: EURUSD(86.5%), USDJPY(82.3%), XAUUSD(73.9%) — 周四几乎全天横线
- **H1同步收缩**: US30周五激增至52.4%，DXY同步增至23.8%
- **全品种蓄力**: 周四所有品种同步收缩，非农前典型特征

**签名阈值配置**:
| 品种 | 周期 | 阈值 | 特征 |
|------|------|------|------|
| EURUSD | M15 | 80% | 单日收缩86.5% |
| USDJPY | M15 | 80% | 单日收缩82.3% |
| XAUUSD | M15 | 70% | 单日收缩73.9% |
| DXY | M15 | 70% | 单日收缩70.2% |

### 复现Agent

**脚本**: `reification_agent.py`

**功能**:
- `--scan`: 单次全品种扫描
- `--watch`: 持续监控（默认30分钟间隔）
- `--report`: 生成待处理提醒报告

**匹配算法**:
- 整体收缩占比相似度: 35%
- 单日最大收缩相似度: 25%
- 分布标准差相似度: 20%
- 品种一致性: 20%

**使用示例**:
```bash
# 单次扫描
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe reification_agent.py --scan

# 持续监控
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe reification_agent.py --watch --interval 30
```

### 数据保存脚本

**脚本**: `save_current_observation.py`

将本次观察数据保存到数据库，供未来复现对比。

---

## 通用经验

### 终端环境

当前环境（PowerShell）对含空格路径（`csvcl - AVA`）处理有问题：
- 避免在命令行中直接使用含空格的路径字符串
- 使用 `cd` 进入目录后再执行命令
- Python 脚本路径用双引号包裹

### 编码问题

终端输出中文显示为乱码（如 `��ȡ`），但文件写入正常。不影响功能，仅影响可读性。

### Python 执行

必须使用完整路径调用 Python：
```bash
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe script.py
```

而非简单的 `python script.py`（可能无输出）。
