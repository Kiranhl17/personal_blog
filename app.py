"""
app.py — Personal Blog · Flask Application
===========================================
ROOT CAUSE OF 404:
  The original app.py had NO route defined for GET /.
  Flask only knew about POST /submit-contact and GET /health.
  Any browser hitting / correctly got 404.

FIX APPLIED:
  Added index() route at "/" that renders the HTML template
  via Flask's render_template(), which correctly resolves
  files inside the /templates/ folder.

Project layout expected:
  personal_blog/
  ├── app.py                   ← this file
  ├── .env                     ← secrets (never commit)
  ├── .env.example             ← safe template to commit
  ├── requirements.txt
  ├── templates/
  │   └── personal_blog.html   ← Jinja2 template (main site)
  └── static/
      └── contact_form.js      ← fetched by {{ url_for('static',...) }}

Run (dev):   python app.py
Run (prod):  gunicorn -w 4 -b 0.0.0.0:5000 app:app
"""

import os
import smtplib
import logging
import html
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# ── Load .env (dev only; prod uses real env vars) ────────────────────────────
load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32))

# ── CORS — lock to your domain in production ─────────────────────────────────
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")
CORS(app, resources={r"/submit-contact": {"origins": ALLOWED_ORIGIN}})

# ── SMTP config (all from environment — NEVER hard-coded) ────────────────────
SMTP_CONFIG = {
    "host":      os.environ.get("SMTP_HOST", "smtp.gmail.com"),
    "port":      int(os.environ.get("SMTP_PORT", 587)),
    "user":      os.environ.get("SMTP_USER", ""),
    "password":  os.environ.get("SMTP_PASSWORD", ""),
    "recipient": os.environ.get("RECIPIENT_EMAIL", "kiranhl1709@gmail.com"),
}

# ── Field validation rules ────────────────────────────────────────────────────
FIELD_RULES = {
    "name":    {"max": 100, "label": "Name"},
    "email":   {"max": 150, "label": "Email"},
    "subject": {"max": 200, "label": "Subject"},
    "message": {"max": 5000, "label": "Message"},
}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ROUTES                                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# ── FIX: Root route — THIS was the missing piece causing 404 ─────────────────
@app.route("/", methods=["GET"])
def index():
    """
    Serve the personal blog / portfolio homepage.

    Flask's render_template() looks inside the /templates/ folder
    automatically. The {{ url_for('static', filename='...') }} calls
    inside personal_blog.html resolve to /static/... correctly.
    """
    return render_template("personal_blog.html")


# ── Contact form submission ───────────────────────────────────────────────────
@app.route("/submit-contact", methods=["POST"])
def submit_contact():
    """
    POST /submit-contact
    Validates form data, builds a styled email, sends via SMTP.

    200 → { "success": true,  "message": "..." }
    4xx → { "success": false, "error":   "..." }
    5xx → { "success": false, "error":   "..." }
    """
    # 1. Parse body (JSON or form-encoded)
    if request.is_json:
        raw = request.get_json(silent=True) or {}
    else:
        raw = request.form.to_dict()

    if not raw:
        return jsonify(success=False, error="Request body is empty or malformed."), 400

    # 2. Validate fields
    fields, err = _validate(raw)
    if err:
        logger.warning("Validation failed: %s", err)
        return jsonify(success=False, error=err), 422

    # 3. Guard: SMTP must be configured
    if not SMTP_CONFIG["user"] or not SMTP_CONFIG["password"]:
        logger.error("SMTP credentials missing — set SMTP_USER and SMTP_PASSWORD in .env")
        return jsonify(
            success=False,
            error="Email service is not configured. Contact the site owner directly."
        ), 503

    # 4. Build + send
    try:
        msg = _build_email(fields)
        _send(msg)
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP auth failed — check SMTP_USER / SMTP_PASSWORD")
        return jsonify(success=False, error="Email authentication failed. Try again later."), 502
    except smtplib.SMTPConnectError:
        logger.error("SMTP connect error — host=%s port=%s", SMTP_CONFIG["host"], SMTP_CONFIG["port"])
        return jsonify(success=False, error="Could not reach email server. Try again later."), 502
    except smtplib.SMTPRecipientsRefused:
        logger.error("Recipient refused by SMTP server.")
        return jsonify(success=False, error="Email delivery failed. Try again later."), 502
    except TimeoutError:
        logger.error("SMTP connection timed out.")
        return jsonify(success=False, error="Email server timed out. Try again later."), 504
    except smtplib.SMTPException as exc:
        logger.exception("Unexpected SMTP error: %s", exc)
        return jsonify(success=False, error="Unexpected error. Try again later."), 500

    logger.info("Contact form OK — from=%s subject=%s", fields["email"], fields["subject"])
    return jsonify(
        success=True,
        message="Message received! Kiran will get back to you soon."
    ), 200


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok", service="personal_blog"), 200


