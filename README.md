# git-practice

デジタル商品販売の自動化(不労所得の仕組み)のプロトタイプです。計画は [docs/plan.md](docs/plan.md) を参照。

## 試す
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
