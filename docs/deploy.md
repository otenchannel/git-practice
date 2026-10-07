# デプロイ手順(Fly.io)

Dockerfile と fly.toml は用意済みです。以下をあなたのPCで実行してください(月数百円〜。Fly.ioのアカウント登録とカード登録が必要)。

## 1. 準備
```sh
curl -L https://fly.io/install.sh | sh   # flyctl のインストール
fly auth login
```

## 2. アプリ作成とボリューム
```sh
fly launch --no-deploy --copy-config      # アプリ名を決める(fly.toml の app / PUBLIC_URL も同名に直す)
fly volumes create orders_data --region nrt --size 1   # SQLite用の永続ディスク
```
> ボリュームは1台のマシンにのみ紐づきます。SQLite運用なので **マシンは1台のまま** にしてください(`fly scale count 1`)。

## 3. シークレット設定
```sh
fly secrets set \
  STRIPE_SECRET_KEY=sk_test_... \
  STRIPE_WEBHOOK_SECRET=whsec_... \
  DOWNLOAD_SECRET=$(python3 -c "import secrets;print(secrets.token_hex(32))") \
  SMTP_HOST=smtp.example.com SMTP_USER=... SMTP_PASSWORD=... MAIL_FROM=shop@your-domain.com
```
`STRIPE_WEBHOOK_SECRET` は手順5で得られるので、先にダミーで設定し後で差し替えても構いません(未設定のままだと起動を拒否します)。

## 4. デプロイ
```sh
fly deploy
fly logs          # "listening on :8000" を確認
```
起動時に危険な設定(既定の秘密鍵、http の PUBLIC_URL など)があると `設定エラー: ...` で停止します。

## 5. Stripe の Webhook 登録
Stripe ダッシュボード → Developers → Webhooks → エンドポイント追加
- URL: `https://<アプリ名>.fly.dev/webhook/stripe`
- イベント: `checkout.session.completed`, `checkout.session.async_payment_succeeded`
- 表示された署名シークレット(`whsec_...`)を `fly secrets set STRIPE_WEBHOOK_SECRET=...` で設定

## 6. 本番前チェック
- [ ] **テストモード**(`sk_test_`)で、テストカード `4242 4242 4242 4242` で購入し、メールが届いてDLできる
- [ ] Webhook を意図的に失敗させ(SMTP誤設定など)、Stripe再送で復旧することを確認
- [ ] `store/static/legal.html` の【】を記入、`store/products/` に実際の商品ファイルを置く
- [ ] 送信元ドメインの SPF / DKIM 設定
- [ ] 本番キー(`sk_live_`)と本番Webhookに切り替え
- [ ] バックアップ: `fly volumes snapshots list`(自動で日次取得されます。復元手順も一度確認を)

## 運用メモ
- 商品追加: `store/products.json` と `store/products/` を更新して `fly deploy`
- 注文の確認: `fly ssh console -C "sqlite3 /data/orders.db 'select * from orders'"`(イメージに sqlite3 CLI は無いので、必要なら python3 -c で代用)
- 独自ドメイン: `fly certs add your-domain.com` 後、`PUBLIC_URL` を変更
- ローカルで本番相当を試す: `docker build -t store . && docker run -p 8000:8000 -v $PWD/data:/data store`
