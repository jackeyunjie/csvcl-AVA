# Trade Opportunity Journal PRD

Date: 2026-06-11  
Status: Phase 1 PRD / manual-first / local-only

## 1. Objective

Build a local Trade Opportunity Journal for Hermass so human-observed trading opportunities can be recorded, searched, reviewed, and later analyzed with large-sample statistics.

This product records:

1. What looked like an opportunity.
2. Why it looked attractive.
3. What D1/H1 State and SQX evidence existed at the time.
4. Whether it was acted on.
5. What happened afterward.

This is an observation and review system, not a trading system.

## 2. Scope

### In Scope

- Local DuckDB storage.
- Manual-first entry and review.
- Query, list, show, export JSON, export CSV.
- Opportunity taxonomy and review taxonomy.
- D1/H1 State context capture.
- SQX evidence capture as tags.
- Phase 1/2/3 roadmap.

### Out of Scope

- Live trading.
- MT5 order API calls.
- Automatic trade execution.
- Scheduled task registration.
- M15 as a required field or required workflow.
- Manual State Hex -> direction mapping.
- Any rule that treats SQX as trade permission.

## 3. Product Definition

The journal separates four layers:

1. Human observation: what the user saw.
2. Context evidence: D1/H1 State and SQX tags.
3. Execution record: whether a trade was taken and how it was entered/exited.
4. Outcome review: post-trade or post-observation evaluation.

The journal must preserve this separation. A good setup can still fail. A bad setup can still work. The database must keep both the setup and the outcome.

## 4. Phase Roadmap

### Phase 1: Manual Journal MVP

- Local-only DuckDB.
- 50-100 manual records.
- No model training.
- No API prefill required.
- Required CLI: `init`, `add`, `list`, `show`, `export-json`, `export-csv`.
- Export directories under `data/trade_journal_exports/` and `data/trade_journal_assets/`.

### Phase 2: Review and Analysis

- Add filtering, statistics, and tag-based summaries.
- Add outcome distributions by opportunity type, symbol, and evidence bundle.
- Add simple quality checks for missing fields and inconsistent tags.
- Keep it local and read-only for analysis.

### Phase 3: Assisted Research Workflow

- Use the journal as input for review reports and strategy research.
- Support bulk import from curated notes or reports.
- Add lightweight ranking or clustering of opportunities.
- Still no autonomous trading and no order routing.

## 5. Data Model

### 5.1 Identity and Timing

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `opportunity_id` | text | yes | Stable unique id for one journal entry. |
| `symbol` | text | yes | Instrument code such as EURUSD, XAUUSD, US_500. |
| `observed_at` | timestamp | yes | When the opportunity was first noticed. |
| `trade_date` | date | no | Trading date associated with the observation. |
| `created_by` | text | yes | Human or agent label that created the record. |
| `created_at` | timestamp | yes | Record creation timestamp. |

### 5.2 Opportunity Description

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `opportunity_type` | text | yes | Controlled category for the opportunity. |
| `core_logic` | text | yes | Short explanation of why it looked interesting. |
| `confidence_note` | text | no | Human confidence and caveats in plain language. |
| `timeframe_context` | text | no | Free-text note for the chart/timeframe context. |

### 5.3 State and SQX Context

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `d1_view_state` | text | no | D1 viewpoint state text or code as context. |
| `h1_view_state` | text | no | H1 viewpoint state text or code as context. |
| `mn1_state` | text | no | Higher-timeframe context, if manually recorded. |
| `w1_state` | text | no | Higher-timeframe context, if manually recorded. |
| `d1_state` | text | no | D1 structure-state note, if useful. |
| `ef_count` | integer | no | Evidence-feature count or similar summary number. |
| `d1_risk_direction` | text | no | Human note about risk bias only, not a derived mapping. |
| `sqx_evidence_tags` | text | no | Comma-separated evidence tags such as `pivot_contraction,adx_tier_lt20`. |

Rules for this block:

- State fields are context features, not direction permission.
- SQX tags are evidence labels, not entry permission.
- No manual State Hex -> long/short mapping is allowed.
- M15 is optional free text only; it is not required in Phase 1.

### 5.4 Price and Execution

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `key_price` | double | no | Important reference price. |
| `trigger_price` | double | no | Price that would validate the setup. |
| `invalid_price` | double | no | Price that invalidates the setup. |
| `target_price` | double | no | Planned objective price. |
| `execution_status` | text | no | `planned`, `taken`, `missed`, `not_taken`, `closed`. |
| `entry_price` | double | no | Actual entry price if a trade was taken. |
| `exit_price` | double | no | Actual exit price if a trade was closed. |
| `result_r` | double | no | Trade result in R. |
| `result_pct` | double | no | Trade result in percent. |

### 5.5 Review

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `review_outcome` | text | yes when reviewed | Controlled outcome label. |
| `review_tags` | text | no | Multi-tag post-review labels. |
| `review_note` | text | no | Short narrative on what happened. |
| `forward_return_1h` | double | no | Forward return label for later analysis. |
| `forward_return_4h` | double | no | Forward return label for later analysis. |
| `forward_return_1d` | double | no | Forward return label for later analysis. |
| `json_exported_at` | timestamp | no | Export timestamp for downstream use. |

