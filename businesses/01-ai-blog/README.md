# 事業01: AI特化ブログ/SEOメディア

担当エージェント: `.claude/agents/blog-seo-agent.md`

## 概要
フリーランス・個人開発者・中小企業向けに、AIツールの比較・レビュー・活用法を発信するSEOブログ。

## 収益モデル
- Google AdSense(要審査、コンテンツ蓄積後に申請)
- アフィリエイト(紹介ツールの提携プログラム経由)

## 公開URL
https://git-practice-nu-three.vercel.app (Vercel, 本番)

## セットアップチェックリスト(人間側)
- [x] ホスティング先の決定・公開 → **Vercel** で公開完了(2026-09-28)。Vercelプロジェクト「git-practice」(otenchannel/git-practice)のRoot Directoryを`businesses/01-ai-blog/site`に設定し、本番デプロイ済み。※このVercelプロジェクトは事業01専用として使用(他事業が使う場合は別プロジェクトを作成すること)
- [ ] 独自ドメイン取得(任意、最初はVercelの自動割当ドメインでも可)
- [x] Google Search Console 登録 → URLプレフィックス `https://git-practice-nu-three.vercel.app` で登録・所有権確認済み(2026-09-28)。検索パフォーマンスデータは反映待ち(登録直後のため)
- [x] Google Analytics(GA4)登録 → 測定ID `G-B5R6H9BGSW`(2026-09-28)。`build_site.py`のテンプレートに埋め込み済みで、リアルタイムレポートでの計測も確認済み
- [ ] 記事が10本以上たまったら Google AdSense 申請

## Vercelへの接続手順(人間側の作業)
このリポジトリは5事業共有のモノレポのため、Vercelプロジェクト作成時に **Root Directory** をこの事業のサイト出力先に指定する必要があります。

1. https://vercel.com/ でGitHubアカウント連携してログイン(初回のみアカウント作成)
2. 「Add New...」→「Project」→ このリポジトリ `otenchannel/git-practice` をImport
3. 設定画面で以下を指定:
   - **Root Directory**: `businesses/01-ai-blog/site`
   - **Framework Preset**: `Other`(ビルドコマンド不要、静的ファイルをそのまま配信)
   - **Build Command**: 空欄のままでOK
   - **Output Directory**: 空欄のままでOK(Root Directory自体が出力物)
4. 「Deploy」をクリック
5. デプロイ完了後に発行される `https://xxxx.vercel.app` のURLで記事一覧が表示されることを確認

もし画面の内容が不明な場合は、その画面のスクリーンショットを共有してください。内容を確認しながら手順を案内します。

## サイト生成の仕組み
`posts/` 内のMarkdown記事から `site/` 以下に静的HTMLを生成し、Vercelはその `site/` をそのまま配信します(ビルドコマンド不要)。

- 生成スクリプト: `build_site.py`(標準ライブラリのみ、外部依存なし)
- **記事を追加・編集したら、このディレクトリで `python3 build_site.py` を実行して `site/` を再生成し、生成された差分ごとコミットする。**

## ディレクトリ構成
```
posts/        公開用記事(Markdown)。ここを編集する
build_site.py Markdown → 静的HTML 生成スクリプト
site/         生成された静的サイト(Vercelの配信対象)。posts/ 編集後に再生成して都度コミット
```

## 運用ログ
- 2026-09-25: 事業立ち上げ。初回記事「無料で使える文字起こしAIツール5選」を作成。
- 2026-09-25: 2本目の記事「AIライティングツールを選ぶ前に確認すべき7つのチェックポイント」を作成。
- 2026-09-25: 3本目の記事「AI画像生成ツールを商用利用する前に確認すべき5つのポイント」を作成。
- 2026-09-25: ホスティングをVercelに決定。`build_site.py`でMarkdown→静的HTML変換する仕組みと`site/`(配信用出力)を追加。Vercel側のプロジェクト作成(Root Directory指定含む)は人間の作業として手順を本READMEに記載、ユーザーの実施待ち。
- 2026-09-25: ユーザーより公開プラン(Vercelでの静的サイト公開)を承認済み。リポジトリ側の準備は完了。エージェントはブラウザ操作・外部アカウント作成ができないため、Vercelアカウント作成〜プロジェクトImportは引き続きユーザー自身の作業として待機中(手順は上記「Vercelへの接続手順」参照)。
- 2026-09-28: ユーザーがVercelにログインし、リポジトリ`otenchannel/git-practice`を連携(既存プロジェクト「git-practice」)。ユーザーと画面をスクリーンショットで確認しながら、Build and Deployment設定でRoot Directoryを`businesses/01-ai-blog/site`に変更・保存。既存デプロイをRedeployして動作確認(記事一覧・記事詳細ページとも正常表示)、その後「生産段階へ昇格」で本番昇格し、本番URL https://git-practice-nu-three.vercel.app での表示も確認済み。ブログが正式に公開状態になった(現時点で3記事)。
- 2026-09-28: GA4プロパティを作成し測定ID `G-B5R6H9BGSW` を取得、`build_site.py`のページテンプレートにgtag.jsを埋め込みsite/を再生成・デプロイ・本番昇格。GA4リアルタイムレポートでアクセスが計測されることを確認。続けてGoogle Search ConsoleにURLプレフィックス `https://git-practice-nu-three.vercel.app` で登録し、所有権確認まで完了(検索パフォーマンスデータは反映待ち)。これで基盤構築(ホスティング・GA4・Search Console)は一通り完了。
- 2026-09-28: 4本目「個人開発者のためのAIコーディングアシスタント選定ガイド」・5本目「AIチャットボットを自社サイトに導入する前に確認すべきポイント」を作成し`site/`を再生成(計5記事)。push後、Vercelでの再デプロイ・本番昇格をユーザーと実施予定。
