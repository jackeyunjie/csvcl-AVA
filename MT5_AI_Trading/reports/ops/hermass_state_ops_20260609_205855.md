# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 20:58:55
- action: check
- symbols: EURUSD, GBPUSD, USDJPY, XAUUSD, US_30, US_500, US_TECH100
- status: failed

## MT5 Raw
```json
{
  "connected": true,
  "account": {
    "login": 89467841,
    "server": "Ava-Real 1-MT5",
    "balance": 162.5,
    "equity": 160.12
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 20:58:43",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 20:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 20:45:00"
      }
    },
    "GBPUSD": {
      "mt5_symbol": "GBPUSD",
      "tick_time": "2026-06-09 20:58:43",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 20:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 20:45:00"
      }
    },
    "USDJPY": {
      "mt5_symbol": "USDJPY",
      "tick_time": "2026-06-09 20:58:41",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 20:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 20:45:00"
      }
    },
    "XAUUSD": {
      "mt5_symbol": "GOLD",
      "tick_time": "2026-06-09 20:58:43",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 20:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 20:45:00"
      }
    },
    "US_30": {
      "mt5_symbol": "US_30",
      "tick_time": "2026-06-09 20:58:41",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 20:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 20:45:00"
      }
    },
    "US_500": {
      "mt5_symbol": "US_500",
      "tick_time": "2026-06-09 20:58:38",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 20:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 20:45:00"
      }
    },
    "US_TECH100": {
      "mt5_symbol": "US_TECH100",
      "tick_time": "2026-06-09 20:58:43",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 20:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 20:45:00"
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
        "rows": 3055,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-09 20:00:00",
        "date_key": "timestamp"
      },
      "GBPUSD": {
        "rows": 2964,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-04 01:00:00",
        "date_key": "timestamp"
      },
      "USDJPY": {
        "rows": 2964,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-04 01:00:00",
        "date_key": "timestamp"
      },
      "XAUUSD": {
        "rows": 2960,
        "earliest": "2025-12-02 01:00:00",
        "latest": "2026-06-05 00:00:00",
        "date_key": "timestamp"
      },
      "US_30": {
        "rows": 2982,
        "earliest": "2025-12-02 11:00:00",
        "latest": "2026-06-05 00:00:00",
        "date_key": "timestamp"
      },
      "US_500": {
        "rows": 2924,
        "earliest": "2025-12-05 00:00:00",
        "latest": "2026-06-05 00:00:00",
        "date_key": "timestamp"
      },
      "US_TECH100": {
        "rows": 2961,
        "earliest": "2025-12-02 11:00:00",
        "latest": "2026-06-05 00:00:00",
        "date_key": "timestamp"
      }
    }
  },
  "m15_state": {
    "path": "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\data\\m15_state.duckdb",
    "exists": true,
    "symbols": {
      "EURUSD": {
        "rows": 190,
        "earliest": "2026-06-07 21:00:00",
        "latest": "2026-06-09 20:15:00",
        "date_key": "timestamp"
      },
      "GBPUSD": {
        "rows": 0,
        "earliest": null,
        "latest": null,
        "date_key": "timestamp"
      },
      "USDJPY": {
        "rows": 0,
        "earliest": null,
        "latest": null,
        "date_key": "timestamp"
      },
      "XAUUSD": {
        "rows": 0,
        "earliest": null,
        "latest": null,
        "date_key": "timestamp"
      },
      "US_30": {
        "rows": 2902,
        "earliest": "2026-04-14 14:15:00",
        "latest": "2026-05-28 02:00:00",
        "date_key": "timestamp"
      },
      "US_500": {
        "rows": 2902,
        "earliest": "2026-04-14 14:00:00",
        "latest": "2026-05-28 02:00:00",
        "date_key": "timestamp"
      },
      "US_TECH100": {
        "rows": 2902,
        "earliest": "2026-04-14 13:45:00",
        "latest": "2026-05-28 02:00:00",
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
        "earliest": "2010-07-23",
        "latest": "2026-05-27",
        "date_key": "date"
      },
      "GBPUSD": {
        "rows": 4950,
        "earliest": "2010-07-23",
        "latest": "2026-05-27",
        "date_key": "date"
      },
      "USDJPY": {
        "rows": 4950,
        "earliest": "2010-07-23",
        "latest": "2026-05-27",
        "date_key": "date"
      },
      "XAUUSD": {
        "rows": 0,
        "earliest": null,
        "latest": null,
        "date_key": "date"
      },
      "US_30": {
        "rows": 0,
        "earliest": null,
        "latest": null,
        "date_key": "date"
      },
      "US_500": {
        "rows": 0,
        "earliest": null,
        "latest": null,
        "date_key": "date"
      },
      "US_TECH100": {
        "rows": 0,
        "earliest": null,
        "latest": null,
        "date_key": "date"
      }
    },
    "rows": 81322,
    "symbols": 17,
    "earliest": "2010-07-23",
    "latest": "2026-05-27",
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
  "errors": [
    "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\data\\m15_state.duckdb: INTERNAL Error: Attempted to access index 0 within vector of size 0\nThis error signals an assertion failure within DuckDB. This usually occurs due to unexpected conditions or errors in the program's logic.\nFor more information, see https://duckdb.org/docs/stable/dev/internal_errors",
    "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\data\\m15_state.duckdb: INTERNAL Error: Attempted to access index 0 within vector of size 0\nThis error signals an assertion failure within DuckDB. This usually occurs due to unexpected conditions or errors in the program's logic.\nFor more information, see https://duckdb.org/docs/stable/dev/internal_errors"
  ]
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
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
      },
      "H1": {
        "ok": true,
        "raw_latest": "2026-06-09 20:00:00",
        "db_latest": "2026-06-09 20:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 20:45:00",
        "db_latest": "2026-06-09 20:15:00",
        "lag_hours": 0.5,
        "status": "stale"
      }
    },
    "GBPUSD": {
      "D1": {
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 20:00:00",
        "db_latest": "2026-06-04 01:00:00",
        "lag_hours": 139.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 20:45:00",
        "db_latest": null,
        "lag_hours": null,
        "status": "missing"
      }
    },
    "USDJPY": {
      "D1": {
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 20:00:00",
        "db_latest": "2026-06-04 01:00:00",
        "lag_hours": 139.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 20:45:00",
        "db_latest": null,
        "lag_hours": null,
        "status": "missing"
      }
    },
    "XAUUSD": {
      "D1": {
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 20:00:00",
        "db_latest": "2026-06-05 00:00:00",
        "lag_hours": 116.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 20:45:00",
        "db_latest": null,
        "lag_hours": null,
        "status": "missing"
      }
    },
    "US_30": {
      "D1": {
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 20:00:00",
        "db_latest": "2026-06-05 00:00:00",
        "lag_hours": 116.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 20:45:00",
        "db_latest": "2026-05-28 02:00:00",
        "lag_hours": 306.75,
        "status": "stale"
      }
    },
    "US_500": {
      "D1": {
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 20:00:00",
        "db_latest": "2026-06-05 00:00:00",
        "lag_hours": 116.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 20:45:00",
        "db_latest": "2026-05-28 02:00:00",
        "lag_hours": 306.75,
        "status": "stale"
      }
    },
    "US_TECH100": {
      "D1": {
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 20:00:00",
        "db_latest": "2026-06-05 00:00:00",
        "lag_hours": 116.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 20:45:00",
        "db_latest": "2026-05-28 02:00:00",
        "lag_hours": 306.75,
        "status": "stale"
      }
    }
  }
}
```

## Contraction Watch
```json
{}
```

## Notes
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_205855.md: [WinError 5] 拒绝访问。: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass'
