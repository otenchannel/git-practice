"""note の編集画面の「構造」だけを調べるスクリプト(あなたの PC で実行する)。

安全面:
  - パスワードは扱わない。ログインは、開いたブラウザで、あなたが手動で行う
  - ログイン状態は、このスクリプト専用のプロフィール用フォルダ(~/.articlebot/note-profile)にだけ残る
  - 書き出すのは、入力欄・ボタンなどの「種類・属性・短い文字」だけ。Cookie・保存済みの値・リンク先は書き出さない
  - 記事の公開・保存・送信は、一切行わない

使い方:
  py tools/articlebot/note_inspect.py login     # 開いたブラウザで note にログイン → ターミナルで Enter
  py tools/articlebot/note_inspect.py inspect   # 編集画面が開く → 画面が表示されたら Enter → 構造を表示
"""
import json
import sys
from pathlib import Path

PROFILE = Path.home() / ".articlebot" / "note-profile"
EDITOR_URL = "https://editor.note.com/new"

# ページ内で実行する。入力欄・ボタンなどの構造だけを集める(値・リンク先・Cookie は集めない)
DUMP_JS = r"""
() => {
  const sel = 'input, textarea, [contenteditable], button, [role="button"], select, label';
  const out = [];
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  document.querySelectorAll(sel).forEach(e => {
    const tag = e.tagName.toLowerCase();
    const isFile = tag === 'input' && e.type === 'file';
    if (!vis(e) && !isFile) return;                       // 画面に見えないものは除く(ファイル選択欄は例外)
    const r = e.getBoundingClientRect();
    const text = (tag === 'button' || e.getAttribute('role') === 'button' || tag === 'label')
      ? (e.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 24) : '';
    out.push({
      tag, type: e.type || '', role: e.getAttribute('role') || '',
      placeholder: (e.getAttribute('placeholder') || '').slice(0, 40),
      aria: (e.getAttribute('aria-label') || '').slice(0, 40),
      testid: e.getAttribute('data-testid') || '',
      editable: e.getAttribute('contenteditable') || '',
      cls: (e.className && e.className.toString ? e.className.toString() : '').slice(0, 60),
      text, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)
    });
  });
  return out.slice(0, 120);
}
"""


def format_elements(elements):
    """1行1要素の、貼り付けやすい文字列にする。"""
    lines = []
    for e in elements:
        parts = [e["tag"] + (f"[{e['type']}]" if e.get("type") else "")]
        for key in ("role", "placeholder", "aria", "testid", "editable", "text"):
            if e.get(key):
                parts.append(f"{key}={e[key]!r}")
        if e.get("cls"):
            parts.append(f"class={e['cls']!r}")
        parts.append(f"@({e['x']},{e['y']} {e['w']}x{e['h']})")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _context(p):
    PROFILE.mkdir(parents=True, exist_ok=True)
    return p.chromium.launch_persistent_context(str(PROFILE), headless=False, viewport={"width": 1280, "height": 900})


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv or argv[0] not in ("login", "inspect"):
        raise SystemExit(__doc__)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("playwright が入っていません。先に: py -m pip install playwright && py -m playwright install chromium")
    with sync_playwright() as p:
        ctx = _context(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if argv[0] == "login":
            page.goto("https://note.com/login")
            input("開いたブラウザで note にログインしてください(パスワードは、そこに入力します)。\nログインできたら、ここで Enter を押してください: ")
            print("ログイン状態を、プロフィールに保存しました。")
        else:
            page.goto(EDITOR_URL)
            print(f"現在のURL: {page.url}")
            if "login" in page.url:
                ctx.close()
                raise SystemExit("ログイン画面に移りました。先に `login` を実行してください。")
            input("編集画面が表示されたら、ここで Enter を押してください(記事は書かなくて構いません): ")
            elements = page.evaluate(DUMP_JS)
            print("\n===== ここから =====")
            print(format_elements(elements))
            print("===== ここまで =====")
            print(f"\n(要素 {len(elements)} 件。個人情報や記事の内容が含まれていないか確認してから、貼り付けてください)")
        ctx.close()


if __name__ == "__main__":
    main()
