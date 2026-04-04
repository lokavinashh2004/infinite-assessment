"""
tool_router.py — MCP pipeline orchestrator.

Wires Tools 1-5 into a sequential pipeline and returns a merged FinalResponse.
Tools 3 and 4 are executed concurrently using concurrent.futures.ThreadPoolExecutor
since they are independent retrieval operations.
"""

from __future__ import annotations

import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path

from claim_copilot.models.schemas import (
    CoverageResponse,
    ExtractedClaim,
    FinalResponse,
    RAGResult,
    ValidationDecision,
)
from claim_copilot.tools.tool1_file_reader import read_file
from claim_copilot.tools.tool2_data_extractor import extract_claim_data
from claim_copilot.tools.tool3_rag_retriever import retrieve_policy_rules
from claim_copilot.tools.tool4_structured_retriever import (
    get_coverage_rules,
    get_policy_record,
)
from claim_copilot.tools.tool5_validation_engine import validate_claim


def run_pipeline(file_path: str) -> dict:
    """
    Execute the full 5-tool MCP claim processing pipeline.

    Steps:
      1. Tool 1 — Read and extract raw text from the document.
      2. Tool 2 — Use Groq AI to extract structured claim fields.
      3. Tool 3 + Tool 4 — Retrieve policy rules (RAG) and policy record/
                            coverage rules (structured) in parallel.
      4. Tool 5 — Validate the claim and produce a final adjudication decision.

    Args:
        file_path: Absolute path to the uploaded claim document (PDF or image).

    Returns:
        Dictionary matching the FinalResponse schema, ready for JSON serialisation.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: On extraction or validation failures.
        RuntimeError: On infrastructure failures (vector store, Groq API, etc.).
    """
    execution_log: list[str] = []

    def _log(msg: str) -> None:
        """Append a timestamped message to the execution log."""
        ts = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
        execution_log.append(f"[{ts}] {msg}")

    # ── STEP 1: File reading ───────────────────────────────────────────────────
    _log("STEP 1: Reading document …")
    try:
        file_result = read_file(file_path)
        _log(
            f"STEP 1 ✓ — '{file_result.file_name}' ({file_result.file_type}), "
            f"{file_result.char_count:,} characters extracted. Status: {file_result.status}"
        )
    except Exception as exc:
        _log(f"STEP 1 ✗ — {exc}")
        raise

    # ── STEP 2: Claim data extraction via Groq ─────────────────────────────────
    _log("STEP 2: Extracting structured claim data via Groq AI …")
    try:
        claim: ExtractedClaim = extract_claim_data(file_result.raw_text)
        _log(
            f"STEP 2 ✓ — policy_id='{claim.policy_id}', patient='{claim.patient_name}', "
            f"total_amount=₹{claim.total_amount:,.2f}, claim_type='{claim.claim_type}'"
        )
    except Exception as exc:
        _log(f"STEP 2 ✗ — {exc}")
        raise

    # ── STEP 3 + STEP 4 (parallel): RAG retrieval + structured lookup ──────────
    _log("STEP 3+4: Retrieving policy rules (RAG) and policy record (parallel) …")

    rag_result: RAGResult | None = None
    rag_error: str | None = None

    def _run_rag() -> RAGResult:
        return retrieve_policy_rules(
            treatment=claim.treatment,
            claim_type=claim.claim_type,
        )

    def _run_structured() -> tuple:
        policy_rec = get_policy_record(claim.policy_id)
        plan_type = policy_rec.plan_type or "unknown"
        coverage_resp = get_coverage_rules(
            treatment=claim.treatment,
            plan_type=plan_type,
        )
        return policy_rec, coverage_resp

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        rag_future = executor.submit(_run_rag)
        struct_future = executor.submit(_run_structured)

        try:
            rag_result = rag_future.result()
            _log(
                f"STEP 3 ✓ — Retrieved {len(rag_result.rules)} RAG rule chunk(s) "
                f"for query: '{rag_result.query[:80]}'"
            )
        except Exception as exc:
            rag_error = str(exc)
            _log(
                f"STEP 3 ⚠ — RAG retrieval failed (non-fatal, continuing): {exc}"
            )
            # RAG failure is non-fatal; create an empty result
            from claim_copilot.models.schemas import RAGResult
            rag_result = RAGResult(query="", rules=[])

        try:
            policy_record, coverage_response = struct_future.result()
            _log(
                f"STEP 4 ✓ — Policy found={policy_record.found}, "
                f"status={policy_record.status!r}, plan={policy_record.plan_type!r}. "
                f"Coverage results: {len(coverage_response.coverage_results)} treatment(s) checked."
            )
        except Exception as exc:
            _log(f"STEP 4 ✗ — {exc}")
            raise

    # ── STEP 4: Validation ─────────────────────────────────────────────────────
    _log("STEP 5: Running validation engine …")
    try:
        decision: ValidationDecision = validate_claim(
            claim=claim,
            policy=policy_record,
            coverage=coverage_response,
        )
        _log(
            f"STEP 5 ✓ — Decision: '{decision.decision}', "
            f"Approved amount: ₹{decision.approved_amount:,.2f}"
        )
    except Exception as exc:
        _log(f"STEP 5 ✗ — {exc}")
        raise

    # ── Build final merged response ────────────────────────────────────────────
    rag_rules_used = [r.text[:120] for r in rag_result.rules] if rag_result else []

    final = FinalResponse(
        decision=decision.decision,
        approved_amount=decision.approved_amount,
        reason=decision.reason,
        clauses_cited=decision.clauses_cited,
        checks_passed=decision.checks_passed,
        policy_id=claim.policy_id,
        patient_name=claim.patient_name,
        total_claimed=claim.total_amount,
        execution_log=execution_log,
        rag_rules_used=rag_rules_used,
        timestamp=decision.timestamp,
    )

    return final.model_dump()
