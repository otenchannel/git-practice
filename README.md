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
