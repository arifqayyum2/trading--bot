import MetaTrader5 as mt5

if not mt5.initialize():
    print("initialize() FAILED, error code =", mt5.last_error())
    quit()

print("MT5 connected successfully!")
print(mt5.terminal_info())
print(mt5.account_info())

symbol = "XAUUSD"
tick = mt5.symbol_info_tick(symbol)
if tick is None:
    print(f"{symbol} symbol nahi mila — Market Watch mein add karo MT5 app mein")
else:
    print(f"{symbol} Bid: {tick.bid}, Ask: {tick.ask}")

mt5.shutdown()