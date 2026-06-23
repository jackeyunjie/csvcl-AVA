import MetaTrader5 as mt5
mt5.initialize()
all_syms = mt5.symbols_get()
print(f"Total: {len(all_syms)}")

# show all with D1 data availability
categories = {"forex":[], "index":[], "commodity":[], "crypto":[], "stock":[]}

for s in all_syms:
    n = s.name.upper()
    # Try to get 1 bar to check availability
    try:
        r = mt5.copy_rates_from_pos(s.name, mt5.TIMEFRAME_D1, 0, 1)
        has_data = r is not None and len(r) > 0
    except:
        has_data = False
    
    label = s.name
    if has_data:
        label = f"{s.name}✓"

    if any(n.endswith(x) for x in ['USD','JPY','GBP','CHF','CAD','AUD','NZD','EUR','TRY','ZAR','NOK','SEK','SGD','MXN','PLN','HKD','CNH']):
        if len(n) == 6 and n[:3] != n[3:]:
            categories["forex"].append(label)
        elif len(n) > 5:
            categories["commodity"].append(label)  # XAUUSD etc
        else:
            categories["forex"].append(label)
    elif 'BTC' in n or 'ETH' in n or 'XRP' in n or 'LTC' in n or 'BNB' in n or 'SOL' in n or 'DOG' in n:
        categories["crypto"].append(label)
    elif any(x in n for x in ['SP500','NSDQ','DJ30','DAX','FTSE','NIKKEI','JPN225','AUS200','EU50','FRA40','GER40','UK100','HK50','NAS100','US30','NDX','SPN35','STOXX','DOLLAR']):
        categories["index"].append(label)
    elif any(x in n for x in ['XAU','XAG','OIL','WTI','BRENT','COPPER','GAS','GOLD','SILVER','COCOA','COFFEE','SUGAR','COTTON','CORN','WHEAT','SOYBEAN','COPP','NGAS']):
        categories["commodity"].append(label)
    else:
        categories["stock"].append(label)

for cat, items in categories.items():
    if items:
        print(f"\n{cat} ({len(items)}):")
        print("  " + " ".join(sorted(items)[:50]))

mt5.shutdown()
