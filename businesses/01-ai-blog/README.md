# 事業01: AI特化ブログ/SEOメディア

担当エージェント: `.claude/agents/blog-seo-agent.md`

## 概要
フリーランス・個人開発者・中小企業向けに、AIツールの比較・レビュー・活用法を発信するSEOブログ。

## 収益モデル
- Google AdSense(要審査、コンテンツ蓄積後に申請)
- アフィリエイト(紹介ツールの提携プログラム経由)

## セットアップチェックリスト(人間側)
- [x] ホスティング先の決定 → **Vercel** に決定(2026-09-25)。リポジトリ側の準備は完了、Vercel側のプロジェクト作成のみ人間の作業が必要(下記「Vercelへの接続手順」参照)
- [ ] 独自ドメイン取得(任意、最初はVercelの自動割当ドメインでも可)
- [ ] Google Search Console 登録
- [ ] Google Analytics(GA4)登録
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
