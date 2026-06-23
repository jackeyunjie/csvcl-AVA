# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 22:20:17
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
    "balance": 169.24,
    "equity": 169.24
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 22:20:15",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 22:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 22:15:00"
      }
    },
    "GBPUSD": {
      "mt5_symbol": "GBPUSD",
      "tick_time": "2026-06-09 22:20:16",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 22:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 22:15:00"
      }
    },
    "USDJPY": {
      "mt5_symbol": "USDJPY",
      "tick_time": "2026-06-09 22:20:15",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 22:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 22:15:00"
      }
    },
    "XAUUSD": {
      "mt5_symbol": "GOLD",
      "tick_time": "2026-06-09 22:20:16",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 22:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 22:15:00"
      }
    },
    "US_30": {
      "mt5_symbol": "US_30",
      "tick_time": "2026-06-09 22:20:15",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 22:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 22:15:00"
      }
    },
    "US_500": {
      "mt5_symbol": "US_500",
      "tick_time": "2026-06-09 22:20:16",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 22:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 22:15:00"
      }
    },
    "US_TECH100": {
      "mt5_symbol": "US_TECH100",
      "tick_time": "2026-06-09 22:20:16",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 22:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 22:15:00"
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
        "rows": 3056,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-09 21:00:00",
        "date_key": "timestamp"
      },
      "GBPUSD": {
        "rows": 3055,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-09 21:00:00",
        "date_key": "timestamp"
      },
      "USDJPY": {
        "rows": 3055,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-09 21:00:00",
        "date_key": "timestamp"
      },
      "XAUUSD": {
        "rows": 3048,
        "earliest": "2025-12-02 01:00:00",
        "latest": "2026-06-09 21:00:00",
        "date_key": "timestamp"
      },
      "US_30": {
        "rows": 3049,
        "earliest": "2025-12-02 11:00:00",
        "latest": "2026-06-09 21:00:00",
        "date_key": "timestamp"
      },
      "US_500": {
        "rows": 2991,
        "earliest": "2025-12-05 00:00:00",
        "latest": "2026-06-09 21:00:00",
        "date_key": "timestamp"
      },
      "US_TECH100": {
        "rows": 3049,
        "earliest": "2025-12-02 11:00:00",
        "latest": "2026-06-09 21:00:00",
        "date_key": "timestamp"
      }
    }
  },
  "m15_state": {
    "path": "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\data\\m15_state.duckdb",
    "exists": true,
    "symbols": {
      "EURUSD": {
        "rows": 2115,
        "earliest": "2026-05-11 05:00:00",
        "latest": "2026-06-09 21:30:00",
        "date_key": "timestamp"
      },
      "GBPUSD": {
        "rows": 2083,
        "earliest": "2026-05-11 05:00:00",
        "latest": "2026-06-09 21:30:00",
        "date_key": "timestamp"
      },
      "USDJPY": {
        "rows": 2083,
        "earliest": "2026-05-11 05:00:00",
        "latest": "2026-06-09 21:30:00",
        "date_key": "timestamp"
      },
      "XAUUSD": {
        "rows": 1985,
        "earliest": "2026-05-11 06:00:00",
        "latest": "2026-06-09 21:30:00",
        "date_key": "timestamp"
      },
      "US_30": {
        "rows": 3825,
        "earliest": "2026-04-14 14:15:00",
        "latest": "2026-06-09 21:30:00",
        "date_key": "timestamp"
      },
      "US_500": {
        "rows": 3825,
        "earliest": "2026-04-14 14:00:00",
        "latest": "2026-06-09 21:30:00",
        "date_key": "timestamp"
      },
      "US_TECH100": {
        "rows": 3825,
        "earliest": "2026-04-14 13:45:00",
        "latest": "2026-06-09 21:30:00",
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
      },
      "GBPUSD": {
        "rows": 4950,
        "earliest": "2010-08-05",
        "latest": "2026-06-09",
        "date_key": "date"
      },
      "USDJPY": {
        "rows": 4950,
        "earliest": "2010-08-05",
        "latest": "2026-06-09",
        "date_key": "date"
      },
      "XAUUSD": {
        "rows": 4950,
        "earliest": "2010-06-17",
        "latest": "2026-06-09",
        "date_key": "date"
      },
      "US_30": {
        "rows": 4729,
        "earliest": "2011-03-18",
        "latest": "2026-06-09",
        "date_key": "date"
      },
      "US_500": {
        "rows": 4729,
        "earliest": "2011-03-18",
        "latest": "2026-06-09",
        "date_key": "date"
      },
      "US_TECH100": {
        "rows": 4440,
        "earliest": "2012-02-26",
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
        "ok": true,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-06-09",
        "lag_hours": 8.0,
        "status": "fresh"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 22:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 22:15:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 0.75,
        "status": "stale"
      }
    },
    "GBPUSD": {
      "D1": {
        "ok": true,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-06-09",
        "lag_hours": 8.0,
        "status": "fresh"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 22:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 22:15:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 0.75,
        "status": "stale"
      }
    },
    "USDJPY": {
      "D1": {
        "ok": true,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-06-09",
        "lag_hours": 8.0,
        "status": "fresh"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 22:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 22:15:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 0.75,
        "status": "stale"
      }
    },
    "XAUUSD": {
      "D1": {
        "ok": true,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-06-09",
        "lag_hours": 8.0,
        "status": "fresh"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 22:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 22:15:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 0.75,
        "status": "stale"
      }
    },
    "US_30": {
      "D1": {
        "ok": true,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-06-09",
        "lag_hours": 8.0,
        "status": "fresh"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 22:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 22:15:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 0.75,
        "status": "stale"
      }
    },
    "US_500": {
      "D1": {
        "ok": true,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-06-09",
        "lag_hours": 8.0,
        "status": "fresh"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 22:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 22:15:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 0.75,
        "status": "stale"
      }
    },
    "US_TECH100": {
      "D1": {
        "ok": true,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-06-09",
        "lag_hours": 8.0,
        "status": "fresh"
      },
      "H1": {
        "ok": false,
        "raw_latest": "2026-06-09 22:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 22:15:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 0.75,
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
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_222017.md: [Errno 13] Permission denied: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass\\Reports\\hermass_state_ops_20260609_222017.md'
