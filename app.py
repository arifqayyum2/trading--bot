from flask import Flask, render_template_string, jsonify, request
import requests
from textblob import TextBlob
import time
import os

TWELVE_KEY = "8a118b37963347c0941f8736b2aaf6c2"
ALPHA_KEY = "WJ7ZFIBBMPUTCIAY"

app = Flask(__name__)

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
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=50&apikey={TWELVE_KEY}"
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
            return headlines, "Positive"
        elif avg < -0.1:
            return headlines, "Negative"
        else:
            return headlines, "Neutral"
    except:
        return [], "Neutral"

def get_tf_score(symbol, interval, price):
    weighted_score = 0
    max_score = 0
    indicators = {}

    d = get_data("rsi", symbol, interval)
    if d:
        rsi = float(d["rsi"])
        max_score += 25
        if rsi < 30:
            weighted_score += 25
            rsi_signal = "BUY"
        elif rsi > 70:
            weighted_score -= 25
            rsi_signal = "SELL"
        elif rsi < 45:
            weighted_score += 15
            rsi_signal = "BUY"
        elif rsi > 55:
            weighted_score -= 15
            rsi_signal = "SELL"
        else:
            rsi_signal = "NEUTRAL"
        indicators["rsi"] = {"value": round(rsi, 1), "signal": rsi_signal}

    d = get_data("macd", symbol, interval)
    if d:
        macd = float(d["macd"])
        macd_sig = float(d["macd_signal"])
        diff = macd - macd_sig
        max_score += 20
        if diff > 0:
            weighted_score += 20
            macd_signal = "BUY"
        else:
            weighted_score -= 20
            macd_signal = "SELL"
        indicators["macd"] = {"signal": macd_signal}

    d = get_data("ema", symbol, interval, "&time_period=20")
    if d:
        ema20 = float(d["ema"])
        max_score += 10
        if price > ema20:
            weighted_score += 10
            ema20_signal = "BUY"
        else:
            weighted_score -= 10
            ema20_signal = "SELL"
        indicators["ema20"] = {"value": round(ema20, 2), "signal": ema20_signal}

    d = get_data("ema", symbol, interval, "&time_period=50")
    if d:
        ema50 = float(d["ema"])
        max_score += 10
        if price > ema50:
            weighted_score += 10
            ema50_signal = "BUY"
        else:
            weighted_score -= 10
            ema50_signal = "SELL"
        indicators["ema50"] = {"value": round(ema50, 2), "signal": ema50_signal}

    d = get_data("stoch", symbol, interval)
    if d:
        stoch_k = float(d["slow_k"])
        max_score += 15
        if stoch_k < 20:
            weighted_score += 15
            stoch_signal = "BUY"
        elif stoch_k > 80:
            weighted_score -= 15
            stoch_signal = "SELL"
        else:
            stoch_signal = "NEUTRAL"
        indicators["stoch"] = {"value": round(stoch_k, 1), "signal": stoch_signal}

    d = get_data("bbands", symbol, interval)
    if d:
        upper = float(d["upper_band"])
        lower = float(d["lower_band"])
        max_score += 10
        if price < lower:
            weighted_score += 10
            bb_signal = "BUY"
        elif price > upper:
            weighted_score -= 10
            bb_signal = "SELL"
        else:
            bb_signal = "NEUTRAL"
        indicators["bbands"] = {"signal": bb_signal}

    # Support & Resistance from candles
    candles = get_candles(symbol, interval)
    support = 0
    resistance = 0
    if candles and len(candles) >= 10:
        highs = [float(c["high"]) for c in candles[:30]]
        lows = [float(c["low"]) for c in candles[:30]]
        resistance = round(max(highs), 2)
        support = round(min(lows), 2)
        max_score += 10
        if len(candles) > 5:
            all_highs = [float(c["high"]) for c in candles[1:]]
            all_lows = [float(c["low"]) for c in candles[1:]]
            if float(candles[0]["low"]) < min(all_lows) and price > min(all_lows):
                weighted_score += 10
                liq_signal = "BULLISH SWEEP"
            elif float(candles[0]["high"]) > max(all_highs) and price < max(all_highs):
                weighted_score -= 10
                liq_signal = "BEARISH SWEEP"
            else:
                liq_signal = "NO SWEEP"
            indicators["liquidity"] = {"signal": liq_signal}

    indicators["support"] = support
    indicators["resistance"] = resistance

    if max_score > 0:
        confidence = round(((weighted_score + max_score) / (2 * max_score)) * 100)
        confidence = max(0, min(confidence, 100))
    else:
        confidence = 50

    return weighted_score, max_score, confidence, indicators