# ── JSON error handlers ───────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(_):
    return jsonify(success=False, error="Endpoint not found."), 404

@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify(success=False, error="Method not allowed."), 405


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def _validate(data: dict) -> tuple:
    cleaned = {}
    for field, rules in FIELD_RULES.items():
        val = data.get(field, "").strip()
        if not val:
            return None, f"'{rules['label']}' is required."
        if len(val) > rules["max"]:
            return None, f"'{rules['label']}' exceeds {rules['max']} characters."
        cleaned[field] = val

    if not EMAIL_RE.match(cleaned["email"]):
        return None, "Please enter a valid email address."

    return cleaned, None


def _build_email(f: dict) -> MIMEMultipart:
    """Build a plain + HTML multipart email from validated fields."""
    sn = html.escape(f["name"])
    se = html.escape(f["email"])
    ss = html.escape(f["subject"])
    sm = html.escape(f["message"]).replace("\n", "<br>")

    msg = MIMEMultipart("alternative")
    msg["Subject"]  = f"[Portfolio Contact] {ss}"
    msg["From"]     = formataddr((f"Portfolio — {sn}", SMTP_CONFIG["user"]))
    msg["To"]       = SMTP_CONFIG["recipient"]
    msg["Date"]     = formatdate(localtime=True)
    msg["Reply-To"] = f["email"]

    plain = (
        f"New contact via personal_blog\n{'─'*48}\n\n"
        f"Name    : {f['name']}\n"
        f"Email   : {f['email']}\n"
        f"Subject : {f['subject']}\n\n"
        f"Message :\n{f['message']}\n\n{'─'*48}\n"
        f"Reply to this email to respond to {f['name']}.\n"
    )

    htm = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#0d1220;margin:0;padding:24px;color:#e8edf5}}
  .card{{max-width:560px;margin:0 auto;background:#131c2e;border:1px solid rgba(0,212,255,.15);border-radius:12px;overflow:hidden}}
  .hdr{{background:linear-gradient(135deg,#080c14,#0d1220);padding:24px 28px;border-bottom:1px solid rgba(0,212,255,.15)}}
  .hdr h2{{margin:0;color:#00d4ff;font-size:1rem;letter-spacing:.05em}}
  .hdr p{{margin:4px 0 0;color:#7a8ca0;font-size:.8rem}}
  .body{{padding:24px 28px}}
  .row{{margin-bottom:16px}}
  .lbl{{font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#7a8ca0;margin-bottom:3px}}
  .val{{font-size:.92rem;color:#e8edf5;word-break:break-word}}
  .msg{{background:#0d1220;border-left:3px solid #00d4ff;border-radius:0 8px 8px 0;padding:12px 16px;font-size:.9rem;line-height:1.6}}
  .ftr{{padding:14px 28px;background:#080c14;font-size:.72rem;color:#7a8ca0;text-align:center}}
</style></head><body>
<div class="card">
  <div class="hdr"><h2>📬 New Portfolio Contact</h2><p>via personal_blog · /submit-contact</p></div>
  <div class="body">
    <div class="row"><div class="lbl">Name</div><div class="val">{sn}</div></div>
    <div class="row"><div class="lbl">Email</div><div class="val"><a href="mailto:{se}" style="color:#00d4ff">{se}</a></div></div>
    <div class="row"><div class="lbl">Subject</div><div class="val">{ss}</div></div>
    <div class="row"><div class="lbl">Message</div><div class="msg">{sm}</div></div>
  </div>
  <div class="ftr">Reply to this email to respond directly to {sn}.</div>
</div></body></html>"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(htm, "html"))
    return msg


def _send(msg: MIMEMultipart) -> None:
    """Open STARTTLS SMTP connection and dispatch message."""
    with smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"], timeout=10) as srv:
        srv.ehlo()
        srv.starttls()
        srv.ehlo()
        srv.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
        srv.sendmail(SMTP_CONFIG["user"], [SMTP_CONFIG["recipient"]], msg.as_string())
        logger.info("Email dispatched → %s", SMTP_CONFIG["recipient"])


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
