# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 21:52:10
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
    "balance": 178.66,
    "equity": 180.31
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 21:52:08",
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
        "latest": "2026-06-09 21:45:00"
      }
    },
    "GBPUSD": {
      "mt5_symbol": "GBPUSD",
      "tick_time": "2026-06-09 21:52:08",
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
        "latest": "2026-06-09 21:45:00"
      }
    },
    "USDJPY": {
      "mt5_symbol": "USDJPY",
      "tick_time": "2026-06-09 21:52:08",
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
        "latest": "2026-06-09 21:45:00"
      }
    },
    "XAUUSD": {
      "mt5_symbol": "GOLD",
      "tick_time": "2026-06-09 21:52:09",
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
        "latest": "2026-06-09 21:45:00"
      }
    },
    "US_30": {
      "mt5_symbol": "US_30",
      "tick_time": "2026-06-09 21:52:09",
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
        "latest": "2026-06-09 21:45:00"
      }
    },
    "US_500": {
      "mt5_symbol": "US_500",
      "tick_time": "2026-06-09 21:52:09",
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
        "latest": "2026-06-09 21:45:00"
      }
    },
    "US_TECH100": {
      "mt5_symbol": "US_TECH100",
      "tick_time": "2026-06-09 21:52:09",
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
        "latest": "2026-06-09 21:45:00"
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
        "ok": true,
        "raw_latest": "2026-06-09 21:00:00",
        "db_latest": "2026-06-09 21:00:00",
        "lag_hours": 0.0,
        "status": "fresh"
      },
      "M15": {
        "ok": false,
        "raw_latest": "2026-06-09 21:45:00",
        "db_latest": "2026-06-09 21:30:00",
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
        "raw_latest": "2026-06-09 21:45:00",
        "db_latest": "2026-06-09 21:30:00",
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
        "raw_latest": "2026-06-09 21:45:00",
        "db_latest": "2026-06-09 21:30:00",
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
        "raw_latest": "2026-06-09 21:45:00",
        "db_latest": "2026-06-09 21:30:00",
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
        "raw_latest": "2026-06-09 21:45:00",
        "db_latest": "2026-06-09 21:30:00",
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
        "raw_latest": "2026-06-09 21:45:00",
        "db_latest": "2026-06-09 21:30:00",
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
        "raw_latest": "2026-06-09 21:45:00",
        "db_latest": "2026-06-09 21:30:00",
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
        "bb_width": 0.014957330477277313,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.6061549100968222,
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
            "1d": 1.15575,
            "3d": 1.1533733333333334,
            "6d": 1.1565227777777778
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
        "bb_width": 0.005261427415373031,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.44173582295988484,
        "sr_squeezed_20": false,
        "adx": 21.493073398135145,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:45:00",
        "rows": 1344,
        "bb_width": 0.0020270790385714978,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.2411825726141139,
        "sr_squeezed_20": false,
        "adx": 41.41999743121464,
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
        "bb_width": 0.013607444854521195,
        "bb_squeezed_20": true,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.5423876788072772,
        "sr_squeezed_20": true,
        "adx": 15.69489079409899,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 1,
          "is_30d_low": false,
          "squeeze_score": 0,
          "pivots": {
            "1d": 1.3380766666666668,
            "3d": 1.3348433333333334,
            "6d": 1.3381911111111109
          },
          "ranges": {
            "1d": 0.008000000000000007,
            "3d": 0.005463333333333302,
            "6d": 0.0072533333333332966
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
        "bb_width": 0.007451858819751877,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.612627133188575,
        "sr_squeezed_20": false,
        "adx": 27.879002698234828,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:45:00",
        "rows": 1344,
        "bb_width": 0.0019539004848422095,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.23878280465328672,
        "sr_squeezed_20": false,
        "adx": 48.014871485635275,
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
        "bb_width": 0.013001147054493475,
        "bb_squeezed_20": true,
        "bb_squeezed_10": true,
        "sr_range_pct": 1.1236586325074513,
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
            "1d": 160.17166666666665,
            "3d": 160.19544444444443,
            "6d": 160.0632222222222
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
        "bb_width": 0.0007861260249024489,
        "bb_squeezed_20": true,
        "bb_squeezed_10": true,
        "sr_range_pct": 0.14233009345094833,
        "sr_squeezed_20": true,
        "adx": 11.948872269861402,
        "adx_lt_20": true,
        "adx_lt_13": true,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:45:00",
        "rows": 1344,
        "bb_width": 0.00044055477807607596,
        "bb_squeezed_20": true,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.05118889325866848,
        "sr_squeezed_20": true,
        "adx": 10.490377929617855,
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
        "bb_width": 0.07424753859715873,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 7.528038879965695,
        "sr_squeezed_20": false,
        "adx": 30.312447019142088,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 2,
          "is_30d_low": true,
          "squeeze_score": 0,
          "pivots": {
            "1d": 4339.3133333333335,
            "3d": 4328.662222222223,
            "6d": 4381.681111111111
          },
          "ranges": {
            "1d": 48.470000000000255,
            "3d": 56.8766666666667,
            "6d": 80.0066666666665
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
        "bb_width": 0.006540760702907844,
        "bb_squeezed_20": true,
        "bb_squeezed_10": true,
        "sr_range_pct": 1.1657729611647163,
        "sr_squeezed_20": true,
        "adx": 16.228144489610198,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:45:00",
        "rows": 1278,
        "bb_width": 0.004577172782590098,
        "bb_squeezed_20": true,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.9072243819145015,
        "sr_squeezed_20": false,
        "adx": 18.933092296135023,
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
        "bb_width": 0.04122889227480581,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 5.191842782500196,
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
            "1d": 51094.666666666664,
            "3d": 50939.44444444444,
            "6d": 51048.777777777774
          },
          "ranges": {
            "1d": 630.0,
            "3d": 522.0,
            "6d": 720.0
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
        "bb_width": 0.009283692856689717,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.228261717226858,
        "sr_squeezed_20": false,
        "adx": 16.33790328420681,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:45:00",
        "rows": 1272,
        "bb_width": 0.007327053008199635,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.8831786633393122,
        "sr_squeezed_20": false,
        "adx": 23.914216520067097,
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
        "bb_width": 0.04328521166294809,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 3.708157947484466,
        "sr_squeezed_20": false,
        "adx": 29.891420890599584,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 1,
          "is_30d_low": false,
          "squeeze_score": 0,
          "pivots": {
            "1d": 7454.583333333333,
            "3d": 7421.444444444444,
            "6d": 7471.958333333333
          },
          "ranges": {
            "1d": 100.75,
            "3d": 80.5,
            "6d": 107.5
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
        "bb_width": 0.010550706578097464,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.346295182735351,
        "sr_squeezed_20": false,
        "adx": 25.402963262916515,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:45:00",
        "rows": 1272,
        "bb_width": 0.005472983418747442,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.7416315894968932,
        "sr_squeezed_20": false,
        "adx": 25.41415604933598,
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
        "bb_width": 0.07712955082803023,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 7.191522209729658,
        "sr_squeezed_20": false,
        "adx": 31.7824584797642,
        "adx_lt_20": false,
        "adx_lt_13": false,
        "adx_lt_9": false,
        "pivot_1d_3d_6d": {
          "is_contracting": false,
          "contraction_count": 1,
          "is_30d_low": false,
          "squeeze_score": 0,
          "pivots": {
            "1d": 29648.0,
            "3d": 29343.166666666668,
            "6d": 29696.875
          },
          "ranges": {
            "1d": 541.5,
            "3d": 530.4166666666666,
            "6d": 659.75
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
        "bb_width": 0.01607203382932865,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.8173885318252754,
        "sr_squeezed_20": false,
        "adx": 14.740584240877086,
        "adx_lt_20": true,
        "adx_lt_13": false,
        "adx_lt_9": false
      },
      "M15": {
        "status": "ok",
        "latest": "2026-06-09 21:45:00",
        "rows": 1272,
        "bb_width": 0.004854609814926678,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.7517913778926348,
        "sr_squeezed_20": false,
        "adx": 24.132482298392542,
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
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_215211.md: [WinError 5] 拒绝访问。: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass'
