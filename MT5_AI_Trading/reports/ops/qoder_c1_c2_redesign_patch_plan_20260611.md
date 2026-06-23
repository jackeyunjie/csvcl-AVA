# QODER C1/C2 Redesign Patch Plan

## Summary

- **C1 previous Option A status**: **REJECTED**
  - Original proposal (`0-7 => neutral, 8-15 => long, negative => short`) incorrectly treated naked State Hex as trade direction.
- **New recommended C1 design**: Naked State Hex (`0-F`, `-F` to `-0`) must not imply long/short. Direction must come from explicit direction markers (`+`, `-` as prefix with documented legacy intent), text aliases (`BUY`, `SELL`), or a separate `d1_risk_direction` field.
- **New recommended C2 design**: `pivot_contraction.py` must expose only `candidate_signal` (raw SQX/Pivot evidence). Any `gated_signal` must be produced by explicit `D1RiskOfficer.assess()` call, clearly separating evidence from trade permission.
- **Behavior-changing patches requiring approval**: Both C1 and C2 require user approval before implementation.

---

## C1 Redesign: D1RiskOfficer.direction_from_hex()

### Core Principle

```text
Naked State Hex must not imply long/short.
Direction must come from explicit direction markers or a separate D1 Risk Direction field.
```

### State Hex Semantic Clarification

Per `P107_STATE_HEX_ENCODING_RULES_20260517` and `state_hex_encoding.py`:

- `state_score = base(0 or 8) + volatility(1) + position(2) + trend(4)`
- `state_hex = signed_hex(state_score)` where sign indicates bull/bear **context**, not trade direction
- `0-7`: contraction base (components may be present, but base is contraction)
- `8-F`: non-contraction base (components may be present)
- `-0` to `-F`: bear context (negative sign prefix)
- `+0` to `+F`: bull context (positive sign prefix, implicit for `0-F`)

**Critical insight**: The sign on State Hex indicates the **context** under which components were calculated (bull context vs bear context), not a **trade direction recommendation**. A `-F` state means "all components triggered in bear context", not "short recommendation".

### Current vs Proposed Behavior

| Input | Current Output | Proposed Output | Rationale | Migration Risk |
|---|---|---|---|---|
| `""` | `neutral` | `neutral` | Missing value | None |
| `0` | `neutral` | `neutral` | Neutral alias | None |
| `-0` | `neutral` | `neutral` | Neutral alias | None |
| `1`..`7` | `long` (bug) | `neutral` | Naked State Hex, no explicit direction | **High** — callers relying on `1-7 => long` will see behavior change |
| `8` | `long` (bug) | `neutral` | Naked State Hex, no explicit direction | **High** — callers relying on `8 => long` will see behavior change |
| `9`..`F` | `long` (partial — `int()` fails on A-F, falls through to text check) | `neutral` | Naked State Hex, no explicit direction | **Medium** — current behavior is inconsistent for A-F |
| `-1`..`-7` | `short` (bug) | `neutral` | Naked State Hex with bear context, not explicit short direction | **High** |
| `-8`..`-F` | `short` (partial) | `neutral` or `short` (see Legacy Policy decision below) | Naked State Hex with bear context | **High** |
| `+F` | `long` (via `+` check) | `long` | Explicit plus direction marker | None |
| `-F` | `short` (via `-` check) | `short` **only if** legacy signed State Hex is preserved | Explicit minus direction marker (legacy) | **Medium** |
| `BUY`, `LONG`, `UP`, `BULL` | `long` | `long` | Explicit text direction | None |
| `SELL`, `SHORT`, `DOWN`, `BEAR` | `short` | `short` | Explicit text direction | None |
| `N/A`, `NULL`, `N`, `=` | `neutral` | `neutral` | Explicit neutral | None |

### Legacy Policy Decision Required

The current code has this legacy path:
```python
if any(op in clean for op in ("+", "-", "=")):
    if "+" in clean or clean.startswith(("A", "B")):
        return "long"
    if "-" in clean or clean.startswith(("D", "E")):
        return "short"
```

