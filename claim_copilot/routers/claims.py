"""
claims.py — FastAPI router for claim processing endpoints.

Defines:
  POST /claims/process  — multipart file upload → run full MCP pipeline → return JSON
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from claim_copilot.mcp.tool_router import run_pipeline

router = APIRouter(prefix="/claims", tags=["Claims"])

# Accepted MIME types
_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
}

# Extension fallback (for clients not sending content-type)
_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}


@router.post(
    "/process",
    summary="Process a medical insurance claim document",
    description=(
        "Upload a claim document (PDF or image) via multipart form. "
        "The pipeline extracts structured data using Groq AI, retrieves relevant "
        "policy rules, and produces a final adjudication decision."
    ),
    response_description="Full pipeline result including decision and execution log",
)
async def process_claim(
    file: UploadFile = File(..., description="Claim document: PDF, PNG, JPG, or TIFF"),
) -> JSONResponse:
    """
    Accept a claim document upload, run the full 5-tool MCP pipeline, return JSON.

    The uploaded file is saved to a unique temp path, processed synchronously,
    and the temp file is always deleted in the finally block.

    Args:
        file: Multipart-uploaded claim document.

    Returns:
        JSONResponse containing the FinalResponse schema.

    Raises:
        HTTPException 400: Unsupported file type.
        HTTPException 422: Extraction or validation error.
        HTTPException 500: Unexpected internal error.
    """
    # ── Validate file extension / content type ─────────────────────────────────
    original_filename = file.filename or "upload"
    ext = Path(original_filename).suffix.lower()

    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file extension '{ext}'. "
                f"Accepted: {sorted(_ALLOWED_EXTENSIONS)}"
            ),
        )

    # ── Write to a unique temp file ────────────────────────────────────────────
    tmp_filename = f"{uuid.uuid4().hex}{ext}"
    tmp_path = Path(tempfile.gettempdir()) / tmp_filename

    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        tmp_path.write_bytes(contents)

        # ── Run pipeline (synchronous; FastAPI thread pool handles this) ───────
        result = run_pipeline(str(tmp_path))
        return JSONResponse(content=result, status_code=200)

    except HTTPException:
        raise  # Re-raise explicit HTTP errors unchanged

    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal pipeline error: {exc}",
        ) from exc

    finally:
        # Always clean up the temp file
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass  # Best-effort cleanup
