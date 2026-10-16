import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "articlebot"))
import articlebot as ab

CLEAN = "# タイトル\n\nAI と一緒に作りました。執筆時点の情報です。\n\n- 手順1\n"


def rules(text):
    return {i["rule"] for i in ab.lint(text)}


class LintTest(unittest.TestCase):
    def test_clean_has_no_issues(self):
        self.assertEqual(ab.lint(CLEAN), [])

    def test_secrets_detected(self):
        self.assertIn("secret-key", rules(CLEAN + "sk_test_" + "A" * 20))
        self.assertIn("secret-webhook", rules(CLEAN + "whsec_" + "b" * 20))
        self.assertIn("download-url", rules(CLEAN + "/download/-0S_qCakUd0.1792214694." + "a" * 40))
        self.assertIn("email", rules(CLEAN + "me@gmail.com"))
        self.assertNotIn("email", rules(CLEAN + "you@example.com"))

    def test_short_prefix_alone_is_not_a_secret(self):
        self.assertNotIn("secret-key", rules(CLEAN + "`sk_test_` から始まる"))

    def test_claims_and_unverified(self):
        self.assertIn("income-claim", rules(CLEAN + "誰でも簡単に稼げる"))
        self.assertIn("unverified", rules(CLEAN + "【確認】ここを直す"))

    def test_unverified_inside_html_comment_is_ignored(self):
        self.assertNotIn("unverified", rules("<!-- 【確認】の行を直す -->\n" + CLEAN))
        self.assertIn("unverified", rules("<!-- メモ -->\n" + CLEAN + "【確認】本文"))
        self.assertIn("secret-key", rules("<!-- sk_test_" + "A" * 20 + " -->\n" + CLEAN))  # コメント内の秘密は検出

    def test_note_warnings(self):
        r = rules(CLEAN + "| a | b |\n#### 深い\n")
        self.assertIn("table", r)
        self.assertIn("deep-heading", r)
        self.assertIn("ai-disclosure", rules("# t\n執筆時点\n"))
        self.assertIn("as-of-date", rules("# t\nAI\n"))


class RenderTest(unittest.TestCase):
    def test_html_is_escaped_and_links_restricted(self):
        out = ab.render("# <script>x</script>\n\n[a](javascript:alert(1)) [b](https://example.com)\n\n```\n<b>\n```")
        self.assertNotIn("<script>", out)
        self.assertNotIn('href="javascript', out)
        self.assertIn('href="https://example.com"', out)
        self.assertIn("&lt;b&gt;", out)

    def test_comments_removed(self):
        self.assertNotIn("秘密メモ", ab.render("<!-- 秘密メモ -->\n本文"))


SAMPLE = """# Stripe「エラー」の直し方

AI と一緒に作りました。執筆時点の情報です。リード文。

## 30秒で分かる結論
1. **原因**: これ
2. 直し方

## 直し方
```
x = 1
```

## 比較
本文

## よくある質問
**Q. 試しましたか?**
はい。
"""


class SiteTest(unittest.TestCase):
    def test_structure(self):
        page = ab.site_page("Stripe「エラー」の直し方", SAMPLE.split("\n", 1)[1])
        self.assertIn('id="bar"', page)                       # 進捗バー
        self.assertIn('class="sec tldr"', page)               # 結論カード
        self.assertIn('class="toc"', page)                    # 目次(見出し3つ以上)
        self.assertIn('<mark>エラー</mark>', page)             # タイトルの強調
        self.assertIn('class="qa"', page)                     # FAQカード
        self.assertIn("prefers-reduced-motion", page)         # 動きを減らす設定に対応

    def test_title_and_content_are_escaped(self):
        page = ab.site_page("<script>x</script>", "本文 <img src=x onerror=1>")
        self.assertNotIn("<script>x", page)
        self.assertNotIn("<img", page)

    def test_export_site_requires_approval(self):
        path = Path(tempfile.mkdtemp()) / "a.md"
        path.write_text(SAMPLE, encoding="utf-8")
        with self.assertRaises(SystemExit):
            ab.export_site(path)
        ab.approve(path, "me", reviewed=True)
        self.assertIn("直し方", ab.export_site(path))
        self.assertNotIn("検査結果", ab.export_site(path))  # 公開版に検査パネルは出さない

    def test_preview_site_shows_check_panel(self):
        self.assertIn("検査結果", ab.preview_site(SAMPLE + "\n【確認】未確認", ab.lint(SAMPLE + "\n【確認】未確認")))

    def test_eyecatch_escapes(self):
        self.assertNotIn("<b>x", ab.eyecatch_html("<b>x</b>", "<i>"))


class ApprovalTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "a.md"

    def test_cannot_approve_with_errors(self):
        self.path.write_text(CLEAN + "【確認】未確認", encoding="utf-8")
        with self.assertRaises(SystemExit):
            ab.approve(self.path, "me", reviewed=True)

    def test_approve_requires_human_attestation(self):
        self.path.write_text(CLEAN, encoding="utf-8")
        with self.assertRaises(SystemExit):
            ab.approve(self.path, "me")  # reviewed 宣言なし
        rec = ab.approve(self.path, "me", reviewed=True)
        self.assertIn("自分で行った", rec["attestation"])

    def test_missing_ai_disclosure_blocks_approval(self):
        self.path.write_text("# t\n\n執筆時点の情報です。\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            ab.approve(self.path, "me", reviewed=True)

    def test_export_html_requires_approval_and_has_copy_buttons(self):
        self.path.write_text(CLEAN, encoding="utf-8")
        with self.assertRaises(SystemExit):
            ab.export_html(self.path)
        ab.approve(self.path, "me", reviewed=True)
        page = ab.export_html(self.path)
        self.assertIn("タイトルをコピー", page)
        self.assertIn("本文をコピー", page)
        self.assertIn('<h2 id="t">タイトル</h2>', page)
        self.assertNotIn("<h1>", page)           # タイトルは本文に重複させない
        self.assertIn("公開は、ご自身で押す", page)

    def test_export_html_escapes_title(self):
        self.path.write_text("# <b>t</b>\n\nAI を使いました。執筆時点。\n", encoding="utf-8")
        ab.approve(self.path, "me", reviewed=True)
        self.assertNotIn("<b>t</b>", ab.export_html(self.path))

    def test_export_requires_approval(self):
        self.path.write_text(CLEAN, encoding="utf-8")
        with self.assertRaises(SystemExit):
            ab.export(self.path)

    def test_export_after_approval_and_blocked_after_edit(self):
        self.path.write_text("<!-- 内部メモ -->\n" + CLEAN, encoding="utf-8")
        ab.approve(self.path, "me", reviewed=True)
        out = ab.export(self.path)
        self.assertNotIn("内部メモ", out)
        self.assertIn("タイトル", out)
        self.path.write_text(CLEAN + "追記", encoding="utf-8")  # 承認後の変更
        with self.assertRaises(SystemExit):
            ab.export(self.path)


if __name__ == "__main__":
    unittest.main()
