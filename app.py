"""
app.py — Personal Blog · Flask Application
===========================================
Email is now handled entirely by EmailJS on the frontend.
The /submit-contact Flask route has been removed.

Routes:
  GET  /        → serves the portfolio homepage
  GET  /health  → health check
"""

import os
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32))


# ── Homepage ──────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return render_template("personal_blog.html")


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok", service="personal_blog"), 200


# ── 404 handler ───────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(_):
    return jsonify(error="Not found."), 404


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
