"""台本Markdownからナレーション音声(mp3)をElevenLabs APIで生成する。

必要な環境変数:
  ELEVENLABS_API_KEY   ElevenLabsのAPIキー
  ELEVENLABS_VOICE_ID  使用する音声のVoice ID(ElevenLabsのVoice Libraryで確認)
"""
import argparse
import os
import sys
from pathlib import Path

import requests

from parse_script import extract_narration, extract_title

API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def generate_audio(text: str, voice_id: str, api_key: str) -> bytes:
    response = requests.post(
        API_URL.format(voice_id=voice_id),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_file", help="scripts/episode-XXX-*.md へのパス")
    parser.add_argument(
        "-o", "--output", help="出力mp3パス(省略時は pipeline/output/<episode名>.mp3)"
    )
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
    if not api_key or not voice_id:
        print(
            "ELEVENLABS_API_KEY と ELEVENLABS_VOICE_ID を環境変数に設定してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    episode_path = Path(args.episode_file)
    markdown = episode_path.read_text(encoding="utf-8")
    title = extract_title(markdown)
    narration = extract_narration(markdown)

    output_path = Path(args.output) if args.output else Path("pipeline/output") / f"{episode_path.stem}.mp3"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"タイトル: {title}")
    print(f"文字数: {len(narration)}文字")
    print("ElevenLabs APIに音声生成をリクエスト中...")

    audio_bytes = generate_audio(narration, voice_id, api_key)
    output_path.write_bytes(audio_bytes)

    print(f"保存しました: {output_path}")


if __name__ == "__main__":
    main()
