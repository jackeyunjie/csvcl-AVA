# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 20:19:56
- action: update-h1
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
    "equity": 163.1
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 20:19:54",
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
        "rows": 3055,
        "earliest": "2025-12-10 15:00:00",
        "latest": "2026-06-09 20:00:00",
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
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe build_h1_state_real.py --symbols EURUSD --days 120
returncode=0
==================================================
EURUSD State ���ݿ�ժҪ:
{
  "symbol": "EURUSD",
  "total_rows": 3055,
  "earliest": "2025-12-10 15:00:00",
  "latest": "2026-06-09 20:00:00",
  "hex_distributions": {
    "mn1_hex": {
      "6": 1490,
      "E": 1447,
      "C": 116,
      "4": 2
    },
    "w1_hex": {
      "0": 1560,
      "-6": 486,
      "4": 393,
      "-4": 234,
      "2": 152,
      "-2": 143,
      "6": 87
    },
    "d1_hex": {
      "8": 1109,
      "-F": 239,
      "E": 224,
      "-6": 202,
      "4": 191,
      "-A": 156,
      "D": 120,
      "-E": 118,
      "0": 108,
      "-C": 95,
      "-2": 83,
      "C": 79,
      "-4": 78,
      "6": 58,
      "-D": 44,
      "1": 35,
      "2": 28,
      "5": 24,
      "F": 21,
      "9": 13,
      "3": 13,
      "-B": 11,
      "-7": 6
    },
    "h4_hex": {
      "8": 382,
      "-6": 313,
      "-E": 278,
      "F": 255,
      "0": 227,
      "-F": 214,
      "D": 163,
      "-4": 160,
      "6": 144,
      "-D": 142,
      "E": 115,
      "4": 113,
      "2": 97,
      "-2": 72,
      "C": 53,
      "7": 51,
      "9": 51,
      "-C": 46,
      "5": 43,
      "B": 41,
      "-5": 26,
      "-7": 18,
      "1": 16,
      "-A": 12,
      "3": 12,
      "A": 7,
      "-B": 3,
      "-3": 1
    },
    "h1_hex": {
      "-4": 474,
      "4": 302,
      "F": 252,
      "-F": 246,
      "-D": 189,
      "-C": 159,
      "C": 157,
      "0": 150,
      "D": 125,
      "8": 121,
      "1": 116,
      "E": 112,
      "-E": 108,
      "-5": 96,
      "-6": 71,
      "6": 69,
      "7": 55,
      "5": 53,
      "9": 44,
      "-7": 39,
      "B": 21,
      "-2": 19,
      "A": 17,
      "-B": 17,
      "-A": 16,
      "-3": 16,
      "2": 6,
      "3": 5
    }
  }
}
2026-06-09 20:19:46,637 [INFO] MT5�����Ž������ӳɹ� | �˻�: 89467841
2026-06-09 20:19:46,637 [INFO] 
==================================================
2026-06-09 20:19:46,637 [INFO] ���� EURUSD (120��)
2026-06-09 20:19:46,637 [INFO] ==================================================
2026-06-09 20:19:46,656 [INFO]   MN1: 60 ��
2026-06-09 20:19:46,657 [INFO]   W1: 260 ��
2026-06-09 20:19:46,657 [INFO]   D1: 120 ��
2026-06-09 20:19:46,657 [INFO]   H4: 720 ��
2026-06-09 20:19:46,657 [INFO]   H1: 2880 ��
2026-06-09 20:19:46,657 [INFO] StateHexEncoder��ʼ�����
2026-06-09 20:19:46,657 [INFO] StateHexEngine��ʼ�����
2026-06-09 20:19:46,990 [INFO] MN1@view: ������� 2880 �� state_hex
2026-06-09 20:19:47,208 [INFO] W1@view: ������� 2880 �� state_hex
2026-06-09 20:19:47,304 [INFO] D1@view: ������� 2006 �� state_hex
2026-06-09 20:19:47,864 [INFO] H4@view: ������� 2706 �� state_hex
2026-06-09 20:19:50,566 [INFO] H1@view: ������� 2861 �� state_hex
2026-06-09 20:19:50,579 [INFO] ��Ԫ�������� | ��2880��
2026-06-09 20:19:50,580 [INFO]   ��Ԫ��: 2880 ��
2026-06-09 20:19:50,749 [INFO] h1_state_snapshot ����ʼ�����
2026-06-09 20:19:56,267 [INFO] [EURUSD] ���� 2880 ����Ԫ��
2026-06-09 20:19:56,267 [INFO]   �ѱ���: 2880 ��
2026-06-09 20:19:56,314 [INFO] MT5�����Ž����ѶϿ�
2026-06-09 20:19:56,314 [INFO] 
������ɣ�
2026-06-09 20:19:56,345 [INFO] h1_state_snapshot ����ʼ�����
```

## Notes
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_201957.md: [WinError 5] 拒绝访问。: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass'
