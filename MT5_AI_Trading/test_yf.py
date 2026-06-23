import yfinance as yf
import time

stocks = ['AAPL', 'MSFT', 'TSLA', 'BABA', 'KO']
for s in stocks:
    try:
        time.sleep(2)
        t = yf.Ticker(s)
        info = t.info
        pe = info.get('trailingPE')
        cap = info.get('marketCap')
        print(f"{s}: PE={pe}, Cap={cap}")
    except Exception as e:
        print(f"{s}: ERROR {str(e)[:40]}")
