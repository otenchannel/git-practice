# 研究室PCのセットアップ手順

公開リポジトリ(コード・文書)と、非公開リポジトリ(市資料から起こしたデータ)の2つを組み合わせる。
非公開データは公開リポジトリに入れない(`.gitignore` で除外済み)。

## 事前
- Unity Hub と **Unity 6000.6.5f1**(自宅PCと同じパッチ)。Quest実機ビルド用に **Android Build Support**(OpenJDK, Android SDK & NDK Tools)を追加
- Git for Windows
- 空きストレージ 10GB 以上
- 非公開リポジトリは **自分のGitHubアカウントでサインイン**して取得する。共有PCにパスワード・トークンを残さない(使い終わったらサインアウト)

## 手順
```
cd C:\\dev
git clone -b kuzuha-daiba-vr https://github.com/otenchannel/git-practice.git
git clone https://github.com/otenchannel/kuzuha-daiba-private-data.git
```
1. `kuzuha-daiba-private-data\\Assets\\` の中身(`Private` フォルダ、`Private.meta`、`StreamingAssets` の2ファイルと `.meta`)を、
   `git-practice\\unity\\KuzuhaDaiba\\Assets\\` に上書きコピーする(`.meta` も必ず)
2. Unity Hub で `git-practice\\unity\\KuzuhaDaiba` を開く(初回は Library 生成に数分〜十数分)
3. Console に赤いエラーが無いことを確認 → メニュー Kuzuha > Setup MVP → ▶ で動作確認

## 更新の同期
- コード: `git pull origin kuzuha-daiba-vr`
- 非公開データ: 自宅PCで更新したら `kuzuha-daiba-private-data` にコピーして commit/push。研究室で pull して上書きコピー

## VRの試験
- まず Meta Quest Link(USB接続)で ▶ をVR再生して操作確認
- 次に Android ビルド(Quest 3 を開発者モードにして実機で動作確認)

## 注意
- 市資料の利用条件(Q14, Q17)が確認できるまで、非公開リポジトリに他者を追加しない
- 非公開リポジトリは、アカウント設定次第で後から公開に変えられるので設定変更に注意
