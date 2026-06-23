# Hermass MT5 State Ops Report

- generated_at: 2026-06-10 10:29:56
- action: check
- symbols: EURUSD
- status: failed

## MT5 Raw
```json
{
  "connected": true,
  "account": {
    "login": 89467841,
    "server": "Ava-Real 1-MT5",
    "balance": 101.92,
    "equity": 101.92
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-10 10:29:54",
      "D1": {
        "rows": 5,
        "latest": "2026-06-10 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-10 10:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-10 10:15:00"
      }
    }
  },
  "error": null
}
```

## DuckDB
```json
{
  "h1_state": {
    "path": "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\data\\h1_state.duckdb",
    "exists": true,
    "symbols": {
      "EURUSD": {
        "rows": 3057,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-09 22:00:00",
        "date_key": "timestamp"
      }
    }
  },
  "m15_state": {
    "path": "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\data\\m15_state.duckdb",
    "exists": true,
    "symbols": {
      "EURUSD": {
        "rows": 2121,
        "earliest": "2026-05-11 05:00:00",
        "latest": "2026-06-09 23:00:00",
        "date_key": "timestamp"
      }
    }
  },
  "d1_hermass": {
    "path": "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\data\\hermass_state.db",
    "exists": true,
    "by_symbol": {
      "EURUSD": {
        "rows": 4950,
        "earliest": "2010-08-05",
        "latest": "2026-06-09",
        "date_key": "date"
      }
    },
    "rows": 33698,
    "symbols": 7,
    "earliest": "2010-06-17",
    "latest": "2026-06-09",
    "date_key": "date"
  },
  "h1_hermass": {
    "path": "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\data\\hermass_h1_state.db",
    "exists": true,
    "rows": 1400000,
    "symbols": 14,
    "earliest": "2010-05-05 14:00:00",
    "latest": "2026-05-28 18:00:00",
    "date_key": "timestamp"
  },
  "errors": []
}
```

## Freshness
```json
{
  "ok": false,
  "policy": {
    "D1": "DB date must match raw D1 calendar date.",
    "H1": "DB timestamp must be no earlier than raw H1 latest.",
    "M15": "DB timestamp must be no earlier than raw M15 latest."
  },
  "symbols": {
    "EURUSD": {
      "D1": {
        "ok": false,
        "raw_latest": "2026-06-10 08:00:00",
        "db_latest": "2026-06-09",
        "lag_hours": 32.0,
        "status": "stale"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-10 10:00:00",
        "db_latest": "2026-06-09 22:00:00",
        "lag_hours": 12.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-10 10:15:00",
        "db_latest": "2026-06-09 23:00:00",
        "lag_hours": 11.25,
        "status": "stale"
      }
    }
  }
}
```

## D1 First Symbol Analysis
```json
{
  "status": "ok",
  "policy": {
    "analysis_order": [
      "D1 MA144/MA169/MA200 structure",
      "D1 State Hex and D1 risk direction",
      "H1 indicators only after D1 context",
      "M15 indicators only after D1 context"
    ],
    "risk_gate": "H1/M15 directional trades must align with D1; neutral/unknown D1 is observe-only.",
    "state_source": "Prefer latest H1-view d1_hex for lower-timeframe risk gating; fall back to native D1 state."
  },
  "symbols": {
    "EURUSD": {
      "d1_ma_144_169_200": {
        "status": "ok",
        "rows": 260,
        "latest": "2026-06-10 08:00:00",
        "close": 1.15425,
        "ma144": 1.1690046527777778,
        "ma169": 1.168934852071006,
        "ma200": 1.1671118,
        "close_vs_ma144": "below",
        "close_vs_ma169": "below",
        "close_vs_ma200": "below",
        "ma_relation": "bullish_alignment",
        "structure": "mixed_or_transition"
      },
      "d1_state_hex": {
        "risk_hex": "-4",
        "risk_hex_source": "h1_state_snapshot.d1_hex",
        "risk_direction": "short",
        "lower_timeframe_permission": "short_only",
        "native_d1": {
          "date": "2026-06-09",
          "mn1_hex": "-1",
          "w1_hex": "-2",
          "d1_hex": "-F",
          "mn1_score": -1,
          "w1_score": -2,
          "d1_score": -15,
          "ef_count": 0
        },
        "h1_view_d1": {
          "timestamp": "2026-06-09 22:00:00",
          "d1_hex": "-4",
          "h1_hex": "C",
          "d1_duration": 0,
          "h1_duration": 2
        }
      },
      "h1_after_d1": {
        "state": {
          "timestamp": "2026-06-09 22:00:00",
          "d1_hex": "-4",
          "h1_hex": "C",
          "d1_duration": 0,
          "h1_duration": 2
        },
        "indicators": {
          "status": "missing"
        }
      },
      "m15_after_d1": {
        "state": {
          "timestamp": "2026-06-09 23:00:00",
          "d1_hex": "-5",
          "h1_hex": "0",
          "m15_hex": "-0",
          "d1_duration": 0,
          "h1_duration": 0,
          "m15_duration": 0,
          "sr_breakout": false,
          "breakout_direction": "none",
          "breakout_tf": ""
        },
        "indicators": {
          "status": "missing"
        }
      },
      "d1_contraction_context": {
        "status": "missing"
      }
    }
  },
  "errors": []
}
```

## Contraction Watch
```json
{}
```

## Table Exports
- local csv: D:\qoder\csvcl - AVA\MT5_AI_Trading\reports\ops\tables\hermass_state_table_20260610_102956.csv (1 rows)
- local markdown: D:\qoder\csvcl - AVA\MT5_AI_Trading\reports\ops\tables\hermass_state_table_20260610_102956.md (1 rows)
- obsidian csv: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Tables\hermass_state_table_20260610_102956.csv (1 rows)
- obsidian markdown: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Tables\hermass_state_table_20260610_102956.md (1 rows)
