"""
tool4_structured_retriever.py — Tool 4: Structured data lookup.

Provides two functions:
  get_policy_record()  — read data/policies.csv and look up a policy by ID.
  get_coverage_rules() — read data/coverage_rules.json and match treatments
                         against coverage clauses by keyword matching.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import COVERAGE_JSON, POLICY_CSV
from models.schemas import CoverageResponse, CoverageResult, PolicyRecord

# ─── Caching (Loaded on first use) ─────────────────────────────────────────────

_policies_cache: pd.DataFrame | None = None
_coverage_cache: list[dict] | None = None

def _get_policies_df() -> pd.DataFrame:
    """Lazy-load the policies CSV into a cached DataFrame."""
    global _policies_cache
    if _policies_cache is None:
        csv_path = Path(POLICY_CSV)
        if not csv_path.exists():
            raise FileNotFoundError(f"Policy CSV not found: {csv_path}")
        try:
            df = pd.read_csv(str(csv_path), dtype=str)
            # Normalise column names once
            df.columns = [c.strip().lower() for c in df.columns]
            _policies_cache = df
        except Exception as exc:
            raise RuntimeError(f"Failed to read policies CSV: {exc}") from exc
    return _policies_cache

def _get_coverage_clauses() -> list[dict]:
    """Lazy-load the coverage rules JSON into a cached list."""
    global _coverage_cache
    if _coverage_cache is None:
        json_path = Path(COVERAGE_JSON)
        if not json_path.exists():
            raise FileNotFoundError(f"Coverage rules JSON not found: {json_path}")
        try:
            with open(str(json_path), "r", encoding="utf-8") as fh:
                _coverage_cache = json.load(fh)
        except Exception as exc:
            raise RuntimeError(f"Failed to read coverage rules JSON: {exc}") from exc
    return _coverage_cache


# ─── Policy record lookup ──────────────────────────────────────────────────────

def get_policy_record(policy_id: str) -> PolicyRecord:
    """
    Look up a policy record from data/policies.csv by its ID.

    Args:
        policy_id: The insurance policy identifier string to search for.

    Returns:
        PolicyRecord with all fields populated if found, or with found=False
        and all optional fields set to None if not found.

    Raises:
        FileNotFoundError: If data/policies.csv does not exist.
        RuntimeError: If the CSV cannot be parsed.
    """
    df = _get_policies_df()

    # Search case-insensitively
    mask = df["policy_id"].str.strip().str.upper() == policy_id.strip().upper()
    matched = df[mask]

    if matched.empty:
        return PolicyRecord(found=False, policy_id=policy_id)

    row = matched.iloc[0]

    def _safe_float(val: str | None) -> float | None:
        try:
            return float(str(val).replace(",", "").strip())
        except (ValueError, TypeError):
            return None

    def _safe_int(val: str | None) -> int | None:
        try:
            return int(str(val).strip())
        except (ValueError, TypeError):
            return None

    def _safe_date(val: str | None):
        """Parse a date string to a date object, or return None."""
        from datetime import date
        import re
        if not val or str(val).strip().lower() in ("nan", "none", ""):
            return None
        val = str(val).strip()
        # Try common formats
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                from datetime import datetime
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None

    return PolicyRecord(
        found=True,
        policy_id=row.get("policy_id", policy_id).strip(),
        holder_name=row.get("holder_name", None),
        status=row.get("status", None),
        plan_type=row.get("plan_type", None),
        coverage_limit=_safe_float(row.get("coverage_limit")),
        start_date=_safe_date(row.get("start_date")),
        end_date=_safe_date(row.get("end_date")),
        waiting_period_days=_safe_int(row.get("waiting_period_days")),
    )


# ─── Coverage rules lookup ─────────────────────────────────────────────────────

def get_coverage_rules(treatment: list[str], plan_type: str) -> CoverageResponse:
    """
    Match each treatment against coverage clauses read from data/coverage_rules.json.

    Matching logic:
      - For each treatment, scan every clause's keywords list.
      - A treatment is matched to a clause if ANY keyword is a substring of the
        treatment string (case-insensitive).
      - Coverage is True only if the treatment is matched AND the plan_type is in
        the clause's eligible_plans list.

    Args:
        treatment: List of treatment/procedure name strings from the claim.
        plan_type: Policy plan tier (e.g. "gold", "silver") to check eligibility.

    Returns:
        CoverageResponse with per-treatment coverage decisions.

    Raises:
        FileNotFoundError: If data/coverage_rules.json does not exist.
        RuntimeError: If the JSON cannot be parsed.
    """
    clauses = _get_coverage_clauses()

    plan_type_lower = plan_type.strip().lower()
    coverage_results: list[CoverageResult] = []

    for treatment_name in treatment:
        treatment_lower = treatment_name.strip().lower()
        matched_clause: dict | None = None

        # Find the first clause whose keywords match this treatment
        for clause in clauses:
            keywords: list[str] = [kw.lower() for kw in clause.get("keywords", [])]
            if any(kw in treatment_lower for kw in keywords):
                matched_clause = clause
                break

        if matched_clause is None:
            # No matching clause found → not covered
            coverage_results.append(
                CoverageResult(
                    treatment=treatment_name,
                    covered=False,
                    sub_limit=None,
                    clause_id=None,
                    notes="No matching coverage clause found for this treatment.",
                )
            )
        else:
            eligible_plans = [p.lower() for p in matched_clause.get("eligible_plans", [])]
            is_covered = plan_type_lower in eligible_plans

            coverage_results.append(
                CoverageResult(
                    treatment=treatment_name,
                    covered=is_covered,
                    sub_limit=float(matched_clause.get("sub_limit", 0)) if is_covered else None,
                    clause_id=matched_clause.get("clause_id"),
                    notes=matched_clause.get("notes"),
                )
            )

    return CoverageResponse(plan_type=plan_type, coverage_results=coverage_results)
