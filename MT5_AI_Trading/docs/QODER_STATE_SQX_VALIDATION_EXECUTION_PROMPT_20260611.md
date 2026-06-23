# QODER Prompt: Execute State/SQX Validation Readiness

Date: 2026-06-11
Status: QODER execution prompt

## Objective

Execute Phase 0 readiness and prepare Phase 1-3 validation tasks for State/SQX.

The current goal is to validate D1/H1 data readiness and define execution evidence. M15 is excluded from current data update, validation, and reporting tasks. Do not modify trading logic. Do not create a manual State Hex -> direction mapping.

## Workspace

```text
D:\qoder\csvcl - AVA\MT5_AI_Trading
```

## Required Reading

Read completely:

```text
docs/STATE_VIEWPOINT_AGENT_CONTRACT.md
docs/STATE_SQX_VALIDATION_PRD_20260611.md
docs/STATE_SQX_VALIDATION_TECH_SPEC_20260611.md
docs/HERMASS_MT5_STATE_RUNBOOK_20260609.md
hermass_state_ops.py
```

## Hard Restrictions

1. Do not place trades.
2. Do not call MT5 order APIs.
3. Do not register scheduled tasks.
4. Do not run D1 full rebuild.
5. Do not modify trading behavior.
6. Do not write State Hex -> direction mapping rules.
7. Do not introduce vectorbt, Streamlit, or MLflow in this phase.

## Phase 0: Readiness Execution

Run:

```powershell
python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --report
```

Then inspect existing D1/H1 data coverage:

```powershell
python -c "import duckdb; p='data/h1_state.duckdb'; c=duckdb.connect(p, read_only=True); print(c.execute(\"select table_name from information_schema.tables where table_schema='main'\").fetchall()); c.close()"
```

If table names are known, report per-symbol coverage:

```text
symbol, earliest timestamp, latest timestamp, row count
```

If table names differ, discover them and report exact schema.

## Phase 1 Plan: Data Expansion

Do not run expansion until Phase 0 report is written, unless the user explicitly asks.

Prepare commands:

```powershell
python hermass_state_ops.py update-h1 --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 180 --report
```

Fallback:

```powershell
python hermass_state_ops.py update-h1 --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 120 --report
```

Do not run M15 update in this phase.

## Phase 2-3 Plan

Inventory existing scripts and reports:

```powershell
rg -n "StateHexBacktestEngine|walk_forward|strategy_mining|squeeze|contraction|RSIOMA|ACD|Kaufman|pivot|forward_return|heatmap" .
```

Report which existing scripts should be reused and which new analysis-only scripts may be needed.

## Output Report

Write:

```text
reports/ops/qoder_state_sqx_validation_readiness_20260611.md
```

Required format:

```text
# QODER State/SQX Validation Readiness Report

## Summary
- Readiness status:
- Check command:
- Code changed: no
- Trading action: no
- D1 rebuild: no

## Freshness
| Symbol | Raw D1 | DB D1 | Raw H1 | DB H1 | Status |

## H1 Coverage
| Symbol | Earliest | Latest | Rows | Notes |

## Existing Validation Assets
| Asset | Purpose | Reuse Decision |

## Gaps
| Severity | Gap | Evidence | Proposed Next Action |

## Phase 1 Data Expansion Plan
| Command | Target | Fallback | Risk |

## Phase 2 Statistical Validation Plan
| Dataset | Grouping Keys | Horizons | Output |

## Phase 3 Backtest Plan
| Existing Script | Required Extension | Output |

## Safety Confirmation
- [ ] No code changes.
- [ ] No State Hex direction mapping.
- [ ] No trade placed.
- [ ] No MT5 order API call.
- [ ] No scheduled task registration.
- [ ] No D1 full rebuild.
```

## Acceptance Criteria

1. Report exists at the required path.
2. D1/H1 data freshness and coverage are reported or exact blockers are documented.
3. Existing validation assets are inventoried.
4. Phase 1-3 plan is concrete enough for execution.
5. No behavior-changing code modification is made.
