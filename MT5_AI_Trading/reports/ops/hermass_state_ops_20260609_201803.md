# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 20:18:02
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
    "equity": 162.4
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 20:18:01",
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
2026-06-09 20:17:56,124 [INFO] MT5�����Ž������ӳɹ� | �˻�: 89467841
2026-06-09 20:17:56,124 [INFO] 
============================================================
2026-06-09 20:17:56,124 [INFO] ���� M15 State: EURUSD (EURUSD) | 2��
2026-06-09 20:17:56,124 [INFO] ============================================================
2026-06-09 20:17:56,124 [WARNING] δ��ȡ������: EURUSD MN1 2026-06-07 20:17:56.124668~2026-06-09 20:17:56.124668
2026-06-09 20:17:56,125 [INFO]   MN1: 0 ��
2026-06-09 20:17:56,125 [WARNING] δ��ȡ������: EURUSD W1 2026-06-07 20:17:56.124668~2026-06-09 20:17:56.124668
2026-06-09 20:17:56,126 [INFO]   W1: 0 ��
2026-06-09 20:17:56,129 [INFO] ��ȡ����: EURUSD D1 | 2�� | 2026-06-08 00:00:00 ~ 2026-06-09 00:00:00
2026-06-09 20:17:56,129 [INFO]   D1: 2 ��
2026-06-09 20:17:56,132 [INFO] ��ȡ����: EURUSD H4 | 11�� | 2026-06-07 20:00:00 ~ 2026-06-09 12:00:00
2026-06-09 20:17:56,132 [INFO]   H4: 11 ��
2026-06-09 20:17:56,136 [INFO] ��ȡ����: EURUSD H1 | 40�� | 2026-06-07 21:00:00 ~ 2026-06-09 12:00:00
2026-06-09 20:17:56,136 [INFO]   H1: 40 ��
2026-06-09 20:17:56,139 [INFO] ��ȡ����: EURUSD M30 | 79�� | 2026-06-07 21:00:00 ~ 2026-06-09 12:00:00
2026-06-09 20:17:56,139 [INFO]   M30: 79 ��
2026-06-09 20:17:56,141 [INFO] ��ȡ����: EURUSD M15 | 158�� | 2026-06-07 21:00:00 ~ 2026-06-09 12:15:00
2026-06-09 20:17:56,141 [INFO]   M15: 158 ��
2026-06-09 20:17:57,870 [INFO] m15_state_snapshot ����ʼ�����
2026-06-09 20:18:01,890 [INFO] EURUSD ���� 158 ��M15 State
2026-06-09 20:18:01,891 [INFO]   �ѱ���: 158 �� M15 State
2026-06-09 20:18:01,913 [INFO] M15StateDB �����ѹر�
2026-06-09 20:18:01,913 [INFO] MT5�����Ž����ѶϿ�
2026-06-09 20:18:01,913 [INFO] 
============================================================
2026-06-09 20:18:01,913 [INFO] ������ɣ��ܼ�: 158 �� M15 State
2026-06-09 20:18:01,913 [INFO] ============================================================
2026-06-09 20:18:01,942 [INFO] m15_state_snapshot ����ʼ�����
2026-06-09 20:18:01,952 [INFO] M15StateDB �����ѹر�
```

## Notes
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_201803.md: [WinError 5] 拒绝访问。: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass'
