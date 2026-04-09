"""
mcp_server.py — Official Model Context Protocol (MCP) Server for ClaimCopilot.
"""

import sys
import logging
import os
import base64
import tempfile
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("mcp_server")

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    logger.error("The 'mcp' package is not installed. Please run: pip install mcp[cli]")
    sys.exit(1)

# Initialize FastMCP server
server = FastMCP("ClaimCopilot Server")

# ─── TOOLS ────────────────────────────────────────────────────────────────────

@server.tool(
    name="process_medical_claim",
    description="Processes a medical claim document. Supports both local file paths and base64 encoded content."
)
def process_claim_tool(
    file_path: str = "",
    file_base64: str = "",
    file_name: str = "upload.pdf",
    mime_type: str = "application/pdf"
) -> dict:
    """
    Processes a claim. 
    Provide either file_path (if local) or file_base64 (preferred for Claude).
    """
    try:
        from pipeline.tool_router import run_pipeline
        import os

        # 1. Handle Base64 input
        if file_base64:
            ext = Path(file_name).suffix or (".pdf" if "pdf" in mime_type else ".png")
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext)
            try:
                with os.fdopen(tmp_fd, 'wb') as tmp:
                    tmp.write(base64.b64decode(file_base64))
                file_path = tmp_path
                logger.info(f"Decoded base64 to temp file: {file_path}")
            except Exception as e:
                return {"error": True, "message": f"Failed to decode base64: {e}", "type": "DecodeError"}
        
        # 2. Validate file_path
        if not file_path or not os.path.exists(file_path):
            return {"error": True, "message": f"File not found: {file_path}", "type": "FileNotFound"}

        # 3. Run pipeline
        result = run_pipeline(file_path)

        # 4. Archiving to SQLite (if result is valid)
        try:
            from models.db import save_record
            import uuid
            record_id = uuid.uuid4().hex[:8]
            claim_details = result.get("claim_details", {})
            patient_name = str(claim_details.get("patient_name", "unknown")) if isinstance(claim_details, dict) else "unknown"
            policy_id = result.get("policy_id", "unknown")
            
            # For base64, we have the bytes in memory (if we kept them)
            # For simplicity, we read the tmp file back if needed or just skip file_bytes if not provided
            save_record(
                record_id=record_id,
                patient_name=patient_name,
                policy_id=policy_id,
                original_filename=file_name,
                result=result,
                file_bytes=b"" # We can optimize this later
            )
        except Exception as archive_err:
            logger.warning(f"Archive failed: {archive_err}")

        # Cleanup tmp if used
        if file_base64 and os.path.exists(file_path):
            os.remove(file_path)

        return result

    except Exception as e:
        logger.exception("Error in process_medical_claim tool")
        return {"error": True, "message": str(e), "type": type(e).__name__}


@server.tool(
    name="query_policy_guidelines",
    description="Queries the vector store for rules about treatments and claim types."
)
def query_policy_tool(treatments: list[str], claim_type: str) -> dict:
    try:
        from tools.tool3_rag_retriever import retrieve_policy_rules
        res = retrieve_policy_rules(treatments, claim_type)
        return {
            "query": res.query,
            "rules": [r.text for r in res.rules],
            "sources": list(set(r.source for r in res.rules))
        }
    except Exception as e:
        return {"error": True, "message": str(e), "type": type(e).__name__}


@server.tool("summarize_claim")
def summarize_claim_tool(claim_result: dict) -> str:
    """Converts a complex claim result into a human-readable summary for agents."""
    try:
        decision = claim_result.get("decision", "Unknown")
        amount = claim_result.get("approved_amount", 0)
        reason = claim_result.get("reason", "No reason provided")
        patient = claim_result.get("patient_name", "Unknown")
        policy = claim_result.get("policy_id", "Unknown")
        
        summary = (
            f"📋 CLAIM SUMMARY REPORT\n"
            f"------------------------\n"
            f"Patient: {patient}\n"
            f"Policy:  {policy}\n"
            f"Status:  {decision.upper()}\n"
            f"Approved Amount: ₹{amount:,.2f}\n\n"
            f"Analysis:\n{reason}\n"
        )
        return summary
    except Exception as e:
        return f"Error generating summary: {e}"


