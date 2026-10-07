"""デジタル商品販売の自動化プロトタイプ(標準ライブラリのみ)。

流れ: 注文作成 -> 決済プロバイダの Webhook(HMAC署名検証) -> 署名付き期限付きDL URLを発行 -> メール送信(outbox)
本番では PaymentProvider/メール送信部分を Stripe 等と SMTP/メールAPIに差し替える。
"""
import hashlib
import hmac
import json
import os
import secrets
import smtplib
import sqlite3
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BASE = Path(__file__).parent
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "dev-webhook-secret").encode()
DOWNLOAD_SECRET = os.environ.get("DOWNLOAD_SECRET", "dev-download-secret").encode()
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").encode()
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8000")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))  # 465ならSSL、それ以外はSTARTTLS
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER)
STRIPE_TOLERANCE_SEC = 300
LINK_TTL_SEC = int(os.environ.get("LINK_TTL_SEC", 24 * 3600))
MAX_DOWNLOADS = int(os.environ.get("MAX_DOWNLOADS", 3))


def load_products():
    return {p["id"]: p for p in json.loads((BASE / "products.json").read_text(encoding="utf-8"))}


def connect(db_path):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS orders(
        id TEXT PRIMARY KEY, product_id TEXT, email TEXT, status TEXT,
        downloads INTEGER DEFAULT 0, created_at REAL, emailed INTEGER DEFAULT 0)""")
    try:  # 既存DBの移行
        db.execute("ALTER TABLE orders ADD COLUMN emailed INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    return db


def send_mail(msg):
    """メール送信。SMTP_HOST未設定なら何もしない(開発時は outbox に残るだけ)。失敗時は例外。"""
    if not SMTP_HOST:
        return
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = MAIL_FROM, msg["to"], msg["subject"]
    m.set_content(msg["body"])
    if SMTP_PORT == 465:
        smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15)
    else:
        smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        smtp.starttls()
    with smtp:
        if SMTP_USER:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(m)


def sign(data: bytes, secret: bytes) -> str:
    return hmac.new(secret, data, hashlib.sha256).hexdigest()


def create_order(db, product_id, email):
    if product_id not in load_products():
        raise KeyError(product_id)
    oid = secrets.token_urlsafe(8)
    db.execute("INSERT INTO orders(id,product_id,email,status,created_at) VALUES(?,?,?,?,?)",
               (oid, product_id, email, "pending", time.time()))
    db.commit()
    return oid


def make_token(order_id, now=None):
    exp = int((now or time.time()) + LINK_TTL_SEC)
    payload = f"{order_id}.{exp}"
    return f"{payload}.{sign(payload.encode(), DOWNLOAD_SECRET)}"


def verify_token(token, now=None):
    """有効なら order_id を返す。無効/期限切れは None。"""
    try:
        order_id, exp, sig = token.rsplit(".", 2)
    except ValueError:
        return None
    if not hmac.compare_digest(sig.encode(), sign(f"{order_id}.{exp}".encode(), DOWNLOAD_SECRET).encode()):
        return None
    if not exp.isdigit() or int(exp) < (now or time.time()):
        return None
    return order_id


def handle_payment_webhook(db, raw_body: bytes, signature: str, base_url, outbox):
    """決済完了通知を処理。署名不正は False。冪等(二重通知でも二重送信しない)。"""
    if not hmac.compare_digest(signature or "", sign(raw_body, WEBHOOK_SECRET)):
        return False
    event = json.loads(raw_body)
    if event.get("type") != "payment.succeeded":
        return True
    return fulfill_order(db, event["order_id"], base_url, outbox)


def fulfill_order(db, order_id, base_url, outbox, amount_jpy=None):
    """入金確認済みの注文を確定し、DL URLを送る。冪等。注文が無い/金額不一致は False。"""
    row = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if row is None:
        return False
    product = load_products()[row["product_id"]]
    if amount_jpy is not None and amount_jpy != product["price_jpy"]:
        return False
    if row["emailed"]:
        return True
    db.execute("UPDATE orders SET status='paid' WHERE id=?", (row["id"],))
    db.commit()
    link = f"{base_url}/download/{make_token(row['id'])}"
    msg = {"to": row["email"], "subject": f"ご購入ありがとうございます: {product['name']}",
           "body": f"{product['name']} をご購入いただきありがとうございます。\n\n"
                   f"ダウンロードURL(24時間有効・{MAX_DOWNLOADS}回まで):\n{link}\n\n"
                   "期限が切れた場合はこのメールにご返信ください。"}
    try:
        send_mail(msg)
    except Exception as e:  # 失敗時は未送信のまま残し、Webhook再送で再試行させる
        print(f"mail failed for order {row['id']}: {e}")
        return False
    outbox.append(msg)
    db.execute("UPDATE orders SET emailed=1 WHERE id=?", (row["id"],))
    db.commit()
    return True


def verify_stripe_signature(raw_body: bytes, header: str, secret=None, now=None):
    """Stripe-Signature (t=...,v1=...) を検証。署名= HMAC-SHA256(secret, f"{t}.{body}")。"""
    secret = secret or STRIPE_WEBHOOK_SECRET
    if not secret or not header:
        return False
    parts = [kv.split("=", 1) for kv in header.split(",") if "=" in kv]
    ts = next((v for k, v in parts if k == "t"), None)
    sigs = [v for k, v in parts if k == "v1"]
    if not ts or not ts.isdigit() or abs((now or time.time()) - int(ts)) > STRIPE_TOLERANCE_SEC:
        return False
    expected = hmac.new(secret, ts.encode() + b"." + raw_body, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, v) for v in sigs)


def handle_stripe_webhook(db, raw_body: bytes, header: str, base_url, outbox):
    if not verify_stripe_signature(raw_body, header):
        return False
    event = json.loads(raw_body)
    if event.get("type") not in ("checkout.session.completed",
                                 "checkout.session.async_payment_succeeded"):
        return True
    obj = event["data"]["object"]
    if obj.get("payment_status") != "paid":  # コンビニ払い等は入金後の async イベントで処理
        return True
    return fulfill_order(db, obj.get("client_reference_id"), base_url, outbox,
                         amount_jpy=obj.get("amount_total"))


def create_checkout_session(order_id, product, email):
    """Stripe Checkout Session を作成し、決済ページURLを返す。"""
    form = {
        "mode": "payment",
        "client_reference_id": order_id,
        "customer_email": email,
        "success_url": f"{PUBLIC_URL}/thanks",
        "cancel_url": f"{PUBLIC_URL}/",
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": "jpy",
        "line_items[0][price_data][unit_amount]": str(product["price_jpy"]),
        "line_items[0][price_data][product_data][name]": product["name"],
    }
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=urllib.parse.urlencode(form).encode(),
        headers={"Authorization": f"Bearer {STRIPE_SECRET_KEY}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["url"]


def make_handler(db_path, outbox):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body=b"", ctype="application/json", extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode())

        def do_GET(self):
            db = connect(db_path)
            if self.path in ("/", "/legal"):
                page = "index.html" if self.path == "/" else "legal.html"
                return self._send(200, (BASE / "static" / page).read_bytes(), "text/html; charset=utf-8")
            if self.path == "/products":
                return self._json(200, list(load_products().values()))
            if self.path.startswith("/download/"):
                order_id = verify_token(self.path[len("/download/"):])
                row = order_id and db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
                if not row or row["status"] != "paid" or row["downloads"] >= MAX_DOWNLOADS:
                    return self._json(403, {"error": "invalid, expired or download limit reached"})
                db.execute("UPDATE orders SET downloads=downloads+1 WHERE id=?", (order_id,))
                db.commit()
                f = BASE / "products" / load_products()[row["product_id"]]["file"]
                return self._send(200, f.read_bytes(), "application/octet-stream",
                                  {"Content-Disposition": f'attachment; filename="{f.name}"'})
            if self.path == "/thanks":
                return self._send(200, "ご購入ありがとうございます。ダウンロードURLをメールでお送りします。".encode(),
                                  "text/plain; charset=utf-8")
            self._json(404, {"error": "not found"})

        def do_POST(self):
            db = connect(db_path)
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path == "/orders":
                try:
                    d = json.loads(raw)
                    email = d.get("email")
                    if not isinstance(email, str) or "@" not in email or len(email) > 254:
                        raise ValueError("invalid email")
                    oid = create_order(db, d["product_id"], d["email"])
                except (KeyError, ValueError):
                    return self._json(400, {"error": "bad request"})
                resp = {"order_id": oid}
                if STRIPE_SECRET_KEY:
                    try:
                        resp["checkout_url"] = create_checkout_session(
                            oid, load_products()[d["product_id"]], d["email"])
                    except Exception as e:
                        print(f"stripe checkout failed for order {oid}: {e}")
                        return self._json(502, {"error": "payment provider unavailable"})
                return self._json(201, resp)
            if self.path == "/webhook/payment":
                ok = handle_payment_webhook(db, raw, self.headers.get("X-Signature"),
                                            f"http://{self.headers.get('Host')}", outbox)
                return self._json(200 if ok else 400, {"ok": ok})
            if self.path == "/webhook/stripe":
                ok = handle_stripe_webhook(db, raw, self.headers.get("Stripe-Signature"),
                                           PUBLIC_URL, outbox)
                return self._json(200 if ok else 400, {"ok": ok})
            self._json(404, {"error": "not found"})

        def log_message(self, *a):
            pass

    return Handler


if __name__ == "__main__":
    outbox = []
    port = int(os.environ.get("PORT", 8000))
    print(f"listening on :{port}")
    HTTPServer(("", port), make_handler(str(BASE / "orders.db"), outbox)).serve_forever()
