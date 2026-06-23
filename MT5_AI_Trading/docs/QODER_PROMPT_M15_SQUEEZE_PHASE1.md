# Qoder 任务: M15 收缩突破 Phase 1 快速诊断

> 日期: 2026-06-05 | 优先级: 高 | 预计耗时: 30-45分钟

---

## 一、背景

### 1.1 已有成果

H1多周期共振收缩→突破系统 v5 已完成，验证状态 **"已验证有效"**：

| 指标 | 数值 |
|------|------|
| 品种白名单 | 14个 |
| 数据窗口 | 730天 H1/H4/D1 |
| 唯一突破事件 | 305个 |
| 净胜率 | 68.5% |
| 净期望 | +0.271% |
| Test段期望 | +0.299% |

**核心文件（本地 `d:\qoder\csvcl - AVA\MT5_AI_Trading\`）：**

| 文件 | 作用 |
|------|------|
| `SQUEEZE_README.md` | **入口文档 — 先读这个** |
| `docs/FINAL_DELIVERY_v5.md` | 最终交付文档 |
| `squeeze_multi_timeframe_research_v5.py` | 核心引擎 (继承v4/v3) |
| `run_v5_simulation.py` | 模拟盘扫描脚本 |
| `run_v5_sensitivity.py` | 参数敏感性分析 |
| `python/analytics/squeeze_observer.py` | MT5数据获取 (`_fetch_from_mt5`) |
| `python/analytics/multi_timeframe_squeeze.py` | 指标计算 (BB/SR/ADX) |
| `docs/STATE_VIEWPOINT_AGENT_CONTRACT.md` | **State架构合约 — 必读** |
| `docs/SQUEEZE_MT_STATE_STRATEGY_UPGRADE_20260605.md` | State提升方案 |

### 1.2 为什么做M15

用户实际交易中使用M15做小止损+3:1盈亏比的交易。当前H1 v5已经验证收缩→突破框架有效，现在要评估这个框架能否下沉到M15视角，辅助用户的M15决策。

**注意：这是探索性Phase 1，只做诊断，不做完整管线重建。**

### 1.3 State架构约束

M15不是"再加一个时间周期列"，而是**独立的Viewpoint Agent**。根据 `STATE_VIEWPOINT_AGENT_CONTRACT.md`：

```text
M15 Agent:
  MN1/W1/D1/H4/H1/M30/M15 @ M15_view
  
  timestamp = M15 bar timestamp
  view_price = M15 close  ← 所有position计算使用M15 close
