# QODER Prompt: Redesign C1/C2 Patch Plan

Date: 2026-06-11
Status: Follow-up instruction after review

## Context

The previous QODER patch plan at:

```text
reports/ops/qoder_skill_agent_orchestration_patch_plan_20260611.md
```

correctly identified C1 and C2 risks, but its recommended C1 Option A is not approved.

Do not implement the previous C1 Option A.

## Required Reading

Read these files before redesigning the patch:

```text
docs/STATE_VIEWPOINT_AGENT_CONTRACT.md
..\P107_STATE_HEX_ENCODING_RULES_20260517.md
..\hermass_state_mt5_package\state_encoding_table.md
..\hermass_state_mt5_package\common_mistakes.md
python\ai_engine\d1_risk_officer.py
python\ai_engine\pivot_contraction.py
reports\ops\qoder_skill_agent_orchestration_patch_plan_20260611.md
docs\HERMASS_SKILL_AGENT_ORCHESTRATION_DECISION_AND_PROMPTS_20260611.md
```

## Critical Review Decision

### C1 Previous Option A Is Rejected

Do not apply this logic:

```text
0-7 => neutral
8-15 => long
negative => short
```

Reason:

1. It still treats naked numeric State Hex values as trade direction.
2. `8` and `9` are not long direction. `8` is only non-contraction/expansion base without trend, position, or volatility trigger.
3. Even `E/F` are state component codes, not standalone trade permission.
4. Current implementation also does not correctly parse `A-F` through `int(...)`, so the previous analysis overstated current behavior for hex letters.

## New C1 Design Requirement

Redesign `D1RiskOfficer.direction_from_hex()` with this principle:

```text
Naked State Hex must not imply long/short.
Direction must come from explicit direction markers or a separate D1 Risk Direction field.
```

Do not create a manual mapping table from State Hex to trade direction at this stage.

Project policy:

```text
State Hex -> direction mapping is not a hand-written rule.
State Hex is retained as a feature/evidence field.
Directional value must be summarized later through large-sample statistics,
walk-forward validation, symbol segmentation, and regime-specific performance.
```

For now, raw/naked State Hex values should be treated as `neutral` by the risk gate unless an explicit independent direction field is provided.

Required behavior:

| Input | Expected Direction | Reason |
|---|---|---|
| `""` | neutral | missing |
| `0` | neutral | neutral alias |
| `-0` | neutral | neutral alias |
| `1`..`9` | neutral | naked State Hex |
| `A`..`F` | neutral | naked State Hex |
| `-1`..`-9` | neutral or short only if legacy policy is explicitly justified | do not infer without decision |
| `-A`..`-F` | neutral or short only if legacy policy is explicitly justified | do not infer without decision |
| `+F` | long | explicit plus direction marker |
| `-F` | short only if preserving signed legacy direction is explicitly chosen and documented |
| `BUY`, `LONG`, `UP`, `BULL` | long | explicit text direction |
| `SELL`, `SHORT`, `DOWN`, `BEAR` | short | explicit text direction |
| `N/A`, `NULL`, `N`, `=` | neutral | explicit neutral |

Important:

- Do not recommend a permanent hand-written mapping such as `E/F => long` or `-E/-F => short`.
- If any legacy signed-hex compatibility is discussed, it must be behind an explicit opt-in legacy flag and default to disabled.
- Direction should come from `d1_risk_direction`, MA structure, or another explicitly named direction field, not raw State Hex.
- Prefer adding a new explicit field or method for D1 risk direction if current callers pass raw `d1_hex` where they should pass `d1_risk_direction`.

## New C2 Design Requirement

`pivot_contraction.py` must not expose ungated SQX/Pivot output as a final trade signal.

Redesign around two concepts:

```text
candidate_signal = raw SQX/Pivot evidence output
gated_signal     = candidate signal after D1 Risk Officer approval
```

Required behavior:

1. Without `d1_hex` or explicit D1 risk direction:
   - output must be clearly marked as `candidate` or `observation`;
   - avoid final execution labels such as final `BUY`/`SELL`;
   - do not imply it is trade permission.
2. With `d1_hex` or explicit D1 risk direction:
   - call `D1RiskOfficer.assess(...)`;
   - if blocked, return `HOLD`, confidence `0.0`, and a reason containing `blocked_by_d1_risk_officer`;
   - if allowed, return a clearly marked gated signal.
3. SQX/Pivot evidence must remain an evidence module and cannot bypass D1 gate.

## Deliverable

Produce a revised patch plan report at:

```text
reports/ops/qoder_c1_c2_redesign_patch_plan_20260611.md
```

The report must include:

```text
# QODER C1/C2 Redesign Patch Plan

## Summary
- C1 previous Option A status: rejected
- New recommended C1 design:
- New recommended C2 design:
- Behavior-changing patches requiring approval:

## C1 Redesign
| Input | Current Output | Proposed Output | Rationale | Migration Risk |

## C2 Redesign
| Scenario | Candidate Output | Gated Output | Rationale |

## Recommended Patch
- Files:
- Function signatures:
- Compatibility strategy:
- Risk:

## Test Plan
- D1RiskOfficer tests:
- pivot_contraction candidate/gated tests:
- Regression tests:

## Approval Request
- C1 behavior change:
- C2 behavior change:
- Test creation:
```

## Hard Restrictions

- Do not modify code in this pass unless explicitly asked.
- Do not create tests that lock in the rejected C1 Option A.
- Do not place trades.
- Do not call MT5 order APIs.
- Do not register scheduled tasks.
- Do not run D1 full rebuild.
- Do not use n8n/Coze/Agently for trading decisions.

## Acceptance Criteria

The revised patch plan is acceptable only if:

1. It does not claim `8-15 => long`.
2. It explicitly states that naked State Hex is not trade direction.
3. It separates raw SQX/Pivot candidate output from D1-gated trading output.
4. It identifies all behavior-changing patches that require user approval.
5. It includes a test plan that matches the revised semantics.
6. It does not invent a State Hex directional mapping table; mapping must be deferred to future large-sample validation.
