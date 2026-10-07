# git-practice

デジタル商品販売の自動化(不労所得の仕組み)のプロトタイプです。計画は [docs/plan.md](docs/plan.md) を参照。

## 試す
サーバー起動後 http://localhost:8000/ が販売ページです(`store/static/index.html`)。商品は `store/products.json` から自動表示されます。

```sh
python3 -m unittest discover -s tests   # テスト
python3 store/app.py                    # サーバ起動 (:8000)
```
```sh
curl localhost:8000/products
curl -XPOST localhost:8000/orders -d '{"product_id":"starter-guide","email":"a@example.com"}'
# 決済完了Webhook(署名は HMAC-SHA256(body, WEBHOOK_SECRET))
```
商品は `store/products.json` と `store/products/` に追加します。

## Stripe 連携
環境変数を設定すると、`POST /orders` が Stripe Checkout の決済URL(`checkout_url`)を返します。

| 変数 | 内容 |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_test_...`(まずテストモードで) |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...`(Webhookエンドポイント作成時に表示) |
| `PUBLIC_URL` | 公開URL(例: `https://example.com`)。DLリンクと決済後の戻り先に使用 |

1. Stripe ダッシュボード → Developers → Webhooks で `PUBLIC_URL/webhook/stripe` を登録し、
   `checkout.session.completed` と `checkout.session.async_payment_succeeded` を選択
2. ローカル確認: `stripe listen --forward-to localhost:8000/webhook/stripe`(表示される `whsec_` を設定)
3. テストカード `4242 4242 4242 4242` で決済し、`outbox` にDL URLが積まれることを確認

Webhook は署名と時刻(5分以内)を検証し、支払済み・金額一致の場合のみ納品します。
`/webhook/payment` はStripeなしの開発用モックです。

## メール送信(SMTP)
決済完了後、購入者にダウンロードURLをメールで送ります。`SMTP_HOST` を設定すると有効になります(未設定なら送信せず `outbox` に積むだけの開発モード)。

| 変数 | 内容 |
|---|---|
| `SMTP_HOST` / `SMTP_PORT` | 例: `smtp.gmail.com` / `587`(465はSSL、それ以外はSTARTTLS) |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP認証情報(Gmailは「アプリパスワード」) |
| `MAIL_FROM` | 送信元アドレス(未設定なら `SMTP_USER`) |

- 送信に失敗すると Webhook が 400 を返し、Stripe が自動で再送 → 再試行します。`emailed` フラグで二重送信を防ぎます。
- 本番では独自ドメインの送信元に SPF / DKIM を設定してください(迷惑メール対策)。

## 販売ページ
- `/` 商品一覧と購入フォーム(メールアドレス入力 → Stripe Checkout へ遷移)、`/legal` 特定商取引法に基づく表記
- **公開前に `store/static/legal.html` の【】を実際の事業者情報に書き換えてください**(日本で販売する場合は表記が必須です)
- Stripe未設定の開発モードでは「決済が未設定です」と表示されます

## デプロイ
Fly.io([docs/deploy.md](docs/deploy.md)、要PC)と Render([docs/deploy-render.md](docs/deploy-render.md)、スマホのブラウザだけで可)の設定を用意しています。
本番では `STRIPE_SECRET_KEY` を設定すると起動時に設定を検査し、危険な設定は拒否します。開発用モック決済(`/webhook/payment`)は `ENABLE_MOCK_PAYMENT=1` のときだけ有効です。
