from flask import Flask, render_template_string, jsonify, request
import requests
from textblob import TextBlob
import time

app = Flask(__name__)

TWELVE_KEY = "8a118b37963347c0941f8736b2aaf6c2"
ALPHA_KEY = "WJ7ZFIBBMPUTCIAY"

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Bot</title>
    <meta charset="UTF-8">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#0d1117; color:#fff; font-family:Arial; }
        .header { background:#161b22; padding:20px; text-align:center; border-bottom:2px solid #00ff88; }
        .header h1 { color:#00ff88; font-size:28px; }
        .header p { color:#888; margin-top:5px; }
        .container { max-width:900px; margin:30px auto; padding:20px; }
        .section { background:#161b22; border-radius:10px; padding:20px; margin-bottom:20px; border:1px solid #30363d; }
        .section h2 { color:#00ff88; margin-bottom:15px; }
        .grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; }
        .btn { padding:12px 20px; border:none; border-radius:8px; cursor:pointer; font-size:16px; font-weight:bold; transition:0.3s; }
        .btn-pair { background:#1f2937; color:#fff; border:2px solid #30363d; }
        .btn-pair:hover { border-color:#00ff88; color:#00ff88; }
        .btn-pair.active { background:#00ff88; color:#000; border-color:#00ff88; }
        .btn-tf { background:#1f2937; color:#fff; border:2px solid #30363d; }
        .btn-tf:hover { border-color:#3b82f6; color:#3b82f6; }
        .btn-tf.active { background:#3b82f6; color:#fff; border-color:#3b82f6; }
        .btn-analyze { background:#00ff88; color:#000; width:100%; padding:15px; font-size:18px; border-radius:8px; margin-top:10px; }
        .btn-analyze:hover { background:#00cc66; }
        .result { background:#0d1117; border-radius:10px; padding:20px; margin-top:10px; border:1px solid #30363d; }
        .signal-box { border-radius:10px; padding:20px; text-align:center; margin:15px 0; }
        .strong-buy { background:linear-gradient(135deg,#00ff88,#00cc66); color:#000; }
        .buy { background:linear-gradient(135deg,#22c55e,#16a34a); color:#fff; }
        .strong-sell { background:linear-gradient(135deg,#ef4444,#dc2626); color:#fff; }
        .sell { background:linear-gradient(135deg,#f97316,#ea580c); color:#fff; }
        .neutral { background:linear-gradient(135deg,#6b7280,#4b5563); color:#fff; }
        .signal-box h2 { font-size:28px; }
        .signal-box p { font-size:18px; margin-top:5px; }
        .info-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin:15px 0; }
        .info-card { background:#161b22; border-radius:8px; padding:15px; border:1px solid #30363d; }
        .info-card label { color:#888; font-size:12px; }
        .info-card p { color:#fff; font-size:18px; font-weight:bold; margin-top:5px; }
        .tf-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:15px 0; }
        .tf-card { background:#161b22; border-radius:8px; padding:12px; text-align:center; border:1px solid #30363d; }
        .tf-card h4 { color:#888; font-size:12px; }
        .tf-card p { font-size:16px; font-weight:bold; margin-top:5px; }
        .buy-color { color:#00ff88; }
        .sell-color { color:#ef4444; }
        .wait-color { color:#6b7280; }
        .loading { text-align:center; padding:40px; }
        .loading p { color:#888; font-size:18px; }
        .spinner { border:4px solid #30363d; border-top:4px solid #00ff88; border-radius:50%; width:50px; height:50px; animation:spin 1s linear infinite; margin:20px auto; }
        @keyframes spin { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }
        .news { background:#161b22; border-radius:8px; padding:15px; margin-top:10px; }
        .news h4 { color:#00ff88; margin-bottom:10px; }
        .news p { color:#aaa; font-size:13px; margin:5px 0; }
        .pair-result { margin-bottom:30px; border:1px solid #30363d; border-radius:10px; overflow:hidden; }
        .pair-header { background:#161b22; padding:15px 20px; border-bottom:1px solid #30363d; }
        .pair-header h3 { color:#fff; font-size:20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Advanced Trading Bot</h1>
        <p>TradingView Style Signals + Multi Timeframe Analysis</p>
    </div>

    <div class="container">
        <div class="section">
            <h2>💹 Pair Select کریں</h2>
            <div class="grid">
                <button class="btn btn-pair" onclick="togglePair(this,'XAU/USD','GOLD','XAUUSD')">🥇 Gold</button>
                <button class="btn btn-pair" onclick="togglePair(this,'BTC/USD','BITCOIN','CRYPTO:BTC')">₿ Bitcoin</button>
                <button class="btn btn-pair" onclick="togglePair(this,'SLV','SILVER','XAGUSD')">🥈 Silver</button>
                <button class="btn btn-pair" onclick="togglePair(this,'USO','CRUDE OIL','WTI')">🛢️ Crude Oil</button>
            </div>
        </div>

        <div class="section">
            <h2>⏱️ Timeframe Select کریں (3 select کریں)</h2>
            <div class="grid">
                <button class="btn btn-tf" onclick="toggleTF(this,'5min','5 Min')">5 Minute</button>
                <button class="btn btn-tf" onclick="toggleTF(this,'15min','15 Min')">15 Minute</button>
                <button class="btn btn-tf" onclick="toggleTF(this,'30min','30 Min')">30 Minute</button>
                <button class="btn btn-tf" onclick="toggleTF(this,'1h','1 Hour')">1 Hour</button>
                <button class="btn btn-tf" onclick="toggleTF(this,'4h','4 Hour')">4 Hour</button>
                <button class="btn btn-tf" onclick="toggleTF(this,'1day','1 Day')">1 Day</button>
            </div>
        </div>

        <button class="btn btn-analyze" onclick="analyze()">🚀 Analyze کریں</button>

        <div id="results" style="margin-top:20px;"></div>
    </div>

    <script>
        let selectedPairs = [];
        let selectedTFs = [];

        function togglePair(btn, symbol, name, news) {
            const exists = selectedPairs.findIndex(p => p.symbol === symbol);
            if (exists >= 0) {
                selectedPairs.splice(exists, 1);
                btn.classList.remove('active');
            } else {
                selectedPairs.push({symbol, name, news});
                btn.classList.add('active');
            }
        }

        function toggleTF(btn, tf, label) {
            const exists = selectedTFs.findIndex(t => t.tf === tf);
            if (exists >= 0) {
                selectedTFs.splice(exists, 1);
                btn.classList.remove('active');
            } else if (selectedTFs.length < 3) {
                selectedTFs.push({tf, label});
                btn.classList.add('active');
            } else {
                alert('صرف 3 timeframes select کریں!');
            }
        }

        function getSignalClass(signal) {
            if (signal.includes('STRONG BUY')) return 'strong-buy';
            if (signal.includes('BUY')) return 'buy';
            if (signal.includes('STRONG SELL')) return 'strong-sell';
            if (signal.includes('SELL')) return 'sell';
            return 'neutral';
        }

        function getTFColor(sig) {
            if (sig.includes('BUY')) return 'buy-color';
            if (sig.includes('SELL')) return 'sell-color';
            return 'wait-color';
        }

        async function analyze() {
            if (selectedPairs.length === 0) {
                alert('کوئی pair select کریں!');
                return;
            }
            if (selectedTFs.length === 0) {
                alert('کوئی timeframe select کریں!');
                return;
            }

            document.getElementById('results').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analyzing... please wait</p>
                </div>`;

            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({pairs: selectedPairs, timeframes: selectedTFs})
            });

            const data = await response.json();
            let html = '';

            for (const result of data.results) {
                if (result.error) {
                    html += `<div class="pair-result">
                        <div class="pair-header"><h3>${result.name}</h3></div>
                        <div style="padding:20px;color:#ef4444;">⚠️ No data found</div>
                    </div>`;
                    continue;
                }

                let tfHtml = '';
                for (const tf of result.timeframes) {
                    tfHtml += `
                        <div class="tf-card">
                            <h4>${tf.label}</h4>
                            <p class="${getTFColor(tf.signal)}">${tf.signal}</p>
                            <p style="color:#888;font-size:13px;">${tf.confidence}%</p>
                        </div>`;
                }

                let newsHtml = '';
                if (result.headlines && result.headlines.length > 0) {
                    newsHtml = `<div class="news"><h4>📰 Latest News</h4>`;
                    for (const h of result.headlines) {
                        newsHtml += `<p>• ${h}</p>`;
                    }
                    newsHtml += `</div>`;
                }

                html += `
                <div class="pair-result">
                    <div class="pair-header"><h3>🔍 ${result.name}</h3></div>
                    <div style="padding:20px;">
                        <div class="signal-box ${getSignalClass(result.final_signal)}">
                            <h2>${result.final_signal}</h2>
                            <p>Confidence: ${result.confidence}% | News: ${result.news}</p>
                        </div>
                        <div class="info-grid">
                            <div class="info-card">
                                <label>💰 Price</label>
                                <p>${result.price}</p>
                            </div>
                            <div class="info-card">
                                <label>🛑 Stop Loss</label>
                                <p style="color:#ef4444;">${result.sl}</p>
                            </div>
                            <div class="info-card">
                                <label>🎯 TP Level 1</label>
                                <p style="color:#00ff88;">${result.tp1}</p>
                            </div>
                            <div class="info-card">
                                <label>🎯 TP Level 2</label>
                                <p style="color:#00ff88;">${result.tp2}</p>
                            </div>
                            <div class="info-card">
                                <label>🎯 TP Level 3</label>
                                <p style="color:#00ff88;">${result.tp3}</p>
                            </div>
                            <div class="info-card">
                                <label>📊 ATR</label>
                                <p>${result.atr}</p>
                            </div>
                        </div>
                        <h4 style="color:#888;margin:10px 0;">⏱️ Timeframe Analysis</h4>
                        <div class="tf-grid">${tfHtml}</div>
                        ${newsHtml}
                    </div>
                </div>`;
            }

            document.getElementById('results').innerHTML = html;
        }
    </script>
</body>
</html>
"""

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
            headlines.append(title[:60])
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
        if rsi < 30: score += 1
        elif rsi > 70: score -= 1

    d = get_data("macd", symbol, interval)
    if d:
        total += 1
        if float(d["macd"]) > float(d["macd_signal"]): score += 1
        else: score -= 1

    d = get_data("ema", symbol, interval, "&time_period=20")
    if d:
        total += 1
        if price > float(d["ema"]): score += 1
        else: score -= 1

    d = get_data("ema", symbol, interval, "&time_period=50")
    if d:
        total += 1
        if price > float(d["ema"]): score += 1
        else: score -= 1

    d = get_data("stoch", symbol, interval)
    if d:
        stoch_k = float(d["slow_k"])
        total += 1
        if stoch_k < 20: score += 1
        elif stoch_k > 80: score -= 1

    d = get_data("bbands", symbol, interval)
    if d:
        total += 1
        if price < float(d["lower_band"]): score += 1
        elif price > float(d["upper_band"]): score -= 1

    d = get_data("cci", symbol, interval)
    if d:
        cci = float(d["cci"])
        total += 1
        if cci < -100: score += 1
        elif cci > 100: score -= 1

    d = get_data("willr", symbol, interval)
    if d:
        willr = float(d["willr"])
        total += 1
        if willr < -80: score += 1
        elif willr > -20: score -= 1

    candles = get_candles(symbol, interval)
    if len(candles) > 5:
        highs = [float(c["high"]) for c in candles[1:]]
        lows = [float(c["low"]) for c in candles[1:]]
        total += 1
        if float(candles[0]["low"]) < min(lows) and price > min(lows): score += 1
        elif float(candles[0]["high"]) > max(highs) and price < max(highs): score -= 1

    return score, total

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    pairs = data.get('pairs', [])
    timeframes = data.get('timeframes', [])
    results = []

    for pair in pairs:
        symbol = pair['symbol']
        name = pair['name']
        news_keyword = pair['news']

        price = get_price(symbol)
        if price == 0:
            results.append({'name': name, 'error': True})
            continue

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

        tf_results = []
        total_score = 0
        total_ind = 0

        for i, tf_data in enumerate(timeframes):
            tf = tf_data['tf']
            label = tf_data['label']
            s, t = get_tf_score(symbol, tf, price)
            c = min(round(abs(s / t * 100) + 50) if t > 0 else 50, 95)
            sig = "BUY ✅" if s > 0 else "SELL ❌" if s < 0 else "WAIT ⚪"
            tf_results.append({'label': label, 'signal': sig, 'confidence': c})
            weight = 2 if i == len(timeframes) - 1 else 1
            total_score += s * weight
            total_ind += t * weight

        if "Positive" in news_dir:
            total_score += 2
        elif "Negative" in news_dir:
            total_score -= 2

        confidence = min(round(abs(total_score / total_ind * 100) + 50), 95) if total_ind > 0 else 50

        if total_score > 2:
            final_signal = "✅✅✅ STRONG BUY" if confidence >= 80 else "✅ BUY"
        elif total_score < -2:
            final_signal = "❌❌❌ STRONG SELL" if confidence >= 80 else "❌ SELL"
            sl  = round(price + (atr * 1.5), 2) if atr > 0 else round(price * 1.02, 2)
            tp1 = round(price - (atr * 1.5), 2) if atr > 0 else round(price * 0.98, 2)
            tp2 = round(price - (atr * 3),   2) if atr > 0 else round(price * 0.96, 2)
            tp3 = round(price - (atr * 5),   2) if atr > 0 else round(price * 0.94, 2)
        else:
            final_signal = "⚪ NEUTRAL — WAIT"

        results.append({
            'name': name,
            'price': round(price, 2),
            'atr': round(atr, 2),
            'news': news_dir,
            'sl': sl,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'final_signal': final_signal,
            'confidence': confidence,
            'timeframes': tf_results,
            'headlines': headlines
        })

    return jsonify({'results': results})

if __name__ == '__main__':
 import os
port = int(os.environ.get('PORT', 5000))
app.run(debug=False, host='0.0.0.0', port=port) 