<!-- note に貼る本文。先頭のこの行は、貼る前に削除する。【確認】の行は、公開前に直す -->

# Stripe「product tax code is missing」400の原因と対処【Managed Payments】

Stripe の Checkout Session を API で作ったら、いきなり **400 エラー**。

```
Invalid line_items[0]: the product tax code is missing.
```

商品名も価格も、ちゃんと送っています。税金の設定なんて、していません。なのに、なぜ?

原因は、コードではありませんでした。**アカウントで、既定で有効になっていた「Managed Payments」** です。そして、エラー文を最後まで読むと、**直し方まで書いてありました。**

この記事では、実際に出たエラー文、2つの直し方、どちらを選ぶかの考え方を、Python のコードつきで書きます。

**こんな人に向けた記事です**
- Stripe Checkout Session を、API(Python など)で作っていて、400 になった
- 「product tax code is missing」「Managed Payments」の意味が分からない
- サンドボックスで試しているのに、税コードを求められて戸惑っている

> 執筆時点: 2026年10月。Stripe の仕様や画面は変わることがあります。最新は、公式ドキュメントで確認してください。

## 30秒で分かる結論
1. **原因**: アカウントで Managed Payments が既定で有効になっていて、この機能では、**商品の税コードが必須**。
2. **直し方A**: その決済だけ、`managed_payments[enabled]=false` を送って、無効にする。(私が選んだ方法。決済は通った)
3. **直し方B**: 商品に、**対象の税コード**(`txcd_...`)を付ける。公式の利用資格ページに、対象の一覧がある。
4. どちらを選ぶかで、**販売者の扱いや税金の扱いが変わる**可能性がある。選ぶ前に、「どちらを選ぶか」の項を読む。

## 実際に出たエラー文
サーバーのログに、Stripe の返事の本文を出してみると、こう書いてありました(長いので、途中までです)。

```
Stripe 400: {
  "error": {
    "message": "Invalid line_items[0]: the product tax code is missing.
      Set the product's tax_code field to an eligible product tax code (more details: ...).
      Product tax code is required for Managed Payments, which is enabled by default on your account.
      If you want to disable Managed Payments on this session, you can pass managed_payments[enabled]=false.
      You can configure whether Managed Paymen...
```

読み取れることは、次の4つです。
1. 商品の**税コードが、ありません**。
2. **Managed Payments には、税コードが必要**です。
3. Managed Payments は、**このアカウントで、既定で有効**です。
4. この決済だけ無効にするなら、**`managed_payments[enabled]=false`** を渡せます。

## 原因の見分け方
- 私のコードは、商品名と価格だけを送っていて、税コードは送っていませんでした。
- 税コードを使う設定は、していません。それなのに「Managed Payments が既定で有効」と言われたので、**アカウント側の設定**が原因だと分かりました。
- ここで効いたのは、**Stripe の返事の本文を、ログに出していた**ことです。最初は `HTTP Error 400` としか出ず、理由が分かりませんでした。

```python
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["url"]
except urllib.error.HTTPError as e:
    # Stripe のエラー本文(理由)をログに残す。API キーは含まれない
    raise RuntimeError(f"Stripe {e.code}: {e.read()[:500].decode('utf-8', 'replace')}") from None
```

## Managed Payments とは
【確認】定義の部分は、公式の概要ページで確認して書き直してください。以下は、第三者の解説で読んだ内容です。
- Managed Payments が有効な決済では、Stripe が **merchant of record(販売者として、取引の当事者になる立場)** になり、売上税・VAT・GST などの徴収と納付を代行する、とされています。
- 対象になるかどうかは、**商品の税コード**で決まる、とされています。

公式の**「利用資格」ページ**には、**対象の税コードの一覧**がありました(確認済み)。たとえば、次のような行があります。

- `txcd_10000000` … General - Electronically Supplied Services
- `txcd_10010001` … Infrastructure as a service (IaaS) - personal use
- `txcd_10101000` … Infrastructure as a service (IaaS) - business use

`txcd_10000000` の説明には、「インターネット経由で、人の手をほとんど介さずに提供されるデジタルサービス」とありました。さらに、「**ソフトウェア、デジタル商品、クラウドサービス、ウェブサイトサービスのような、より具体的なカテゴリを検討してください**」という趣旨の案内もありました。

