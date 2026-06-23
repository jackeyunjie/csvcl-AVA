# Hermass Skill/Agent Orchestration Decision and KIMI/qoder Prompts

Date: 2026-06-11
Status: Architecture decision / delegation prompt

## Decision

Use **Skill + local Agents** as the core governance and decision layer. Use **n8n / Coze / Agently only as peripheral orchestration, reporting, notification, and human-confirmation tools**.

Do not put n8n, Coze, Agently, or any external orchestration layer inside the trading decision path until the State/SQX semantics, D1 Risk Officer gate, backtest evidence, and paper-trading controls are stable.

## Architecture Boundary

```text
Core decision layer:
  Python modules + State Viewpoint Agents + SQX indicator modules

Governance layer:
  Codex/KIMI/qoder skills + audit prompts + acceptance reports

Orchestration layer:
  Windows Task Scheduler / n8n

Collaboration and presentation layer:
  Obsidian / GitHub Issues / Coze / Feishu
```

## Non-Negotiable Rules

1. `State Hex` is a viewpoint state health code, not a linear score and not standalone trade permission.
2. D1/H1/M15 are independent viewpoint Agents:
   - D1 uses D1 timestamp and D1 close.
   - H1 uses H1 timestamp and H1 close for every structure timeframe position.
   - M15 uses M15 timestamp and M15 close for every structure timeframe position.
3. D1 Risk Officer is the hard direction gate. Lower timeframe signals and SQX evidence cannot bypass it.
4. SQX modules provide strategy evidence only: ACD, Pivot, Kaufman Bands, RSIOMA, SR PercentRank, ADX, BB Width, contraction, breakout.
5. Contraction Watch remains observer/reporting-only unless the user separately approves a trading rule.
6. No tool may place trades, call MT5 order APIs, register live execution tasks, or trigger broker actions without explicit user approval.
7. D1 full rebuild remains guarded and must not be automated by default.

## Tool Choice

| Tool | Use | Boundary |
|---|---|---|
| Skill | Encode project rules, audit contracts, safe entry points, acceptance criteria | Required for all State/SQX work |
| Local Agent | D1/H1/M15/Resonance structured analysis and reports | May score and explain, must not place trades |
| qoder | Implementation audit, patches, tests, acceptance evidence | Must not silently change trading behavior |
| KIMI | Independent research validation, data notes, semantic review | Must not change code or execute trades |
| n8n | Scheduled report orchestration, notifications, GitHub Issue creation | Report-only; no broker/MT5 order APIs |
| Coze | Conversational query/report assistant and human confirmation UI | Report-only; no strategy execution |
| Agently | Experimental multi-agent orchestration | Research-only until separately approved |
| GitHub Projects | Issue/Milestone/decision tracking | Recommended for project management |

## Recommended Project Management Tracks

Use GitHub private repository + GitHub Projects after repository cleanup. Suggested tracks:

| Track | Scope |
|---|---|
| P0 State/SQX Semantics | State Hex contract, viewpoint contract, D1 Risk Officer, SQX boundary |
| P0 Safety Gate | No silent trading behavior changes, no live execution, kill-switch design |
| P1 Data Freshness | D1/H1/M15 raw MT5 vs DuckDB freshness, scheduled checks |
| P1 Strategy Evidence | SQX indicator evidence, scoring formulas, walk-forward validation |
| P2 Automation | Windows Task Scheduler, n8n report flow, GitHub Issue automation |
| P2 Documentation | Architecture docs, audit reports, Obsidian reports |
| P3 UI/ChatOps | Coze/Feishu reporting assistant, human confirmation workflows |

## KIMI Prompt

You are responsible for independent research validation and semantic review for the Hermass MT5 State/SQX project.

Workspace:

```text
D:\qoder\csvcl - AVA\MT5_AI_Trading
```

Required reading:

```text
docs/STATE_VIEWPOINT_AGENT_CONTRACT.md
..\P107_STATE_HEX_ENCODING_RULES_20260517.md
..\hermass_state_mt5_package\state_encoding_table.md
..\hermass_state_mt5_package\common_mistakes.md
docs\MULTI_TIMEFREME_RESONANCE_FRAMEWORK.md
docs\QODER_STATE_SQX_CONSISTENCY_AUDIT_PROMPT_20260611.md
reports\ops\qoder_state_sqx_consistency_audit_20260611.md
```

Task:

1. Independently review whether the current architecture decision is correct:
   - Skill + local Agents as core governance and decision layer.
   - n8n / Coze / Agently as peripheral report-only orchestration.
