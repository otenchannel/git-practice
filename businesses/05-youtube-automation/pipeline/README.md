# 動画制作パイプライン(ローカル実行用)

台本(Markdown)→ ナレーション音声(ElevenLabs)→ 動画(ffmpeg)までを自動化するスクリプト群です。
**このリポジトリを実行しているクラウド環境にはffmpegが入っていないため、ローカルPC(ユーザー自身の環境)で実行してください。**

## 事前準備

### 1. ffmpegのインストール(ローカルPC)
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: https://www.gyan.dev/ffmpeg/builds/ からビルド済みバイナリを取得し、PATHに追加

インストール後、`ffmpeg -version` と `ffprobe -version` が実行できることを確認してください。

### 2. Python依存パッケージ
```
cd businesses/05-youtube-automation/pipeline
pip install -r requirements.txt
```

### 3. 環境変数(ElevenLabs)
```
export ELEVENLABS_API_KEY="自分のAPIキー"
export ELEVENLABS_VOICE_ID="使用する音声のVoice ID"
```
Voice IDは ElevenLabs の Voice Library で使いたい声を選び、詳細画面からコピーできます。
**APIキーはコードや `.env` をリポジトリにコミットしないこと**(`.gitignore` で `.env` を除外済み)。

## 使い方

### 1. ナレーション音声を生成
```
python3 generate_audio.py ../scripts/episode-001-5-ai-habits.md
```
`pipeline/output/episode-001-5-ai-habits.mp3` が生成されます(出力先は `-o` で変更可)。

台本からナレーション文のみを確認したいだけなら、API呼び出しなしで以下も実行できます。
```
python3 parse_script.py ../scripts/episode-001-5-ai-habits.md
```

### 2. 動画を組み立て
```
python3 build_video.py \
  --audio output/episode-001-5-ai-habits.mp3 \
  --title "生成AIで作業時間を半分にする5つの習慣" \
  --output output/episode-001-5-ai-habits.mp4
```
背景画像を指定しない場合は単色背景(ダークネイビー)にタイトルを焼き込んだ動画になります。
`--background 画像パス` で任意の背景画像(サムネイル用に作った画像など)を指定できます。

## 今の自動化範囲と今後

- 自動化済み: 台本 → ナレーション音声 → (単色背景+タイトル焼き込みの)動画ファイル生成
- 未対応(手動 or 今後の課題):
  - テロップ・図解・BGM・効果音の追加(ユーザーの編集経験を活かして仕上げる想定)
  - サムネイル画像の作成
  - YouTubeへのアップロード自動化(`SETUP_GUIDE.md` の手順でOAuth認証情報は準備済み。次のステップとして `upload_video.py` 等を追加する想定だが、**実際のアップロード=公開作業は、事前にユーザーへ公開プランを提示し承認を得てから着手する**)

## 注意事項
- ElevenLabsの無料枠はクレジット制限があるため、生成前に残高([要確認]: 最新の上限は公式サイトで確認)を意識してください。
- ここで生成される動画は「音声+単色背景+タイトル」のみの簡易版です。実際に公開する場合は、テロップや図解を加えるなど、内容と齟齬がない範囲で見やすさを高めることを推奨します。