## 直し方
### 直し方A: この決済では、Managed Payments を無効にする(私が選んだ方法)
Checkout Session を作るときに、`managed_payments[enabled]=false` を送ります。

```python
form = {
    "mode": "payment",
    "success_url": "https://example.com/thanks",
    "cancel_url": "https://example.com/",
    # 自分が販売者として売る前提。Managed Payments は無効にする
    "managed_payments[enabled]": "false",
    "line_items[0][quantity]": "1",
    "line_items[0][price_data][currency]": "jpy",
    "line_items[0][price_data][unit_amount]": "1980",
    "line_items[0][price_data][product_data][name]": "Starter Guide",
}
```

これで、決済画面に進めて、テストカードで支払いが通りました(サンドボックス環境、日本円)。

### 直し方B: 商品に、対象の税コードを付ける
利用資格ページの一覧から、**自分の商品に合う税コード**を選んで、商品に付けます。
【確認】API では、`line_items[0][price_data][product_data][tax_code]` に指定する形のはずですが、**私は試していません**。公式の API リファレンスで、パラメータ名と指定方法を確認してください。確認して試した場合は、ここにコードと結果を足します。

どの税コードが、自分の商品に当たるのかは、一覧の説明文を読んで、自分で判断する必要があります。迷う場合は、専門家に確認してください。

## どちらを選ぶか
私は、**自分が販売者として売る前提**で、販売ページと、特定商取引法の表記を作っています。そこで、直し方Aを選びました。

考え方の違いは、次のとおりです。
- **A(無効にする)**: 自分が、販売者のままです。消費税などの扱いは、自分で行います。
- **B(税コードを付ける)**: 【確認】Stripe が販売者になり、税金の扱いを代行する形のはずです。その場合は、特商法の表記など、他の部分にも影響するかもしれません。

どちらが自分に合うかは、事業の状況によって変わります。**税金や法律の扱いは、税理士や税務署などの専門家に確認してください。** この記事は、そうした助言を含みません。

## よくある質問
**Q. サンドボックス(テスト環境)でも、このエラーは出ますか?**
私は、サンドボックスで出ました。

**Q. 税コードを付けないと、必ず失敗しますか?**
Managed Payments が有効なアカウントで、その決済でも有効なままなら、私の環境では失敗しました。無効にするか、税コードを付けると、決済ページを作れます。

**Q. `managed_payments[enabled]=false` を送ると、何か危険ですか?**
その決済で、Managed Payments を使わなくなるだけです。ただし、販売者や税金の扱いに関わる可能性があるので、専門家への確認をおすすめします。

**Q. アカウント全体で、Managed Payments をオフにできますか?**
エラー文には、「設定で、有効にするかを切り替えられる」という趣旨の文がありましたが、途中で切れていて、読めていません。【確認】Stripe の設定画面か、公式ドキュメントで確認してください。

## 再発防止
- API のエラーは、**返事の本文まで、ログに出す**。エラー文に、原因と直し方が書いてあることがあります。
- アカウントの設定(今回は、Managed Payments が既定で有効)は、**画面を見るだけでは気づきにくい**。API が返す理由を、手がかりにします。

## 参考
- Stripe 公式の「利用資格」ページ(エラー文の中にもリンクがあります): `https://docs.stripe.com/payments/managed-payments/eligibility`
- 第三者の解説(Stripe の公式ではありません):
  - [Managed Payments(Superwall)](https://superwall.com/docs/web-checkout/web-checkout-managed-payments)
  - [stripe managed payments(RevenueCat)](https://www.revenuecat.com/docs/web/integrations/stripe/stripe-managed-payments.md)

## このシリーズについて
デジタル商品の販売システム(決済 → メール → ダウンロード)を、自前で作ったときの、つまずきを書いています。
- 【#1 公開後に、記事のリンクを入れる】Stripe の API キーが入らない(401)
- 【#3 公開後にリンク】決済は通ったのに、メールが来ない
- 【#4 公開後にリンク】Gmail の SMTP 設定でハマった

手順書とスターターキットを、準備中です。「読みたい」「ここが知りたい」という声を、コメントや X で、教えてもらえると助かります。
