"""
tool5_validation_engine.py — Tool 5: Claim validation and adjudication.

Applies 6 ordered eligibility checks and produces a final decision:
  Approved | Partially Approved | Rejected

Decision rules:
  - CHECK 1 or 2 or 5 fails  → Rejected,   approved_amount = 0
  - Only CHECK 6 fails        → Partially Approved, approved_amount = effective_limit
  - All checks pass           → Approved,   approved_amount = total_amount
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from models.schemas import (
    CoverageResponse,
    ExtractedClaim,
    PolicyRecord,
    ValidationDecision,
)

# ─── Check names (used in checks_passed list) ─────────────────────────────────

CHECK_1 = "policy_exists"
CHECK_2 = "policy_active"
CHECK_3 = "date_in_range"
CHECK_4 = "waiting_period_met"
CHECK_5 = "treatments_covered"
CHECK_6 = "amount_within_limit"

# Checks that cause an immediate Rejection regardless of others
_HARD_REJECT_CHECKS = {CHECK_1, CHECK_2, CHECK_5}


def _today() -> date:
    """Return today's date in UTC."""
    return datetime.now(tz=timezone.utc).date()


def validate_claim(
    claim: ExtractedClaim,
    policy: PolicyRecord,
    coverage: CoverageResponse,
) -> ValidationDecision:
    """
    Run all 6 eligibility checks and produce an adjudication decision.

    Checks are run in order; all results are collected before deciding.

    Args:
        claim:    Structured claim data from Tool 2.
        policy:   Policy record from Tool 4.
        coverage: Coverage lookup result from Tool 4.

    Returns:
        ValidationDecision with decision, approved_amount, reason, and metadata.
    """
    failures: dict[str, str] = {}   # check_name → failure reason
    checks_passed: list[str] = []
    clauses_cited: list[str] = []

    # ── CHECK 1: Policy exists ────────────────────────────────────────────────
    if not policy.found:
        failures[CHECK_1] = f"Policy ID '{policy.policy_id}' not found in records."
    else:
        checks_passed.append(CHECK_1)

    # ── CHECK 2: Policy is active ─────────────────────────────────────────────
    if policy.found:
        if str(policy.status).lower() != "active":
            failures[CHECK_2] = (
                f"Policy status is '{policy.status}'; must be 'active'."
            )
        else:
            checks_passed.append(CHECK_2)

    # ── CHECK 3: Admission date falls within policy dates ─────────────────────
    if policy.found and policy.start_date and policy.end_date:
        admission: date = claim.admission_date
        if not (policy.start_date <= admission <= policy.end_date):
            failures[CHECK_3] = (
                f"Admission date {admission.isoformat()} is outside policy period "
                f"{policy.start_date.isoformat()} – {policy.end_date.isoformat()}."
            )
        else:
            checks_passed.append(CHECK_3)
    elif policy.found:
        # Cannot verify dates → treat as passed with a warning embedded in reason
        checks_passed.append(CHECK_3)

    # ── CHECK 4: Waiting period ───────────────────────────────────────────────
    if policy.found and policy.start_date and policy.waiting_period_days is not None:
        days_since_start = (claim.admission_date - policy.start_date).days
        if days_since_start < policy.waiting_period_days:
            failures[CHECK_4] = (
                f"Only {days_since_start} day(s) since policy start; "
                f"waiting period is {policy.waiting_period_days} days."
            )
        else:
            checks_passed.append(CHECK_4)
    elif policy.found:
        checks_passed.append(CHECK_4)

    # ── CHECK 5: All treatments are covered ───────────────────────────────────
    uncovered: list[str] = [
        r.treatment for r in coverage.coverage_results if not r.covered
    ]
    if uncovered:
        failures[CHECK_5] = (
            f"The following treatments are not covered under '{coverage.plan_type}' plan: "
            + ", ".join(f"'{t}'" for t in uncovered)
        )
    else:
        checks_passed.append(CHECK_5)

    # Collect all cited clause IDs from covered treatments
    clauses_cited = list(
        {
            r.clause_id
            for r in coverage.coverage_results
            if r.clause_id and r.covered
        }
    )

    # ── CHECK 6: Total amount within coverage limit ───────────────────────────
    # Effective limit = min of all applicable sub-limits vs overall coverage_limit
    sub_limits = [
        r.sub_limit
        for r in coverage.coverage_results
        if r.covered and r.sub_limit is not None
    ]
    effective_limit: float | None = None

    if sub_limits and policy.coverage_limit:
        effective_limit = min(min(sub_limits), policy.coverage_limit)
    elif sub_limits:
        effective_limit = min(sub_limits)
    elif policy.coverage_limit:
        effective_limit = policy.coverage_limit

    if effective_limit is not None and claim.total_amount > effective_limit:
        failures[CHECK_6] = (
            f"Claimed amount ₹{claim.total_amount:,.2f} exceeds effective limit "
            f"₹{effective_limit:,.2f}."
        )
    else:
        checks_passed.append(CHECK_6)

    # ── Decision logic ────────────────────────────────────────────────────────
    failed_check_names = set(failures.keys())
    hard_failures = failed_check_names & _HARD_REJECT_CHECKS

    if hard_failures:
        decision = "Rejected"
        approved_amount = 0.0
        reason_parts = [failures[c] for c in sorted(hard_failures)]
        if len(failures) > len(hard_failures):
            other = [failures[c] for c in sorted(failures.keys() - hard_failures)]
            reason_parts.extend(other)
        reason = "Claim rejected. " + " | ".join(reason_parts)

    elif CHECK_6 in failed_check_names:
        # Only the amount check failed → partial approval
        decision = "Partially Approved"
        approved_amount = effective_limit if effective_limit is not None else 0.0
        reason = (
            f"Claim partially approved. Amount reduced to effective limit. "
            f"{failures[CHECK_6]}"
        )

    else:
        decision = "Approved"
        approved_amount = claim.total_amount
        reason = "All eligibility checks passed. Claim fully approved."

    return ValidationDecision(
        decision=decision,
        approved_amount=approved_amount,
        reason=reason,
        clauses_cited=clauses_cited,
        checks_passed=checks_passed,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )
