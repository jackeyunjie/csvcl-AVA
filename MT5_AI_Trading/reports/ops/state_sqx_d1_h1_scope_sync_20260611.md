# State/SQX D1-H1 Scope Sync

Date: 2026-06-11
Status: Sync note for agents and Obsidian

## Decision

Current State/SQX validation scope is **D1 viewpoint + H1 viewpoint only**.

M15 is not deleted and not abandoned, but it is excluded from current data update, validation, and reporting tasks. M15 remains a future real-time/short-term observation branch.

## Operational Rules

1. Do not run `update-m15` in the current phase.
2. Do not require M15 coverage tables in current readiness reports.
3. Do not include M15 in current State/SQX validation acceptance criteria.
4. Do not hand-write State Hex -> long/short mapping rules.
5. Treat State Hex as feature/evidence.
6. Use D1/H1 data first to validate State/SQX statistical value.
7. No live trading, no MT5 order API calls, no scheduled trading tasks, no D1 full rebuild.

## Updated Files

| File | Change |
|---|---|
| `docs/STATE_SQX_VALIDATION_PRD_20260611.md` | Scope changed to D1/H1; M15 removed from required validation |
| `docs/STATE_SQX_VALIDATION_TECH_SPEC_20260611.md` | M15 update commands removed |
| `docs/QODER_STATE_SQX_VALIDATION_EXECUTION_PROMPT_20260611.md` | QODER execution narrowed to D1/H1 |
| `docs/AGENTS.md` | Added 2026-06-11 D1/H1 validation mainline section |

## QODER Next Task

Execute Phase 0 readiness from:

```text
docs/QODER_STATE_SQX_VALIDATION_EXECUTION_PROMPT_20260611.md
```

Expected report:

```text
reports/ops/qoder_state_sqx_validation_readiness_20260611.md
```

The report must explicitly confirm:

- no M15 update was run,
- no code changes were made,
- no State Hex direction mapping was written,
- no trading or MT5 order API was called.
