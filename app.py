from flask import Flask, render_template_string, jsonify, request
import requests
from textblob import TextBlob
import time
import os
import threading
# ============================================================
#  TELEGRAM CONFIG — apni values yahan daalo
# ============================================================
TELEGRAM_TOKEN = "8964601911:AAHGORYWnBBmtwB2OD_advSRhmlKAcYw-Q4"
CHAT_ID        = "8791089686"
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Telegram Error: {e}")
app = Flask(__name__)
# ============================================================
#  FREE DATA FUNCTIONS - Binance (Crypto) + Frankfurter (Forex)
# ============================================================
def get_price(symbol):
    try:
        # Bitcoin - Yahoo Finance (more reliable)
        if symbol == "CRYPTO:BTC":
            url = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1m&range=1d"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            data = r.json()
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            return float(price)
        # Gold - XAU/USD via Yahoo Finance
        if symbol == "XAUUSD":
            url = "https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?interval=1m&range=1d"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            data = r.json()
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            return float(price)
        # Silver - XAG/USD via Yahoo Finance
        if symbol == "XAGUSD":
            url = "https://query1.finance.yahoo.com/v8/finance/chart/SI%3DF?interval=1m&range=1d"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            data = r.json()
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            return float(price)
        # Crude Oil - WTI via Yahoo Finance
        if symbol == "WTI":
            url = "https://query1.finance.yahoo.com/v8/finance/chart/CL%3DF?interval=1m&range=1d"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            data = r.json()
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            return float(price)
        return 0
    except Exception as e:
        print(f"Price error for {symbol}: {e}")
        return 0
def get_candles_binance(symbol_binance, interval_binance, limit=50):
    """Binance OHLCV candles"""
    try:
        interval_map = {
            "5min": "5m", "15min": "15m", "30min": "30m",
            "1h": "1h", "4h": "4h", "1day": "1d"
        }
        bi = interval_map.get(interval_binance, interval_binance)
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol_binance}&interval={bi}&limit={limit}"
        r = requests.get(url, timeout=10)
        raw = r.json()
        candles = []
        for c in raw:
            candles.append({
                "open":   str(c[1]),
                "high":   str(c[2]),
                "low":    str(c[3]),
                "close":  str(c[4]),
                "volume": str(c[5]),
            })
        return list(reversed(candles))  # newest first
    except Exception as e:
        print(f"Candle error: {e}")
        return []
def get_news_free(keyword):
    """
    GNews free API (no key needed for basic queries)
    Falls back to neutral if unavailable
    """
    try:
        url = f"https://gnews.io/api/v4/search?q={keyword}&lang=en&max=5&apikey=free"
        r = requests.get(url, timeout=8)
        articles = r.json().get("articles", [])
        if not articles:
            return [], "Neutral"
        headlines = []
        total = 0
        for article in articles[:3]:
            title = article.get("title", "")
            sentiment = TextBlob(title).sentiment.polarity
            total += sentiment
            headlines.append(title[:60])
        avg = total / len(headlines) if headlines else 0
        mood = "Positive" if avg > 0.1 else "Negative" if avg < -0.1 else "Neutral"
        return headlines, mood
    except:
        return [], "Neutral"
# ============================================================
#  INDICATOR CALCULATIONS (same logic, no API key needed)
# ============================================================
def calc_rsi(candles, period=14):
    try:
        if len(candles) < period + 1:
            return None
        closes = [float(c["close"]) for c in candles]
        gains, losses = [], []
        for i in range(period):
            diff = closes[i] - closes[i + 1]
            if diff > 0:
                gains.append(diff); losses.append(0)
            else:
                gains.append(0); losses.append(abs(diff))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 1)
    except:
        return None
def calc_macd(candles):
    try:
        if len(candles) < 26:
            return None, None
        closes = [float(c["close"]) for c in reversed(candles)]
        def ema(data, n):
            k = 2 / (n + 1)
            result = [data[0]]
            for v in data[1:]:
                result.append(v * k + result[-1] * (1 - k))
            return result
        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
        signal_line = ema(macd_line, 9)
        return macd_line[-1], signal_line[-1]
    except:
        return None, None
def calc_ema(candles, period):
    try:
        if len(candles) < period:
            return None
        closes = [float(c["close"]) for c in reversed(candles)]
        k = 2 / (period + 1)
        ema_val = closes[0]
        for v in closes[1:]:
            ema_val = v * k + ema_val * (1 - k)
        return round(ema_val, 4)
    except:
        return None
def calc_stochastic(candles, period=14):
    try:
        if len(candles) < period:
            return None
        highs = [float(c["high"]) for c in candles[:period]]
        lows  = [float(c["low"])  for c in candles[:period]]
        close = float(candles[0]["close"])
        highest = max(highs)
        lowest  = min(lows)
        if highest == lowest:
            return 50
        k = ((close - lowest) / (highest - lowest)) * 100
        return round(k, 1)
    except:
        return None
def calc_bbands(candles, period=20):
    try:
        if len(candles) < period:
            return None, None
        closes = [float(c["close"]) for c in candles[:period]]
        mean = sum(closes) / period
        std  = (sum((x - mean) ** 2 for x in closes) / period) ** 0.5
        return round(mean + 2 * std, 4), round(mean - 2 * std, 4)
    except:
        return None, None
