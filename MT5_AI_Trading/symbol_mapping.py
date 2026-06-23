"""
KVB/MT5 品种名称对照表
用户输入名称 -> MT5实际名称
"""

SYMBOL_MAPPING = {
    # 股指
    "HSI": "HK50",           # 恒生指数
    "SPX500": "US500",       # 标普500
    "NAS100": "USTEC",       # 纳斯达克100
    "DAX": "GER30",          # 德国DAX
    "NIKKEI": "JP225",       # 日经225
    "CHINA300": "CHINA_A50", # 中国A50
    "DOW": "US30",           # 道琼斯
    "ChinaA50": "CHINA_A50", # 中国A50
    "FTSE100": "UK100",      # 英国富时100
    
    # 外汇
    "USDJPY": "USDJPY",
    "GBPUSD": "GBPUSD",
    
    # 现货 (KVB用.v后缀，MT5不用)
    "XAUUSD.v": "GOLD",
    "XAGUSD.v": "SILVER",
    "USOIL.v": "CrudeOIL",
    
    # 个股 (去掉#前缀，用MT5实际名称)
    "#BABA": "#ALIBABA",
    "#GOOG": "#GOOGLE",
    "#AMZN": "#AMAZON",
    "#BA": "#BOEING",
    "#AMD": "#AMD",
    "#AAPL": "#APPLE",
    "#MMM": "#3M",
    "#CLX": "#CLOROX",
    "#KO": "#COCACOLA",
    "#DIS": "#DISNEY",
    "#EBAY": "#EBAY",
    "#META": "#META",
    "#GS": "#GS",
    "#FDX": "#FEDEX",
    "#INTEL": "#INTEL",
    "#JPM": "#JPMORGAN",
    "#MAR": "#MARRIOTT",
    "#MA": "#MASTERCARD",
    "#MCD": "#MCDONALDS",
    "#MRK": "#MERCK",
    "#NFLX": "#NETFLIX",
    "#NKE": "#NIKE",
    "#PEP": "#PEPSICO",
    "#QCOM": "#QUALCOMM",
    "#SBUX": "#STARBUCKS",
    "#TSLA": "#TESLA",
    "#VZ": "#VERIZON",
    "#ZM": "#ZOOM",
    "#IBM": "#IBM",
    "#MSFT": "#MICROSOFT",
    "#XOM": "#EXXON",
    "#LMT": "#LOCKHEED",
    "#AVGO": "#BROADCOM",
    "#NVDA": "#NVIDIA",
    "#CAT": "#CATERPILLAR",
    "#JNJ": "#JNJ",
    "#PFE": "#PFIZER",
    "#ADS": "#ADIDAS",
    "#AIR": "_AIRBUS",
    "#ALV": "#AUTOLIV",
    "#BAYN": "#BAYER",
    "#BMW": "_BMW.DE",
    "#VOW3": "#VOLKSWAGEN",
    "#MOH": "#MOHAWKIND",
    "#LOR": "_LOREAL.FR",
    "#MBG": "#MERCEDES",
    
    # 加密货币
    "BTCUSD": "BTCUSD",
}

# 反向映射 (MT5名称 -> 用户名称)
REVERSE_MAPPING = {v: k for k, v in SYMBOL_MAPPING.items()}

def get_mt5_symbol(user_symbol):
    """将用户品种名转换为MT5品种名"""
    return SYMBOL_MAPPING.get(user_symbol, user_symbol)

def get_user_symbol(mt5_symbol):
    """将MT5品种名转换为用户品种名"""
    return REVERSE_MAPPING.get(mt5_symbol, mt5_symbol)

# 分类
CATEGORY_MAP = {
    "HSI": "股指", "SPX500": "股指", "NAS100": "股指", "DAX": "股指",
    "NIKKEI": "股指", "CHINA300": "股指", "DOW": "股指", "ChinaA50": "股指", "FTSE100": "股指",
    "USDJPY": "外汇", "GBPUSD": "外汇",
    "XAUUSD.v": "现货", "XAGUSD.v": "现货", "USOIL.v": "现货",
    "BTCUSD": "加密货币",
}

def get_category(symbol):
    if symbol in CATEGORY_MAP:
        return CATEGORY_MAP[symbol]
    if symbol.startswith("#"):
        return "个股"
    return "其他"

if __name__ == "__main__":
    print("品种对照表测试:")
    for user, mt5 in SYMBOL_MAPPING.items():
        print(f"  {user} -> {mt5}")
