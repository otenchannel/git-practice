# Unity プロジェクト方針
- Unity LTS(最新版)、OpenXR + XR Interaction Toolkit、Meta Quest 3想定
- 機能(MVP): 現地スケール歩行、現況⇔復元の切替、根拠レベル(A確認済み/B史料/C推定/D演出/U未復元)の色分け、解説表示
- `data/evidence.csv` をScriptableObject等に取り込み、各モデルに根拠を紐付ける
- プロジェクト作成後、`.gitignore`(Library/ Temp/ 等)とGit LFSを設定する

## 開発環境
- 開発PC: 研究室PCまたは自前のビルトインPC(GPU性能を確認: VR開発はGTX 1060 / RTX 2060相当以上が目安)
- ヘッドセット: 研究室の機材を使用(機種は要確認。Quest系ならLink/Air Link接続またはAndroidビルド、PC接続型ならOpenXR経由)。デスクトップ操作モードも予備として用意する
- Unityのバージョンは両PCで統一する(`ProjectSettings/ProjectVersion.txt` で管理)

## スクリプト(未コンパイル・Unityで要確認)
`KuzuhaDaiba/Assets/Scripts/` に根拠データの読み込みと色分けの雛形がある。Unityプロジェクト作成後にコンパイルエラーがないか確認すること。
- `EvidenceDatabase`: `StreamingAssets/evidence.csv` を読む(空のGameObjectに付ける)
- `EvidenceTag`: 復元モデルに付け、`element` 名で根拠レベルを色分け
- `sync-evidence.sh`: `data/evidence.csv` を StreamingAssets にコピー(`evidence.csv` を更新したら実行)

## バージョン管理(2026-10-12 記録)
- Unity: 6.6(自宅PCにインストール済み。パッチ番号は `ProjectSettings/ProjectVersion.txt` で確認して追記する)
- Unity Hub: 3.22.2 / ライセンス: Personal
- 研究室PCにも**同じ 6.6 の同じパッチ**を入れる。研究期間(〜12月末)中は途中でバージョンを上げない
- 6.6 が LTS かどうかは未確認(Hub の案内では 6.7 が LTS と読める)。XR関連パッケージの互換は、プロジェクト作成後に Package Manager で確認する
