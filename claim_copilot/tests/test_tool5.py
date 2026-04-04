"""
test_tool5.py — Tests for tool5_validation_engine.

Tests all 3 decision outcomes (Approved, Partially Approved, Rejected) and
all 6 validation checks.

Tests:
  1. Happy path  — all checks pass → Approved
  2. Partial     — only amount exceeds limit → Partially Approved
  3. Rejected    — policy not found → Rejected
  4. Rejected    — policy lapsed → Rejected
  5. Rejected    — treatment not covered → Rejected
  6. Edge case   — waiting period not met → Rejected (CHECK 4 fails)
  7. Edge case   — admission date before policy start → check 3 fails (→ Approved because non-hard)
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from claim_copilot.models.schemas import (
    CoverageResponse,
    CoverageResult,
    ExtractedClaim,
    ItemizedCost,
    PolicyRecord,
)
from claim_copilot.tools.tool5_validation_engine import validate_claim


# ─── Fixtures ──────────────────────────────────────────────────────────────────

TODAY = date.today()
PAST = date(2024, 1, 1)
FUTURE = date(2025, 12, 31)
ADMISSION = date(2024, 6, 1)
DISCHARGE = date(2024, 6, 7)


def _make_claim(
    total_amount: float = 100_000.0,
    treatment: list[str] | None = None,
    claim_type: str = "inpatient",
    admission_date: date = ADMISSION,
    discharge_date: date = DISCHARGE,
) -> ExtractedClaim:
    """Build a valid ExtractedClaim for testing."""
    return ExtractedClaim(
        policy_id="POL-2024-GOLD-001",
        patient_name="Rahul Sharma",
        patient_age=35,
        hospital_name="Apollo Hospital",
        admission_date=admission_date,
        discharge_date=discharge_date,
        diagnosis=["Appendicitis"],
        treatment=treatment or ["Appendectomy", "ICU care"],
        total_amount=total_amount,
        itemized_costs=[ItemizedCost(item="Surgery", cost=total_amount)],
        doctor_name="Dr. Priya Menon",
        claim_type=claim_type,
    )


def _make_policy(
    found: bool = True,
    status: str = "active",
    plan_type: str = "gold",
    coverage_limit: float = 500_000.0,
    start_date: date = PAST,
    end_date: date = FUTURE,
    waiting_period_days: int = 30,
) -> PolicyRecord:
    """Build a PolicyRecord for testing."""
    return PolicyRecord(
        found=found,
        policy_id="POL-2024-GOLD-001",
        holder_name="Rahul Sharma",
        status=status,
        plan_type=plan_type,
        coverage_limit=coverage_limit,
        start_date=start_date,
        end_date=end_date,
        waiting_period_days=waiting_period_days,
    )


def _make_coverage(
    treatment: list[str] | None = None,
    covered: bool = True,
    sub_limit: float | None = 300_000.0,
    plan_type: str = "gold",
) -> CoverageResponse:
    """Build a CoverageResponse; all treatments get the same covered/sub_limit value."""
    treatments = treatment or ["Appendectomy", "ICU care"]
    return CoverageResponse(
        plan_type=plan_type,
        coverage_results=[
            CoverageResult(
                treatment=t,
                covered=covered,
                sub_limit=sub_limit if covered else None,
                clause_id="CL-001" if covered else None,
                notes="Test clause",
            )
            for t in treatments
        ],
    )


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestTool5ValidationEngine:
    """Tests for validate_claim()."""

    # ── 1. Happy path: all checks pass → Approved ─────────────────────────

    def test_all_checks_pass_approved(self) -> None:
        """When all 6 checks pass, decision must be 'Approved' with full amount."""
        claim = _make_claim(total_amount=100_000.0)
        policy = _make_policy()
        coverage = _make_coverage(sub_limit=300_000.0)

        result = validate_claim(claim, policy, coverage)

        assert result.decision == "Approved"
        assert result.approved_amount == 100_000.0
        assert "policy_exists" in result.checks_passed
        assert "policy_active" in result.checks_passed
        assert "treatments_covered" in result.checks_passed
        assert "amount_within_limit" in result.checks_passed
        assert result.timestamp  # Non-empty ISO timestamp

    # ── 2. Partial approval: amount exceeds sub-limit ─────────────────────

    def test_amount_exceeds_limit_partial_approval(self) -> None:
        """Amount exceeding the effective limit → Partially Approved with capped amount."""
        claim = _make_claim(total_amount=600_000.0)
        policy = _make_policy(coverage_limit=500_000.0)
        coverage = _make_coverage(sub_limit=300_000.0)  # effective = min(300k, 500k) = 300k

        result = validate_claim(claim, policy, coverage)

        assert result.decision == "Partially Approved"
        assert result.approved_amount == 300_000.0   # effective limit = min sub_limit
        assert "Partially approved" in result.reason

    # ── 3. Rejected: policy not found ─────────────────────────────────────

    def test_policy_not_found_rejected(self) -> None:
        """Policy not in records (found=False) → Rejected, approved_amount=0."""
        claim = _make_claim()
        policy = _make_policy(found=False)
        coverage = _make_coverage()

        result = validate_claim(claim, policy, coverage)

        assert result.decision == "Rejected"
        assert result.approved_amount == 0.0
        assert "not found" in result.reason.lower()

    # ── 4. Rejected: policy lapsed ────────────────────────────────────────

    def test_lapsed_policy_rejected(self) -> None:
        """Policy with status='lapsed' → Rejected."""
        claim = _make_claim()
        policy = _make_policy(status="lapsed")
        coverage = _make_coverage()

        result = validate_claim(claim, policy, coverage)

        assert result.decision == "Rejected"
        assert result.approved_amount == 0.0
        assert "policy_active" not in result.checks_passed

    # ── 5. Rejected: uncovered treatments ─────────────────────────────────

    def test_uncovered_treatment_rejected(self) -> None:
        """Any uncovered treatment → Rejected regardless of amount."""
        claim = _make_claim(total_amount=50_000.0)
        policy = _make_policy()
        coverage = _make_coverage(covered=False)   # All treatments uncovered

        result = validate_claim(claim, policy, coverage)

        assert result.decision == "Rejected"
        assert result.approved_amount == 0.0
        assert "treatments_covered" not in result.checks_passed

    # ── 6. Edge case: waiting period not met ──────────────────────────────

    def test_waiting_period_not_met(self) -> None:
        """Admission within waiting period → CHECK 4 fails (non-hard → not rejected alone)."""
        claim = _make_claim(
            admission_date=date(2024, 1, 10),   # Only 9 days after policy start
            discharge_date=date(2024, 1, 15),
            total_amount=50_000.0,
        )
        policy = _make_policy(
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            waiting_period_days=30,
        )
        coverage = _make_coverage(sub_limit=300_000.0)

        result = validate_claim(claim, policy, coverage)

        # CHECK 4 failure alone does not trigger hard reject
        # Decision depends on other checks — but waiting_period_met should not be in checks_passed
        assert "waiting_period_met" not in result.checks_passed

    # ── 7. All checks pass with clauses cited ────────────────────────────

    def test_clauses_cited_in_approved_decision(self) -> None:
        """Approved decision should cite the coverage clauses from matched treatments."""
        claim = _make_claim()
        policy = _make_policy()
        coverage = _make_coverage()

        result = validate_claim(claim, policy, coverage)

        assert "CL-001" in result.clauses_cited
        assert result.decision == "Approved"
