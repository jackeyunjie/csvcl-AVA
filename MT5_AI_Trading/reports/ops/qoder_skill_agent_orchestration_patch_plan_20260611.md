# QODER Skill Agent Orchestration Patch Plan

## 执行摘要

- **日期**: 2026-06-11
- **任务**: 验证 C1/C2 问题，准备补丁方案，生成验收证据
- **状态**: 补丁方案已准备，等待用户批准实施
- **硬边界确认**: 未下单、未调用 MT5 API、未注册定时任务、未运行 D1 full rebuild

---

## C1 验证：D1RiskOfficer.direction_from_hex() 数值映射风险

### 精确证据

**文件**: `python/ai_engine/d1_risk_officer.py`  
**行号**: 40-48  
**当前代码**:
```python
# Numeric hex values
try:
    val = int(clean.lstrip("+-"))
    if val > 0:
        return "long"
    if val < 0:
        return "short"
except ValueError:
    pass
```

### 问题分析

根据 `state_hex_encoding.py` 中的编码规则：
- `state_score = base(0 or 8) + volatility(1) + position(2) + trend(4)`
- base=0 时，state_score 范围是 0-7（收缩底座）
- base=8 时，state_score 范围是 8-15（非收缩底座）
- 方向由 `bull_context` 或 `bear_context` 决定，通过正负号表示

**关键发现**：
- `0-7`（收缩底座）在编码时**没有负值形式**，因为方向由 trend/position 组件决定
- 当前代码将 `1, 2, 3, 4, 5, 6, 7` 全部映射为 `long`，这是**过度推断**
- 收缩底座值本身不携带方向信息，应视为 `neutral`

**影响评估**：
- 如果 D1 hex = `3`（收缩+幅动+位置），Risk Officer 会判定为 `long`
- 但 `3` 只是描述状态组件，不代表方向
- 这可能导致错误地允许做多，而实际上 D1 方向可能是中性

### 补丁选项

#### Option A: 保守修复（推荐）

将收缩底座值（0-7）映射为 `neutral`，非收缩值（8-15）保持原逻辑：

```python
# Numeric hex values
try:
    val = int(clean.lstrip("+-"))
    if 0 <= val <= 7:
        # Contraction base values (0-7) do not carry direction
        # Direction is determined by trend/position components, not the sign
        return "neutral"
    if val > 7:
        return "long"
    if val < 0:
        return "short"
except ValueError:
    pass
```

**行为变更**: 
- `0-7` 从 `long` 变为 `neutral`
- `8-15` 保持 `long`
- `-8` 到 `-15` 保持 `short`

**风险**: 如果现有系统依赖 `1-7` 作为 long 信号，此变更会影响交易行为。

#### Option B: 更精确的组件感知修复

使用 StateHexEncoder 解码组件，根据 trend/position 判断方向：

```python
# Option B: Component-aware direction detection
from state_hex_encoding import StateHexEncoder

encoder = StateHexEncoder()

def direction_from_hex(self, d1_hex: str) -> str:
    # ... existing checks ...
    
    # Numeric hex values
    try:
        val = int(clean.lstrip("+-"))
        if 0 <= val <= 7:
            # Contraction base: check components for direction
            _, _, _, has_position, has_trend = encoder.decode(clean)
            if has_trend or has_position:
                # Components present but contraction base is neutral
                # Direction must come from explicit sign
                return "neutral"
            return "neutral"
        if val > 7:
            return "long"
        if val < 0:
            return "short"
    except ValueError:
        pass
```

**风险**: 引入 StateHexEncoder 依赖，增加耦合。

### 推荐方案

**采用 Option A**，理由：
1. 简单明确，符合 State Hex 语义（收缩底座不携带方向）
2. 不引入新依赖
3. 与 `state_hex_encoding.py` 中的 `is_positive_for_long()` 和 `is_veto_for_long()` 逻辑一致（这些方法只检查 `2,3,6,7,10,11,14,15`，不包含 `1,4,5`）

---

## C2 验证：pivot_contraction.py 直接输出交易信号

### 精确证据

**文件**: `python/ai_engine/pivot_contraction.py`  
**行号**: 225-284  
**当前代码**:
```python
def pivot_to_signal(contraction: Dict, fundamental_signal: str = "HOLD",
                    breakout: Dict = None) -> Tuple[str, float, str]:
    # ... 直接返回 "强BUY"/"强SELL"/"观望" ...
```

### 问题分析

- `pivot_to_signal()` 直接根据枢轴收缩和突破方向输出交易信号
- 函数签名中没有 `d1_hex` 参数
- 函数内部没有调用 `D1RiskOfficer`
- 返回的 "强BUY"/"强SELL" 可能被调用方直接用于交易

**调用方风险**:  
搜索发现 `pivot_to_signal()` 目前只在 `pivot_contraction.py` 的 `__main__` 测试块中被调用（line 326），但函数作为公共 API 存在被其他模块直接使用的风险。