```

**核心规则：**
- `structure_tf` = 结构来源周期（即哪个周期的OHLCV）
- `view_tf` = 观察者时钟（即用哪个周期的close计算position）
- `state_hex` = structure_tf的state在view_tf下的状态
- M15 Agent中所有position（即当前价格相对SR的位置）必须用M15的close计算
- 不能把原生H1@H1、H4@H4的state简单拼接后当作M15视角状态

但在Phase 1诊断阶段，我们先**不构建完整的State序列**，只做收缩密度和突破频率的统计诊断。

### 1.4 实战验证：DAX 2026年6月3日 M15收缩突破做空案例

**来源：** 用户MT4实盘交易记录 `d:\qoder\csvcl - AVA\交易记录\DetailedStatement20260605.htm`

用户确认：这组做空交易就是**看到M15收缩后入场**的。这是M15收缩→突破模式在实盘中的直接证据。

#### 行情背景

DAX（德意志指数，MT5对应品种：**GER40**）在6月3日经历了一轮显著的下跌趋势：
- 起始：25110 → 终了：24716，单日下跌 **394点（-1.57%）**
- 趋势路径：持续且流畅的下行，中间几乎没有反弹

#### 交易记录

| # | MT4时间 | MT5时间(+4h) | 入场价 | 止损(SL) | 出场价 | 盈利 | 止损点数 | 盈亏比 |
|---|---------|-------------|--------|----------|--------|------|----------|--------|
| 1 | 06:41 | **10:41** | 25110.4 | 25018.8 | 24916.0 | **+$56.38** | 91.6点 | **2.12R** |
| 2 | 16:26 | **20:26** | 24883.9 | 无SL | 24812.0 | +$20.86 | - | - |
| 3 | 16:43 | **20:43** | 24834.4 | 无SL | 24811.7 | +$6.59 | - | - |
| 4 | 18:54 | **22:54** | 24808.1 | 无SL | 24717.1 | +$26.41 | - | - |
| 5 | 19:10 | **23:10** | 24785.2 | 无SL | 24716.2 | +$20.02 | - | - |
| **合计** | | | | | | **+$130.26** | | |

> **时区说明：** 交易记录来自MT4平台（KVB Prime），MT5服务器时区与之不同。  
> 用户确认：**MT4时间比MT5早4小时**。所有MT5时间 = MT4时间 + 4小时。

#### 多维解读

**1. 收缩→突破模式识别**

第1笔入场时间（MT5: 10:41）处于欧洲早盘开始时段。DAX在之前几小时很可能处于窄幅盘整（M15收缩），随后向下突破。用户正是在这个"收缩后突破"的节点入场做空。这是典型的 squeeze breakout 空头信号。

**2. 金字塔加仓与趋势延续**

5笔空单的入场价从25110逐步下移到24785，呈**阶梯式加仓**：
```
25110 (入场1) → 24883 (入场2, 已跌227点) → 24834 (入场3) → 24808 (入场4) → 24785 (入场5)
```
每次加仓都在确认趋势延续后执行，而非逆势加仓。最终5笔全部盈利，说明**趋势判断准确，收缩突破方向与更高周期趋势一致**。

**3. 止损与盈亏比**

第1笔设了止损（91.6点），盈利194.4点，盈亏比 **2.12:1**。后续4笔未设止损（但可能通过盘感/手动离场）。用户整体DAX实盘统计：
- DAX共12笔，8赢4亏，胜率 **67%**
- 平均盈利 **$23.60**，平均亏损 **-$8.98**
- **盈亏比 2.63:1**，接近用户追求的3:1目标

**4. DAX品种集中度**

用户5天内交易6个品种共40笔，DAX独占总利润的 **88%**（$141/$161）：
| 品种 | 笔数 | 净盈亏 | 利润占比 |
|------|------|--------|----------|
| **DAX (GER40)** | **12** | **+$141.46** | **88%** |
| 其他5个品种合计 | 28 | +$19.62 | 12% |

这表明DAX是用户M15策略的**绝对核心品种**。

**5. 关键交易时段（MT5时间）**

DAX空单集中在两个窗口：
- **10:00-12:00**（欧洲早盘开盘，流动性涌入）
- **20:00-23:00**（欧洲尾盘/美盘重叠）

这两个窗口是M15收缩突破的高发期。

#### 对Phase 1诊断的指导意义

1. **GER40 (DAX) 作为 Priority 1 品种** — 在Step 3特征对比和Step 4共振检验中必须包含GER40
2. **M15止损范围参考：80-100点** — 第1笔止损91.6点提供了实际参数锚点
3. **M15入场确认timeframe**：MT5时间10:00-12:00和20:00-00:00是重点观察窗口
4. **趋势确认需求**：5笔空单全胜说明更高周期（H1/H4）趋势方向与M15突破方向一致是盈利关键
5. **加仓潜力**：M15收缩突破后趋势可能持续数小时，Phase 2应考虑分批出场/加仓逻辑

---

## 二、任务目标

**一句话：判断M15上是否存在足够数量、足够质量的收缩→突破机会。**

输出一份诊断报告，明确回答：
1. M15上squeeze_score≥2的bar密度是否合理？（不能太稀也不能太密）
2. M15的收缩特征（ADX分布、anchor_range分布）与H1相比有什么差异？
3. 用M15的squeeze setup识别，然后对照H1/H4趋势，是否有初步的共振信号？
4. 给出"值得继续"或"不必继续"的明确建议。

---

## 三、执行步骤

### Step 1: 获取M15数据（~5分钟）

**要求：**
- 使用 `squeeze_observer._fetch_from_mt5(symbol, "M15", lookback_days)` 
- 14个白名单品种：**GER40(首要)**, XAGUSD, UKOIL, US30, ETHUSD, XAUUSD, UK100, EURUSD, AUDUSD, US500, GBPUSD, USDJPY, CADJPY, CHFJPY
- lookback_days=365（**先只用365天，不需要730天**，Phase 1追求速度）
- 同时获取H1/H4数据（也365天），用于后续跨周期共振检查
- **不要获取D1及以上周期**，Phase 1不需要
- **时区注意：** 用户MT4平台（KVB Prime）时间比MT5服务器时间**早4小时**。数据分析使用MT5时间。6月3日DAX第1笔入场MT4=06:41，对应MT5≈10:41。

**数据要求：**
- 确保每条数据的 `timestamp` 列是 `pd.to_datetime` 格式
- 数据量检查：每个品种M15应该有 ~24000条（365天×24h×4bar/h，实际会有非交易时段缺口）
- 如果某品种M15数据 < 5000条，跳过该品种并在报告中记录

**验证方式：**
- 打印每个品种的M15数据条数和时间范围
- 例：`EURUSD M15: 22184条, 2025-06-06 ~ 2026-06-05`

### Step 2: M15收缩密度扫描（~10分钟）

**要求：**
- 使用v4/v5的 `find_setups` 逻辑，但**不要在M15上运行完整管线**
- **只计算每根M15 bar的squeeze_score分布**，不做setup识别和回测

**具体操作：**

对每个品种的M15数据，逐bar计算（滚动窗口，从第30根开始）：

```
for each M15 bar i >= 30:
    1. 计算 rolling BB_width(20) → 是否 ≤ 20分位值(expanding)
    2. 计算 rolling SR_range(20) → 是否 ≤ 20分位值(expanding) 
    3. 计算 rolling Pivot_range(20) → 是否 ≤ 20分位值(expanding)  ← 新增
    4. 计算 rolling ADX(14) → 是否 < 20 / 13 / 9
    5. squeeze_score = bb + sr + pivot + adx_lt_20 + adx_lt_13 + adx_lt_9  (满分6)
    6. structural_score = bb + sr + pivot

