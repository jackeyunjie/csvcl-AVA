# SQX Natural Language to MT5 EA Workflow

Date: 2026-06-09

## Answer

Yes, natural language can organize SQX-style modules and generate an MT5 EA, but it should not generate a live-trading EA directly.

The safe path is:

1. Natural language strategy brief.
2. Structured strategy DSL / manifest.
3. SQX block mapping and custom-indicator references.
4. Signal-only MT5 observer EA or indicator.
5. Backtest and paper observation.
6. Risk-gated execution only after manual approval.

## Hermass Contraction Brief

Current observation requirements:

- D1/H1/M15 viewpoint separation.
- Per-symbol D1-first order: D1 MA144/169/200, then D1 State Hex/risk direction, then H1/M15 indicators.
- Multi-timeframe SR support/resistance contraction.
- 1D/3D/6D pivot contraction.
- Multi-timeframe Bollinger Band width contraction.
- ADX tiers `<20`, `<13`, `<9`.

SQX references verified under `D:\SQX136\custom_indicators\MetaTrader5\Indicators`:

- `SqSRPercentRank.mq5`
- `SqPivots.mq5`
- `SqBBWidthRatio.mq5`
- `SqADX.mq5`

Local MT5 indicator pack under `D:\qoder\csvcl - AVA\MT5\Indicators`:

- `RSIOMA_v2HHLSX.mq5`
- `Kaufman_Bands.mq5`
- `ACD_Kaufman_Bandwidth616.mq5`
- `ACD_枢轴.mq5`
- `ACD_6.mq5`
- `ACD_3.mq5`
- `ACD_2.mq5`
- `ACD_1.mq5`

## DSL Shape

```yaml
strategy_id: hermass_contraction_observer_v1
mode: observer_only
symbols:
  - EURUSD
  - GBPUSD
  - USDJPY
  - XAUUSD
  - US_30
  - US_500
  - US_TECH100
timeframes:
  signal: M15
  context:
    - H1
    - D1
features:
  d1_first:
    ma_structure:
      timeframe: D1
      periods: [144, 169, 200]
    state_hex:
      source: hermass_state
      risk_gate: d1_risk_officer
  sr_contraction:
    source: SqSRPercentRank
    timeframes: [M15, H1, D1]
  pivots:
    source: [SqPivots, ACD_1, ACD_2, ACD_3, ACD_6, ACD_枢轴]
    windows: [1D, 3D, 6D]
  bb_width:
    source: [SqBBWidthRatio, ACD_Kaufman_Bandwidth616]
    timeframes: [M15, H1, D1]
  adx:
    source: SqADX
    tiers: [20, 13, 9]
  momentum:
    source: RSIOMA_v2HHLSX
    buffers: [Rsioma, TrendUp, TrendDn, BuyTrigger, SellTrigger, MaRsioma, Up/DnXsig]
  adaptive_bands:
    source: Kaufman_Bands
    buffers: [Kaufman AMA, AMA Up Signal, AMA Down Signal, Upper Band, Lower Band]
outputs:
  - chart_comment
  - file_report
  - alert
risk_gate:
  live_orders: false
  requires_manual_approval: true
```

## Module Mapping

| DSL field | SQX / MT5 target | Notes |
|---|---|---|
| `sr_contraction` | `SqSRPercentRank.mq5` plus Hermass SR state | Use as observer metric first. |
| `pivots.windows` | `SqPivots.mq5`, `ACD_1/2/3/6`, `ACD_枢轴.mq5` | Compare 1D/3D/6D pivot ranges without future bars. |
| `bb_width` | `SqBBWidthRatio.mq5`, `ACD_Kaufman_Bandwidth616.mq5` | Report multi-timeframe percentile/rank, not a trade trigger by itself. |
| `adx.tiers` | `SqADX.mq5` | Tier labels: quiet `<20`, compressed `<13`, extreme `<9`. |
| `momentum` | `RSIOMA_v2HHLSX.mq5` | Use only after D1 direction permission is known. |
| `adaptive_bands` | `Kaufman_Bands.mq5` | Also a required dependency for ACD Kaufman bandwidth. |
| `mode: observer_only` | MT5 indicator or EA with no `OrderSend` | First implementation must be signal/report only. |

## Acceptance Gates

Before any EA is allowed to trade:

1. MQL5 compiles without warnings that affect execution.
2. Strategy Tester passes on fixed symbols and time windows.
3. Point-in-time checks prove no forming higher-timeframe bar leaks into lower-timeframe decisions.
4. Spread, commission, slippage, session hours, and broker symbol mapping are explicit.
5. Each run emits a run card with config hash, symbol set, timeframe set, and data timestamp.
6. At least four weeks of paper observation are reviewed.
7. Manual approval enables any live order path.

## Prohibited In Phase 2

- Free-form LLM generation of live `OrderSend` logic.
- Direct natural-language changes to lot size, leverage, stop loss, or take profit without a typed config diff.
- Reusing current forming D1/H1 bars as closed context.
- Enabling auto-trading from n8n, Coze, Dify, Agently, TradingAgents-CN, Vibe-Trading, or agentmemory.

## Implementation Steps

1. Write `config/strategies/hermass_contraction_observer_v1.yaml`.
2. Generate a deterministic MQL5 observer template from the YAML.
3. Load it in MT5 as an indicator or EA with `live_orders=false`.
4. Compare its chart/report output with `hermass_state_ops.py check`.
5. Add paper-trading bridge only after the observer has stable agreement.