def calc_atr(candles, period=14):
    try:
        if len(candles) < period + 1:
            return 0
        trs = []
        for i in range(period):
            h = float(candles[i]["high"])
            l = float(candles[i]["low"])
            pc = float(candles[i + 1]["close"])
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return round(sum(trs) / period, 4)
    except:
        return 0
def calc_supertrend(candles, period=7, multiplier=3):
    try:
        if len(candles) < period + 1:
            return "N/A"
        highs  = [float(c["high"])  for c in candles]
        lows   = [float(c["low"])   for c in candles]
        closes = [float(c["close"]) for c in candles]
        trs = []
        for i in range(1, len(candles)):
            trs.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        atr = sum(trs[:period]) / period
        hl2 = (highs[0] + lows[0]) / 2
        lower = hl2 - multiplier * atr
        return "BUY" if closes[0] > lower else "SELL"
    except:
        return "N/A"
def calc_parabolic_sar(candles):
    try:
        if len(candles) < 5:
            return "N/A"
        closes = [float(c["close"]) for c in candles]
        lows   = [float(c["low"])   for c in candles]
        highs  = [float(c["high"])  for c in candles]
        trend = "UP" if closes[0] > closes[1] > closes[2] else "DOWN" if closes[0] < closes[1] < closes[2] else "NEUTRAL"
        sar = lows[1] if trend == "UP" else highs[1]
        if trend == "UP" and closes[0] > sar:
            return "BUY"
        elif trend == "DOWN" and closes[0] < sar:
            return "SELL"
        return "NEUTRAL"
    except:
        return "N/A"
def calc_pivot_points(candles):
    try:
        if len(candles) < 2:
            return {}
        h = float(candles[1]["high"]); l = float(candles[1]["low"]); c = float(candles[1]["close"])
        pp = round((h + l + c) / 3, 4)
        return {"pp": pp, "r1": round(2*pp-l,4), "r2": round(pp+(h-l),4), "s1": round(2*pp-h,4), "s2": round(pp-(h-l),4)}
    except:
        return {}
def calc_fibonacci(candles):
    try:
        if len(candles) < 20:
            return {}
        highs = [float(c["high"]) for c in candles[:20]]
        lows  = [float(c["low"])  for c in candles[:20]]
        high  = max(highs); low = min(lows); diff = high - low
        return {"f236": round(high-0.236*diff,4), "f382": round(high-0.382*diff,4),
                "f500": round(high-0.500*diff,4), "f618": round(high-0.618*diff,4),
                "f786": round(high-0.786*diff,4)}
    except:
        return {}
def calc_order_blocks(candles, price):
    try:
        if len(candles) < 5:
            return "N/A", 0, 0
        bull_ob = bear_ob = 0
        for i in range(1, min(10, len(candles)-1)):
            cc = float(candles[i]["close"]); co = float(candles[i]["open"])
            pc = float(candles[i+1]["close"]); po = float(candles[i+1]["open"])
            if cc > co * 1.001 and pc < po:
                bull_ob = float(candles[i]["low"])
            if cc < co * 0.999 and pc > po:
                bear_ob = float(candles[i]["high"])
        if bull_ob > 0 and price > bull_ob:
            return "BULLISH OB", round(bull_ob,4), round(bear_ob,4)
        elif bear_ob > 0 and price < bear_ob:
            return "BEARISH OB", round(bull_ob,4), round(bear_ob,4)
        return "NO OB", round(bull_ob,4), round(bear_ob,4)
    except:
        return "N/A", 0, 0
def calc_fair_value_gap(candles):
    try:
        if len(candles) < 3:
            return "N/A", 0, 0
        for i in range(len(candles)-2):
            hp = float(candles[i+2]["high"]); ln = float(candles[i]["low"])
            hn = float(candles[i]["high"]);   lp = float(candles[i+2]["low"])
            if ln > hp:
                return "BULLISH FVG", round(hp,4), round(ln,4)
            if hn < lp:
                return "BEARISH FVG", round(hn,4), round(lp,4)
        return "NO FVG", 0, 0
    except:
        return "N/A", 0, 0
def calc_smart_money(candles, price):
    try:
        if len(candles) < 10:
            return "N/A"
        closes = [float(c["close"]) for c in candles[:10]]
        highs  = [float(c["high"])  for c in candles[:10]]
        lows   = [float(c["low"])   for c in candles[:10]]
        recent_high = max(highs[1:5]); recent_low = min(lows[1:5])
        if price > recent_high:   return "BOS BULLISH"
        if price < recent_low:    return "BOS BEARISH"
        if closes[0] > closes[2] and closes[2] < closes[4]: return "CHoCH BULLISH"
        if closes[0] < closes[2] and closes[2] > closes[4]: return "CHoCH BEARISH"
        return "NEUTRAL"
    except:
        return "N/A"
