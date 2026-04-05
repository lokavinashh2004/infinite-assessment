"""
config.py — Central configuration for the ClaimCopilot application.

Loads environment variables via python-dotenv and defines shared constants
that are imported across all tools and the MCP router.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

# Load .env into environment — override=True ensures stale system env vars
# (e.g. from a previous broken session) never shadow the .env file values.
load_dotenv(find_dotenv(usecwd=True), override=True)

# ─── OpenRouter ──────────────────────────────────────────────────────────────

OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
"""OpenRouter API key. Set via OPENROUTER_API_KEY in .env"""

OPENROUTER_MODEL: str = "google/gemini-2.0-flash-001"
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

POLICY_PDF_DIR: Path = BASE_DIR / "policies"
"""Directory where users place policy documents for RAG indexing."""

VECTOR_DB_DIR: Path = DATA_DIR / "vector_db"
"""Directory where the ChromaDB persistent vector store is saved."""

PAST_RECORDS_DIR: Path = BASE_DIR / "Past records"
"""Legacy directory for file-based archiving."""

RECORDS_DB: Path = DATA_DIR / "records.db"
"""SQLite database for storing processed claim records."""

# ─── RAG settings ──────────────────────────────────────────────────────────────

EMBEDDING_MODEL: str = "openai/text-embedding-3-small"
"""Embedding model used for building and querying the vector store (via OpenRouter API)."""

CHUNK_SIZE: int = 500
"""Character chunk size for text splitting during vector store construction."""

CHUNK_OVERLAP: int = 50
"""Overlap between consecutive text chunks."""

RAG_TOP_K: int = 4
"""Default number of chunks to retrieve from the vector store per query."""

# ─── Ensure required directories exist ─────────────────────────────────────────

for _dir in (DATA_DIR, POLICY_PDF_DIR, VECTOR_DB_DIR, PAST_RECORDS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
