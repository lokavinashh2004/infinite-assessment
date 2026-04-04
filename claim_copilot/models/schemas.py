"""
schemas.py — Pydantic v2 data models for the Medical Insurance Claim Processing pipeline.

Defines all structured types used across tools, the MCP router, and the API layer.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# ─── Tool 1 output ────────────────────────────────────────────────────────────

class FileReadResult(BaseModel):
    """Result returned by tool1_file_reader after extracting text from a document."""

    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="Detected MIME type or extension")
    raw_text: str = Field(..., description="Extracted plain text content")
    char_count: int = Field(..., ge=0, description="Number of characters in raw_text")
    status: str = Field(..., description="'ok' or an informational note")


# ─── Tool 2 output ────────────────────────────────────────────────────────────

class ItemizedCost(BaseModel):
    """A single line-item from the medical bill."""

    item: str = Field(..., description="Description of the service or product")
    cost: float = Field(..., ge=0, description="Cost in INR")


class ExtractedClaim(BaseModel):
    """Structured claim data extracted from the raw document text by Groq."""

    policy_id: str = Field(..., description="Insurance policy identifier")
    patient_name: str = Field(..., description="Full name of the patient")
    patient_age: int = Field(..., ge=0, le=150, description="Patient age in years")
    hospital_name: str = Field(..., description="Name of the treating hospital")
    admission_date: date = Field(..., description="Date of hospital admission (YYYY-MM-DD)")
    discharge_date: date = Field(..., description="Date of hospital discharge (YYYY-MM-DD)")
    diagnosis: list[str] = Field(default_factory=list, description="List of diagnosed conditions")
    treatment: list[str] = Field(default_factory=list, description="List of treatments/procedures performed")
    total_amount: float = Field(..., ge=0, description="Total claimed amount in INR")
    itemized_costs: list[ItemizedCost] = Field(default_factory=list, description="Line-item cost breakdown")
    doctor_name: str = Field(..., description="Name of the primary treating physician")
    claim_type: str = Field(..., description="One of: inpatient | outpatient | daycare")

    @field_validator("claim_type")
    @classmethod
    def validate_claim_type(cls, v: str) -> str:
        """Ensure claim_type is one of the accepted values."""
        allowed = {"inpatient", "outpatient", "daycare"}
        if v.lower() not in allowed:
            raise ValueError(f"claim_type must be one of {allowed}, got: {v!r}")
        return v.lower()

    @field_validator("discharge_date")
    @classmethod
    def discharge_after_admission(cls, v: date, info: Any) -> date:
        """Discharge date must not be before admission date."""
        admission = info.data.get("admission_date")
        if admission and v < admission:
            raise ValueError("discharge_date must be >= admission_date")
        return v


# ─── Tool 3 output ────────────────────────────────────────────────────────────

class RAGRuleItem(BaseModel):
    """A single retrieved policy rule chunk from the vector store."""

    text: str = Field(..., description="Retrieved document chunk text")
    source: str = Field(..., description="Source PDF filename")
    relevance_rank: int = Field(..., ge=1, description="1 = most relevant")


class RAGResult(BaseModel):
    """Full result from the RAG retriever tool."""

    query: str = Field(..., description="Query string used for retrieval")
    rules: list[RAGRuleItem] = Field(default_factory=list, description="Ranked list of retrieved rules")


# ─── Tool 4 output ────────────────────────────────────────────────────────────

class PolicyRecord(BaseModel):
    """Structured policy record retrieved from policies.csv."""

    found: bool = Field(..., description="True if the policy_id was found in the CSV")
    policy_id: str = Field(..., description="Policy identifier")
    holder_name: Optional[str] = Field(None, description="Name of the policyholder")
    status: Optional[str] = Field(None, description="Policy status: active | lapsed | expired")
    plan_type: Optional[str] = Field(None, description="Plan tier: gold | silver | bronze")
    coverage_limit: Optional[float] = Field(None, ge=0, description="Maximum coverage amount in INR")
    start_date: Optional[date] = Field(None, description="Policy start date")
    end_date: Optional[date] = Field(None, description="Policy end date")
    waiting_period_days: Optional[int] = Field(None, ge=0, description="Waiting period before coverage activates")


class CoverageResult(BaseModel):
    """Coverage decision for a single treatment item."""

    treatment: str = Field(..., description="Treatment name as submitted")
    covered: bool = Field(..., description="Whether the treatment is covered under the plan")
    sub_limit: Optional[float] = Field(None, description="Sub-limit for this treatment in INR")
    clause_id: Optional[str] = Field(None, description="Matched policy clause identifier")
    notes: Optional[str] = Field(None, description="Additional notes from the clause")


class CoverageResponse(BaseModel):
    """Full coverage lookup result for all submitted treatments."""

    plan_type: str = Field(..., description="Plan type used for matching")
    coverage_results: list[CoverageResult] = Field(
        default_factory=list, description="Per-treatment coverage decisions"
    )


# ─── Tool 5 output ────────────────────────────────────────────────────────────

class ValidationDecision(BaseModel):
    """Final adjudication decision produced by the validation engine."""

    decision: str = Field(..., description="Approved | Partially Approved | Rejected")
    approved_amount: float = Field(..., ge=0, description="Amount approved for reimbursement in INR")
    reason: str = Field(..., description="Human-readable explanation of the decision")
    clauses_cited: list[str] = Field(default_factory=list, description="Policy clause IDs referenced")
    checks_passed: list[str] = Field(default_factory=list, description="Names of checks that passed")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of the decision")


# ─── Pipeline final output ─────────────────────────────────────────────────────

class FinalResponse(BaseModel):
    """Merged response returned by the MCP router after running the full pipeline."""

    # Decision fields (from Tool 5)
    decision: str = Field(..., description="Approved | Partially Approved | Rejected")
    approved_amount: float = Field(..., ge=0, description="Amount approved for reimbursement in INR")
    reason: str = Field(..., description="Human-readable explanation of the decision")
    clauses_cited: list[str] = Field(default_factory=list, description="Policy clause IDs referenced")
    checks_passed: list[str] = Field(default_factory=list, description="Names of validation checks that passed")

    # Claim summary fields (from Tool 2)
    policy_id: str = Field(..., description="Policy ID from the claim document")
    patient_name: str = Field(..., description="Patient name from the claim document")
    total_claimed: float = Field(..., ge=0, description="Total amount claimed as per the document")

    # Execution metadata
    execution_log: list[str] = Field(default_factory=list, description="Step-by-step execution log")
    rag_rules_used: list[str] = Field(
        default_factory=list,
        description="First 120 characters of each RAG-retrieved rule used in processing",
    )
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of the pipeline completion")
