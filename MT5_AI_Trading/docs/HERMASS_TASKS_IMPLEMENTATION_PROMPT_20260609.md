# Hermass Implementation Prompt

Use this prompt when assigning execution after the runbook is accepted.

```text
You are implementing the Hermass MT5 state update loop in D:\qoder\csvcl - AVA\MT5_AI_Trading.

Rules:
- Do not place trades.
- Do not register Windows scheduled tasks until the user explicitly approves.
- Do not run D1 full rebuild unless `--confirm-full-rebuild` is present and the user has approved.
- Always compare MT5 raw latest bars with DuckDB latest state timestamps.
- Always write reports to `reports/ops/` and to the Obsidian vault via `--report`.

Commands:
1. Check:
   python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --report
2. H1 update:
   python hermass_state_ops.py update-h1 --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 120 --report
3. M15 update:
   python hermass_state_ops.py update-m15 --symbols EURUSD GBPUSD USDJPY --days 30 --report
4. Task plan:
   python hermass_state_ops.py plan-schedule --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --output docs/HERMASS_TASKS_PLAN_20260609.md

Acceptance:
- Provide latest raw MT5 D1/H1/M15 time per symbol.
- Provide latest DuckDB D1/H1/M15 state time per symbol.
- Provide command outputs and non-zero exits.
- Provide whether the system is ready for task registration.
```
