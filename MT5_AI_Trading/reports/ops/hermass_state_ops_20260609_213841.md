# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 21:38:40
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
    "equity": 158.19
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 21:38:39",
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
      "tick_time": "2026-06-09 21:38:39",
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
      "tick_time": "2026-06-09 21:38:39",
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
      "tick_time": "2026-06-09 21:38:39",
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
      "tick_time": "2026-06-09 21:38:39",
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
      "tick_time": "2026-06-09 21:38:39",
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
      "tick_time": "2026-06-09 21:38:39",
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
{
  "status": "ok",
  "reference": {
    "project_modules": [
      "python.analytics.squeeze_observer.SqueezeObserver",
      "python.ai_engine.pivot_contraction.detect_contraction",
      "SQUEEZE_README.md"
    ],
    "sqx_blocks": [
      "D:\\SQX136\\custom_indicators\\MetaTrader5\\Indicators\\SqSRPercentRank.mq5",
      "D:\\SQX136\\custom_indicators\\MetaTrader5\\Indicators\\SqPivots.mq5"
    ],
    "metrics": [
      "SR support/resistance multi-timeframe contraction",
      "1D/3D/6D pivot contraction",
      "Bollinger Band width multi-timeframe contraction",
      "ADX contraction thresholds: <20, <13, <9"
    ]
  },
  "symbols": {
    "EURUSD": {
      "D1": {
        "status": "ok",
        "latest": "2026-06-09 08:00:00",
        "rows": 223,
        "bb_width": 0.015031283737848613,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.6067104808024937,
        "sr_squeezed_20": true,
        "adx": 16.270255025619715,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 1,
          "is_30d_low": false,
          "squeeze_score": 0,
          "pivots": {
            "1d": 1.1556166666666667,
            "3d": 1.1533288888888888,
            "6d": 1.1565005555555554
          },
          "ranges": {
            "1d": 0.005109999999999948,
            "3d": 0.004106666666666629,
            "6d": 0.005596666666666657
          },
          "details": {
            "1d": {
              "contracting": false,
              "low": "False"
            },
            "3d": {
              "contracting": false,
              "low": "False"
            },
            "6d": {
              "contracting": false,
              "low": "False"
            }
          }
        }
      },
      "H1": {
        "status": "ok",
        "latest": "2026-06-09 21:00:00",
        "rows": 1008,
        "bb_width": 0.005157427131360966,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.44188861985471706,
        "sr_squeezed_20": false,
        "adx": 21.493073398135145,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:30:00",
        "rows": 1344,
        "bb_width": 0.0024003664793518635,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.2845036319612604,
        "sr_squeezed_20": false,
        "adx": 42.67870796444006,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      }
    },
    "GBPUSD": {
      "D1": {
        "status": "ok",
        "latest": "2026-06-09 08:00:00",
        "rows": 223,
        "bb_width": 0.013660737955458215,
        "bb_squeezed_20": true,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.5431131019036928,
        "sr_squeezed_20": true,
        "adx": 15.73569529783518,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 1,
          "is_30d_low": false,
          "squeeze_score": 0,
          "pivots": {
            "1d": 1.33779,
            "3d": 1.3347477777777776,
            "6d": 1.3381433333333332
          },
          "ranges": {
            "1d": 0.007769999999999833,
            "3d": 0.005386666666666577,
            "6d": 0.007214999999999934
          },
          "details": {
            "1d": {
              "contracting": false,
              "low": "False"
            },
            "3d": {
              "contracting": false,
              "low": "False"
            },
            "6d": {
              "contracting": false,
              "low": "False"
            }
          }
        }
      },
      "H1": {
        "status": "ok",
        "latest": "2026-06-09 21:00:00",
        "rows": 1008,
        "bb_width": 0.007302896091924085,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.5957446808510545,
        "sr_squeezed_20": false,
        "adx": 27.97274134249702,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:30:00",
        "rows": 1344,
        "bb_width": 0.0022321109419186783,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.2642777155655003,
        "sr_squeezed_20": false,
        "adx": 48.83182984167393,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      }
    },
    "USDJPY": {
      "D1": {
        "status": "ok",
        "latest": "2026-06-09 08:00:00",
        "rows": 223,
        "bb_width": 0.01303812580477132,
        "bb_squeezed_20": true,
        "bb_squeezed_10": true,
        "sr_range_pct": 1.1235113474646166,
        "sr_squeezed_20": true,
        "adx": 15.46718051117419,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 1,
          "is_30d_low": true,
          "squeeze_score": 0,
          "pivots": {
            "1d": 160.17866666666666,
            "3d": 160.1977777777778,
            "6d": 160.06438888888889
          },
          "ranges": {
            "1d": 0.22800000000000864,
            "3d": 0.3216666666666678,
            "6d": 0.4581666666666611
          },
          "details": {
            "1d": {
              "contracting": false,
              "low": "True"
            },
            "3d": {
              "contracting": false,
              "low": "True"
            },
            "6d": {
              "contracting": false,
              "low": "False"
            }
          }
        }
      },
      "H1": {
        "status": "ok",
        "latest": "2026-06-09 21:00:00",
        "rows": 1008,
        "bb_width": 0.0007983214986170627,
        "bb_squeezed_20": true,
        "bb_squeezed_10": true,
        "sr_range_pct": 0.1423114373455226,
        "sr_squeezed_20": true,
        "adx": 12.059080697130627,
        "adx_lt_20": true,
        "adx_lt_13": true,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:30:00",
        "rows": 1344,
        "bb_width": 0.000418943784477834,
        "bb_squeezed_20": true,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.04930966469426717,
        "sr_squeezed_20": true,
        "adx": 10.9720663949083,
        "adx_lt_20": true,
        "adx_lt_13": true,
        "adx_lt_9": false
      }
    },
    "XAUUSD": {
      "D1": {
        "status": "ok",
        "latest": "2026-06-09 08:00:00",
        "rows": 222,
        "bb_width": 0.07482706505136709,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 7.540602177144584,
        "sr_squeezed_20": false,
        "adx": 30.51697536740014,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 2,
          "is_30d_low": true,
          "squeeze_score": 0,
          "pivots": {
            "1d": 4332.87,
            "3d": 4326.514444444445,
            "6d": 4380.607222222222
          },
          "ranges": {
            "1d": 36.3700000000008,
            "3d": 52.843333333333554,
            "6d": 77.98999999999994
          },
          "details": {
            "1d": {
              "contracting": false,
              "low": "True"
            },
            "3d": {
              "contracting": false,
              "low": "True"
            },
            "6d": {
              "contracting": false,
              "low": "True"
            }
          }
        }
      },
      "H1": {
        "status": "ok",
        "latest": "2026-06-09 21:00:00",
        "rows": 964,
        "bb_width": 0.006369570594789628,
        "bb_squeezed_20": true,
        "bb_squeezed_10": true,
        "sr_range_pct": 0.8884467301282626,
        "sr_squeezed_20": true,
        "adx": 15.101725079282694,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:30:00",
        "rows": 1278,
        "bb_width": 0.0047692205408336324,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.49073467088923656,
        "sr_squeezed_20": true,
        "adx": 16.94401077052516,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false
      }
    },
    "US_30": {
      "D1": {
        "status": "ok",
        "latest": "2026-06-09 08:00:00",
        "rows": 223,
        "bb_width": 0.04074374770654097,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 5.204729795758819,
        "sr_squeezed_20": false,
        "adx": 36.1748957003158,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 3,
          "is_30d_low": false,
          "squeeze_score": 0,
          "pivots": {
            "1d": 51015.0,
            "3d": 50912.88888888888,
            "6d": 51035.5
          },
          "ranges": {
            "1d": 518.0,
            "3d": 484.6666666666667,
            "6d": 701.3333333333334
          },
          "details": {
            "1d": {
              "contracting": false,
              "low": "False"
            },
            "3d": {
              "contracting": false,
              "low": "False"
            },
            "6d": {
              "contracting": false,
              "low": "False"
            }
          }
        }
      },
      "H1": {
        "status": "ok",
        "latest": "2026-06-09 21:00:00",
        "rows": 962,
        "bb_width": 0.007689495782835658,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.0124108277142578,
        "sr_squeezed_20": false,
        "adx": 15.539430653974037,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:30:00",
        "rows": 1272,
        "bb_width": 0.00492763427239027,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.6664712205609303,
        "sr_squeezed_20": false,
        "adx": 20.707434032960823,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      }
    },
    "US_500": {
      "D1": {
        "status": "ok",
        "latest": "2026-06-09 08:00:00",
        "rows": 223,
        "bb_width": 0.04345637246374442,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 3.7161031134917977,
        "sr_squeezed_20": false,
        "adx": 29.68028009277999,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 1,
          "is_30d_low": false,
          "squeeze_score": 0,
          "pivots": {
            "1d": 7442.5,
            "3d": 7417.416666666667,
            "6d": 7469.944444444445
          },
          "ranges": {
            "1d": 80.5,
            "3d": 73.75,
            "6d": 104.125
          },
          "details": {
            "1d": {
              "contracting": false,
              "low": "False"
            },
            "3d": {
              "contracting": false,
              "low": "False"
            },
            "6d": {
              "contracting": false,
              "low": "False"
            }
          }
        }
      },
      "H1": {
        "status": "ok",
        "latest": "2026-06-09 21:00:00",
        "rows": 962,
        "bb_width": 0.009479320257028254,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.0780046869769,
        "sr_squeezed_20": false,
        "adx": 24.188119842883825,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:30:00",
        "rows": 1272,
        "bb_width": 0.0031646212890701093,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.47204553063274185,
        "sr_squeezed_20": false,
        "adx": 22.390002611798845,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      }
    },
    "US_TECH100": {
      "D1": {
        "status": "ok",
        "latest": "2026-06-09 08:00:00",
        "rows": 223,
        "bb_width": 0.07719980042101518,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 7.211732633279483,
        "sr_squeezed_20": false,
        "adx": 31.586473844470664,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 1,
          "is_30d_low": false,
          "squeeze_score": 0,
          "pivots": {
            "1d": 29587.083333333332,
            "3d": 29322.86111111111,
            "6d": 29686.72222222222
          },
          "ranges": {
            "1d": 442.25,
            "3d": 497.3333333333333,
            "6d": 643.2083333333334
          },
          "details": {
            "1d": {
              "contracting": false,
              "low": "False"
            },
            "3d": {
              "contracting": false,
              "low": "False"
            },
            "6d": {
              "contracting": false,
              "low": "False"
            }
          }
        }
      },
      "H1": {
        "status": "ok",
        "latest": "2026-06-09 21:00:00",
        "rows": 962,
        "bb_width": 0.015118569934361975,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.4884558427571353,
        "sr_squeezed_20": false,
        "adx": 13.387675090416284,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:30:00",
        "rows": 1272,
        "bb_width": 0.003357416613422828,
        "bb_squeezed_20": true,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.419864028002154,
        "sr_squeezed_20": true,
        "adx": 24.374123640369362,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      }
    }
  },
  "errors": []
}
```

## Notes
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_213841.md: [WinError 5] 拒绝访问。: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass'
