"""
config.py — Central configuration for the ClaimCopilot application.

Loads environment variables via python-dotenv and defines shared constants
that are imported across all tools and the MCP router.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env into environment as early as possible so all imports see the vars.
load_dotenv()

# ─── OpenRouter ──────────────────────────────────────────────────────────────

OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
"""OpenRouter API key. Set via OPENROUTER_API_KEY in .env"""

OPENROUTER_MODEL: str = "qwen/qwen-plus"
"""The OpenRouter model used for data extraction."""

# ─── Project root ──────────────────────────────────────────────────────────────

BASE_DIR: Path = Path(__file__).resolve().parent
"""Absolute path to the claim_copilot/ package directory."""

# ─── Data paths ────────────────────────────────────────────────────────────────

DATA_DIR: Path = BASE_DIR / "data"
"""Root directory for all data assets."""

POLICY_CSV: Path = DATA_DIR / "policies.csv"
"""CSV file containing structured policy records."""

COVERAGE_JSON: Path = DATA_DIR / "coverage_rules.json"
"""JSON file containing coverage clause definitions."""

POLICY_PDF_DIR: Path = DATA_DIR / "policy_pdfs"
"""Directory where users place policy PDF documents for RAG indexing."""

VECTOR_DB_DIR: Path = DATA_DIR / "vectorstore"
"""Directory where the ChromaDB persistent vector store is saved."""

# ─── RAG settings ──────────────────────────────────────────────────────────────

EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
"""HuggingFace embedding model used for building and querying the vector store."""

CHUNK_SIZE: int = 500
"""Character chunk size for text splitting during vector store construction."""

CHUNK_OVERLAP: int = 50
"""Overlap between consecutive text chunks."""

RAG_TOP_K: int = 4
"""Default number of chunks to retrieve from the vector store per query."""

# ─── Ensure required directories exist ─────────────────────────────────────────

for _dir in (DATA_DIR, POLICY_PDF_DIR, VECTOR_DB_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
