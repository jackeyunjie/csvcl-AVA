#!/usr/bin/env python3
"""运行v4多周期共振收缩研究"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "python"))

from squeeze_multi_timeframe_research_v4 import main

if __name__ == "__main__":
    main()
