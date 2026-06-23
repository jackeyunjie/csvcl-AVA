# State Hex / SQX 一致性审计报告

## 执行摘要

- **审计时间**：2026-06-11
- **审计范围**：14 个核心文件（State Hex 核心、SQX 指标、交易信号、架构文档）
- **发现问题**：2 个 CRITICAL，4 个 WARNING，3 个 INFO
- **总体评估**：项目整体架构符合 State Hex 语义规范，D1 Risk Officer 在主要交易路径中被正确调用。但存在两处关键代码风险需要人工确认修复。

---

## CRITICAL 问题（需立即修复）

### [C1] D1RiskOfficer.direction_from_hex() 中 int(hex)>0 => long 的粗略映射风险

- **位置**：`python/ai_engine/d1_risk_officer.py:41-46`
- **问题描述**：
  ```python
  try:
      val = int(clean.lstrip("+-"))
      if val > 0:
          return "long"
      if val < 0:
          return "short"
  except ValueError:
      pass
  ```
  这段代码将任何正数 state_hex（如 `1`, `2`, `3`, `4`, `5`, `6`, `7`）都映射为 `long`，但 `0-7` 是**收缩底座**状态，它们的方向由 trend/position 组件决定，并非简单的 "正数=long"。例如 `3`（收缩+幅动+位置）在空向语境下应为 `-3`，但 `3` 本身被映射为 `long` 可能产生误导。
- **影响**：如果 D1 hex 为收缩底座值（0-7），Risk Officer 可能错误地将其判定为 long 方向，导致交易方向错误。
- **修复建议**：
  收缩底座值（0-7）本身不携带方向信息，应返回 `neutral`，或至少需要检查其组件。推荐修改：
  ```python
  # 收缩底座值 (0-7) 不携带方向，应返回 neutral
  try:
      val = int(clean.lstrip("+-"))
      if 0 <= val <= 7:
          return "neutral"  # 收缩底座，方向由其他逻辑判断
      if val > 7:
          return "long"
      if val < 0:
          return "short"
  except ValueError:
      pass
  ```
- **状态**：待修复（需人工确认）

### [C2] pivot_contraction.py 中 pivot_to_signal() 直接输出交易信号，未经过 D1 Risk Officer

- **位置**：`python/ai_engine/pivot_contraction.py:225-284`
- **问题描述**：`pivot_to_signal()` 函数直接根据枢轴收缩和突破方向输出 "强BUY"/"强SELL"/"观望" 信号，**没有任何调用 D1RiskOfficer 的逻辑**。虽然该函数返回的是信号元组而非直接执行交易，但如果调用方直接使用该信号而不经过 Risk Officer，就会绕过硬门槛。
- **影响**：如果其他模块直接调用 `pivot_to_signal()` 并使用其返回的 "强BUY"/"强SELL" 信号，将绕过 D1 Risk Officer 的 D1 方向审核。
- **修复建议**：
  1. 在 `pivot_to_signal()` 函数签名中增加 `d1_hex` 参数
  2. 在函数内部调用 `D1RiskOfficer().assess()` 审核信号
  3. 或者明确标注该函数为 "原始信号生成，调用方必须经过 Risk Officer"
- **状态**：待修复（需人工确认）

---

## WARNING 问题（建议修复）

### [W1] strategy_miner.py 中 _is_squeeze() 和 _has_trend() 使用 int(hex) 进行位运算，存在语义混淆风险

- **位置**：`python/ai_engine/strategy_miner.py:325-344`
- **问题描述**：
  ```python
  @staticmethod
  def _is_squeeze(hex_val: str) -> bool:
      v = abs(int(hex_val.lstrip('-'), 16))
      return (v & 8) == 0  # bit3=0 表示收缩
  
  @staticmethod
  def _has_trend(hex_val: str) -> bool:
      v = abs(int(hex_val.lstrip('-'), 16))
      return (v & 4) != 0  # bit2=+4 表示有趋势
  ```
  这里使用位运算检查 state_hex 的组件，虽然技术上正确（因为 state_hex 的编码确实基于位运算），但**注释和函数名存在误导**：
  - `_is_squeeze` 检查的是 `bit3=0`（base=0，收缩底座），但函数名暗示 "是否是收缩状态"，而实际上 `8-F` 是非收缩，`0-7` 是收缩
  - `_has_trend` 检查 `bit2=4`，但 `4` 是趋势组件位，不是 "有趋势" 的完整语义
