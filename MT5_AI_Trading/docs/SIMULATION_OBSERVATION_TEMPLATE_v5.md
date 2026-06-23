# Multi-Timeframe Squeeze v5 Simulation Observation Template
> Date: 2026-06-05 | Purpose: paper-trading observation log for v5

## 1. Objective

Use this template to answer:

1. Whether `run_v5_simulation.py` behaves consistently with v5 backtest logic
2. Whether real-time candidate signals remain explainable and executable
3. Whether there is systematic drift between backtest and simulation observation

Current stage:

- Allowed: simulation scan, manual observation, manual review
- Not allowed: direct live auto-trading

## 2. Daily Checklist

### Before run

- [ ] Script confirmed: `run_v5_simulation.py`
- [ ] Params confirmed: `max_adx=12`, `min_range=0.50`, `cooldown=5`
- [ ] v5 whitelist of 14 symbols still in use
- [ ] MT5 / data source connection healthy
- [ ] `simulation_logs/` writable

### During run

- [ ] Hourly scan runs normally
- [ ] No obvious symbol gaps
- [ ] No empty-data or runtime errors
- [ ] Candidate fields are complete

### End of day

- [ ] Daily `simulation_logs` retained
- [ ] Candidate count recorded
- [ ] Confirmed breakout vs pending setup marked
- [ ] Any mismatch with backtest logic recorded
- [ ] Daily conclusion updated

## 3. Daily Run Record

| Field | Value |
|------|------|
| Date | |
| Operator | |
| Run mode | `--once` / continuous |
| Scan window | |
| Output file | |
| Completed normally | Yes / No |

## 4. Parameter Snapshot

| Parameter | Value |
|------|------|
| min_squeeze_score | 2 |
| cooldown_bars | 5 |
| max_adx | 12 |
| min_anchor_range_pct | 0.50% |
| max_wait_bars | 30 |
| min_breakout_anchor_multiple | 0.1 |
| require_1bar_confirmation | True |

## 5. Candidate Observation Table

| Scan time | Symbol | setup_time | direction | confirmed | squeeze_score | adx | anchor_range_pct | H4 | D1 | Notes |
|------|------|------|------|------|------|------|------|------|------|------|
| | | | | | | | | | | |
| | | | | | | | | | | |
| | | | | | | | | | | |

Recommended notes:

- structurally valid but not broken out
- 1-bar confirmation observed or not
- H4/D1 trend conflict
- visual chart check inconsistent with script output

## 6. Exception And Drift Log

| Time | Type | Symptom | Scope | Initial judgment | Resolved |
|------|------|------|------|------|------|
| | data | | | | |
| | logic | | | | |
| | runtime | | | | |

Typical categories:

- data gap
- as-of alignment issue
- symbol mapping issue
- breakout confirmation issue
- CSV output issue
- wrong parameter use

## 7. Backtest Consistency Review

| Symbol | setup_time | Simulation observation | Backtest expectation | Match | Notes |
|------|------|------|------|------|------|
| | | | | | |
| | | | | | |

Summary:

- matched samples:
- mismatched samples:
- dominant mismatch type:

## 8. Weekly Summary

| Period | Scan days | Candidate setups | Confirmed signals | Major issues | Conclusion |
|------|------|------|------|------|------|
| Week 1 | | | | | |
| Week 2 | | | | | |
| Week 3 | | | | | |
| Week 4 | | | | | |

Recommendation: observe at least 4 weeks before any next-stage decision.

## 9. Admission Gate

Only discuss moving to manual-confirmation trading after all items are checked:

- [ ] At least 4 weeks of simulation observation
- [ ] Signal generation stable
- [ ] Backtest logic and real-time scan broadly consistent
- [ ] No systematic look-ahead / as-of issue found
- [ ] Whitelist symbols executable in real-time environment
- [ ] Risk controls separately defined and reviewed

Current assessment:

- conclusion: not ready / ready for next-stage evaluation
- notes:

## 10. Notes

- This template is only for simulation-stage observation.
- If default params in `run_v5_simulation.py` change, record date, reason, and impact.
- If whitelist or exit rule changes, start a new observation cycle instead of mixing records.
