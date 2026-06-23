# MT5 ACD / Kaufman Indicator Pack

Use this reference when building Hermass contraction reports, MT5 observer EAs, or SQX DSL mappings from the local MT5 indicators under:

```text
D:\qoder\csvcl - AVA\MT5\Indicators
```

These indicators are observation inputs. They do not override the D1 risk officer and must not create live orders without a separate approval gate.

## RSIOMA_v2HHLSX.mq5

Role: RSI-on-moving-average momentum and trigger filter.

Inputs:

- `RSIOMA=14`
- `RSIOMA_MODE=MODE_EMA`
- `RSIOMA_PRICE=PRICE_CLOSE`
- `Ma_RSIOMA=21`
- `Ma_RSIOMA_MODE=MODE_EMA`
- `BuyTrigger=80`
- `SellTrigger=20`
- `MainTrendLong=70`
- `MainTrendShort=30`
- `MajorTrend=50`

Buffers:

| Buffer | Label | Meaning |
|---:|---|---|
| 0 | `Rsioma` | Main RSIOMA value. |
| 1 | `TrendDn` | Down-trend histogram, `-6` or `-12`. |
| 2 | `TrendUp` | Up-trend histogram, `6` or `12`. |
| 3 | `SellTrigger` | Sell/overbought trigger histogram. |
| 4 | `BuyTrigger` | Buy/oversold trigger histogram. |
| 5 | `MaRsioma` | MA of RSIOMA. |
| 6 | `Up/DnXsig` | Cross signal: `-8` for RSIOMA crossing above MA, `8` for crossing below MA. |

Hermass use: H1/M15 momentum confirmation after D1 permission is known.

## Kaufman_Bands.mq5

Role: Kaufman adaptive moving average with upper/lower deviation bands.

Inputs:

- `periodAMA=9`
- `nfast=2`
- `nslow=30`
- `G=2.0`
- `dK=2.0`
- `BollingerPeriod=20`
- `K_Bollinger=2.0`

Buffers:

| Buffer | Label | Meaning |
|---:|---|---|
| 0 | `Kaufman AMA` | Adaptive moving average. |
| 1 | `AMA Up Signal` | Up arrow when AMA slope exceeds `dK`. |
| 2 | `AMA Down Signal` | Down arrow when AMA slope exceeds `dK`. |
| 3 | `Upper Band` | AMA plus deviation band. |
| 4 | `Lower Band` | AMA minus deviation band. |

Hermass use: adaptive band context and source dependency for `ACD_Kaufman_Bandwidth616`.

## ACD_Kaufman_Bandwidth616.mq5

Role: Bandwidth contraction/expansion observer comparing Kaufman and Bollinger widths.

Dependencies: `Kaufman_Bands.mq5` must compile and be available to `iCustom`.

Inputs:

- `BBPeriod=20`, `StdDeviation=2`
- `BBPeriod1=20`, `StdDeviation1=2`
- `BBPeriod2=50`, `StdDeviation2=2`
- `BBPeriod3=50`, `StdDeviation3=2`
- alert flags are optional and should stay off in automation unless explicitly requested.

Buffers:

| Buffer | Label | Meaning |
|---:|---|---|
| 0 | `Kaufman20 Bandwidth` | `(Kaufman upper - Kaufman lower) / AMA`. |
| 1 | `BB20 Bandwidth` | Bollinger 20 bandwidth ratio. |
| 2 | `BB50 Bandwidth` | Bollinger 50 bandwidth ratio. |
| 3 | `Kaufman50 Bandwidth` | Kaufman 50 bandwidth ratio. |
| 4 | `BB20 Up (aux)` | BB20 expansion/up auxiliary line. |
| 5 | `BB20 Down (aux)` | BB20 down/expansion auxiliary line. |
| 6 | `BB50 Narrow (aux)` | Empty when BB50 is narrower than Kaufman50. |
| 7 | internal | Signal value: `1` expansion, `-1` contraction, `0` neutral. |

Hermass use: multi-timeframe bandwidth contraction, especially H1/M15 after D1 direction gating.

## ACD_1.mq5

Role: ACD opening range plus A/C trigger levels.

Buffers:

| Buffer | Label | Meaning |
|---:|---|---|
| 0 | `O/R High` | Opening range high. |
| 1 | `O/R Low` | Opening range low. |
| 2 | `A Up` | `openRangeHigh + A`. |
| 3 | `A Down` | `openRangeLow - A`. |
| 4 | `C Up` | `openRangeHigh + C`. |
| 5 | `C Down` | `openRangeLow - C`. |

Hermass use: M15/H1 breakout position context after D1 permission is known.

## ACD_2.mq5

Role: single-session pivot range, previous high/low, and pivot moving averages.

Buffers:

| Buffer | Label | Meaning |
|---:|---|---|
| 0 | `Pivot Point` | `(high + low + close) / 3`. |
| 1 | `Pivot Range Top` | Pivot range top. |
| 2 | `Pivot Range Bottom` | Pivot range bottom. |
| 3 | `Previous Day High` | Previous range high. |
| 4 | `Previous Day Low` | Previous range low. |
| 5 | `14 MA` | 14-period pivot MA. |
| 6 | `30 MA` | 30-period pivot MA. |
| 7 | `50 MA` | 50-period pivot MA. |

Hermass use: one-day pivot location and support/resistance context.

## ACD_3.mq5 and ACD_6.mq5

Role: rolling three-day and six-day pivot ranges.

Buffers:

| Buffer | Label | Meaning |
|---:|---|---|
| 0 | `Pivot Point` | Rolling pivot point. |
| 1 | `Pivot Range Top` | Rolling pivot top. |
| 2 | `Pivot Range Bottom` | Rolling pivot bottom. |
| 3 | `Pivot Range Width` | `top - bottom`. |

Hermass use: 3D/6D pivot contraction and breakout location. In reports, compare widths point-in-time and only use completed windows.

## ACD_枢轴.mq5

Role: dashboard combining 1D/3D/6D pivot ranges, contraction counts, range averages, room-up/down, and stop-distance display.

Important formulas:

- 1D pivot: high, low, close -> pivot, top, bottom, width.
- 3D pivot: rolling max high, rolling min low, close -> pivot, top, bottom, width.
- 6D pivot: rolling max high, rolling min low, close -> pivot, top, bottom, width.
- Contraction count: current width compared with the previous 31 windows.
- Alert thresholds: `alert_1s=1`, `alert_3s=2`, `alert_6s=3`, `alert_hs=8`.

Hermass use: reference implementation for 1D/3D/6D pivot contraction. Prefer structured extraction from `ACD_1/2/3/6` buffers for automated reports; use this dashboard as chart-side visual confirmation.

## Report Order

For each symbol, always report:

1. D1 MA144/MA169/MA200 structure.
2. D1 State Hex and D1 risk direction.
3. H1 indicators, including RSIOMA, Kaufman/Bollinger bandwidth, pivot/SR, ADX tiers.
4. M15 indicators, including ACD opening range, A/C levels, bandwidth, pivot/SR, ADX tiers.

H1/M15 observations may be bullish or bearish, but trade permission comes only from the D1 risk officer.
