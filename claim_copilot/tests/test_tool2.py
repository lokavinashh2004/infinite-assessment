"""
test_tool2.py — Tests for tool2_data_extractor.

Uses unittest.mock to patch the Groq API so no real API calls
are made during testing.

Tests:
  1. Happy path — valid JSON response from Groq
  2. Edge case  — Groq response wrapped in markdown fences (stripped correctly)
  3. Failure    — Groq returns invalid JSON
  4. Failure    — Groq returns valid JSON but with wrong claim_type
  5. Failure    — empty raw_text input
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

# ─── Fixtures ──────────────────────────────────────────────────────────────────

VALID_CLAIM_DICT = {
    "policy_id": "POL-2024-GOLD-001",
    "patient_name": "Rahul Sharma",
    "patient_age": 35,
    "hospital_name": "Apollo Hospital",
    "admission_date": "2024-06-01",
    "discharge_date": "2024-06-07",
    "diagnosis": ["Appendicitis"],
    "treatment": ["Appendectomy", "ICU care"],
    "total_amount": 125000.0,
    "itemized_costs": [
        {"item": "Surgery", "cost": 80000.0},
        {"item": "ICU", "cost": 30000.0},
        {"item": "Medicines", "cost": 15000.0},
    ],
    "doctor_name": "Dr. Priya Menon",
    "claim_type": "inpatient",
}

RAW_TEXT = "Medical claim document for Rahul Sharma..."


def _make_mock_message(content: str) -> MagicMock:
    """Build a mock Groq completion object with the given text content."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    return mock_completion


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestTool2DataExtractor:
    """Tests for the extract_claim_data() function."""

    # ── Happy path: valid clean JSON from Groq ────────────────────────────

    def test_valid_extraction(self) -> None:
        """Groq returns clean JSON → ExtractedClaim model is populated correctly."""
        mock_response = json.dumps(VALID_CLAIM_DICT)
        mock_message = _make_mock_message(mock_response)

        with patch("tools.tool2_data_extractor._client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_message

            from tools.tool2_data_extractor import extract_claim_data
            result = extract_claim_data(RAW_TEXT)

        assert result.policy_id == "POL-2024-GOLD-001"
        assert result.patient_name == "Rahul Sharma"
        assert result.patient_age == 35
        assert result.total_amount == 125000.0
        assert result.claim_type == "inpatient"
        assert len(result.itemized_costs) == 3
        assert result.itemized_costs[0].item == "Surgery"

    # ── Edge case: Groq wraps response in markdown code fences ────────────

    def test_markdown_fence_stripping(self) -> None:
        """Groq response wrapped in ```json fences should be stripped and parsed."""
        fenced_response = f"```json\n{json.dumps(VALID_CLAIM_DICT)}\n```"
        mock_message = _make_mock_message(fenced_response)

        with patch("tools.tool2_data_extractor._client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_message

            from tools.tool2_data_extractor import extract_claim_data
            result = extract_claim_data(RAW_TEXT)

        assert result.policy_id == "POL-2024-GOLD-001"
        assert result.claim_type == "inpatient"

    # ── Edge case: bare code fences without language specifier ────────────

    def test_bare_fence_stripping(self) -> None:
        """Groq response wrapped in plain ``` fences should also be stripped."""
        fenced_response = f"```\n{json.dumps(VALID_CLAIM_DICT)}\n```"
        mock_message = _make_mock_message(fenced_response)

        with patch("tools.tool2_data_extractor._client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_message

            from tools.tool2_data_extractor import extract_claim_data
            result = extract_claim_data(RAW_TEXT)

        assert result.patient_name == "Rahul Sharma"

    # ── Failure: Groq returns invalid JSON ────────────────────────────────

    def test_invalid_json_raises(self) -> None:
        """Non-JSON response from Groq should raise ValueError."""
        mock_message = _make_mock_message("I'm sorry, I cannot process this claim.")

        with patch("tools.tool2_data_extractor._client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_message

            from tools.tool2_data_extractor import extract_claim_data
            with pytest.raises(ValueError, match="invalid JSON"):
                extract_claim_data(RAW_TEXT)

    # ── Failure: Invalid claim_type value ─────────────────────────────────

    def test_invalid_claim_type_raises(self) -> None:
        """claim_type not in allowed set should raise ValueError via Pydantic."""
        bad_dict = {**VALID_CLAIM_DICT, "claim_type": "emergency"}
        mock_message = _make_mock_message(json.dumps(bad_dict))

        with patch("tools.tool2_data_extractor._client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_message

            from tools.tool2_data_extractor import extract_claim_data
            with pytest.raises(ValueError, match="claim_type"):
                extract_claim_data(RAW_TEXT)

    # ── Failure: empty input text ─────────────────────────────────────────

    def test_empty_raw_text_raises(self) -> None:
        """Passing empty string as raw_text should raise ValueError immediately."""
        from tools.tool2_data_extractor import extract_claim_data
        with pytest.raises(ValueError, match="raw_text must not be empty"):
            extract_claim_data("")