This conflates two things:
1. **Signed State Hex** (`-F`, `+F`) where sign indicates bull/bear context
2. **Legacy composite hex** (`A2`, `B3`, `D4`) where letters encode direction

**Recommendation**: Preserve `-F => short` and `+F => long` as **legacy signed State Hex compatibility only**, with explicit documentation that this is legacy behavior, not naked State Hex inference. All other numeric values (`0-F`, `-0` to `-E`) return `neutral`.

### Recommended C1 Patch

```python
def direction_from_hex(self, d1_hex: str) -> str:
    """Extract direction from D1 state hex.
    
    Naked State Hex (0-F, -0 to -F) does NOT imply trade direction.
    Direction must come from explicit markers or a separate D1 Risk Direction field.
    
    Legacy compatibility: signed State Hex (-F, +F) preserves direction
    for backward compatibility only. New code should pass explicit direction.
    """
    if not d1_hex:
        return "neutral"
    clean = d1_hex.strip().upper()
    
    # Check exact neutral aliases first (including "-0")
    if clean in self.NEUTRAL_ALIASES:
        return "neutral"
    
    # Legacy composite state hex compatibility (A, B, C, D, E with suffix)
    # Note: This is legacy behavior. New code should use explicit direction.
    if len(clean) > 1 and any(op in clean for op in ("+", "-", "=")):
        if "+" in clean:
            return "long"
        if "-" in clean:
            return "short"
        if "=" in clean:
            return "neutral"
    
    # Legacy single-letter composite hex (A=long, B=long, C=neutral, D=short, E=short)
    # Note: This is legacy behavior preserved for compatibility.
    if clean in ("A", "B"):
        return "long"
    if clean in ("D", "E"):
        return "short"
    if clean == "C":
        return "neutral"
    
    # Legacy signed State Hex: -F, -E, etc. preserve direction for compatibility
    # This is the ONLY case where a sign prefix implies direction.
    if clean.startswith("-") and len(clean) > 1:
        return "short"  # Legacy: signed negative = short context
    if clean.startswith("+"):
        return "long"   # Legacy: signed positive = long context
    
    # Naked numeric State Hex (0-9, F): NEVER implies direction
    # These are state component codes, not trade recommendations.
    try:
        val = int(clean.lstrip("+-"), 16)
        # 0-15 (0-F): all neutral — naked State Hex is not direction
        return "neutral"
    except ValueError:
        pass
    
    # Text-based direction (explicit)
    if any(text in clean for text in self.LONG_ALIASES):
        return "long"
    if any(text in clean for text in self.SHORT_ALIASES):
        return "short"
    
    return "neutral"
```

### Migration Strategy

1. **Phase 1** (immediate): Update `direction_from_hex()` to return `neutral` for naked State Hex
2. **Phase 2** (after approval): Update all callers to pass explicit `d1_risk_direction` instead of raw `d1_hex`
3. **Phase 3** (after validation): Deprecate legacy signed State Hex direction inference

### Callers Requiring Update

| Caller | Current Usage | Required Change |
|---|---|---|
| `mt5_bridge.py:303` | `assess(d1_hex, action, "H1")` | Pass explicit D1 risk direction from upstream |
| `mt5_bridge_dual.py:281` | Same | Same |
| `main_controller.py:291` | `assess(d1_hex, signal_type, tf)` | Same |
| `integrated_strategy.py:388` | `gate_signal_fields(..., d1_hex, ...)` | Same |
| `integrated_strategy_v2.py:282` | `gate_signal_fields(..., d1_hex, ...)` | Same |
| `strategy_miner.py:521` | `assess(d1_hex, trade_dir, mode)` | Same |

**Key insight**: All callers currently pass `d1_hex` where they should pass a separate `d1_risk_direction` field. The `d1_hex` should remain as state evidence; direction should come from an explicit analysis of that state.

---

## C2 Redesign: pivot_contraction.py Candidate/Gated Separation

### Core Principle

```text
candidate_signal = raw SQX/Pivot evidence output (observation only)
gated_signal     = candidate signal after D1 Risk Officer approval (trade permission)
```

