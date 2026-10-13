import logging
from typing import List, Dict, Any
from app.core.config import MAX_SEARCH_RESULTS

logger = logging.getLogger(__name__)

def perform_web_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """Searches the web using ddgs and returns top results with title, link, and concise snippet."""
    results = []
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        raw_results = list(ddgs.text(query, max_results=max_results))
        for r in raw_results:
            body = r.get("body", "").strip()
            snippet = body[:180] + ("..." if len(body) > 180 else "")
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": snippet
            })
    except Exception as e:
        logger.warning(f"Web search error: {e}. Trying fallback...")
        try:
            from duckduckgo_search import DDGS as FallbackDDGS
            fallback_ddgs = FallbackDDGS()
            raw_results = list(fallback_ddgs.text(query, max_results=max_results))
            for r in raw_results:
                body = r.get("body", "").strip()
                snippet = body[:180] + ("..." if len(body) > 180 else "")
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": snippet
                })
        except Exception as e2:
            logger.error(f"Fallback search also failed: {e2}")

    return results

def format_search_context(results: List[Dict[str, str]]) -> str:
    """Formats search results into a clean, concise grounding prompt for CPU efficiency."""
    if not results:
        return ""
    
    formatted = "### Web Search Context:\n"
    for i, r in enumerate(results[:3], 1):
        clean_snip = r['snippet'].replace('\n', ' ')
        formatted += f"[{i}] {r['title']}: {clean_snip}\n"
    
    formatted += "Answer clearly grounded in these facts when relevant, citing [1], [2].\n"
    return formatted
