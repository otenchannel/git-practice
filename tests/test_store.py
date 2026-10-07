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
        token = self.outbox[0]["body"].split("/download/")[1].split(" ")[0]
        self.assertEqual(app.verify_token(token), oid)

    def test_bad_signature_rejected(self):
        oid = app.create_order(self.db, "starter-guide", "a@example.com")
        self.assertFalse(webhook(self.db, oid, self.outbox, sig="bad"))
        self.assertEqual(self.outbox, [])

    def test_token_tamper_and_expiry(self):
        token = app.make_token("o1")
        self.assertIsNone(app.verify_token(token + "0"))
        self.assertIsNone(app.verify_token(token, now=time.time() + app.LINK_TTL_SEC + 10))

    def test_unknown_product(self):
        with self.assertRaises(KeyError):
            app.create_order(self.db, "nope", "a@example.com")


if __name__ == "__main__":
    unittest.main()
