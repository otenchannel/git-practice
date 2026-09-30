"""ナレーション音声とタイトルテキストから、フェイスレス動画(mp4)をffmpegで組み立てる。

背景画像を指定しない場合は単色背景を自動生成する。
サムネイルや本格的なテロップ・図解は別途動画編集ツールで追加する想定で、
ここでは「音声の長さに合わせた背景+タイトル焼き込み」までを自動化する。

事前準備: ffmpegをローカル環境にインストールしておくこと
  - macOS:   brew install ffmpeg
  - Ubuntu:  sudo apt install ffmpeg
  - Windows: https://www.gyan.dev/ffmpeg/builds/ からダウンロードしPATHに追加
"""
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def build_video(audio_path: Path, title: str, output_path: Path, background_image: Optional[Path]):
    duration = get_audio_duration(audio_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    escaped_title = title.replace(":", r"\:").replace("'", r"\'")
    drawtext = (
        f"drawtext=text='{escaped_title}':fontcolor=white:fontsize=56:"
        "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5:boxborderw=20"
    )

    if background_image:
        video_input = ["-loop", "1", "-i", str(background_image)]
    else:
        video_input = ["-f", "lavfi", "-i", f"color=c=0x1a1a2e:s=1920x1080:d={duration}"]

    cmd = [
        "ffmpeg", "-y",
        *video_input,
        "-i", str(audio_path),
        "-vf", drawtext,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True, help="ナレーション音声ファイル(mp3等)")
    parser.add_argument("--title", required=True, help="動画タイトル(画面に焼き込む)")
    parser.add_argument("--output", required=True, help="出力mp4パス")
    parser.add_argument("--background", help="背景画像(省略時は単色背景を自動生成)")
    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"音声ファイルが見つかりません: {audio_path}", file=sys.stderr)
        sys.exit(1)

    background = Path(args.background) if args.background else None
    build_video(audio_path, args.title, Path(args.output), background)
    print(f"保存しました: {args.output}")


if __name__ == "__main__":
    main()
