"""
tool6_web_search.py - Supplemental web search tool for ClaimCopilot.
"""

import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

def search_medical_policies(query: str) -> list[dict]:
    """
    Performs a web search for medical policies, insurance coverage, and guidelines.
    Refines the query to ensure relevant results based on internal policy search rules.
    """
    # 1. Refine query to include mandatory keywords if missing
    keywords = ["insurance", "coverage", "medical policy", "guidelines"]
    query_lower = query.lower()
    
    missing_keywords = [k for k in keywords if k not in query_lower]
    
    refined_query = query
    if missing_keywords:
        refined_query = f"{query} {' '.join(missing_keywords)}"
    
    logger.info(f"Original search query: {query}")
    logger.info(f"Refined search query: {refined_query}")
    
    results = []
    try:
        # Use DDGS to perform the search
        with DDGS() as ddgs:
            # max_results=5 to keep it concise but informative
            ddgs_results = ddgs.text(refined_query, max_results=5)
            for r in ddgs_results:
                results.append({
                    "title": r.get("title", "No Title"),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", "No description available.")
                })
                
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return [{"error": True, "message": f"Web search failed: {str(e)}"}]

    if not results:
        return [{"message": "No relevant external policies found for this query."}]

    return results
