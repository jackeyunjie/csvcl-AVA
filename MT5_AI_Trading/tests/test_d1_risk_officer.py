import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ai_engine.d1_risk_officer import D1RiskOfficer, gate_signal_fields


def test_d1_long_blocks_short_and_allows_long():
    officer = D1RiskOfficer()

    assert officer.assess("6", "BUY", "H1").allowed
    decision = officer.assess("6", "SELL", "H1")

    assert not decision.allowed
    assert decision.d1_direction == "long"
    assert decision.trade_direction == "short"


def test_d1_short_blocks_long_and_allows_short():
    officer = D1RiskOfficer()

    assert officer.assess("-F", "SELL", "M15").allowed
    decision = officer.assess("-F", "BUY", "M15")

    assert not decision.allowed
    assert decision.d1_direction == "short"
    assert decision.trade_direction == "long"


def test_d1_neutral_blocks_directional_trades_but_not_hold():
    officer = D1RiskOfficer()

    assert not officer.assess("0", "BUY", "H1").allowed
    assert not officer.assess("-0", "SELL", "M15").allowed
    assert not officer.assess("N/A", "SELL", "M15").allowed
    assert officer.assess("0", "HOLD", "H1").allowed


def test_legacy_composite_state_hex_direction():
    officer = D1RiskOfficer()

    assert officer.direction_from_hex("B+H") == "long"
    assert officer.direction_from_hex("A+M") == "long"
    assert officer.direction_from_hex("D-H") == "short"
    assert officer.direction_from_hex("E-M") == "short"
    assert officer.direction_from_hex("C=M") == "neutral"


def test_gate_signal_fields_converts_blocked_trade_to_hold():
    final, confidence, reason, decision = gate_signal_fields(
        final_signal="BUY",
        confidence=0.8,
        reason="candidate",
        d1_hex="-6",
        lower_timeframe="M15",
    )

    assert final == "HOLD"
    assert confidence == 0.0
    assert "blocked_by_d1_risk_officer" in reason
    assert not decision.allowed


@dataclass
class DummySignal:
    final_signal: str = "SELL"
    d1_hex: str = "8"


def test_assess_signal_reads_d1_hex_metadata():
    decision = D1RiskOfficer().assess_signal(DummySignal(), "H1")

    assert not decision.allowed
    assert decision.d1_direction == "long"
    assert decision.trade_direction == "short"
