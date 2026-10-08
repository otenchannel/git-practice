# Unity プロジェクト方針
- Unity LTS(最新版)、OpenXR + XR Interaction Toolkit、Meta Quest 3想定
- 機能(MVP): 現地スケール歩行、現況⇔復元の切替、根拠レベルの色分け(confirmed/estimated/speculative)、解説表示
- `data/evidence.csv` をScriptableObject等に取り込み、各モデルに根拠を紐付ける
- プロジェクト作成後、`.gitignore`(Library/ Temp/ 等)とGit LFSを設定する

## 開発環境
- 開発PC: 研究室PCまたは自前のビルトインPC(GPU性能を確認: VR開発はGTX 1060 / RTX 2060相当以上が目安)
- ヘッドセット: 未確認(Quest 3なら Link/Air Link でPC接続、またはAndroidビルド)。ヘッドセットが使えない場合はデスクトップ操作のモードも用意し、実験は研究室機材で行う
- Unityのバージョンは両PCで統一する(`ProjectSettings/ProjectVersion.txt` で管理)
