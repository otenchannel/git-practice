# デプロイ手順(Render・スマホのブラウザだけで可能)

`render.yaml` を用意済みです。**料金に注意**: 永続ディスク付きは有料プラン(Starter)です。申込前に https://render.com/pricing で現在の料金を確認してください。

## 1. 準備
1. https://render.com でアカウント作成(GitHub でログイン)し、支払い方法を登録
2. GitHub 連携で、このリポジトリ(`otenchannel/git-practice`)へのアクセスを許可
3. ブランチ: `claude/passive-income-system-72hwuk`(必要なら先に main へマージ)

## 2. Blueprint でデプロイ
1. Dashboard → **New → Blueprint** → リポジトリとブランチを選ぶ
2. 入力欄が出るので、次を入力(わからない項目は後からでも変更可):

| 項目 | 値 |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_test_...`(まずテストモード) |
| `STRIPE_WEBHOOK_SECRET` | 仮に `whsec_dummy`。手順3で本物に差し替え |
| `PUBLIC_URL` | 仮に `https://digital-store.onrender.com`(実際のURLに合わせる) |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` / `MAIL_FROM` | メール送信の設定(Gmailならアプリパスワード) |

3. **Apply** で作成開始。ログに `listening on :10000` が出れば起動成功
   (`設定エラー: ...` が出たら、その項目を Environment 画面で直して再デプロイ)
4. 発行された URL(`https://〜.onrender.com`)が `PUBLIC_URL` と違えば、Environment で修正

## 3. Stripe の Webhook 登録
Stripe ダッシュボード → Developers → Webhooks → エンドポイント追加
- URL: `<PUBLIC_URL>/webhook/stripe`
- イベント: `checkout.session.completed`, `checkout.session.async_payment_succeeded`
- 表示された `whsec_...` を Render の Environment `STRIPE_WEBHOOK_SECRET` に設定(自動で再デプロイ)

## 4. 動作確認(テストモード)
スマホで販売ページを開き、テストカード `4242 4242 4242 4242`(期限は未来、CVC任意)で購入 → メールが届き、URLからダウンロードできれば成功です。

## 本番前チェック
`docs/deploy.md` の「本番前チェック」と同じです(特商法の記入、商品ファイル配置、SPF/DKIM、本番キーへの切替)。
