# QODER State Hex / SQX 一致性审计提示词

## 任务目标

对 MT5_AI_Trading 全项目进行一致性审计，重点排查 State Hex 编码体系与 SQX 指标模块之间的语义混淆、周期视角错位、以及 D1 Risk Officer 硬门槛被绕过等问题。

**输出要求**：审计报告必须写入 `MT5_AI_Trading/reports/ops/qoder_state_sqx_consistency_audit_20260611.md`

---

## 核心排查清单（6大高危模式）

### 1. 把 State Hex 当线性强弱分数

**错误模式**：将 state_hex 的数值大小直接等同于趋势强弱程度。

**正确语义**：
- State Hex 是 **状态编码**，不是分数。
- `0` = 收缩底座，无额外组件
- `8` = 非收缩底座，无额外组件
- `F` = 非收缩底座 + 幅动活跃 + 位置触发 + 趋势触发
- `-F` = 空向语境下的 F
- **数值大小与趋势强弱无单调关系**：`0`（收缩）可能比 `F`（非收缩+全触发）更具交易价值，因为收缩意味着潜在爆发。

**排查方法**：
- 搜索代码中是否存在 `int(state_hex)`、`state_hex >`、`state_hex <` 等数值比较
- 搜索是否存在根据 hex 数值大小判断信号强弱的逻辑
- 检查是否有 "hex 越大越强势" 的注释或文档描述

### 2. 把 D1=8 写成强多

**错误模式**：将 D1 state_hex = `8` 描述或处理为 "强多"、"强势多头"。

**正确语义**：
- `8` = 非收缩底座，无额外组件
- `8` 表示 **非收缩状态**，但没有任何趋势、位置、波动触发信号
- `8` 是 **中性非收缩** 状态，不是 "强多"
- 真正的多头信号需要 `+` 号（多向语境）且包含趋势/位置组件，如 `C`（+趋势）、`E`（+趋势+位置）、`F`（全触发）

**排查方法**：
- 搜索文档和代码中 "8" 与 "强"、"强势"、"强多"、"bull" 的关联描述
- 检查交易信号生成逻辑是否将 `8` 作为多头入场条件
- 检查 D1 Risk Officer 是否将 `8` 误判为 long 方向（正确应为 neutral）

### 3. 把 State Hex 当交易许可

**错误模式**：直接用 state_hex 判断是否允许交易，绕过 D1 Risk Officer。

**正确语义**：
- State Hex 描述 **市场状态**（收缩/非收缩、趋势/位置/波动组件）
- 交易许可由 **D1 Risk Officer** 单独判定，基于 D1 方向（long/short/neutral）
- D1 Risk Officer 是 **硬门槛**，任何交易信号必须通过它
- State Hex 可以作为 Risk Officer 的输入之一，但不能替代 Risk Officer

**排查方法**：
- 搜索所有交易信号生成/过滤代码
- 确认每个信号路径最终都经过 `D1RiskOfficer.assess()` 或 `gate_signal_fields()`
- 检查是否有 "如果 state_hex == X 则允许交易" 的硬编码逻辑
- 检查 SQX 指标模块是否独立输出交易信号而不经过 Risk Officer

### 4. 混淆 D1/H1/M15 周期视角

**错误模式**：将不同周期的 state_hex 混用，或错误地认为各周期 hex 可以直接比较。

**正确语义**：
- **D1 视角**：D1 结构周期计算 D1 hex，用于判断日线级方向（D1 Risk Officer 输入）
- **H1 视角**：H1 时间戳对齐，MN1/W1/D1/H4/H1 五元组，position 使用 H1 close 作为视角基准价
- **M15 视角**：M15 时间戳对齐，各结构周期 position 使用 M15 close 作为视角基准价
- **关键原则**：同一时刻，D1 hex 和 H1 hex 可能不同，因为它们的 position 计算基准价不同（D1 close vs H1 close）
- **禁止**：用 H1 的 D1_hex 替代 D1 视角的 D1_hex 来做方向判断

