"""
mcp_server.py — Official Model Context Protocol (MCP) Server for Claude Desktop.

This script runs a FastMCP stdio server, exposing the backend claim pipeline
and policy RAG system natively to Claude.
"""

import sys
import logging
import os

# Redirect all standard logging to stderr to avoid corrupting MCP's stdout-based protocol
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

# Import the processing pipeline
try:
    from pipeline.tool_router import run_pipeline
    from tools.tool3_rag_retriever import retrieve_policy_rules
except ImportError as e:
    logger.error(f"Failed to import internal modules: {e}")
    sys.exit(1)

# Create a FastMCP server instance
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
        logger.info(f"Processing claim for file: {file_path}")
        if not os.path.exists(file_path):
            return {"error": f"File not found at: {file_path}"}
            
        return run_pipeline(file_path)
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
        logger.info(f"Querying policy RAG for: {treatments} ({claim_type})")
        res = retrieve_policy_rules(treatments, claim_type)
        return {
            "query": res.query,
            "rules": [r.text for r in res.rules],
            "sources": list(set(r.source for r in res.rules))
        }
    except Exception as e:
        logger.exception("Error in query_policy_guidelines tool")
        return {"error": str(e)}


if __name__ == "__main__":
    logger.info("Starting ClaimCopilot MCP Server. Listening on stdio...")
    server.run()
