"""
Tool: search_web — Tavily Search API
Searches the web for blog posts, documentation, case studies, and current information.

Maps from brainstorm: tool_api_data_contracts.md (Tool 2).
"""

import logging
import os
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
    try:
        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        response = await client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=False,
        )

        results = []
        for item in response.get("results", []):
            results.append(WebSearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content_snippet=item.get("content", ""),
                relevance_score=item.get("score", 0.0),
            ))

        logger.info(f"🌐 search_web('{query}') → {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"❌ Tavily search failed: {str(e)}")
        return []
