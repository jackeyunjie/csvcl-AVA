"""
Regression test for multi-timeframe squeeze -> resonant breakout detection.

This test uses synthetic OHLCV data only. It verifies that a plain squeeze setup
does not become a trade, while multi-timeframe same-direction breakout after a
recent squeeze is promoted to the best opportunity stage.
"""
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "python"))

from analytics.multi_timeframe_squeeze import MultiTimeframeSqueezeSystem


def make_squeeze_breakout_df(n=90, direction="up", freq="h"):
    rng = np.random.default_rng(42)
    timestamps = pd.date_range(end=datetime(2026, 6, 5, 10), periods=n, freq=freq)

    close = np.full(n, 100.0)
    for i in range(1, n):
        if i < 45:
            close[i] = close[i - 1] + rng.normal(0, 0.45)
        elif i < 84:
            close[i] = 100 + rng.normal(0, 0.08)
        else:
            step = 0.65 if direction == "up" else -0.65
            close[i] = close[i - 1] + step + rng.normal(0, 0.05)

    high = close + np.r_[np.full(45, 0.75), np.full(39, 0.16), np.full(n - 84, 0.25)]
    low = close - np.r_[np.full(45, 0.75), np.full(39, 0.16), np.full(n - 84, 0.25)]
    open_price = close + rng.normal(0, 0.05, n)

    if direction == "up":
        close[-1] = max(high[64:84]) + 0.9
        high[-1] = close[-1] + 0.25
        low[-1] = close[-1] - 0.25
    else:
        close[-1] = min(low[64:84]) - 0.9
        high[-1] = close[-1] + 0.25
        low[-1] = close[-1] - 0.25

    return pd.DataFrame({
        "timestamp": timestamps,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.integers(1000, 5000, n),
    })


def make_squeeze_only_df(n=90, freq="D"):
    rng = np.random.default_rng(7)
    timestamps = pd.date_range(end=datetime(2026, 6, 5, 10), periods=n, freq=freq)
    close = 100 + rng.normal(0, 0.06, n)
    high = close + 0.14
    low = close - 0.14
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": close + rng.normal(0, 0.02, n),
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.integers(1000, 5000, n),
    })


def main():
    system = MultiTimeframeSqueezeSystem()

    breakout_signal = system.analyze("TEST_UP", {
        "H1": make_squeeze_breakout_df(freq="h", direction="up"),
        "H4": make_squeeze_breakout_df(freq="4h", direction="up"),
        "D1": make_squeeze_only_df(freq="D"),
    })

    assert breakout_signal.opportunity_stage == "resonant_breakout", breakout_signal.debate_summary
    assert breakout_signal.consensus_direction == "long", breakout_signal.debate_summary
    assert breakout_signal.breakout_resonance_score >= 2, breakout_signal.debate_summary
    assert breakout_signal.setup_resonance_score >= 2, breakout_signal.debate_summary

    setup_signal = system.analyze("TEST_SETUP", {
        "H1": make_squeeze_only_df(freq="h"),
        "H4": make_squeeze_only_df(freq="4h"),
        "D1": make_squeeze_only_df(freq="D"),
    })

    assert setup_signal.consensus_direction == "hold", setup_signal.debate_summary
    assert setup_signal.opportunity_stage in {"squeeze_setup", "none"}, setup_signal.debate_summary

    print("multi-timeframe resonant breakout regression passed")
    print(f"breakout stage={breakout_signal.opportunity_stage}, direction={breakout_signal.consensus_direction}, confidence={breakout_signal.consensus_confidence:.2f}")
    print(f"setup stage={setup_signal.opportunity_stage}, direction={setup_signal.consensus_direction}")


if __name__ == "__main__":
    main()
