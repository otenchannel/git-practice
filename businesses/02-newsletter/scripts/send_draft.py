#!/usr/bin/env python3
"""
Buttondownの下書きメールを実際に配信(送信)する。

**重要**: これは取り消せない操作(購読者に実際にメールが届く)。
このスクリプトは、チャット上でユーザーから明示的な送信の許可を得た
場合にのみ実行すること。特に運用開始から最初の数号は、Claude自身の
判断だけでは絶対に実行しない(README運用方針を参照)。

事故防止のため、第2引数に大文字の "SEND" を渡さない限り何もしない。

使い方:
    export BUTTONDOWN_API_KEY=...
    python3 send_draft.py <email_id> SEND
"""
import json
import os
import sys
import urllib.error
import urllib.request

API_URL_TEMPLATE = "https://api.buttondown.com/v1/emails/{id}"


def send_draft(email_id: str, api_key: str) -> dict:
    payload = json.dumps({"status": "about_to_send"}).encode("utf-8")
    request = urllib.request.Request(
        API_URL_TEMPLATE.format(id=email_id),
        data=payload,
        method="PATCH",
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
    if len(sys.argv) != 3 or sys.argv[2] != "SEND":
        print(
            "使い方: python3 send_draft.py <email_id> SEND\n"
            "第2引数に大文字の SEND を渡さない限り、何も実行しません。\n"
            "このコマンドはユーザーから明示的な送信許可を得てからのみ実行してください。",
            file=sys.stderr,
        )
        return 1

    email_id = sys.argv[1]
    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        print("BUTTONDOWN_API_KEY が環境変数に設定されていません。", file=sys.stderr)
        return 1

    print(f"email_id={email_id} を配信キュー(about_to_send)に変更します...")
    result = send_draft(email_id, api_key)
    print(f"status: {result.get('status')}")
    print("Buttondownのダッシュボードで配信状況を確認してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
