from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple


@dataclass(frozen=True)
class D1RiskDecision:
    allowed: bool
    d1_direction: str
    trade_direction: str
    lower_timeframe: str
    reason: str


class D1RiskOfficer:
    """Top-level gate: lower-timeframe trades must not violate D1 direction."""

    NEUTRAL_ALIASES = {"N/A", "NULL", "0", "-0", "N", "="}
    LONG_ALIASES = {"BUY", "BULL", "LONG", "UP"}
    SHORT_ALIASES = {"BEAR", "DOWN", "SELL", "SHORT"}

    def direction_from_hex(self, d1_hex: str) -> str:
        """Extract direction from D1 state hex."""
        if not d1_hex:
            return "neutral"
        clean = d1_hex.strip().upper()
        # Check exact neutral aliases first (including "-0")
        if clean in self.NEUTRAL_ALIASES:
            return "neutral"
        # Legacy composite state hex compatibility
        if any(op in clean for op in ("+", "-", "=")):
            if "+" in clean or clean.startswith(("A", "B")):
                return "long"
            if "-" in clean or clean.startswith(("D", "E")):
                return "short"
            if "=" in clean or clean.startswith("C"):
                return "neutral"
        # Numeric hex values
        try:
            val = int(clean.lstrip("+-"))
            if val > 0:
                return "long"
            if val < 0:
                return "short"
        except ValueError:
            pass
        # Text-based direction
        if any(text in clean for text in self.LONG_ALIASES):
            return "long"
        if any(text in clean for text in self.SHORT_ALIASES):
            return "short"
        return "neutral"

    def normalize_trade_direction(self, direction_or_action: str) -> str:
        """Normalize trade direction to long/short/neutral."""
        if not direction_or_action:
            return "neutral"
        text = direction_or_action.strip().upper()
        if any(text.startswith(alias) for alias in self.LONG_ALIASES):
            return "long"
        if any(text.startswith(alias) for alias in self.SHORT_ALIASES):
            return "short"
        if any(text.startswith(alias) for alias in self.NEUTRAL_ALIASES):
            return "neutral"
        if text in {"HOLD", "FLAT", "NONE", "WATCH", "OBSERVE"}:
            return "neutral"
        return "neutral"

    def assess(
        self,
        d1_hex: str,
        trade_direction: str,
        lower_timeframe: str,
    ) -> D1RiskDecision:
        """Assess whether a trade direction is allowed given D1 state."""
        d1_direction = self.direction_from_hex(d1_hex)
        normalized_trade = self.normalize_trade_direction(trade_direction)

        # Neutral/unknown D1: only allow non-directional actions
        if d1_direction == "neutral":
            allowed = normalized_trade == "neutral"
            reason = (
                "D1 is neutral/unknown; lower timeframe must observe"
                if not allowed
                else "non-directional action"
            )
            return D1RiskDecision(
                allowed=allowed,
                d1_direction=d1_direction,
                trade_direction=normalized_trade,
                lower_timeframe=lower_timeframe,
                reason=reason,
            )

        # Directional D1: trade must align
        if d1_direction == "long" and normalized_trade == "short":
            return D1RiskDecision(
                allowed=False,
                d1_direction=d1_direction,
                trade_direction=normalized_trade,
                lower_timeframe=lower_timeframe,
                reason="short violates D1 long",
            )
        if d1_direction == "short" and normalized_trade == "long":
            return D1RiskDecision(
                allowed=False,
                d1_direction=d1_direction,
                trade_direction=normalized_trade,
                lower_timeframe=lower_timeframe,
                reason="long violates D1 short",
            )

        # Aligned or neutral trade
        return D1RiskDecision(
            allowed=True,
            d1_direction=d1_direction,
            trade_direction=normalized_trade,
            lower_timeframe=lower_timeframe,
            reason="aligns with D1",
        )

    def assess_signal(self, signal: Any, lower_timeframe: str) -> D1RiskDecision:
        """Assess a signal object that has final_signal and d1_hex attributes."""
        d1_hex = getattr(signal, "d1_hex", "")
        final_signal = getattr(signal, "final_signal", "")
        return self.assess(d1_hex, final_signal, lower_timeframe)


def gate_signal_fields(
    final_signal: str,
    confidence: float,
    reason: str,
    d1_hex: str,
    lower_timeframe: str,
) -> Tuple[str, float, str, D1RiskDecision]:
    """Gate signal fields through D1 risk officer."""
    decision = D1RiskOfficer().assess(d1_hex, final_signal, lower_timeframe)
    if not decision.allowed:
        return (
            "HOLD",
            0.0,
            f"blocked_by_d1_risk_officer: {reason}",
            decision,
        )
    return (final_signal, confidence, reason, decision)


def latest_d1_hex_from_duckdb(
    symbol: str,
    db_path: str | Path = "data/h1_state.duckdb",
    table: str = "h1_state_snapshot",
) -> Optional[str]:
    """Read latest D1 hex from DuckDB for a symbol."""
    try:
        import duckdb
    except ImportError:
        return None

    path = Path(db_path)
    if not path.exists():
        return None

    conn = None
    try:
        conn = duckdb.connect(str(path), read_only=True)
        rows = conn.execute(
            f"""
            SELECT d1_hex
            FROM {table}
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            [symbol],
        ).fetchone()
        return rows[0] if rows else None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()
