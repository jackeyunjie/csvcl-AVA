# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 23:10:57
- action: update-m15
- symbols: EURUSD, GBPUSD, USDJPY, XAUUSD, US_30, US_500, US_TECH100
- status: ok

## MT5 Raw
```json
{
  "connected": true,
  "account": {
    "login": 89467841,
    "server": "Ava-Real 1-MT5",
    "balance": 124.1,
    "equity": 120.69
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 23:10:54",
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
      "tick_time": "2026-06-09 23:10:52",
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
      "tick_time": "2026-06-09 23:10:54",
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
      "tick_time": "2026-06-09 23:10:56",
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
      "tick_time": "2026-06-09 23:10:56",
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
      "tick_time": "2026-06-09 23:10:56",
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
      "tick_time": "2026-06-09 23:10:56",
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
        "rows": 2121,
        "earliest": "2026-05-11 05:00:00",
        "latest": "2026-06-09 23:00:00",
        "date_key": "timestamp"
      },
      "GBPUSD": {
        "rows": 2089,
        "earliest": "2026-05-11 05:00:00",
        "latest": "2026-06-09 23:00:00",
        "date_key": "timestamp"
      },
      "USDJPY": {
        "rows": 2089,
        "earliest": "2026-05-11 05:00:00",
        "latest": "2026-06-09 23:00:00",
        "date_key": "timestamp"
      },
      "XAUUSD": {
        "rows": 1991,
        "earliest": "2026-05-11 06:00:00",
        "latest": "2026-06-09 23:00:00",
        "date_key": "timestamp"
      },
      "US_30": {
        "rows": 3831,
        "earliest": "2026-04-14 14:15:00",
        "latest": "2026-06-09 23:00:00",
        "date_key": "timestamp"
      },
      "US_500": {
        "rows": 3831,
        "earliest": "2026-04-14 14:00:00",
        "latest": "2026-06-09 23:00:00",
        "date_key": "timestamp"
      },
      "US_TECH100": {
        "rows": 3831,
        "earliest": "2026-04-14 13:45:00",
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
        "ok": true,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 23:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
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
        "ok": true,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 23:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
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
        "ok": true,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 23:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
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
        "ok": true,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 23:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
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
        "ok": true,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 23:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
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
        "ok": true,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 23:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
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
        "ok": true,
        "raw_latest": "2026-06-09 23:00:00",
        "db_latest": "2026-06-09 23:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
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
    "M15"
  ],
  "policy": "Update actions are accepted against MT5 raw latest bars captured before the command starts. The check action remains strict against current MT5 raw latest bars.",
  "target_mt5_raw": {
    "connected": true,
    "account": {
      "login": 89467841,
      "server": "Ava-Real 1-MT5",
      "balance": 124.31,
      "equity": 126.14
    },
    "symbols": {
      "EURUSD": {
        "mt5_symbol": "EURUSD",
        "tick_time": "2026-06-09 23:00:44",
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
        "tick_time": "2026-06-09 23:00:44",
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
        "tick_time": "2026-06-09 23:00:44",
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
        "tick_time": "2026-06-09 23:00:44",
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
        "tick_time": "2026-06-09 23:00:44",
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
        "tick_time": "2026-06-09 23:00:44",
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
        "tick_time": "2026-06-09 23:00:44",
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
          "ok": false,
          "raw_latest": "2026-06-09 23:00:00",
          "db_latest": "2026-06-09 22:00:00",
          "lag_hours": 1.0,
          "status": "stale"
        },
        "M15": {
          "ok": true,
          "raw_latest": "2026-06-09 23:00:00",
          "db_latest": "2026-06-09 23:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
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
          "ok": true,
          "raw_latest": "2026-06-09 23:00:00",
          "db_latest": "2026-06-09 23:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
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
          "ok": true,
          "raw_latest": "2026-06-09 23:00:00",
          "db_latest": "2026-06-09 23:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
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
          "ok": true,
          "raw_latest": "2026-06-09 23:00:00",
          "db_latest": "2026-06-09 23:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
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
          "ok": true,
          "raw_latest": "2026-06-09 23:00:00",
          "db_latest": "2026-06-09 23:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
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
          "ok": true,
          "raw_latest": "2026-06-09 23:00:00",
          "db_latest": "2026-06-09 23:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
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
          "ok": true,
          "raw_latest": "2026-06-09 23:00:00",
          "db_latest": "2026-06-09 23:00:00",
          "lag_hours": 0.0,
          "status": "fresh"
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
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe build_m15_state.py --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 30
returncode=0
==================================================
EURUSD M15 State ���ݿ�ժҪ:
{
  "symbol": "EURUSD",
  "total_rows": 2121,
  "earliest": "2026-05-11 05:00:00",
  "latest": "2026-06-09 23:00:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 23:00:00
    M15=-0, H1=0, D1=-5
    SRͻ��=False, ����=none

==================================================
GBPUSD M15 State ���ݿ�ժҪ:
{
  "symbol": "GBPUSD",
  "total_rows": 2089,
  "earliest": "2026-05-11 05:00:00",
  "latest": "2026-06-09 23:00:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 23:00:00
    M15=-0, H1=0, D1=-1
    SRͻ��=False, ����=none

==================================================
USDJPY M15 State ���ݿ�ժҪ:
{
  "symbol": "USDJPY",
  "total_rows": 2089,
  "earliest": "2026-05-11 05:00:00",
  "latest": "2026-06-09 23:00:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 23:00:00
    M15=0, H1=0, D1=5
    SRͻ��=False, ����=none

==================================================
XAUUSD M15 State ���ݿ�ժҪ:
{
  "symbol": "XAUUSD",
  "total_rows": 1991,
  "earliest": "2026-05-11 06:00:00",
  "latest": "2026-06-09 23:00:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 23:00:00
    M15=-5, H1=-5, D1=-D
    SRͻ��=False, ����=none

==================================================
US_30 M15 State ���ݿ�ժҪ:
{
  "symbol": "US_30",
  "total_rows": 3831,
  "earliest": "2026-04-14 14:15:00",
  "latest": "2026-06-09 23:00:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 23:00:00
    M15=-1, H1=1, D1=-9
    SRͻ��=False, ����=none

  SRͻ��ͳ��:
    up: 9 ��
    down: 32 ��

==================================================
US_500 M15 State ���ݿ�ժҪ:
{
  "symbol": "US_500",
  "total_rows": 3831,
  "earliest": "2026-04-14 14:00:00",
  "latest": "2026-06-09 23:00:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 23:00:00
    M15=-5, H1=-5, D1=-D
    SRͻ��=False, ����=none

  SRͻ��ͳ��:
    up: 5 ��
    down: 14 ��

==================================================
US_TECH100 M15 State ���ݿ�ժҪ:
{
  "symbol": "US_TECH100",
  "total_rows": 3831,
  "earliest": "2026-04-14 13:45:00",
  "latest": "2026-06-09 23:00:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 23:00:00
    M15=-D, H1=-5, D1=-D
    SRͻ��=False, ����=none

  SRͻ��ͳ��:
    down: 3 ��
   D1: 26 ��
2026-06-09 23:06:39,960 [INFO] ��ȡ����: US_30 H4 | 135�� | 2026-05-11 04:00:00 ~ 2026-06-09 20:00:00
2026-06-09 23:06:39,960 [INFO]   H4: 135 ��
2026-06-09 23:06:39,963 [INFO] ��ȡ����: US_30 H1 | 497�� | 2026-05-11 06:00:00 ~ 2026-06-09 23:00:00
2026-06-09 23:06:39,963 [INFO]   H1: 497 ��
2026-06-09 23:06:39,976 [INFO] ��ȡ����: US_30 M30 | 993�� | 2026-05-11 06:00:00 ~ 2026-06-09 23:00:00
2026-06-09 23:06:39,976 [INFO]   M30: 993 ��
2026-06-09 23:06:39,981 [INFO] ��ȡ����: US_30 M15 | 1985�� | 2026-05-11 06:00:00 ~ 2026-06-09 23:00:00
2026-06-09 23:06:39,982 [INFO]   M15: 1985 ��
2026-06-09 23:08:04,496 [INFO] US_30 ���� 1985 ��M15 State
2026-06-09 23:08:04,500 [INFO]   �ѱ���: 1985 �� M15 State
2026-06-09 23:08:04,500 [INFO] 
============================================================
2026-06-09 23:08:04,500 [INFO] ���� M15 State: US_500 (US_500) | 30��
2026-06-09 23:08:04,500 [INFO] ============================================================
2026-06-09 23:08:04,503 [INFO] ��ȡ����: US_500 MN1 | 1�� | 2026-06-01 08:00:00 ~ 2026-06-01 08:00:00
2026-06-09 23:08:04,503 [INFO]   MN1: 1 ��
2026-06-09 23:08:04,505 [INFO] ��ȡ����: US_500 W1 | 4�� | 2026-05-17 08:00:00 ~ 2026-06-07 08:00:00
2026-06-09 23:08:04,506 [INFO]   W1: 4 ��
2026-06-09 23:08:04,508 [INFO] ��ȡ����: US_500 D1 | 26�� | 2026-05-11 08:00:00 ~ 2026-06-09 08:00:00
2026-06-09 23:08:04,508 [INFO]   D1: 26 ��
2026-06-09 23:08:04,510 [INFO] ��ȡ����: US_500 H4 | 135�� | 2026-05-11 04:00:00 ~ 2026-06-09 20:00:00
2026-06-09 23:08:04,510 [INFO]   H4: 135 ��
2026-06-09 23:08:04,513 [INFO] ��ȡ����: US_500 H1 | 497�� | 2026-05-11 06:00:00 ~ 2026-06-09 23:00:00
2026-06-09 23:08:04,514 [INFO]   H1: 497 ��
2026-06-09 23:08:04,533 [INFO] ��ȡ����: US_500 M30 | 993�� | 2026-05-11 06:00:00 ~ 2026-06-09 23:00:00
2026-06-09 23:08:04,533 [INFO]   M30: 993 ��
2026-06-09 23:08:04,538 [INFO] ��ȡ����: US_500 M15 | 1984�� | 2026-05-11 06:00:00 ~ 2026-06-09 23:00:00
2026-06-09 23:08:04,538 [INFO]   M15: 1984 ��
2026-06-09 23:09:30,344 [INFO] US_500 ���� 1984 ��M15 State
2026-06-09 23:09:30,349 [INFO]   �ѱ���: 1984 �� M15 State
2026-06-09 23:09:30,349 [INFO] 
============================================================
2026-06-09 23:09:30,349 [INFO] ���� M15 State: US_TECH100 (US_TECH100) | 30��
2026-06-09 23:09:30,349 [INFO] ============================================================
2026-06-09 23:09:30,351 [INFO] ��ȡ����: US_TECH100 MN1 | 1�� | 2026-06-01 08:00:00 ~ 2026-06-01 08:00:00
2026-06-09 23:09:30,351 [INFO]   MN1: 1 ��
2026-06-09 23:09:30,353 [INFO] ��ȡ����: US_TECH100 W1 | 4�� | 2026-05-17 08:00:00 ~ 2026-06-07 08:00:00
2026-06-09 23:09:30,353 [INFO]   W1: 4 ��
2026-06-09 23:09:30,355 [INFO] ��ȡ����: US_TECH100 D1 | 26�� | 2026-05-11 08:00:00 ~ 2026-06-09 08:00:00
2026-06-09 23:09:30,355 [INFO]   D1: 26 ��
2026-06-09 23:09:30,357 [INFO] ��ȡ����: US_TECH100 H4 | 135�� | 2026-05-11 04:00:00 ~ 2026-06-09 20:00:00
2026-06-09 23:09:30,358 [INFO]   H4: 135 ��
2026-06-09 23:09:30,360 [INFO] ��ȡ����: US_TECH100 H1 | 497�� | 2026-05-11 06:00:00 ~ 2026-06-09 23:00:00
2026-06-09 23:09:30,360 [INFO]   H1: 497 ��
2026-06-09 23:09:30,365 [INFO] ��ȡ����: US_TECH100 M30 | 993�� | 2026-05-11 06:00:00 ~ 2026-06-09 23:00:00
2026-06-09 23:09:30,365 [INFO]   M30: 993 ��
2026-06-09 23:09:30,371 [INFO] ��ȡ����: US_TECH100 M15 | 1983�� | 2026-05-11 06:00:00 ~ 2026-06-09 23:00:00
2026-06-09 23:09:30,371 [INFO]   M15: 1983 ��
2026-06-09 23:10:55,097 [INFO] US_TECH100 ���� 1983 ��M15 State
2026-06-09 23:10:55,101 [INFO]   �ѱ���: 1983 �� M15 State
2026-06-09 23:10:55,294 [INFO] M15StateDB �����ѹر�
2026-06-09 23:10:55,294 [INFO] MT5�����Ž����ѶϿ�
2026-06-09 23:10:55,295 [INFO] 
============================================================
2026-06-09 23:10:55,295 [INFO] ������ɣ��ܼ�: 14210 �� M15 State
2026-06-09 23:10:55,295 [INFO] ============================================================
2026-06-09 23:10:55,319 [INFO] m15_state_snapshot ����ʼ�����
2026-06-09 23:10:55,372 [INFO] M15StateDB �����ѹر�
```
