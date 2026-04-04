"""
mcp_server.py — Official Model Context Protocol (MCP) Server for Claude Desktop.

This script runs a FastMCP stdio server, exposing the backend claim pipeline
and policy RAG system natively to Claude.
"""

import sys
import logging

# Ensure logs don't interfere with stdio which Claude uses to communicate
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    logging.error("The 'mcp' package is not installed. Please run: pip install mcp[cli]")
    sys.exit(1)

from mcp.tool_router import run_pipeline
from tools.tool3_rag_retriever import retrieve_policy_rules

# Create a FastMCP server instance
server = FastMCP("ClaimCopilot Server")

@server.tool(
    name="process_medical_claim",
    description="Extracts data from a medical bill document, runs RAG against policy docs, and returns a detailed adjudication decision."
)
def function_process_medical_claim(file_path: str) -> dict:
    """Takes the absolute file path to a medical claim document (PDF/Image)."""
    try:
        logging.info(f"Processing claim for file: {file_path}")
        return run_pipeline(file_path)
    except Exception as e:
        return {"error": str(e)}

@server.tool(
    name="query_policy_guidelines",
    description="Queries the ChromaDB vector store to find rules about specific medical treatments and claim types."
)
def function_query_policy_guidelines(treatments: list[str], claim_type: str) -> dict:
    """Search policy rules. treatments: list of medical procedures. claim_type: 'inpatient', 'outpatient', or 'daycare'."""
    try:
        logging.info(f"Querying policy RAG for: {treatments} ({claim_type})")
        res = retrieve_policy_rules(treatments, claim_type)
        return {
            "query": res.query,
            "rules": [r.text for r in res.rules]
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    logging.info("Starting ClaimCopilot MCP Server. Listening on stdio...")
    server.run()
