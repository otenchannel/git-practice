"""note の編集画面の「構造」だけを調べるスクリプト(あなたの PC で実行する)。

安全面:
  - パスワードは扱わない。ログインは、開いたブラウザで、あなたが手動で行う
  - ログイン状態は、このスクリプト専用のプロフィール用フォルダ(~/.articlebot/note-profile)にだけ残る
  - 書き出すのは、入力欄・ボタンなどの「種類・属性・短い文字」だけ。Cookie・保存済みの値・リンク先は書き出さない
  - 記事の公開・保存・送信は、一切行わない

使い方:
  py tools/articlebot/note_inspect.py login     # 開いたブラウザで note にログイン → ターミナルで Enter
  py tools/articlebot/note_inspect.py inspect   # 編集画面が開く → 画面が表示されたら Enter → 構造を表示
  py tools/articlebot/note_inspect.py diagnose  # 編集画面が読み込み中のまま進まないときの原因調査(失敗した通信・エラーを表示)
"""
import json
import sys
import time
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


def wait_and_collect(pages, want=3, timeout=30):
    """画面の入力欄・ボタンが want 個以上出るまで、1秒おきに調べ直す。時間切れの場合は、その時点の結果を返す。"""
    deadline = time.time() + timeout
    shown = False
    while True:
        elements = []
        for pg in pages:
            if pg.is_closed():
                continue
            try:
                elements += pg.evaluate(DUMP_JS)
            except Exception as e:  # 遷移中など。次の周回で、再試行する
                last = type(e).__name__
        if len(elements) >= want or time.time() > deadline:
            return elements
        if not shown:
            print("編集画面の表示を待っています(最大30秒)…")
            shown = True
        time.sleep(1)


def _short(url):
    """URL から、クエリ(個人情報や認証情報が入りうる部分)を除く。"""
    return url.split("?")[0].split("#")[0][:120]


def diagnose(ctx, page, seconds=25):
    """編集画面を開き、一定時間の間に起きた失敗(通信・エラー)と、ブラウザの状態を表示する。内容(本文・Cookie・クエリ)は出さない。"""
    events = []
    page.on("console", lambda m: events.append(("console." + m.type, m.text[:140])) if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: events.append(("pageerror", str(e)[:140])))
    page.on("requestfailed", lambda r: events.append(("通信失敗", f"{_short(r.url)} ({r.failure})")))
    page.on("response", lambda r: events.append((f"HTTP {r.status}", _short(r.url))) if r.status >= 400 else None)
    page.goto(EDITOR_URL, wait_until="commit")
    print(f"{seconds}秒間、様子を見ます…(ブラウザの窓は閉じないでください)")
    time.sleep(seconds)
    info = {}
    try:
        info = page.evaluate("() => ({state: document.readyState, nodes: document.querySelectorAll('*').length, textLen: (document.body ? document.body.innerText.length : 0), webdriver: navigator.webdriver, ua: navigator.userAgent})")
    except Exception as e:
        info = {"error": type(e).__name__}
    print("\n===== ここから =====")
    print("URL:", _short(page.url))
    print("ブラウザの状態:", json.dumps(info, ensure_ascii=False))
    seen = set()
    print("--- 失敗・エラー(重複は省略) ---")
    for kind, detail in events:
        if (kind, detail) in seen:
            continue
        seen.add((kind, detail))
        print(f"{kind}: {detail}")
        if len(seen) >= 40:
            print("(40件で打ち切り)")
            break
    if not seen:
        print("(失敗・エラーは記録されませんでした)")
    print("===== ここまで =====")


def _context(p):
    PROFILE.mkdir(parents=True, exist_ok=True)
    return p.chromium.launch_persistent_context(str(PROFILE), headless=False, viewport={"width": 1280, "height": 900})


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv or argv[0] not in ("login", "inspect", "diagnose"):
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
        elif argv[0] == "diagnose":
            diagnose(ctx, page)
        else:
            page.goto(EDITOR_URL)
            print(f"現在のURL: {page.url}")
            if "login" in page.url:
                ctx.close()
                raise SystemExit("ログイン画面に移りました。先に `login` を実行してください。")
            input("編集画面が表示されたら、ここで Enter を押してください(記事は書かなくて構いません。ブラウザの窓は、閉じないでください): ")
            # 編集画面が新しいタブで開き直されることがあるので、Enter の時点で開いているタブから、編集画面を探す
            pages = [pg for pg in ctx.pages if not pg.is_closed()]
            if not pages:
                raise SystemExit("ブラウザの窓が、すでに閉じられていました。窓を閉じずに、編集画面が表示された状態で Enter を押してください。")
            print("開いているタブ:")
            for pg in pages:
                print("  -", pg.url.split("?")[0])
            targets = [pg for pg in pages if "editor.note.com" in pg.url] or pages
            # 編集画面は読み込みに時間がかかることがあるので、入力欄などが出てくるまで、最大 30 秒待つ
            elements = wait_and_collect(targets)
            if not elements:
                for pg in pages:  # 診断: 内容は出さず、状態だけを示す
                    try:
                        info = pg.evaluate("() => ({state: document.readyState, nodes: document.querySelectorAll('*').length, textLen: (document.body ? document.body.innerText.length : 0)})")
                        print(f"  診断: {pg.url.split('?')[0]} state={info['state']} nodes={info['nodes']} textLen={info['textLen']}")
                    except Exception as e:
                        print(f"  診断: {pg.url.split('?')[0]} 取得できません({type(e).__name__})")
                raise SystemExit("入力欄やボタンを取得できませんでした。ブラウザの窓に、編集画面(タイトル欄・本文欄)が表示されているか確認して、もう一度 inspect を実行してください。")
            print("\n===== ここから =====")
            print(format_elements(elements))
            print("===== ここまで =====")
            print(f"\n(要素 {len(elements)} 件。個人情報や記事の内容が含まれていないか確認してから、貼り付けてください)")
        try:
            ctx.close()
        except Exception:
            pass  # 窓が、すでに閉じられていても問題ない


if __name__ == "__main__":
    main()
