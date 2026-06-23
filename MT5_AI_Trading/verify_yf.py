import yfinance as yf
import time
import sys

# 重定向输出到文件
with open("logs/yf_test_result.log", "w", encoding="utf-8") as f:
    f.write("=== yfinance 测试开始 ===\n")
    
    stocks = ['AAPL', 'MSFT', 'TSLA', 'BABA', 'KO']
    for s in stocks:
        try:
            time.sleep(2)
            t = yf.Ticker(s)
            info = t.info
            pe = info.get('trailingPE')
            cap = info.get('marketCap')
            result = f"{s}: PE={pe}, Cap={cap}\n"
            f.write(result)
            print(result, end="")
        except Exception as e:
            result = f"{s}: ERROR {str(e)[:80]}\n"
            f.write(result)
            print(result, end="")
    
    f.write("=== yfinance 测试完成 ===\n")

print("结果已保存到 logs/yf_test_result.log")
