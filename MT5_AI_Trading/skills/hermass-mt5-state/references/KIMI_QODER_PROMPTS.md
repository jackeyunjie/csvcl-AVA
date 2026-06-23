# KIMI / qoder Prompts

Latest commander-level summary and delegation pack:

- `docs/HERMASS_RECENT_WORK_SUMMARY_AND_DELEGATION_20260610.md`
- `docs/HERMASS_NEXT_KIMI_QODER_PROMPTS_20260610.md`

Current decision: local CSV/Markdown tables are sufficient for this phase. Feishu/Lark sync is optional and must not block local report/table acceptance.

## KIMI Prompt

You are responsible for independent data expansion and research validation for the Hermass MT5 state pipeline.

Workspace:

```text
D:\qoder\csvcl - AVA\MT5_AI_Trading
```

Required reading:

- `docs/STATE_VIEWPOINT_AGENT_CONTRACT.md`
- `hermass_state_ops.py`
- `docs/HERMASS_MT5_STATE_RUNBOOK_20260609.md`
- `skills/hermass-mt5-state/references/MT5_ACD_KAUFMAN_INDICATORS.md`

Tasks:

1. Run a read-only freshness check:
   ```powershell
   python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --report
   ```
2. Compare MT5 raw latest bars with DuckDB latest timestamps for D1/H1/M15.
3. Review the Contraction Watch section. It must include:
   - per-symbol D1-first order: D1 MA144/169/200, D1 State Hex/risk direction, then H1/M15 indicators,
   - multi-timeframe SR support/resistance contraction,
   - 1D/3D/6D pivot contraction,
   - multi-timeframe Bollinger Band width contraction,
   - ADX contraction tiers `<20`, `<13`, `<9`,
   - references to the project squeeze modules, SQX `SqSRPercentRank` / `SqPivots` blocks, and the local RSIOMA/Kaufman/ACD indicator pack.
4. Do not place trades. Do not register scheduled tasks. Do not run D1 full rebuild unless explicitly approved.
5. Produce a concise report with:
   - connected MT5 account/server,
   - latest raw MT5 D1/H1/M15 bars,
   - latest DuckDB D1/H1/M15 state timestamps,
   - local table export path from `Table Exports`,
   - optional `Lark Sync` status if `--sync-lark` was used,
   - contraction-watch observations,
   - mismatches and proposed next action.

Acceptance:

- The report distinguishes raw MT5 freshness from state DB freshness.
- The local CSV/Markdown table exists under `reports/ops/tables/` when `--report` is used.
- Each symbol starts with D1 MA144/169/200 and D1 State Hex before H1/M15 analysis.
- For update actions, distinguish `fresh_at_start` from `fresh_as_of_finish`; M15/H1 rollover during a long run is a special status, not automatically a broken pipeline.
- Any failure includes command, error, and next action.
- SQX/MT5 EA work must stay DSL/observer-only until the user separately approves paper/live execution.
- External orchestration via n8n/Coze/Dify/Agently/agentmemory must stay report-only and cannot call broker or MT5 order APIs.

## qoder Prompt

You are responsible for implementation and acceptance checks for the Hermass MT5 state pipeline.

Workspace:

```text
D:\qoder\csvcl - AVA\MT5_AI_Trading
```

Tasks:

1. Verify the unified operations script:
   ```powershell
   python hermass_state_ops.py check --symbols EURUSD --report
   python hermass_state_ops.py update-h1 --symbols EURUSD --days 120 --report
   python hermass_state_ops.py update-m15 --symbols EURUSD --days 30 --report
   ```
2. Verify `data/m15_state.duckdb` has SR levels after M15 update:
   ```powershell
   python -c "import duckdb; c=duckdb.connect('data/m15_state.duckdb'); print(c.execute('select count(*) from m15_sr_levels').fetchone()); c.close()"
   ```
3. Draft, but do not register, Windows Task Scheduler commands:
   ```powershell
   python hermass_state_ops.py plan-schedule --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --output docs/HERMASS_TASKS_PLAN_20260609.md
   ```
4. Verify scheduled tasks use wrapper scripts under `scripts/`, with logs in `logs/tasks/` and locks in `locks/`.
5. Validate the local MT5 indicator pack buffer map:
   - `RSIOMA_v2HHLSX.mq5`
   - `Kaufman_Bands.mq5`
   - `ACD_Kaufman_Bandwidth616.mq5`
   - `ACD_枢轴.mq5`
   - `ACD_6.mq5`
   - `ACD_3.mq5`
   - `ACD_2.mq5`
   - `ACD_1.mq5`
6. Verify D1 rebuild creates a pre-rebuild backup and uses the guarded `--confirm-full-rebuild` path.
7. Write acceptance notes into the Obsidian vault through `--report`, not by manually editing outside the workspace unless explicitly approved.
8. If asked to sync Feishu/Lark, use the script flags instead of a separate exporter:
   ```powershell
   python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY --report --sync-lark --lark-spreadsheet-token "<sht...>" --lark-sheet-id "<sheet_id>"
   ```
   Use `C:\Users\MECHREVO\AppData\Roaming\npm\lark-cli.cmd` and default `--lark-as user`.

Acceptance:

- H1 and M15 commands exit 0 or explain why not.
- If command execution succeeds but freshness or acceptance fails, the operation command must return non-zero so Windows Task Scheduler can see the failure.
- The latest DB timestamps after update are reported.
- The generated report includes `D1 First Symbol Analysis`.
- The generated report includes `Table Exports`, and optional `Lark Sync` if enabled.
- D1 full rebuild remains guarded by `--confirm-full-rebuild` and must not be registered as an enabled daily destructive task by default.
- Contraction Watch uses the existing squeeze/SQX references and remains observation-only.
