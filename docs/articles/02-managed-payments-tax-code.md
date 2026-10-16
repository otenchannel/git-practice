# Stripe Checkout で「product tax code is missing」(400)が出たときの原因と直し方

> 下書き。`【確認】` の箇所は、公開前に Stripe の公式ドキュメントで確認して、書き直す。
> 執筆時点: 2026年10月。Stripe の仕様や画面は変わることがあります。

## 先に結論
- Checkout Session を API で作ったら、`Invalid line_items[0]: the product tax code is missing` という 400 エラーが返ってきた。
- エラー文によると、原因は、アカウントで **Managed Payments が既定で有効**になっていて、この機能では**商品の税コードが必須**だったこと。
- 直し方は2つある。
  1. その決済で、`managed_payments[enabled]=false` を送って、Managed Payments を無効にする(今回、私が選んだ方法。決済は通った)
  2. 商品に、税コード(`tax_code`)を付ける 【確認】(私は試していない)
- どちらを選ぶかで、**税金や販売者の扱いが変わる**可能性がある。選ぶ前に、「どちらにするか」の項を読むこと。

## 症状
Python から、Stripe の API で、Checkout Session を作ろうとしました。
ところが、400 エラーになりました。サーバーのログに、Stripe の返事の本文を出してみると、こう書いてありました(長いので、途中までです)。

```
Stripe 400: {
  "error": {
    "message": "Invalid line_items[0]: the product tax code is missing.
      Set the product's tax_code field to an eligible product tax code (more details: ...).
      Product tax code is required for Managed Payments, which is enabled by default on your account.
      If you want to disable Managed Payments on this session, you can pass managed_payments[enabled]=false.
      You can configure whether Managed Paymen...
```

エラー文には、原因と、直し方までが、書いてありました。要点は次の3つです。
1. 商品の税コードが、ありません。
2. Managed Payments には、税コードが必要です。
3. Managed Payments は、**このアカウントで、既定で有効**になっています。
4. この決済だけ無効にするなら、`managed_payments[enabled]=false` を渡せます。

## 原因の見分け方
- 私のコードは、商品名と価格だけを送っていて、税コードは送っていませんでした。
- 税コードを送る設定は、していません。それなのに「Managed Payments が既定で有効」と言われたので、**アカウント側の設定**が原因だと分かりました。
- ここで大事だったのは、**Stripe の返事の本文を、ログに出していた**ことです。最初は `HTTP Error 400` としか出ず、理由が分かりませんでした。

```python
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["url"]
except urllib.error.HTTPError as e:
    # Stripe のエラー本文(理由)をログに残す。API キーは含まれない
    raise RuntimeError(f"Stripe {e.code}: {e.read()[:500].decode('utf-8', 'replace')}") from None
```

## Managed Payments とは
【確認】以下は、第三者の解説で読んだ内容で、Stripe の公式ドキュメントでは確認できていません。公開前に、公式で確認して書き直してください。
- Managed Payments が有効な決済では、Stripe が **merchant of record(販売者として取引の当事者になる立場)**になり、売上税・VAT・GST などの徴収と納付を代行する、とされています。
- 対象になるかどうかは、**商品の税コード**で決まる、とされています。税コードが対象外(または未設定)の商品は、通常の決済になる、という説明もありました。

エラー文にある、公式の説明ページ(`docs.stripe.com/payments/managed-payments/eligibility`)に、条件が書いてあるはずです。

## 直し方
### 方法1: この決済では、Managed Payments を無効にする(私が選んだ方法)
Checkout Session を作るときに、`managed_payments[enabled]=false` を送ります。

```python
form = {
    "mode": "payment",
    "success_url": "https://example.com/thanks",
    "cancel_url": "https://example.com/",
    # 自分が販売者として販売する前提。Managed Payments は無効にする
    "managed_payments[enabled]": "false",
    "line_items[0][quantity]": "1",
    "line_items[0][price_data][currency]": "jpy",
    "line_items[0][price_data][unit_amount]": "1980",
    "line_items[0][price_data][product_data][name]": "Starter Guide",
}
```

これで、決済画面に進めて、テストカードで支払いが通りました(サンドボックス環境)。

### 方法2: 商品に税コードを付ける
【確認】`line_items[0][price_data][product_data][tax_code]` に、Stripe が定める税コード(`txcd_` で始まる文字列)を指定する方法があるはずです。ただし、私は試していません。どの税コードが、デジタル商品に当たるのか、対象の条件は何かを、公式ドキュメントで確認してください。

## どちらにするか
私は、**自分が販売者として売る前提**で、販売ページと、特定商取引法の表記を作っています。そこで、方法1を選びました。
考え方の違いは、次のとおりです。
- **方法1(無効にする)**: 自分が販売者のままです。消費税などの扱いは、自分で行います。
- **方法2(税コードを付ける)**: 【確認】Stripe が販売者になり、税金の扱いを代行するのかもしれません。その場合は、特商法の表記など、他の部分にも影響します。

どちらが自分に合うかは、事業の状況によって変わります。**税金や法律の扱いは、税理士や税務署などの専門家に確認してください。** この記事は、そうした助言を含みません。

## 再発防止
- API のエラーは、**返事の本文まで、ログに出す**。エラー文に、原因と直し方が書いてあることがあります。
- アカウントの設定(今回は、Managed Payments が既定で有効)は、**画面を見るだけでは気づきにくい**。API が返す理由を、手がかりにします。

## 参考
- Stripe のエラー文の中にあった、公式の説明ページ: `https://docs.stripe.com/payments/managed-payments/eligibility`(【確認】私は開けていません。公開前に、自分で開いて確認する)
- 第三者の解説(Stripe の公式ではありません):
  - [Managed Payments(Superwall)](https://superwall.com/docs/web-checkout/web-checkout-managed-payments)
  - [stripe managed payments(RevenueCat)](https://www.revenuecat.com/docs/web/integrations/stripe/stripe-managed-payments.md)

---

*このシリーズでは、デジタル商品の販売システムを自前で作ったときの、つまずきを書いています。手順書とスターターキットを、準備中です。*

---
## 公開前の確認(この行から下は、公開時に削除する)
- [ ] 「Managed Payments とは」を、Stripe の公式ドキュメントの内容に直し、【確認】を消した
- [ ] 方法2を、実際に試すか、「試していない」と明記したまま残すか決めた
- [ ] エラー文の引用は、実際のログと合っている(長い文は、途中で省略した旨を書く)
- [ ] 注文番号・キー・メールアドレスなどが、本文にもスクリーンショットにも、入っていない
- [ ] 収入や売上を連想させる表現がない
- [ ] 税金・法律の助言をしていない旨が、書いてある
