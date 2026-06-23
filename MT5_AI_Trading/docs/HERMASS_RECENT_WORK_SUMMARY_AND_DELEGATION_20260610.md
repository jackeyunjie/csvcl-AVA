# Hermass Recent Work Summary And Delegation Prompts

Date: 2026-06-10

## Commander Decision

Local tables are enough for the current phase. Feishu/Lark sync is optional and must not block local MT5 data checks, report generation, table output, Obsidian writing, or scheduled-task acceptance.

The current source of truth is local:

- Project: `D:\qoder\csvcl - AVA\MT5_AI_Trading`
- Main script: `hermass_state_ops.py`
- Run reports: `reports/ops/`
- Local tables: `reports/ops/tables/`
- Obsidian reports: `D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports`
- Obsidian tables: `D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Tables`

Feishu/Lark policy:

- Do not require Feishu for daily operation.
- Do not treat Feishu failure as data failure.
- Only use `--sync-lark` when a spreadsheet token or URL and sheet target are explicitly provided.

## Recent Work Summary

Implemented in `hermass_state_ops.py`:

- D1-first report flow: each symbol starts from D1 MA144/169/200, then D1 State Hex/risk direction, then H1 and M15.
- D1 risk officer remains the hard gate: H1/M15 directional ideas cannot violate D1 direction; neutral/unknown D1 is observe-only.
- Legacy composite State Hex compatibility: `B+H` and `A+M` are long, `D-H` and `E-M` are short, `C=M` is neutral.
- Contraction watch references the existing squeeze/SQX block and the local RSIOMA/Kaufman/ACD indicator pack.
- `--report` now generates local CSV and Markdown tables under `reports/ops/tables/`.
- Optional Feishu/Lark append exists, but local tables remain authoritative.

Latest verified local table example:

- `reports/ops/tables/hermass_state_table_20260610_102149.csv`
- `reports/ops/tables/hermass_state_table_20260610_102149.md`
- Obsidian copy: `D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Tables\hermass_state_table_20260610_102149.csv`

Latest example report:

- `reports/ops/hermass_state_ops_20260610_102149.md`
- Obsidian copy: `D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260610_102149.md`

Latest example status:

- Command: `python hermass_state_ops.py check --symbols EURUSD --report --no-contraction --sync-lark --lark-dry-run`
- Result: report/table output succeeded.
- Overall check status: failed because EURUSD DuckDB D1/H1/M15 timestamps were stale versus MT5 raw bars.
- Feishu/Lark status: missing target, expected because no spreadsheet token or URL was provided.

Verification already run:

- `python -m pytest tests/test_d1_risk_officer.py tests/test_run_live_d1_gate.py tests/test_hermass_state_ops_d1_first.py -q` -> 13 passed.
- `python -m pytest tests/test_imports.py -q` -> passed with an existing pytest warning.
- Compile check on `hermass_state_ops.py`, `python/ai_engine/d1_risk_officer.py`, and `run_live.py` -> compile-ok 3.
- `lark-cli.cmd sheets +append --help` confirmed append parameters, but Feishu is optional.

## Acceptance Gates

Any delegated work must preserve these gates:

- No live trading, no order routing, no MT5 order API calls.
- D1 full rebuild is guarded by `--confirm-full-rebuild`.
- H1 and M15 scheduled tasks may be routine; D1 rebuild must not be enabled as a daily destructive task by default.
- A run is not accepted unless the local Markdown report and local CSV/Markdown table are produced.
- If freshness fails, say which timeframe and timestamp is stale; do not hide it behind successful file output.
- If Feishu is absent or fails, mark it as optional and continue using local tables.

## KIMI Prompt

You are KIMI, responsible for independent research validation and data-quality review for the Hermass MT5 state pipeline.

Workspace:

```text
D:\qoder\csvcl - AVA\MT5_AI_Trading
```

Required reading:

- `docs/STATE_VIEWPOINT_AGENT_CONTRACT.md`
- `docs/HERMASS_MT5_STATE_RUNBOOK_20260609.md`
- `docs/HERMASS_AGENT_WORKFLOW_ORCHESTRATION_20260609.md`
- `docs/HERMASS_RECENT_WORK_SUMMARY_AND_DELEGATION_20260610.md`
- `skills/hermass-mt5-state/references/MT5_ACD_KAUFMAN_INDICATORS.md`
- Latest file under `reports/ops/`
- Latest file under `reports/ops/tables/`

Your task:

1. Review the latest local table and report. Treat local table output as sufficient; Feishu is optional.
2. Confirm each symbol follows D1-first order:
   - D1 MA144/169/200 and close-vs-MA location,
   - D1 State Hex and D1 risk direction,
   - H1 indicators after D1,
   - M15 indicators after D1.
3. Review freshness mismatches:
   - compare raw MT5 D1/H1/M15 latest bars,
   - compare DuckDB D1/H1/M15 latest timestamps,
   - list stale symbols and exact stale timeframes.
