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

# ─── Silence noisy third-party libs BEFORE any imports ────────────────────────
# Must be set before tensorflow / absl / chromadb are imported.
import os, warnings, logging

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")       # suppress TF C++ logs
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")      # suppress oneDNN info
os.environ.setdefault("ABSL_LOG_LEVEL", "3")             # suppress absl logs
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")

warnings.filterwarnings("ignore", category=FutureWarning)  # np.object, keras, etc.
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*absl.*")

# Silence TensorFlow / Keras / absl Python-level loggers
for _noisy in ("tensorflow", "absl", "keras", "h5py", "chromadb", "urllib3",
               "httpx", "openai", "sentence_transformers", "transformers"):
    logging.getLogger(_noisy).setLevel(logging.ERROR)

# ─── Structured application logger ────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("claimcopilot")

# Silence Werkzeug's per-request noise, keep startup info
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# ─── Application imports ──────────────────────────────────────────────────────

from flask import Flask, jsonify
from flask_cors import CORS

from routers.claims import claims_bp
from routers.chat import chat_bp

# ─── Application factory ──────────────────────────────────────────────────────

app = Flask(__name__)

# ─── Middleware ───────────────────────────────────────────────────────────────

CORS(app, resources={r"/*": {"origins": "*"}})

# ─── Routers ─────────────────────────────────────────────────────────────────

app.register_blueprint(claims_bp)
app.register_blueprint(chat_bp)

# ─── Request logging ──────────────────────────────────────────────────────────

@app.after_request
def _log_request(response):
    """Log every inbound request with method, path, and status code."""
    # Skip health-check spam
    if request_path := getattr(response, "_request_path", None):
        pass
    import flask
    path = flask.request.path
    if path not in ("/health", "/"):
        status = response.status_code
        level = logging.WARNING if status >= 400 else logging.INFO
        log.log(level, "%-6s %-40s → %s", flask.request.method, path, status)
    return response

# ─── Warm-up (Pre-load models and data) ──────────────────────────────────────

def warm_up():
    """Pre-load heavy models and data caches to speed up the first request."""
    log.info("━━━  ClaimCopilot Backend Starting  ━━━")
    log.info("Warming up services …")

    try:
        from tools.tool3_rag_retriever import get_embeddings, _load_vectorstore
        get_embeddings()
        log.info("✔  Embeddings client ready   (OpenRouter text-embedding-3-small)")
        try:
            _load_vectorstore()
            log.info("✔  Vector store loaded")
        except FileNotFoundError:
            log.warning("⚠  Vector store not found — will build on first claim upload")

        from tools.tool4_structured_retriever import _get_policies_df, _get_coverage_clauses
        _get_policies_df()
        _get_coverage_clauses()
        log.info("✔  Policy & coverage data loaded")

        from models.db import init_db
        init_db()
        log.info("✔  SQLite database ready")

    except Exception as exc:
        log.error("✘  Warm-up error: %s", exc)

    log.info("━━━  Ready  · listening on 0.0.0.0:8000  ━━━")

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    warm_up()

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return "ClaimCopilot backend running", 200

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

# ─── Dev entry-point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