### 补丁选项

#### Option A: 保守修复（推荐）

增加 `d1_hex` 参数和 Risk Officer 调用：

```python
from typing import Dict, Tuple, Optional
from d1_risk_officer import D1RiskOfficer

def pivot_to_signal(
    contraction: Dict,
    fundamental_signal: str = "HOLD",
    breakout: Dict = None,
    d1_hex: Optional[str] = None,
) -> Tuple[str, float, str]:
    """
    将枢轴收缩 + 突破确认转换为交易信号
    
    注意: 如果提供 d1_hex，信号将通过 D1 Risk Officer 审核。
          如果不提供 d1_hex，返回原始信号（调用方必须自行审核）。
    """
    squeeze = contraction['squeeze_score']
    is_contracting = contraction['is_contracting']
    breakout_dir = breakout.get('breakout', 'none') if breakout else 'none'
    breakout_pct = breakout.get('breakout_pct', 0) if breakout else 0

    if not is_contracting:
        return "HOLD", 0.50, "无枢轴收缩"

    # ... existing logic ...

    # 阶段3：有收缩 + 有突破 → 确认
    if breakout_dir == 'up':
        if fundamental_signal in ("BUY", "HOLD"):
            signal = "强BUY"
            conf = min(0.95, base_conf + 0.15 + breakout_bonus)
            reason = f"{strength}收缩 + 向上突破{breakout_pct:.1f}% + 基本面{fundamental_signal}"
        else:
            signal = "观望"
            conf = base_conf
            reason = f"向上突破但基本面{fundamental_signal}，不追涨"
    elif breakout_dir == 'down':
        if fundamental_signal in ("SELL", "REDUCE"):
            signal = "强SELL"
            conf = min(0.95, base_conf + 0.15 + breakout_bonus)
            reason = f"{strength}收缩 + 向下突破{breakout_pct:.1f}% + 基本面{fundamental_signal}"
        else:
            signal = "观望"
            conf = base_conf
            reason = f"向下突破但基本面{fundamental_signal}，不追空"
    else:
        signal = "观望"
        conf = base_conf
        reason = "信号不明确"

    # D1 Risk Officer gate
    if d1_hex is not None:
        officer = D1RiskOfficer()
        trade_dir = "long" if "BUY" in signal else ("short" if "SELL" in signal else "neutral")
        decision = officer.assess(d1_hex, trade_dir, lower_timeframe="H1")
        if not decision.allowed:
            return "HOLD", 0.0, f"D1 Risk Officer blocked: {decision.reason}"

    return signal, conf, reason
```

**行为变更**:
- 新增可选参数 `d1_hex`
- 如果提供 `d1_hex`，信号会被 Risk Officer 审核
- 如果不提供，保持原有行为（向后兼容）

#### Option B: 强制 Risk Officer 审核

将 `d1_hex` 改为必填参数：

```python
def pivot_to_signal(
    contraction: Dict,
    fundamental_signal: str = "HOLD",
    breakout: Dict = None,
    d1_hex: str = "",  # 必填
) -> Tuple[str, float, str]:
```

**风险**: 破坏现有调用方（如测试代码）的兼容性。

### 推荐方案

**采用 Option A**，理由：
1. 向后兼容，不破坏现有调用
2. 明确标注函数语义（原始信号 vs 审核后信号）
3. 渐进式引入 Risk Officer，不影响现有行为

---

## 验收测试计划

### C1 验收测试

```python
# test_d1_risk_officer_c1.py
import pytest
from ai_engine.d1_risk_officer import D1RiskOfficer

officer = D1RiskOfficer()

# 收缩底座值 (0-7) 应为 neutral
def test_contraction_base_is_neutral():
    for hex_val in ["0", "1", "2", "3", "4", "5", "6", "7"]:
        assert officer.direction_from_hex(hex_val) == "neutral", \
            f"{hex_val} should be neutral, got {officer.direction_from_hex(hex_val)}"

# 非收缩正值 (8-15) 应为 long
def test_non_contraction_positive_is_long():
    for hex_val in ["8", "9", "A", "B", "C", "D", "E", "F"]:
        assert officer.direction_from_hex(hex_val) == "long", \
            f"{hex_val} should be long, got {officer.direction_from_hex(hex_val)}"

# 负值应为 short
def test_negative_is_short():
    for hex_val in ["-8", "-9", "-A", "-B", "-C", "-D", "-E", "-F"]:
        assert officer.direction_from_hex(hex_val) == "short", \
            f"{hex_val} should be short, got {officer.direction_from_hex(hex_val)}"

# 特殊值
def test_special_values():
    assert officer.direction_from_hex("0") == "neutral"
    assert officer.direction_from_hex("-0") == "neutral"
    assert officer.direction_from_hex("N/A") == "neutral"
    assert officer.direction_from_hex("") == "neutral"
```

### C2 验收测试