@server.tool("batch_process_claims")
def batch_process_claims_tool(files: list[dict]) -> list[dict]:
    """Processes multiple claims concurrently. Each file dict: {'file_base64': '...', 'file_name': '...'}"""
    import concurrent.futures
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_file = {executor.submit(process_claim_tool, file_base64=f['file_base64'], file_name=f['file_name']): f for f in files}
        for future in concurrent.futures.as_completed(future_to_file):
            results.append(future.result())
    return results


@server.tool(
    name="searchMedicalPolicies",
    description="Refine and search for external medical policies, insurance coverage, and guidelines. Use results to support reasoning or add validation, but do NOT override internal decisions."
)
def search_medical_policies_tool(query: str) -> dict:
    """
    Search the web for medical policies. 
    Refines queries to include insurance, coverage, medical policy, or guidelines.
    """
    try:
        from tools.tool6_web_search import search_medical_policies
        results = search_medical_policies(query)
        return {
            "query": query,
            "results": results,
            "usage_rules": [
                "Use results only to support reasoning, provide explanation, or add external validation.",
                "DO NOT override internal policy decisions with web results."
            ]
        }
    except Exception as e:
        return {"error": True, "message": str(e), "type": type(e).__name__}



# ─── RESOURCES ────────────────────────────────────────────────────────────────

@server.resource("past-records://list")
def list_past_records() -> str:
    """Lists all successfully processed claim records from the database."""
    try:
        from models.db import get_connection
        conn = get_connection()
        rows = conn.execute("SELECT record_id, patient_name, created_at FROM claim_records ORDER BY created_at DESC").fetchall()
        conn.close()
        if not rows: return "No records found."
        return "\n".join(f"- {r['record_id']}: {r['patient_name']} ({r['created_at']})" for r in rows)
    except Exception as e:
        return f"Error listing records: {e}"

@server.resource("past-records://{record_id}/result")
def get_past_record_resource(record_id: str) -> str:
    """Retrieves the full JSON extraction result for a specific record ID."""
    try:
        from models.db import get_connection
        conn = get_connection()
        row = conn.execute("SELECT result_json FROM claim_records WHERE record_id = ?", (record_id,)).fetchone()
        conn.close()
        return row["result_json"] if row else "Record not found"
    except Exception as e:
        return f"Error retrieving record: {e}"

@server.resource("policy://{policy_id}")
def get_policy_resource(policy_id: str) -> str:
    """Retrieves structured policy metadata from the central policies CSV."""
    try:
        import pandas as pd
        from config import POLICY_CSV
        df = pd.read_csv(str(POLICY_CSV))
        row = df[df["policy_id"] == policy_id]
        return row.to_json(orient="records") if not row.empty else "Policy not found"
    except Exception as e:
        return f"Error retrieving policy: {e}"


# ─── PROMPTS ──────────────────────────────────────────────────────────────────

@server.prompt("evaluate_claim")
def evaluate_claim_prompt(file_path: str) -> list:
    """Template for initiating a claim evaluation."""
    return [{"role": "user", "content": f"Please process this medical claim document: {file_path}"}]

@server.prompt("query_policy")
def query_policy_prompt(treatment: str, plan: str) -> list:
    """Template for checking policy coverage rules."""
    return [{"role": "user", "content": f"What is the official policy regarding coverage for '{treatment}' under the '{plan}' plan?"}]

@server.prompt("review_past_claim")
def review_past_claim_prompt(record_id: str) -> list:
    """Template for reviewing a past adjudication decision."""
    return [{"role": "user", "content": f"Please provide a detailed review and summary of past claim decision: {record_id}"}]


# ─── RUN SERVER ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Ensure DB is ready
    try:
        from models.db import init_db
        init_db()
    except:
        pass

    logger.info("ClaimCopilot MCP Server booting with STDIO transport...")
    server.run(transport="stdio")