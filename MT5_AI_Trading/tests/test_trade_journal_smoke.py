"""
Smoke tests for trade_journal.py

Run with: pytest tests/test_trade_journal_smoke.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import trade_journal as tj


@pytest.fixture
def temp_journal(tmp_path):
    """Create an isolated journal in a temp directory."""
    original_db_path = tj.DB_PATH
    original_data_dir = tj.DATA_DIR
    original_export_dir = tj.EXPORT_DIR
    original_assets_dir = tj.ASSETS_DIR

    tj.DATA_DIR = tmp_path / "data"
    tj.DB_PATH = tj.DATA_DIR / "trade_journal.duckdb"
    tj.EXPORT_DIR = tj.DATA_DIR / "trade_journal_exports"
    tj.ASSETS_DIR = tj.DATA_DIR / "trade_journal_assets"

    yield tj

    # Restore
    tj.DB_PATH = original_db_path
    tj.DATA_DIR = original_data_dir
    tj.EXPORT_DIR = original_export_dir
    tj.ASSETS_DIR = original_assets_dir


def test_init_creates_database_and_dirs(temp_journal):
    temp_journal.init_db()
    assert temp_journal.DB_PATH.exists()
    assert temp_journal.EXPORT_DIR.exists()
    assert temp_journal.ASSETS_DIR.exists()

    conn = duckdb.connect(str(temp_journal.DB_PATH))
    try:
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = 'trade_opportunities'"
        ).fetchall()
        assert len(tables) == 1
    finally:
        conn.close()


def test_add_and_list_record(temp_journal):
    temp_journal.init_db()

    record = {
        "opportunity_id": temp_journal.generate_id(),
        "symbol": "EURUSD",
        "observed_at": temp_journal.parse_observed_at("2026-06-11 14:00"),
        "trade_date": "2026-06-11",
        "opportunity_type": "pivot_breakout",
        "core_logic": "Price broke above 1D pivot top with D1 long permission",
        "confidence_note": "High confidence due to D1 Risk long",
        "timeframe_context": "D1+H1",
        "d1_view_state": "bullish trend, ADX > 25",
        "h1_view_state": "price above 1D pivot top",
        "mn1_state": "8",
        "w1_state": "6",
        "d1_state": "8",
        "ef_count": 3,
        "d1_risk_direction": "long",
        "sqx_evidence_tags": "rsioma_momentum,pivot_breakout",
        "key_price": 1.0850,
        "trigger_price": 1.0860,
        "invalid_price": 1.0820,
        "target_price": 1.0920,
        "screenshot_path": None,
        "chart_note": "Clean breakout above pivot range",
        "execution_status": "planned",
        "entry_price": None,
        "exit_price": None,
        "result_r": None,
        "result_pct": None,
        "review_outcome": None,
        "review_tags": None,
        "review_note": None,
        "forward_return_1h": None,
        "forward_return_4h": None,
        "forward_return_1d": None,
        "json_exported_at": None,
        "created_by": "manual",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    conn = temp_journal.get_connection()
    try:
        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))
        conn.execute(
            f"INSERT INTO trade_opportunities ({columns}) VALUES ({placeholders})",
            list(record.values()),
        )

        rows = conn.execute(
            "SELECT COUNT(*) FROM trade_opportunities"
        ).fetchone()
        assert rows[0] == 1
    finally:
        conn.close()


def test_export_json_and_csv(temp_journal):
    temp_journal.init_db()

    record = {
        "opportunity_id": temp_journal.generate_id(),
        "symbol": "XAUUSD",
        "observed_at": temp_journal.parse_observed_at("2026-06-11 10:00"),
        "trade_date": "2026-06-11",
        "opportunity_type": "rsioma_momentum",
        "core_logic": "RSIOMA golden cross near 1D pivot support",
        "confidence_note": "Medium confidence",
        "timeframe_context": "H1",
        "execution_status": "taken",
        "entry_price": 2345.50,
        "exit_price": 2350.00,
        "result_r": 1.5,
        "result_pct": 0.19,
        "review_outcome": "worked",
        "review_tags": "momentum_strength,good_setup_bad_execution",
        "review_note": "Target hit but entry was slightly late",
        "forward_return_1h": 0.10,
        "forward_return_4h": 0.15,
        "forward_return_1d": 0.22,
        "created_by": "manual",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    conn = temp_journal.get_connection()
    try:
        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))
        conn.execute(
            f"INSERT INTO trade_opportunities ({columns}) VALUES ({placeholders})",
            list(record.values()),
        )
    finally:
        conn.close()

    json_out = temp_journal.EXPORT_DIR / "test.json"
    csv_out = temp_journal.EXPORT_DIR / "test.csv"

    temp_journal.cmd_export_json(str(json_out))
    temp_journal.cmd_export_csv(str(csv_out))

    assert json_out.exists()
    assert csv_out.exists()
    assert json_out.stat().st_size > 0
    assert csv_out.stat().st_size > 0


def test_controlled_vocabularies_are_defined():
    """Ensure PRD-controlled vocabularies exist and contain expected values."""
    assert "pivot_breakout" in tj.OPPORTUNITY_TYPES
    assert "rsioma_momentum" in tj.OPPORTUNITY_TYPES
    assert "taken" in tj.EXECUTION_STATUSES
    assert "worked" in tj.REVIEW_OUTCOMES
    assert "false_breakout" in tj.REVIEW_TAGS
