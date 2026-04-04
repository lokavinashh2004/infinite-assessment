"""
mcp_server.py — Official Model Context Protocol (MCP) Server for Claude Desktop.
"""

import sys
import logging
import os

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

# ── DO NOT import run_pipeline or retrieve_policy_rules here ──
# Those imports load sentence-transformers at module level, which takes
# 60+ seconds and causes the MCP initialize handshake to time out.

server = FastMCP("ClaimCopilot Server")

@server.tool(
    name="process_medical_claim",
    description="Extracts data from a medical bill document, runs RAG against policy docs, and returns a detailed adjudication decision."
)
def process_claim_tool(file_path: str) -> dict:
    """
    Takes the absolute file path to a medical claim document (PDF/Image).
    Example: 'C:/claims/my_bill.pdf'
    """
    try:
        # Lazy import — only loads when the tool is actually called
        from pipeline.tool_router import run_pipeline

        logger.info(f"Processing claim for file: {file_path}")
        if not os.path.exists(file_path):
            return {"error": f"File not found at: {file_path}"}

        return run_pipeline(file_path)
    except ImportError as e:
        logger.error(f"Failed to import pipeline: {e}")
        return {"error": f"Import error: {e}"}
    except Exception as e:
        logger.exception("Error in process_medical_claim tool")
        return {"error": str(e)}


@server.tool(
    name="query_policy_guidelines",
    description="Queries the vector store to find rules about specific medical treatments and claim types."
)
def query_policy_tool(treatments: list[str], claim_type: str) -> dict:
    """
    Search policy rules.
    treatments: list of medical procedures (e.g. ['X-Ray', 'Consultation']).
    claim_type: 'inpatient', 'outpatient', or 'daycare'.
    """
    try:
        # Lazy import — only loads when the tool is actually called
        from tools.tool3_rag_retriever import retrieve_policy_rules

        logger.info(f"Querying policy RAG for: {treatments} ({claim_type})")
        res = retrieve_policy_rules(treatments, claim_type)
        return {
            "query": res.query,
            "rules": [r.text for r in res.rules],
            "sources": list(set(r.source for r in res.rules))
        }
    except ImportError as e:
        logger.error(f"Failed to import RAG retriever: {e}")
        return {"error": f"Import error: {e}"}
    except Exception as e:
        logger.exception("Error in query_policy_guidelines tool")
        return {"error": str(e)}


if __name__ == "__main__":
    logger.info("Starting ClaimCopilot MCP Server. Listening on stdio...")
    server.run()