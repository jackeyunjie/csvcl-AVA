# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 21:17:35
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
    "balance": 162.5,
    "equity": 159.7
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 21:17:23",
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
        "latest": "2026-06-09 21:15:00"
      }
    },
    "GBPUSD": {
      "mt5_symbol": "GBPUSD",
      "tick_time": "2026-06-09 21:17:23",
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
        "latest": "2026-06-09 21:15:00"
      }
    },
    "USDJPY": {
      "mt5_symbol": "USDJPY",
      "tick_time": "2026-06-09 21:17:24",
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
        "latest": "2026-06-09 21:15:00"
      }
    },
    "XAUUSD": {
      "mt5_symbol": "GOLD",
      "tick_time": "2026-06-09 21:17:24",
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
        "latest": "2026-06-09 21:15:00"
      }
    },
    "US_30": {
      "mt5_symbol": "US_30",
      "tick_time": "2026-06-09 21:17:24",
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
        "latest": "2026-06-09 21:15:00"
      }
    },
    "US_500": {
      "mt5_symbol": "US_500",
      "tick_time": "2026-06-09 21:17:22",
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
        "latest": "2026-06-09 21:15:00"
      }
    },
    "US_TECH100": {
      "mt5_symbol": "US_TECH100",
      "tick_time": "2026-06-09 21:17:24",
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
        "latest": "2026-06-09 21:15:00"
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
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:15:00",
        "db_latest": "2026-06-09 20:15:00",
        "lag_hours": 1.0,
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
        "raw_latest": "2026-06-09 21:15:00",
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
        "ok": true,
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:15:00",
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
        "ok": true,
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:15:00",
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
        "ok": true,
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:15:00",
        "db_latest": "2026-05-28 02:00:00",
        "lag_hours": 307.25,
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
        "raw_latest": "2026-06-09 21:15:00",
        "db_latest": "2026-05-28 02:00:00",
        "lag_hours": 307.25,
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
        "raw_latest": "2026-06-09 21:15:00",
        "db_latest": "2026-05-28 02:00:00",
        "lag_hours": 307.25,
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
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe build_h1_state_real.py --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 120
returncode=0
: 19,
      "3": 17,
      "A": 8,
      "9": 5
    },
    "h1_hex": {
      "F": 354,
      "-F": 339,
      "6": 338,
      "E": 223,
      "4": 183,
      "-E": 178,
      "-4": 176,
      "-D": 153,
      "D": 150,
      "-6": 136,
      "8": 102,
      "7": 89,
      "0": 72,
      "-C": 71,
      "-5": 70,
      "-7": 59,
      "C": 52,
      "2": 43,
      "1": 42,
      "B": 38,
      "9": 30,
      "5": 29,
      "-B": 28,
      "-3": 23,
      "-A": 21,
      "-2": 21,
      "A": 16,
      "3": 13
    }
  }
}

==================================================
US_500 State ���ݿ�ժҪ:
{
  "symbol": "US_500",
  "total_rows": 2991,
  "earliest": "2025-12-05 00:00:00",
  "latest": "2026-06-09 21:00:00",
  "hex_distributions": {
    "mn1_hex": {
      "2": 2086,
      "6": 897,
      "0": 8
    },
    "w1_hex": {
      "2": 895,
      "F": 575,
      "0": 469,
      "6": 371,
      "7": 264,
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
      "-E": 46,
      "A": 38,
      "D": 23,
      "9": 23,
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
      "-F": 361,
      "F": 267,
      "-D": 240,
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
      "-5": 45,
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
      "-F": 353,
      "F": 266,
      "E": 264,
      "-D": 249,
      "-4": 198,
      "4": 139,
      "-E": 119,
      "D": 109,
      "8": 100,
      "0": 96,
      "-6": 90,
      "-C": 73,
      "1": 64,
      "-5": 64,
      "2": 57,
      "9": 45,
      "7": 44,
      "C": 43,
      "3": 38,
      "-B": 31,
      "5": 24,
      "-2": 23,
      "-3": 20,
      "B": 19,
      "-7": 15,
      "A": 15,
      "-A": 12
    }
  }
}

