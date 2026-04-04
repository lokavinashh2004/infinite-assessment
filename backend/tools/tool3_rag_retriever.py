"""
tool3_rag_retriever.py — Tool 3: RAG-based policy rule retrieval.

Uses HuggingFace sentence-transformers for embeddings, ChromaDB as the
persistent vector store, and LangChain utilities for PDF loading and
text splitting.

Public API:
  build_vectorstore()   — index all PDFs from POLICY_PDF_DIR
  retrieve_policy_rules() — query the vector store and return ranked chunks
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    POLICY_PDF_DIR,
    RAG_TOP_K,
    VECTOR_DB_DIR,
)
from models.schemas import RAGResult, RAGRuleItem

# ─── Embeddings (loaded once at module level) ─────────────────────────────────

_embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)


# ─── Build / index ─────────────────────────────────────────────────────────────

def build_vectorstore() -> None:
    """
    Index all PDF files found in POLICY_PDF_DIR and persist the vector store.

    Uses RecursiveCharacterTextSplitter with the configured chunk size and
    overlap.  Existing embeddings are replaced each time this function runs.

    Raises:
        FileNotFoundError: If POLICY_PDF_DIR does not exist.
        RuntimeError: If no PDF pages could be extracted from any file.
    """
    pdf_dir = Path(POLICY_PDF_DIR)
    if not pdf_dir.exists():
        raise FileNotFoundError(f"Policy PDF directory not found: {pdf_dir}")

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"[RAG] No PDF files found in {pdf_dir}. Vector store not built.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )

    all_docs: list[Any] = []

    for pdf_path in pdf_files:
        print(f"[RAG] Loading: {pdf_path.name}")
        try:
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()
        except Exception as exc:
            print(f"[RAG] WARNING: Could not load '{pdf_path.name}': {exc}")
            continue

        chunks = splitter.split_documents(pages)
        # Stamp source filename into metadata for retrieval provenance
        for chunk in chunks:
            chunk.metadata["source"] = pdf_path.name
        all_docs.extend(chunks)
        print(f"[RAG]   → {len(chunks)} chunks created from {len(pages)} pages")

    if not all_docs:
        raise RuntimeError(
            "No document chunks were produced. Check that the PDF files are readable."
        )

    print(f"[RAG] Indexing {len(all_docs)} total chunks into ChromaDB …")
    vectorstore = Chroma.from_documents(
        documents=all_docs,
        embedding=_embeddings,
        persist_directory=str(VECTOR_DB_DIR),
        collection_name="policy_rules",
    )
    vectorstore.persist()
    print(f"[RAG] Vector store persisted at: {VECTOR_DB_DIR}")


# ─── Retrieve ──────────────────────────────────────────────────────────────────

def _load_vectorstore() -> Chroma:
    """
    Load the persisted ChromaDB vector store from disk.

    Returns:
        Chroma vector store instance ready for similarity search.

    Raises:
        FileNotFoundError: If the vector store has not been built yet.
    """
    vs_path = Path(VECTOR_DB_DIR)
    if not any(vs_path.iterdir()):
        raise FileNotFoundError(
            f"Vector store not found at '{vs_path}'. "
            "Run 'python scripts/build_vectorstore.py' first."
        )

    return Chroma(
        persist_directory=str(vs_path),
        embedding_function=_embeddings,
        collection_name="policy_rules",
    )


def retrieve_policy_rules(
    treatment: list[str],
    claim_type: str,
    top_k: int = RAG_TOP_K,
) -> RAGResult:
    """
    Query the vector store for the most relevant policy rule chunks.

    Constructs a natural-language query from the claim type and treatments,
    then performs a similarity search and returns the top-k results ranked
    by relevance.

    Args:
        treatment: List of treatment/procedure names from the claim.
        claim_type: One of "inpatient" | "outpatient" | "daycare".
        top_k: Number of top results to retrieve.

    Returns:
        RAGResult containing the query string and ranked rule chunks.

    Raises:
        FileNotFoundError: If the vector store has not been built yet.
        RuntimeError: On ChromaDB query failures.
    """
    treatments_str = ", ".join(treatment) if treatment else "general treatment"
    query = f"{claim_type} claim: {treatments_str}"

    try:
        vectorstore = _load_vectorstore()
        docs_with_scores = vectorstore.similarity_search_with_score(query, k=top_k)
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Vector store query failed: {exc}") from exc

    rules: list[RAGRuleItem] = []
    for rank, (doc, _score) in enumerate(docs_with_scores, start=1):
        source = doc.metadata.get("source", "unknown")
        rules.append(
            RAGRuleItem(
                text=doc.page_content.strip(),
                source=source,
                relevance_rank=rank,
            )
        )

    return RAGResult(query=query, rules=rules)
