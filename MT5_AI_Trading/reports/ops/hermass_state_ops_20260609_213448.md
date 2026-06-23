# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 21:34:48
- action: update-m15
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
    "equity": 156.24
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 21:34:44",
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
      "tick_time": "2026-06-09 21:34:45",
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
      "tick_time": "2026-06-09 21:34:45",
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
      "tick_time": "2026-06-09 21:34:47",
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
      "tick_time": "2026-06-09 21:34:47",
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
      "tick_time": "2026-06-09 21:34:47",
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
      "tick_time": "2026-06-09 21:34:47",
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
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
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
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
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
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
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
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
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
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
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
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
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
        "ok": false,
        "raw_latest": "2026-06-09 08:00:00",
        "db_latest": "2026-05-27",
        "lag_hours": 320.0,
        "status": "stale"
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

## Commands

```text
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe build_m15_state.py --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 30
returncode=0
==================================================
EURUSD M15 State ���ݿ�ժҪ:
{
  "symbol": "EURUSD",
  "total_rows": 2114,
  "earliest": "2026-05-11 05:00:00",
  "latest": "2026-06-09 21:15:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:15:00
    M15=0, H1=0, D1=-5
    SRͻ��=False, ����=none

==================================================
GBPUSD M15 State ���ݿ�ժҪ:
{
  "symbol": "GBPUSD",
  "total_rows": 2082,
  "earliest": "2026-05-11 05:00:00",
  "latest": "2026-06-09 21:15:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:15:00
    M15=0, H1=0, D1=-1
    SRͻ��=False, ����=none

==================================================
USDJPY M15 State ���ݿ�ժҪ:
{
  "symbol": "USDJPY",
  "total_rows": 2082,
  "earliest": "2026-05-11 05:00:00",
  "latest": "2026-06-09 21:15:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:15:00
    M15=0, H1=-0, D1=5
    SRͻ��=False, ����=none

==================================================
XAUUSD M15 State ���ݿ�ժҪ:
{
  "symbol": "XAUUSD",
  "total_rows": 1984,
  "earliest": "2026-05-11 06:00:00",
  "latest": "2026-06-09 21:15:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:15:00
    M15=-1, H1=1, D1=-D
    SRͻ��=False, ����=none

==================================================
US_30 M15 State ���ݿ�ժҪ:
{
  "symbol": "US_30",
  "total_rows": 3824,
  "earliest": "2026-04-14 14:15:00",
  "latest": "2026-06-09 21:15:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:15:00
    M15=1, H1=1, D1=9
    SRͻ��=False, ����=none

  SRͻ��ͳ��:
    down: 32 ��
    up: 9 ��

==================================================
US_500 M15 State ���ݿ�ժҪ:
{
  "symbol": "US_500",
  "total_rows": 3824,
  "earliest": "2026-04-14 14:00:00",
  "latest": "2026-06-09 21:15:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:15:00
    M15=1, H1=1, D1=-D
    SRͻ��=False, ����=none

  SRͻ��ͳ��:
    down: 14 ��
    up: 5 ��

==================================================
US_TECH100 M15 State ���ݿ�ժҪ:
{
  "symbol": "US_TECH100",
  "total_rows": 3824,
  "earliest": "2026-04-14 13:45:00",
  "latest": "2026-06-09 21:15:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:15:00
    M15=1, H1=1, D1=-D
    SRͻ��=False, ����=none

  SRͻ��ͳ��:
    down: 3 ��
   D1: 26 ��
2026-06-09 21:28:27,255 [INFO] ��ȡ����: US_30 H4 | 135�� | 2026-05-11 04:00:00 ~ 2026-06-09 20:00:00
2026-06-09 21:28:27,255 [INFO]   H4: 135 ��
2026-06-09 21:28:27,259 [INFO] ��ȡ����: US_30 H1 | 495�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:00:00
2026-06-09 21:28:27,259 [INFO]   H1: 495 ��
2026-06-09 21:28:27,284 [INFO] ��ȡ����: US_30 M30 | 989�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:00:00
2026-06-09 21:28:27,284 [INFO]   M30: 989 ��
2026-06-09 21:28:27,290 [INFO] ��ȡ����: US_30 M15 | 1978�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:15:00
2026-06-09 21:28:27,290 [INFO]   M15: 1978 ��
2026-06-09 21:30:29,342 [INFO] US_30 ���� 1978 ��M15 State
2026-06-09 21:30:29,347 [INFO]   �ѱ���: 1978 �� M15 State
2026-06-09 21:30:29,347 [INFO] 
============================================================
2026-06-09 21:30:29,347 [INFO] ���� M15 State: US_500 (US_500) | 30��
2026-06-09 21:30:29,347 [INFO] ============================================================
2026-06-09 21:30:29,350 [INFO] ��ȡ����: US_500 MN1 | 1�� | 2026-06-01 08:00:00 ~ 2026-06-01 08:00:00
2026-06-09 21:30:29,350 [INFO]   MN1: 1 ��
2026-06-09 21:30:29,352 [INFO] ��ȡ����: US_500 W1 | 4�� | 2026-05-17 08:00:00 ~ 2026-06-07 08:00:00
2026-06-09 21:30:29,352 [INFO]   W1: 4 ��
2026-06-09 21:30:29,354 [INFO] ��ȡ����: US_500 D1 | 26�� | 2026-05-11 08:00:00 ~ 2026-06-09 08:00:00
2026-06-09 21:30:29,354 [INFO]   D1: 26 ��
2026-06-09 21:30:29,356 [INFO] ��ȡ����: US_500 H4 | 135�� | 2026-05-11 04:00:00 ~ 2026-06-09 20:00:00
2026-06-09 21:30:29,356 [INFO]   H4: 135 ��
2026-06-09 21:30:29,360 [INFO] ��ȡ����: US_500 H1 | 495�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:00:00
2026-06-09 21:30:29,360 [INFO]   H1: 495 ��
2026-06-09 21:30:29,376 [INFO] ��ȡ����: US_500 M30 | 989�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:00:00
2026-06-09 21:30:29,376 [INFO]   M30: 989 ��
2026-06-09 21:30:29,382 [INFO] ��ȡ����: US_500 M15 | 1977�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:15:00
2026-06-09 21:30:29,382 [INFO]   M15: 1977 ��
2026-06-09 21:32:35,859 [INFO] US_500 ���� 1977 ��M15 State
2026-06-09 21:32:35,864 [INFO]   �ѱ���: 1977 �� M15 State
2026-06-09 21:32:35,864 [INFO] 
============================================================
2026-06-09 21:32:35,864 [INFO] ���� M15 State: US_TECH100 (US_TECH100) | 30��
2026-06-09 21:32:35,864 [INFO] ============================================================
2026-06-09 21:32:35,867 [INFO] ��ȡ����: US_TECH100 MN1 | 1�� | 2026-06-01 08:00:00 ~ 2026-06-01 08:00:00
2026-06-09 21:32:35,867 [INFO]   MN1: 1 ��
2026-06-09 21:32:35,870 [INFO] ��ȡ����: US_TECH100 W1 | 4�� | 2026-05-17 08:00:00 ~ 2026-06-07 08:00:00
2026-06-09 21:32:35,870 [INFO]   W1: 4 ��
2026-06-09 21:32:35,872 [INFO] ��ȡ����: US_TECH100 D1 | 26�� | 2026-05-11 08:00:00 ~ 2026-06-09 08:00:00
2026-06-09 21:32:35,872 [INFO]   D1: 26 ��
2026-06-09 21:32:35,875 [INFO] ��ȡ����: US_TECH100 H4 | 135�� | 2026-05-11 04:00:00 ~ 2026-06-09 20:00:00
2026-06-09 21:32:35,875 [INFO]   H4: 135 ��
2026-06-09 21:32:35,878 [INFO] ��ȡ����: US_TECH100 H1 | 495�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:00:00
2026-06-09 21:32:35,878 [INFO]   H1: 495 ��
2026-06-09 21:32:35,895 [INFO] ��ȡ����: US_TECH100 M30 | 989�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:00:00
2026-06-09 21:32:35,895 [INFO]   M30: 989 ��
2026-06-09 21:32:35,902 [INFO] ��ȡ����: US_TECH100 M15 | 1976�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:15:00
2026-06-09 21:32:35,902 [INFO]   M15: 1976 ��
2026-06-09 21:34:45,990 [INFO] US_TECH100 ���� 1976 ��M15 State
2026-06-09 21:34:45,995 [INFO]   �ѱ���: 1976 �� M15 State
2026-06-09 21:34:46,307 [INFO] M15StateDB �����ѹر�
2026-06-09 21:34:46,307 [INFO] MT5�����Ž����ѶϿ�
2026-06-09 21:34:46,307 [INFO] 
============================================================
2026-06-09 21:34:46,307 [INFO] ������ɣ��ܼ�: 14161 �� M15 State
2026-06-09 21:34:46,307 [INFO] ============================================================
2026-06-09 21:34:46,338 [INFO] m15_state_snapshot ����ʼ�����
2026-06-09 21:34:46,405 [INFO] M15StateDB �����ѹر�
```

## Notes
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_213448.md: [WinError 5] 拒绝访问。: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass'