==================================================
US_TECH100 State ���ݿ�ժҪ:
{
  "symbol": "US_TECH100",
  "total_rows": 3049,
  "earliest": "2025-12-02 11:00:00",
  "latest": "2026-06-09 21:00:00",
  "hex_distributions": {
    "mn1_hex": {
      "6": 1411,
      "2": 883,
      "A": 479,
      "E": 152,
      "0": 124
    },
    "w1_hex": {
      "6": 645,
      "0": 588,
      "2": 485,
      "E": 460,
      "-4": 409,
      "-6": 196,
      "F": 154,
      "4": 66,
      "-2": 46
    },
    "d1_hex": {
      "8": 1193,
      "E": 708,
      "6": 206,
      "1": 147,
      "-C": 140,
      "0": 104,
      "C": 85,
      "-A": 81,
      "9": 81,
      "2": 71,
      "A": 46,
      "-B": 46,
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
      "-F": 341,
      "E": 285,
      "F": 258,
      "-D": 197,
      "7": 131,
      "2": 117,
      "-4": 103,
      "9": 79,
      "D": 78,
      "A": 69,
      "-5": 65,
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
      "6": 392,
      "-F": 363,
      "E": 320,
      "F": 249,
      "-D": 237,
      "-4": 177,
      "-E": 132,
      "8": 106,
      "4": 99,
      "D": 92,
      "0": 85,
      "-6": 84,
      "1": 80,
      "2": 77,
      "-C": 76,
      "7": 72,
      "C": 52,
      "-5": 51,
      "3": 49,
      "B": 47,
      "9": 47,
      "5": 30,
      "A": 27,
      "-7": 25,
      "-2": 24,
      "-B": 22,
      "-3": 18,
      "-A": 16
    }
  }
}
26-06-09 21:17:07,156 [INFO] StateHexEngine��ʼ�����
2026-06-09 21:17:07,479 [INFO] MN1@view: ������� 2880 �� state_hex
2026-06-09 21:17:07,645 [INFO] W1@view: ������� 2880 �� state_hex
2026-06-09 21:17:07,732 [INFO] D1@view: ������� 1920 �� state_hex
2026-06-09 21:17:08,119 [INFO] H4@view: ������� 2587 �� state_hex
2026-06-09 21:17:09,894 [INFO] H1@view: ������� 2861 �� state_hex
2026-06-09 21:17:09,905 [INFO] ��Ԫ�������� | ��2880��
2026-06-09 21:17:09,905 [INFO]   ��Ԫ��: 2880 ��
2026-06-09 21:17:11,077 [INFO] [XAUUSD] ���� 2880 ����Ԫ��
2026-06-09 21:17:11,077 [INFO]   �ѱ���: 2880 ��
2026-06-09 21:17:11,077 [INFO] 
==================================================
2026-06-09 21:17:11,077 [INFO] ���� US_30 (120��)
2026-06-09 21:17:11,077 [INFO] ==================================================
2026-06-09 21:17:11,148 [INFO]   MN1: 60 ��
2026-06-09 21:17:11,148 [INFO]   W1: 260 ��
2026-06-09 21:17:11,148 [INFO]   D1: 120 ��
2026-06-09 21:17:11,148 [INFO]   H4: 720 ��
2026-06-09 21:17:11,148 [INFO]   H1: 2880 ��
2026-06-09 21:17:11,148 [INFO] StateHexEncoder��ʼ�����
2026-06-09 21:17:11,148 [INFO] StateHexEngine��ʼ�����
2026-06-09 21:17:11,429 [INFO] MN1@view: ������� 2880 �� state_hex
2026-06-09 21:17:11,596 [INFO] W1@view: ������� 2880 �� state_hex
2026-06-09 21:17:11,667 [INFO] D1@view: ������� 1909 �� state_hex
2026-06-09 21:17:12,067 [INFO] H4@view: ������� 2583 �� state_hex
2026-06-09 21:17:13,779 [INFO] H1@view: ������� 2861 �� state_hex
2026-06-09 21:17:13,786 [INFO] ��Ԫ�������� | ��2880��
2026-06-09 21:17:13,787 [INFO]   ��Ԫ��: 2880 ��
2026-06-09 21:17:14,912 [INFO] [US_30] ���� 2880 ����Ԫ��
2026-06-09 21:17:14,912 [INFO]   �ѱ���: 2880 ��
2026-06-09 21:17:14,912 [INFO] 
==================================================
2026-06-09 21:17:14,912 [INFO] ���� US_500 (120��)
2026-06-09 21:17:14,912 [INFO] ==================================================
2026-06-09 21:17:14,978 [INFO]   MN1: 60 ��
2026-06-09 21:17:14,978 [INFO]   W1: 260 ��
2026-06-09 21:17:14,978 [INFO]   D1: 120 ��
2026-06-09 21:17:14,978 [INFO]   H4: 720 ��
2026-06-09 21:17:14,978 [INFO]   H1: 2880 ��
2026-06-09 21:17:14,978 [INFO] StateHexEncoder��ʼ�����
2026-06-09 21:17:14,978 [INFO] StateHexEngine��ʼ�����
2026-06-09 21:17:15,240 [INFO] MN1@view: ������� 2880 �� state_hex
2026-06-09 21:17:15,397 [INFO] W1@view: ������� 2880 �� state_hex
2026-06-09 21:17:15,469 [INFO] D1@view: ������� 1909 �� state_hex
2026-06-09 21:17:15,977 [INFO] H4@view: ������� 2583 �� state_hex
2026-06-09 21:17:17,679 [INFO] H1@view: ������� 2861 �� state_hex
2026-06-09 21:17:17,688 [INFO] ��Ԫ�������� | ��2880��
2026-06-09 21:17:17,689 [INFO]   ��Ԫ��: 2880 ��
2026-06-09 21:17:18,930 [INFO] [US_500] ���� 2880 ����Ԫ��
2026-06-09 21:17:18,930 [INFO]   �ѱ���: 2880 ��
2026-06-09 21:17:18,930 [INFO] 
==================================================
2026-06-09 21:17:18,930 [INFO] ���� US_TECH100 (120��)
2026-06-09 21:17:18,930 [INFO] ==================================================
2026-06-09 21:17:19,000 [INFO]   MN1: 60 ��
2026-06-09 21:17:19,000 [INFO]   W1: 260 ��
2026-06-09 21:17:19,000 [INFO]   D1: 120 ��
2026-06-09 21:17:19,000 [INFO]   H4: 720 ��
2026-06-09 21:17:19,000 [INFO]   H1: 2880 ��
2026-06-09 21:17:19,000 [INFO] StateHexEncoder��ʼ�����
2026-06-09 21:17:19,000 [INFO] StateHexEngine��ʼ�����
2026-06-09 21:17:19,267 [INFO] MN1@view: ������� 2880 �� state_hex
2026-06-09 21:17:19,428 [INFO] W1@view: ������� 2880 �� state_hex
2026-06-09 21:17:19,543 [INFO] D1@view: ������� 1909 �� state_hex
2026-06-09 21:17:19,988 [INFO] H4@view: ������� 2583 �� state_hex
2026-06-09 21:17:21,673 [INFO] H1@view: ������� 2861 �� state_hex
2026-06-09 21:17:21,702 [INFO] ��Ԫ�������� | ��2880��
2026-06-09 21:17:21,702 [INFO]   ��Ԫ��: 2880 ��
2026-06-09 21:17:22,974 [INFO] [US_TECH100] ���� 2880 ����Ԫ��
2026-06-09 21:17:22,975 [INFO]   �ѱ���: 2880 ��
2026-06-09 21:17:23,038 [INFO] MT5�����Ž����ѶϿ�
2026-06-09 21:17:23,038 [INFO] 
������ɣ�
2026-06-09 21:17:23,061 [INFO] h1_state_snapshot ����ʼ�����
```

## Notes
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_211735.md: [WinError 5] 拒绝访问。: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass'