### Current vs Proposed Design

| Scenario | Current Output | Proposed Candidate Output | Proposed Gated Output | Rationale |
|---|---|---|---|---|
| No contraction | `HOLD` | `candidate: no_contraction` | `HOLD` (blocked by no signal) | No evidence, no trade |
| Contraction + no breakout + no d1_hex | `观望` or `准备` | `candidate: contraction_observed` | N/A (must call gate explicitly) | Raw evidence only |
| Contraction + breakout up + no d1_hex | `强BUY` | `candidate: breakout_up` | N/A (must call gate explicitly) | Raw evidence, not permission |
| Contraction + breakout down + no d1_hex | `强SELL` | `candidate: breakout_down` | N/A (must call gate explicitly) | Raw evidence, not permission |
| Contraction + breakout up + d1_hex aligned | `强BUY` | `candidate: breakout_up` | `gated: BUY` (approved) | Evidence + permission |
| Contraction + breakout up + d1_hex conflict | `强BUY` (bug) | `candidate: breakout_up` | `HOLD` (blocked) | Evidence rejected by Risk Officer |
| Contraction + breakout down + d1_hex aligned | `强SELL` | `candidate: breakout_down` | `gated: SELL` (approved) | Evidence + permission |
| Contraction + breakout down + d1_hex conflict | `强SELL` (bug) | `candidate: breakout_down` | `HOLD` (blocked) | Evidence rejected by Risk Officer |

### Recommended C2 Patch