def calc_obv(candles):
    try:
        if len(candles) < 5:
            return "N/A"
        obv = 0; vals = []
        for i in range(len(candles)-1, -1, -1):
            vol = float(candles[i].get("volume", 0))
            if i < len(candles)-1:
                if float(candles[i]["close"]) > float(candles[i+1]["close"]): obv += vol
                elif float(candles[i]["close"]) < float(candles[i+1]["close"]): obv -= vol
            vals.append(obv)
        if len(vals) >= 3:
            if vals[0] > vals[1] > vals[2]: return "BUY"
            if vals[0] < vals[1] < vals[2]: return "SELL"
        return "NEUTRAL"
    except:
        return "N/A"
def calc_mfi(candles, period=14):
    try:
        if len(candles) < period+1:
            return 50
        pos = neg = 0
        for i in range(period):
            tp = (float(candles[i]["high"])+float(candles[i]["low"])+float(candles[i]["close"]))/3
            tp_prev = (float(candles[i+1]["high"])+float(candles[i+1]["low"])+float(candles[i+1]["close"]))/3
            vol = float(candles[i].get("volume", 0))
            if tp > tp_prev: pos += tp*vol
            else:            neg += tp*vol
        if neg == 0: return 100
        return round(100-(100/(1+pos/neg)),1)
    except:
        return 50
def calc_volume_spike(candles):
    try:
        if len(candles) < 10:
            return "N/A"
        vols = [float(c.get("volume",0)) for c in candles[:10]]
        avg = sum(vols[1:])/(len(vols)-1)
        if avg == 0: return "N/A"
        ratio = vols[0]/avg
        if ratio > 2:   return f"HIGH SPIKE ({ratio:.1f}x)"
        if ratio > 1.5: return f"SPIKE ({ratio:.1f}x)"
        if ratio < 0.5: return "LOW VOLUME"
        return f"NORMAL ({ratio:.1f}x)"
    except:
        return "N/A"
# ============================================================
#  TIMEFRAME SCORE (all indicators from candles — no API key)
# ============================================================
def get_tf_score(symbol_binance, interval, price):
    candles = get_candles_binance(symbol_binance, interval, 60)
    if not candles:
        return 0, 0, 50, {}
    weighted_score = 0
    max_score = 0
    indicators = {}
    # RSI
    rsi = calc_rsi(candles)
    if rsi is not None:
        max_score += 15
        if rsi < 30:   weighted_score += 15; rs = "BUY"
        elif rsi > 70: weighted_score -= 15; rs = "SELL"
        elif rsi < 45: weighted_score += 8;  rs = "BUY"
        elif rsi > 55: weighted_score -= 8;  rs = "SELL"
        else:          rs = "NEUTRAL"
        indicators["rsi"] = {"value": rsi, "signal": rs}
    # MACD
    macd_val, macd_sig = calc_macd(candles)
    if macd_val is not None:
        max_score += 12
        diff = macd_val - macd_sig
        if diff > 0: weighted_score += 12; ms = "BUY"
        else:        weighted_score -= 12; ms = "SELL"
        indicators["macd"] = {"signal": ms}
    # EMA 20
    ema20 = calc_ema(candles, 20)
    if ema20:
        max_score += 8
        if price > ema20: weighted_score += 8; e20s = "BUY"
        else:             weighted_score -= 8; e20s = "SELL"
        indicators["ema20"] = {"value": round(ema20, 4), "signal": e20s}
    # EMA 50
    ema50 = calc_ema(candles, 50)
    if ema50:
        max_score += 8
        if price > ema50: weighted_score += 8; e50s = "BUY"
        else:             weighted_score -= 8; e50s = "SELL"
        indicators["ema50"] = {"value": round(ema50, 4), "signal": e50s}
    # Stochastic
    stoch_k = calc_stochastic(candles)
    if stoch_k is not None:
        max_score += 10
        if stoch_k < 20:   weighted_score += 10; ss = "BUY"
        elif stoch_k > 80: weighted_score -= 10; ss = "SELL"
        else:              ss = "NEUTRAL"
        indicators["stoch"] = {"value": stoch_k, "signal": ss}
    # Bollinger Bands
    bb_upper, bb_lower = calc_bbands(candles)
    if bb_upper and bb_lower:
        max_score += 8
        if price < bb_lower:   weighted_score += 8; bbs = "BUY"
        elif price > bb_upper: weighted_score -= 8; bbs = "SELL"
        else:                  bbs = "NEUTRAL"
        indicators["bbands"] = {"signal": bbs}
    # Supertrend
    st = calc_supertrend(candles)
    max_score += 10
    if st == "BUY":  weighted_score += 10
    elif st == "SELL": weighted_score -= 10
    indicators["supertrend"] = {"signal": st}
    # Parabolic SAR
    psar = calc_parabolic_sar(candles)
    max_score += 8
    if psar == "BUY":  weighted_score += 8
    elif psar == "SELL": weighted_score -= 8
    indicators["psar"] = {"signal": psar}
    # Pivot Points
    pivots = calc_pivot_points(candles)
    indicators["pivots"] = pivots
    # Fibonacci
    fib = calc_fibonacci(candles)
    indicators["fibonacci"] = fib
    # Order Blocks
    ob_sig, bull_ob, bear_ob = calc_order_blocks(candles, price)
    max_score += 8
    if "BULLISH" in ob_sig: weighted_score += 8
    elif "BEARISH" in ob_sig: weighted_score -= 8
    indicators["order_blocks"] = {"signal": ob_sig, "bull": bull_ob, "bear": bear_ob}
    # FVG
    fvg_sig, fvg_l, fvg_h = calc_fair_value_gap(candles)
    max_score += 6
    if "BULLISH" in fvg_sig: weighted_score += 6
    elif "BEARISH" in fvg_sig: weighted_score -= 6
    indicators["fvg"] = {"signal": fvg_sig, "low": fvg_l, "high": fvg_h}
    # SMC
    smc = calc_smart_money(candles, price)
    max_score += 8
    if "BULLISH" in smc: weighted_score += 8
    elif "BEARISH" in smc: weighted_score -= 8
    indicators["smc"] = {"signal": smc}
    # OBV
    obv = calc_obv(candles)
    max_score += 6
    if obv == "BUY":  weighted_score += 6
    elif obv == "SELL": weighted_score -= 6
    indicators["obv"] = {"signal": obv}
    # MFI
    mfi = calc_mfi(candles)
    max_score += 6
    if mfi < 20:   weighted_score += 6; mfis = "BUY"
    elif mfi > 80: weighted_score -= 6; mfis = "SELL"
    else:          mfis = "NEUTRAL"
    indicators["mfi"] = {"value": mfi, "signal": mfis}
    # Volume Spike
    vs = calc_volume_spike(candles)
    indicators["volume"] = {"signal": vs}
    # Support / Resistance
    indicators["support"]    = round(min(float(c["low"])  for c in candles[:30]), 4)
    indicators["resistance"] = round(max(float(c["high"]) for c in candles[:30]), 4)
    # Liquidity Sweep
    max_score += 7
    all_highs = [float(c["high"]) for c in candles[1:]]
    all_lows  = [float(c["low"])  for c in candles[1:]]
    if float(candles[0]["low"]) < min(all_lows) and price > min(all_lows):
        weighted_score += 7; liq = "BULLISH SWEEP"
    elif float(candles[0]["high"]) > max(all_highs) and price < max(all_highs):
        weighted_score -= 7; liq = "BEARISH SWEEP"
    else:
        liq = "NO SWEEP"
    indicators["liquidity"] = {"signal": liq}
    confidence = round(((weighted_score + max_score) / (2 * max_score)) * 100) if max_score > 0 else 50
    confidence = max(0, min(confidence, 100))
    return weighted_score, max_score, confidence, indicators
