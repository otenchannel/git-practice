import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "store"))
import app


def webhook(db, order_id, outbox, sig=None):
    body = json.dumps({"type": "payment.succeeded", "order_id": order_id}).encode()
    return app.handle_payment_webhook(db, body, sig or app.sign(body, app.WEBHOOK_SECRET),
                                      "http://x", outbox)


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.db = app.connect(tempfile.mktemp())
        self.outbox = []

    def test_paid_order_gets_valid_link_once(self):
        oid = app.create_order(self.db, "starter-guide", "a@example.com")
        self.assertTrue(webhook(self.db, oid, self.outbox))
        self.assertTrue(webhook(self.db, oid, self.outbox))  # 二重通知
        self.assertEqual(len(self.outbox), 1)
        token = self.outbox[0]["body"].split("/download/")[1].split()[0]
        self.assertEqual(app.verify_token(token), oid)

    def test_bad_signature_rejected(self):
        oid = app.create_order(self.db, "starter-guide", "a@example.com")
        self.assertFalse(webhook(self.db, oid, self.outbox, sig="bad"))
        self.assertEqual(self.outbox, [])

    def test_token_tamper_and_expiry(self):
        token = app.make_token("o1")
        self.assertIsNone(app.verify_token(token + "0"))
        self.assertIsNone(app.verify_token("o1.9999999999.あ"))  # 非ASCIIでも例外にしない
        self.assertIsNone(app.verify_token(token, now=time.time() + app.LINK_TTL_SEC + 10))

    def test_unknown_product(self):
        with self.assertRaises(KeyError):
            app.create_order(self.db, "nope", "a@example.com")


SECRET = b"whsec_test"


def stripe_event(order_id, amount=1980, status="paid", etype="checkout.session.completed"):
    return json.dumps({"type": etype, "data": {"object": {
        "client_reference_id": order_id, "amount_total": amount, "payment_status": status}}}).encode()


def stripe_header(body, ts=None, secret=SECRET):
    import hashlib, hmac
    ts = str(int(ts or time.time()))
    return f"t={ts},v1=" + hmac.new(secret, ts.encode() + b"." + body, hashlib.sha256).hexdigest()


class StripeTest(unittest.TestCase):
    def setUp(self):
        self.db = app.connect(tempfile.mktemp())
        self.outbox = []
        app.STRIPE_WEBHOOK_SECRET = SECRET
        self.oid = app.create_order(self.db, "starter-guide", "a@example.com")

    def run_hook(self, body, header=None):
        return app.handle_stripe_webhook(self.db, body, stripe_header(body) if header is None else header, "http://x", self.outbox)

    def test_paid_session_fulfills_once(self):
        body = stripe_event(self.oid)
        self.assertTrue(self.run_hook(body))
        self.assertTrue(self.run_hook(body))
        self.assertEqual(len(self.outbox), 1)

    def test_bad_or_old_signature(self):
        body = stripe_event(self.oid)
        self.assertFalse(self.run_hook(body, stripe_header(body, secret=b"wrong")))
        self.assertFalse(self.run_hook(body, stripe_header(body, ts=time.time() - 3600)))
        self.assertFalse(self.run_hook(body, ""))
        self.assertEqual(self.outbox, [])

    def test_unpaid_and_amount_mismatch_not_fulfilled(self):
        self.assertTrue(self.run_hook(stripe_event(self.oid, status="unpaid")))
        self.assertFalse(self.run_hook(stripe_event(self.oid, amount=1)))
        self.assertEqual(self.outbox, [])


class MailTest(unittest.TestCase):
    def setUp(self):
        self.db = app.connect(tempfile.mktemp())
        self.outbox = []
        self.sent = []
        self._orig = app.send_mail
        self.oid = app.create_order(self.db, "starter-guide", "a@example.com")

    def tearDown(self):
        app.send_mail = self._orig

    def test_mail_failure_then_retry_sends_once(self):
        def boom(msg):
            raise OSError("smtp down")
        app.send_mail = boom
        self.assertFalse(webhook(self.db, self.oid, self.outbox))  # Stripeに再送させる
        self.assertEqual(self.outbox, [])
        app.send_mail = self.sent.append
        self.assertTrue(webhook(self.db, self.oid, self.outbox))   # 再送で成功
        self.assertTrue(webhook(self.db, self.oid, self.outbox))   # 以降は二重送信しない
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["to"], "a@example.com")

    def test_smtp_sends_with_starttls_and_login(self):
        calls = []

        class FakeSMTP:
            def __init__(self, host, port, timeout=None): calls.append(("conn", host, port))
            def starttls(self): calls.append("tls")
            def login(self, u, p): calls.append(("login", u))
            def send_message(self, m): calls.append(("send", m["To"], m["From"]))
            def __enter__(self): return self
            def __exit__(self, *a): pass

        orig = (app.smtplib.SMTP, app.SMTP_HOST, app.SMTP_USER, app.MAIL_FROM)
        app.smtplib.SMTP, app.SMTP_HOST, app.SMTP_USER, app.MAIL_FROM = FakeSMTP, "smtp.x", "u", "shop@x"
        try:
            app.send_mail({"to": "a@example.com", "subject": "s", "body": "b"})
        finally:
            app.smtplib.SMTP, app.SMTP_HOST, app.SMTP_USER, app.MAIL_FROM = orig
        self.assertEqual(calls, [("conn", "smtp.x", 587), "tls", ("login", "u"),
                                 ("send", "a@example.com", "shop@x")])


if __name__ == "__main__":
    unittest.main()
