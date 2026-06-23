# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 23:00:05
- action: update-h1
- symbols: EURUSD, GBPUSD, USDJPY, XAUUSD, US_30, US_500, US_TECH100
- status: ok

## MT5 Raw
```json
{
  "connected": true,
  "account": {
    "login": 89467841,
    "server": "Ava-Real 1-MT5",
    "balance": 124.31,
    "equity": 127.67
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 23:00:04",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      }
    },
    "GBPUSD": {
      "mt5_symbol": "GBPUSD",
      "tick_time": "2026-06-09 23:00:04",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      }
    },
    "USDJPY": {
      "mt5_symbol": "USDJPY",
      "tick_time": "2026-06-09 23:00:04",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      }
    },
    "XAUUSD": {
      "mt5_symbol": "GOLD",
      "tick_time": "2026-06-09 23:00:05",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      }
    },
    "US_30": {
      "mt5_symbol": "US_30",
      "tick_time": "2026-06-09 23:00:04",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      }
    },
    "US_500": {
      "mt5_symbol": "US_500",
      "tick_time": "2026-06-09 23:00:04",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      }
    },
    "US_TECH100": {
      "mt5_symbol": "US_TECH100",
      "tick_time": "2026-06-09 23:00:05",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 23:00:00"
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
      },
      "GBPUSD": {
        "rows": 3056,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-09 22:00:00",
        "date_key": "timestamp"
      },
      "USDJPY": {
        "rows": 3056,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-09 22:00:00",
        "date_key": "timestamp"
      },
      "XAUUSD": {
        "rows": 3049,
        "earliest": "2025-12-02 01:00:00",
        "latest": "2026-06-09 22:00:00",
        "date_key": "timestamp"
      },
      "US_30": {
        "rows": 3050,
        "earliest": "2025-12-02 11:00:00",
        "latest": "2026-06-09 22:00:00",
        "date_key": "timestamp"
      },
      "US_500": {
        "rows": 2992,
        "earliest": "2025-12-05 00:00:00",
        "latest": "2026-06-09 22:00:00",
        "date_key": "timestamp"
      },
      "US_TECH100": {
        "rows": 3051,
        "earliest": "2025-12-02 11:00:00",
        "latest": "2026-06-09 23:00:00",
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
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 22:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 1.5,
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
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 22:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 1.5,
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
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 22:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 1.5,
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
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 22:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 1.5,
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
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 22:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 1.5,
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
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 22:00:00",
        "lag_hours": 1.0,
        "status": "stale"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 1.5,
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
        "ok": true,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 23:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 21:30:00",
        "lag_hours": 1.5,
        "status": "stale"
      }
    }
  }
}
```

