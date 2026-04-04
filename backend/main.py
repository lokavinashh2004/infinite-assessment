"""
main.py — Flask application entry point for ClaimCopilot.

Registers:
  - CORS middleware (all origins allowed for development)
  - GET  /health  — liveness check
  - POST /claims/process — claim processing pipeline (via claims router)

Run with:
  python main.py
"""

from __future__ import annotations

from flask import Flask, jsonify
from flask_cors import CORS

from routers.claims import claims_bp
from routers.chat import chat_bp

# ─── Application factory ───────────────────────────────────────────────────────

app = Flask(__name__)

# ─── Middleware ────────────────────────────────────────────────────────────────

CORS(app, resources={r"/*": {"origins": "*"}})

# ─── Routers ──────────────────────────────────────────────────────────────────

app.register_blueprint(claims_bp)
app.register_blueprint(chat_bp)

# ─── Health check ─────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health_check():
    """
    Liveness endpoint for load balancers and monitoring systems.

    Returns:
        JSON: {"status": "ok"}
    """
    return jsonify({"status": "ok"}), 200

# ─── Dev entry-point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
