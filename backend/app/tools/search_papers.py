"""
Tool: search_papers — Semantic Scholar Academic Graph API
Searches for academic papers with metadata (title, abstract, authors, citations).

Maps from brainstorm: tool_api_data_contracts.md (Tool 1).
"""

import logging
from typing import List

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from aiolimiter import AsyncLimiter

from app.models.schemas import PaperSearchResult

logger = logging.getLogger(__name__)

# Rate limiter: max 15 requests/minute (safe margin under 100 req/5 min)
_scholar_limiter = AsyncLimiter(max_rate=15, time_period=60)

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "paperId,title,abstract,authors,citationCount,year,url,openAccessPdf"


class ScholarRateLimitError(Exception):
    """Raised when Semantic Scholar returns 429 Too Many Requests."""
    pass


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=16),
    retry=retry_if_exception_type(ScholarRateLimitError),
)
async def search_papers(query: str, max_results: int = 5) -> List[PaperSearchResult]:
    """
    Search Semantic Scholar for academic papers.
    
    Args:
        query: Search query (English recommended for best results).
        max_results: Maximum number of results to return.
    
    Returns:
        List of PaperSearchResult with metadata.
    """
    async with _scholar_limiter:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                SEMANTIC_SCHOLAR_API,
                params={
                    "query": query,
                    "limit": max_results,
                    "fields": FIELDS,
                },
            )

            if response.status_code == 429:
                raise ScholarRateLimitError(
                    "Semantic Scholar rate limit reached. Backing off..."
                )

            if response.status_code != 200:
                logger.warning(
                    f"Semantic Scholar returned {response.status_code}: {response.text[:200]}"
                )
                return []

            data = response.json().get("data", [])
            results = []

            for paper in data:
                authors = [
                    a["name"] for a in paper.get("authors", []) if "name" in a
                ]
                open_access = paper.get("openAccessPdf")
                pdf_url = open_access.get("url") if open_access else None

                results.append(PaperSearchResult(
                    paper_id=paper.get("paperId", ""),
                    title=paper.get("title", ""),
                    abstract=paper.get("abstract") or "No abstract available",
                    authors=authors,
                    citation_count=paper.get("citationCount", 0),
                    year=paper.get("year"),
                    url=paper.get("url") or f"https://www.semanticscholar.org/paper/{paper.get('paperId')}",
                    open_access_pdf=pdf_url,
                ))

            logger.info(f"📚 search_papers('{query}') → {len(results)} results")
            return results
