# KIMI / QODER Prompts: Trade Opportunity Journal

Date: 2026-06-11
Status: Delegation prompts / manual-recording phase

## Background

KIMI proposed a "交易机会记录系统": structured recording of human-perceived trading opportunities so they can become a searchable local database and later be used for model learning, ranking, and review.

Current Hermass project policy:

1. Current State/SQX validation scope is **D1 viewpoint + H1 viewpoint only**.
2. M15 is retained for future real-time work, but it is excluded from current data update, validation, and reporting tasks.
3. State Hex is a feature/evidence field, not a manual long/short mapping.
4. SQX indicators are evidence modules, not trade permission.
5. No live trading, no MT5 order API calls, no scheduled trading tasks.

## Target Outcome

Build a local "Trade Opportunity Journal" that records:

```text
What looked like a good opportunity,
why it looked good,
what D1/H1 State/SQX context existed,
whether it was acted on,
and what happened afterward.
```

This is an observation and data-collection system first. It is not a trading bot.

## Shared Field Draft

Required fields:

```text
opportunity_id
symbol
observed_at
trade_date
opportunity_type
core_logic
created_by
created_at
```

Strongly recommended fields:

```text
d1_view_state
h1_view_state
mn1_state
w1_state
d1_state
ef_count
d1_risk_direction
sqx_evidence_tags
key_price
trigger_price
invalid_price
target_price
timeframe_context
confidence_note
```

Optional fields:

```text
screenshot_path
chart_note
execution_status
entry_price
exit_price
result_r
result_pct
review_tags
review_note
forward_return_1h
forward_return_4h
forward_return_1d
json_exported_at
```

Important:

- Do not force State Hex into direction labels.
- Do not require M15 fields in Phase 1.
- If M15 context is mentioned manually, store it as free-text evidence only.

---

# KIMI Prompt

You are responsible for refining the product design and data taxonomy for the Hermass Trade Opportunity Journal.

Workspace:

```text
D:\qoder\csvcl - AVA\MT5_AI_Trading
```

Required reading:

```text
docs\STATE_VIEWPOINT_AGENT_CONTRACT.md
docs\STATE_SQX_VALIDATION_PRD_20260611.md
docs\STATE_SQX_VALIDATION_TECH_SPEC_20260611.md
docs\QODER_DATA_AND_STRATEGYSET_ACCUMULATION_PROMPT_20260611.md
docs\KIMI_QODER_TRADE_OPPORTUNITY_JOURNAL_PROMPTS_20260611.md
```

Task:

1. Convert the existing "交易机会记录系统" idea into a Hermass-compatible PRD.
2. Keep Phase 1 manual-first:
   - human records 50-100 opportunities,
   - no API prefill required,
   - no model training yet.
3. Define a field dictionary:
   - required fields,
   - recommended fields,
   - optional fields,
   - allowed values for opportunity type and review tags.
4. Define opportunity categories, for example:
   - state_regime_observation,
   - sqx_contraction,
   - pivot_breakout,
   - rsioma_momentum,
   - d1_h1_alignment,
   - fundamental_event,
   - missed_trade,
   - failed_setup.
5. Define review outcomes:
   - worked,
   - failed,
   - too_early,
   - too_late,
   - invalidated,
   - no_trade,
   - data_insufficient.
6. Define how the journal connects to current State/SQX validation:
   - D1/H1 state as context features,
   - SQX evidence as tags,
   - no M15 requirement,
   - no State Hex -> direction mapping.
7. Provide 5 concrete example records using realistic symbols such as EURUSD, XAUUSD, US_500.
8. Produce a concise PRD at:

```text
docs/TRADE_OPPORTUNITY_JOURNAL_PRD_20260611.md
```

Hard restrictions:

- Do not modify code.
- Do not place trades.
- Do not call MT5 order APIs.
- Do not propose automatic trading.
- Do not create manual State Hex direction mappings.
- Do not make M15 mandatory.

Acceptance:

- The PRD can be handed to QODER for implementation.
- The PRD distinguishes human observation, State/SQX evidence, execution record, and outcome review.
- The PRD includes Phase 1/2/3 roadmap.
- Phase 1 remains local, manual, and DuckDB-based.

---

# QODER Prompt

You are responsible for implementing a minimal local Trade Opportunity Journal MVP for Hermass.

Workspace:

```text
D:\qoder\csvcl - AVA\MT5_AI_Trading
```

Required reading:

