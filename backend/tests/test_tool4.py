"""
test_tool4.py — Tests for tool4_structured_retriever.

Uses temporary CSV and JSON files (created with pytest fixtures) so no
real data files are required on disk during testing.

Tests:
  1. Happy path  — policy found in CSV (active gold plan)
  2. Happy path  — coverage rules match a treatment
  3. Edge case   — policy ID not in CSV → found=False
  4. Edge case   — treatment not matching any clause → covered=False
  5. Failure     — missing CSV file raises FileNotFoundError
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ─── Fixtures ──────────────────────────────────────────────────────────────────

POLICIES_CSV_CONTENT = """\
policy_id,holder_name,status,plan_type,coverage_limit,start_date,end_date,waiting_period_days
POL-2024-GOLD-001,Rahul Sharma,active,gold,500000,2024-01-01,2025-12-31,30
POL-2024-SILV-003,Anita Verma,active,silver,250000,2024-03-01,2026-02-28,60
POL-2023-SILV-004,Deepak Nair,lapsed,silver,250000,2021-07-01,2023-06-30,60
"""

COVERAGE_JSON_CONTENT = [
    {
        "clause_id": "CL-001",
        "description": "Surgical Procedures",
        "keywords": ["surgery", "appendectomy", "operation"],
        "eligible_plans": ["gold", "silver"],
        "sub_limit": 300000,
        "notes": "All listed surgical procedures.",
    },
    {
        "clause_id": "CL-008",
        "description": "Dental Treatment",
        "keywords": ["dental", "tooth"],
        "eligible_plans": [],
        "sub_limit": 0,
        "notes": "Dental excluded from all plans.",
    },
]


@pytest.fixture
def policies_csv(tmp_path: Path) -> Path:
    """Write a temporary policies.csv and return its path."""
    p = tmp_path / "policies.csv"
    p.write_text(POLICIES_CSV_CONTENT, encoding="utf-8")
    return p


@pytest.fixture
def coverage_json(tmp_path: Path) -> Path:
    """Write a temporary coverage_rules.json and return its path."""
    p = tmp_path / "coverage_rules.json"
    p.write_text(json.dumps(COVERAGE_JSON_CONTENT), encoding="utf-8")
    return p


# ─── Tests — get_policy_record ────────────────────────────────────────────────

class TestGetPolicyRecord:
    """Tests for get_policy_record()."""

    def test_policy_found_active_gold(self, policies_csv: Path, monkeypatch) -> None:
        """Active gold policy should be found and returned with correct fields."""
        monkeypatch.setattr("tools.tool4_structured_retriever.POLICY_CSV", policies_csv)

        from tools.tool4_structured_retriever import get_policy_record
        result = get_policy_record("POL-2024-GOLD-001")

        assert result.found is True
        assert result.policy_id == "POL-2024-GOLD-001"
        assert result.holder_name == "Rahul Sharma"
        assert result.status == "active"
        assert result.plan_type == "gold"
        assert result.coverage_limit == 500000.0
        assert result.waiting_period_days == 30

    def test_policy_found_lapsed(self, policies_csv: Path, monkeypatch) -> None:
        """Lapsed policy should be found with status='lapsed'."""
        monkeypatch.setattr("tools.tool4_structured_retriever.POLICY_CSV", policies_csv)

        from tools.tool4_structured_retriever import get_policy_record
        result = get_policy_record("POL-2023-SILV-004")

        assert result.found is True
        assert result.status == "lapsed"

    def test_policy_not_found(self, policies_csv: Path, monkeypatch) -> None:
        """Unknown policy ID should return found=False with no other fields."""
        monkeypatch.setattr("tools.tool4_structured_retriever.POLICY_CSV", policies_csv)

        from tools.tool4_structured_retriever import get_policy_record
        result = get_policy_record("POL-9999-NONE-999")

        assert result.found is False
        assert result.policy_id == "POL-9999-NONE-999"
        assert result.holder_name is None
        assert result.status is None

    def test_policy_csv_missing_raises(self, tmp_path: Path, monkeypatch) -> None:
        """Missing CSV file should raise FileNotFoundError."""
        monkeypatch.setattr(
            "tools.tool4_structured_retriever.POLICY_CSV",
            tmp_path / "nonexistent.csv",
        )
        from tools.tool4_structured_retriever import get_policy_record
        with pytest.raises(FileNotFoundError):
            get_policy_record("POL-2024-GOLD-001")


# ─── Tests — get_coverage_rules ───────────────────────────────────────────────

class TestGetCoverageRules:
    """Tests for get_coverage_rules()."""

    def test_coverage_matched_gold_plan(self, coverage_json: Path, monkeypatch) -> None:
        """Surgery matched to CL-001 should be covered under gold plan."""
        monkeypatch.setattr("tools.tool4_structured_retriever.COVERAGE_JSON", coverage_json)

        from tools.tool4_structured_retriever import get_coverage_rules
        result = get_coverage_rules(treatment=["Appendectomy", "surgery"], plan_type="gold")

        assert result.plan_type == "gold"
        assert len(result.coverage_results) == 2
        for cr in result.coverage_results:
            assert cr.covered is True
            assert cr.clause_id == "CL-001"
            assert cr.sub_limit == 300000.0

    def test_dental_not_covered_any_plan(self, coverage_json: Path, monkeypatch) -> None:
        """Dental treatment should never be covered (eligible_plans=[])."""
        monkeypatch.setattr("tools.tool4_structured_retriever.COVERAGE_JSON", coverage_json)

        from tools.tool4_structured_retriever import get_coverage_rules
        result = get_coverage_rules(treatment=["dental cleaning"], plan_type="gold")

        assert result.coverage_results[0].covered is False

    def test_unknown_treatment_not_covered(self, coverage_json: Path, monkeypatch) -> None:
        """Treatment with no matching clause should be marked not covered."""
        monkeypatch.setattr("tools.tool4_structured_retriever.COVERAGE_JSON", coverage_json)

        from tools.tool4_structured_retriever import get_coverage_rules
        result = get_coverage_rules(treatment=["acupuncture"], plan_type="gold")

        assert result.coverage_results[0].covered is False
        assert result.coverage_results[0].clause_id is None
        assert "No matching" in result.coverage_results[0].notes

    def test_coverage_json_missing_raises(self, tmp_path: Path, monkeypatch) -> None:
        """Missing JSON file should raise FileNotFoundError."""
        monkeypatch.setattr(
            "tools.tool4_structured_retriever.COVERAGE_JSON",
            tmp_path / "nonexistent.json",
        )
        from tools.tool4_structured_retriever import get_coverage_rules
        with pytest.raises(FileNotFoundError):
            get_coverage_rules(treatment=["surgery"], plan_type="gold")
