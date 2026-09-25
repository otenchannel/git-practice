#!/usr/bin/env python3
"""businesses/01-ai-blog/posts/ の Markdown 記事から site/ 以下の静的HTMLを生成する。
外部依存なし(標準ライブラリのみ)。記事を追加・編集したら実行して site/ をコミットする。

使い方: python3 build_site.py  (このファイルと同じディレクトリで実行)
"""
import html
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
POSTS_DIR = BASE_DIR / "posts"
SITE_DIR = BASE_DIR / "site"
SITE_NAME = "AIツール活用ラボ"
SITE_DESCRIPTION = "フリーランス・個人開発者・中小企業向けに、AIツールの比較・レビュー・活用法を発信するブログ。"

def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def parse_body(lines: list[str]) -> tuple[str, str]:
    """本文行から (HTML, 最初の段落テキスト) を返す。"""
    html_lines: list[str] = []
    in_list = None
    first_paragraph = ""

    def close_list():
        nonlocal in_list
        if in_list:
            html_lines.append(f"</{in_list}>")
            in_list = None

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "":
            close_list()
            i += 1
            continue
        if stripped == "---":
            close_list()
            html_lines.append("<hr>")
            i += 1
            continue
        if stripped.startswith("### "):
            close_list()
            html_lines.append(f"<h3>{inline(stripped[4:])}</h3>")
            i += 1
            continue
        if stripped.startswith("## "):
            close_list()
            html_lines.append(f"<h2>{inline(stripped[3:])}</h2>")
            i += 1
            continue
        if stripped.startswith("# "):
            # 記事タイトル行(別途 <h1> として扱うためスキップ)
            i += 1
            continue
        if stripped.startswith("> "):
            close_list()
            html_lines.append(f"<blockquote><p>{inline(stripped[2:])}</p></blockquote>")
            i += 1
            continue
        checkbox_match = re.match(r"^-\s\[([ xX])\]\s(.*)", stripped)
        if checkbox_match:
            if in_list != "ul":
                close_list()
                html_lines.append('<ul class="checklist">')
                in_list = "ul"
            checked = "checked" if checkbox_match.group(1).lower() == "x" else ""
            html_lines.append(
                f'<li><input type="checkbox" disabled {checked}> {inline(checkbox_match.group(2))}</li>'
            )
            i += 1
            continue
        if stripped.startswith("- "):
            if in_list != "ul":
                close_list()
                html_lines.append("<ul>")
                in_list = "ul"
            html_lines.append(f"<li>{inline(stripped[2:])}</li>")
            i += 1
            continue
        ordered_match = re.match(r"^(\d+)\.\s(.*)", stripped)
        if ordered_match:
            if in_list != "ol":
                close_list()
                html_lines.append("<ol>")
                in_list = "ol"
            html_lines.append(f"<li>{inline(ordered_match.group(2))}</li>")
            i += 1
            continue
        close_list()
        rendered = inline(stripped)
        html_lines.append(f"<p>{rendered}</p>")
        if not first_paragraph and not stripped.startswith(("*", ">")):
            first_paragraph = stripped
        i += 1

    close_list()
    return "\n".join(html_lines), first_paragraph


def page_template(title: str, description: str, body_html: str, is_index: bool) -> str:
    home_link = "" if is_index else '<a href="/">&larr; 記事一覧へ戻る</a>'
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}{'' if is_index else f' | {SITE_NAME}'}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header class="site-header">
  <a class="site-title" href="/">{SITE_NAME}</a>
  <p class="site-description">{SITE_DESCRIPTION}</p>
</header>
<main>
{home_link}
{body_html}
</main>
<footer>
  <p>&copy; {SITE_NAME}</p>
</footer>
</body>
</html>
"""


def build():
    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / "posts").mkdir(exist_ok=True)

    posts = []
    for md_path in sorted(POSTS_DIR.glob("*.md"), reverse=True):
        text = md_path.read_text(encoding="utf-8")
        lines = text.split("\n")
        title_line = next((l for l in lines if l.strip().startswith("# ")), None)
        title = title_line.strip()[2:] if title_line else md_path.stem
        body_html, first_paragraph = parse_body(lines)

        date = md_path.stem[:10]
        slug = md_path.stem[11:] or md_path.stem
        description = first_paragraph[:120] if first_paragraph else SITE_DESCRIPTION

        article_html = f'<article>\n<h1>{inline(title)}</h1>\n<p class="post-date">{date}</p>\n{body_html}\n</article>'
        out_path = SITE_DIR / "posts" / f"{slug}.html"
        out_path.write_text(
            page_template(title, description, article_html, is_index=False), encoding="utf-8"
        )

        posts.append({"title": title, "slug": slug, "date": date, "excerpt": description})

    index_items = "\n".join(
        f'''<li class="post-item">
  <a href="/posts/{p['slug']}">{html.escape(p['title'])}</a>
  <p class="post-date">{p['date']}</p>
  <p class="post-excerpt">{html.escape(p['excerpt'])}</p>
</li>'''
        for p in posts
    )
    index_body = f'<ul class="post-list">\n{index_items}\n</ul>' if posts else "<p>記事はまだありません。</p>"
    (SITE_DIR / "index.html").write_text(
        page_template(SITE_NAME, SITE_DESCRIPTION, index_body, is_index=True), encoding="utf-8"
    )

    print(f"生成完了: {len(posts)} 記事 -> {SITE_DIR}")


if __name__ == "__main__":
    build()
