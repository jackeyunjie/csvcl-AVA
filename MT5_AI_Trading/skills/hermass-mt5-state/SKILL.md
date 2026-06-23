---
name: hermass-mt5-state
description: Operate the Hermass/MT5 state data pipeline for D1, H1, and M15 viewpoint agents. Use when updating MT5/AvaTrade data, checking DuckDB freshness, generating LLM-ready state reports, planning Windows scheduled tasks, writing reports to the MT5AVATRADE Obsidian vault, or coordinating KIMI/qoder execution around Hermass state data.
---

# Hermass MT5 State

Use this skill to work on the local project at `D:\qoder\csvcl - AVA\MT5_AI_Trading`.

## Contract

Read `docs/STATE_VIEWPOINT_AGENT_CONTRACT.md` before changing state logic. D1, H1, and M15 are separate viewpoint agents:

- D1 uses D1 timestamps and D1 close.
- H1 uses H1 timestamps and H1 close for every structure timeframe position.
- M15 uses M15 timestamps and M15 close for every structure timeframe position.

Never treat native `D1@D1`, `H1@H1`, and `M15@M15` as interchangeable columns in one lower-timeframe table.

## Safe Entry Points

Prefer the unified operations script:

```powershell
cd "D:\qoder\csvcl - AVA\MT5_AI_Trading"
python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY --report
python hermass_state_ops.py update-h1 --symbols EURUSD GBPUSD USDJPY --days 120 --report
python hermass_state_ops.py update-m15 --symbols EURUSD --days 30 --report
python hermass_state_ops.py plan-schedule --symbols EURUSD GBPUSD USDJPY
```

Reports are written to `reports/ops/` and, by default, to the detected Obsidian vault `D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\`.

`--report` also writes local table outputs for scan/review:

- `reports/ops/tables/hermass_state_table_YYYYMMDD_HHMMSS.csv`
- `reports/ops/tables/hermass_state_table_YYYYMMDD_HHMMSS.md`

The table is one row per symbol and preserves the D1-first order: D1 MA144/169/200, D1 State Hex/risk direction, H1/M15 indicators, contraction metrics, and freshness status.

Optional Feishu/Lark sync appends the same table rows to an existing sheet:

```powershell
python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY --report --sync-lark --lark-spreadsheet-token "<sht...>" --lark-sheet-id "<sheet_id>"
```

Use `C:\Users\MECHREVO\AppData\Roaming\npm\lark-cli.cmd` for sync. Do not call the `.ps1` shim directly from PowerShell. Sync failures are report/notification failures only; local MT5 data freshness remains the source of truth.

## D1-First Analysis Order

Every per-symbol report must start from D1:

1. D1 MA144/MA169/MA200 structure and close-vs-MA location.
2. D1 State Hex and D1 risk direction.
3. H1 indicators only after D1 context is known.
4. M15 indicators only after D1 context is known.

D1 is the risk officer. H1 and M15 may observe any setup, but directional trades must align with D1. If D1 is `0`, `N/A`, unknown, or neutral, lower-timeframe directional trades are observe-only.

## Contraction Watch

Use the existing squeeze/contraction block instead of inventing a new one:

- Project modules: `python.analytics.squeeze_observer.SqueezeObserver` and `python.ai_engine.pivot_contraction.detect_contraction`.
- SQX references: `D:\SQX136\custom_indicators\MetaTrader5\Indicators\SqSRPercentRank.mq5` and `SqPivots.mq5`.
- Required report fields: multi-timeframe SR contraction, 1D/3D/6D pivot contraction, multi-timeframe Bollinger Band width contraction, and ADX contraction tiers `<20`, `<13`, `<9`.

Treat these as observation and LLM-reporting metrics. Do not convert them into live trading unless the user separately approves a trading rule.

When the user mentions ACD, Kaufman, RSIOMA, or the local indicator pack, read `references/MT5_ACD_KAUFMAN_INDICATORS.md`. The required local MT5 indicators are:

- `D:\qoder\csvcl - AVA\MT5\Indicators\RSIOMA_v2HHLSX.mq5`
- `D:\qoder\csvcl - AVA\MT5\Indicators\Kaufman_Bands.mq5`
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_Kaufman_Bandwidth616.mq5`
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_枢轴.mq5`
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_6.mq5`
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_3.mq5`
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_2.mq5`
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_1.mq5`

## D1 Full Rebuild Guard

`build_hermass_state.py` rebuilds `data/hermass_state.db`. Do not run it from automation unless the user confirms a full rebuild.

Use:

```powershell
python hermass_state_ops.py rebuild-d1 --confirm-full-rebuild --report
```

If the user only asks for routine updates, run `check`, `update-h1`, or `update-m15` instead.

Before D1 rebuild, ensure a backup exists under `data/backups/`. The builder now writes a temporary DB and replaces the target only after a successful build.

## H1/M15 Checks

Always compare two clocks after an update:

- MT5 raw latest bars from Python API.
- DuckDB latest timestamps in `data/h1_state.duckdb` or `data/m15_state.duckdb`.

If MT5 raw bars are newer than DuckDB, report the mismatch instead of saying the update is complete.

For `check`, compare against the current MT5 raw latest bars at check time. For `update-h1`, `update-m15`, and `rebuild-d1`, use the report's `Acceptance` section: the target raw bars are captured before the command starts, so a long M15 run can be accepted even if a new bar appears before the final report is written.

Scheduled tasks should call the wrapper scripts in `scripts/`, not long inline Python commands:

- `scripts/hermass_update_h1.cmd`
- `scripts/hermass_update_m15.cmd`
- `scripts/hermass_rebuild_d1.cmd`

The wrappers set the project directory, write logs to `logs/tasks/`, and use lock files in `locks/` to prevent reentry.

Register scheduled tasks with `scripts/register_hermass_tasks.ps1`. It should register only H1 and M15 by default. D1 rebuild must be explicit and disabled/on-demand because it rewrites `data/hermass_state.db`.

## Delegation

Use `references/KIMI_QODER_PROMPTS.md` when assigning tasks to KIMI or qoder. KIMI should focus on data expansion, data-quality notes, and independent research writeups. qoder should focus on script fixes, test runs, task scheduling drafts, and acceptance evidence.