注意: H1 v3-v5中移除了Pivot Range（与SR高度等价导致重复计分），
     但M15视角下Pivot和SR可能不高度等价，Phase 1应包含Pivot以便对比。
     在Step 3中单独对比Pivot vs SR的相关性，判断是否重复。
```

**注意：**
- `SqueezeObserver.compute_bb_width` / `compute_sr_range` / `compute_adx` 是静态方法，可以直接调用
- 不需要cooldown过滤、不需要anchor计算、不需要趋势对齐
- 目标是统计密度，不是筛选信号

**输出每个品种的统计：**

```
品种      总bar数    score=0   score=1   score=2   score=3   score=4   score=5   score=6   density(≥3)
EURUSD    22184     12000     5000      3000      1500      500       184       23.4%
GBPUSD    ...
...
平均                                                                    X.X%
```

**密度判断标准（M15满分6分，阈值为≥3）：**
- density(≥3) ≥ 12% → 正常密度
- density(≥3) < 8% → 可能太稀
- density(≥3) > 25% → 可能太密

### Step 3: M15 vs H1 特征对比（~10分钟）

**要求：**
- 选取4个代表性品种：**GER40（DAX，用户核心品种）**、EURUSD（外汇）、XAUUSD（金属）、US30（指数）
- 对每个品种的M15和H1，分别计算以下指标分布：

```
1. ADX分布:
   - ADX < 10: X%
   - ADX 10-15: Y%  
   - ADX 15-20: Z%
   - ADX 20-25: W%
   - ADX > 25: V%

2. BB_width分布:
   - P10 / P25 / P50 / P75 / P90

3. SR_range分布（占close的百分比）:
   - P10 / P25 / P50 / P75 / P90

