# QODER Prompt: Data and Strategy-Set Accumulation

Date: 2026-06-11
Status: Execution prompt / no code-change phase

## Objective

Current phase is **data accumulation and strategy-set accumulation only**.

Do not modify trading logic. Do not summarize a manual State Hex -> direction mapping. Do not convert SQX evidence into live trading rules. The goal is to collect enough H1/M15/D1 viewpoint data and strategy evidence so later decisions can be made by large-sample statistics, walk-forward validation, symbol segmentation, and regime-specific performance.

## Workspace

```text
D:\qoder\csvcl - AVA\MT5_AI_Trading
```

## Required Reading

Read before execution:

```text
docs/STATE_VIEWPOINT_AGENT_CONTRACT.md
docs/HERMASS_MT5_STATE_RUNBOOK_20260609.md
docs/HERMASS_SKILL_AGENT_ORCHESTRATION_DECISION_AND_PROMPTS_20260611.md
docs/QODER_C1_C2_REDESIGN_PROMPT_20260611.md
hermass_state_ops.py
```

## Non-Negotiable Rules

1. No code changes in this task.
2. No trading, no MT5 order API calls, no broker actions.
3. No Windows scheduled task registration.
4. No D1 full rebuild unless the user separately approves it.
5. Do not write a hand-made State Hex -> long/short mapping.
6. Treat State Hex as a feature/evidence field.
7. Treat SQX indicators as evidence modules only.
8. Always compare MT5 raw latest bars with DuckDB latest timestamps after updates.

## Target Symbols

Use this initial symbol set unless a symbol fails because it is unavailable in the connected MT5 terminal:

```text
EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100
```

Optional expansion candidates, report-only unless already supported by the current scripts:

```text
SILVER USOIL BRENT_OIL GER30 JP225 HK_50 BTCUSD
```

## Execution Plan

### Step 1: Baseline Freshness Check

Run:

```powershell
python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --report
```

Record:

- connected MT5 account/server if available,
- latest MT5 raw D1/H1/M15 bars,
- latest DuckDB D1/H1/M15 timestamps,
- stale symbols/timeframes,
- failures and exact errors.

### Step 2: H1 Data Expansion

Run:

```powershell
python hermass_state_ops.py update-h1 --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 180 --report
```

If 180 days is too slow or fails because of MT5/history limits, retry with 120 days and record the reason.

### Step 3: M15 Data Expansion

Run:

```powershell
python hermass_state_ops.py update-m15 --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 60 --report
```

If 60 days is too slow or fails because of MT5/history limits, retry with 30 days and record the reason.

### Step 4: Post-Update Freshness Check

Run:

```powershell
python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --report
```

Compare post-update results against Step 1.

### Step 5: Strategy-Set Inventory, Report-Only

Do not invent new strategy rules. Inventory existing strategy evidence and datasets:

```powershell
rg -n "D1=|H1=|M15=|squeeze|contraction|RSIOMA|ACD|Pivot|Kaufman|walk_forward|strategy_mining|state_hex" .
```

Report:

- existing strategy mining reports,
- existing walk-forward scripts,
- current State/SQX evidence sources,
- missing datasets required for future large-sample validation.

## Output Report

Write the execution report to:

```text
reports/ops/qoder_data_strategyset_accumulation_20260611.md
```

Required structure:

```text
# QODER Data and Strategy-Set Accumulation Report

## Summary
- Commands executed:
- Symbols attempted:
- Symbols succeeded:
- Symbols failed:
- H1 target days:
- M15 target days:
- Code changed: no
- Trading action: no

## Baseline Freshness
| Symbol | Raw D1 | DB D1 | Raw H1 | DB H1 | Raw M15 | DB M15 | Status |

## Update Results
| Command | Exit Code | Duration | Report Path | Notes |

## Post-Update Freshness
| Symbol | Raw D1 | DB D1 | Raw H1 | DB H1 | Raw M15 | DB M15 | Status |

## Data Coverage
| Symbol | H1 Earliest | H1 Latest | H1 Rows | M15 Earliest | M15 Latest | M15 Rows |

## Strategy-Set Inventory
| Source | Type | Symbols/Patterns | Status | Notes |

## Issues
| Severity | Area | Issue | Evidence | Next Action |

## Next Data Tasks
- Suggested symbol expansion:
- Suggested history expansion:
- Suggested validation scripts:

## Safety Confirmation
- [ ] No code changes.
- [ ] No State Hex direction mapping was hand-written.
- [ ] No trade was placed.
- [ ] No MT5 order API was called.
- [ ] No scheduled task was registered.
- [ ] No D1 full rebuild was run.
```

## Acceptance Criteria

The task is complete only if:

1. The report exists at `reports/ops/qoder_data_strategyset_accumulation_20260611.md`.
2. Baseline and post-update freshness are both reported.
3. H1 and M15 coverage is reported by symbol.
4. Any failed command includes command, exit code, error summary, and next action.
5. The report does not create or recommend a manual State Hex -> direction mapping.
6. The report keeps SQX evidence separate from trade permission.