2. Validate that the following rules are consistently stated:
   - State Hex is not a linear strength score.
   - State Hex is not standalone trade permission.
   - `D1=8` must not mean strong bullish.
   - D1/H1/M15 viewpoint Agents must not be mixed.
   - SQX modules must not bypass D1 Risk Officer.
3. Review QODER audit conclusions, especially:
   - C1: `D1RiskOfficer.direction_from_hex()` raw numeric mapping risk.
   - C2: `pivot_contraction.py` direct BUY/SELL signal risk.
4. Propose a research-safe rollout plan:
   - documentation cleanup,
   - code-risk review,
   - backtest/walk-forward validation,
   - paper-trading only after explicit approval,
   - no live trading.
5. Produce a concise report at:

```text
reports/ops/kimi_skill_agent_orchestration_review_20260611.md
```

Hard restrictions:

- Do not modify code.
- Do not place trades.
- Do not call MT5 order APIs.
- Do not register scheduled tasks.
- Do not run D1 full rebuild.
- Do not recommend n8n/Coze/Agently inside the trading decision path.

Acceptance:

- The report clearly separates decision-layer, governance-layer, orchestration-layer, and presentation-layer responsibilities.
- The report explicitly states whether C1/C2 should be fixed before any automation expansion.
- Any disagreement must cite specific file paths and line-level evidence.

## qoder Prompt

You are responsible for implementation audit, patch planning, and acceptance evidence for the Hermass MT5 State/SQX project.

Workspace:

```text
D:\qoder\csvcl - AVA\MT5_AI_Trading
```

Required reading:

```text
docs/STATE_VIEWPOINT_AGENT_CONTRACT.md
..\P107_STATE_HEX_ENCODING_RULES_20260517.md
..\hermass_state_mt5_package\state_encoding_table.md
..\hermass_state_mt5_package\common_mistakes.md
python\ai_engine\d1_risk_officer.py
python\ai_engine\pivot_contraction.py
docs\QODER_STATE_SQX_CONSISTENCY_AUDIT_PROMPT_20260611.md
reports\ops\qoder_state_sqx_consistency_audit_20260611.md
docs\HERMASS_SKILL_AGENT_ORCHESTRATION_DECISION_AND_PROMPTS_20260611.md
```

Task:

1. Verify the reported C1/C2 issues with exact file and line evidence:
   - C1: raw numeric `state_hex` mapping in `D1RiskOfficer.direction_from_hex()`.
   - C2: `pivot_contraction.py` returning direct BUY/SELL style output without D1 Risk Officer gate.
2. Prepare patch options, but do not silently change trading behavior:
   - Option A: conservative report-only guard comments and tests.
   - Option B: code patch that changes behavior, clearly marked as requiring user approval.
3. Create or update tests that demonstrate the intended behavior. If behavior changes require approval, write tests as proposed acceptance tests and do not force them into the current suite unless approved.
4. Verify that SQX indicators remain evidence modules:
   - ACD,
   - Pivot,
   - Kaufman Bands,
   - RSIOMA,
   - SR PercentRank,
   - ADX,
   - BB Width,
   - contraction/breakout.
5. Verify that n8n/Coze/Agently are documented as report-only until explicit approval.
6. Produce an implementation report at:

```text
reports/ops/qoder_skill_agent_orchestration_patch_plan_20260611.md
```

Hard restrictions:

- Do not place trades.
- Do not call MT5 order APIs.
- Do not register scheduled tasks.
- Do not run D1 full rebuild.
- Do not make behavior-changing patches unless the user explicitly approves.
- Do not use n8n/Coze/Agently to trigger trading decisions.

Acceptance:

- The report includes exact file/line evidence for C1/C2.
- The report provides patch diffs or clear patch plans for C1/C2.
- The report distinguishes documentation-only changes from behavior-changing code changes.
- The report includes a test plan.
- The report confirms no live execution path was touched.

## GitHub Project Prompt

If GitHub project management is approved, create issues only after repository cleanup and private GitHub repository creation.

Initial issue set:

```text
P0: Fix State Hex semantic misuse in docs
P0: Review D1RiskOfficer direction_from_hex numeric mapping
P0: Gate pivot_contraction signals through D1 Risk Officer
P0: Add State/SQX no-live-trading safety contract
P1: Define resonance scoring formula with D1/H1/M15/SQX weights
P1: Add tests for State Hex viewpoint semantics
P1: Add walk-forward validation for SQX evidence scoring
P2: Build n8n report-only workflow for freshness and audit reports
P2: Build Coze report-query assistant with no execution permissions
```

Do not push secrets, `.venv`, `.npm-cache`, DuckDB/SQLite databases, logs, zip archives, broker configs, or trading records to GitHub.
