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

from pipeline.tool_router import run_pipeline
from config import PAST_RECORDS_DIR
import json

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
        
        # ── 3. Archive the record to "Past records" ────────────────────────────────
        try:
            # Create a unique subfolder for this specific upload
            record_id = uuid.uuid4().hex[:8]
            patient_name = "unknown"
            
            # Try to grab patient name for a nicer folder name if available in result
            # Based on standard extracted structures (e.g. claim_details.patient_name)
            claim_details = result.get("claim_details", {})
            if isinstance(claim_details, dict):
                patient_name = secure_filename(str(claim_details.get("patient_name", "unknown")))
            
            archive_dir = PAST_RECORDS_DIR / f"{patient_name}_{record_id}"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the original file
            archive_path = archive_dir / original_filename
            archive_path.write_bytes(contents)
            
            # Save the extracted JSON result
            json_path = archive_dir / "result.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
                
            print(f"[ARCHIVE] Saved record to: {archive_dir}")
        except Exception as arc_exc:
            # Archiving failure should not break the API response
            print(f"[ARCHIVE WARNING] Failed to archive record: {arc_exc}")

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
