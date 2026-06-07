import requests
from textblob import TextBlob
import time
import threading
from telegram import Bot

TWELVE_KEY = "bce405b049d24b2fb7c7c709f92b0f7b"
ALPHA_KEY = "WJ7ZFIBBMPUTCIAY"
TELEGRAM_TOKEN = "8964601911:AAHGORYWnBBmtwB2OD_advSRhmlKAcYw-Q4"
CHAT_ID = "8791089686"

bot = Bot(token=TELEGRAM_TOKEN)

def send_telegram(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")
    except Exception as e:
        print(f"  Telegram Error: {e}")

def get_price(symbol):
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_KEY}"
        r = requests.get(url)
        time.sleep(1)
        return float(r.json().get("price", 0))
    except:
        return 0

def get_data(endpoint, symbol, interval, extra=""):
    try:
        url = f"https://api.twelvedata.com/{endpoint}?symbol={symbol}&interval={interval}{extra}&apikey={TWELVE_KEY}"
        r = requests.get(url)
        time.sleep(2)
        values = r.json().get("values", [])
        return values[0] if values else None
    except:
        return None

def get_candles(symbol, interval):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=20&apikey={TWELVE_KEY}"
        r = requests.get(url)
        time.sleep(2)
        return r.json().get("values", [])
    except:
        return []

def get_news(keyword):
    try:
        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={keyword}&apikey={ALPHA_KEY}"
        r = requests.get(url)
        data = r.json()
        articles = data.get("feed", [])
        if not articles:
            return [], "Neutral"
        headlines = []
        total = 0
        count = 0
        for article in articles[:3]:
            title = article.get("title", "")
            sentiment = TextBlob(title).sentiment.polarity
            total += sentiment
            count += 1
            headlines.append(title[:55])
        avg = total / count if count > 0 else 0
        if avg > 0.1:
            return headlines, "Positive ✅"
        elif avg < -0.1:
            return headlines, "Negative ❌"
        else:
            return headlines, "Neutral ➡️"
    except:
        return [], "Neutral ➡️"

def get_tf_score(symbol, interval, price):
    score = 0
    total = 0

    d = get_data("rsi", symbol, interval)
    if d:
        rsi = float(d["rsi"])
        total += 1
        if rsi < 30:
            score += 1
        elif rsi > 70:
            score -= 1

    d = get_data("macd", symbol, interval)
    if d:
        total += 1
        if float(d["macd"]) > float(d["macd_signal"]):
            score += 1
        else:
            score -= 1

    d = get_data("ema", symbol, interval, "&time_period=20")
    if d:
        total += 1
        if price > float(d["ema"]):
            score += 1
        else:
            score -= 1

    d = get_data("ema", symbol, interval, "&time_period=50")
    if d:
        total += 1
        if price > float(d["ema"]):
            score += 1
        else:
            score -= 1

    d = get_data("stoch", symbol, interval)
    if d:
        stoch_k = float(d["slow_k"])
        total += 1
        if stoch_k < 20:
            score += 1
        elif stoch_k > 80:
            score -= 1

    d = get_data("bbands", symbol, interval)
    if d:
        total += 1
        if price < float(d["lower_band"]):
            score += 1
        elif price > float(d["upper_band"]):
            score -= 1

    d = get_data("cci", symbol, interval)
    if d:
        cci = float(d["cci"])
        total += 1
        if cci < -100:
            score += 1
        elif cci > 100:
            score -= 1

    d = get_data("willr", symbol, interval)
    if d:
        willr = float(d["willr"])
        total += 1
        if willr < -80:
            score += 1
        elif willr > -20:
            score -= 1

    candles = get_candles(symbol, interval)
    if len(candles) > 5:
        highs = [float(c["high"]) for c in candles[1:]]
        lows = [float(c["low"]) for c in candles[1:]]
        total += 1
        if float(candles[0]["low"]) < min(lows) and price > min(lows):
            score += 1
        elif float(candles[0]["high"]) > max(highs) and price < max(highs):
            score -= 1

    return score, total

