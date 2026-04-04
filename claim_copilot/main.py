"""
main.py — FastAPI application entry point for ClaimCopilot.

Registers:
  - CORS middleware (all origins allowed for development)
  - GET  /health  — liveness check
  - POST /claims/process — claim processing pipeline (via claims router)

Run with:
  uvicorn main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.claims import router as claims_router

# ─── Application factory ───────────────────────────────────────────────────────

app = FastAPI(
    title="ClaimCopilot — AI-Powered Medical Insurance Claim Processor",
    description=(
        "A 5-tool MCP pipeline that reads claim documents, extracts structured "
        "data via Groq AI, retrieves policy rules (RAG + structured data), "
        "and produces an adjudication decision."
    ),
    version="1.0.0",
    contact={
        "name": "ClaimCopilot API",
    },
    license_info={
        "name": "MIT",
    },
)

# ─── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Open for development — restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(claims_router)

# ─── Health check ─────────────────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["System"],
    summary="Liveness check",
    description="Returns HTTP 200 with status='ok' if the server is running.",
)
def health_check() -> dict:
    """
    Liveness endpoint for load balancers and monitoring systems.

    Returns:
        dict: {"status": "ok"}
    """
    return {"status": "ok"}


# ─── Dev entry-point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
