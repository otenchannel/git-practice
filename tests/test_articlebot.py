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
