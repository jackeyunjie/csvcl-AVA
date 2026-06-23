# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 21:37:25
- action: rebuild-d1
- symbols: EURUSD, GBPUSD, USDJPY, XAUUSD, US_30, US_500, US_TECH100
- status: ok

## MT5 Raw
```json
{
  "connected": true,
  "account": {
    "login": 89467841,
    "server": "Ava-Real 1-MT5",
    "balance": 162.5,
    "equity": 159.48
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 21:37:24",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 21:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 21:30:00"
      }
    },
    "GBPUSD": {
      "mt5_symbol": "GBPUSD",
      "tick_time": "2026-06-09 21:37:22",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 21:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 21:30:00"
      }
    },
    "USDJPY": {
      "mt5_symbol": "USDJPY",
      "tick_time": "2026-06-09 21:37:23",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 21:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 21:30:00"
      }
    },
    "XAUUSD": {
      "mt5_symbol": "GOLD",
      "tick_time": "2026-06-09 21:37:24",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 21:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 21:30:00"
      }
    },
    "US_30": {
      "mt5_symbol": "US_30",
      "tick_time": "2026-06-09 21:37:24",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 21:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 21:30:00"
      }
    },
    "US_500": {
      "mt5_symbol": "US_500",
      "tick_time": "2026-06-09 21:37:24",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 21:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 21:30:00"
      }
    },
    "US_TECH100": {
      "mt5_symbol": "US_TECH100",
      "tick_time": "2026-06-09 21:37:24",
      "D1": {
        "rows": 5,
        "latest": "2026-06-09 08:00:00"
      },
      "H1": {
        "rows": 5,
        "latest": "2026-06-09 21:00:00"
      },
      "M15": {
        "rows": 5,
        "latest": "2026-06-09 21:30:00"
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
        "rows": 2114,
        "earliest": "2026-05-11 05:00:00",
        "latest": "2026-06-09 21:15:00",
        "date_key": "timestamp"
      },
      "GBPUSD": {
        "rows": 2082,
        "earliest": "2026-05-11 05:00:00",
        "latest": "2026-06-09 21:15:00",
        "date_key": "timestamp"
      },
      "USDJPY": {
        "rows": 2082,
        "earliest": "2026-05-11 05:00:00",
        "latest": "2026-06-09 21:15:00",
        "date_key": "timestamp"
      },
      "XAUUSD": {
        "rows": 1984,
        "earliest": "2026-05-11 06:00:00",
        "latest": "2026-06-09 21:15:00",
        "date_key": "timestamp"
      },
      "US_30": {
        "rows": 3824,
        "earliest": "2026-04-14 14:15:00",
        "latest": "2026-06-09 21:15:00",
        "date_key": "timestamp"
      },
      "US_500": {
        "rows": 3824,
        "earliest": "2026-04-14 14:00:00",
        "latest": "2026-06-09 21:15:00",
        "date_key": "timestamp"
      },
      "US_TECH100": {
        "rows": 3824,
        "earliest": "2026-04-14 13:45:00",
        "latest": "2026-06-09 21:15:00",
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
        "ok": true,
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:30:00",
        "db_latest": "2026-06-09 21:15:00",
        "lag_hours": 0.25,
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
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:30:00",
        "db_latest": "2026-06-09 21:15:00",
        "lag_hours": 0.25,
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
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:30:00",
        "db_latest": "2026-06-09 21:15:00",
        "lag_hours": 0.25,
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
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:30:00",
        "db_latest": "2026-06-09 21:15:00",
        "lag_hours": 0.25,
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
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:30:00",
        "db_latest": "2026-06-09 21:15:00",
        "lag_hours": 0.25,
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
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:30:00",
        "db_latest": "2026-06-09 21:15:00",
        "lag_hours": 0.25,
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
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:30:00",
        "db_latest": "2026-06-09 21:15:00",
        "lag_hours": 0.25,
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

## Backups
- D:\qoder\csvcl - AVA\MT5_AI_Trading\data\backups\20260609_213529_pre_d1_rebuild\hermass_state.db
- D:\qoder\csvcl - AVA\MT5_AI_Trading\data\backups\20260609_213529_pre_d1_rebuild\h1_state.duckdb
- D:\qoder\csvcl - AVA\MT5_AI_Trading\data\backups\20260609_213529_pre_d1_rebuild\m15_state.duckdb
- D:\qoder\csvcl - AVA\MT5_AI_Trading\data\backups\20260609_213529_pre_d1_rebuild\hermass_h1_state.db

## Commands

```text
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe build_hermass_state.py --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100
returncode=0
============================================================
  Hermass 4-bit State v2 — 向量化加速
============================================================
[MT5] Ava-Real 1-MT5 | 89467841
  [ 1/7] EURUSD     (EURUSD) ->  4950条  [2010-06-08~2026-06-09]  13.7s
  [ 2/7] GBPUSD     (GBPUSD) ->  4950条  [2010-06-08~2026-06-09]  12.9s
  [ 3/7] USDJPY     (USDJPY) ->  4950条  [2010-06-08~2026-06-09]  13.4s
  [ 4/7] XAUUSD     (GOLD) ->  4950条  [2010-04-08~2026-06-09]  13.4s
  [ 5/7] US_30      (US_30) ->  4729条  [2011-01-17~2026-06-09]  20.3s
  [ 6/7] US_500     (US_500) ->  4729条  [2011-01-17~2026-06-09]  12.9s
  [ 7/7] US_TECH100 (US_TECH100) ->  4440条  [2011-12-27~2026-06-09]  18.6s

[Slice] 生成中...
  切片: 3772 个

============================================================
  Hermass State DB: 33698条 7品种 3772切片
  日期: 2010-06-17 ~ 2026-06-09
  EF分布:
    ef=2:    935 #####
    ef=1:  11531 ##########################################################
    ef=0:  21232 ###########################################################################################################
  今日共振 (ef>=1):
  EURUSD样本:
    2026-06-09 MN1=-1  W1=-2  D1=-F  ef=0
    2026-06-08 MN1=0   W1=-2  D1=-7  ef=0
    2026-06-07 MN1=0   W1=-2  D1=-6  ef=0
    2026-06-05 MN1=-1  W1=-3  D1=-7  ef=0
    2026-06-04 MN1=0   W1=-1  D1=-4  ef=0

[Done] data\hermass_state.db (1.3MB) 总耗时113s

```

## Notes
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_213725.md: [WinError 5] 拒绝访问。: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass'
