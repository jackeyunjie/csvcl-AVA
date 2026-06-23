import sys
print("Python:", sys.executable)
try:
    import MetaTrader5
    print("MetaTrader5: installed")
except ImportError:
    print("MetaTrader5: NOT installed")
