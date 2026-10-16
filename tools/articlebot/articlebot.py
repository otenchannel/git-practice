"""記事の「検査 → プレビュー → 承認 → 書き出し」ツール(標準ライブラリのみ)。

方針:
  - 公開できるのは「人間が承認した、その内容そのもの」だけ。承認後に1文字でも変わると書き出せない
  - 秘密情報・未確認マーカー・誇大表現を機械的に止める
  - 自動投稿はしない(noteへの貼り付けは人間。自動化する場合は docs/automation-design.md の段階2以降)

使い方:
  python3 tools/articlebot/articlebot.py lint    docs/articles/xx.note.md
  python3 tools/articlebot/articlebot.py preview docs/articles/xx.note.md   # HTMLを生成して目視確認
  python3 tools/articlebot/articlebot.py approve docs/articles/xx.note.md --by 名前 --reviewed
  python3 tools/articlebot/articlebot.py export  docs/articles/xx.note.md   # 承認済みのみ
"""
import argparse
import hashlib
import html
import json
import re
import sys
import time
from pathlib import Path

CONFIRM_MARK = "【確認】"

# (rule, level, regex, message)
RULES = [
    ("secret-key", "error", r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{12,}", "Stripe の秘密鍵に見える文字列"),
    ("secret-webhook", "error", r"\bwhsec_[A-Za-z0-9]{12,}", "Webhook 署名シークレットに見える文字列"),
    ("download-url", "error", r"/download/[A-Za-z0-9_\-]+\.\d{9,}\.[0-9a-f]{32,}", "ダウンロードURL(署名付き)に見える文字列"),
    ("email", "error", r"\b[A-Za-z0-9._%+\-]+@(?!example\.(?:com|org|net)\b)[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", "実在しうるメールアドレス(例は example.com を使う)"),
    ("income-claim", "error", r"(?:簡単に|誰でも|絶対に|必ず)稼げ|月\s*\d+\s*万円?\s*(?:稼|収入)|収入を?保証|不労所得で(?:稼|生活)", "収入・成果を約束する表現"),
    ("table", "warn", r"^\s*\|.+\|\s*$", "Markdown の表(note は非対応の可能性。箇条書きに)"),
    ("deep-heading", "warn", r"^#{4,}\s", "見出しが4段以上(note は段数が少ない可能性)"),
]


def lint(text):
    """[{rule, level, line, msg}] を返す。コードブロック内も検査する(秘密は、コード内にも入りうる)。"""
    issues = []
    # 公開時に削除される HTML コメントは、未確認マーカーの対象外(秘密情報などは、コメント内も検査する)
    visible = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", "", m.group(0)), text, flags=re.S).splitlines()
    for n, line in enumerate(text.splitlines(), 1):
        for rule, level, pat, msg in RULES:
            if re.search(pat, line):
                issues.append({"rule": rule, "level": level, "line": n, "msg": msg})
        if CONFIRM_MARK in (visible[n - 1] if n - 1 < len(visible) else ""):
            issues.append({"rule": "unverified", "level": "error", "line": n, "msg": "未確認マーカー(【確認】)が残っている"})
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    if "AI" not in body:
        issues.append({"rule": "ai-disclosure", "level": "error", "line": 0, "msg": "AI を使って作ったことの記載が必要(投稿先の規約)"})
    if "執筆時点" not in body:
        issues.append({"rule": "as-of-date", "level": "warn", "line": 0, "msg": "「執筆時点」の注記が見当たらない"})
    return issues


def errors(issues):
    return [i for i in issues if i["level"] == "error"]


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- 最小限の Markdown → HTML(プレビュー用。HTMLは必ずエスケープする) ----
def _inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" rel="noopener">\1</a>', s)


def render(md):
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    out, in_code, in_list = [], False, None
    for line in md.splitlines():
        if line.strip().startswith("```"):
            out.append("</pre>" if in_code else "<pre>")
            in_code = not in_code
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        m_ul, m_ol = re.match(r"^\s*[-*]\s+(.*)", line), re.match(r"^\s*\d+\.\s+(.*)", line)
        kind = "ul" if m_ul else "ol" if m_ol else None
        if in_list and kind != in_list:
            out.append(f"</{in_list}>")
            in_list = None
        if kind:
            if not in_list:
                out.append(f"<{kind}>")
                in_list = kind
            out.append(f"<li>{_inline((m_ul or m_ol).group(1))}</li>")
            continue
        h = re.match(r"^(#{1,6})\s+(.*)", line)
        if h:
            out.append(f"<h{len(h.group(1))}>{_inline(h.group(2))}</h{len(h.group(1))}>")
        elif line.startswith(">"):
            out.append(f"<blockquote>{_inline(line.lstrip('> '))}</blockquote>")
        elif re.match(r"^-{3,}$", line.strip()):
            out.append("<hr>")
        elif line.strip():
            out.append(f"<p>{_inline(line)}</p>")
    if in_list:
        out.append(f"</{in_list}>")
    return "\n".join(out)


def preview_html(text, issues):
    rows = "".join(
        f'<li class="{i["level"]}"><b>{i["level"].upper()}</b> 行{i["line"]}: {html.escape(i["msg"])} <small>({i["rule"]})</small></li>'
        for i in issues) or "<li>問題は見つかりませんでした</li>"
    status = "承認できません(error あり)" if errors(issues) else "承認できます(目視で確認してから)"
    return f"""<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>プレビュー</title><style>
body{{font:16px/1.8 system-ui,"Hiragino Sans","Noto Sans JP",sans-serif;max-width:720px;margin:0 auto;padding:16px;color:#222}}
pre{{background:#f4f4f2;padding:12px;overflow:auto;border-radius:6px}} code{{background:#f4f4f2;padding:0 4px;border-radius:4px}}
blockquote{{margin:0;padding-left:12px;border-left:3px solid #ccc;color:#555}}
.panel{{position:sticky;top:0;background:#fff8e1;border:1px solid #e0c060;border-radius:8px;padding:8px 16px;margin-bottom:24px}}
.error{{color:#b3261e}} .warn{{color:#8a5a00}}
</style><div class="panel"><b>検査結果: {status}</b><ul>{rows}</ul>
<small>sha256: {sha256(text)[:16]}…</small></div><article>{render(text)}</article></html>"""


def approval_path(path):
    return Path(str(path) + ".approval.json")


ATTESTATION = "全文を読み、事実を確認し、必要な修正を自分で行った"


def approve(path, by, reviewed=False):
    """人間の確認の宣言(reviewed)が必須。機械は、読んだことを検証できないので、宣言を記録に残す。"""
    if not reviewed:
        raise SystemExit(f"承認には、人間の確認が必要です。「{ATTESTATION}」場合に限り、--reviewed を付けてください。")
    text = Path(path).read_text(encoding="utf-8")
    errs = errors(lint(text))
    if errs:
        raise SystemExit("承認できません:\n" + "\n".join(f"  行{e['line']}: {e['msg']}" for e in errs))
    rec = {"sha256": sha256(text), "approved_by": by, "attestation": ATTESTATION, "approved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    approval_path(path).write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return rec


def export(path):
    """承認済み、かつ承認後に内容が変わっていない場合だけ、公開用の本文を返す。"""
    text = Path(path).read_text(encoding="utf-8")
    ap = approval_path(path)
    if not ap.exists():
        raise SystemExit("承認がありません。先に preview で確認し、approve してください。")
    if json.loads(ap.read_text(encoding="utf-8"))["sha256"] != sha256(text):
        raise SystemExit("承認後に内容が変更されています。もう一度 preview → approve してください。")
    if errors(lint(text)):
        raise SystemExit("承認後に検査ルールに違反しています。")
    return re.sub(r"<!--.*?-->\n*", "", text, flags=re.S).strip() + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["lint", "preview", "approve", "export"])
    ap.add_argument("file")
    ap.add_argument("--by", help="approve: 承認者の名前")
    ap.add_argument("--reviewed", action="store_true", help="approve: 人間が全文を読み、事実を確認し、必要な修正をしたことの宣言")
    ap.add_argument("--out", help="preview/export: 出力先(省略時は <file>.preview.html / 標準出力)")
    a = ap.parse_args(argv)
    text = Path(a.file).read_text(encoding="utf-8")
    if a.command == "lint":
        issues = lint(text)
        for i in issues:
            print(f"[{i['level']}] 行{i['line']}: {i['msg']} ({i['rule']})")
        print("問題なし" if not issues else f"error {len(errors(issues))} / warn {len(issues) - len(errors(issues))}")
        return 1 if errors(issues) else 0
    if a.command == "preview":
        out = Path(a.out or a.file + ".preview.html")
        out.write_text(preview_html(text, lint(text)), encoding="utf-8")
        print(f"生成しました: {out}(ブラウザで開いて、見た目と検査結果を確認してください)")
    elif a.command == "approve":
        if not a.by:
            raise SystemExit("--by に承認者の名前を指定してください。")
        print("承認を記録しました:", json.dumps(approve(a.file, a.by, a.reviewed), ensure_ascii=False))
    else:
        body = export(a.file)
        if a.out:
            Path(a.out).write_text(body, encoding="utf-8")
            print(f"書き出しました: {a.out}")
        else:
            sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
