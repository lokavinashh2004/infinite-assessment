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

import os
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

# ─── Warm-up (Pre-load models and data) ───────────────────────────────────────

def warm_up():
    """Pre-load heavy models and data caches to speed up the first request."""
    import sys
    sys.stdout.write("[WARM-UP] Warming up backend services...\n")
    try:
        # Pre-load embeddings and vector store (Tool 3)
        from tools.tool3_rag_retriever import get_embeddings, _load_vectorstore
        get_embeddings()
        _load_vectorstore()
        
        # Pre-load policy and coverage data (Tool 4)
        from tools.tool4_structured_retriever import _get_policies_df, _get_coverage_clauses
        _get_policies_df()
        _get_coverage_clauses()

        # Initialize SQLite database
        from models.db import init_db
        init_db()
        sys.stdout.write("[WARM-UP] Database initialized.\n")
        
        sys.stdout.write("[WARM-UP] Pre-loading complete.\n")
    except Exception as e:
        sys.stderr.write(f"[WARM-UP WARNING] Failed to pre-load some services: {e}\n")

# Normally we'd do this in a thread or if not in debug mode to avoid double-loading
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    warm_up()

# ─── Health check ─────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    """Root endpoint for status verification."""
    return "Backend running", 200

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
