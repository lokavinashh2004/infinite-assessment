"""
build_vectorstore.py — Standalone script to build the ChromaDB vector store
from all PDF files in data/policy_pdfs/.

Usage:
    python scripts/build_vectorstore.py

Run this script once before starting the server (or whenever you add new
policy PDFs).  Progress is printed to stdout.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Add the project root to sys.path so that `claim_copilot` is importable ───
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import POLICY_PDF_DIR, VECTOR_DB_DIR  # noqa: E402
from tools.tool3_rag_retriever import build_vectorstore  # noqa: E402


def main() -> None:
    """
    Entry point for the vectorstore build script.

    Prints progress to stdout and exits with code 1 on failure.
    """
    print("=" * 60)
    print("ClaimCopilot — Policy Vector Store Builder")
    print("=" * 60)
    print(f"PDF source directory : {POLICY_PDF_DIR}")
    print(f"Vector store path    : {VECTOR_DB_DIR}")
    print("-" * 60)

    pdf_files = list(Path(POLICY_PDF_DIR).glob("*.pdf"))
    if not pdf_files:
        print(
            "\n[WARNING] No PDF files found in the policy_pdfs/ directory.\n"
            "Place your policy PDF documents there, then re-run this script.\n"
        )
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF file(s):")
    for f in pdf_files:
        print(f"  • {f.name}")
    print()

    try:
        build_vectorstore()
        print("\n[SUCCESS] Vector store built and persisted successfully.")
    except Exception as exc:
        print(f"\n[ERROR] Failed to build vector store: {exc}")
        sys.exit(1)

    print("=" * 60)
    print("Done! You can now start the API server.")
    print("  uvicorn main:app --reload")
    print("=" * 60)


if __name__ == "__main__":
    main()
