"""
test_tool3.py — Tests for tool3_rag_retriever.

Mocks ChromaDB and HuggingFace embeddings to avoid real network/disk calls.

Tests:
  1. Happy path  — successful retrieval returns ranked RAGRuleItems
  2. Edge case   — retrieval with empty treatment list
  3. Failure     — vector store not built (FileNotFoundError)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claim_copilot.models.schemas import RAGResult, RAGRuleItem


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_doc_factory():
    """Factory for creating mock LangChain Document objects."""
    def _make(text: str, source: str) -> MagicMock:
        doc = MagicMock()
        doc.page_content = text
        doc.metadata = {"source": source}
        return doc
    return _make


@pytest.fixture
def mock_vectorstore(mock_doc_factory):
    """Provides a mock Chroma vectorstore that returns 2 pre-built documents."""
    vs = MagicMock()
    docs_with_scores = [
        (mock_doc_factory("Surgery is covered up to ₹3,00,000.", "health_policy_gold.pdf"), 0.92),
        (mock_doc_factory("ICU charges: ₹10,000 per day max 15 days.", "health_policy_gold.pdf"), 0.87),
    ]
    vs.similarity_search_with_score.return_value = docs_with_scores
    return vs


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestTool3RagRetriever:
    """Tests for retrieve_policy_rules()."""

    # ── Happy path: successful retrieval ──────────────────────────────────

    def test_retrieve_returns_ranked_rules(self, mock_vectorstore) -> None:
        """Valid query should return a RAGResult with ranked RAGRuleItems."""
        with patch("claim_copilot.tools.tool3_rag_retriever._load_vectorstore",
                   return_value=mock_vectorstore), \
             patch("claim_copilot.tools.tool3_rag_retriever.Path.iterdir",
                   return_value=iter([MagicMock()])):

            from claim_copilot.tools.tool3_rag_retriever import retrieve_policy_rules
            result = retrieve_policy_rules(
                treatment=["Appendectomy", "ICU care"],
                claim_type="inpatient",
                top_k=2,
            )

        assert isinstance(result, RAGResult)
        assert "inpatient" in result.query
        assert "Appendectomy" in result.query
        assert len(result.rules) == 2
        assert result.rules[0].relevance_rank == 1
        assert result.rules[1].relevance_rank == 2
        assert result.rules[0].source == "health_policy_gold.pdf"

    # ── Edge case: empty treatment list ───────────────────────────────────

    def test_retrieve_with_empty_treatment_list(self, mock_vectorstore) -> None:
        """Empty treatment list should still produce a valid query and return rules."""
        with patch("claim_copilot.tools.tool3_rag_retriever._load_vectorstore",
                   return_value=mock_vectorstore), \
             patch("claim_copilot.tools.tool3_rag_retriever.Path.iterdir",
                   return_value=iter([MagicMock()])):

            from claim_copilot.tools.tool3_rag_retriever import retrieve_policy_rules
            result = retrieve_policy_rules(
                treatment=[],
                claim_type="outpatient",
                top_k=2,
            )

        assert "outpatient" in result.query
        assert "general treatment" in result.query  # fallback phrase
        assert isinstance(result.rules, list)

    # ── Failure: vector store not built ───────────────────────────────────

    def test_missing_vectorstore_raises(self, tmp_path: Path) -> None:
        """Querying without a built vector store should raise FileNotFoundError."""
        empty_vs_path = tmp_path / "empty_vs"
        empty_vs_path.mkdir()

        with patch("claim_copilot.tools.tool3_rag_retriever.VECTOR_DB_DIR", empty_vs_path), \
             patch("claim_copilot.tools.tool3_rag_retriever.Path.iterdir",
                   return_value=iter([])):   # Empty directory

            from claim_copilot.tools.tool3_rag_retriever import retrieve_policy_rules
            with pytest.raises(FileNotFoundError, match="Vector store not found"):
                retrieve_policy_rules(
                    treatment=["surgery"],
                    claim_type="inpatient",
                )

    # ── Happy path: content of retrieved rules ────────────────────────────

    def test_retrieved_rule_content(self, mock_vectorstore) -> None:
        """Rule text should match the mock document content."""
        with patch("claim_copilot.tools.tool3_rag_retriever._load_vectorstore",
                   return_value=mock_vectorstore), \
             patch("claim_copilot.tools.tool3_rag_retriever.Path.iterdir",
                   return_value=iter([MagicMock()])):

            from claim_copilot.tools.tool3_rag_retriever import retrieve_policy_rules
            result = retrieve_policy_rules(
                treatment=["Surgery"],
                claim_type="inpatient",
            )

        assert "Surgery is covered" in result.rules[0].text
        assert "ICU charges" in result.rules[1].text
