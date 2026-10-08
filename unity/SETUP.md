# Unity セットアップ手順(Quest 3 / 研究室PC)

プロジェクト本体(`Assets/` など)は Unity エディタで作成する。ここに手順と `.gitignore` を置く。

1. Unity Hub で最新の LTS を入れる。**Android Build Support**(OpenJDK / SDK&NDK)も追加する
2. 新規プロジェクト: テンプレート「3D (URP)」。プロジェクトはこのリポジトリの `unity/KuzuhaDaiba/` に作る
3. Package Manager で次を入れる: XR Plug-in Management、OpenXR、XR Interaction Toolkit(Starter Assets サンプルも)
4. Project Settings → XR Plug-in Management → PC タブと Android タブの両方で OpenXR を有効化。Interaction Profile に Oculus Touch Controller Profile を追加
5. Quest 3 側: 開発者モードを有効化(Meta Quest アプリ)。PC 接続で試すなら Quest Link / Air Link を使う
6. 動作確認の最小シーン: XR Origin + 平面 + テレポート移動(Teleportation Area)
7. 実験用ビルドは Android(Quest 3 単体)で作る。PC 接続の保険として Windows ビルドも残す

## 運用メモ
- `Library/`, `Temp/`, `Builds/` などは Git に入れない(`unity/.gitignore`)
- 大きなアセット(点群・テクスチャ・FBX)は Git LFS で管理する
- Unity のバージョンは研究室PCと自前PCで統一する