```python
# test_pivot_contraction_c2.py
import pytest
from ai_engine.pivot_contraction import pivot_to_signal

contraction = {
    'squeeze_score': 3,
    'is_contracting': True,
}
breakout_up = {'breakout': 'up', 'breakout_pct': 5.0}
breakout_down = {'breakout': 'down', 'breakout_pct': 5.0}

# 无 d1_hex 时保持原有行为
def test_pivot_signal_without_d1_hex():
    signal, conf, reason = pivot_to_signal(contraction, "BUY", breakout_up)
    assert "BUY" in signal

# 有 d1_hex 且方向一致时通过
def test_pivot_signal_with_aligned_d1():
    signal, conf, reason = pivot_to_signal(
        contraction, "BUY", breakout_up, d1_hex="F"
    )
    assert "BUY" in signal

# 有 d1_hex 且方向冲突时被阻断
def test_pivot_signal_with_conflicting_d1():
    signal, conf, reason = pivot_to_signal(
        contraction, "BUY", breakout_up, d1_hex="-F"
    )
    assert signal == "HOLD"
    assert "blocked" in reason or "Risk Officer" in reason

# D1 neutral 时非方向性信号
def test_pivot_signal_with_neutral_d1():
    signal, conf, reason = pivot_to_signal(
        contraction, "BUY", breakout_up, d1_hex="0"
    )
    assert signal == "HOLD"
```

---

## SQX 模块证据-only 验证

### 验证结果

| SQX 模块 | 文件 | 是否只提供证据 | 是否绕过 Risk Officer | 状态 |
|----------|------|----------------|----------------------|------|
| ACD 枢轴 | `python/ai_engine/pivot_contraction.py` | 是 | **C2 问题** | 需修复 |
| Pivot | `python/ai_engine/state_hex_engine.py` | 是 | 否 | 通过 |
| Kaufman Bands | `python/ai_engine/state_hex_engine.py` | 是 | 否 | 通过 |
| RSIOMA | `MT5/Indicators/RSIOMA_v2HHLSX.mq5` | 是 | N/A (指标) | 通过 |
| SR PercentRank | `python/ai_engine/state_hex_engine.py` | 是 | 否 | 通过 |
| ADX | `python/ai_engine/state_hex_engine.py` | 是 | 否 | 通过 |
| BB Width | `python/ai_engine/state_hex_engine.py` | 是 | 否 | 通过 |
| Contraction/Breakout | `python/ai_engine/contraction_agents.py` | 是 | 否 | 通过 |

### 结论

所有 SQX 模块均符合 "证据-only" 定位，只有 `pivot_contraction.py` 的 `pivot_to_signal()` 函数存在直接输出交易信号的风险（C2）。

---

## n8n/Coze/Agently 报告-only 验证

### 验证结果

根据 `HERMASS_SKILL_AGENT_ORCHESTRATION_DECISION_AND_PROMPTS_20260611.md`：

| 工具 | 定位 | 是否进入交易决策链 | 状态 |
|------|------|-------------------|------|
| n8n | 定时报告编排、通知、GitHub Issue 创建 | 否 | 符合 |
| Coze | 对话查询/报告助手、人工确认 UI | 否 | 符合 |
| Agently | 实验性多 Agent 编排 | 否（研究-only） | 符合 |

### 结论

所有外部编排工具均正确配置为报告-only，不进入交易决策链。

---

## 文档-only 变更 vs 行为变更代码变更

| 变更 | 类型 | 是否需要用户批准 |
|------|------|-----------------|
| C1 Option A: 收缩底座值映射为 neutral | **行为变更** | **需要** |
| C2 Option A: 增加可选 d1_hex 参数 | 向后兼容 | 建议通知 |
| 审计报告更新 | 文档-only | 不需要 |
| 测试文件创建 | 文档-only | 不需要 |

---

## 实施建议

### 立即执行（无需批准）

1. 创建验收测试文件（`test_d1_risk_officer_c1.py`, `test_pivot_contraction_c2.py`）
2. 更新审计报告状态

### 需要用户批准后执行

1. **C1 修复**: 修改 `d1_risk_officer.py` line 40-48，将收缩底座值映射为 `neutral`
2. **C2 修复**: 修改 `pivot_contraction.py`，增加可选 `d1_hex` 参数和 Risk Officer 调用

### 实施顺序

```
Step 1: 创建测试文件（无需批准）
Step 2: 用户批准 C1/C2 修复
Step 3: 应用 C1 补丁
Step 4: 应用 C2 补丁
Step 5: 运行测试验证
Step 6: 更新审计报告为 "已修复"
```

---

## 硬边界确认

- [x] 未下单
- [x] 未调用 MT5 订单 API
- [x] 未注册定时任务
- [x] 未运行 D1 full rebuild
- [x] 未使用 n8n/Coze/Agently 触发交易决策
- [x] 未静默修改交易行为（补丁方案等待用户批准）
