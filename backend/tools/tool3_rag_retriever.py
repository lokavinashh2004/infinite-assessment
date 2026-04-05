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
import sys
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from openai import OpenAI

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    OPENROUTER_API_KEY,
    POLICY_PDF_DIR,
    RAG_TOP_K,
    VECTOR_DB_DIR,
)
from models.schemas import RAGResult, RAGRuleItem

# ─── Lightweight OpenRouter Embeddings (no PyTorch / sentence-transformers) ────

class OpenRouterEmbeddings(Embeddings):
    """
    LangChain-compatible embedding class that calls OpenRouter's
    text-embedding-3-small model. No local ML framework required.
    """
    _EMBED_MODEL = "openai/text-embedding-3-small"

    def __init__(self):
        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        texts = [t.replace("\n", " ") for t in texts]
        response = self._client.embeddings.create(
            model=self._EMBED_MODEL,
            input=texts,
        )
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


# ─── Cache / Lazy Loading ──────────────────────────────────────────────────────

_embeddings_cache: OpenRouterEmbeddings | None = None
_vectorstore_cache: Chroma | None = None

def get_embeddings() -> OpenRouterEmbeddings:
    """Lazy initialization of the OpenRouter embedding client."""
    global _embeddings_cache
    if _embeddings_cache is None:
        sys.stderr.write("[RAG] Initializing OpenRouter embeddings (text-embedding-3-small) ...\n")
        _embeddings_cache = OpenRouterEmbeddings()
    return _embeddings_cache



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
                            if not isinstance(item, dict):
                                continue
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
        embedding=get_embeddings(),
        persist_directory=str(VECTOR_DB_DIR),
        collection_name="policy_rules",
    )
    if hasattr(vectorstore, "persist"):
        vectorstore.persist()
    sys.stderr.write(f"[RAG] Vector store persisted at: {VECTOR_DB_DIR}\n")


# ─── Retrieve ──────────────────────────────────────────────────────────────────

def _load_vectorstore() -> Chroma:
    """
    Load or return the cached ChromaDB vector store.
    """
    global _vectorstore_cache
    if _vectorstore_cache is not None:
        return _vectorstore_cache

    vs_path = Path(VECTOR_DB_DIR)
    if not vs_path.exists() or not any(vs_path.iterdir()):
        raise FileNotFoundError(
            f"Vector store not found at '{vs_path}'. "
            "Run 'python scripts/build_vectorstore.py' first."
        )

    _vectorstore_cache = Chroma(
        persist_directory=str(vs_path),
        embedding_function=get_embeddings(),
        collection_name="policy_rules",
    )
    return _vectorstore_cache


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
        # Ensure page_content is a string even if None was returned by previous buggy indexes
        text_content = (doc.page_content or "").strip()
        
        # Only add non-empty rules
        if not text_content:
            continue
            
        rules.append(
            RAGRuleItem(
                text=text_content,
                source=source,
                relevance_rank=rank,
            )
        )

    return RAGResult(query=query, rules=rules)
