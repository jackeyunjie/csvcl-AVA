import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from backtest_platform.data_layer import MT5DataBridge

bridge = MT5DataBridge()
if bridge.connect():
    symbols = bridge._mt5.symbols_get()
    print(f"MT5总品种数: {len(symbols)}")
    
    # 查找所有股票类品种
    stocks = [s.name for s in symbols if s.name.startswith('#')]
    print(f"\n股票类品种 ({len(stocks)}):")
    for s in sorted(stocks):
        print(f"  {s}")
    
    bridge.disconnect()
