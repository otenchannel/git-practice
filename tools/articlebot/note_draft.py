"""承認済みの記事を、note の編集画面に入力する(あなたの PC で実行する)。第1版。

守ること:
  - 承認済みの記事だけ入力する(articlebot の export と同じ検査。承認後に1文字でも変えると、動かない)
  - 「公開」ボタンを押す処理は、このスクリプトには存在しない。公開は、必ず人間が、ブラウザで押す
  - パスワードは扱わない。ログインは、note_inspect.py の login で、手動で済ませておく
  - 編集画面を開くと、note は記事の枠(下書き)を作る。実行のたびに下書きが1件増える。不要なものは、記事管理で削除する

使い方:
  py tools/articlebot/note_draft.py docs\\articles\\02-managed-payments-tax-code.note.md
  py tools/articlebot/note_draft.py <記事.md> --method clipboard   # 書式つきの入力がうまくいかない場合の、もう1つの方式

確認できていること(あなたの実行結果): タイトル欄は textarea[placeholder='記事タイトル']、本文欄は div[role='textbox'].ProseMirror
未確認: 実際の貼り付け結果の見た目(見出し・箇条書き・コード)、見出し画像の入力(次の段階)
"""
import sys
import time

import articlebot as ab
import note_inspect as ni

TITLE_SEL = 'textarea[placeholder="記事タイトル"]'
BODY_SEL = 'div[role="textbox"].ProseMirror'

# 手動の貼り付けと同じ「書式つきの貼り付けイベント」を、本文欄に送る
PASTE_JS = """
([html, text]) => {
  const el = document.querySelector('div[role="textbox"].ProseMirror');
  if (!el) return 'no-editor';
  el.focus();
  const dt = new DataTransfer();
  dt.setData('text/html', html);
  dt.setData('text/plain', text);
  const ev = new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true});
  el.dispatchEvent(ev);
  return ev.defaultPrevented ? 'handled' : 'not-handled';
}
"""

CLIPBOARD_JS = """
async ([html, text]) => {
  await navigator.clipboard.write([new ClipboardItem({
    'text/html': new Blob([html], {type: 'text/html'}),
    'text/plain': new Blob([text], {type: 'text/plain'})})]);
  return 'copied';
}
"""


def prepare(path):
    """承認済みの記事から、(タイトル, 本文HTML, 本文テキスト)を作る。承認がなければ SystemExit。"""
    approved = ab.export(path)
    title, rest = ab._split_title(approved)
    if not title:
        raise SystemExit("記事の先頭に、「# タイトル」の行が必要です。")
    return title, ab.render(rest), rest


def body_length(page):
    return len(page.locator(BODY_SEL).first.inner_text().strip())


def fill_note(ctx, page, title, html_body, text_body, method="paste-event"):
    page.goto(ni.EDITOR_URL)
    print(f"現在のURL: {ni._short(page.url)}")
    if "login" in page.url:
        raise SystemExit("ログイン画面に移りました。先に note_inspect.py の login を実行してください。")
    title_box = page.locator(TITLE_SEL)
    try:
        title_box.wait_for(state="visible", timeout=60000)
        page.locator(BODY_SEL).first.wait_for(state="visible", timeout=30000)
    except Exception as e:
        raise SystemExit(f"編集画面のタイトル欄・本文欄が表示されませんでした({type(e).__name__})。画面を確認してください。")
    title_box.click()
    title_box.fill(title)
    page.locator(BODY_SEL).first.click()

    results = {}
    if method == "paste-event":
        results["paste-event"] = page.evaluate(PASTE_JS, [html_body, text_body])
        time.sleep(2)
        if body_length(page) < 20:  # 反映されなかった場合は、クリップボード経由に切り替える
            print("書式つきの入力が反映されなかったため、クリップボード経由に切り替えます。")
            method = "clipboard"
    if method == "clipboard":
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://editor.note.com")
        results["clipboard"] = page.evaluate(CLIPBOARD_JS, [html_body, text_body])
        page.locator(BODY_SEL).first.click()
        page.keyboard.press("Control+V")
        time.sleep(2)
    time.sleep(3)  # 自動保存を待つ
    return {"title_filled": title_box.input_value() == title, "body_chars": body_length(page), **results}


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        raise SystemExit(__doc__)
    path = argv[0]
    method = "clipboard" if "--method" in argv and argv[argv.index("--method") + 1] == "clipboard" else "paste-event"
    title, html_body, text_body = prepare(path)  # 承認がなければ、ここで止まる(ブラウザは開かない)
    print(f"承認済みの記事を確認しました: {title}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("playwright が入っていません。先に: py -m pip install playwright && py -m playwright install chromium")
    with sync_playwright() as p:
        ctx = ni._context(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        result = fill_note(ctx, page, title, html_body, text_body, method)
        print("\n===== 入力の結果 =====")
        print(f"タイトル: {'入力できました' if result['title_filled'] else '入力できていません'}")
        print(f"本文: {result['body_chars']} 文字が、本文欄に入りました")
        print("方式:", {k: v for k, v in result.items() if k in ("paste-event", "clipboard")})
        print("見出し画像は、まだ自動化していません。手動で設定してください。")
        print("入力した時点で、note が自動保存します。\n内容を確認し、**公開は、ブラウザで、ご自身で押してください。**")
        input("\n確認・公開が終わったら、ここで Enter を押してください(ブラウザの窓が閉じます): ")
        try:
            ctx.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
