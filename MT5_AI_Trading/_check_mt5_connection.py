import sys
sys.path.insert(0, '.')
from python.backtest_platform.data_layer import MT5DataBridge

bridge = MT5DataBridge()
result = bridge.connect()
print("MT5连接结果:", result)

if result:
    # 尝试获取一个品种的数据
    from datetime import datetime, timedelta
    end = datetime.now()
    start = end - timedelta(days=1)
    df = bridge.fetch_ohlcv("EURUSD", "H1", start, end)
    print("EURUSD H1数据条数:", len(df))
    bridge.disconnect()
    print("已断开")
