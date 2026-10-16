"""記事の「検査 → プレビュー → 承認 → 書き出し」ツール(標準ライブラリのみ)。

方針:
  - 公開できるのは「人間が承認した、その内容そのもの」だけ。承認後に1文字でも変わると書き出せない
  - 秘密情報・未確認マーカー・誇大表現を機械的に止める
  - 自動投稿はしない(noteへの貼り付けは人間。自動化する場合は docs/automation-design.md の段階2以降)

使い方:
  python3 tools/articlebot/articlebot.py lint    docs/articles/xx.note.md
  python3 tools/articlebot/articlebot.py preview docs/articles/xx.note.md   # HTMLを生成して目視確認
  python3 tools/articlebot/articlebot.py approve docs/articles/xx.note.md --by 名前 --reviewed
  python3 tools/articlebot/articlebot.py export  docs/articles/xx.note.md [--html --out paste.html]   # 承認済みのみ
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


def export_html(path):
    """承認済みの本文を、noteの編集画面に貼りやすい形(タイトル欄・本文欄それぞれのコピーボタン付き)にする。
    投稿そのものは人間が行う(承認が通らなければ、このページは作れない)。"""
    body = export(path)
    m = re.match(r"\s*#\s+(.*)\n", body)
    title = m.group(1).strip() if m else ""
    rest = body[m.end():] if m else body
    return f"""<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>note 貼り付け用</title><style>
