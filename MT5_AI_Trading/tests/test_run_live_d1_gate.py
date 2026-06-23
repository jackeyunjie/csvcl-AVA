import os
import sys
from dataclasses import dataclass
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import run_live


@dataclass
class DummyIntegratedSignal:
    symbol: str = "EURUSD"
    fundamental_signal: str = "HOLD"
    fundamental_score: int = 50
    state_trend: str = "down"
    state_hex: str = "-6"
    pivot_squeeze: int = 0
    final_signal: str = "BUY"
    confidence: float = 0.9
    reason: str = "test"
    d1_hex: str = "-6"


def test_run_live_blocks_action_against_d1_direction(monkeypatch):
    bridge = Mock()
    signal = DummyIntegratedSignal()
    run_live.positions.clear()

    monkeypatch.setattr(run_live, "add_signal", Mock())

    sent = run_live.send_signal_to_mt5(bridge, signal, live=True)

    assert sent is False
    bridge.send_command.assert_not_called()
    run_live.add_signal.assert_not_called()
