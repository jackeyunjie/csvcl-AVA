# Hermass MT5 State Ops Report

- generated_at: 2026-06-09 21:51:16
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
    "balance": 178.66,
    "equity": 180.42
  },
  "symbols": {
    "EURUSD": {
      "mt5_symbol": "EURUSD",
      "tick_time": "2026-06-09 21:51:14",
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
      "tick_time": "2026-06-09 21:51:14",
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
      "tick_time": "2026-06-09 21:51:14",
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
      "tick_time": "2026-06-09 21:51:14",
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
      "tick_time": "2026-06-09 21:51:14",
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
      "tick_time": "2026-06-09 21:51:14",
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
      "tick_time": "2026-06-09 21:51:14",
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
        "bb_width": 0.014950264644076613,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.6060993741571903,
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
            "1d": 1.1557633333333335,
            "3d": 1.1533777777777778,
            "6d": 1.156525
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
        "bb_width": 0.005272716091518878,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.44172054908197744,
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
        "bb_width": 0.002028608806976444,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.24117423325611753,
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
        "bb_width": 0.013595250260900698,
        "bb_squeezed_20": true,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.5421920465567385,
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
            "1d": 1.3381333333333334,
            "3d": 1.3348622222222222,
            "6d": 1.3382005555555556
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
        "bb_width": 0.007495611663722459,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.6125494292322652,
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
        "bb_width": 0.0019766885967523904,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.2387525180929711,
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
        "bb_width": 0.012980448245671985,
        "bb_squeezed_20": true,
        "bb_squeezed_10": true,
        "sr_range_pct": 1.1237428127282674,
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
            "1d": 160.1676666666667,
            "3d": 160.19411111111114,
            "6d": 160.06255555555555
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
        "bb_width": 0.0007869551188955976,
        "bb_squeezed_20": true,
        "bb_squeezed_10": true,
        "sr_range_pct": 0.14234075627891835,
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
        "bb_width": 0.000428086279455574,
        "bb_squeezed_20": true,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.05119272813539455,
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
        "bb_width": 0.0740922083139646,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 7.524588275941481,
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
            "1d": 4339.9766666666665,
            "3d": 4328.883333333334,
            "6d": 4381.791666666667
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
        "bb_width": 0.006640320984720973,
        "bb_squeezed_20": true,
        "bb_squeezed_10": true,
        "sr_range_pct": 1.1652654612461166,
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
        "bb_width": 0.004668900378423675,
        "bb_squeezed_20": true,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.9068294368305859,
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
        "bb_width": 0.04116556368713269,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 5.193361546112292,
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
            "1d": 51089.666666666664,
            "3d": 50937.777777777774,
            "6d": 51047.94444444444
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
        "bb_width": 0.009081468011363817,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.2286210191703884,
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
        "bb_width": 0.007142443819444676,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.8834370185463267,
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
        "bb_width": 0.043293467144520224,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 3.7086535248914134,
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
            "1d": 7454.25,
            "3d": 7421.333333333333,
            "6d": 7471.902777777778
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
        "bb_width": 0.010476601130961579,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.3464751085867022,
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
        "bb_width": 0.005385484024119852,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.7417307049782826,
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
        "bb_width": 0.07712742523509192,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 7.189893380533349,
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
            "1d": 29650.25,
            "3d": 29343.916666666668,
            "6d": 29697.25
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
        "bb_width": 0.016163877263346723,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 1.8169769061060825,
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
        "bb_width": 0.004986684711446426,
        "bb_squeezed_20": false,
        "bb_squeezed_10": false,
        "sr_range_pct": 0.7516211024335411,
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

## Commands

```text
C:\Users\MECHREVO\AppData\Local\Programs\Python\Python312\python.exe build_m15_state.py --symbols EURUSD GBPUSD USDJPY XAUUSD US_30 US_500 US_TECH100 --days 30
returncode=0
==================================================
EURUSD M15 State ���ݿ�ժҪ:
{
  "symbol": "EURUSD",
  "total_rows": 2115,
  "earliest": "2026-05-11 05:00:00",
  "latest": "2026-06-09 21:30:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:30:00
    M15=-0, H1=0, D1=-5
    SRͻ��=False, ����=none

==================================================
GBPUSD M15 State ���ݿ�ժҪ:
{
  "symbol": "GBPUSD",
  "total_rows": 2083,
  "earliest": "2026-05-11 05:00:00",
  "latest": "2026-06-09 21:30:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:30:00
    M15=-0, H1=0, D1=-1
    SRͻ��=False, ����=none

==================================================
USDJPY M15 State ���ݿ�ժҪ:
{
  "symbol": "USDJPY",
  "total_rows": 2083,
  "earliest": "2026-05-11 05:00:00",
  "latest": "2026-06-09 21:30:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:30:00
    M15=0, H1=0, D1=5
    SRͻ��=False, ����=none

==================================================
XAUUSD M15 State ���ݿ�ժҪ:
{
  "symbol": "XAUUSD",
  "total_rows": 1985,
  "earliest": "2026-05-11 06:00:00",
  "latest": "2026-06-09 21:30:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:30:00
    M15=-1, H1=-1, D1=-D
    SRͻ��=False, ����=none

==================================================
US_30 M15 State ���ݿ�ժҪ:
{
  "symbol": "US_30",
  "total_rows": 3825,
  "earliest": "2026-04-14 14:15:00",
  "latest": "2026-06-09 21:30:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:30:00
    M15=1, H1=5, D1=9
    SRͻ��=False, ����=none

  SRͻ��ͳ��:
    down: 32 ��
    up: 9 ��

==================================================
US_500 M15 State ���ݿ�ժҪ:
{
  "symbol": "US_500",
  "total_rows": 3825,
  "earliest": "2026-04-14 14:00:00",
  "latest": "2026-06-09 21:30:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:30:00
    M15=1, H1=5, D1=-D
    SRͻ��=False, ����=none

  SRͻ��ͳ��:
    up: 5 ��
    down: 14 ��

==================================================
US_TECH100 M15 State ���ݿ�ժҪ:
{
  "symbol": "US_TECH100",
  "total_rows": 3825,
  "earliest": "2026-04-14 13:45:00",
  "latest": "2026-06-09 21:30:00"
}

  ���¼�¼:
    ʱ��: 2026-06-09 21:30:00
    M15=1, H1=5, D1=-D
    SRͻ��=False, ����=none

  SRͻ��ͳ��:
    down: 3 ��
   D1: 26 ��
2026-06-09 21:46:18,489 [INFO] ��ȡ����: US_30 H4 | 135�� | 2026-05-11 04:00:00 ~ 2026-06-09 20:00:00
2026-06-09 21:46:18,489 [INFO]   H4: 135 ��
2026-06-09 21:46:18,495 [INFO] ��ȡ����: US_30 H1 | 495�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:00:00
2026-06-09 21:46:18,495 [INFO]   H1: 495 ��
2026-06-09 21:46:19,076 [INFO] ��ȡ����: US_30 M30 | 990�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:30:00
2026-06-09 21:46:19,076 [INFO]   M30: 990 ��
2026-06-09 21:46:19,083 [INFO] ��ȡ����: US_30 M15 | 1979�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:30:00
2026-06-09 21:46:19,083 [INFO]   M15: 1979 ��
2026-06-09 21:48:00,397 [INFO] US_30 ���� 1979 ��M15 State
2026-06-09 21:48:00,403 [INFO]   �ѱ���: 1979 �� M15 State
2026-06-09 21:48:00,403 [INFO] 
============================================================
2026-06-09 21:48:00,403 [INFO] ���� M15 State: US_500 (US_500) | 30��
2026-06-09 21:48:00,403 [INFO] ============================================================
2026-06-09 21:48:00,408 [INFO] ��ȡ����: US_500 MN1 | 1�� | 2026-06-01 08:00:00 ~ 2026-06-01 08:00:00
2026-06-09 21:48:00,408 [INFO]   MN1: 1 ��
2026-06-09 21:48:00,411 [INFO] ��ȡ����: US_500 W1 | 4�� | 2026-05-17 08:00:00 ~ 2026-06-07 08:00:00
2026-06-09 21:48:00,411 [INFO]   W1: 4 ��
2026-06-09 21:48:00,414 [INFO] ��ȡ����: US_500 D1 | 26�� | 2026-05-11 08:00:00 ~ 2026-06-09 08:00:00
2026-06-09 21:48:00,414 [INFO]   D1: 26 ��
2026-06-09 21:48:00,418 [INFO] ��ȡ����: US_500 H4 | 135�� | 2026-05-11 04:00:00 ~ 2026-06-09 20:00:00
2026-06-09 21:48:00,418 [INFO]   H4: 135 ��
2026-06-09 21:48:00,422 [INFO] ��ȡ����: US_500 H1 | 495�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:00:00
2026-06-09 21:48:00,423 [INFO]   H1: 495 ��
2026-06-09 21:48:00,427 [INFO] ��ȡ����: US_500 M30 | 990�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:30:00
2026-06-09 21:48:00,427 [INFO]   M30: 990 ��
2026-06-09 21:48:00,434 [INFO] ��ȡ����: US_500 M15 | 1978�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:30:00
2026-06-09 21:48:00,434 [INFO]   M15: 1978 ��
2026-06-09 21:49:40,160 [INFO] US_500 ���� 1978 ��M15 State
2026-06-09 21:49:40,164 [INFO]   �ѱ���: 1978 �� M15 State
2026-06-09 21:49:40,164 [INFO] 
============================================================
2026-06-09 21:49:40,164 [INFO] ���� M15 State: US_TECH100 (US_TECH100) | 30��
2026-06-09 21:49:40,164 [INFO] ============================================================
2026-06-09 21:49:40,487 [INFO] ��ȡ����: US_TECH100 MN1 | 1�� | 2026-06-01 08:00:00 ~ 2026-06-01 08:00:00
2026-06-09 21:49:40,487 [INFO]   MN1: 1 ��
2026-06-09 21:49:40,827 [INFO] ��ȡ����: US_TECH100 W1 | 4�� | 2026-05-17 08:00:00 ~ 2026-06-07 08:00:00
2026-06-09 21:49:40,827 [INFO]   W1: 4 ��
2026-06-09 21:49:40,830 [INFO] ��ȡ����: US_TECH100 D1 | 26�� | 2026-05-11 08:00:00 ~ 2026-06-09 08:00:00
2026-06-09 21:49:40,830 [INFO]   D1: 26 ��
2026-06-09 21:49:41,260 [INFO] ��ȡ����: US_TECH100 H4 | 135�� | 2026-05-11 04:00:00 ~ 2026-06-09 20:00:00
2026-06-09 21:49:41,260 [INFO]   H4: 135 ��
2026-06-09 21:49:41,264 [INFO] ��ȡ����: US_TECH100 H1 | 495�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:00:00
2026-06-09 21:49:41,264 [INFO]   H1: 495 ��
2026-06-09 21:49:41,715 [INFO] ��ȡ����: US_TECH100 M30 | 990�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:30:00
2026-06-09 21:49:41,715 [INFO]   M30: 990 ��
2026-06-09 21:49:41,722 [INFO] ��ȡ����: US_TECH100 M15 | 1977�� | 2026-05-11 06:00:00 ~ 2026-06-09 21:30:00
2026-06-09 21:49:41,722 [INFO]   M15: 1977 ��
2026-06-09 21:51:13,740 [INFO] US_TECH100 ���� 1977 ��M15 State
2026-06-09 21:51:13,746 [INFO]   �ѱ���: 1977 �� M15 State
2026-06-09 21:51:13,950 [INFO] M15StateDB �����ѹر�
2026-06-09 21:51:13,950 [INFO] MT5�����Ž����ѶϿ�
2026-06-09 21:51:13,950 [INFO] 
============================================================
2026-06-09 21:51:13,950 [INFO] ������ɣ��ܼ�: 14168 �� M15 State
2026-06-09 21:51:13,950 [INFO] ============================================================
2026-06-09 21:51:13,978 [INFO] m15_state_snapshot ����ʼ�����
2026-06-09 21:51:14,034 [INFO] M15StateDB �����ѹر�
```

## Notes
- Report export failures: D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE\Hermass\Reports\hermass_state_ops_20260609_215116.md: [WinError 5] 拒绝访问。: 'D:\\Programs\\Obsidian\\locales\\MT5AVATRADE\\MT5avatrDE\\Hermass'