body{{font:16px/1.8 system-ui,"Hiragino Sans","Noto Sans JP",sans-serif;max-width:720px;margin:0 auto;padding:16px;color:#222}}
.bar{{position:sticky;top:0;background:#e8f5e9;border:1px solid #8bc34a;border-radius:8px;padding:8px 16px;margin-bottom:24px}}
button{{font:inherit;padding:8px 14px;margin:4px 8px 4px 0;border:0;border-radius:6px;background:#2f5d50;color:#fff;cursor:pointer}}
pre{{background:#f4f4f2;padding:12px;overflow:auto;border-radius:6px}} code{{background:#f4f4f2;padding:0 4px;border-radius:4px}}
blockquote{{margin:0;padding-left:12px;border-left:3px solid #ccc;color:#555}}
</style>
<div class="bar"><b>承認済み</b>(承認後に内容が変わると、このページは作れません)<br>
<button onclick="copyEl('t')">タイトルをコピー</button><button onclick="copyEl('b')">本文をコピー</button>
<span id="msg" role="status"></span><br>
<small>手順: note の編集画面で、タイトル欄・本文欄に貼り付け → 見た目を確認 → <b>公開は、ご自身で押す</b></small></div>
<h2 id="t">{html.escape(title)}</h2>
<article id="b">{render(rest)}</article>
<script>
function copyEl(id){{const el=document.getElementById(id),r=document.createRange();r.selectNodeContents(el);
const s=getSelection();s.removeAllRanges();s.addRange(r);const ok=document.execCommand('copy');s.removeAllRanges();
document.getElementById('msg').textContent=ok?'コピーしました':'コピーできませんでした。手動で選択してコピーしてください';}}
</script></html>"""



# ---- 自前サイト用の記事ページ(読みやすさ重視。動きは補助にとどめ、動きを減らす設定では無効化) ----
SITE_CSS = """
:root{--bg:#fafaf7;--ink:#1d1d1b;--muted:#6b6b66;--card:#fff;--line:#e4e4de;--accent:#2f5d50;--accent2:#1fa88a;--mark:#ffe066;--code:#14161b;--codefg:#e6e6e0}
@media (prefers-color-scheme:dark){:root{--bg:#121311;--ink:#ecece6;--muted:#9a9a92;--card:#1c1e1b;--line:#32352f;--accent:#7fc4ae;--accent2:#7fc4ae;--mark:#6b5a00;--code:#0b0c0f}}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:72px}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.9 system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif}
#bar{position:fixed;top:0;left:0;height:3px;width:0;background:var(--accent2);z-index:50}
.top{position:sticky;top:0;z-index:40;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:10px 20px;font-size:.85rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hero{position:relative;overflow:hidden;background:#0f1117;color:#fff;padding:64px 20px 56px}
.hero::before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(47,213,180,.14) 1px,transparent 1px),linear-gradient(90deg,rgba(47,213,180,.14) 1px,transparent 1px);background-size:34px 34px;animation:grid 30s linear infinite}
.hero::after{content:"";position:absolute;inset:auto 0 0 0;height:40%;background:linear-gradient(transparent,#0f1117)}
@keyframes grid{to{background-position:34px 34px}}
.hero .in{position:relative;z-index:1;max-width:760px;margin:0 auto}
.pill{display:inline-block;font:700 .75rem/1 ui-monospace,monospace;letter-spacing:.08em;color:#0f1117;background:#2fd5b4;border-radius:99px;padding:6px 12px;margin-bottom:18px}
.hero h1{font-size:clamp(1.6rem,5.2vw,2.4rem);line-height:1.4;margin:0}
.hero h1 mark{background:linear-gradient(transparent 62%,rgba(47,213,180,.55) 62%);color:#fff;padding:0 .1em;background-size:0 100%;background-repeat:no-repeat;animation:mk .9s .3s forwards}
@keyframes mk{to{background-size:100% 100%}}
.wrap{max-width:760px;margin:0 auto;padding:0 20px 80px}
.toc{margin:28px 0 8px;padding:16px 20px;background:var(--card);border:1px solid var(--line);border-radius:12px}
.toc b{font-size:.8rem;color:var(--muted);letter-spacing:.1em}.toc ol{margin:8px 0 0;padding-left:1.3em}
.toc a,.sec a{color:var(--accent);text-decoration:none;background:linear-gradient(currentColor,currentColor) 0 100%/0 2px no-repeat;transition:background-size .3s}
.toc a:hover,.sec a:hover{background-size:100% 2px}
.lead{font-size:1.05rem;color:var(--ink)}
.sec{margin:44px 0;opacity:0;transform:translateY(14px);transition:opacity .6s,transform .6s}.sec.in{opacity:1;transform:none}
.sec h2{font-size:1.45rem;line-height:1.5;margin:0 0 14px;padding-left:14px;border-left:5px solid var(--accent2)}
.sec h3{font-size:1.15rem;margin:30px 0 8px}
p{margin:0 0 1.1em}
strong{background:linear-gradient(transparent 62%,var(--mark) 62%) 0 0/0 100% no-repeat;transition:background-size .8s .2s}.in strong,.in.sec strong{background-size:100% 100%}
code{background:color-mix(in srgb,var(--accent) 12%,transparent);padding:.1em .4em;border-radius:5px;font-size:.88em;overflow-wrap:anywhere;word-break:break-all}
pre{position:relative;background:var(--code);color:var(--codefg);padding:16px;border-radius:10px;overflow:auto;font-size:.82rem;line-height:1.65;margin:0 0 1.4em}
pre code{background:none;padding:0;overflow-wrap:normal;word-break:normal}
.cp{position:absolute;top:8px;right:8px;font:inherit;font-size:.72rem;border:0;border-radius:6px;padding:4px 10px;background:#ffffff22;color:#fff;cursor:pointer}
blockquote{margin:0 0 1.2em;padding:12px 16px;background:var(--card);border-left:4px solid var(--line);color:var(--muted);border-radius:0 8px 8px 0}
ul,ol{padding-left:1.4em;margin:0 0 1.2em}li{margin:.25em 0}
.tldr{background:var(--card);border:1px solid var(--line);border-top:4px solid var(--accent2);border-radius:12px;padding:20px 22px;box-shadow:0 6px 24px #0000000d}
.tldr h2{border:0;padding:0}
.tldr ol{list-style:none;counter-reset:n;padding:0}.tldr li{counter-increment:n;position:relative;padding-left:2.2em;margin:.7em 0}
.tldr li::before{content:counter(n);position:absolute;left:0;top:.15em;width:1.5em;height:1.5em;border-radius:50%;background:var(--accent);color:var(--bg);font-size:.8em;display:grid;place-items:center;font-weight:700}
.qa{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin:0 0 12px;transition:transform .2s,box-shadow .2s}
.qa:hover{transform:translateY(-3px);box-shadow:0 10px 24px #0000001a}.qa .q{font-weight:700;margin:0 0 4px}.qa p{margin:0}
hr{border:0;border-top:1px solid var(--line);margin:32px 0}
.panel{max-width:760px;margin:16px auto;padding:10px 20px;background:#fff8e1;color:#222;border:1px solid #e0c060;border-radius:10px;font-size:.9rem}
.panel .error{color:#b3261e}.panel .warn{color:#8a5a00}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;scroll-behavior:auto!important}.sec{opacity:1;transform:none}strong{background-size:100% 100%}.hero h1 mark{background-size:100% 100%}}
"""

SITE_JS = """
const bar=document.getElementById('bar');
addEventListener('scroll',()=>{const h=document.documentElement;bar.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight||1)*100)+'%'},{passive:true});
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{threshold:.12});
document.querySelectorAll('.sec').forEach(el=>io.observe(el));
document.querySelectorAll('pre').forEach(pre=>{const b=document.createElement('button');b.className='cp';b.textContent='コピー';
b.onclick=()=>{navigator.clipboard&&navigator.clipboard.writeText(pre.innerText.replace(/^コピー\\n?/,'')).then(()=>{b.textContent='コピーしました';setTimeout(()=>b.textContent='コピー',1500)})};pre.appendChild(b)});
"""


def _faq(section_html):
    """「**Q. …**」の段落と、続く回答の段落を、カードにする(自前で生成した HTML のみが対象)。"""
    return re.sub(r"<p><strong>(Q\.[^<]*)</strong></p>\n<p>(.*?)</p>",
                  r'<div class="qa"><p class="q">\1</p><p>\2</p></div>', section_html, flags=re.S)


def _title_markup(title):
    t = html.escape(title)
    return re.sub(r"「([^」]+)」", r"「<mark>\1</mark>」", t, count=1)


def site_page(title, body_md, panel=""):
    body = render(body_md)
    parts = [p for p in re.split(r"(?=<h2>)", body) if p.strip()]
    lead, secs, toc = "", [], []
    for part in parts:
        m = re.match(r"<h2>(.*?)</h2>", part, flags=re.S)
        if not m:
            lead += part
            continue
        sid = f"s{len(secs) + 1}"
        text = m.group(1)
        toc.append(f'<li><a href="#{sid}">{text}</a></li>')
        cls = "sec tldr" if re.match(r"(30秒|先に結論|結論)", re.sub(r"<[^>]+>", "", text)) else "sec"
        inner = part.replace("<h2>", f'<h2 id="{sid}">', 1)
        if "よくある質問" in text:
            inner = _faq(inner)
        secs.append(f'<section class="{cls}">{inner}</section>')
    desc = re.sub(r"<[^>]+>", "", lead)[:110].strip()
    toc_html = f'<nav class="toc"><b>目次</b><ol>{"".join(toc)}</ol></nav>' if len(toc) >= 3 else ""
    return f"""<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc)}">
<style>{SITE_CSS}</style><div id="bar"></div>
<div class="top">{html.escape(title)}</div>{panel}
<header class="hero"><div class="in"><span class="pill">実録・つまずきメモ</span><h1>{_title_markup(title)}</h1></div></header>
<main class="wrap">{toc_html}<div class="lead">{lead}</div>{"".join(secs)}</main>
<script>{SITE_JS}</script></html>"""


def _split_title(text):
    body = re.sub(r"<!--.*?-->\n*", "", text, flags=re.S)
    m = re.match(r"\s*#\s+(.*)\n", body)
    return (m.group(1).strip(), body[m.end():]) if m else ("", body)


def preview_site(text, issues):
    title, rest = _split_title(text)
    rows = "".join(f'<li class="{i["level"]}"><b>{i["level"].upper()}</b> 行{i["line"]}: {html.escape(i["msg"])} <small>({i["rule"]})</small></li>' for i in issues) or "<li>問題は見つかりませんでした</li>"
    status = "承認できません(error あり)" if errors(issues) else "承認できます(目視で確認してから)"
    panel = f'<div class="panel"><b>検査結果: {status}</b><ul>{rows}</ul><small>sha256: {sha256(text)[:16]}…</small></div>'
    return site_page(title, rest, panel)


def export_site(path):
    """承認済みの本文を、自前サイト用の記事ページにする(承認が通らなければ作れない)。"""
    title, rest = _split_title(export(path))
    return site_page(title, rest)


def eyecatch_html(main, sub="", tag="実録", w=1280, h=670):
    """note の見出し画像用(1280x670)。スクリーンショットは tools/articlebot/eyecatch.py で撮る。"""
    return f"""<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0}}body{{width:{w}px;height:{h}px;background:#0f1117;color:#fff;font-family:"Noto Sans CJK JP","Noto Sans JP","Hiragino Sans",sans-serif;position:relative;overflow:hidden}}
.g{{position:absolute;inset:0;background-image:linear-gradient(rgba(47,213,180,.16) 2px,transparent 2px),linear-gradient(90deg,rgba(47,213,180,.16) 2px,transparent 2px);background-size:56px 56px}}
.d{{position:absolute;right:-60px;top:-60px;width:520px;height:520px;background:radial-gradient(#2fd5b4 3px,transparent 3.5px) 0 0/26px 26px;-webkit-mask:radial-gradient(circle,#000 20%,transparent 68%);mask:radial-gradient(circle,#000 20%,transparent 68%);opacity:.55}}
.c{{position:absolute;left:84px;right:84px;top:50%;transform:translateY(-50%)}}
.t{{display:inline-block;font:700 28px ui-monospace,monospace;color:#0f1117;background:#2fd5b4;border-radius:99px;padding:10px 22px;letter-spacing:.08em}}
h1{{font-size:78px;line-height:1.28;margin:28px 0 0;font-weight:800}}h1 mark{{background:linear-gradient(transparent 64%,rgba(47,213,180,.6) 64%);color:#fff}}
p{{font-size:34px;color:#b9c2cc;margin:26px 0 0}}</style>
<div class="g"></div><div class="d"></div><div class="c"><span class="t">{html.escape(tag)}</span><h1>{_title_markup(main)}</h1><p>{html.escape(sub)}</p></div>"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["lint", "preview", "approve", "export", "eyecatch"])
    ap.add_argument("file")
    ap.add_argument("--by", help="approve: 承認者の名前")
    ap.add_argument("--reviewed", action="store_true", help="approve: 人間が全文を読み、事実を確認し、必要な修正をしたことの宣言")
    ap.add_argument("--out", help="preview/export: 出力先(省略時は <file>.preview.html / 標準出力)")
    ap.add_argument("--html", action="store_true", help="export: note への貼り付け用ページ(コピーボタン付き)を出力")
    ap.add_argument("--sub", default="", help="eyecatch: 画像の小さな説明文")
    ap.add_argument("--site", action="store_true", help="export/preview: 自前サイト用の、読みやすい記事ページを出力")
    a = ap.parse_args(argv)
    text = Path(a.file).read_text(encoding="utf-8")
    if a.command == "lint":
        issues = lint(text)
        for i in issues:
            print(f"[{i['level']}] 行{i['line']}: {i['msg']} ({i['rule']})")
        print("問題なし" if not issues else f"error {len(errors(issues))} / warn {len(issues) - len(errors(issues))}")
        return 1 if errors(issues) else 0
    if a.command == "eyecatch":
        title, _ = _split_title(text)
        out = Path(a.out or a.file + ".eyecatch.html")
        out.write_text(eyecatch_html(title, a.sub), encoding="utf-8")
        print(f"生成しました: {out}(1280x670。ブラウザで開いてスクリーンショットを撮り、note の見出し画像に使う)")
        return 0
    if a.command == "preview":
        out = Path(a.out or a.file + ".preview.html")
        out.write_text((preview_site if a.site else preview_html)(text, lint(text)), encoding="utf-8")
        print(f"生成しました: {out}(ブラウザで開いて、見た目と検査結果を確認してください)")
    elif a.command == "approve":
        if not a.by:
            raise SystemExit("--by に承認者の名前を指定してください。")
        print("承認を記録しました:", json.dumps(approve(a.file, a.by, a.reviewed), ensure_ascii=False))
    else:
        body = export_site(a.file) if a.site else export_html(a.file) if a.html else export(a.file)
        if a.out:
            Path(a.out).write_text(body, encoding="utf-8")
            print(f"書き出しました: {a.out}")
        else:
            sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
