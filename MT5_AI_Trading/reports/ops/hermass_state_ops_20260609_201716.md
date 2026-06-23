# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 20:17:15
- action: update-m15
- symbols: EURUSD
- status: ok

## MT5 Raw
```json
{
  "connected": true,
  "account": {
    "login": 89467841,
    "server": "Ava-Real 1-MT5",
    "balance": 162.5,
    "equity": 160.3
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 20:17:15",
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
        "latest": "2026-06-09 20:15:00"
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
        "rows": 3047,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-09 12:00:00",
        "date_key": "timestamp"
      }
    }
  },
  "m15_state": {
    "path": "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\data\\m15_state.duckdb",
    "exists": true,
    "symbols": {
      "EURUSD": {
        "rows": 158,
        "earliest": "2026-06-07 21:00:00",
        "latest": "2026-06-09 12:15:00",
        "date_key": "timestamp"
      }
    }
  },
  "d1_hermass": {
    "path": "D:\\qoder\\csvcl - AVA\\MT5_AI_Trading\\data\\hermass_state.db",
    "exists": true,
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
  }
}
```

## Commands

```text
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe build_m15_state.py --symbols EURUSD --days 2
returncode=0
==================================================
EURUSD M15 State ���ݿ�ժҪ:
{
  "symbol": "EURUSD",
  "total_rows": 158,
  "earliest": "2026-06-07 21:00:00",
  "latest": "2026-06-09 12:15:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 12:15:00
    M15=0, H1=0, D1=0
    SRͻ��=False, ����=none
ogicalType
2026-06-09 20:17:15,061 [ERROR] ����ʧ�� 2026-06-09 07:30:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,077 [ERROR] ����ʧ�� 2026-06-09 07:45:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,093 [ERROR] ����ʧ�� 2026-06-09 08:00:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,109 [ERROR] ����ʧ�� 2026-06-09 08:15:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,123 [ERROR] ����ʧ�� 2026-06-09 08:30:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,141 [ERROR] ����ʧ�� 2026-06-09 08:45:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,156 [ERROR] ����ʧ�� 2026-06-09 09:00:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,171 [ERROR] ����ʧ�� 2026-06-09 09:15:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,186 [ERROR] ����ʧ�� 2026-06-09 09:30:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,201 [ERROR] ����ʧ�� 2026-06-09 09:45:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,216 [ERROR] ����ʧ�� 2026-06-09 10:00:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,232 [ERROR] ����ʧ�� 2026-06-09 10:15:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,248 [ERROR] ����ʧ�� 2026-06-09 10:30:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,263 [ERROR] ����ʧ�� 2026-06-09 10:45:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,280 [ERROR] ����ʧ�� 2026-06-09 11:00:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,296 [ERROR] ����ʧ�� 2026-06-09 11:15:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,313 [ERROR] ����ʧ�� 2026-06-09 11:30:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,328 [ERROR] ����ʧ�� 2026-06-09 11:45:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,344 [ERROR] ����ʧ�� 2026-06-09 12:00:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,363 [ERROR] ����ʧ�� 2026-06-09 12:15:00: Not implemented Error: Unable to transform python value of type '<class 'numpy.int64'>' to DuckDB LogicalType
2026-06-09 20:17:15,363 [INFO] EURUSD ���� 38 ��M15 State
2026-06-09 20:17:15,364 [INFO]   �ѱ���: 38 �� M15 State
2026-06-09 20:17:15,408 [INFO] M15StateDB �����ѹر�
2026-06-09 20:17:15,408 [INFO] MT5�����Ž����ѶϿ�
2026-06-09 20:17:15,408 [INFO] 
============================================================
2026-06-09 20:17:15,408 [INFO] ������ɣ��ܼ�: 38 �� M15 State
2026-06-09 20:17:15,408 [INFO] ============================================================
2026-06-09 20:17:15,433 [INFO] m15_state_snapshot ����ʼ�����
2026-06-09 20:17:15,444 [INFO] M15StateDB �����ѹر�
```

## Notes
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_201716.md: [WinError 5] 拒绝访问。: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass'
