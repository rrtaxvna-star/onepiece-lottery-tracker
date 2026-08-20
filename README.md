# ワンピースカード BOX抽選トラッカー

nyuka-now.com の抽選まとめ記事を定期スクレイピングし、Claude APIで構造化抽出、
首都圏(東京・神奈川・埼玉・千葉)の店頭受取またはオンライン配送の案件のみを
Discordに通知し、GitHub Pages上に一覧表示する。X(Twitter) APIは不使用。

## 構成
- `src/scraper.py` — nyuka-now.com のカテゴリページからONE PIECE関連記事を発見し、本文取得
- `src/extractor.py` — Claude API (Haiku)で本文を構造化JSON抽出
- `src/filters.py` — 1都3県/オンラインのスコープ判定
- `src/db.py` — SQLite永続化(`db.sqlite3`をリポジトリにコミットして状態保持)
- `src/notifier.py` — Discord Webhook通知(将来Slack/LINEに差し替え可能)
- `src/render.py` / `templates/index.html.j2` — 静的一覧ページ生成(GitHub Pages用)
- `.github/workflows/poll.yml` — 1時間おきの定期実行 + 結果コミット

## セットアップ
1. このディレクトリをGitHubリポジトリにpush(publicリポジトリ推奨: Actions無料枠が無制限)
2. リポジトリの Settings > Secrets and variables > Actions で以下を登録
   - `ANTHROPIC_API_KEY`
   - `DISCORD_WEBHOOK_URL`(Discordのチャンネル設定 > 連携サービス > Webhookで発行)
3. Settings > Pages で Source を「Deploy from a branch」、Branch を `main` / `docs` に設定
4. Actions タブから `Poll lottery listings` を手動実行(`workflow_dispatch`)して動作確認

## ローカル実行
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...  # 未設定なら通知はコンソール出力のみ
python src/main.py
```

## コストの目安
- X API: 不使用のため $0
- ホスティング: GitHub Actions(publicリポジトリは無料枠無制限) + GitHub Pages = $0
- Claude API(Haiku): 記事数本 × 月数十回の抽出のみなので月数円程度

## 既知の制約・注意点
- データソースはnyuka-now.com 1サイトのみ。同サイトのHTML構造が変わるとスクレイパーの
  セレクタ調整が必要になる可能性がある(`src/scraper.py`の`discover_article_urls`/
  `fetch_article_text`)。
- 店舗の都道府県は店舗名からのAI推定であり、100%正確ではない。誤判定に気づいたら
  `src/extractor.py`のプロンプトを調整する。
- nyuka-now.comの掲載範囲外の店舗(同サイトに載らない抽選)は検知できない。カバー範囲を
  広げたい場合はipo-x.net等、他の許諾されたソースの追加を検討(`src/scraper.py`に
  ソースを追加する形で拡張可能)。
