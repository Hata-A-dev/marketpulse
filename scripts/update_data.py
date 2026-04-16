import json
import os
from datetime import datetime
import yfinance as yf
import requests

NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

TICKERS = {
    "sp500":  "^GSPC",
    "nasdaq": "^IXIC",
    "gold":   "GC=F",
    "usdjpy": "JPY=X",
    "vix":    "^VIX",
    "usbond": "^TNX",
}

BTC_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
OUTPUT  = "docs/data.json"

def fetch_prices():
    prices = {}
    for key, symbol in TICKERS.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if len(hist) < 2:
                continue
            curr = round(float(hist["Close"].iloc[-1]), 2)
            prev = round(float(hist["Close"].iloc[-2]), 2)
            chg  = round((curr - prev) / prev * 100, 2)
            prices[key] = {"price": curr, "change_pct": chg}
        except Exception as e:
            print(f"[WARN] {key}: {e}")
    return prices

def fetch_btc():
    try:
        t = yf.Ticker("BTC-USD")
        hist = t.history(period="2d")
        if len(hist) < 2:
            return {}
        curr = round(float(hist["Close"].iloc[-1]), 0)
        prev = round(float(hist["Close"].iloc[-2]), 0)
        chg  = round((curr - prev) / prev * 100, 2)
        return {"price": curr, "change_pct": chg}
    except Exception as e:
        print(f"[WARN] BTC: {e}")
        return {}

def fetch_history(symbol, days=30):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period=f"{days+5}d")
        closes = hist["Close"].tail(days)
        return {
            "dates":  [d.strftime("%-m/%-d") for d in closes.index],
            "values": [round(float(v), 2) for v in closes.values]
        }
    except:
        return {}

def fetch_news():
    if not NEWS_API_KEY:
        return [
            {"title": "FRB、インフレ目標達成には時間が必要と発言", "tag": "経済", "ago": "2時間前"},
            {"title": "ビットコインETF、週次で流入超過を維持", "tag": "BTC", "ago": "4時間前"},
            {"title": "金価格、地政学リスクを背景に高止まり", "tag": "金", "ago": "6時間前"},
            {"title": "S&P500、決算シーズン開幕で強含み", "tag": "株式", "ago": "8時間前"},
        ]
    queries = [
        ("S&P 500 stock market", "株式"),
        ("Bitcoin cryptocurrency", "BTC"),
        ("gold price economy", "金"),
        ("Federal Reserve interest rate", "経済"),
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
                title = art.get("title", "")
                if title and title not in seen:
                    seen.add(title)
                    pub = art.get("publishedAt", "")
                    try:
                        dt  = datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ")
                        diff = datetime.utcnow() - dt
                        h = int(diff.total_seconds() / 3600)
                        ago = f"{h}時間前" if h < 24 else f"{diff.days}日前"
                    except:
                        ago = "本日"
                    news.append({"title": title, "tag": tag, "ago": ago, "url": art.get("url", "")})
        except Exception as e:
            print(f"[WARN] news {q}: {e}")
    return news[:8]

def main():
    print("価格データ取得中...")
    prices = fetch_prices()
    prices["btc"] = fetch_btc()

    print("ニュース取得中...")
    news = fetch_news()

    print("チャート履歴取得中...")
    history = {
        "sp500":  fetch_history("^GSPC"),
        "gold":   fetch_history("GC=F"),
        "usdjpy": fetch_history("JPY=X"),
        "nasdaq": fetch_history("^IXIC"),
    }

    output = {
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "prices": prices,
        "news": news,
        "summary": "毎朝自動更新中。価格データはyfinance・CoinGeckoより取得。",
        "history": history,
    }

    os.makedirs("docs", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"完了 → {OUTPUT}")

if __name__ == "__main__":
    main()