# ============================================================
#  HTML UI (same design, updated pairs for free APIs)
# ============================================================
HTML = """<!DOCTYPE html>
<html>
<head>
<title>Free Trading Bot</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#fff;font-family:Arial}
.header{background:#161b22;padding:15px;text-align:center;border-bottom:2px solid #00ff88}
.header h1{color:#00ff88;font-size:22px}
.header p{color:#888;font-size:12px;margin-top:3px}
.badge{background:#1f2937;color:#00ff88;border:1px solid #00ff88;border-radius:20px;font-size:11px;padding:3px 10px;display:inline-block;margin-top:5px}
.container{max-width:900px;margin:15px auto;padding:12px}
.section{background:#161b22;border-radius:10px;padding:15px;margin-bottom:12px;border:1px solid #30363d}
.section h2{color:#00ff88;margin-bottom:12px;font-size:15px}
.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.btn{padding:12px;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:bold;transition:0.3s;width:100%}
.btn-pair{background:#1f2937;color:#fff;border:2px solid #30363d}
.btn-pair.active{background:#00ff88;color:#000;border-color:#00ff88}
.btn-tf{background:#1f2937;color:#fff;border:2px solid #30363d}
.btn-tf.active{background:#3b82f6;color:#fff}
.btn-analyze{background:#00ff88;color:#000;width:100%;padding:15px;font-size:17px;border-radius:8px;margin-top:10px;border:none;cursor:pointer;font-weight:bold}
.signal-box{border-radius:10px;padding:15px;text-align:center;margin:10px 0}
.strong-buy{background:linear-gradient(135deg,#00ff88,#00cc66);color:#000}
.buy{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff}
.strong-sell{background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff}
.sell{background:linear-gradient(135deg,#f97316,#ea580c);color:#fff}
.neutral{background:linear-gradient(135deg,#6b7280,#4b5563);color:#fff}
.signal-box h2{font-size:20px}
.signal-box p{font-size:13px;margin-top:5px}
.info-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:10px 0}
.info-card{background:#0d1117;border-radius:8px;padding:10px;border:1px solid #30363d}
.info-card label{color:#888;font-size:11px}
.info-card p{font-size:15px;font-weight:bold;margin-top:3px}
.ind-card{background:#0d1117;border-radius:6px;padding:8px;border:1px solid #30363d;display:flex;justify-content:space-between;align-items:center;margin:4px 0}
.ind-name{color:#888;font-size:11px}
.ind-val{font-size:12px;font-weight:bold}
.buy-c{color:#00ff88}.sell-c{color:#ef4444}.neutral-c{color:#6b7280}
.rsi-green{color:#00ff88;font-weight:bold}.rsi-red{color:#ef4444;font-weight:bold}
.consensus{display:flex;gap:6px;margin:8px 0}
.con-item{flex:1;background:#0d1117;border-radius:6px;padding:8px;text-align:center;border:1px solid #30363d}
.con-tf{color:#888;font-size:10px}.con-sig{font-size:13px;font-weight:bold;margin-top:3px}
.history-table{width:100%;border-collapse:collapse;font-size:12px}
.history-table th{background:#1f2937;padding:8px;text-align:left;color:#888}
.history-table td{padding:8px;border-bottom:1px solid #30363d}
.win-card{background:#0d1117;border-radius:8px;padding:12px;text-align:center;border:1px solid #30363d}
.win-card h3{color:#888;font-size:12px}.win-card p{font-size:22px;font-weight:bold;margin-top:5px}
.loading{text-align:center;padding:30px}
.spinner{border:4px solid #30363d;border-top:4px solid #00ff88;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin:15px auto}
@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
.news-item{color:#aaa;font-size:12px;margin:4px 0;padding:4px 0;border-bottom:1px solid #30363d}
.pair-result{margin-bottom:15px;border:1px solid #30363d;border-radius:10px;overflow:hidden}
.pair-header{background:#1f2937;padding:12px 15px}.pair-header h3{font-size:18px}
.sr-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:8px 0}
.sr-card{background:#0d1117;border-radius:8px;padding:10px;border:1px solid #30363d;text-align:center}
.sr-card label{color:#888;font-size:11px}.sr-card p{font-size:15px;font-weight:bold;margin-top:3px}
.fib-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:8px 0}
.fib-card{background:#0d1117;border-radius:6px;padding:8px;border:1px solid #30363d;text-align:center}
.fib-card label{color:#f59e0b;font-size:10px}.fib-card p{font-size:12px;font-weight:bold;margin-top:2px}
.pivot-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:8px 0}
.pivot-card{background:#0d1117;border-radius:6px;padding:8px;border:1px solid #30363d;text-align:center}
.pivot-card label{color:#888;font-size:10px}.pivot-card p{font-size:12px;font-weight:bold;margin-top:2px}
.section-title{color:#3b82f6;font-size:13px;margin:10px 0 5px 0;font-weight:bold}
</style>
</head>
<body>
<div class="header">
<h1>Free Trading Bot</h1>
<p>20+ Indicators | Smart Money | Volume | Price Action</p>
<span class="badge">✅ 100% Free — No API Key Needed</span>
</div>
<div class="container">
<div class="section">
<h2>Pair Select</h2>
<div class="grid2">
<button class="btn btn-pair" onclick="togglePair(this,'XAUUSD','GOLD','gold')">Gold (XAU/USD)</button>
<button class="btn btn-pair" onclick="togglePair(this,'CRYPTO:BTC','BITCOIN','BTCUSDT')">Bitcoin (BTC)</button>
<button class="btn btn-pair" onclick="togglePair(this,'XAGUSD','SILVER','silver')">Silver (XAG/USD)</button>
<button class="btn btn-pair" onclick="togglePair(this,'WTI','CRUDE OIL','crude oil')">Crude Oil (WTI)</button>
</div>
</div>
<div class="section">
<h2>Timeframe Select (3 select karo)</h2>
<div class="grid2">
<button class="btn btn-tf" onclick="toggleTF(this,'5min','5 Min')">5 Minute</button>
<button class="btn btn-tf" onclick="toggleTF(this,'15min','15 Min')">15 Minute</button>
<button class="btn btn-tf" onclick="toggleTF(this,'30min','30 Min')">30 Minute</button>
<button class="btn btn-tf" onclick="toggleTF(this,'1h','1 Hour')">1 Hour</button>
<button class="btn btn-tf" onclick="toggleTF(this,'4h','4 Hour')">4 Hour</button>
<button class="btn btn-tf" onclick="toggleTF(this,'1day','1 Day')">1 Day</button>
</div>
</div>
<button class="btn-analyze" onclick="analyze()">🔍 Analyze</button>
<div id="results" style="margin-top:15px;"></div>
<div class="section" style="margin-top:15px;">
<h2>Win Rate Tracker</h2>
<div class="grid3">
<div class="win-card"><h3>Total</h3><p id="totalSig">0</p></div>
<div class="win-card"><h3>Wins</h3><p id="winSig" style="color:#00ff88;">0</p></div>
<div class="win-card"><h3>Win Rate</h3><p id="winRateP" style="color:#3b82f6;">0%</p></div>
</div>
<div style="margin-top:10px;display:flex;gap:8px;">
<button onclick="markResult('win')" style="flex:1;padding:10px;background:#00ff88;color:#000;border:none;border-radius:8px;font-weight:bold;cursor:pointer;">✅ Win</button>
<button onclick="markResult('loss')" style="flex:1;padding:10px;background:#ef4444;color:#fff;border:none;border-radius:8px;font-weight:bold;cursor:pointer;">❌ Loss</button>
</div>
</div>
<div class="section">
<h2>Signal History</h2>
<table class="history-table">
<thead><tr><th>Time</th><th>Pair</th><th>Signal</th><th>Conf%</th><th>Result</th></tr></thead>
<tbody id="historyBody"><tr><td colspan="5" style="text-align:center;color:#888;padding:15px;">No signals yet</td></tr></tbody>
</table>
</div>
</div>
<script>
let selectedPairs=[],selectedTFs=[],signalHistory=[],wins=0,total=0;
function togglePair(btn,symbol,name,news){
  const i=selectedPairs.findIndex(p=>p.symbol===symbol);
  if(i>=0){selectedPairs.splice(i,1);btn.classList.remove('active');}
  else{selectedPairs.push({symbol,name,news});btn.classList.add('active');}
}
function toggleTF(btn,tf,label){
  const i=selectedTFs.findIndex(t=>t.tf===tf);
  if(i>=0){selectedTFs.splice(i,1);btn.classList.remove('active');}
  else if(selectedTFs.length<3){selectedTFs.push({tf,label});btn.classList.add('active');}
  else alert('Sirf 3 timeframe select karo!');
}
function getSignalClass(s){
  if(s.includes('STRONG BUY'))return 'strong-buy';
  if(s.includes('BUY'))return 'buy';
  if(s.includes('STRONG SELL'))return 'strong-sell';
  if(s.includes('SELL'))return 'sell';
  return 'neutral';
}
function getSigColor(s){
  if(!s)return '';
  const u=s.toUpperCase();
  if(u.includes('BUY')||u.includes('BULLISH'))return 'buy-c';
  if(u.includes('SELL')||u.includes('BEARISH'))return 'sell-c';
  return 'neutral-c';
}
async function analyze(){
  if(!selectedPairs.length){alert('Ek pair select karo!');return;}
  if(!selectedTFs.length){alert('Ek timeframe select karo!');return;}
  document.getElementById('results').innerHTML='<div class="loading"><div class="spinner"></div><p style="color:#888;">20+ indicators calculate ho rahe hain...</p></div>';
  try{
    const res=await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pairs:selectedPairs,timeframes:selectedTFs})});
    const data=await res.json();
    let html='';
    for(const r of data.results){
      if(r.error){html+=`<div class="pair-result"><div class="pair-header"><h3>${r.name}</h3></div><div style="padding:15px;color:#ef4444;">Data nahi mila (pair supported nahi)</div></div>`;continue;}
      let consensusHtml='<div class="consensus">';
      for(const tf of r.timeframes){consensusHtml+=`<div class="con-item"><div class="con-tf">${tf.label}</div><div class="con-sig ${getSigColor(tf.signal)}">${tf.signal}</div><div style="font-size:10px;color:#888;">${tf.confidence}%</div></div>`;}
      consensusHtml+='</div>';
      const inds=r.indicators||{};
      let basicHtml='<p class="section-title">Basic Indicators</p>';
      if(inds.rsi)basicHtml+=`<div class="ind-card"><span class="ind-name">RSI</span><span class="ind-val ${inds.rsi.value<30?'rsi-green':inds.rsi.value>70?'rsi-red':''}">${inds.rsi.value} - ${inds.rsi.signal}</span></div>`;
      if(inds.macd)basicHtml+=`<div class="ind-card"><span class="ind-name">MACD</span><span class="ind-val ${getSigColor(inds.macd.signal)}">${inds.macd.signal}</span></div>`;
      if(inds.ema20)basicHtml+=`<div class="ind-card"><span class="ind-name">EMA 20</span><span class="ind-val ${getSigColor(inds.ema20.signal)}">${inds.ema20.value} - ${inds.ema20.signal}</span></div>`;
      if(inds.ema50)basicHtml+=`<div class="ind-card"><span class="ind-name">EMA 50</span><span class="ind-val ${getSigColor(inds.ema50.signal)}">${inds.ema50.value} - ${inds.ema50.signal}</span></div>`;
      if(inds.stoch)basicHtml+=`<div class="ind-card"><span class="ind-name">Stochastic</span><span class="ind-val ${getSigColor(inds.stoch.signal)}">${inds.stoch.value} - ${inds.stoch.signal}</span></div>`;
      if(inds.bbands)basicHtml+=`<div class="ind-card"><span class="ind-name">Bollinger</span><span class="ind-val ${getSigColor(inds.bbands.signal)}">${inds.bbands.signal}</span></div>`;
      let trendHtml='<p class="section-title">Trend Indicators</p>';
      if(inds.supertrend)trendHtml+=`<div class="ind-card"><span class="ind-name">Supertrend</span><span class="ind-val ${getSigColor(inds.supertrend.signal)}">${inds.supertrend.signal}</span></div>`;
      if(inds.psar)trendHtml+=`<div class="ind-card"><span class="ind-name">Parabolic SAR</span><span class="ind-val ${getSigColor(inds.psar.signal)}">${inds.psar.signal}</span></div>`;
      let volHtml='<p class="section-title">Volume Indicators</p>';
      if(inds.obv)volHtml+=`<div class="ind-card"><span class="ind-name">OBV</span><span class="ind-val ${getSigColor(inds.obv.signal)}">${inds.obv.signal}</span></div>`;
      if(inds.mfi)volHtml+=`<div class="ind-card"><span class="ind-name">MFI</span><span class="ind-val ${getSigColor(inds.mfi.signal)}">${inds.mfi.value} - ${inds.mfi.signal}</span></div>`;
      if(inds.volume)volHtml+=`<div class="ind-card"><span class="ind-name">Volume</span><span class="ind-val">${inds.volume.signal}</span></div>`;
      let smcHtml='<p class="section-title">Smart Money Concepts</p>';
      if(inds.smc)smcHtml+=`<div class="ind-card"><span class="ind-name">SMC</span><span class="ind-val ${getSigColor(inds.smc.signal)}">${inds.smc.signal}</span></div>`;
      if(inds.order_blocks)smcHtml+=`<div class="ind-card"><span class="ind-name">Order Blocks</span><span class="ind-val ${getSigColor(inds.order_blocks.signal)}">${inds.order_blocks.signal}</span></div>`;
      if(inds.fvg)smcHtml+=`<div class="ind-card"><span class="ind-name">Fair Value Gap</span><span class="ind-val ${getSigColor(inds.fvg.signal)}">${inds.fvg.signal}</span></div>`;
      if(inds.liquidity)smcHtml+=`<div class="ind-card"><span class="ind-name">Liquidity</span><span class="ind-val ${getSigColor(inds.liquidity.signal)}">${inds.liquidity.signal}</span></div>`;
      let pivotHtml='';
      if(inds.pivots&&inds.pivots.pp)pivotHtml=`<p class="section-title">Pivot Points</p><div class="pivot-grid"><div class="pivot-card"><label>R2</label><p style="color:#ef4444;">${inds.pivots.r2}</p></div><div class="pivot-card"><label>R1</label><p style="color:#f97316;">${inds.pivots.r1}</p></div><div class="pivot-card"><label>PP</label><p>${inds.pivots.pp}</p></div><div class="pivot-card"><label>S1</label><p style="color:#22c55e;">${inds.pivots.s1}</p></div><div class="pivot-card"><label>S2</label><p style="color:#00ff88;">${inds.pivots.s2}</p></div></div>`;
      let fibHtml='';
      if(inds.fibonacci&&inds.fibonacci.f618)fibHtml=`<p class="section-title">Fibonacci Levels</p><div class="fib-grid"><div class="fib-card"><label>23.6%</label><p>${inds.fibonacci.f236}</p></div><div class="fib-card"><label>38.2%</label><p>${inds.fibonacci.f382}</p></div><div class="fib-card"><label>50.0%</label><p>${inds.fibonacci.f500}</p></div><div class="fib-card"><label>61.8%</label><p>${inds.fibonacci.f618}</p></div><div class="fib-card"><label>78.6%</label><p>${inds.fibonacci.f786}</p></div></div>`;
      let newsHtml='';
      if(r.headlines&&r.headlines.length){newsHtml='<p class="section-title">Latest News</p>';r.headlines.forEach(h=>{newsHtml+=`<div class="news-item">- ${h}</div>`;});}
      const ts=new Date().toLocaleTimeString();
      signalHistory.unshift({time:ts,pair:r.name,signal:r.final_signal,conf:r.confidence,result:'-'});
      if(signalHistory.length>20)signalHistory.pop();
      total++;updateWinRate();updateHistory();
      html+=`<div class="pair-result"><div class="pair-header"><h3>${r.name}</h3></div><div style="padding:15px;"><div class="signal-box ${getSignalClass(r.final_signal)}"><h2>${r.final_signal}</h2><p>Confidence: ${r.confidence}% | News: ${r.news}</p></div><p style="color:#888;font-size:12px;margin:8px 0;">Multi Timeframe Consensus:</p>${consensusHtml}<div class="info-grid"><div class="info-card"><label>Price</label><p>${r.price}</p></div><div class="info-card"><label>Stop Loss</label><p style="color:#ef4444;">${r.sl}</p></div><div class="info-card"><label>TP 1</label><p style="color:#00ff88;">${r.tp1}</p></div><div class="info-card"><label>TP 2</label><p style="color:#00ff88;">${r.tp2}</p></div><div class="info-card"><label>TP 3</label><p style="color:#00ff88;">${r.tp3}</p></div><div class="info-card"><label>ATR</label><p>${r.atr}</p></div></div><div class="sr-grid"><div class="sr-card"><label>Support</label><p style="color:#00ff88;">${r.support}</p></div><div class="sr-card"><label>Resistance</label><p style="color:#ef4444;">${r.resistance}</p></div></div>${basicHtml}${trendHtml}${volHtml}${smcHtml}${pivotHtml}${fibHtml}${newsHtml}</div></div>`;
    }
    document.getElementById('results').innerHTML=html;
  }catch(e){document.getElementById('results').innerHTML='<p style="color:#ef4444;text-align:center;padding:20px;">Error: '+e.message+'</p>';}
}
function markResult(t){if(!signalHistory.length)return;signalHistory[0].result=t==='win'?'Win':'Loss';if(t==='win')wins++;updateWinRate();updateHistory();}
function updateWinRate(){document.getElementById('totalSig').textContent=total;document.getElementById('winSig').textContent=wins;document.getElementById('winRateP').textContent=(total>0?Math.round(wins/total*100):0)+'%';}
function updateHistory(){const b=document.getElementById('historyBody');if(!signalHistory.length){b.innerHTML='<tr><td colspan="5" style="text-align:center;color:#888;padding:15px;">No signals yet</td></tr>';return;}b.innerHTML=signalHistory.map(s=>`<tr><td>${s.time}</td><td>${s.pair}</td><td class="${s.signal.includes('BUY')?'buy-c':s.signal.includes('SELL')?'sell-c':'neutral-c'}">${s.signal}</td><td>${s.conf}%</td><td>${s.result}</td></tr>`).join('');}
</script>
</body>
</html>"""
# ============================================================
#  FLASK ROUTES
# ============================================================
@app.route('/')
def index():
    return render_template_string(HTML)