def analyze(symbol, name, news_keyword, timeframes):
    print(f"\n{'═'*50}")
    print(f"  🔍 {name}")
    print(f"{'═'*50}")

    price = get_price(symbol)
    if price == 0:
        print("  ⚠️ No data found")
        return

    d = get_data("atr", symbol, "1h")
    atr = float(d["atr"]) if d else 0

    headlines, news_dir = get_news(news_keyword)

    if atr > 0:
        sl  = round(price - (atr * 1.5), 2)
        tp1 = round(price + (atr * 1.5), 2)
        tp2 = round(price + (atr * 3),   2)
        tp3 = round(price + (atr * 5),   2)
    else:
        sl  = round(price * 0.98, 2)
        tp1 = round(price * 1.02, 2)
        tp2 = round(price * 1.04, 2)
        tp3 = round(price * 1.06, 2)

    print(f"\n  💰 Price  : {price:.2f}")
    print(f"  📊 ATR    : {atr:.2f}")
    print(f"  📰 News   : {news_dir}")
    print(f"\n  ⏳ Analyzing...")

    scores = []
    for tf, label in timeframes:
        s, t = get_tf_score(symbol, tf, price)
        scores.append((s, t, label))

    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │  ⏱️  Timeframe Analysis               │")
    print(f"  ├─────────────────────────────────────┤")
    for s, t, label in scores:
        c = min(round(abs(s / t * 100) + 50) if t > 0 else 50, 95)
        sig = "BUY  ✅" if s > 0 else "SELL ❌" if s < 0 else "WAIT ⚪"
        print(f"  │  {label:<8}: {sig}  ({c}%){'':>6}│")
    print(f"  └─────────────────────────────────────┘")

    total_score = 0
    total_ind = 0
    for i, (s, t, label) in enumerate(scores):
        weight = 2 if i == len(scores) - 1 else 1
        total_score += s * weight
        total_ind += t * weight

    if "Positive" in news_dir:
        total_score += 2
    elif "Negative" in news_dir:
        total_score -= 2

    if total_ind > 0:
        confidence = min(round(abs(total_score / total_ind * 100) + 50), 95)
    else:
        confidence = 50

    if total_score > 2:
        final_signal = "✅✅✅ STRONG BUY" if confidence >= 80 else "✅ BUY"
        sl  = round(price - (atr * 1.5), 2) if atr > 0 else round(price * 0.98, 2)
        tp1 = round(price + (atr * 1.5), 2) if atr > 0 else round(price * 1.02, 2)
        tp2 = round(price + (atr * 3),   2) if atr > 0 else round(price * 1.04, 2)
        tp3 = round(price + (atr * 5),   2) if atr > 0 else round(price * 1.06, 2)
    elif total_score < -2:
        final_signal = "❌❌❌ STRONG SELL" if confidence >= 80 else "❌ SELL"
        sl  = round(price + (atr * 1.5), 2) if atr > 0 else round(price * 1.02, 2)
        tp1 = round(price - (atr * 1.5), 2) if atr > 0 else round(price * 0.98, 2)
        tp2 = round(price - (atr * 3),   2) if atr > 0 else round(price * 0.96, 2)
        tp3 = round(price - (atr * 5),   2) if atr > 0 else round(price * 0.94, 2)
    else:
        final_signal = "⚪ NEUTRAL — WAIT"

    print(f"\n  ╔═════════════════════════════════════╗")
    print(f"  ║  🎯 SIGNAL     : {final_signal:<19}║")
    print(f"  ║  📊 Confidence : {confidence}%{'':>20}║")
    print(f"  ║  📰 News       : {news_dir:<19}║")
    print(f"  ╠═════════════════════════════════════╣")
    print(f"  ║  🛑 Stop Loss  : {sl:<19}║")
    print(f"  ║  🎯 TP Level 1 : {tp1:<19}║")
    print(f"  ║  🎯 TP Level 2 : {tp2:<19}║")
    print(f"  ║  🎯 TP Level 3 : {tp3:<19}║")
    print(f"  ╚═════════════════════════════════════╝")

    # Telegram Alert
    if "BUY" in final_signal or "SELL" in final_signal:
        tf_text = ""
        for s, t, label in scores:
            c = min(round(abs(s / t * 100) + 50) if t > 0 else 50, 95)
            sig = "BUY ✅" if s > 0 else "SELL ❌" if s < 0 else "WAIT ⚪"
            tf_text += f"  {label}: {sig} ({c}%)\n"

        msg = f"""
🤖 <b>TRADING SIGNAL</b>

💹 <b>{name}</b>
💰 Price: {price:.2f}

⏱️ <b>Timeframes:</b>
{tf_text}
🎯 <b>SIGNAL: {final_signal}</b>
📊 Confidence: {confidence}%
📰 News: {news_dir}

🛑 Stop Loss: {sl}
🎯 TP1: {tp1}
🎯 TP2: {tp2}
🎯 TP3: {tp3}
"""
        send_telegram(msg)
        print(f"\n  📱 Telegram Alert Sent! ✅")

    if headlines:
        print(f"\n  📰 Latest News:")
        for i, h in enumerate(headlines):
            print(f"     {i+1}. {h}")

