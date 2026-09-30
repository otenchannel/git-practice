#!/usr/bin/env python3
"""
issues/issue-XXX.md からButtondown APIへ下書き(draft)を作成する。

このスクリプトは status=draft でのみ作成する。実際の配信(送信)は
一切行わない — それは send_draft.py の役割で、人間の明示的な確認を
経てからのみ実行する運用にしている。

使い方:
    export BUTTONDOWN_API_KEY=...   # 環境のSecrets経由で設定される想定
    python3 create_draft.py ../issues/issue-004.md
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

API_URL = "https://api.buttondown.com/v1/emails"

SUBJECT_RE = re.compile(r"<!--\s*BUTTONDOWN:SUBJECT:\s*(.+?)\s*-->")
BODY_START_MARK = "<!-- BUTTONDOWN:BODY:START -->"
BODY_END_MARK = "<!-- BUTTONDOWN:BODY:END -->"


def extract_subject_and_body(markdown_text: str) -> tuple[str, str]:
    subject_match = SUBJECT_RE.search(markdown_text)
    if not subject_match:
        raise ValueError(
            "件名マーカー <!-- BUTTONDOWN:SUBJECT: ... --> が見つかりません。"
            "issueファイルに追加してください。"
        )
    subject = subject_match.group(1)

    start = markdown_text.find(BODY_START_MARK)
    end = markdown_text.find(BODY_END_MARK)
    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            "本文マーカー BUTTONDOWN:BODY:START / END が見つからないか、"
            "順序が不正です。issueファイルを確認してください。"
        )
    body = markdown_text[start + len(BODY_START_MARK):end].strip()
    return subject, body


def create_draft(subject: str, body: str, api_key: str) -> dict:
    payload = json.dumps({
        "subject": subject,
        "body": body,
        "status": "draft",
    }).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"Buttondown APIエラー ({e.code}): {error_body}") from e


def main() -> int:
    if len(sys.argv) != 2:
        print("使い方: python3 create_draft.py <issueファイルへのパス>", file=sys.stderr)
        return 1

    issue_path = sys.argv[1]
    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        print(
            "BUTTONDOWN_API_KEY が環境変数に設定されていません。"
            "環境のSecrets設定を確認してください(新しいセッションでのみ反映されます)。",
            file=sys.stderr,
        )
        return 1

    with open(issue_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    subject, body = extract_subject_and_body(markdown_text)

    print(f"件名: {subject}")
    print(f"本文文字数: {len(body)}")
    print("Buttondownに下書き(status=draft)として作成します...")

    result = create_draft(subject, body, api_key)

    print("作成しました。")
    print(f"  ID: {result.get('id')}")
    print(f"  status: {result.get('status')}")
    print("  Buttondownのダッシュボードで内容を確認してください。")
    print("  実際の配信は send_draft.py を使い、必ず人間の確認を経てから行ってください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