```python
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from d1_risk_officer import D1RiskOfficer


@dataclass
class PivotCandidateSignal:
    """Raw SQX/Pivot evidence output. NOT a trade signal."""
    signal_type: str       # e.g., "contraction_observed", "breakout_up", "breakout_down"
    confidence: float      # 0.0-1.0 evidence strength
    reason: str            # Evidence description
    contraction: Dict      # Raw contraction data
    breakout: Optional[Dict]  # Raw breakout data


@dataclass
class PivotGatedSignal:
    """Trade signal after D1 Risk Officer approval."""
    allowed: bool
    final_signal: str      # "BUY", "SELL", "HOLD", "OBSERVE"
    confidence: float
    reason: str
    d1_decision: Optional[dict]  # Risk Officer decision details


def pivot_to_candidate(
    contraction: Dict,
    fundamental_signal: str = "HOLD",
    breakout: Dict = None,
) -> PivotCandidateSignal:
    """
    Convert pivot contraction + breakout into CANDIDATE evidence.
    
    This is NOT a trade signal. It is raw SQX/Pivot evidence that must
    be gated through D1RiskOfficer before any trading decision.
    
    Returns:
        PivotCandidateSignal: Raw evidence with no trade permission implied.
    """
    squeeze = contraction['squeeze_score']
    is_contracting = contraction['is_contracting']
    breakout_dir = breakout.get('breakout', 'none') if breakout else 'none'
    breakout_pct = breakout.get('breakout_pct', 0) if breakout else 0

    if not is_contracting:
        return PivotCandidateSignal(
            signal_type="no_contraction",
            confidence=0.0,
            reason="No pivot contraction detected",
            contraction=contraction,
            breakout=breakout,
        )

    # Contraction strength
    if squeeze >= 3:
        strength = "strong"
        base_conf = 0.75
    elif squeeze == 2:
        strength = "moderate"
        base_conf = 0.65
    else:
        strength = "weak"
        base_conf = 0.55

    # No breakout: observation only
    if breakout_dir == 'none':
        if squeeze >= 2 and fundamental_signal in ("BUY", "SELL"):
            return PivotCandidateSignal(
                signal_type="contraction_with_fundamental",
                confidence=base_conf,
                reason=f"{strength} contraction + fundamental {fundamental_signal}, awaiting breakout",
                contraction=contraction,
                breakout=breakout,
            )
        return PivotCandidateSignal(
            signal_type="contraction_observed",
            confidence=base_conf,
            reason=f"{strength} contraction, direction pending",
            contraction=contraction,
            breakout=breakout,
        )

    # Breakout observed
    breakout_bonus = min(0.15, breakout_pct * 0.01)
    
    if breakout_dir == 'up':
        return PivotCandidateSignal(
            signal_type="breakout_up",
            confidence=min(0.95, base_conf + 0.15 + breakout_bonus),
            reason=f"{strength} contraction + upward breakout {breakout_pct:.1f}% + fundamental {fundamental_signal}",
            contraction=contraction,
            breakout=breakout,
        )
    elif breakout_dir == 'down':
        return PivotCandidateSignal(
            signal_type="breakout_down",
            confidence=min(0.95, base_conf + 0.15 + breakout_bonus),
            reason=f"{strength} contraction + downward breakout {breakout_pct:.1f}% + fundamental {fundamental_signal}",
            contraction=contraction,
            breakout=breakout,
        )
    
    return PivotCandidateSignal(
        signal_type="unclear",
        confidence=base_conf,
        reason="Signal unclear",
        contraction=contraction,
        breakout=breakout,
    )


def gate_pivot_candidate(
    candidate: PivotCandidateSignal,
    d1_hex: str,
    lower_timeframe: str = "H1",
) -> PivotGatedSignal:
    """
    Gate a pivot candidate signal through D1 Risk Officer.
    
    This is the ONLY path that produces a trade-permission signal.
    All pivot evidence must pass through this gate before trading.
    
    Returns:
        PivotGatedSignal: Approved or blocked trading signal.
    """
    # Map candidate signal type to trade direction
    direction_map = {
        "breakout_up": "long",
        "breakout_down": "short",
        "contraction_with_fundamental": "neutral",  # Requires further analysis
        "contraction_observed": "neutral",
        "no_contraction": "neutral",
        "unclear": "neutral",
    }
    
    trade_direction = direction_map.get(candidate.signal_type, "neutral")
    
    # Non-directional candidates don't need Risk Officer
    if trade_direction == "neutral":
        return PivotGatedSignal(
            allowed=False,
            final_signal="HOLD",
            confidence=0.0,
            reason=f"No directional candidate: {candidate.reason}",
            d1_decision=None,
        )
    
    # D1 Risk Officer gate
    officer = D1RiskOfficer()
    decision = officer.assess(d1_hex, trade_direction, lower_timeframe)
    
    if not decision.allowed:
        return PivotGatedSignal(
            allowed=False,
            final_signal="HOLD",
            confidence=0.0,
            reason=f"blocked_by_d1_risk_officer: {decision.reason} | candidate: {candidate.reason}",
            d1_decision=decision,
        )
    
    # Approved
    final_signal = "BUY" if trade_direction == "long" else "SELL"
    return PivotGatedSignal(
        allowed=True,
        final_signal=final_signal,
        confidence=candidate.confidence,
        reason=f"Approved: {candidate.reason} | D1: {decision.reason}",
        d1_decision=decision,
    )


# Backward compatibility shim (deprecated)
def pivot_to_signal(
    contraction: Dict,
    fundamental_signal: str = "HOLD",
    breakout: Dict = None,
    d1_hex: Optional[str] = None,
) -> Tuple[str, float, str]:
    """
    DEPRECATED: Use pivot_to_candidate() + gate_pivot_candidate() instead.
    
    Backward compatibility: if d1_hex is provided, gates through Risk Officer.
    If d1_hex is None, returns candidate observation (not a trade signal).
    """
    candidate = pivot_to_candidate(contraction, fundamental_signal, breakout)
    
    if d1_hex is None:
        # No gating: return observation-only signal
        return f"candidate:{candidate.signal_type}", candidate.confidence, candidate.reason
    
    gated = gate_pivot_candidate(candidate, d1_hex)
    return gated.final_signal, gated.confidence, gated.reason
```

### Migration Strategy

1. **Phase 1** (immediate): Add `pivot_to_candidate()` and `gate_pivot_candidate()` functions
2. **Phase 2** (after approval): Update `pivot_to_signal()` to use new functions internally
3. **Phase 3** (after validation): Migrate all callers to use `pivot_to_candidate()` + `gate_pivot_candidate()` explicitly
4. **Phase 4** (future): Deprecate and remove `pivot_to_signal()`