**排查方法**：
- 检查代码中 D1 hex 的来源：是 D1 视角计算的还是从 H1 五元组中取的
- 检查 D1 Risk Officer 的输入是否总是来自 D1 视角的 D1_hex
- 检查文档中是否明确区分 "D1 结构周期的 state" 和 "H1 视角下的 D1 结构周期 state"
- 检查 `compute_quintuplets()` 中 D1_hex 的使用是否被误用于 D1 方向判断

### 5. SQX 指标模块绕过 D1 Risk Officer

**错误模式**：SQX 指标（如 RSIOMA、ACD 枢轴等）独立生成交易信号，不经过 D1 Risk Officer 审核。

**正确语义**：
- **所有交易信号**必须经过 D1 Risk Officer
- SQX 指标可以提供 **辅助信息**（如收缩突破方向、RSIOMA 金叉死叉）
- 但最终的 trade direction 必须经 Risk Officer 确认与 D1 方向一致
- 如果 D1 = neutral/unknown，只允许非方向性操作（HOLD/OBSERVE）

**排查方法**：
- 搜索所有 `RSIOMA`、`ACD`、`pivot`、`squeeze` 相关的信号生成代码
- 确认这些信号是否都经过 `gate_signal_fields()` 或 `D1RiskOfficer.assess()`
- 检查是否有 "SQX 信号直接触发交易" 的代码路径
- 检查 `MULTI_TIMEFREME_RESONANCE_FRAMEWORK.md` 中的共振评分是否与 Risk Officer 兼容

### 6. 架构文档中出现口号式或不可验证措辞

**错误模式**：文档中使用模糊、情绪化、口号式、不可验证的措辞来替代证据、阈值和决策依据。

**必须排查并替换的措辞**：
- "深刻反思"
- "彻底打倒"
- "粉碎"
- "颠覆"
- "推翻一切"
- "革命性"

**需要补充定义而不是一刀切删除的措辞**：
- "顺势而为"：如果保留，必须定义趋势判定来源，例如 D1 Risk Direction、MA144/169/200 结构、ADX 阈值。
- "严格风控"：如果保留，必须定义风险阈值，例如单笔风险、日亏损上限、D1 Risk Officer 阻断规则。
- "精准入场"：如果保留，必须定义触发条件，例如 M15 RSIOMA 交叉、ACD A-up/A-down、Pivot/SR 突破。
- "共振"：如果保留，必须定义评分公式和各模块权重。

**正确做法**：
- 每个概念必须有 **可量化定义**
- 每个规则必须有 **具体阈值**
- 每个流程必须有 **明确输入输出**
- 使用 "当 X > Y 时" 而非 "在适当的时候"

**排查方法**：
- 扫描所有 `.md` 文档中的模糊措辞
- 检查每个交易策略描述是否有具体的参数和阈值
- 检查共振/评分系统是否有明确的计算公式

---

## 审计边界与权限

### 只读优先
- 首先以 **只读模式** 审计，标记问题位置
- 不要立即修改代码逻辑

### 文档可修
- 发现文档中的错误描述可以直接修正
- 发现口号式措辞可以直接重写为精确描述

### 代码交易行为不能静默改
- **严禁**在不通知的情况下修改交易信号生成逻辑
- 如果发现代码交易行为有问题：
  1. 在审计报告中详细记录
  2. 标记为 `CRITICAL` 或 `WARNING`
  3. 提供修复建议
  4. **等待用户确认后再修改**

---

## 审计范围

### 必须检查的文件

1. **State Hex 核心**
   - `python/ai_engine/state_hex_encoding.py`
   - `python/ai_engine/state_hex_engine.py`
   - `python/ai_engine/d1_risk_officer.py`

2. **SQX 指标模块**
   - `python/indicators/` 下所有 RSIOMA、ACD、枢轴相关代码
   - `mql5/` 下所有指标 EA 代码

3. **交易信号与回测**
   - `python/backtest/state_hex_backtest.py`
   - `python/ai_engine/` 下所有信号生成代码
   - `run_live.py` 及相关的实时交易代码

4. **架构文档**
   - `docs/*.md` 所有文档
   - `MULTI_TIMEFREME_RESONANCE_FRAMEWORK.md`
   - `RSIOMA_ACD_PIVOT_TRADING_FRAMEWORK.md`
   - `HERMASS_NEXT_KIMI_QODER_PROMPTS_20260610.md`