```text
docs\STATE_VIEWPOINT_AGENT_CONTRACT.md
docs\STATE_SQX_VALIDATION_PRD_20260611.md
docs\STATE_SQX_VALIDATION_TECH_SPEC_20260611.md
docs\KIMI_QODER_TRADE_OPPORTUNITY_JOURNAL_PROMPTS_20260611.md
docs\TRADE_OPPORTUNITY_JOURNAL_PRD_20260611.md
```

KIMI's PRD is available. Implement from `docs\TRADE_OPPORTUNITY_JOURNAL_PRD_20260611.md` as the source of truth. If this prompt conflicts with the PRD, follow the PRD and document the difference in the implementation report.

Implementation scope:

1. Add a CLI script:

```text
trade_journal.py
```

2. Store data under the project workspace, not `~/trade_journal`:

```text
data/trade_journal.duckdb
data/trade_journal_exports/
data/trade_journal_assets/
```

3. Support commands:

```powershell
python trade_journal.py init
python trade_journal.py add
python trade_journal.py list
python trade_journal.py show --id <opportunity_id>
python trade_journal.py export-json --output data/trade_journal_exports/opportunities.json
python trade_journal.py export-csv --output data/trade_journal_exports/opportunities.csv
```

4. MVP schema:

```sql
trade_opportunities(
  opportunity_id TEXT PRIMARY KEY,
  symbol TEXT NOT NULL,
  observed_at TIMESTAMP NOT NULL,
  trade_date DATE,
  opportunity_type TEXT NOT NULL,
  core_logic TEXT NOT NULL,
  d1_view_state TEXT,
  h1_view_state TEXT,
  mn1_state TEXT,
  w1_state TEXT,
  d1_state TEXT,
  ef_count INTEGER,
  d1_risk_direction TEXT,
  sqx_evidence_tags TEXT,
  key_price DOUBLE,
  trigger_price DOUBLE,
  invalid_price DOUBLE,
  target_price DOUBLE,
  timeframe_context TEXT,
  confidence_note TEXT,
  screenshot_path TEXT,
  chart_note TEXT,
  execution_status TEXT,
  entry_price DOUBLE,
  exit_price DOUBLE,
  result_r DOUBLE,
  result_pct DOUBLE,
  review_outcome TEXT,
  review_tags TEXT,
  review_note TEXT,
  forward_return_1h DOUBLE,
  forward_return_4h DOUBLE,
  forward_return_1d DOUBLE,
  json_exported_at TIMESTAMP,
  created_by TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

5. CLI behavior:
   - `init`: creates DB, table, export/assets dirs.
   - `add`: interactive prompt for required fields and important optional fields from the PRD.
   - `list`: shows latest records with symbol, observed_at, opportunity_type, execution_status.
   - `show`: prints one record as readable JSON.
   - `export-json`: exports all records.
   - `export-csv`: exports all records.
   - validate controlled values for `opportunity_type`, `execution_status`, and `review_outcome` when provided.

6. Add minimal tests or a smoke-check command if the project test style supports it.

7. Produce implementation report at:

```text
reports/ops/qoder_trade_opportunity_journal_mvp_20260611.md
```

Hard restrictions:

- Do not place trades.
- Do not call MT5 order APIs.
- Do not register scheduled tasks.
- Do not run D1 full rebuild.
- Do not run M15 update.
- Do not create State Hex -> direction mappings.
- Do not make external network calls.

Acceptance:

- `python trade_journal.py init` creates the DuckDB database and directories.
- `python trade_journal.py add` can create at least one manual record.
- `list`, `show`, `export-json`, and `export-csv` work.
- Data remains local under `MT5_AI_Trading/data/`.
- Schema includes PRD fields including `review_outcome`, `chart_note`, forward return labels, and `json_exported_at`.
- Controlled vocabulary from the PRD is enforced or clearly warned in CLI input.
- Report confirms no trading action and no MT5 order API calls.

---

# Immediate WeChat Summary

```text
当前任务：做“交易机会记录系统”MVP。

KIMI：先完善 PRD 和字段字典，明确机会类型、复盘标签、Phase 1/2/3，不改代码。

QODER：实现本地 DuckDB + Python CLI：
python trade_journal.py init
python trade_journal.py add
python trade_journal.py list
python trade_journal.py show --id <id>
python trade_journal.py export-json
python trade_journal.py export-csv

边界：不下单、不调用 MT5 order API、不跑 M15 更新、不写 State Hex 到方向的人工映射。D1/H1 State 只作为上下文特征。
```
