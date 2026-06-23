# Hermass Agent Workflow Orchestration

Date: 2026-06-09

## Goal

Use n8n, Coze, Dify, Agently, KIMI/qoder, Obsidian, and agentmemory as orchestration, reporting, and memory layers around the Hermass MT5 state pipeline.

They must not bypass the local data freshness checks, the D1 rebuild guard, or future live-trading approval gates.

## Current Local Source Of Truth

- Project: `D:\qoder\csvcl - AVA\MT5_AI_Trading`
- Operations script: `hermass_state_ops.py`
- Reports: `reports/ops/`
- Local tables: `reports/ops/tables/`
- Obsidian vault target: `D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE`
- Reference clones: `D:\tmp\hermass_refs`

## Workflow Boundary

| Layer | Recommended tool | Role | May trade |
|---|---|---|---|
| Local data update | Windows Task Scheduler + wrapper scripts | H1/M15 scheduled update, D1 manual rebuild | No |
| Workflow control | n8n / Coze / Dify | Trigger runs, collect reports, send notifications | No |
| Agent execution | Agently | Structured task dispatch, Action logs, Dynamic Task / TriggerFlow experiments | No |
| Research debate | KIMI, qoder, TradingAgents-CN-style roles | Independent review, risk notes, implementation checks | No |
| Product pattern reference | Vibe-Trading | Run card, shadow/paper, swarm status, API/MCP safety ideas | No |
| Memory | Obsidian + agentmemory | Durable reports, decisions, search, recap | No |

## n8n / Coze / Dify Flow

Minimum workflow:

1. Scheduled trigger.
2. Run local command through an approved local runner.
3. Capture exit code, stdout/stderr tail, and report path.
4. Parse the report's `status`, `Freshness`, `Acceptance`, `Table Exports`, and optional `Lark Sync`.
5. Notify user with concrete timestamps.
6. Write summary to Obsidian and memory only after the run has a local report.

Suggested nodes:

- `H1 hourly`: call `scripts/hermass_update_h1.cmd`.
- `M15 every 15 min`: call `scripts/hermass_update_m15.cmd`.
- `Strict check`: call `python hermass_state_ops.py check --report`.
- `LLM analyst`: summarize the latest report, observation-only.
- `Human approval`: required before D1 rebuild or any EA/code generation step.

Every workflow run needs:

- `trace_id`
- `idempotency_key`
- `symbols`
- `timeframes`
- `command`
- `report_path`
- `table_csv_path`
- `exit_code`
- `fresh_at_start`
- `fresh_as_of_finish`
- `d1_first_summary`
- `indicator_pack_status`
- `lark_sync_status`

Optional Lark sync should call the existing script flags instead of building a separate table pipeline:

```powershell
python hermass_state_ops.py check --report --sync-lark --lark-spreadsheet-token "<sht...>" --lark-sheet-id "<sheet_id>"
```

Use `C:\Users\MECHREVO\AppData\Roaming\npm\lark-cli.cmd`. Keep `--lark-as user` unless the sheet is explicitly shared with the bot.

## Agently Dispatch Design

Agently is suitable as the local AI application runtime because its README and docs emphasize structured output contracts, observable Actions, MCP capabilities, Dynamic Task, TriggerFlow, and recoverable workflows.

Recommended use:

- Wrap `hermass_state_ops.py` commands as explicit Actions.
- Require JSON schemas for agent outputs.
- Use Dynamic Task only for non-trading tasks:
  - parse report,
  - assign KIMI/qoder review,
  - generate Obsidian summary,
  - draft SQX DSL,
  - produce risk checklist.
- Keep side effects in host code, not inside free-form model text.

Do not let Agently call MT5 order APIs directly.

## KIMI / qoder Roles

KIMI:

- Validate data-quality and research conclusions.
- Validate that every symbol starts with D1 MA144/169/200 and D1 State Hex before H1/M15 analysis.
- Review RSIOMA, Kaufman, ACD bandwidth, and ACD pivot observations for lookahead and timeframe leakage.
- Review SQX/EA design for lookahead, overfit, and risk leakage.
- Produce concise narrative reports.

qoder:

- Validate scripts, scheduled tasks, exit codes, locks, and report paths.
- Validate the local indicator pack buffer map and observer-only MT5/SQX integration.
- Run syntax checks and smoke tests.
- Draft implementation patches in a disjoint scope.

Commander:

- Own acceptance.
- Decide whether to merge or reject delegated work.
- Report to user before implementing high-risk steps.

## Memory Design

Obsidian remains the human-readable vault. agentmemory can be added later as a cross-agent recall layer.

agentmemory local facts from its README / install guide:

- It provides MCP and REST access.
- Default REST port is `3111`.
- The viewer uses `3113`.
- It has Codex integration via MCP/plugin paths.
- Native Windows setup is more manual than WSL2; full setup needs the iii engine or Docker path.

Memory namespaces:

- `hermass.reports`: immutable run reports and report summaries.
- `hermass.decisions`: user-approved decisions only.
- `hermass.risks`: open risks and mitigation status.
- `hermass.prompts`: KIMI/qoder/Agently prompts.
- `hermass.sqx`: SQX DSL and MQL5 observer plans.

Retention:

- Raw reports are kept in files.
- agentmemory stores summaries and pointers, not whole databases.
- Any memory item affecting execution must include report path and timestamp.

## Security Gates

Required for external workflow tools:

- local-only by default,
- scoped token or API key for non-local access,
- webhook signature verification,
- replay protection,
- idempotency key,
- command allowlist,
- working-directory allowlist,
- no arbitrary shell input,
- no direct broker/MT5 order command,
- manual approval before D1 rebuild, code generation, or EA deployment.

## Phase Plan

### Phase 1: Stable Local Ops

- H1/M15 updates via Windows Task Scheduler.
- D1 rebuild remains manual or disabled on-demand.
- Strict freshness reports stay local.
- Local CSV/Markdown tables are produced with every `--report`.

### Phase 2: Workflow Shell

- Add n8n/Coze/Dify wrappers around the existing commands.
- Send report summaries to Obsidian.
- Keep workflows observation-only.

### Phase 3: Agently Dispatch

- Wrap report parsing and reviewer assignment as typed Actions.
- Use Agently for structured planning and review DAGs.
- Persist only summaries and evidence pointers.

### Phase 4: SQX/EA Observer

- Generate DSL and observer-only MT5 artifacts.
- Use local `RSIOMA_v2HHLSX`, `Kaufman_Bands`, `ACD_Kaufman_Bandwidth616`, `ACD_1/2/3/6`, and `ACD_枢轴` as indicator references.
- Compare observer output with Hermass reports.
- Paper observation before any execution approval.

## Acceptance

The workflow is accepted only when:

- H1 and M15 scheduled tasks run with logs and correct exit codes.
- D1 is not active as a daily destructive job by default.
- Reports include strict freshness and update acceptance.
- Local table exports exist under `reports/ops/tables/`.
- Obsidian or memory failures are visible, not silently treated as data success.
- Lark sync failures are visible in the report and do not override local freshness acceptance.
- All LLM outputs remain report/DSL/review artifacts unless separately approved.
