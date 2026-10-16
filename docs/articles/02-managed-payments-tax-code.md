<!--
【公開メタ】(この囲みは、公開時に削除。媒体の入力欄に転記する)
タイトル(32〜40字目安で先頭に重要語):
  Stripe「product tax code is missing」400の原因と対処【Managed Payments】
別案:
  Stripe Checkout が 400 で作れない?税コード必須エラーの直し方(API・Python)
メタディスクリプション(120字以内):
  Stripe Checkout Session の作成で「product tax code is missing」(400)が出た原因は、アカウントで既定で有効な Managed Payments でした。実際のエラー文、2つの直し方、判断の基準を、Python のコードつきで解説します。
スラッグ: stripe-checkout-product-tax-code-is-missing-managed-payments
タグ案: Stripe, Checkout, Python, 決済, Webhook
想定検索語: product tax code is missing / Stripe Managed Payments / Stripe Checkout 400 / managed_payments[enabled] / Stripe 税コード
公開日・更新日: 【公開日を入れる】(更新したら更新日も記す)
アイキャッチ・画像の alt: 「Stripe Checkout のエラー(product tax code is missing)のログ」など、内容が分かる文
-->

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
> この記事は、AI アシスタントと一緒に作業した記録(実際のログと画面)をもとに、AI の助けを借りて書き、私が内容を確認しました。

## 30秒で分かる結論
1. **原因**: アカウントで Managed Payments が既定で有効になっていて、この機能では、**商品の税コードが必須**。
2. **直し方A**: その決済だけ、`managed_payments[enabled]=false` を送って、無効にする。(私が選んだ方法。決済は通った)
3. **直し方B**: 商品に、**対象の税コード**(`txcd_...`)を付ける方法もあるようです。公式の利用資格ページに、対象の一覧があります。(私は試していません)
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
この記事では、**確認できたことだけ**を書きます。
- Stripe のエラー文によると、Managed Payments には**商品の税コードが必要**で、私のアカウントでは**既定で有効**になっていました。
- Stripe 公式の「利用資格」ページに、**対象の税コードの一覧**があります。

Managed Payments の仕組みの詳しい説明(販売者の扱い、税金の扱いなど)は、この記事では扱いません。公式のドキュメントで確認してください。

公式の**「利用資格」ページ**には、**対象の税コードの一覧**がありました(確認済み)。たとえば、次のような行があります。

| 税コード | カテゴリ名 |
|---|---|
| `txcd_10000000` | General - Electronically Supplied Services |
| `txcd_10010001` | Infrastructure as a service (IaaS) - personal use |
| `txcd_10101000` | Infrastructure as a service (IaaS) - business use |

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
利用資格ページの一覧から、**自分の商品に合う税コード**を選んで、商品に付ける方法もあるようです。
**私は、この方法を試していないので、具体的なやり方や結果は書けません。** 税コードの指定方法(API のパラメータ名など)は、Stripe の公式ドキュメントで確認してください。

どの税コードが、自分の商品に当たるのかは、一覧の説明文を読んで、自分で判断する必要があります。迷う場合は、専門家に確認してください。

## どちらを選ぶか
私は、**自分が販売者として売る前提**で、販売ページと、特定商取引法の表記を作っています。そこで、直し方Aを選びました。

考え方の違いは、次のとおりです。
- **A(無効にする)**: Managed Payments を使わない形です。私は、この形で、自分が販売者として売る前提で作っています。
- **B(税コードを付ける)**: 私は試していないため、販売者や税金の扱いが、どう変わるのかは書けません。公式のドキュメントや、専門家に確認してください。

どちらが自分に合うかは、事業の状況によって変わります。**税金や法律の扱いは、税理士や税務署などの専門家に確認してください。** この記事は、そうした助言を含みません。

## よくある質問
**Q. サンドボックス(テスト環境)でも、このエラーは出ますか?**
私は、サンドボックスで出ました。

**Q. 税コードを付けないと、必ず失敗しますか?**
私の環境では、失敗しました。無効にすると、決済ページを作れました。税コードを付ける方法は、試していません。

**Q. `managed_payments[enabled]=false` を送ると、何か危険ですか?**
その決済で、Managed Payments を使わない、という指定です。販売者や税金の扱いに、どう影響するかは、私は確認していません。公式のドキュメントや、専門家に確認してください。

## 再発防止
- API のエラーは、**返事の本文まで、ログに出す**。エラー文に、原因と直し方が書いてあることがあります。
- アカウントの設定(今回は、Managed Payments が既定で有効)は、**画面を見るだけでは気づきにくい**。API が返す理由を、手がかりにします。

## 参考
- Stripe 公式の「利用資格」ページ(エラー文の中にもリンクがあります): `https://docs.stripe.com/payments/managed-payments/eligibility`

## このシリーズについて
デジタル商品の販売システム(決済 → メール → ダウンロード)を、自前で作ったときの、つまずきを書いています。
- 【#1 公開後にリンク】Stripe の API キーが入らない(401)
- 【#3 公開後にリンク】決済は通ったのに、メールが来ない
- 【#4 公開後にリンク】Gmail の SMTP 設定でハマった

手順書とスターターキットを、準備中です。「読みたい」「ここが知りたい」という声を、コメントや X で、教えてもらえると助かります。

---
## 告知文の案(X 用。公開後に、記事の URL を入れる)
**案1(問題提起)**
> Stripe の Checkout Session を API で作ったら 400。「product tax code is missing」。
> 原因は、アカウントで既定で有効だった Managed Payments でした。エラー文に、直し方まで書いてあった。
> 実際のログと、2つの直し方をまとめました → 【URL】 #Stripe #Python

**案2(学び)**
> API のエラーは、「返事の本文」までログに出すと、原因が書いてあることがある。
> 今回は Stripe の 400 で、そこに直し方まで載っていた。ハマった記録 → 【URL】 #Stripe

**案3(質問)**
> Stripe の Managed Payments、API 利用者は気づきにくい。税コード必須エラーで止まった人はいますか?
> 原因と対処を書きました → 【URL】

## 公開前の確認(この行から下は、公開時に削除する)
- [x] 確認できていないこと(Managed Payments の仕組み、直し方B の詳細)は、書かない・「試していない」と明記する方針に変更済み
- [ ] エラー文の引用は、実際のログと合っている(省略した旨を書いている)
- [ ] 注文番号・キー・メールアドレスなどが、本文にもスクリーンショットにも、入っていない
- [ ] 画像に alt テキストを付けた
- [ ] 収入や売上を連想させる表現がない
- [ ] タイトル・見出しが、内容と合っている(誇張していない)
- [ ] 公開メタ(タイトル、説明、スラッグ、タグ、日付)を媒体に入力した