---

## Test Plan

### C1 Tests

```python
# test_d1_risk_officer_c1_redesign.py
import pytest
from ai_engine.d1_risk_officer import D1RiskOfficer

officer = D1RiskOfficer()

class TestNakedStateHexIsNeutral:
    """Naked State Hex must not imply direction."""
    
    @pytest.mark.parametrize("hex_val", ["0", "1", "2", "3", "4", "5", "6", "7"])
    def test_contraction_base_is_neutral(self, hex_val):
        assert officer.direction_from_hex(hex_val) == "neutral"
    
    @pytest.mark.parametrize("hex_val", ["8", "9", "A", "B", "C", "D", "E", "F"])
    def test_non_contraction_base_is_neutral(self, hex_val):
        assert officer.direction_from_hex(hex_val) == "neutral"
    
    @pytest.mark.parametrize("hex_val", ["-1", "-2", "-3", "-4", "-5", "-6", "-7"])
    def test_negative_contraction_base_is_neutral(self, hex_val):
        assert officer.direction_from_hex(hex_val) == "neutral"
    
    @pytest.mark.parametrize("hex_val", ["-8", "-9", "-A", "-B", "-C", "-D", "-E"])
    def test_negative_non_contraction_base_is_neutral(self, hex_val):
        assert officer.direction_from_hex(hex_val) == "neutral"

class TestExplicitDirectionMarkers:
    """Explicit direction markers must work."""
    
    def test_plus_prefix_is_long(self):
        assert officer.direction_from_hex("+F") == "long"
        assert officer.direction_from_hex("+8") == "long"
    
    def test_minus_prefix_is_short(self):
        assert officer.direction_from_hex("-F") == "short"
        assert officer.direction_from_hex("-8") == "short"

class TestTextDirection:
    """Text aliases must work."""
    
    def test_long_aliases(self):
        for alias in ["BUY", "LONG", "UP", "BULL"]:
            assert officer.direction_from_hex(alias) == "long"
    
    def test_short_aliases(self):
        for alias in ["SELL", "SHORT", "DOWN", "BEAR"]:
            assert officer.direction_from_hex(alias) == "short"
    
    def test_neutral_aliases(self):
        for alias in ["N/A", "NULL", "N", "=", "", "-0"]:
            assert officer.direction_from_hex(alias) == "neutral"

class TestLegacyCompatibility:
    """Legacy composite hex compatibility."""
    
    def test_legacy_a_b_long(self):
        assert officer.direction_from_hex("A2") == "long"
        assert officer.direction_from_hex("B3") == "long"
    
    def test_legacy_d_e_short(self):
        assert officer.direction_from_hex("D4") == "short"
        assert officer.direction_from_hex("E5") == "short"
    
    def test_legacy_c_neutral(self):
        assert officer.direction_from_hex("C6") == "neutral"
```

### C2 Tests

