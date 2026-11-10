"""
Tool: search_web — Tavily Search API
Searches the web for blog posts, documentation, case studies, and current information.

Maps from brainstorm: tool_api_data_contracts.md (Tool 2).
"""

import logging
from typing import List

from tavily import AsyncTavilyClient

from app.config import settings
from app.models.schemas import WebSearchResult

logger = logging.getLogger(__name__)


async def search_web(query: str, max_results: int = 5) -> List[WebSearchResult]:
    """
    Search the web using Tavily API for up-to-date technical content.
    
    Args:
        query: Search query.
        max_results: Maximum number of results to return.
    
    Returns:
        List of WebSearchResult with title, URL, snippet, and relevance score.
    """
    if max_results < 1 or max_results > 10:
        raise ValueError("max_results must be between 1 and 10.")
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is required for web search.")

    try:
        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        response = await client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=False,
        )

        results = []
        for item in response.get("results", [])[:max_results]:
            results.append(WebSearchResult(
                title=str(item.get("title", ""))[:500],
                url=str(item.get("url", ""))[:2_048],
                content_snippet=str(item.get("content", ""))[:2_000],
                relevance_score=item.get("score", 0.0),
            ))

        logger.info("Web search returned %s results", len(results))
        return results

    except Exception as e:
        logger.error("Tavily search failed (%s)", type(e).__name__)
        raise RuntimeError(f"Tavily search failed ({type(e).__name__}).") from e
