# Hermass MT5 State Runbook

Date: 2026-06-09

## Current Path

- Project: `D:\qoder\csvcl - AVA\MT5_AI_Trading`
- Obsidian vault: `D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE`
- Unified script: `hermass_state_ops.py`
- Skill source: `skills/hermass-mt5-state/SKILL.md`

## Safe Commands

```powershell
cd "D:\qoder\csvcl - AVA\MT5_AI_Trading"
python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --report
python hermass_state_ops.py update-h1 --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 120 --report
python hermass_state_ops.py update-m15 --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 30 --report --no-contraction
```

`--report` now writes both the Markdown audit report and local table outputs:

- `reports/ops/hermass_state_ops_YYYYMMDD_HHMMSS.md`
- `reports/ops/tables/hermass_state_table_YYYYMMDD_HHMMSS.csv`
- `reports/ops/tables/hermass_state_table_YYYYMMDD_HHMMSS.md`

The table rows are one row per symbol. They include D1 MA144/169/200, D1 State Hex/risk direction, H1/M15 state and contraction fields, pivot contraction, and freshness timestamps.

## D1 / H1 / M15 Policy

- D1/Hermass full rebuild is a daily or manual operation, not an M15/H1 scheduled operation.
- H1 can run hourly after the update method is accepted.
- M15 can run every 15 minutes after the M15 save path is accepted.
- All automation must remain data/report only unless live trading is separately approved.
- Every symbol report starts with D1 MA144/MA169/MA200 structure, then D1 State Hex/risk direction, then H1 and M15 indicators.
- D1 is the risk officer for directional trading. H1 and M15 may observe any setup, but `long/BUY` is blocked when D1 is short, `short/SELL` is blocked when D1 is long, and D1 `0`/`N/A`/unknown blocks all lower-timeframe directional trades.
- The reusable gate is `python/ai_engine/d1_risk_officer.py`; strategy reports should mark blocked candidates as `blocked_by_d1_risk_officer`, not silently delete the observation.
- `check` is a strict current-clock freshness test: DuckDB must match the latest MT5 raw bar visible at check time.
- `update-h1`, `update-m15`, and `rebuild-d1` are accepted against the MT5 raw bars captured before the command starts. If a new H1/M15 bar appears during a long update, the report may show current-clock freshness as stale while the `Acceptance` section is still `ok` for the command target.

## Full Rebuild Guard

The D1 builder rewrites `data/hermass_state.db`. Use this only after confirmation:

```powershell
python hermass_state_ops.py rebuild-d1 --confirm-full-rebuild --report
```

`rebuild-d1` first copies existing state databases into `data/backups/` and the D1 builder writes a temporary DB before replacing the active DB.

## Contraction Watch

The report includes an observation-only `Contraction Watch` section. It reuses the project squeeze block and SQX references:

- `python.analytics.squeeze_observer.SqueezeObserver`
- `python.ai_engine.pivot_contraction.detect_contraction`
- `D:\SQX136\custom_indicators\MetaTrader5\Indicators\SqSRPercentRank.mq5`
- `D:\SQX136\custom_indicators\MetaTrader5\Indicators\SqPivots.mq5`

Required observations:

- multi-timeframe SR support/resistance contraction,
- 1D/3D/6D pivot contraction,
- multi-timeframe Bollinger Band width contraction,
- ADX contraction tiers `<20`, `<13`, `<9`.

These metrics support LLM analysis and memory notes only. They are not live-trading approval.

## Local MT5 Indicator Pack

Use these user-provided MT5 indicators as the chart-side reference set for the contraction board and any observer-only MT5 EA:

