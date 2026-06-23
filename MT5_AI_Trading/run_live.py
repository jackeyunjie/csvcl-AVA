"""Live runner for Hermass MT5 state pipeline."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from python.ai_engine.d1_risk_officer import D1RiskOfficer, gate_signal_fields

positions: dict[str, Any] = {}


def add_signal(signal: Any) -> None:
    """Add a signal to the tracking system."""
    positions[signal.symbol] = signal


def send_signal_to_mt5(bridge: Any, signal: Any, live: bool = False) -> bool:
    """Send signal to MT5 via bridge, with D1 risk officer gate."""
    officer = D1RiskOfficer()
    decision = officer.assess_signal(signal, "H1")
    if not decision.allowed:
        return False
    if live and bridge:
        bridge.send_command(signal)
    add_signal(signal)
    return True


def main() -> None:
    """Run live Hermass state checks."""
    import argparse
    parser = argparse.ArgumentParser(description="Live runner for Hermass MT5 state pipeline")
    parser.add_argument("--symbols", nargs="+", default=["EURUSD"])
    parser.add_argument("--terminal", default="AVATRADE")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--no-contraction", action="store_true")
    args = parser.parse_args()
    print(f"Live run at {datetime.now().isoformat()}")
    print(f"Symbols: {args.symbols}")


if __name__ == "__main__":
    main()