4. Review contraction observations:
   - multi-timeframe SR contraction,
   - 1D/3D/6D pivot contraction,
   - Bollinger bandwidth contraction,
   - ADX tiers `<20`, `<13`, `<9`,
   - RSIOMA/Kaufman/ACD pack references.
5. Identify research risks:
   - lookahead,
   - timeframe leakage,
   - state-hex interpretation errors,
   - overfitting risk if SQX/EA rules are generated later.
6. Do not register scheduled tasks, rebuild D1, write Feishu, place trades, or edit code.

KIMI output format:

```markdown
# KIMI Review

## Evidence
- Latest report:
- Latest table:
- MT5 raw latest:
- DuckDB latest:

## D1-First Check
- Pass/fail:
- Notes:

## Freshness Gaps
| symbol | timeframe | raw_latest | db_latest | status | required action |
|---|---|---|---|---|---|

## Contraction Review
- SR:
- Pivot 1D/3D/6D:
- Bollinger bandwidth:
- ADX tier:
- RSIOMA/Kaufman/ACD reference:

## Risks
- 

## Recommendation
- Observe only / update H1 / update M15 / guarded D1 rebuild review:
```

KIMI acceptance:

- Must cite local table path.
- Must explicitly say Feishu is optional.
- Must not propose live trading.
- Must separate data freshness failure from report/table output success.

## qoder Prompt

You are qoder, responsible for engineering verification, task-run evidence, and implementation hardening for the Hermass MT5 state pipeline.

Workspace:

```text
D:\qoder\csvcl - AVA\MT5_AI_Trading
```

Required reading:

- `hermass_state_ops.py`
- `python/ai_engine/d1_risk_officer.py`
- `docs/HERMASS_MT5_STATE_RUNBOOK_20260609.md`
- `docs/HERMASS_RECENT_WORK_SUMMARY_AND_DELEGATION_20260610.md`
- `skills/hermass-mt5-state/SKILL.md`
- `skills/hermass-mt5-state/references/KIMI_QODER_PROMPTS.md`

Your task:

1. Verify local table generation:
   ```powershell
   python hermass_state_ops.py check --symbols EURUSD --report --no-contraction
   ```
2. Confirm output files exist:
   - `reports/ops/hermass_state_ops_*.md`
   - `reports/ops/tables/hermass_state_table_*.csv`
   - `reports/ops/tables/hermass_state_table_*.md`
3. Verify table columns include:
   - `d1_close`, `ma144`, `ma169`, `ma200`,
   - `d1_risk_hex`, `d1_risk_direction`, `lower_tf_permission`,
   - `h1_hex`, `h1_adx_tier`,
   - `m15_hex`, `m15_sr_breakout`, `m15_adx_tier`,
   - freshness columns for D1/H1/M15.
4. Run test suite:
   ```powershell
   python -m pytest tests/test_d1_risk_officer.py tests/test_run_live_d1_gate.py tests/test_hermass_state_ops_d1_first.py -q
   python -m pytest tests/test_imports.py -q
   python -c "from pathlib import Path; files=['hermass_state_ops.py','python/ai_engine/d1_risk_officer.py','run_live.py']; [compile(Path(f).read_text(encoding='utf-8'), f, 'exec') for f in files]; print('compile-ok', len(files))"
   ```
5. Verify task scheduler plan, but do not register tasks unless the commander explicitly approves:
   ```powershell
   python hermass_state_ops.py plan-schedule --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --output docs/HERMASS_TASKS_PLAN_20260609.md
   ```
6. If asked about Feishu, verify only the optional path:
   ```powershell
   python hermass_state_ops.py check --symbols EURUSD --report --sync-lark --lark-dry-run
   ```
   Do not require Feishu token or sheet setup for acceptance.
7. Do not change strategy logic unless a failing test or documented acceptance gap requires it.

qoder output format:

```markdown
# qoder Engineering Verification

## Commands Run
| command | exit_code | result |
|---|---:|---|

## Generated Files
| file | exists | rows/notes |
|---|---|---|

## Table Schema Check
- Pass/fail:
- Missing columns:

## Freshness Result
| symbol | timeframe | raw_latest | db_latest | status |
|---|---|---|---|---|

## Tests
- D1 risk/gate/table tests:
- imports:
- compile:

## Scheduler Notes
- H1:
- M15:
- D1 rebuild guard:

## Risks And Next Engineering Action
-
```

qoder acceptance:

- Must treat local table output as required.
- Must treat Feishu as optional.
- Must keep D1 rebuild guarded.
- Must report stale data as stale even when file generation succeeds.

## Commander Follow-Up Queue

1. Decide whether to refresh H1 and M15 now to close the latest EURUSD stale gaps.
2. Register or re-run Windows scheduled tasks only after a fresh update run passes acceptance.
3. Keep Feishu disabled unless a specific spreadsheet target is provided.
4. Ask KIMI to review data quality and contraction logic before turning any observation into SQX/EA rules.
5. Ask qoder to verify table output and task wrappers before enabling unattended scheduling.

Latest next-task prompts:

- `docs/HERMASS_NEXT_KIMI_QODER_PROMPTS_20260610.md`