- **影响**：代码逻辑正确，但注释和命名可能导致维护者误解 State Hex 的语义。
- **修复建议**：
  更新注释，明确说明这是基于 P107 编码规则的位运算检查：
  ```python
  @staticmethod
  def _is_squeeze(hex_val: str) -> bool:
      """检测是否收缩底座 (base=0, 即值 0-7)"""
      v = abs(int(hex_val.lstrip('-'), 16))
      return v < 8  # 更清晰的写法
  
  @staticmethod
  def _has_trend(hex_val: str) -> bool:
      """检测是否包含趋势组件 (trend bit = 4)"""
      v = abs(int(hex_val.lstrip('-'), 16))
      return (v & 4) != 0
  ```
- **状态**：建议修复

### [W2] strategy_miner.py 中 _count_bull() 将非负 hex 视为 bullish，存在方向误判风险

- **位置**：`python/ai_engine/strategy_miner.py:347-365`
- **问题描述**：
  ```python
  def _count_bull(row, mode: str = "h1") -> int:
      for col in cols:
          val = str(row.get(col, ''))
          if val and not val.startswith('-') and val != 'N/A':
              try:
                  v = int(val, 16)
                  if (v & 4) != 0:  # has trend
                      count += 1
  ```
  该函数将 "非负 hex 且包含趋势组件" 视为 bullish，但：
  - `8`（非收缩底座，无组件）不包含趋势组件，不会被计数
  - `C`（非收缩+趋势）会被计数为 bullish
  - 但 `0-7` 的收缩底座值即使包含趋势组件（如 `4`=收缩+趋势）也会被计数
  - **问题**：收缩底座值 `4` 被计数为 bullish，但 `4` 本身没有方向符号，其方向由 trend/position 决定
- **影响**：回测统计中的 "bullish 周期数" 可能不准确，导致策略评估偏差。
- **修复建议**：
  明确区分 "有趋势组件" 和 "bullish 方向"，或增加方向语境检查。
- **状态**：建议修复

### [W3] MULTI_TIMEFREME_RESONANCE_FRAMEWORK.md 中 D1View 示例使用 d1_hex='8'，可能误导读者

- **位置**：`docs/MULTI_TIMEFREME_RESONANCE_FRAMEWORK.md:65`
- **问题描述**：
  ```python
  class D1View:
      def analyze(self, symbol):
          return {
              'd1_hex': '8',
              # ...
          }
  ```
  示例中 `d1_hex='8'`，但 `8` 是中性非收缩状态。在 "强多头趋势" 的上下文中使用 `8` 作为示例，可能让读者误以为 `8` 代表某种趋势状态。
- **影响**：文档示例可能误导读者对 State Hex 语义的理解。
- **修复建议**：将示例中的 `d1_hex` 改为更具代表性的值，如 `'F'`（非收缩+全触发，多向语境）或 `'C'`（非收缩+趋势）。
- **状态**：建议修复（文档可直接修改）

### [W4] 多周期共振框架中 "共振" 评分公式未完全量化

- **位置**：`docs/MULTI_TIMEFREME_RESONANCE_FRAMEWORK.md:244-260`
- **问题描述**：共振矩阵中使用了 "完美共振"、"强共振"、"中等共振" 等定性描述，但评分公式中各模块权重的具体计算逻辑未在文档中完整展示。
- **影响**：框架难以被精确复现和验证。
- **修复建议**：补充完整的评分公式和权重计算代码示例。
- **状态**：建议修复（文档可直接修改）

---

## INFO 问题（文档改进）

### [I1] RSIOMA_ACD_PIVOT_TRADING_FRAMEWORK.md 中 "强多头"/"强空头" 表述需补充定义

- **位置**：`docs/RSIOMA_ACD_PIVOT_TRADING_FRAMEWORK.md:52-53`
- **问题描述**：文档中使用了 "强多头"、"强空头" 表述，但未明确这些术语的量化标准。
- **修复建议**：补充定义，如 "强多头 = RSIOMA > 70 且 TrendUp = 12 且 D1 Risk Direction = long"。
- **状态**：建议补充

### [I2] QODER_STATE_SQX_CONSISTENCY_AUDIT_PROMPT_20260611.md 自身包含口号式措辞的示例

- **位置**：`docs/QODER_STATE_SQX_CONSISTENCY_AUDIT_PROMPT_20260611.md:107-110`
- **问题描述**：文档自身在解释 "顺势而为"、"严格风控" 等措辞时，使用了 "例如 D1 Risk Direction、MA144/169/200 结构、ADX 阈值" 等，但这些示例本身也需要更具体的阈值定义。
- **修复建议**：将示例中的模糊描述替换为具体阈值，如 "ADX > 25 判定为趋势"。
- **状态**：建议补充

### [I3] 部分代码文件缺少 State Hex 语义的注释说明

- **位置**：`python/ai_engine/state_hex_encoding.py`、`python/ai_engine/state_hex_engine.py`
- **问题描述**：核心编码文件虽然有 docstring，但在关键函数（如 `encode()`、`decode()`）中缺少对 State Hex 语义（不是线性强弱分数）的显式注释。
- **修复建议**：在 `encode()` 和 `decode()` 函数的 docstring 中增加语义说明。
- **状态**：建议补充

