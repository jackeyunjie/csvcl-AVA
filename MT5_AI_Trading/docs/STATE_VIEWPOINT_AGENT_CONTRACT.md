# State Viewpoint Agent Contract

This document is the project-level contract for State architecture. Use it to resolve wording or implementation disputes in docs, scripts, prompts, and strategy code.

## Core Principle

Timeframe and viewpoint are independent dimensions.

```text
structure_tf = where structure comes from
view_tf      = which observer price timestamps the calculation
state_hex    = structure_tf state under view_tf
```

Examples:

```text
D1_state_under_H1_view != D1_state_under_D1_view
W1_state_under_D1_view != W1_state_under_W1_view
```

The only State component that changes with viewpoint is `position`.

```text
base/trend/volatility = computed from structure_tf OHLCV
position              = view_tf close vs structure_tf SR
timestamp             = view_tf timestamp
```

## Viewpoint Agents

Each viewpoint is an independent Agent. An Agent contains timestamp-aligned states for its own timeframe and all higher structure timeframes needed for global context.

```text
MN1 Agent:
  MN1@MN1_view

W1 Agent:
  MN1@W1_view, W1@W1_view

D1 Agent:
  MN1@D1_view, W1@D1_view, D1@D1_view

H4 Agent:
  MN1@H4_view, W1@H4_view, D1@H4_view, H4@H4_view

H1 Agent:
  MN1@H1_view, W1@H1_view, D1@H1_view, H4@H1_view, H1@H1_view

M30 Agent:
  MN1/W1/D1/H4/H1/M30 @ M30_view

M15 Agent:
  MN1/W1/D1/H4/H1/M30/M15 @ M15_view
```

An independent Agent is not a bundle of native states from different timeframe views. It is one viewpoint system with one shared `view_tf` close for all `position` calculations.

## H1 Agent

The H1 Agent is a complete intraday global observer:

```text
timestamp = H1 bar timestamp
view_price = H1 close

MN1@H1_view: MN1 structure + H1 close vs MN1 SR
W1@H1_view:  W1  structure + H1 close vs W1 SR
D1@H1_view:  D1  structure + H1 close vs D1 SR
H4@H1_view:  H4  structure + H1 close vs H4 SR
H1@H1_view:  H1  structure + H1 close vs H1 SR
```

## M15 Agent

M15 is a separate viewpoint Agent, not just one more column. It changes the observation clock and the `position` base price for every structure timeframe.

```text
timestamp = M15 bar timestamp
view_price = M15 close
```

Because this raises frequency, noise, data volume, and execution cost, M15 should remain an optional short-term/scalping research branch unless strategy evidence justifies promoting it.

## Naming Rules

Prefer explicit names when designing new tables or APIs:

```text
view_tf
structure_tf
state_hex
```

Existing wide-table columns such as `d1_hex` inside `h1_state_snapshot` must be read as:

```text
d1_hex = D1 structure state under the table's viewpoint Agent
```

For `h1_state_snapshot`, the intended meaning is `D1@H1_view`, not native `D1@D1_view`.

## Implementation Rule

For a row in any viewpoint Agent table:

```text
for each structure_tf <= view context:
    base/trend/volatility use structure_tf OHLCV
    position uses view_tf close vs structure_tf SR
```

Any implementation that computes each structure timeframe with its own close and then merely aligns those native states to a lower timestamp is not compliant with this contract.