## Acceptance
```json
{
  "ok": true,
  "command_ok": true,
  "target_timeframes": [
    "H1"
  ],
  "policy": "Update actions are accepted against MT5 raw latest bars captured before the command starts. The check action remains strict against current MT5 raw latest bars.",
  "target_mt5_raw": {
    "connected": true,
    "account": {
      "login": 89467841,
      "server": "Ava-Real 1-MT5",
      "balance": 124.31,
      "equity": 125.02
    },
    "symbols": {
      "EURUSD": {
        "mt5_symbol": "EURUSD",
        "tick_time": "2026-06-09 22:59:32",
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
          "latest": "2026-06-09 22:45:00"
        }
      },
      "GBPUSD": {
        "mt5_symbol": "GBPUSD",
        "tick_time": "2026-06-09 22:59:34",
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
          "latest": "2026-06-09 22:45:00"
        }
      },
      "USDJPY": {
        "mt5_symbol": "USDJPY",
        "tick_time": "2026-06-09 22:59:34",
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
          "latest": "2026-06-09 22:45:00"
        }
      },
      "XAUUSD": {
        "mt5_symbol": "GOLD",
        "tick_time": "2026-06-09 22:59:34",
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
          "latest": "2026-06-09 22:45:00"
        }
      },
      "US_30": {
        "mt5_symbol": "US_30",
        "tick_time": "2026-06-09 22:59:34",
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
          "latest": "2026-06-09 22:45:00"
        }
      },
      "US_500": {
        "mt5_symbol": "US_500",
        "tick_time": "2026-06-09 22:59:34",
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
          "latest": "2026-06-09 22:45:00"
        }
      },
      "US_TECH100": {
        "mt5_symbol": "US_TECH100",
        "tick_time": "2026-06-09 22:59:34",
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
          "latest": "2026-06-09 22:45:00"
        }
      }
    },
    "error": null
  },
  "target_freshness": {
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
          "ok": true,
          "raw_latest": "2026-06-09 22:00:00",
          "db_latest": "2026-06-09 22:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
        },
        "M15": {
          "ok": false,
          "raw_latest": "2026-06-09 22:45:00",
          "db_latest": "2026-06-09 21:30:00",
          "lag_hours": 1.25,
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
          "ok": true,
          "raw_latest": "2026-06-09 22:00:00",
          "db_latest": "2026-06-09 22:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
        },
        "M15": {
          "ok": false,
          "raw_latest": "2026-06-09 22:45:00",
          "db_latest": "2026-06-09 21:30:00",
          "lag_hours": 1.25,
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
          "ok": true,
          "raw_latest": "2026-06-09 22:00:00",
          "db_latest": "2026-06-09 22:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
        },
        "M15": {
          "ok": false,
          "raw_latest": "2026-06-09 22:45:00",
          "db_latest": "2026-06-09 21:30:00",
          "lag_hours": 1.25,
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
          "ok": true,
          "raw_latest": "2026-06-09 22:00:00",
          "db_latest": "2026-06-09 22:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
        },
        "M15": {
          "ok": false,
          "raw_latest": "2026-06-09 22:45:00",
          "db_latest": "2026-06-09 21:30:00",
          "lag_hours": 1.25,
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
          "ok": true,
          "raw_latest": "2026-06-09 22:00:00",
          "db_latest": "2026-06-09 22:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
        },
        "M15": {
          "ok": false,
          "raw_latest": "2026-06-09 22:45:00",
          "db_latest": "2026-06-09 21:30:00",
          "lag_hours": 1.25,
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
          "ok": true,
          "raw_latest": "2026-06-09 22:00:00",
          "db_latest": "2026-06-09 22:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
        },
        "M15": {
          "ok": false,
          "raw_latest": "2026-06-09 22:45:00",
          "db_latest": "2026-06-09 21:30:00",
          "lag_hours": 1.25,
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
          "ok": true,
          "raw_latest": "2026-06-09 22:00:00",
          "db_latest": "2026-06-09 23:00:00",
          "lag_hours": -1.0,
          "status": "fresh"
        },
        "M15": {
          "ok": false,
          "raw_latest": "2026-06-09 22:45:00",
          "db_latest": "2026-06-09 21:30:00",
          "lag_hours": 1.25,
          "status": "stale"
        }
      }
    }
  }
}
```

## Contraction Watch
```json
{}
```

## Commands