5. **数据管道**
   - `build_state_*.py` 系列脚本
   - `update-h1`、`update-m15` 相关代码

### 检查方法

对每个文件，回答以下问题：
1. 是否将 state_hex 当作数值比较？
2. 是否将 `8` 描述为 "强" 或 "bull"？
3. 是否绕过 D1 Risk Officer 直接生成交易信号？
4. 是否混淆了不同周期的 state_hex？
5. 是否有口号式措辞？
6. 是否有不可验证的模糊描述？

---

## 审计报告格式

```markdown
# State Hex / SQX 一致性审计报告

## 执行摘要
- 审计时间：2026-06-11
- 审计范围：X 个文件
- 发现问题：Y 个 CRITICAL，Z 个 WARNING，W 个 INFO

## CRITICAL 问题（需立即修复）

### [C1] 问题标题
- **位置**：`文件路径:行号`
- **问题描述**：...
- **影响**：...
- **修复建议**：...
- **状态**：待修复 / 已修复

## WARNING 问题（建议修复）

### [W1] 问题标题
...

## INFO 问题（文档改进）

### [I1] 问题标题
...

## 附录：文件检查清单
| 文件 | 检查项1 | 检查项2 | ... | 状态 |
|------|---------|---------|-----|------|
| ...  | ...     | ...     | ... | ...  |
```

---

## 关键代码参考

### D1 Risk Officer 用法与代码风险边界

```python
from python.ai_engine.d1_risk_officer import D1RiskOfficer, gate_signal_fields

officer = D1RiskOfficer()

# 用法：通过 Risk Officer 判断
decision = officer.assess(d1_hex="F", trade_direction="BUY", lower_timeframe="M15")
if decision.allowed:
    # 注意：本审计任务不得执行交易；这里只是接口示例。
    pass

# 用法：使用 gate 函数
signal, confidence, reason, decision = gate_signal_fields(
    final_signal="BUY",
    confidence=0.85,
    reason="RSIOMA golden cross + pivot breakout",
    d1_hex="F",
    lower_timeframe="M15"
)
```

注意：当前 `D1RiskOfficer.direction_from_hex()` 中如存在 `int(hex) > 0 => long`、`int(hex) < 0 => short` 的粗略映射，必须在审计报告中列为代码风险。不要在本任务中静默修改该交易行为；应给出推荐补丁并等待人工确认。

### State Hex 正确语义

```python
# 用法：使用 describe 理解状态
from python.ai_engine.state_hex_encoding import describe_state
print(describe_state("8"))
# 输出: 8(8) = 多向/非空向 | 非收缩底座

print(describe_state("F"))
# 输出: F(15) = 多向/非空向 | 非收缩底座 + 幅动活跃 + 位置触发 + 趋势触发

print(describe_state("-F"))
# 输出: -F(-15) = 空向 | 非收缩底座 + 幅动活跃 + 位置触发 + 趋势触发
```

### 周期视角正确用法

```python
# 概念示例：D1 视角以 D1 close 作为 position 基准价
d1_hex = compute_d1_hex(d1_data, viewpoint_close=d1_close)

# 概念示例：H1 视角以 H1 close 作为 position 基准价
h1_view_d1_hex = compute_d1_hex(d1_data, viewpoint_close=h1_close)

# D1 Risk Officer 必须使用 D1 视角的 d1_hex
decision = officer.assess(d1_hex=d1_hex, ...)  # 正确
decision = officer.assess(d1_hex=h1_view_d1_hex, ...)  # 错误！
```

---

## 执行指令

1. 扫描所有目标文件，标记问题
2. 按 CRITICAL / WARNING / INFO 分类
3. 生成审计报告到 `reports/ops/qoder_state_sqx_consistency_audit_20260611.md`
4. 对于 CRITICAL 问题，提供具体修复代码建议
5. 对于文档问题，可直接修改文档
6. 对于代码交易行为问题，**只报告不修改**，等待用户确认

---

## 成功标准

- [ ] 所有 6 大高危模式均已排查
- [ ] 审计报告已生成并写入指定路径
- [ ] CRITICAL 问题有明确的修复建议
- [ ] 没有未经确认的代码交易行为修改
