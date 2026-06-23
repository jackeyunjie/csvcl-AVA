"""
Trade Opportunity Journal CLI MVP

Local DuckDB-based manual recording system for Hermass trading opportunities.
Implements MT5_AI_Trading/docs/TRADE_OPPORTUNITY_JOURNAL_PRD_20260611.md.

Commands:
    python trade_journal.py init
    python trade_journal.py add
    python trade_journal.py list [--limit N]
    python trade_journal.py show --id <opportunity_id>
    python trade_journal.py export-json --output <path>
    python trade_journal.py export-csv --output <path>

Hard restrictions:
- No trading actions.
- No MT5 order API calls.
- No scheduled tasks.
- No State Hex -> direction mappings.
- Data stays local under MT5_AI_Trading/data/.
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORKSPACE = Path(__file__).resolve().parent
DATA_DIR = WORKSPACE / "data"
DB_PATH = DATA_DIR / "trade_journal.duckdb"
EXPORT_DIR = DATA_DIR / "trade_journal_exports"
ASSETS_DIR = DATA_DIR / "trade_journal_assets"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trade_opportunities (
    opportunity_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    observed_at TIMESTAMP NOT NULL,
    trade_date DATE,
    opportunity_type TEXT NOT NULL,
    core_logic TEXT NOT NULL,
    confidence_note TEXT,
    timeframe_context TEXT,
    d1_view_state TEXT,
    h1_view_state TEXT,
    mn1_state TEXT,
    w1_state TEXT,
    d1_state TEXT,
    ef_count INTEGER,
    d1_risk_direction TEXT,
    sqx_evidence_tags TEXT,
    key_price DOUBLE,
    trigger_price DOUBLE,
    invalid_price DOUBLE,
    target_price DOUBLE,
    screenshot_path TEXT,
    chart_note TEXT,
    execution_status TEXT DEFAULT 'planned',
    entry_price DOUBLE,
    exit_price DOUBLE,
    result_r DOUBLE,
    result_pct DOUBLE,
    review_outcome TEXT,
    review_tags TEXT,
    review_note TEXT,
    forward_return_1h DOUBLE,
    forward_return_4h DOUBLE,
    forward_return_1d DOUBLE,
    json_exported_at TIMESTAMP,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ---------------------------------------------------------------------------
# Controlled vocabularies (from PRD section 6)
# ---------------------------------------------------------------------------

OPPORTUNITY_TYPES = {
    "state_regime_observation",
    "sqx_contraction",
    "pivot_breakout",
    "rsioma_momentum",
    "d1_h1_alignment",
    "fundamental_event",
    "missed_trade",
    "failed_setup",
}

EXECUTION_STATUSES = {
    "planned",
    "taken",
    "missed",
    "not_taken",
    "closed",
}

REVIEW_OUTCOMES = {
    "worked",
    "failed",
    "too_early",
    "too_late",
    "invalidated",
    "no_trade",
    "data_insufficient",
}

REVIEW_TAGS = {
    "early_entry",
    "late_entry",
    "missed_entry",
    "false_breakout",
    "trend_continuation",
    "mean_reversion",
    "news_driven",
    "range_bound",
    "momentum_strength",
    "momentum_failure",
    "risk_too_wide",
    "risk_too_tight",
    "good_setup_bad_execution",
    "bad_setup_good_outcome",
    "clean_invalidated",
    "post_event_move",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> duckdb.DuckDBPyConnection:
    ensure_dirs()
    return duckdb.connect(str(DB_PATH))


def init_db() -> None:
    ensure_dirs()
    conn = get_connection()
    try:
        conn.execute(CREATE_TABLE_SQL)
        print(f"[init] Database ready: {DB_PATH}")
        print(f"[init] Export dir: {EXPORT_DIR}")
        print(f"[init] Assets dir: {ASSETS_DIR}")
    finally:
        conn.close()


def prompt_input(
    label: str,
    required: bool = False,
    default: Optional[str] = None,
    allowed: Optional[set] = None,
) -> Optional[str]:
    suffix = " (required)" if required else ""
    if default is not None:
        suffix += f" [{default}]"
    if allowed:
        suffix += f" [{'/'.join(sorted(allowed))}]"
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value == "":
            if required and default is None:
                print("  -> This field is required.")
                continue
            value = default
        if allowed and value is not None and value not in allowed:
            print(f"  -> Allowed values: {', '.join(sorted(allowed))}")
            continue
        return value


def prompt_number(label: str, required: bool = False, default: Optional[str] = None) -> Optional[float]:
    while True:
        value = prompt_input(label, required=required, default=default)
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            print("  -> Please enter a valid number.")


def prompt_int(label: str, required: bool = False, default: Optional[str] = None) -> Optional[int]:
    while True:
        value = prompt_input(label, required=required, default=default)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            print("  -> Please enter a valid integer.")


def generate_id() -> str:
    return f"opp_{uuid.uuid4().hex[:12]}"


def parse_observed_at(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse observed_at: {value}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init() -> None:
    init_db()


def cmd_add() -> None:
    conn = get_connection()
    try:
        print("\n--- Add new trade opportunity ---")
        print("Tip: leave optional fields blank and press Enter.\n")

        record: Dict[str, Any] = {}
        record["opportunity_id"] = generate_id()
        record["symbol"] = prompt_input("Symbol (e.g. EURUSD, XAUUSD)", required=True)

        observed_at_str = prompt_input("Observed at (YYYY-MM-DD HH:MM)", default=datetime.now().strftime("%Y-%m-%d %H:%M"))
        record["observed_at"] = parse_observed_at(observed_at_str)

        record["trade_date"] = prompt_input("Trade date (YYYY-MM-DD)", default=record["observed_at"].strftime("%Y-%m-%d"))
        record["opportunity_type"] = prompt_input(
            "Opportunity type",
            required=True,
            allowed=OPPORTUNITY_TYPES,
        )
        record["core_logic"] = prompt_input("Core logic / why it looked good", required=True)
        record["confidence_note"] = prompt_input("Confidence note")
        record["timeframe_context"] = prompt_input("Timeframe context (e.g. D1+H1)")

        # Optional context fields
        record["d1_view_state"] = prompt_input("D1 view state (free text)")
        record["h1_view_state"] = prompt_input("H1 view state (free text)")
        record["mn1_state"] = prompt_input("MN1 State Hex")
        record["w1_state"] = prompt_input("W1 State Hex")
        record["d1_state"] = prompt_input("D1 State Hex")
        record["ef_count"] = prompt_int("EF count")
        record["d1_risk_direction"] = prompt_input("D1 Risk Direction (long/short/neutral)")
        record["sqx_evidence_tags"] = prompt_input("SQX evidence tags (comma separated)")

        # Prices
        record["key_price"] = prompt_number("Key price")
        record["trigger_price"] = prompt_number("Trigger price")
        record["invalid_price"] = prompt_number("Invalid price")
        record["target_price"] = prompt_number("Target price")

        record["screenshot_path"] = prompt_input("Screenshot path")
        record["chart_note"] = prompt_input("Chart note")
        record["execution_status"] = prompt_input(
            "Execution status",
            default="planned",
            allowed=EXECUTION_STATUSES,
        )
        record["entry_price"] = prompt_number("Entry price")
        record["exit_price"] = prompt_number("Exit price")
        record["result_r"] = prompt_number("Result (R)")
        record["result_pct"] = prompt_number("Result (%)")
        record["review_outcome"] = prompt_input(
            "Review outcome (required when reviewed)",
            allowed=REVIEW_OUTCOMES,
        )
        record["review_tags"] = prompt_input("Review tags (comma separated)")
        record["review_note"] = prompt_input("Review note")
        record["forward_return_1h"] = prompt_number("Forward return 1h (%)")
        record["forward_return_4h"] = prompt_number("Forward return 4h (%)")
        record["forward_return_1d"] = prompt_number("Forward return 1d (%)")
        record["json_exported_at"] = None
        record["created_by"] = prompt_input("Created by", default=os.environ.get("USER", "manual"))
        record["created_at"] = datetime.now()
        record["updated_at"] = datetime.now()

        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))
        sql = f"INSERT INTO trade_opportunities ({columns}) VALUES ({placeholders})"
        conn.execute(sql, list(record.values()))

        print(f"\n[add] Created opportunity: {record['opportunity_id']}")
    finally:
        conn.close()


def cmd_list(limit: int = 20) -> None:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT opportunity_id, symbol, observed_at, opportunity_type,
                   execution_status, d1_risk_direction, created_at
            FROM trade_opportunities
            ORDER BY observed_at DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()

        if not rows:
            print("[list] No records found.")
            return

        print(f"\n--- Latest {len(rows)} opportunities ---")
        print(f"{'ID':<20} {'Symbol':<10} {'Observed':<20} {'Type':<22} {'Status':<12} {'D1 Risk':<10}")
        print("-" * 100)
        for row in rows:
            oid, symbol, observed_at, opp_type, status, d1_risk, _ = row
            print(f"{oid:<20} {symbol:<10} {str(observed_at):<20} {opp_type:<22} {status or '-':<12} {d1_risk or '-':<10}")
    finally:
        conn.close()


def cmd_show(opportunity_id: str) -> None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM trade_opportunities WHERE opportunity_id = ?",
            [opportunity_id],
        ).fetchone()

        if row is None:
            print(f"[show] Opportunity not found: {opportunity_id}")
            sys.exit(1)

        columns = [desc[0] for desc in conn.description]
        record = dict(zip(columns, row))

        # Convert datetime/date objects to ISO strings for readability
        for key, value in record.items():
            if isinstance(value, datetime):
                record[key] = value.isoformat()
            elif hasattr(value, "isoformat"):
                record[key] = value.isoformat()

        print(json.dumps(record, indent=2, ensure_ascii=False))
    finally:
        conn.close()


def cmd_export_json(output_path: str) -> None:
    conn = get_connection()
    try:
        df = conn.execute("SELECT * FROM trade_opportunities").fetchdf()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_json(out, orient="records", indent=2, force_ascii=False, date_format="iso")

        # Mark export timestamp in database
        conn.execute(
            "UPDATE trade_opportunities SET json_exported_at = CURRENT_TIMESTAMP WHERE json_exported_at IS NULL"
        )

        print(f"[export-json] Wrote {len(df)} records to {out}")
    finally:
        conn.close()


def cmd_export_csv(output_path: str) -> None:
    conn = get_connection()
    try:
        df = conn.execute("SELECT * FROM trade_opportunities").fetchdf()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"[export-csv] Wrote {len(df)} records to {out}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trade Opportunity Journal CLI (local DuckDB MVP)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize database and directories")

    subparsers.add_parser("add", help="Add a new opportunity record interactively")

    list_parser = subparsers.add_parser("list", help="List recent opportunities")
    list_parser.add_argument("--limit", type=int, default=20, help="Max records to show")

    show_parser = subparsers.add_parser("show", help="Show one opportunity as JSON")
    show_parser.add_argument("--id", required=True, dest="opportunity_id", help="Opportunity ID")

    export_json_parser = subparsers.add_parser("export-json", help="Export all records to JSON")
    export_json_parser.add_argument(
        "--output",
        default=str(EXPORT_DIR / "opportunities.json"),
        help="Output file path",
    )

    export_csv_parser = subparsers.add_parser("export-csv", help="Export all records to CSV")
    export_csv_parser.add_argument(
        "--output",
        default=str(EXPORT_DIR / "opportunities.csv"),
        help="Output file path",
    )

    args = parser.parse_args()

    if args.command == "init":
        cmd_init()
    elif args.command == "add":
        cmd_add()
    elif args.command == "list":
        cmd_list(args.limit)
    elif args.command == "show":
        cmd_show(args.opportunity_id)
    elif args.command == "export-json":
        cmd_export_json(args.output)
    elif args.command == "export-csv":
        cmd_export_csv(args.output)


if __name__ == "__main__":
    main()
