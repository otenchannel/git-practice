# 事業03: ミニSaaSツール

担当エージェント: `.claude/agents/saas-tool-agent.md`

## 概要
ブラウザ完結型の単機能Webツールを複数展開する。バックエンド不要でホスティングコストを抑える。

## 収益モデル
- 当面は全機能無料で公開し、「開発を支援する」投げ銭ボタン(Stripe Payment Link)で収益化する
- アクセス・支援実績を見ながら、将来的に機能追加型の有料プランへ発展させることを検討する

## セットアップチェックリスト(人間側)
- [ ] Vercel / Netlify / GitHub Pages でのホスティング設定
- [ ] 独自ドメイン(任意)
- [x] Stripeアカウント開設(サンドボックス、publishable key取得済み)
- [ ] Stripe本番環境の有効化(本人確認・銀行口座登録)
- [ ] Stripeダッシュボードで投げ銭用のPayment Linkを作成し、各ツールの `#donation-link-pending` を実リンクに差し替え

## Stripe連携について
バックエンドを持たない静的サイト構成のため、**Stripe Payment Link**(ダッシュボードでノーコード作成できる決済リンク)を使う方針。secret keyをリポジトリに置く必要はない。publishable keyは `stripe-config.js` に保存済み(公開可能な値のため問題なし)。

## ディレクトリ構成
```
tools/text-diff/       テキスト差分比較ツール(第1弾、動作可能)
tools/json-formatter/  JSON整形ツール(第2弾、動作可能)
stripe-config.js       Stripe publishable key
```

## 運用ログ
- 2026-09-25: 事業立ち上げ。第1弾ツール「テキスト差分比較ツール」を実装(バックエンド不要、単体HTML)。
- 2026-09-25: 第2弾ツール「JSON整形ツール」を実装(整形/圧縮/コピー機能)。
- 2026-09-25: Stripeサンドボックスのpublishable keyを登録。
- 2026-09-25: 投げ銭型で収益化する方針を決定。各ツールに「開発を支援する」ボタンを設置(Payment Linkは未作成のためプレースホルダー)。