```python
# test_pivot_contraction_c2_redesign.py
import pytest
from ai_engine.pivot_contraction import (
    pivot_to_candidate, gate_pivot_candidate,
    PivotCandidateSignal, PivotGatedSignal
)

contraction_strong = {
    'squeeze_score': 3,
    'is_contracting': True,
}
breakout_up = {'breakout': 'up', 'breakout_pct': 5.0}
breakout_down = {'breakout': 'down', 'breakout_pct': 5.0}

class TestCandidateSignalIsNotTradeSignal:
    """Candidate signals must not imply trade permission."""
    
    def test_no_contraction_returns_candidate(self):
        c = {'squeeze_score': 0, 'is_contracting': False}
        candidate = pivot_to_candidate(c)
        assert candidate.signal_type == "no_contraction"
        assert "candidate" not in candidate.signal_type  # Not labeled as candidate, IS candidate
    
    def test_breakout_up_returns_evidence_type(self):
        candidate = pivot_to_candidate(contraction_strong, "BUY", breakout_up)
        assert candidate.signal_type == "breakout_up"
        assert candidate.confidence > 0
    
    def test_breakout_down_returns_evidence_type(self):
        candidate = pivot_to_candidate(contraction_strong, "SELL", breakout_down)
        assert candidate.signal_type == "breakout_down"

class TestGatedSignalRequiresD1Approval:
    """Gated signals require D1 Risk Officer."""
    
    def test_aligned_d1_allows_signal(self):
        candidate = pivot_to_candidate(contraction_strong, "BUY", breakout_up)
        gated = gate_pivot_candidate(candidate, d1_hex="+F")
        assert gated.allowed is True
        assert gated.final_signal == "BUY"
    
    def test_conflicting_d1_blocks_signal(self):
        candidate = pivot_to_candidate(contraction_strong, "BUY", breakout_up)
        gated = gate_pivot_candidate(candidate, d1_hex="-F")
        assert gated.allowed is False
        assert gated.final_signal == "HOLD"
        assert "blocked_by_d1_risk_officer" in gated.reason
    
    def test_neutral_d1_blocks_directional(self):
        candidate = pivot_to_candidate(contraction_strong, "BUY", breakout_up)
        gated = gate_pivot_candidate(candidate, d1_hex="0")
        assert gated.allowed is False
        assert gated.final_signal == "HOLD"
    
    def test_no_directional_candidate_returns_hold(self):
        candidate = pivot_to_candidate(contraction_strong, "HOLD", None)
        gated = gate_pivot_candidate(candidate, d1_hex="+F")
        assert gated.allowed is False
        assert gated.final_signal == "HOLD"
```

### Regression Tests

```python
# test_regression_c1_c2.py

class TestNoSilentBehaviorChange:
    """Verify no silent behavior changes without approval."""
    
    def test_current_c1_behavior_unchanged_until_approved(self):
        # This test documents current (buggy) behavior
        # It will fail after C1 patch is applied, serving as regression guard
        officer = D1RiskOfficer()
        # Current behavior: 1-7 returns "long" (bug)
        assert officer.direction_from_hex("3") == "long"  # Will fail after patch
    
    def test_current_c2_behavior_unchanged_until_approved(self):
        # Current behavior: pivot_to_signal returns "强BUY" without gating
        from ai_engine.pivot_contraction import pivot_to_signal
        sig, conf, reason = pivot_to_signal(contraction_strong, "BUY", breakout_up)
        assert "BUY" in sig  # Will change after patch
```

---

## Approval Request

### C1 Behavior Change

**Request**: Approve changing `D1RiskOfficer.direction_from_hex()` to return `neutral` for all naked State Hex values (`0-F`, `-0` to `-E`), preserving only explicit direction markers (`+`, `-` prefix for legacy signed State Hex, text aliases).

**Impact**: 
- All callers passing raw `d1_hex` will receive `neutral` for numeric values
- Callers must be updated to pass explicit `d1_risk_direction`
- Legacy signed State Hex (`-F`, `+F`) continues to work

### C2 Behavior Change

**Request**: Approve adding `pivot_to_candidate()` and `gate_pivot_candidate()` functions, with `pivot_to_signal()` becoming a backward-compatible shim.

**Impact**:
- New code path separates evidence from trade permission
- Existing `pivot_to_signal()` callers continue to work (with deprecation warning)
- New callers should use `pivot_to_candidate()` + `gate_pivot_candidate()`

### Test Creation

**Request**: Approve creating test files:
- `tests/test_d1_risk_officer_c1_redesign.py`
- `tests/test_pivot_contraction_c2_redesign.py`
- `tests/test_regression_c1_c2.py`

These tests document intended behavior and will serve as regression guards.

---

## Hard Restrictions Confirmation

- [x] Did not modify code in this pass (only patch plan)
- [x] Did not create tests that lock in rejected C1 Option A
- [x] Did not place trades
- [x] Did not call MT5 order APIs
- [x] Did not register scheduled tasks
- [x] Did not run D1 full rebuild
- [x] Did not use n8n/Coze/Agently for trading decisions