- `D:\qoder\csvcl - AVA\MT5\Indicators\RSIOMA_v2HHLSX.mq5`: RSIOMA momentum, trend histogram, buy/sell trigger, MA-RSIOMA, cross signal.
- `D:\qoder\csvcl - AVA\MT5\Indicators\Kaufman_Bands.mq5`: Kaufman AMA, up/down AMA slope signals, upper/lower adaptive bands.
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_Kaufman_Bandwidth616.mq5`: Kaufman20, BB20, BB50, Kaufman50 bandwidth and contraction/expansion signal.
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_1.mq5`: opening range, A Up/A Down, C Up/C Down.
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_2.mq5`: 1D pivot range, previous high/low, pivot 14/30/50 MAs.
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_3.mq5`: 3D rolling pivot point/top/bottom/width.
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_6.mq5`: 6D rolling pivot point/top/bottom/width.
- `D:\qoder\csvcl - AVA\MT5\Indicators\ACD_枢轴.mq5`: dashboard reference for 1D/3D/6D contraction counts and range/room display.

The exact buffer map is stored in `skills/hermass-mt5-state/references/MT5_ACD_KAUFMAN_INDICATORS.md`.

## Obsidian / Memory Agent

Reports are copied to:

```text
D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports
```

Table copies go to:

```text
D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Tables
```

Memory-agent convention:

- One report per run.
- Keep raw command evidence in fenced blocks.
- Summarize decisions in `Hermass/Decisions/` only after user confirmation.
- Do not overwrite historical reports.

## Lark / Feishu Sheet Sync

Lark sync is optional and never replaces the local report/table files. Enable it only when the target spreadsheet is known:

```powershell
python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY --report --sync-lark --lark-spreadsheet-token "<sht...>" --lark-sheet-id "<sheet_id>"
```

Equivalent environment variables are supported for scheduled runners:

```text
HERMASS_SYNC_LARK=1
HERMASS_LARK_SPREADSHEET_TOKEN=<sht...>
HERMASS_LARK_SHEET_ID=<sheet_id>
HERMASS_LARK_RANGE=A1
HERMASS_LARK_AS=user
```

Implementation notes:

- The command uses `C:\Users\MECHREVO\AppData\Roaming\npm\lark-cli.cmd`, not `lark-cli.ps1`, to avoid PowerShell execution-policy blocks.
- Default identity is `user`; use `--lark-as bot` only when the spreadsheet is owned/shared for the bot.
- Sync appends rows through `lark-cli sheets +append --spreadsheet-token/--url --sheet-id/--range --values`.
- Lark failures are written to the report's `Lark Sync` and `Notes` sections. They do not turn a successful local MT5 data update into a data failure.

## Implementation Sequence

1. Run `check` and confirm MT5 raw data freshness.
2. Run `update-h1` for a small symbol set, then compare raw H1 latest vs DuckDB H1 latest.
3. Run `update-m15` for a small symbol set, then verify `m15_state_snapshot` and `m15_sr_levels`.
4. Generate task plan:
   ```powershell
   python hermass_state_ops.py plan-schedule --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --output docs/HERMASS_TASKS_PLAN_20260609.md
   ```
5. Review report with the user.
6. Register Windows scheduled tasks using `scripts/register_hermass_tasks.ps1`.

## Scheduled Task Wrappers

Use wrapper scripts instead of long inline `/TR` commands:

```text
scripts/hermass_update_h1.cmd
scripts/hermass_update_m15.cmd
scripts/hermass_rebuild_d1.cmd
```

The wrappers write logs to `logs/tasks/` and lock files to `locks/` to prevent duplicate task runs.

Default registration creates only H1 and M15 update tasks:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_hermass_tasks.ps1
```

D1 rebuild is guarded because it rewrites `data/hermass_state.db`. If a D1 task is needed, register it explicitly; the script creates it disabled so it stays an on-demand/manual control:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_hermass_tasks.ps1 -IncludeD1Rebuild
```

## MT5 Software Option

The preferred first phase is script-run data/report automation through the official MetaTrader5 Python API. MT5 EA loading can be added later for chart-side execution, alerts, or order routing.

MT5 EA/indicator loading is not required for D1/H1/M15 data refresh while the Python API can read raw bars from the logged-in AvaTrade terminal.