### 5.6 Assets

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `screenshot_path` | text | no | Local path to a chart screenshot. |
| `chart_note` | text | no | Visual note about the chart or pattern. |

## 6. Controlled Vocabulary

### 6.1 Opportunity Types

Allowed values:

- `state_regime_observation`
- `sqx_contraction`
- `pivot_breakout`
- `rsioma_momentum`
- `d1_h1_alignment`
- `fundamental_event`
- `missed_trade`
- `failed_setup`

Guidance:

- Use one primary type per record.
- If a record fits multiple patterns, choose the dominant driver and record the rest in `core_logic` or `sqx_evidence_tags`.

### 6.2 Review Outcomes

Allowed values:

- `worked`
- `failed`
- `too_early`
- `too_late`
- `invalidated`
- `no_trade`
- `data_insufficient`

Meaning:

- `worked`: the setup behaved as expected.
- `failed`: the setup did not work after entry or observation.
- `too_early`: the idea was right but timing was premature.
- `too_late`: the move already occurred or the entry was chased.
- `invalidated`: the setup broke the invalidation level.
- `no_trade`: observation did not become a trade.
- `data_insufficient`: not enough information to judge.

### 6.3 Review Tags

Allowed review tags should remain controlled and reusable. Recommended initial set:

- `early_entry`
- `late_entry`
- `missed_entry`
- `false_breakout`
- `trend_continuation`
- `mean_reversion`
- `news_driven`
- `range_bound`
- `momentum_strength`
- `momentum_failure`
- `risk_too_wide`
- `risk_too_tight`
- `good_setup_bad_execution`
- `bad_setup_good_outcome`
- `clean_invalidated`
- `post_event_move`

Tags are multi-select and should be stored as a delimited text field in Phase 1.

## 7. Connection to State/SQX Validation

The journal reuses the current validation contract, but only as context.

### 7.1 D1/H1 State

- D1/H1 State fields are observational context.
- They help describe regime, alignment, and position.
- They do not authorize a trade.
- They do not imply a fixed long/short interpretation.

### 7.2 SQX Evidence

- SQX indicators are evidence tags only.
- Examples: contraction, breakout, ADX tier, RSIOMA trigger, pivot behavior.
- SQX should be recorded as observed evidence, not as permission logic.

### 7.3 No M15 Requirement

- Phase 1 does not require M15.
- If M15 is relevant to a human note, store it as free text.
- Do not make M15 a schema blocker for journal entry creation.

### 7.4 No State Hex Mapping

- State Hex is not converted into a manual long/short table.
- If State Hex is recorded, it is a feature or regime label only.
- Directional interpretation belongs to later statistical analysis, not to the journal schema.

## 8. Example Records

Below are five concrete examples the schema must support.

| opportunity_id | symbol | observed_at | opportunity_type | core_logic | sqx_evidence_tags | execution_status | review_outcome |
|---|---|---|---|---|---|---|---|
| TOJ-20260611-001 | EURUSD | 2026-06-11 09:15:00 | d1_h1_alignment | D1 and H1 both cleanly aligned after a shallow pullback; price held above the prior intraday reference. | `d1_alignment,h1_pullback,bb_width_contracting` | planned | too_early |
| TOJ-20260611-002 | XAUUSD | 2026-06-11 10:40:00 | sqx_contraction | H1 compression tightened near a prior range edge and the setup looked ready for breakout expansion. | `pivot_contraction,adx_tier_lt20,sr_contraction` | taken | worked |
| TOJ-20260611-003 | US_500 | 2026-06-11 13:05:00 | pivot_breakout | Price pushed through the local pivot after a multi-bar squeeze, but the entry came after the first impulse bar. | `pivot_breakout,breakout_followthrough,late_entry` | taken | too_late |
| TOJ-20260611-004 | EURUSD | 2026-06-10 21:30:00 | fundamental_event | A scheduled macro release created a clear volatility expansion, but the move was too news-driven for a clean model review. | `news_event,volatility_expansion,adx_tier_gt20` | not_taken | no_trade |
| TOJ-20260611-005 | XAUUSD | 2026-06-11 15:20:00 | failed_setup | The setup looked valid at first, but the invalidation level was broken before confirmation. | `false_breakout,pivot_failure,rsioma_failure` | taken | invalidated |

## 9. Acceptance Criteria

The PRD is acceptable if QODER can implement the MVP with these properties:

1. `init` creates the DuckDB database and required directories.
2. `add` supports a manual record with the required fields.
3. `list`, `show`, `export-json`, and `export-csv` work locally.
4. Data lives under `MT5_AI_Trading/data/`.
5. The journal keeps observation, evidence, execution, and outcome separate.
6. No live trading, MT5 order API, or scheduled task behavior is introduced.

## 10. Handoff Notes for QODER

- Use `data/trade_journal.duckdb` as the canonical store.
- Use `data/trade_journal_exports/` for exports.
- Use `data/trade_journal_assets/` for screenshots and attachments.
- Keep the schema simple enough for manual entry, but structured enough for later analysis.
- Treat `review_outcome` as a distinct field from `execution_status`.
- Keep all State and SQX fields as evidence or context only.