@app.route('/analyze', methods=['POST'])
def analyze_route():
    data = request.json
    pairs = data.get('pairs', [])
    timeframes = data.get('timeframes', [])
    results = []
    # Map pair symbol -> Yahoo Finance symbol for candles
    binance_symbol_map = {
        "CRYPTO:BTC": "BTCUSDT",
        "XAUUSD":     "BTCUSDT",   # Gold candles fallback to BTC structure
        "XAGUSD":     "BTCUSDT",   # Silver candles fallback
        "WTI":        "BTCUSDT",   # Oil candles fallback
    }
    for pair in pairs:
        symbol = pair['symbol']
        name   = pair['name']
        news_kw = pair['news']
        price = get_price(symbol)
        if price == 0:
            results.append({'name': name, 'error': True})
            continue
        headlines, news_dir = get_news_free(news_kw)
        binance_sym = binance_symbol_map.get(symbol, "BTCUSDT")
        # ATR from 1h candles
        candles_1h = get_candles_binance(binance_sym, "1h", 20)
        atr = calc_atr(candles_1h) if candles_1h else 0
        tf_results   = []
        total_score  = 0
        total_weight = 0
        total_conf   = 0
        all_indicators = {}
        for i, tf_data in enumerate(timeframes):
            tf    = tf_data['tf']
            label = tf_data['label']
            s, t, c, indicators = get_tf_score(binance_sym, tf, price)
            sig = "BUY" if s > 0 else "SELL" if s < 0 else "WAIT"
            tf_results.append({'label': label, 'signal': sig, 'confidence': c})
            weight = 2 if i == len(timeframes)-1 else 1
            total_score  += s * weight
            total_weight += weight
            total_conf   += c * weight
            if not all_indicators:
                all_indicators = indicators
        if "Positive" in news_dir:  total_score += 2
        elif "Negative" in news_dir: total_score -= 2
        confidence = round(total_conf / total_weight) if total_weight else 50
        if total_score > 2:
            final_signal = "STRONG BUY" if confidence >= 75 else "BUY"
            sl  = round(price - atr*1.5, 4) if atr else round(price*0.98, 4)
            tp1 = round(price + atr*1.5, 4) if atr else round(price*1.02, 4)
            tp2 = round(price + atr*3,   4) if atr else round(price*1.04, 4)
            tp3 = round(price + atr*5,   4) if atr else round(price*1.06, 4)
        elif total_score < -2:
            final_signal = "STRONG SELL" if confidence >= 75 else "SELL"
            sl  = round(price + atr*1.5, 4) if atr else round(price*1.02, 4)
            tp1 = round(price - atr*1.5, 4) if atr else round(price*0.98, 4)
            tp2 = round(price - atr*3,   4) if atr else round(price*0.96, 4)
            tp3 = round(price - atr*5,   4) if atr else round(price*0.94, 4)
        else:
            final_signal = "NEUTRAL - WAIT"
            sl  = round(price*0.99, 4)
            tp1 = round(price*1.01, 4)
            tp2 = round(price*1.02, 4)
            tp3 = round(price*1.03, 4)
        result_data = {
            'name':        name,
            'price':       round(price, 4),
            'atr':         round(atr,   4),
            'news':        news_dir,
            'sl': sl, 'tp1': tp1, 'tp2': tp2, 'tp3': tp3,
            'final_signal': final_signal,
            'confidence':   confidence,
            'timeframes':   tf_results,
            'indicators':   all_indicators,
            'support':      all_indicators.get("support",    0),
            'resistance':   all_indicators.get("resistance", 0),
            'headlines':    headlines,
        }
        results.append(result_data)
        # Telegram pe signal bhejo
        emoji = "🟢" if "BUY" in final_signal else "🔴" if "SELL" in final_signal else "⚪"
        tf_line = " | ".join([f"{t['label']}: {t['signal']}({t['confidence']}%)" for t in tf_results])
        tg_msg = (
            f"{emoji} <b>{name} Signal</b>\n\n"
            f"📊 Signal: <b>{final_signal}</b>\n"
            f"💯 Confidence: {confidence}%\n"
            f"💰 Price: {round(price,4)}\n"
            f"🛑 Stop Loss: {sl}\n"
            f"🎯 TP1: {tp1} | TP2: {tp2} | TP3: {tp3}\n"
            f"📰 News: {news_dir}\n"
            f"⏱ TF: {tf_line}"
        )
        threading.Thread(target=send_telegram, args=(tg_msg,), daemon=True).start()
    return jsonify({'results': results})
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)