def select_timeframes():
    print("\n  ┌─────────────────────────────┐")
    print("  │   ⏱️  Timeframe Select کریں  │")
    print("  ├─────────────────────────────┤")
    print("  │  1 = 5  Minute              │")
    print("  │  2 = 15 Minute              │")
    print("  │  3 = 30 Minute              │")
    print("  │  4 = 1  Hour                │")
    print("  │  5 = 4  Hour                │")
    print("  │  6 = 1  Day                 │")
    print("  └─────────────────────────────┘")

    tf_map = {
        "1": ("5min",  "5 Min"),
        "2": ("15min", "15 Min"),
        "3": ("30min", "30 Min"),
        "4": ("1h",    "1 Hour"),
        "5": ("4h",    "4 Hour"),
        "6": ("1day",  "1 Day"),
    }

    print("\n  3 timeframes select کریں (مثلاً: 1 2 4)")
    choices = input("  آپ کا انتخاب: ").strip().split()

    tfs = []
    for c in choices[:3]:
        if c in tf_map:
            tfs.append(tf_map[c])

    if not tfs:
        tfs = [("5min", "5 Min"), ("15min", "15 Min"), ("1h", "1 Hour")]

    while len(tfs) < 3:
        tfs.append(("1h", "1 Hour"))

    return tfs

def select_pairs():
    print("\n  ┌─────────────────────────────┐")
    print("  │   💹 Pair Select کریں       │")
    print("  ├─────────────────────────────┤")
    print("  │  1 = Gold                   │")
    print("  │  2 = Bitcoin                │")
    print("  │  3 = Silver                 │")
    print("  │  4 = Crude Oil              │")
    print("  │  5 = سب کے سب              │")
    print("  └─────────────────────────────┘")

    pair_map = {
        "1": ("XAU/USD", "GOLD",      "XAUUSD"),
        "2": ("BTC/USD", "BITCOIN",   "CRYPTO:BTC"),
        "3": ("SLV",     "SILVER",    "XAGUSD"),
        "4": ("USO",     "CRUDE OIL", "WTI"),
    }

    print("\n  Pairs select کریں (مثلاً: 1 2 یا 5 سب کے لیے)")
    choices = input("  آپ کا انتخاب: ").strip().split()

    if "5" in choices:
        return list(pair_map.values())

    pairs = []
    for c in choices:
        if c in pair_map:
            pairs.append(pair_map[c])

    if not pairs:
        pairs = [pair_map["1"]]

    return pairs

# ─── Main ───────────────────────────────────────
print("╔══════════════════════════════════════════╗")
print("║   🤖 ADVANCED TRADING BOT                ║")
print("║   TradingView + Telegram Alerts          ║")
print("╚══════════════════════════════════════════╝")

send_telegram("🤖 Trading Bot Started! ✅")

pairs = select_pairs()
timeframes = select_timeframes()

for symbol, name, news_keyword in pairs:
    analyze(symbol, name, news_keyword, timeframes)

print("\n✅ Analysis Complete!")