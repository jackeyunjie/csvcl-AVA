# State/SQX Validation PRD

Date: 2026-06-11
Status: Validation requirements / no-live-trading

## Objective

Validate whether the Hermass State viewpoint system and SQX indicator evidence can produce repeatable, explainable, and statistically useful strategy signals.

Current validation scope is **D1 viewpoint + H1 viewpoint only**. M15 is retained for future real-time work, but it is excluded from current data update, validation, and reporting tasks.

This project does **not** validate a hand-written State Hex -> long/short mapping. State Hex values are treated as features and regime labels. Directional value must be discovered through large-sample statistics, walk-forward validation, symbol segmentation, and regime-specific performance.

## Scope

### In Scope

1. Validate State viewpoint data quality across D1/H1.
2. Validate whether State regimes have measurable forward-return distributions.
3. Validate SQX evidence modules:
   - Pivot contraction,
   - SR PercentRank / support-resistance contraction,
   - Bollinger Band width contraction,
   - ADX tiers `<20`, `<13`, `<9`,
   - RSIOMA trigger,
   - ACD breakout,
   - Kaufman Bands.
4. Validate multi-timeframe evidence combinations:
   - D1 context,
   - H1 position/momentum,
   - SQX contraction/breakout evidence.
5. Produce static reports, tables, and charts for review.

### Out of Scope

1. Live trading.
2. MT5 order API calls.
3. Broker integration.
4. Automatic scheduled trading.
5. Manual State Hex -> direction mapping.
6. D1 full rebuild unless separately approved.

## Key Questions

### Q1: Data Quality

Can we reliably produce fresh, aligned, and viewpoint-correct D1/H1 State data?

Acceptance:

- Raw MT5 latest bars and DuckDB latest timestamps are reported separately.
- D1/H1 viewpoint contract is not violated.
- Each symbol has coverage statistics and missing-data notes.

### Q2: State Regime Value

Do State regimes show non-random forward-return distributions?

Acceptance:

- For each symbol/timeframe/regime, report sample count, mean return, median return, win rate, volatility, max adverse excursion, max favorable excursion.
- No regime is promoted if sample count is too small.
- Results are segmented by symbol and timeframe.

### Q3: SQX Evidence Value

Do SQX evidence modules improve signal quality compared with State-only baselines?

Acceptance:

- Compare baseline State regimes vs State + SQX evidence combinations.
- Report lift in win rate, profit factor, drawdown, Sharpe, and trade count.
- Identify evidence modules that add value and modules that add noise.

### Q4: Multi-Timeframe Resonance

Does D1/H1 evidence alignment improve outcomes?

Acceptance:

- Compare D1-only and D1+H1 evidence sets.
- Do not assume fixed weights before evidence supports them.
- Report whether adding H1 evidence improves or worsens out-of-sample performance.

### Q5: Robustness

Do results survive out-of-sample and walk-forward tests?

Acceptance:

- Use train/test or rolling walk-forward splits.
- Report in-sample and out-of-sample separately.
- Flag overfit patterns where in-sample is strong and out-of-sample collapses.

## Validation Horizon

### Phase 0: Readiness Audit

Duration: 1-2 days.

Goal:

- Confirm current data coverage, freshness, and available strategy reports.

Deliverables:

- Data readiness report.
- Missing data list.
- Strategy-set inventory.

### Phase 1: Data Accumulation

Duration: 3-7 days operationally, depending on MT5 history availability.

Target:

- H1: 180 days if available, fallback 120 days.
- M15: excluded from current data update.
- Symbols: EURUSD, GBPUSD, USDJPY, XAUUSD, US_30, US_500, US_TECH100.

Deliverables:

- H1 coverage table.
- Freshness comparison before and after update.
- Failure report for unavailable symbols/timeframes.

### Phase 2: Statistical Validation

Duration: 3-5 days after data is ready.

Goal:

- Compute forward-return distributions for State regimes and SQX evidence.

Forward horizons:

- H1: 1, 4, 12, 24 bars.
- D1: 1, 3, 5, 10 bars.

Deliverables:

- State regime forward-return tables.
- SQX evidence lift tables.
- Multi-timeframe evidence comparison.

### Phase 3: Strategy Backtest

Duration: 3-5 days after Phase 2.

Goal:

- Validate candidate strategy sets in the existing StateHexBacktestEngine or project-native backtest scripts.

Deliverables:

- Static HTML/Markdown reports.
- Equity curve and drawdown charts.
- State-regime heatmap.
- Parameter scan summary.

### Phase 4: Paper-Only Observation

Duration: minimum 2 weeks after Phase 3 approval.

Goal:

- Observe signals without live execution.

Deliverables:

- Daily candidate signal log.
- D1 Risk gate outcome.
- SQX evidence snapshot.
- Forward outcome after fixed horizons.

## Critical Metrics

| Area | Metric | Required View |
|---|---|---|
| Data | raw latest vs DB latest | by symbol/timeframe |
| Data | row count and coverage days | by symbol/timeframe |
| Regime | sample count | by state/timeframe/symbol |
| Regime | forward return mean/median | by horizon |
| Regime | win rate | by horizon |
| Regime | MAE/MFE | by horizon |
| Strategy | profit factor | in-sample/out-of-sample |
| Strategy | max drawdown | in-sample/out-of-sample |
| Strategy | Sharpe | in-sample/out-of-sample |
| Strategy | trade count | by symbol/regime |
| Robustness | OOS degradation | by strategy set |

## Promotion Rules

A State/SQX pattern can be promoted from observation to strategy candidate only if:

1. Sample count is sufficient for the symbol and timeframe.
2. Out-of-sample performance is not materially worse than in-sample.
3. Drawdown and trade frequency are acceptable.
4. SQX evidence improves over State-only baseline.
5. D1 Risk gate is respected.
6. Results are documented in reports and linked to experiment configuration.

## Rejection Rules

Reject or quarantine a pattern if:

1. It has low sample count.
2. It only works in one symbol without explanation.
3. It fails out-of-sample.
4. It depends on lookahead leakage.
5. It requires manual State Hex direction mapping.
6. It bypasses D1 Risk Officer.

## Required Reports

1. `reports/ops/qoder_state_sqx_validation_readiness_20260611.md`
2. `reports/validation/state_sqx_forward_returns_YYYYMMDD.md`
3. `reports/validation/state_sqx_strategy_backtest_YYYYMMDD.md`
4. `reports/validation/state_sqx_validation_summary_YYYYMMDD.md`

## Decision Gate

No live or paper-trading automation is allowed until Phase 0-3 reports are complete and explicitly reviewed.