---

## 附录：文件检查清单

| 文件 | 检查项1:数值比较 | 检查项2:D1=8强多 | 检查项3:绕过RiskOfficer | 检查项4:周期混淆 | 检查项5:口号措辞 | 状态 |
|------|------------------|------------------|-------------------------|------------------|------------------|------|
| `python/ai_engine/state_hex_encoding.py` | 无 | 无 | N/A | N/A | 无 | 通过 |
| `python/ai_engine/state_hex_engine.py` | 无 | 无 | N/A | 无 | 无 | 通过 |
| `python/ai_engine/d1_risk_officer.py` | **有(C1)** | 无 | N/A | N/A | 无 | **需修复** |
| `python/ai_engine/strategy_miner.py` | **有(W1,W2)** | 无 | 无 | 无 | 无 | **需修复** |
| `python/ai_engine/pivot_contraction.py` | 无 | 无 | **有(C2)** | 无 | 无 | **需修复** |
| `python/ai_engine/contraction_agents.py` | 无 | 无 | 无 | 无 | 无 | 通过 |
| `python/ai_engine/trading_strategy.py` | 无 | 无 | 无 | 无 | 无 | 通过 |
| `python/strategies/integrated_strategy.py` | 无 | 无 | 无 | 无 | 无 | 通过 |
| `python/strategies/integrated_strategy_v2.py` | 无 | 无 | 无 | 无 | 无 | 通过 |
| `python/core/mt5_bridge.py` | 无 | 无 | 无 | 无 | 无 | 通过 |
| `python/core/mt5_bridge_dual.py` | 无 | 无 | 无 | 无 | 无 | 通过 |
| `python/core/main_controller.py` | 无 | 无 | 无 | 无 | 无 | 通过 |
| `python/backtest_platform/strategy_layer.py` | 无 | 无 | 无 | 无 | 无 | 通过 |
| `python/backtest_platform/compute_layer.py` | 无 | 无 | 无 | 无 | 无 | 通过 |
| `docs/MULTI_TIMEFREME_RESONANCE_FRAMEWORK.md` | N/A | **有(W3)** | 无 | 无 | **有(W4)** | **需修复** |
| `docs/RSIOMA_ACD_PIVOT_TRADING_FRAMEWORK.md` | N/A | 无 | 无 | 无 | **有(I1)** | 建议补充 |
| `docs/QODER_STATE_SQX_CONSISTENCY_AUDIT_PROMPT_20260611.md` | N/A | 无 | 无 | 无 | **有(I2)** | 建议补充 |

---

## 关键发现总结

### 符合规范的部分

1. **D1 Risk Officer 在主要交易路径中被正确调用**：
   - `mt5_bridge.py:303` — 下单前调用 `D1RiskOfficer().assess()`
   - `mt5_bridge_dual.py:281` — 同上
   - `main_controller.py:291` — 信号执行前调用 Risk Officer
   - `integrated_strategy.py:388` — 使用 `gate_signal_fields()`
   - `integrated_strategy_v2.py:282` — 使用 `gate_signal_fields()`
   - `strategy_miner.py:521` — 回测中调用 `risk_officer.assess()`

2. **State Hex 未被当作线性强弱分数**：
   - 未发现 `state_hex > X` 或 `state_hex < X` 的数值比较
   - `strategy_miner.py` 中的位运算是正确的组件检查

3. **周期视角基本正确**：
   - `state_hex_engine.py` 中 `compute_quintuplets()` 正确区分了各周期视角
   - D1 hex 和 H1 hex 的计算使用了不同的 viewpoint_close

### 需要修复的部分

1. **C1: D1RiskOfficer 中收缩底座值的方向判定** — 需人工确认修复方案
2. **C2: pivot_contraction.py 直接输出交易信号** — 需增加 Risk Officer 调用或明确标注
3. **W1/W2: strategy_miner.py 中的位运算注释和 bullish 计数逻辑** — 建议优化
4. **W3/W4: 文档中的示例和评分公式** — 可直接修改

---

## 修复优先级建议

| 优先级 | 问题 | 操作 |
|--------|------|------|
| P0 | C1: D1RiskOfficer 收缩底座方向判定 | **人工确认后修复** |
| P0 | C2: pivot_contraction.py 绕过 Risk Officer | **人工确认后修复** |
| P1 | W3: 文档示例 d1_hex='8' | 直接修改文档 |
| P1 | W4: 共振评分公式补充 | 直接修改文档 |
| P2 | W1/W2: strategy_miner.py 注释优化 | 建议修复 |
| P2 | I1/I2/I3: 文档补充定义 | 建议补充 |
