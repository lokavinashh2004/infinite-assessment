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
from langchain_huggingface import HuggingFaceEmbeddings
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
    Index all PDF and JSON files found in POLICY_PDF_DIR and persist the vector store.
    """
    pdf_dir = Path(POLICY_PDF_DIR)
    if not pdf_dir.exists():
        raise FileNotFoundError(f"Policy directory not found: {pdf_dir}")

    # Support PDF and JSON files
    files = sorted(list(pdf_dir.glob("*.pdf")) + list(pdf_dir.glob("*.json")))
    import sys
    if not files:
        sys.stderr.write(f"[RAG] No policy files found in {pdf_dir}. Vector store not built.\n")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )

    all_docs: list[Any] = []

    import json
    from langchain_core.documents import Document

    for file_path in files:
        sys.stderr.write(f"[RAG] Loading: {file_path.name}\n")
        ext = file_path.suffix.lower()
        try:
            if ext == ".pdf":
                loader = PyPDFLoader(str(file_path))
                pages = loader.load()
                chunks = splitter.split_documents(pages)
                for chunk in chunks:
                    chunk.metadata["source"] = file_path.name
                all_docs.extend(chunks)
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Expecting a list of objects with 'policy_text' or similar
                    if isinstance(data, list):
                        for item in data:
                            text = item.get("policy_text") or item.get("text") or str(item)
                            policy_id = item.get("policy_id", "unknown")
                            doc = Document(page_content=text, metadata={"source": file_path.name, "policy_id": policy_id})
                            chunks = splitter.split_documents([doc])
                            all_docs.extend(chunks)
        except Exception as exc:
            sys.stderr.write(f"[RAG] WARNING: Could not load '{file_path.name}': {exc}\n")
            continue

    if not all_docs:
        raise RuntimeError(
            "No document chunks were produced. Check that the files are readable."
        )

    sys.stderr.write(f"[RAG] Indexing {len(all_docs)} total chunks into ChromaDB …\n")
    vectorstore = Chroma.from_documents(
        documents=all_docs,
        embedding=_embeddings,
        persist_directory=str(VECTOR_DB_DIR),
        collection_name="policy_rules",
    )
    vectorstore.persist()
    sys.stderr.write(f"[RAG] Vector store persisted at: {VECTOR_DB_DIR}\n")


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