HTML = """<!DOCTYPE html>
<html>
<head>
<title>Advanced Trading Bot</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#fff;font-family:Arial}
.header{background:#161b22;padding:15px;text-align:center;border-bottom:2px solid #00ff88}
.header h1{color:#00ff88;font-size:22px}
.header p{color:#888;font-size:12px;margin-top:3px}
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
.tf-card{background:#0d1117;border-radius:8px;padding:10px;text-align:center;border:1px solid #30363d}
.ind-card{background:#0d1117;border-radius:6px;padding:8px;border:1px solid #30363d;display:flex;justify-content:space-between;align-items:center;margin:4px 0}
.ind-name{color:#888;font-size:11px}
.ind-val{font-size:12px;font-weight:bold}
.buy-c{color:#00ff88}
.sell-c{color:#ef4444}
.neutral-c{color:#6b7280}
.rsi-green{color:#00ff88;font-weight:bold}
.rsi-red{color:#ef4444;font-weight:bold}
.consensus{display:flex;gap:6px;margin:8px 0}
.con-item{flex:1;background:#0d1117;border-radius:6px;padding:8px;text-align:center;border:1px solid #30363d}
.con-tf{color:#888;font-size:10px}
.con-sig{font-size:13px;font-weight:bold;margin-top:3px}
.history-table{width:100%;border-collapse:collapse;font-size:12px}
.history-table th{background:#1f2937;padding:8px;text-align:left;color:#888}
.history-table td{padding:8px;border-bottom:1px solid #30363d}
.win-card{background:#0d1117;border-radius:8px;padding:12px;text-align:center;border:1px solid #30363d}
.win-card h3{color:#888;font-size:12px}
.win-card p{font-size:22px;font-weight:bold;margin-top:5px}
.loading{text-align:center;padding:30px}
.spinner{border:4px solid #30363d;border-top:4px solid #00ff88;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin:15px auto}
@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
.news-item{color:#aaa;font-size:12px;margin:4px 0;padding:4px 0;border-bottom:1px solid #30363d}
.pair-result{margin-bottom:15px;border:1px solid #30363d;border-radius:10px;overflow:hidden}
.pair-header{background:#1f2937;padding:12px 15px}
.pair-header h3{font-size:18px}
.sr-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:8px 0}
.sr-card{background:#0d1117;border-radius:8px;padding:10px;border:1px solid #30363d;text-align:center}
.sr-card label{color:#888;font-size:11px}
.sr-card p{font-size:15px;font-weight:bold;margin-top:3px}
</style>
</head>
<body>
<div class="header">
<h1>Advanced Trading Bot</h1>
<p>TradingView Style + Multi Timeframe + Smart Confidence</p>
</div>
<div class="container">
<div class="section">
<h2>Pair Select</h2>
<div class="grid2">
<button class="btn btn-pair" onclick="togglePair(this,'XAU/USD','GOLD','XAUUSD')">Gold</button>
<button class="btn btn-pair" onclick="togglePair(this,'BTC/USD','BITCOIN','CRYPTO:BTC')">Bitcoin</button>
<button class="btn btn-pair" onclick="togglePair(this,'SLV','SILVER','XAGUSD')">Silver</button>
<button class="btn btn-pair" onclick="togglePair(this,'USO','CRUDE OIL','WTI')">Crude Oil</button>
</div>
</div>
<div class="section">
<h2>Timeframe Select (3 select)</h2>
<div class="grid2">
<button class="btn btn-tf" onclick="toggleTF(this,'5min','5 Min')">5 Minute</button>
<button class="btn btn-tf" onclick="toggleTF(this,'15min','15 Min')">15 Minute</button>
<button class="btn btn-tf" onclick="toggleTF(this,'30min','30 Min')">30 Minute</button>
<button class="btn btn-tf" onclick="toggleTF(this,'1h','1 Hour')">1 Hour</button>
<button class="btn btn-tf" onclick="toggleTF(this,'4h','4 Hour')">4 Hour</button>
<button class="btn btn-tf" onclick="toggleTF(this,'1day','1 Day')">1 Day</button>
</div>
</div>
<button class="btn-analyze" onclick="analyze()">Analyze</button>
<div id="results" style="margin-top:15px;"></div>
<div class="section" style="margin-top:15px;">
<h2>Win Rate Tracker</h2>
<div class="grid3">
<div class="win-card"><h3>Total</h3><p id="totalSig">0</p></div>
<div class="win-card"><h3>Wins</h3><p id="winSig" style="color:#00ff88;">0</p></div>
<div class="win-card"><h3>Win Rate</h3><p id="winRateP" style="color:#3b82f6;">0%</p></div>
</div>
<div style="margin-top:10px;display:flex;gap:8px;">
<button onclick="markResult('win')" style="flex:1;padding:10px;background:#00ff88;color:#000;border:none;border-radius:8px;font-weight:bold;cursor:pointer;">Win</button>
<button onclick="markResult('loss')" style="flex:1;padding:10px;background:#ef4444;color:#fff;border:none;border-radius:8px;font-weight:bold;cursor:pointer;">Loss</button>
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
let selectedPairs=[];
let selectedTFs=[];
let signalHistory=[];
let wins=0;
let total=0;

function togglePair(btn,symbol,name,news){
const exists=selectedPairs.findIndex(p=>p.symbol===symbol);
if(exists>=0){selectedPairs.splice(exists,1);btn.classList.remove('active');}
else{selectedPairs.push({symbol,name,news});btn.classList.add('active');}
}

function toggleTF(btn,tf,label){
const exists=selectedTFs.findIndex(t=>t.tf===tf);
if(exists>=0){selectedTFs.splice(exists,1);btn.classList.remove('active');}
else if(selectedTFs.length<3){selectedTFs.push({tf,label});btn.classList.add('active');}
else{alert('Select only 3 timeframes!');}
}

function getSignalClass(signal){
if(signal.includes('STRONG BUY'))return 'strong-buy';
if(signal.includes('BUY'))return 'buy';
if(signal.includes('STRONG SELL'))return 'strong-sell';
if(signal.includes('SELL'))return 'sell';
return 'neutral';
}

function getTFColor(sig){
if(sig.includes('BUY'))return 'buy-c';
if(sig.includes('SELL'))return 'sell-c';
return 'neutral-c';
}

async function analyze(){
if(selectedPairs.length===0){alert('Select a pair!');return;}
if(selectedTFs.length===0){alert('Select a timeframe!');return;}
document.getElementById('results').innerHTML='<div class="loading"><div class="spinner"></div><p style="color:#888;">Analyzing...</p></div>';
try{
const response=await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pairs:selectedPairs,timeframes:selectedTFs})});
const data=await response.json();
let html='';
for(const result of data.results){
if(result.error){html+=`<div class="pair-result"><div class="pair-header"><h3>${result.name}</h3></div><div style="padding:15px;color:#ef4444;">No data found</div></div>`;continue;}
let consensusHtml='<div class="consensus">';
for(const tf of result.timeframes){
const col=getTFColor(tf.signal);
consensusHtml+=`<div class="con-item"><div class="con-tf">${tf.label}</div><div class="con-sig ${col}">${tf.signal}</div><div style="font-size:10px;color:#888;">${tf.confidence}%</div></div>`;
}
consensusHtml+='</div>';
let indHtml='';
const inds=result.indicators||{};
if(inds.rsi){const rc=inds.rsi.value<30?'rsi-green':inds.rsi.value>70?'rsi-red':'';indHtml+=`<div class="ind-card"><span class="ind-name">RSI</span><span class="ind-val ${rc}">${inds.rsi.value} - ${inds.rsi.signal}</span></div>`;}
if(inds.macd){const mc=inds.macd.signal==='BUY'?'buy-c':'sell-c';indHtml+=`<div class="ind-card"><span class="ind-name">MACD</span><span class="ind-val ${mc}">${inds.macd.signal}</span></div>`;}
if(inds.ema20){const ec=inds.ema20.signal==='BUY'?'buy-c':'sell-c';indHtml+=`<div class="ind-card"><span class="ind-name">EMA 20</span><span class="ind-val ${ec}">${inds.ema20.value} - ${inds.ema20.signal}</span></div>`;}
if(inds.ema50){const ec=inds.ema50.signal==='BUY'?'buy-c':'sell-c';indHtml+=`<div class="ind-card"><span class="ind-name">EMA 50</span><span class="ind-val ${ec}">${inds.ema50.value} - ${inds.ema50.signal}</span></div>`;}
if(inds.stoch){const sc=inds.stoch.signal==='BUY'?'buy-c':inds.stoch.signal==='SELL'?'sell-c':'neutral-c';indHtml+=`<div class="ind-card"><span class="ind-name">Stoch</span><span class="ind-val ${sc}">${inds.stoch.value} - ${inds.stoch.signal}</span></div>`;}
if(inds.bbands){const bc=inds.bbands.signal==='BUY'?'buy-c':inds.bbands.signal==='SELL'?'sell-c':'neutral-c';indHtml+=`<div class="ind-card"><span class="ind-name">Bollinger</span><span class="ind-val ${bc}">${inds.bbands.signal}</span></div>`;}
if(inds.liquidity){indHtml+=`<div class="ind-card"><span class="ind-name">Liquidity</span><span class="ind-val">${inds.liquidity.signal}</span></div>`;}
let newsHtml='';
if(result.headlines&&result.headlines.length>0){newsHtml='<div style="margin-top:8px;"><p style="color:#888;font-size:11px;margin-bottom:5px;">Latest News:</p>';for(const h of result.headlines){newsHtml+=`<div class="news-item">- ${h}</div>`;}newsHtml+='</div>';}
const timestamp=new Date().toLocaleTimeString();
signalHistory.unshift({time:timestamp,pair:result.name,signal:result.final_signal,conf:result.confidence,result:'-'});
if(signalHistory.length>20)signalHistory.pop();
total++;
updateWinRate();
updateHistory();
html+=`<div class="pair-result"><div class="pair-header"><h3>${result.name}</h3></div><div style="padding:15px;"><div class="signal-box ${getSignalClass(result.final_signal)}"><h2>${result.final_signal}</h2><p>Confidence: ${result.confidence}% | News: ${result.news}</p></div><p style="color:#888;font-size:12px;margin:8px 0;">Multi Timeframe Consensus:</p>${consensusHtml}<div class="info-grid"><div class="info-card"><label>Price</label><p>${result.price}</p></div><div class="info-card"><label>Stop Loss</label><p style="color:#ef4444;">${result.sl}</p></div><div class="info-card"><label>TP Level 1</label><p style="color:#00ff88;">${result.tp1}</p></div><div class="info-card"><label>TP Level 2</label><p style="color:#00ff88;">${result.tp2}</p></div><div class="info-card"><label>TP Level 3</label><p style="color:#00ff88;">${result.tp3}</p></div><div class="info-card"><label>ATR</label><p>${result.atr}</p></div></div><div class="sr-grid"><div class="sr-card"><label>Support</label><p style="color:#00ff88;">${result.support}</p></div><div class="sr-card"><label>Resistance</label><p style="color:#ef4444;">${result.resistance}</p></div></div><p style="color:#888;font-size:12px;margin:8px 0;">Indicators:</p>${indHtml}${newsHtml}</div></div>`;
}
document.getElementById('results').innerHTML=html;
}catch(e){document.getElementById('results').innerHTML='<p style="color:#ef4444;text-align:center;padding:20px;">Error: '+e.message+'</p>';}
}

function markResult(type){
if(signalHistory.length===0)return;
signalHistory[0].result=type==='win'?'Win':'Loss';
if(type==='win')wins++;
updateWinRate();
updateHistory();
}

function updateWinRate(){
document.getElementById('totalSig').textContent=total;
document.getElementById('winSig').textContent=wins;
const rate=total>0?Math.round((wins/total)*100):0;
document.getElementById('winRateP').textContent=rate+'%';
}

function updateHistory(){
const tbody=document.getElementById('historyBody');
if(signalHistory.length===0){tbody.innerHTML='<tr><td colspan="5" style="text-align:center;color:#888;padding:15px;">No signals yet</td></tr>';return;}
tbody.innerHTML=signalHistory.map(s=>{const sc=s.signal.includes('BUY')?'buy-c':s.signal.includes('SELL')?'sell-c':'neutral-c';return `<tr><td>${s.time}</td><td>${s.pair}</td><td class="${sc}">${s.signal}</td><td>${s.conf}%</td><td>${s.result}</td></tr>`;}).join('');
}
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/analyze', methods=['POST'])
def analyze_route():
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

        tf_results = []
        total_conf = 0
        total_weight = 0
        total_score = 0
        all_indicators = {}

        for i, tf_data in enumerate(timeframes):
            tf = tf_data['tf']
            label = tf_data['label']
            s, t, c, indicators = get_tf_score(symbol, tf, price)
            sig = "BUY" if s > 0 else "SELL" if s < 0 else "WAIT"
            tf_results.append({'label': label, 'signal': sig, 'confidence': c})
            weight = 2 if i == len(timeframes) - 1 else 1
            total_score += s * weight
            total_weight += weight
            total_conf += c * weight
            if not all_indicators:
                all_indicators = indicators

        if "Positive" in news_dir:
            total_score += 2
        elif "Negative" in news_dir:
            total_score -= 2

        confidence = round(total_conf / total_weight) if total_weight > 0 else 50

        if total_score > 2:
            final_signal = "STRONG BUY" if confidence >= 75 else "BUY"
            sl = round(price - (atr * 1.5), 2) if atr > 0 else round(price * 0.98, 2)
            tp1 = round(price + (atr * 1.5), 2) if atr > 0 else round(price * 1.02, 2)
            tp2 = round(price + (atr * 3), 2) if atr > 0 else round(price * 1.04, 2)
            tp3 = round(price + (atr * 5), 2) if atr > 0 else round(price * 1.06, 2)
        elif total_score < -2:
            final_signal = "STRONG SELL" if confidence >= 75 else "SELL"
            sl = round(price + (atr * 1.5), 2) if atr > 0 else round(price * 1.02, 2)
            tp1 = round(price - (atr * 1.5), 2) if atr > 0 else round(price * 0.98, 2)
            tp2 = round(price - (atr * 3), 2) if atr > 0 else round(price * 0.96, 2)
            tp3 = round(price - (atr * 5), 2) if atr > 0 else round(price * 0.94, 2)
        else:
            final_signal = "NEUTRAL - WAIT"
            sl = round(price * 0.99, 2)
            tp1 = round(price * 1.01, 2)
            tp2 = round(price * 1.02, 2)
            tp3 = round(price * 1.03, 2)

        support = all_indicators.get("support", 0)
        resistance = all_indicators.get("resistance", 0)

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
            'indicators': all_indicators,
            'support': support,
            'resistance': resistance,
            'headlines': headlines
        })

    return jsonify({'results': results})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)