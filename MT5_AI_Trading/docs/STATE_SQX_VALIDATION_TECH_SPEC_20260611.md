# State/SQX Validation Technical Spec

Date: 2026-06-11
Status: Technical validation design / no-live-trading

## Existing Assets

Use project-native infrastructure first.

Current validation scope is **D1 viewpoint + H1 viewpoint only**. M15 is retained for future real-time work, but it is excluded from current data update, validation, and reporting tasks.

| Area | Existing Asset |
|---|---|
| State contract | `docs/STATE_VIEWPOINT_AGENT_CONTRACT.md` |
| Operations | `hermass_state_ops.py` |
| H1 DB | `data/h1_state.duckdb` |
| D1 DB | `data/hermass_state.db`, `data/state_hermass.duckdb` |
| Backtest | `python/backtest/state_hex_backtest.py` |
| SQX contraction | `python.analytics.squeeze_observer.SqueezeObserver`, `python.ai_engine.pivot_contraction.detect_contraction` |
| Reports | `reports/`, `data/strategy_report.md`, `data/strategy_state_heatmap.svg` |

Do not introduce vectorbt, Streamlit, or MLflow for this phase unless a later decision explicitly approves it.

## Data Model

### Viewpoint State Rows

Each row should be interpreted as:

```text
view_tf timestamp + view_tf close + structure_tf state components
```

Required fields when available:

```text
symbol
view_tf
timestamp
close
d1_hex
h1_hex
bb_width
sr_range_pct
adx
adx_tier
pivot_contracting
pivot_count
pivot_30d_low
pivot_squeeze_score
sr_breakout
breakout_direction
```

### Forward Return Table

Recommended output table:

```text
symbol
view_tf
timestamp
state_key
evidence_key
horizon_bars
entry_close
future_close
forward_return_pct
mae_pct
mfe_pct
raw_state_features
sqx_features
```

### Strategy Experiment Table

Recommended output table:

```text
experiment_id
created_at
strategy_set
symbols
timeframes
train_start
train_end
test_start
test_end
params_json
trade_count
win_rate
profit_factor
max_drawdown_pct
sharpe
oos_degradation_pct
report_path
```

## Validation Jobs

### Job 1: Readiness

Commands:

```powershell
python hermass_state_ops.py check --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --report
```

Output:

```text
reports/ops/qoder_state_sqx_validation_readiness_20260611.md
```

Required checks:

- raw MT5 latest D1/H1 bars,
- DuckDB latest D1/H1 timestamps,
- row coverage by symbol/timeframe,
- missing tables/columns,
- unavailable symbols.

### Job 2: Data Expansion

Commands:

```powershell
python hermass_state_ops.py update-h1 --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 180 --report
```

Fallback:

```powershell
python hermass_state_ops.py update-h1 --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 120 --report
```

M15 update is excluded from this phase.

Acceptance:

- report command, exit code, duration, report path,
- compare raw latest with DB latest after update,
- distinguish `fresh_at_start` vs `fresh_as_of_finish` if long run crosses bar boundary.

### Job 3: Forward Return Statistics

Build a read-only analysis script or notebook only after data readiness is confirmed.

Inputs:

- H1 state rows,
- D1 state rows if available,
- SQX evidence fields.

Forward horizons:

```text
H1: 1, 4, 12, 24
D1: 1, 3, 5, 10
```

Grouping keys:

```text
symbol
view_tf
state_hex
state_combo
adx_tier
bb_width_bucket
sr_range_bucket
pivot_squeeze_score
sr_breakout
breakout_direction
```

Metrics:

```text
sample_count
mean_forward_return_pct
median_forward_return_pct
win_rate
std_forward_return_pct
mae_pct_mean
mfe_pct_mean
p05_return
p95_return
```

Output:

```text
data/validation/state_sqx_forward_returns.parquet
reports/validation/state_sqx_forward_returns_YYYYMMDD.md
```

### Job 4: Strategy Candidate Backtest

Use project-native backtest infrastructure.

Preferred base:

```text
python/backtest/state_hex_backtest.py
```

Required additions if not already available:

- multi-symbol batch runner,
- parameter scan config,
- static HTML/Markdown summary,
- CSV/Parquet result export.

Do not add live execution.

Strategy candidate types:

```text
State-only baseline
State + ADX tier
State + contraction
State + contraction + breakout
D1/H1 evidence combination
```

Output:

```text
data/validation/state_sqx_strategy_results.parquet
reports/validation/state_sqx_strategy_backtest_YYYYMMDD.md
reports/validation/state_sqx_strategy_heatmap_YYYYMMDD.svg
```

## Leakage Controls

1. Entry must use only information known at or before signal timestamp.
2. Forward returns must use future prices only for labels, not for signal construction.
3. H1 rows must not use future D1 close.
4. Walk-forward split must report train/test separately.

## Minimum Viable Validation

The first acceptable validation package contains:

1. Data readiness report.
2. H1 coverage table for at least 7 target symbols or explicit failure notes.
3. Forward-return statistics for D1/H1.
4. At least one State-only baseline and one State+SQX comparison.
5. Static Markdown report with tables.
6. No code path that places trades.

## QODER Deliverables

QODER should produce:

```text
reports/ops/qoder_state_sqx_validation_readiness_20260611.md
docs/QODER_STATE_SQX_VALIDATION_EXECUTION_PROMPT_20260611.md
```

If QODER proposes code changes, they must be separated into:

```text
documentation-only
analysis-script-only
behavior-changing trading-code
```

Behavior-changing trading-code requires explicit user approval.