4. Pivot_range分布（占close的百分比）:  ← M15新增
   - P10 / P25 / P50 / P75 / P90
   - 计算 Pivot_range 与 SR_range 的相关系数
   - 如果 r > 0.8: Pivot和SR在M15上仍高度等价，Phase 2建议只保留一个

5. squeeze_score分布:
   - score 0/1/2/3/4/5/6各占比 (M15满分6，H1满分5)
   - score 0/1/2/3/4/5各占比
```

**对比格式：**

```
品种: EURUSD
指标              M15          H1
ADX<10           15.2%       22.1%
ADX 10-15        18.7%       25.3%
...
squeeze_score≥2   23.4%       28.1%
```

**关键洞察点：**
- M15的ADX是否整体高于H1？（M15噪音大，ADX应该更高）
- M15的BB_width是否更窄？（M15的20bar=5小时，比H1的20bar=20小时窄）
- M15的squeeze_score≥4（高质量收缩，6分制下）占比是否显著低于H1的squeeze_score≥3（5分制下）？
- M15的Pivot_range与SR_range相关系数 — 决定Phase 2是否保留Pivot计分

### Step 4: 跨周期共振初步检验（~10分钟）

**要求：**
- 不对所有M15 bar做，只抽取**squeeze_score ≥ 4的高质量收缩bar**（6分制，≈ H1的squeeze≥3）
- 对每个这样的M15 bar，用 `pd.merge_asof` 获取**同一timestamp之前最近的H1和H4 bar的squeeze状态**

**操作：**
```
for each M15 bar where squeeze_score >= 4:
    1. 用 merge_asof(direction='backward') 找到 ≤ M15_timestamp 的最新H1 bar
    2. 同样找到最新H4 bar
    3. 记录:
       - H1的squeeze_score（该H1 bar是否有收缩）
       - H4的squeeze_score
       - H1的adx
       - H4的adx
```

**输出共振矩阵：**

```
M15 squeeze≥4 bar总数: NNNN

高周期共振情况:
  H1也收缩 + H4也收缩:  XXX (X.X%)  ← 最强共振
  H1也收缩 + H4未收缩:  XXX (X.X%)
  H1未收缩 + H4也收缩:  XXX (X.X%)
  H1未收缩 + H4未收缩:  XXX (X.X%)  ← 孤立收缩

H1趋势方向(ADX>20时):
  H1 bullish + M15 squeeze: XXX
  H1 bearish + M15 squeeze: XXX
  H1 neutral (ADX<20):      XXX
```

**判断标准：**
- 如果"H1也收缩 + H4也收缩"占比 > 15%，说明M15上的高质量收缩常常与更高周期共振 → 值得继续
- 如果此占比 < 5%，说明M15收缩基本独立于更高周期 → 与用户的多周期视角不匹配

### Step 5: 生成诊断报告（~5分钟）

**报告位置：** `reports/squeeze/squeeze_m15_phase1_diagnosis_YYYYMMDD_HHMM.md`

**报告结构：**

```markdown
# M15 收缩突破 Phase 1 诊断报告

## 一、数据概览
- 品种数、数据窗口、各品种M15数据量

## 二、收缩密度扫描
- 14品种的squeeze_score分布表
- 平均density(≥2)、density(≥3) 
- 与H1 v5的对比

## 三、M15 vs H1 特征对比 (GER40/EURUSD/XAUUSD/US30)
- ADX分布对比表
- BB_width分布对比表
- SR_range分布对比表
- 关键差异分析

## 四、跨周期共振初步检验
- M15 squeeze≥3 与 H1/H4 的共振矩阵
- 趋势方向分布

## 五、结论与建议

### 是否值得继续？
- [ ] 值得继续 → Phase 2: M15 v1研究
- [ ] 不必继续 → M15不适合当前框架
- [ ] 需要调整 → 某方面有问题需先解决

### 如果继续，Phase 2需要调整什么？
- 列举基于诊断发现需要的参数调整

