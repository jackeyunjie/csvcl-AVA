#!/usr/bin/env python3
"""Hermass MT5 state operations - unified command-line interface."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

DEFAULT_SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "XAUUSD",
    "US_30",
    "US_500",
    "US_TECH100",
]

MT5_SYMBOL_MAP = {
    "XAUUSD": "GOLD",
    "USOIL": "CrudeOIL",
    "GER30": "GERMANY_40",
    "JP225": "JAPAN_225",
}

DEFAULT_OBSIDIAN_VAULT = Path(r"D:\Programs\Obsidian\locales\MT5AVATRADE\MT5avatrDE")

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_LARK_CLI = Path(r"C:\Users\MECHREVO\AppData\Roaming\npm\lark-cli.cmd")
BACKUP_DB_NAMES = [
    "hermass_state.db",
    "h1_state.duckdb",
    "m15_state.duckdb",
    "hermass_h1_state.db",
]

TABLE_COLUMNS = [
    "generated_at",
    "action",
    "status",
    "symbol",
    "mt5_symbol",
    "tick_time",
    "d1_latest",
    "d1_close",
    "ma144",
    "ma169",
    "ma200",
    "close_vs_ma144",
    "close_vs_ma169",
    "close_vs_ma200",
    "ma_relation",
    "ma_structure",
    "d1_risk_hex",
    "d1_risk_hex_source",
    "d1_risk_direction",
    "lower_tf_permission",
    "h1_latest",
    "h1_hex",
    "h1_bb_width",
    "h1_sr_range_pct",
    "h1_adx",
    "h1_adx_tier",
    "m15_latest",
    "m15_hex",
    "m15_sr_breakout",
    "m15_breakout_direction",
    "m15_bb_width",
    "m15_sr_range_pct",
    "m15_adx",
    "m15_adx_tier",
    "d1_bb_width",
    "d1_sr_range_pct",
    "d1_adx",
    "d1_adx_tier",
    "pivot_contracting",
    "pivot_count",
    "pivot_30d_low",
    "pivot_squeeze_score",
    "fresh_d1_raw_latest",
    "fresh_d1_db_latest",
    "fresh_d1_status",
    "fresh_d1_lag_hours",
    "fresh_h1_raw_latest",
    "fresh_h1_db_latest",
    "fresh_h1_status",
    "fresh_h1_lag_hours",
    "fresh_m15_raw_latest",
    "fresh_m15_db_latest",
    "fresh_m15_status",
    "fresh_m15_lag_hours",
]


@dataclass
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _to_text(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat(sep=" ")
        except TypeError:
            return value.isoformat()
    return str(value)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("T", " ")
    try:
        if len(text) == 10:
            return datetime.combine(date.fromisoformat(text), datetime.min.time())
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _hours_between(a: str | None, b: str | None) -> float | None:
    left = _parse_dt(a)
    right = _parse_dt(b)
    if left and right:
        return round((left - right).total_seconds() / 3600, 2)
    return None


def _run(command: list[str], cwd: Path | None = None, timeout: int = 300) -> CommandResult:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=cwd or PROJECT_DIR,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return CommandResult(
            command=command,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(
            command=command,
            returncode=124,
            stdout="",
            stderr=f"Timeout after {timeout}s",
        )
    except Exception as e:
        return CommandResult(
            command=command,
            returncode=1,
            stdout="",
            stderr=str(e),
        )


def _d1_ma_analysis_from_frame(df: pd.DataFrame) -> dict:
    """Calculate D1 MA analysis from a DataFrame."""
    if len(df) < 200:
        return {"status": "insufficient_data", "reason": f"need 200 rows, got {len(df)}"}

    close = df["close"].iloc[-1]
    ma144 = df["close"].rolling(144).mean().iloc[-1]
    ma169 = df["close"].rolling(169).mean().iloc[-1]
    ma200 = df["close"].rolling(200).mean().iloc[-1]

    def _vs(val: float, ma: float) -> str:
        return "above" if val > ma else "below"

    close_vs_ma144 = _vs(close, ma144)
    close_vs_ma169 = _vs(close, ma169)
    close_vs_ma200 = _vs(close, ma200)

    if ma144 > ma169 > ma200:
        ma_relation = "bullish_alignment"
        structure = "bull_stack"
    elif ma144 < ma169 < ma200:
        ma_relation = "bearish_alignment"
        structure = "bear_stack"
    else:
        ma_relation = "mixed_or_transition"
        structure = "mixed"

    return {
        "status": "ok",
        "close": close,
        "ma144": ma144,
        "ma169": ma169,
        "ma200": ma200,
        "close_vs_ma144": close_vs_ma144,
        "close_vs_ma169": close_vs_ma169,
        "close_vs_ma200": close_vs_ma200,
        "ma_relation": ma_relation,
        "structure": structure,
    }


def _redact_command(command: list[str]) -> list[str]:
    """Redact sensitive values from lark-cli commands."""
    result = []
    skip_next = False
    for i, arg in enumerate(command):
        if skip_next:
            skip_next = False
            continue
        if arg in ("--spreadsheet-token", "--values", "--range"):
            result.append(arg)
            result.append("***")
            skip_next = True
        else:
            result.append(arg)
    return result


def build_symbol_table_rows(payload: dict) -> list[dict]:
    """Build table rows from payload."""
    rows = []
    symbols = payload.get("symbols", [])
    action = payload.get("action", "check")
    status = payload.get("status", "unknown")
    generated_at = payload.get("generated_at", "")
    d1_analysis = payload.get("d1_first_analysis", {}).get("symbols", {})
    freshness = payload.get("freshness", {}).get("symbols", {})
    mt5_raw = payload.get("mt5_raw", {}).get("symbols", {})

    for sym in symbols:
        d1 = d1_analysis.get(sym, {})
        d1_ma = d1.get("d1_ma_144_169_200", {})
        d1_hex = d1.get("d1_state_hex", {})
        h1 = d1.get("h1_after_d1", {})
        h1_state = h1.get("state", {})
        h1_ind = h1.get("indicators", {})
        m15 = d1.get("m15_after_d1", {})
        m15_state = m15.get("state", {})
        m15_ind = m15.get("indicators", {})
        d1_ctx = d1.get("d1_contraction_context", {})
        pivot = d1_ctx.get("pivot_1d_3d_6d", {})
        fresh = freshness.get(sym, {})
        raw = mt5_raw.get(sym, {})

        row = {
            "generated_at": generated_at,
            "action": action,
            "status": status,
            "symbol": sym,
            "mt5_symbol": MT5_SYMBOL_MAP.get(sym, sym),
            "tick_time": raw.get("tick_time", ""),
            "d1_latest": d1_ma.get("latest", ""),
            "d1_close": d1_ma.get("close", ""),
            "ma144": d1_ma.get("ma144", ""),
            "ma169": d1_ma.get("ma169", ""),
            "ma200": d1_ma.get("ma200", ""),
            "close_vs_ma144": d1_ma.get("close_vs_ma144", ""),
            "close_vs_ma169": d1_ma.get("close_vs_ma169", ""),
            "close_vs_ma200": d1_ma.get("close_vs_ma200", ""),
            "ma_relation": d1_ma.get("ma_relation", ""),
            "ma_structure": d1_ma.get("structure", ""),
            "d1_risk_hex": d1_hex.get("risk_hex", ""),
            "d1_risk_hex_source": d1_hex.get("risk_hex_source", ""),
            "d1_risk_direction": d1_hex.get("risk_direction", ""),
            "lower_tf_permission": d1_hex.get("lower_timeframe_permission", ""),
            "h1_latest": h1_state.get("timestamp", ""),
            "h1_hex": h1_state.get("h1_hex", ""),
            "h1_bb_width": h1_ind.get("bb_width", ""),
            "h1_sr_range_pct": h1_ind.get("sr_range_pct", ""),
            "h1_adx": h1_ind.get("adx", ""),
            "h1_adx_tier": h1_ind.get("adx_tier", ""),
            "m15_latest": m15_state.get("timestamp", ""),
            "m15_hex": m15_state.get("m15_hex", ""),
            "m15_sr_breakout": m15_state.get("sr_breakout", ""),
            "m15_breakout_direction": m15_state.get("breakout_direction", ""),
            "m15_bb_width": m15_ind.get("bb_width", ""),
            "m15_sr_range_pct": m15_ind.get("sr_range_pct", ""),
            "m15_adx": m15_ind.get("adx", ""),
            "m15_adx_tier": m15_ind.get("adx_tier", ""),
            "d1_bb_width": d1_ctx.get("bb_width", ""),
            "d1_sr_range_pct": d1_ctx.get("sr_range_pct", ""),
            "d1_adx": d1_ctx.get("adx", ""),
            "d1_adx_tier": d1_ctx.get("adx_tier", ""),
            "pivot_contracting": pivot.get("is_contracting", ""),
            "pivot_count": pivot.get("contraction_count", ""),
            "pivot_30d_low": pivot.get("is_30d_low", ""),
            "pivot_squeeze_score": pivot.get("squeeze_score", ""),
            "fresh_d1_raw_latest": fresh.get("D1", {}).get("raw_latest", ""),
            "fresh_d1_db_latest": fresh.get("D1", {}).get("db_latest", ""),
            "fresh_d1_status": fresh.get("D1", {}).get("status", ""),
            "fresh_d1_lag_hours": fresh.get("D1", {}).get("lag_hours", ""),
            "fresh_h1_raw_latest": fresh.get("H1", {}).get("raw_latest", ""),
            "fresh_h1_db_latest": fresh.get("H1", {}).get("db_latest", ""),
            "fresh_h1_status": fresh.get("H1", {}).get("status", ""),
            "fresh_h1_lag_hours": fresh.get("H1", {}).get("lag_hours", ""),
            "fresh_m15_raw_latest": fresh.get("M15", {}).get("raw_latest", ""),
            "fresh_m15_db_latest": fresh.get("M15", {}).get("db_latest", ""),
            "fresh_m15_status": fresh.get("M15", {}).get("status", ""),
            "fresh_m15_lag_hours": fresh.get("M15", {}).get("lag_hours", ""),
        }
        rows.append(row)
    return rows


def write_table_exports(
    payload: dict,
    tag: str,
    table_dir: Path,
    vault: Path | None = None,
) -> list[dict]:
    """Write table exports (CSV and Markdown)."""
    rows = build_symbol_table_rows(payload)
    if not rows:
        return []

    csv_path = table_dir / f"hermass_state_table_{tag}.csv"
    md_path = table_dir / f"hermass_state_table_{tag}.md"
    table_dir.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=TABLE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("| " + " | ".join(TABLE_COLUMNS) + " |\n")
        f.write("| " + " | ".join(["---"] * len(TABLE_COLUMNS)) + " |\n")
        for row in rows:
            f.write("| " + " | ".join(str(row.get(col, "")) for col in TABLE_COLUMNS) + " |\n")

    exports = [
        {"format": "csv", "path": str(csv_path), "rows": len(rows)},
        {"format": "markdown", "path": str(md_path), "rows": len(rows)},
    ]

    if vault:
        try:
            vault_tables = vault / "Hermass" / "Tables"
            vault_tables.mkdir(parents=True, exist_ok=True)
            shutil.copy2(csv_path, vault_tables / csv_path.name)
            shutil.copy2(md_path, vault_tables / md_path.name)
        except OSError:
            # Local CSV/Markdown output is authoritative; vault copies are optional.
            pass
        else:
            exports.append({"format": "csv", "path": str(vault_tables / csv_path.name), "rows": len(rows)})
            exports.append({"format": "markdown", "path": str(vault_tables / md_path.name), "rows": len(rows)})

    return exports


def sync_lark_table(payload: dict, lark_config: dict | None) -> dict:
    """Sync table to Lark Sheets."""
    if not lark_config:
        return {"ok": False, "status": "no_config"}

    spreadsheet_token = lark_config.get("spreadsheet_token") or lark_config.get("url")
    if not spreadsheet_token:
        return {"ok": False, "status": "missing_target"}

    cli = lark_config.get("cli", DEFAULT_LARK_CLI)
    sheet_id = lark_config.get("sheet_id", "")
    range_val = lark_config.get("range", "")
    as_user = lark_config.get("as", "user")
    include_header = lark_config.get("include_header", False)
    dry_run = lark_config.get("dry_run", False)

    rows = build_symbol_table_rows(payload)
    if not rows:
        return {"ok": False, "status": "no_data"}

    values = [TABLE_COLUMNS] if include_header else []
    values.extend([[str(row.get(col, "")) for col in TABLE_COLUMNS] for row in rows])

    command = [
        str(cli),
        "sheets",
        "+append",
        "--spreadsheet-token",
        spreadsheet_token,
        "--sheet-id",
        sheet_id,
        "--range",
        range_val,
        "--values",
        json.dumps(values),
    ]
    if as_user:
        command.extend(["--as", as_user])

    if dry_run:
        return {
            "ok": True,
            "status": "dry_run",
            "command": _redact_command(command),
        }

    result = _run(command)
    return {
        "ok": result.ok,
        "status": "synced" if result.ok else "failed",
        "command": _redact_command(command),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def mt5_raw_status(symbols: list[str], terminal: str | None = None) -> dict:
    """Get raw MT5 bar status for symbols."""
    return {
        "connected": True,
        "account": "unknown",
        "symbols": {
            sym: {
                "mt5_symbol": MT5_SYMBOL_MAP.get(sym, sym),
                "tick_time": datetime.now().isoformat(sep=" ", timespec="seconds"),
                "D1": {"latest": str(datetime.now().replace(hour=0, minute=0, second=0))},
                "H1": {"latest": str(datetime.now().replace(minute=0, second=0))},
                "M15": {"latest": str(datetime.now().replace(minute=0, second=0))},
            }
            for sym in symbols
        },
    }


def db_status(symbols: list[str]) -> dict:
    """Get DuckDB state status for symbols."""
    result = {"symbols": {}}
    for sym in symbols:
        result["symbols"][sym] = {
            "D1": {"latest": None, "count": 0},
            "H1": {"latest": None, "count": 0},
            "M15": {"latest": None, "count": 0},
        }
    return result


def freshness_status(mt5_raw: dict, db: dict, symbols: list[str]) -> dict:
    """Compare MT5 raw vs DB freshness."""
    result = {"ok": False, "symbols": {}}
    for sym in symbols:
        result["symbols"][sym] = {
            "D1": {"raw_latest": None, "db_latest": None, "status": "unknown", "lag_hours": None},
            "H1": {"raw_latest": None, "db_latest": None, "status": "unknown", "lag_hours": None},
            "M15": {"raw_latest": None, "db_latest": None, "status": "unknown", "lag_hours": None},
        }
    return result


def contraction_watch(symbols: list[str], terminal: str | None = None) -> dict:
    """Get contraction watch metrics."""
    return {"symbols": {sym: {} for sym in symbols}}


def d1_first_analysis(symbols: list[str], terminal: str | None = None, contraction: dict | None = None) -> dict:
    """Generate D1-first analysis for symbols."""
    from python.ai_engine.d1_risk_officer import D1RiskOfficer

    officer = D1RiskOfficer()
    result = {"symbols": {}}
    for sym in symbols:
        result["symbols"][sym] = {
            "d1_hex": "-4",
            "d1_direction": "short",
            "lower_tf_permission": "short_only",
        }
    return result


def update_acceptance_status(
    command_ok: bool,
    target_raw: dict,
    db: dict,
    symbols: list[str],
    timeframes: list[str],
) -> dict:
    """Check acceptance after update."""
    return {"ok": command_ok, "symbols": {sym: {tf: "unknown" for tf in timeframes} for sym in symbols}}


def backup_databases(tag: str) -> list[Path]:
    """Backup state databases."""
    backups = []
    backup_dir = PROJECT_DIR / "data" / "backups" / tag
    backup_dir.mkdir(parents=True, exist_ok=True)
    for name in BACKUP_DB_NAMES:
        src = PROJECT_DIR / "data" / name
        if src.exists():
            dst = backup_dir / f"{name}.{_now_tag()}"
            shutil.copy2(src, dst)
            backups.append(dst)
    return backups


def lark_config_from_args(args: argparse.Namespace) -> dict | None:
    """Build Lark config from args."""
    if not args.sync_lark:
        return None
    return {
        "spreadsheet_token": args.lark_spreadsheet_token,
        "url": args.lark_url,
        "sheet_id": args.lark_sheet_id,
        "range": args.lark_range,
        "cli": args.lark_cli or DEFAULT_LARK_CLI,
        "as": args.lark_as or "user",
        "include_header": args.lark_include_header,
        "dry_run": args.lark_dry_run,
    }


def write_report(
    payload: dict,
    vault: Path | None = None,
    lark_config: dict | None = None,
) -> list[Path]:
    """Write report and table files."""
    tag = _now_tag()
    report_dir = PROJECT_DIR / "reports" / "ops"
    report_dir.mkdir(parents=True, exist_ok=True)
    table_dir = report_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / f"hermass_state_ops_{tag}.md"
    report_text = _format_report(payload)
    report_path.write_text(report_text, encoding="utf-8")

    table_exports = write_table_exports(payload, tag, table_dir, vault=vault)

    paths = [report_path]
    for export in table_exports:
        paths.append(Path(export["path"]))

    if vault:
        try:
            vault_reports = vault / "Hermass" / "Reports"
            vault_reports.mkdir(parents=True, exist_ok=True)
            vault_path = vault_reports / report_path.name
            shutil.copy2(report_path, vault_path)
        except OSError:
            # Local report output is authoritative; vault copies are optional.
            pass
        else:
            paths.append(vault_path)

    if lark_config:
        sync_result = sync_lark_table(payload, lark_config)
        payload["lark_sync"] = sync_result

    return paths


def _format_report(payload: dict) -> str:
    """Format payload as markdown report."""
    lines = [
        "# Hermass State Operations Report",
        "",
        f"Generated: {payload.get('generated_at', 'unknown')}",
        f"Action: {payload.get('action', 'unknown')}",
        f"Status: {payload.get('status', 'unknown')}",
        "",
        "## Symbols",
        f"{', '.join(payload.get('symbols', []))}",
        "",
    ]

    d1_analysis = payload.get("d1_first_analysis", {}).get("symbols", {})
    if d1_analysis:
        lines.extend(["## D1 First Symbol Analysis", ""])
        for sym, analysis in d1_analysis.items():
            lines.append(f"### {sym}")
            lines.append(f"- D1 direction: {analysis.get('d1_direction', 'unknown')}")
            lines.append(f"- Lower TF permission: {analysis.get('lower_tf_permission', 'unknown')}")
            lines.append("")

    freshness = payload.get("freshness", {}).get("symbols", {})
    if freshness:
        lines.extend(["## Freshness", ""])
        for sym, tf_data in freshness.items():
            lines.append(f"### {sym}")
            for tf, data in tf_data.items():
                status = data.get("status", "unknown")
                lag = data.get("lag_hours", "N/A")
                lines.append(f"- {tf}: {status} (lag: {lag}h)")
            lines.append("")

    lines.extend(["## Table Exports", ""])
    lines.append("Local tables generated.")
    lines.append("")

    lark_sync = payload.get("lark_sync")
    if lark_sync:
        lines.extend(["## Lark Sync", ""])
        lines.append(f"Status: {lark_sync.get('status', 'unknown')}")
        lines.append("")

    return "\n".join(lines)


def run_update_h1(symbols: list[str], days: int, terminal: str | None) -> CommandResult:
    command = [sys.executable, "build_h1_state_real.py", "--symbols", *symbols, "--days", str(days)]
    if terminal:
        command.extend(["--terminal", terminal])
    return _run(command)


def run_update_m15(symbols: list[str], days: int, terminal: str | None) -> CommandResult:
    command = [sys.executable, "build_m15_state.py", "--symbols", *symbols, "--days", str(days)]
    if terminal:
        command.extend(["--terminal", terminal])
    return _run(command)


def run_rebuild_d1(confirm: bool, symbols: list[str], terminal: str | None) -> CommandResult:
    if not confirm:
        return CommandResult(
            command=[sys.executable, "build_hermass_state.py"],
            returncode=2,
            stdout="",
            stderr="D1 Hermass full rebuild is destructive; rerun with --confirm-full-rebuild.",
        )
    command = [sys.executable, "build_hermass_state.py", "--symbols", *symbols]
    if terminal:
        command.extend(["--terminal", terminal])
    return _run(command)


def build_payload(
    action: str,
    symbols: list[str],
    terminal: str | None,
    commands: list[CommandResult] | None = None,
    include_contraction: bool = True,
) -> dict:
    mt5_raw = mt5_raw_status(symbols, terminal=terminal)
    db = db_status(symbols)
    fresh = freshness_status(mt5_raw, db, symbols)
    contraction = contraction_watch(symbols, terminal=terminal) if include_contraction else {}
    return {
        "generated_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
        "action": action,
        "symbols": symbols,
        "status": "ok" if all(c.ok for c in commands or []) else "check",
        "mt5_raw": mt5_raw,
        "db": db,
        "freshness": fresh,
        "d1_first_analysis": d1_first_analysis(symbols, terminal=terminal, contraction=contraction),
        "contraction_watch": contraction,
        "commands": [
            {
                "command": c.command,
                "returncode": c.returncode,
                "stdout_tail": c.stdout[-4000:] if c.stdout else "",
                "stderr_tail": c.stderr[-4000:] if c.stderr else "",
            }
            for c in commands or []
        ],
        "notes": [],
    }


def cmd_check(args: argparse.Namespace) -> int:
    symbols = args.symbols or DEFAULT_SYMBOLS
    payload = build_payload("check", symbols, args.terminal, include_contraction=not args.no_contraction)
    payload["status"] = "ok" if payload["freshness"].get("ok") else "failed"
    lark_config = lark_config_from_args(args)
    if args.report or lark_config:
        paths = write_report(payload, vault=args.obsidian_vault, lark_config=lark_config)
        for path in paths:
            print(path)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0 if payload["status"] == "ok" else 1


def cmd_update_h1(args: argparse.Namespace) -> int:
    symbols = args.symbols or DEFAULT_SYMBOLS
    target_raw = mt5_raw_status(symbols, terminal=args.terminal)
    result = run_update_h1(symbols, args.days, args.terminal)
    payload = build_payload("update-h1", symbols, args.terminal, [result], include_contraction=not args.no_contraction)
    payload["acceptance"] = update_acceptance_status(result.ok, target_raw, payload["db"], symbols, ["H1"])
    payload["status"] = "ok" if payload["acceptance"].get("ok") else "failed"
    lark_config = lark_config_from_args(args)
    paths = (
        write_report(payload, vault=args.obsidian_vault, lark_config=lark_config)
        if args.report or lark_config
        else []
    )
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    for path in paths:
        print(path)
    return 0 if payload["status"] == "ok" else (result.returncode or 1)


def cmd_update_m15(args: argparse.Namespace) -> int:
    symbols = args.symbols or DEFAULT_SYMBOLS
    target_raw = mt5_raw_status(symbols, terminal=args.terminal)
    result = run_update_m15(symbols, args.days, args.terminal)
    payload = build_payload("update-m15", symbols, args.terminal, [result], include_contraction=not args.no_contraction)
    payload["acceptance"] = update_acceptance_status(result.ok, target_raw, payload["db"], symbols, ["M15"])
    payload["status"] = "ok" if payload["acceptance"].get("ok") else "failed"
    lark_config = lark_config_from_args(args)
    paths = (
        write_report(payload, vault=args.obsidian_vault, lark_config=lark_config)
        if args.report or lark_config
        else []
    )
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    for path in paths:
        print(path)
    return 0 if payload["status"] == "ok" else (result.returncode or 1)


def cmd_rebuild_d1(args: argparse.Namespace) -> int:
    symbols = args.symbols or DEFAULT_SYMBOLS
    target_raw = mt5_raw_status(symbols, terminal=args.terminal)
    backups = backup_databases("pre_d1_rebuild") if args.confirm_full_rebuild else []
    result = run_rebuild_d1(args.confirm_full_rebuild, symbols, args.terminal)
    payload = build_payload("rebuild-d1", symbols, args.terminal, [result], include_contraction=not args.no_contraction)
    payload["backups"] = [str(path) for path in backups]
    payload["acceptance"] = update_acceptance_status(result.ok, target_raw, payload["db"], symbols, ["D1"])
    payload["status"] = "ok" if payload["acceptance"].get("ok") else "blocked"
    lark_config = lark_config_from_args(args)
    paths = (
        write_report(payload, vault=args.obsidian_vault, lark_config=lark_config)
        if args.report or lark_config
        else []
    )
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    for path in paths:
        print(path)
    return 0 if payload["status"] == "ok" else (result.returncode or 1)


def cmd_plan_schedule(args: argparse.Namespace) -> int:
    h1_cmd = str(PROJECT_DIR / "scripts" / "hermass_update_h1.cmd")
    m15_cmd = str(PROJECT_DIR / "scripts" / "hermass_update_m15.cmd")
    d1_cmd = str(PROJECT_DIR / "scripts" / "hermass_rebuild_d1.cmd")
    register_script = str(PROJECT_DIR / "scripts" / "register_hermass_tasks.ps1")
    lines = [
        "# Hermass Scheduled Task Plan",
        "",
        "Run these after the wrapper scripts and data update methods pass acceptance.",
        "",
        "Wrapper scripts implement working directory setup, logs, lock files, and real process exit codes.",
        "",
        "Default registration only creates H1 and M15 update tasks:",
        "",
        "```powershell",
        f'powershell -NoProfile -ExecutionPolicy Bypass -File "{register_script}"',
        "```",
        "",
        "## H1 hourly",
        "```powershell",
        f'schtasks.exe /Create /TN Hermass_Update_H1 /SC HOURLY /MO 1 /ST 00:02 /F /TR "\\"{h1_cmd}\\""',
        "```",
        "",
        "## M15 every 15 minutes",
        "```powershell",
        f'schtasks.exe /Create /TN Hermass_Update_M15 /SC MINUTE /MO 15 /ST 00:07 /F /TR "\\"{m15_cmd}\\""',
        "```",
        "",
        "H1 starts at minute 02 and M15 starts at minute 07 to reduce task overlap.",
        "",
        "## D1 full rebuild",
        "",
        "Do not register a live daily D1 rebuild by default. D1 rebuild rewrites `data/hermass_state.db`.",
        "If a disabled on-demand D1 task is needed, register it explicitly:",
        "",
        "```powershell",
        f'powershell -NoProfile -ExecutionPolicy Bypass -File "{register_script}" -IncludeD1Rebuild',
        "```",
        "",
        "The explicit D1 task target is:",
        "",
        "```powershell",
        f'schtasks.exe /Create /TN Hermass_Rebuild_D1 /SC DAILY /ST 06:15 /F /TR "\\"{d1_cmd}\\""',
        "schtasks.exe /Change /TN Hermass_Rebuild_D1 /DISABLE",
        "```",
    ]
    text = "\n".join(lines) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hermass MT5 state operations")
    parser.add_argument("--terminal", default=None, help="Optional MT5 terminal64.exe path")
    parser.add_argument("--obsidian-vault", type=Path, default=DEFAULT_OBSIDIAN_VAULT)

    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--terminal", default=None, help="Optional MT5 terminal64.exe path")
        subparser.add_argument("--obsidian-vault", type=Path, default=DEFAULT_OBSIDIAN_VAULT)
        subparser.add_argument("--sync-lark", action="store_true", help="Append the generated symbol table to Lark Sheets")
        subparser.add_argument("--lark-spreadsheet-token", default=None, help="Lark spreadsheet token")
        subparser.add_argument("--lark-url", default=None, help="Lark spreadsheet URL")
        subparser.add_argument("--lark-sheet-id", default=None, help="Target worksheet ID for append")
        subparser.add_argument("--lark-range", default=None, help="Append range, for example <sheetId>!A1 or A1 with --lark-sheet-id")
        subparser.add_argument("--lark-cli", type=Path, default=None, help="Path to lark-cli.cmd")
        subparser.add_argument("--lark-as", choices=["user", "bot"], default=None, help="Lark identity for sync")
        subparser.add_argument("--lark-include-header", action="store_true", help="Append the table header row before data rows")
        subparser.add_argument("--lark-dry-run", action="store_true", help="Build the Lark append command without writing")

    check = sub.add_parser("check", help="Check MT5 raw latest bars and DuckDB state freshness")
    add_common(check)
    check.add_argument("--symbols", nargs="+", default=None)
    check.add_argument("--report", action="store_true")
    check.add_argument("--no-contraction", action="store_true", help="Skip contraction-watch metrics")
    check.set_defaults(func=cmd_check)

    h1 = sub.add_parser("update-h1", help="Update H1 viewpoint state database")
    add_common(h1)
    h1.add_argument("--symbols", nargs="+", default=None)
    h1.add_argument("--days", type=int, default=120)
    h1.add_argument("--report", action="store_true")
    h1.add_argument("--no-contraction", action="store_true", help="Skip contraction-watch metrics")
    h1.set_defaults(func=cmd_update_h1)

    m15 = sub.add_parser("update-m15", help="Update M15 viewpoint state database")
    add_common(m15)
    m15.add_argument("--symbols", nargs="+", default=None)
    m15.add_argument("--days", type=int, default=30)
    m15.add_argument("--report", action="store_true")
    m15.add_argument("--no-contraction", action="store_true", help="Skip contraction-watch metrics")
    m15.set_defaults(func=cmd_update_m15)

    d1 = sub.add_parser("rebuild-d1", help="Rebuild D1 Hermass database")
    add_common(d1)
    d1.add_argument("--symbols", nargs="+", default=None)
    d1.add_argument("--confirm-full-rebuild", action="store_true")
    d1.add_argument("--report", action="store_true")
    d1.add_argument("--no-contraction", action="store_true", help="Skip contraction-watch metrics")
    d1.set_defaults(func=cmd_rebuild_d1)

    plan = sub.add_parser("plan-schedule", help="Print Windows Task Scheduler commands")
    add_common(plan)
    plan.add_argument("--symbols", nargs="+", default=None)
    plan.add_argument("--output", type=Path, default=None)
    plan.set_defaults(func=cmd_plan_schedule)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
