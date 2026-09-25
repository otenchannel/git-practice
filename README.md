# git-practice

これはデモです

ブランチやってます

## 事業運営プロジェクト

このリポジトリでは、Claude Codeの専用エージェントが5つの事業のコンテンツ生成・運用を担当する仕組みを構築しています。

- 事業計画: [`BUSINESS_PLAN.md`](./BUSINESS_PLAN.md)
- 必要な外部連携: [`INTEGRATIONS.md`](./INTEGRATIONS.md)
- 各事業の運営エージェント: [`.claude/agents/`](./.claude/agents/)
- 各事業の詳細・コンテンツ: [`businesses/`](./businesses/)

| 事業 | ディレクトリ |
|---|---|
| AI特化ブログ/SEOメディア | [`businesses/01-ai-blog`](./businesses/01-ai-blog) |
| AIニュースレター | [`businesses/02-newsletter`](./businesses/02-newsletter) |
| ミニSaaSツール | [`businesses/03-saas-tool`](./businesses/03-saas-tool) |
| アフィリエイト比較サイト | [`businesses/04-affiliate-site`](./businesses/04-affiliate-site) |
| AI自動運営YouTubeチャンネル | [`businesses/05-youtube-automation`](./businesses/05-youtube-automation) |

**注意:** エージェントはコンテンツ生成・コード実装までを自律的に行います。決済・広告・ドメイン等の外部アカウント開設や実際の収益化には人間の対応が必要です。詳細は `INTEGRATIONS.md` を参照してください。