## 六、原始统计附录
- 各品种完整数据
```

---

## 四、过程控制

### 4.1 关键决策点

| 阶段 | 检查点 | 如果不通过 |
|------|--------|-----------|
| Step 1后 | 至少10个品种M15数据≥5000条 | 减少品种，只用数据足够的 |
| Step 2后 | 平均density(≥3)在8%~25%之间 | density<8%: 报告"太稀"并停止；>25%: 建议提高squeeze_score门槛到≥4 |
| Step 3后 | M15与H1特征有合理差异（不是完全重合）；Pivot/SR相关系数已计算 | 如果完全重合→M15无增量信息 |
| Step 4后 | 共振占比数据有意义 | 无论结果如何都写入报告，0%也是有价值的结论 |

### 4.2 中断条件

- MT5连接失败超过3次 → 报告中断原因，建议检查MT5终端
- 运行时间超过60分钟 → 中断，报告当前进度
- 出现无法自主解决的Python错误 → 记录错误信息和位置，中断

### 4.3 复原策略

- 如果中断，`self.raw_data`中已获取的数据不要丢弃
- 可以从Step 2重新开始，不需要重新获取数据
- 每一步完成后打印进度标记：`[Phase 1 - Step X 完成]`

---

## 五、技术注意事项

### 5.1 性能优化

- M15数据量大（每品种~24000条），`_precompute_trend_biases` 很慢。**Phase 1不需要做预计算**，直接用逐条扫描即可
- Step 2的滚动计算用pandas内置的 `.rolling().quantile()` 和 `.expanding().quantile()`，不要写Python循环
- Step 4的merge_asof是向量化操作，很快

### 5.2 指标计算复用

- `SqueezeObserver.compute_bb_width(close_series)` → 返回BB宽度序列
- `SqueezeObserver.compute_sr_range(high, low, close)` → 返回SR间距序列
- `SqueezeObserver.compute_adx(high, low, close, period=14)` → 返回ADX序列
- **Pivot Range**: 查看 `python/analytics/multi_timeframe_squeeze.py` 或 `squeeze_multi_timeframe_research.py` 中的 `compute_pivot_range` 实现。如果不存在，用H-L的近期范围作为替代（`high.rolling(20).max() - low.rolling(20).min()` 除以 close）

这四个都是静态方法或可直接用pandas计算，不需要实例化observer

### 5.3 不要做的事情

- ❌ 不要修改 `squeeze_multi_timeframe_research_v5.py` 或任何v3/v4/v5文件
- ❌ 不要运行完整回测（detect_breakouts/run_trade_backtest）
- ❌ 不要计算交易成本和walk-forward
- ❌ 不要生成CSV数据文件（只生成诊断报告md）
- ❌ 不要创建新的State数据库

### 5.4 文件命名

- 诊断脚本：`squeeze_m15_phase1_diagnosis.py`（放在 `MT5_AI_Trading/` 根目录）
- 诊断报告：`reports/squeeze/squeeze_m15_phase1_diagnosis_YYYYMMDD_HHMM.md`
- **不创建任何v6或新版本号文件**

---

## 六、14品种白名单

```python
SYMBOL_WHITELIST_V5 = {
    "XAGUSD", "UKOIL", "US30", "ETHUSD", "XAUUSD", 
    "UK100", "EURUSD", "AUDUSD", "US500", "GBPUSD",
    "USDJPY", "CADJPY", "GER40", "CHFJPY"
}
```

MT5名称映射参考 `squeeze_multi_timeframe_research_v5.py` 中的 `SYMBOL_MAP`。

---

## 七、用户场景

用户使用M15做小止损+3:1盈亏比交易。Phase 1诊断的目的不是直接生成交易信号，而是回答：

> "M15上的收缩→突破模式是否有统计基础？是否能与多周期趋势共振形成有效过滤？"

如果Phase 1通过，Phase 2将构建完整的M15研究管线：
- M15参数调优（anchor窗口、突破等待bar数、1bar确认是否保留）
- H1/H4 @ M15_view as-of对齐
- 出场匹配用户风格：小止损 + 3R目标检测
- walk-forward验证

**但Phase 2的前提是Phase 1给出"值得继续"的结论。**