```text
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe build_h1_state_real.py --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 120
returncode=0
: 19,
      "3": 17,
      "A": 8,
      "9": 5
    },
    "h1_hex": {
      "F": 355,
      "-F": 338,
      "6": 337,
      "E": 224,
      "4": 183,
      "-E": 179,
      "-4": 174,
      "-D": 153,
      "D": 151,
      "-6": 136,
      "8": 104,
      "7": 88,
      "0": 72,
      "-C": 72,
      "-5": 71,
      "-7": 59,
      "C": 51,
      "2": 42,
      "1": 42,
      "B": 38,
      "9": 30,
      "5": 29,
      "-B": 28,
      "-3": 23,
      "-2": 21,
      "-A": 21,
      "A": 16,
      "3": 13
    }
  }
}

==================================================
US_500 State ���ݿ�ժҪ:
{
  "symbol": "US_500",
  "total_rows": 2992,
  "earliest": "2025-12-05 00:00:00",
  "latest": "2026-06-09 22:00:00",
  "hex_distributions": {
    "mn1_hex": {
      "2": 2087,
      "6": 897,
      "0": 8
    },
    "w1_hex": {
      "2": 895,
      "F": 575,
      "0": 469,
      "6": 371,
      "7": 265,
      "-4": 124,
      "-5": 120,
      "-6": 99,
      "-2": 74
    },
    "d1_hex": {
      "8": 1181,
      "6": 446,
      "E": 410,
      "1": 247,
      "-C": 161,
      "-3": 158,
      "C": 81,
      "2": 69,
      "-E": 47,
      "A": 38,
      "9": 23,
      "D": 23,
      "0": 23,
      "-A": 20,
      "-F": 15,
      "4": 14,
      "-7": 13,
      "-5": 11,
      "-D": 8,
      "-6": 2,
      "3": 2
    },
    "h4_hex": {
      "8": 440,
      "6": 406,
      "-F": 362,
      "F": 267,
      "-D": 242,
      "E": 225,
      "-4": 119,
      "7": 116,
      "2": 95,
      "4": 86,
      "D": 80,
      "1": 63,
      "9": 57,
      "B": 47,
      "-C": 45,
      "-5": 43,
      "C": 43,
      "-E": 41,
      "3": 41,
      "-6": 37,
      "-7": 27,
      "-3": 26,
      "A": 24,
      "5": 22,
      "0": 16,
      "-A": 14,
      "-B": 8
    },
    "h1_hex": {
      "6": 421,
      "-F": 354,
      "F": 267,
      "E": 264,
      "-D": 249,
      "-4": 200,
      "4": 139,
      "-E": 118,
      "D": 109,
      "8": 101,
      "0": 96,
      "-6": 90,
      "-C": 71,
      "-5": 64,
      "1": 64,
      "2": 57,
      "9": 45,
      "C": 43,
      "7": 43,
      "3": 38,
      "-B": 32,
      "5": 24,
      "-2": 23,
      "-3": 20,
      "B": 19,
      "-7": 15,
      "A": 14,
      "-A": 12
    }
  }
}

==================================================
US_TECH100 State ���ݿ�ժҪ:
{
  "symbol": "US_TECH100",
  "total_rows": 3051,
  "earliest": "2025-12-02 11:00:00",
  "latest": "2026-06-09 23:00:00",
  "hex_distributions": {
    "mn1_hex": {
      "6": 1411,
      "2": 883,
      "A": 479,
      "E": 154,
      "0": 124
    },
    "w1_hex": {
      "6": 645,
      "0": 588,
      "2": 485,
      "E": 460,
      "-4": 409,
      "-6": 196,
      "F": 156,
      "4": 66,
      "-2": 46
    },
    "d1_hex": {
      "8": 1193,
      "E": 710,
      "6": 206,
      "1": 147,
      "-C": 126,
      "0": 104,
      "C": 99,
      "9": 81,
      "-A": 81,
      "2": 71,
      "-B": 46,
      "A": 46,
      "-3": 33,
      "4": 27,
      "-2": 19,
      "D": 15,
      "3": 14,
      "-E": 12,
      "B": 9,
      "F": 8,
      "-6": 4
    },
    "h4_hex": {
      "8": 487,
      "6": 367,
      "-F": 343,
      "E": 285,
      "F": 258,
      "-D": 199,
      "7": 131,
      "2": 117,
      "-4": 103,
      "9": 79,
      "D": 78,
      "A": 69,
      "-5": 63,
      "-E": 52,
      "4": 51,
      "B": 51,
      "1": 49,
      "C": 48,
      "-B": 46,
      "-7": 38,
      "-C": 31,
      "3": 31,
      "5": 23,
      "-6": 20,
      "-A": 12,
      "0": 11,
      "-3": 9
    },
    "h1_hex": {
      "6": 395,
      "-F": 364,
      "E": 315,
      "F": 252,
      "-D": 238,
      "-4": 177,
      "-E": 129,
      "8": 107,
      "4": 99,
      "D": 93,
      "0": 85,
      "-6": 81,
      "1": 80,
      "-C": 76,
      "2": 76,
      "7": 71,
      "C": 51,
      "-5": 50,
      "3": 49,
      "9": 47,
      "B": 47,
      "5": 30,
      "-7": 28,
      "A": 27,
      "-2": 24,
      "-B": 23,
      "-3": 19,
      "-A": 18
    }
  }
}
26-06-09 22:59:47,356 [INFO] StateHexEngine��ʼ�����
2026-06-09 22:59:47,789 [INFO] MN1@view: ������� 2880 �� state_hex
2026-06-09 22:59:47,973 [INFO] W1@view: ������� 2880 �� state_hex
2026-06-09 22:59:48,073 [INFO] D1@view: ������� 1921 �� state_hex
2026-06-09 22:59:48,569 [INFO] H4@view: ������� 2588 �� state_hex
2026-06-09 22:59:50,301 [INFO] H1@view: ������� 2861 �� state_hex
2026-06-09 22:59:50,311 [INFO] ��Ԫ�������� | ��2880��
2026-06-09 22:59:50,311 [INFO]   ��Ԫ��: 2880 ��
2026-06-09 22:59:51,471 [INFO] [XAUUSD] ���� 2880 ����Ԫ��
2026-06-09 22:59:51,472 [INFO]   �ѱ���: 2880 ��
2026-06-09 22:59:51,472 [INFO] 
==================================================
2026-06-09 22:59:51,472 [INFO] ���� US_30 (120��)
2026-06-09 22:59:51,472 [INFO] ==================================================
2026-06-09 22:59:51,525 [INFO]   MN1: 60 ��
2026-06-09 22:59:51,525 [INFO]   W1: 260 ��
2026-06-09 22:59:51,525 [INFO]   D1: 120 ��
2026-06-09 22:59:51,525 [INFO]   H4: 720 ��
2026-06-09 22:59:51,525 [INFO]   H1: 2880 ��
2026-06-09 22:59:51,525 [INFO] StateHexEncoder��ʼ�����
2026-06-09 22:59:51,525 [INFO] StateHexEngine��ʼ�����
2026-06-09 22:59:51,792 [INFO] MN1@view: ������� 2880 �� state_hex
2026-06-09 22:59:51,952 [INFO] W1@view: ������� 2880 �� state_hex
2026-06-09 22:59:52,035 [INFO] D1@view: ������� 1910 �� state_hex
2026-06-09 22:59:52,607 [INFO] H4@view: ������� 2584 �� state_hex
2026-06-09 22:59:54,471 [INFO] H1@view: ������� 2861 �� state_hex
2026-06-09 22:59:54,479 [INFO] ��Ԫ�������� | ��2880��
2026-06-09 22:59:54,480 [INFO]   ��Ԫ��: 2880 ��
2026-06-09 22:59:55,626 [INFO] [US_30] ���� 2880 ����Ԫ��
2026-06-09 22:59:55,627 [INFO]   �ѱ���: 2880 ��
2026-06-09 22:59:55,627 [INFO] 
==================================================
2026-06-09 22:59:55,627 [INFO] ���� US_500 (120��)
2026-06-09 22:59:55,627 [INFO] ==================================================
2026-06-09 22:59:55,671 [INFO]   MN1: 60 ��
2026-06-09 22:59:55,671 [INFO]   W1: 260 ��
2026-06-09 22:59:55,671 [INFO]   D1: 120 ��
2026-06-09 22:59:55,671 [INFO]   H4: 720 ��
2026-06-09 22:59:55,671 [INFO]   H1: 2880 ��
2026-06-09 22:59:55,671 [INFO] StateHexEncoder��ʼ�����
2026-06-09 22:59:55,671 [INFO] StateHexEngine��ʼ�����
2026-06-09 22:59:55,935 [INFO] MN1@view: ������� 2880 �� state_hex
2026-06-09 22:59:56,103 [INFO] W1@view: ������� 2880 �� state_hex
2026-06-09 22:59:56,178 [INFO] D1@view: ������� 1910 �� state_hex
2026-06-09 22:59:56,634 [INFO] H4@view: ������� 2584 �� state_hex
2026-06-09 22:59:58,670 [INFO] H1@view: ������� 2861 �� state_hex
2026-06-09 22:59:58,677 [INFO] ��Ԫ�������� | ��2880��
2026-06-09 22:59:58,678 [INFO]   ��Ԫ��: 2880 ��
2026-06-09 22:59:59,914 [INFO] [US_500] ���� 2880 ����Ԫ��
2026-06-09 22:59:59,915 [INFO]   �ѱ���: 2880 ��
2026-06-09 22:59:59,915 [INFO] 
==================================================
2026-06-09 22:59:59,915 [INFO] ���� US_TECH100 (120��)
2026-06-09 22:59:59,915 [INFO] ==================================================
2026-06-09 22:59:59,967 [INFO]   MN1: 60 ��
2026-06-09 22:59:59,967 [INFO]   W1: 260 ��
2026-06-09 22:59:59,967 [INFO]   D1: 120 ��
2026-06-09 22:59:59,967 [INFO]   H4: 720 ��
2026-06-09 22:59:59,967 [INFO]   H1: 2880 ��
2026-06-09 22:59:59,967 [INFO] StateHexEncoder��ʼ�����
2026-06-09 22:59:59,967 [INFO] StateHexEngine��ʼ�����
2026-06-09 23:00:00,255 [INFO] MN1@view: ������� 2880 �� state_hex
2026-06-09 23:00:00,422 [INFO] W1@view: ������� 2880 �� state_hex
2026-06-09 23:00:00,497 [INFO] D1@view: ������� 1911 �� state_hex
2026-06-09 23:00:00,951 [INFO] H4@view: ������� 2585 �� state_hex
2026-06-09 23:00:02,673 [INFO] H1@view: ������� 2861 �� state_hex
2026-06-09 23:00:02,704 [INFO] ��Ԫ�������� | ��2880��
2026-06-09 23:00:02,705 [INFO]   ��Ԫ��: 2880 ��
2026-06-09 23:00:03,958 [INFO] [US_TECH100] ���� 2880 ����Ԫ��
2026-06-09 23:00:03,959 [INFO]   �ѱ���: 2880 ��
2026-06-09 23:00:04,025 [INFO] MT5�����Ž����ѶϿ�
2026-06-09 23:00:04,025 [INFO] 
������ɣ�
2026-06-09 23:00:04,050 [INFO] h1_state_snapshot ����ʼ�����
```
