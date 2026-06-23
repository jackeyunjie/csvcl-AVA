"""
双MT5平台品种名称对照表
KVB Prime MT5 + Ava Trade MT5
"""

# =====================================================================
# KVB Prime MT5 品种名称
# =====================================================================
KVB_SYMBOLS = {
    # 股指
    "HSI": "HK50",
    "SPX500": "US500", 
    "NAS100": "USTEC",
    "DAX": "GER30",
    "NIKKEI": "JP225",
    "CHINA300": "CHINA_A50",
    "DOW": "US30",
    "ChinaA50": "CHINA_A50",
    "FTSE100": "UK100",
    
    # 外汇
    "USDJPY": "USDJPY",
    "GBPUSD": "GBPUSD",
    
    # 现货
    "XAUUSD.v": "GOLD",
    "XAGUSD.v": "SILVER", 
    "USOIL.v": "CrudeOIL",
    
    # 个股 (KVB用 #前缀)
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

# =====================================================================
# Ava Trade MT5 品种名称 (通常不同)
# =====================================================================
AVATRADE_SYMBOLS = {
    # 股指 (AvaTrade可能用不同命名)
    "HSI": "HK50",
    "SPX500": "SPX500",
    "NAS100": "NAS100", 
    "DAX": "GER30",
    "NIKKEI": "JPN225",
    "CHINA300": "CHINA50",
    "DOW": "US30",
    "ChinaA50": "CHINA50",
    "FTSE100": "UK100",
    
    # 外汇
    "USDJPY": "USDJPY",
    "GBPUSD": "GBPUSD",
    
    # 现货 (AvaTrade可能有不同后缀)
    "XAUUSD.v": "XAUUSD",
    "XAGUSD.v": "XAGUSD",
    "USOIL.v": "OIL",
    
    # 个股 (AvaTrade可能不用#前缀或不同格式)
    "#BABA": "BABA",
    "#GOOG": "GOOG",
    "#AMZN": "AMZN",
    "#BA": "BA",
    "#AMD": "AMD",
    "#AAPL": "AAPL",
    "#MMM": "MMM",
    "#CLX": "CLX",
    "#KO": "KO",
    "#DIS": "DIS",
    "#EBAY": "EBAY",
    "#META": "META",
    "#GS": "GS",
    "#FDX": "FDX",
    "#INTEL": "INTC",
    "#JPM": "JPM",
    "#MAR": "MAR",
    "#MA": "MA",
    "#MCD": "MCD",
    "#MRK": "MRK",
    "#NFLX": "NFLX",
    "#NKE": "NKE",
    "#PEP": "PEP",
    "#QCOM": "QCOM",
    "#SBUX": "SBUX",
    "#TSLA": "TSLA",
    "#VZ": "VZ",
    "#ZM": "ZM",
    "#IBM": "IBM",
    "#MSFT": "MSFT",
    "#XOM": "XOM",
    "#LMT": "LMT",
    "#AVGO": "AVGO",
    "#NVDA": "NVDA",
    "#CAT": "CAT",
    "#JNJ": "JNJ",
    "#PFE": "PFE",
    "#ADS": "ADS",
    "#AIR": "AIR",
    "#ALV": "ALV",
    "#BAYN": "BAYN",
    "#BMW": "BMW",
    "#VOW3": "VOW3",
    "#MOH": "MOH",
    "#LOR": "LOR",
    "#MBG": "MBG",
    
    # 加密货币
    "BTCUSD": "BTCUSD",
}

# =====================================================================
# 分类映射
# =====================================================================
CATEGORY_MAP = {
    "HSI": "股指", "SPX500": "股指", "NAS100": "股指", "DAX": "股指",
    "NIKKEI": "股指", "CHINA300": "股指", "DOW": "股指", "ChinaA50": "股指", "FTSE100": "股指",
    "USDJPY": "外汇", "GBPUSD": "外汇",
    "XAUUSD.v": "现货", "XAGUSD.v": "现货", "USOIL.v": "现货",
    "BTCUSD": "加密货币",
}

def get_category(symbol):
    """获取品种分类"""
    if symbol in CATEGORY_MAP:
        return CATEGORY_MAP[symbol]
    if symbol.startswith("#"):
        return "个股"
    return "其他"

def get_mt5_symbol(user_symbol, platform="KVB"):
    """
    将用户品种名转换为指定MT5平台的品种名
    platform: "KVB" 或 "AVATRADE"
    """
    if platform.upper() == "KVB":
        return KVB_SYMBOLS.get(user_symbol, user_symbol)
    elif platform.upper() == "AVATRADE":
        return AVATRADE_SYMBOLS.get(user_symbol, user_symbol)
    else:
        return user_symbol

def get_all_symbols(platform="KVB"):
    """获取指定平台的所有品种列表"""
    if platform.upper() == "KVB":
        return list(KVB_SYMBOLS.values())
    elif platform.upper() == "AVATRADE":
        return list(AVATRADE_SYMBOLS.values())
    else:
        return []

# 用户统一品种名列表
USER_SYMBOLS = [
    # 股指
    "HSI", "SPX500", "NAS100", "DAX", "NIKKEI", "CHINA300",
    "DOW", "ChinaA50", "FTSE100",
    # 外汇
    "USDJPY", "GBPUSD",
    # 现货
    "XAUUSD.v", "XAGUSD.v", "USOIL.v",
    # 个股
    "#BABA", "#GOOG", "#AMZN", "#BA", "#AMD", "#AAPL", "#MMM",
    "#KO", "#DIS", "#META", "#GS", "#INTEL", "#JPM", "#MA",
    "#MCD", "#NFLX", "#NKE", "#TSLA", "#IBM", "#MSFT", "#XOM",
    "#NVDA", "#CAT", "#JNJ", "#PFE",
    # 加密货币
    "BTCUSD"
]

if __name__ == "__main__":
    print("双平台品种对照表")
    print("="*60)
    print(f"{'用户名称':<15} {'KVB':<20} {'AvaTrade':<20}")
    print("-"*60)
    for user in USER_SYMBOLS:
        kvb = get_mt5_symbol(user, "KVB")
        ava = get_mt5_symbol(user, "AVATRADE")
        print(f"{user:<15} {kvb:<20} {ava:<20}")
