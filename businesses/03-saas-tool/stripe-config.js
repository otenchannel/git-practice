// Stripe Publishable Key
// このキーはクライアント側での公開を前提に設計されており、リポジトリへのコミットに問題ありません。
// (Secret Keyは絶対にコミットしないでください。環境のSecrets設定で管理します。)
export const STRIPE_PUBLISHABLE_KEY = "pk_test_51UJSpDAYQiXc7Y37cAVD7dSieRCUNcOf1C3sd7nxq6AQX7ikuciOcbpgHJx9JlYeNMF7isCdQeUggdKJKBo0LMMR00v2DKMc2s";

// 現在サンドボックス(テスト環境)のキーです。本番課金を開始する際は、
// Stripeダッシュボードで本番環境を有効化した後に発行される pk_live_... キーに差し替えてください。
