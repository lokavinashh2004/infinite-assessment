"""
claims.py — Flask Blueprint for claim processing endpoints.

Defines:
  POST /claims/process  — multipart file upload → run full MCP pipeline → return JSON
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from mcp.tool_router import run_pipeline

claims_bp = Blueprint("claims", __name__, url_prefix="/claims")

# Accepted MIME types & Extensions
_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}

@claims_bp.route("/process", methods=["POST"])
def process_claim():
    """
    Accept a claim document upload, run the full 5-tool MCP pipeline, return JSON.
    """
    if "file" not in request.files:
        return jsonify({"detail": "No file part in the request"}), 400
        
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"detail": "No selected file"}), 400

    original_filename = secure_filename(file.filename) or "upload"
    ext = Path(original_filename).suffix.lower()

    if ext not in _ALLOWED_EXTENSIONS:
        return jsonify({"detail": f"Unsupported file extension '{ext}'. Accepted: {sorted(_ALLOWED_EXTENSIONS)}"}), 400

    # ── Write to a unique temp file ────────────────────────────────────────────
    tmp_filename = f"{uuid.uuid4().hex}{ext}"
    tmp_path = Path(tempfile.gettempdir()) / tmp_filename

    try:
        contents = file.read()
        if not contents:
            return jsonify({"detail": "Uploaded file is empty."}), 400

        tmp_path.write_bytes(contents)

        # ── Run pipeline (synchronous) ───────
        result = run_pipeline(str(tmp_path))
        return jsonify(result), 200

    except (FileNotFoundError, ValueError) as exc:
        return jsonify({"detail": str(exc)}), 422

    except Exception as exc:
        return jsonify({"detail": f"Internal pipeline error: {exc}"}), 500

    finally:
        # Always clean up the temp file
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass  # Best-effort cleanup
