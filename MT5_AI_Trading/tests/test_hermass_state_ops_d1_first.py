from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermass_state_ops import (
    TABLE_COLUMNS,
    _d1_ma_analysis_from_frame,
    _redact_command,
    build_symbol_table_rows,
    sync_lark_table,
    write_table_exports,
)


def test_d1_ma_analysis_bull_stack():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=220, freq="D"),
            "close": [float(i) for i in range(1, 221)],
        }
    )

    result = _d1_ma_analysis_from_frame(df)

    assert result["status"] == "ok"
    assert result["close_vs_ma144"] == "above"
    assert result["close_vs_ma169"] == "above"
    assert result["close_vs_ma200"] == "above"
    assert result["ma_relation"] == "bullish_alignment"
    assert result["structure"] == "bull_stack"


def test_d1_ma_analysis_bear_stack():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=220, freq="D"),
            "close": [float(i) for i in range(220, 0, -1)],
        }
    )

    result = _d1_ma_analysis_from_frame(df)

    assert result["status"] == "ok"
    assert result["close_vs_ma144"] == "below"
    assert result["close_vs_ma169"] == "below"
    assert result["close_vs_ma200"] == "below"
    assert result["ma_relation"] == "bearish_alignment"
    assert result["structure"] == "bear_stack"


def _sample_payload():
    return {
        "generated_at": "2026-06-10 10:00:00",
        "action": "check",
        "status": "ok",
        "symbols": ["EURUSD"],
        "mt5_raw": {
            "symbols": {
                "EURUSD": {
                    "mt5_symbol": "EURUSD",
                    "tick_time": "2026-06-10 10:00:00",
                }
            }
        },
        "freshness": {
            "symbols": {
                "EURUSD": {
                    "D1": {
                        "raw_latest": "2026-06-10 00:00:00",
                        "db_latest": "2026-06-10",
                        "status": "fresh",
                        "lag_hours": 0.0,
                    },
                    "H1": {
                        "raw_latest": "2026-06-10 09:00:00",
                        "db_latest": "2026-06-10 09:00:00",
                        "status": "fresh",
                        "lag_hours": 0.0,
                    },
                    "M15": {
                        "raw_latest": "2026-06-10 09:45:00",
                        "db_latest": "2026-06-10 09:45:00",
                        "status": "fresh",
                        "lag_hours": 0.0,
                    },
                }
            }
        },
        "d1_first_analysis": {
            "symbols": {
                "EURUSD": {
                    "d1_ma_144_169_200": {
                        "latest": "2026-06-10 00:00:00",
                        "close": 1.1,
                        "ma144": 1.08,
                        "ma169": 1.07,
                        "ma200": 1.06,
                        "close_vs_ma144": "above",
                        "close_vs_ma169": "above",
                        "close_vs_ma200": "above",
                        "ma_relation": "bullish_alignment",
                        "structure": "bull_stack",
                    },
                    "d1_state_hex": {
                        "risk_hex": "B+H",
                        "risk_hex_source": "h1_state_snapshot.d1_hex",
                        "risk_direction": "long",
                        "lower_timeframe_permission": "long_only",
                    },
                    "h1_after_d1": {
                        "state": {"timestamp": "2026-06-10 09:00:00", "h1_hex": "8"},
                        "indicators": {
                            "bb_width": 0.01,
                            "sr_range_pct": 0.15,
                            "adx": 12.5,
                            "adx_tier": "compressed_lt_13",
                        },
                    },
                    "m15_after_d1": {
                        "state": {
                            "timestamp": "2026-06-10 09:45:00",
                            "m15_hex": "6",
                            "sr_breakout": True,
                            "breakout_direction": "up",
                        },
                        "indicators": {
                            "bb_width": 0.005,
                            "sr_range_pct": 0.08,
                            "adx": 8.5,
                            "adx_tier": "extreme_compressed_lt_9",
                        },
                    },
                    "d1_contraction_context": {
                        "bb_width": 0.03,
                        "sr_range_pct": 0.3,
                        "adx": 18.0,
                        "adx_tier": "weak_trend_lt_20",
                        "pivot_1d_3d_6d": {
                            "is_contracting": True,
                            "contraction_count": 2,
                            "is_30d_low": False,
                            "squeeze_score": 55,
                        },
                    },
                }
            }
        },
    }


def test_build_symbol_table_rows_maps_d1_first_fields():
    row = build_symbol_table_rows(_sample_payload())[0]

    assert row["symbol"] == "EURUSD"
    assert row["ma_structure"] == "bull_stack"
    assert row["d1_risk_hex"] == "B+H"
    assert row["d1_risk_direction"] == "long"
    assert row["lower_tf_permission"] == "long_only"
    assert row["h1_adx_tier"] == "compressed_lt_13"
    assert row["m15_sr_breakout"] is True
    assert row["pivot_contracting"] is True
    assert row["fresh_m15_status"] == "fresh"


def test_write_table_exports_creates_csv_and_markdown(tmp_path):
    exports = write_table_exports(_sample_payload(), "test", tmp_path, vault=tmp_path / "missing_vault")

    csv_export = next(item for item in exports if item["format"] == "csv")
    md_export = next(item for item in exports if item["format"] == "markdown")

    assert Path(csv_export["path"]).exists()
    assert Path(md_export["path"]).exists()
    assert csv_export["rows"] == 1
    assert "d1_risk_direction" in Path(csv_export["path"]).read_text(encoding="utf-8-sig")
    assert "| generated_at | action | status | symbol |" in Path(md_export["path"]).read_text(encoding="utf-8")


def test_lark_sync_missing_target_does_not_call_cli(tmp_path):
    result = sync_lark_table(
        _sample_payload(),
        {"cli": tmp_path / "lark-cli.cmd", "sheet_id": "sheet123", "range": "A1"},
    )

    assert result["status"] == "missing_target"
    assert not result["ok"]


def test_lark_command_redaction_hides_target_and_values():
    redacted = _redact_command(
        [
            "lark-cli.cmd",
            "sheets",
            "+append",
            "--spreadsheet-token",
            "secret-token",
            "--values",
            "[[1]]",
        ]
    )

    assert "secret-token" not in redacted
    assert "[[1]]" not in redacted
    assert redacted[-1] == "***"
    assert "d1_risk_hex" in TABLE_COLUMNS
