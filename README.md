# MarketPulse

毎朝自動更新される相場まとめサイト。

## ファイル構成

```
marketpulse/
├── .github/workflows/daily_update.yml  ← GitHub Actions (毎朝6時JST)
├── scripts/update_data.py              ← データ取得 & AI要約スクリプト
├── public/
│   ├── index.html                      ← フロントページ
│   └── data.json                       ← 自動生成データ (gitignore不要)
└── README.md
```

## セットアップ手順

### 1. GitHubリポジトリを作成

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_NAME/marketpulse.git
git push -u origin main
```

### 2. GitHub Secrets を設定

リポジトリの Settings → Secrets and variables → Actions で追加:

| Name | 値 | 取得先 |
|------|-----|--------|
| `ANTHROPIC_API_KEY` | sk-ant-... | https://console.anthropic.com |
| `NEWS_API_KEY` | xxxxxxxx | https://newsapi.org (無料) |

### 3. GitHub Pages を有効化

Settings → Pages → Source: `Deploy from branch` → Branch: `main` / `public`

これで `https://YOUR_NAME.github.io/marketpulse/` でアクセス可能。

### 4. 手動で初回データ生成

ローカルで実行:
```bash
pip install yfinance requests anthropic
export ANTHROPIC_API_KEY=sk-ant-...
export NEWS_API_KEY=xxxxxxxx
python scripts/update_data.py
```
または GitHub Actions の "Run workflow" ボタンで実行。

## 動作フロー

```
毎朝 06:00 JST
  ↓ GitHub Actions 起動
  ↓ update_data.py 実行
      ├─ yfinance     → SP500 / NASDAQ / GOLD / USDJPY / VIX
      ├─ CoinGecko    → BTC 価格
      ├─ NewsAPI      → 最新ニュース8件
      └─ Claude API   → 日本語相場まとめ生成
  ↓ public/data.json 更新
  ↓ git push
  ↓ GitHub Pages 自動反映
```

## コスト目安

| サービス | コスト |
|---------|--------|
| GitHub Actions | 無料 (月2000分) |
| yfinance / CoinGecko | 無料 |
| NewsAPI | 無料 (月100リクエスト) |
| Claude API (Haiku) | 約0.3〜1円/日 |
| **合計** | **ほぼ無料** |
