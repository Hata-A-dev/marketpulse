"""
MarketPulse - データ自動更新スクリプト
毎朝GitHub Actionsから実行される
必要: pip install yfinance requests anthropic
"""

import json
import os
import sys
from datetime import datetime, timedelta
import yfinance as yf
import requests
import anthropic

# ── 設定 ──────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
NEWS_API_KEY      = os.environ.get("NEWS_API_KEY")  # https://newsapi.org 無料枠あり

TICKERS = {
    "sp500":  "^GSPC",
    "nasdaq": "^IXIC",
    "gold":   "GC=F",
    "usdjpy": "JPY=X",
    "vix":    "^VIX",
    "usbond": "^TNX",
}

BTC_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
OUTPUT  = "public/data.json"

# ── 価格取得 ──────────────────────────────────────
def fetch_prices():
    prices = {}
    for key, symbol in TICKERS.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if len(hist) < 2:
                continue
            curr  = round(float(hist["Close"].iloc[-1]), 2)
            prev  = round(float(hist["Close"].iloc[-2]), 2)
            chg   = round((curr - prev) / prev * 100, 2)
            prices[key] = {"price": curr, "change_pct": chg, "prev": prev}
        except Exception as e:
            print(f"[WARN] {key}: {e}")
    return prices

def fetch_btc():
    try:
        r = requests.get(BTC_API, timeout=10)
        d = r.json()["bitcoin"]
        price = round(d["usd"], 0)
        chg   = round(d["usd_24h_change"], 2)
        return {"price": price, "change_pct": chg}
    except Exception as e:
        print(f"[WARN] BTC: {e}")
        return {}

# ── 30日の履歴データ（チャート用）──────────────────
def fetch_history(symbol, days=30):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period=f"{days+5}d")
        closes = hist["Close"].tail(days)
        dates  = [d.strftime("%-m/%-d") for d in closes.index]
        values = [round(float(v), 2) for v in closes.values]
        return {"dates": dates, "values": values}
    except:
        return {}

# ── ニュース取得 ──────────────────────────────────
def fetch_news():
    if not NEWS_API_KEY:
        print("[WARN] NEWS_API_KEY が未設定 — ダミーニュースを使用")
        return [
            {"title": "FRB議長、インフレ目標達成には時間が必要と発言", "tag": "マクロ", "ago": "2時間前"},
            {"title": "ビットコインETF、週次で流入超過を維持", "tag": "BTC", "ago": "4時間前"},
            {"title": "金価格、地政学リスクを背景に高止まり", "tag": "GOLD", "ago": "6時間前"},
            {"title": "S&P500、決算シーズン開幕で強含み", "tag": "SP500", "ago": "8時間前"},
        ]
    
    queries = [
        ("S&P 500 stock market", "SP500"),
        ("Bitcoin cryptocurrency", "BTC"),
        ("gold price economy", "GOLD"),
        ("Federal Reserve interest rate", "マクロ"),
    ]
    news = []
    seen = set()
    for q, tag in queries:
        try:
            url = (
                f"https://newsapi.org/v2/everything"
                f"?q={requests.utils.quote(q)}&language=en"
                f"&sortBy=publishedAt&pageSize=2"
                f"&apiKey={NEWS_API_KEY}"
            )
            r = requests.get(url, timeout=10)
            for art in r.json().get("articles", []):
                title = art.get("title","")
                if title and title not in seen:
                    seen.add(title)
                    pub = art.get("publishedAt","")
                    try:
                        dt  = datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ")
                        ago = _time_ago(dt)
                    except:
                        ago = "本日"
                    news.append({"title": title, "tag": tag, "ago": ago, "url": art.get("url","")})
        except Exception as e:
            print(f"[WARN] news {q}: {e}")
    return news[:8]

def _time_ago(dt):
    diff = datetime.utcnow() - dt
    h = int(diff.total_seconds() / 3600)
    if h < 1:   return "1時間以内"
    if h < 24:  return f"{h}時間前"
    return f"{diff.days}日前"

# ── AI 相場まとめ ─────────────────────────────────
def generate_summary(prices, btc):
    if not ANTHROPIC_API_KEY:
        return "（ANTHROPIC_API_KEY未設定 — AI要約はスキップされました）"
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    sp  = prices.get("sp500",  {})
    nas = prices.get("nasdaq", {})
    gld = prices.get("gold",   {})
    jpy = prices.get("usdjpy", {})
    vix = prices.get("vix",    {})

    prompt = f"""以下の市場データをもとに、日本語で80〜120字の相場まとめを書いてください。
箇条書き不可。自然な一段落で。専門用語は使ってOKだが読みやすく。

S&P500: {sp.get('price','N/A')} ({sp.get('change_pct','N/A')}%)
NASDAQ: {nas.get('price','N/A')} ({nas.get('change_pct','N/A')}%)
BTC: {btc.get('price','N/A')} ({btc.get('change_pct','N/A')}%)
GOLD: {gld.get('price','N/A')} ({gld.get('change_pct','N/A')}%)
USD/JPY: {jpy.get('price','N/A')} ({jpy.get('change_pct','N/A')}%)
VIX: {vix.get('price','N/A')}

まとめのみ出力し、前置きは不要。"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",  # 安いモデルで十分
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()

# ── メイン ────────────────────────────────────────
def main():
    print("📊 価格データ取得中...")
    prices = fetch_prices()
    btc    = fetch_btc()
    prices["btc"] = btc

    print("📰 ニュース取得中...")
    news = fetch_news()

    print("🤖 AI要約生成中...")
    summary = generate_summary(prices, btc)

    print("📈 チャート履歴取得中...")
    history = {
        "sp500":  fetch_history("^GSPC"),
        "btc":    {},  # CoinGecko有料のためスキップ（必要なら追加）
        "gold":   fetch_history("GC=F"),
        "usdjpy": fetch_history("JPY=X"),
        "nasdaq": fetch_history("^IXIC"),
    }

    output = {
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "prices": prices,
        "news": news,
        "summary": summary,
        "history": history,
    }

    os.makedirs("public", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 完了 → {OUTPUT}")
    print(f"   要約: {summary[:60]}...")

if __name__ == "__main__":
    main()
