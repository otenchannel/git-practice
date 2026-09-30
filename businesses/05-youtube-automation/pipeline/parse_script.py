"""台本Markdown(scripts/episode-XXX-*.md)からナレーション用の本文テキストとタイトルを抽出する。"""
import re
import sys
from pathlib import Path


def extract_title(markdown: str) -> str:
    match = re.search(r"^#\s*エピソード\d+:\s*(.+)$", markdown, re.MULTILINE)
    if not match:
        raise ValueError("タイトル行(# エピソードNNN: ...)が見つかりません")
    return match.group(1).strip()


def extract_narration(markdown: str) -> str:
    body_match = re.search(r"##\s*台本本文\s*\n(.+?)\n---", markdown, re.DOTALL)
    if not body_match:
        raise ValueError("「## 台本本文」セクションが見つかりません")
    body = body_match.group(1)

    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            # 「導入(0:00-0:30)」等の構成見出しはナレーションでは読み上げないため除外
            continue
        stripped = re.sub(r"^\*\*(.+?)\*\*$", r"\1", stripped)
        lines.append(stripped)

    return "\n\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print(f"使い方: python3 {sys.argv[0]} <episode-file.md>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    markdown = path.read_text(encoding="utf-8")
    print(f"# タイトル: {extract_title(markdown)}\n")
    print(extract_narration(markdown))


if __name__ == "__main__":
    main()
