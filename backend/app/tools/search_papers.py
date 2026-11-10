"""Search Semantic Scholar once and validate the returned paper metadata."""

import logging
from urllib.parse import quote, urlsplit

import httpx
from aiolimiter import AsyncLimiter

from app.models.schemas import PaperSearchResult

logger = logging.getLogger(__name__)

_scholar_limiter = AsyncLimiter(max_rate=15, time_period=60)
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "paperId,title,abstract,authors,citationCount,year,url,openAccessPdf"
MAX_QUERY_CHARS = 500
MAX_RESULTS = 100
MAX_TITLE_CHARS = 500
MAX_PAPER_ID_CHARS = 200
MAX_ABSTRACT_CHARS = 10_000
MAX_AUTHORS = 30
MAX_AUTHOR_CHARS = 200
MAX_URL_CHARS = 2_048


class ScholarRateLimitError(Exception):
    """Raised when Semantic Scholar returns 429 Too Many Requests."""


def _http_url(value: str) -> bool:
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() in {"http", "https"}
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and (port is None or 1 <= port <= 65535)
    )


async def search_papers(query: str, max_results: int = 5) -> list[PaperSearchResult]:
    """Search once; provider errors propagate so callers can account for failures."""
    if not isinstance(query, str):
        raise TypeError("Search query must be a string.")
    if not query.strip() or len(query) > MAX_QUERY_CHARS:
        raise ValueError("Search query must be a non-empty string of at most 500 characters.")
    if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= MAX_RESULTS:
        raise ValueError("max_results must be between 1 and 100.")

    async with _scholar_limiter, httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            SEMANTIC_SCHOLAR_API,
            params={"query": query.strip(), "limit": max_results, "fields": FIELDS},
        )
    if response.status_code == 429:
        raise ScholarRateLimitError("Semantic Scholar rate limit reached.")
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("Semantic Scholar returned malformed JSON.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise TypeError("Semantic Scholar returned malformed search data.")

    results: list[PaperSearchResult] = []
    for paper in payload["data"][:max_results]:
        if not isinstance(paper, dict):
            raise TypeError("Semantic Scholar returned a malformed paper entry.")
        paper_id, title = paper.get("paperId"), paper.get("title")
        if not isinstance(paper_id, str) or not paper_id.strip() or not isinstance(title, str) or not title.strip():
            raise ValueError("Semantic Scholar paper is missing its ID or title.")
        paper_id = paper_id.strip()
        if len(paper_id) > MAX_PAPER_ID_CHARS:
            raise ValueError("Semantic Scholar returned an invalid paper ID.")

        raw_abstract = paper.get("abstract")
        if raw_abstract is not None and not isinstance(raw_abstract, str):
            raise TypeError("Semantic Scholar returned a malformed paper abstract.")
        abstract = raw_abstract.strip()[:MAX_ABSTRACT_CHARS] if raw_abstract else None

        raw_authors = paper.get("authors")
        if raw_authors is None:
            raw_authors = []
        if not isinstance(raw_authors, list):
            raise TypeError("Semantic Scholar returned malformed paper authors.")
        authors: list[str] = []
        for author in raw_authors[:MAX_AUTHORS]:
            if not isinstance(author, dict) or not isinstance(author.get("name"), str):
                raise TypeError("Semantic Scholar returned a malformed paper author.")
            name = author["name"].strip()
            if name:
                authors.append(name[:MAX_AUTHOR_CHARS])

        citation_count = paper.get("citationCount")
        if citation_count is None:
            citation_count = 0
        if isinstance(citation_count, bool) or not isinstance(citation_count, int):
            raise TypeError("Semantic Scholar returned a malformed citation count.")
        if citation_count < 0:
            raise ValueError("Semantic Scholar returned a malformed citation count.")
        year = paper.get("year")
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            raise TypeError("Semantic Scholar returned a malformed publication year.")

        raw_url = paper.get("url")
        if raw_url is not None and not isinstance(raw_url, str):
            raise TypeError("Semantic Scholar returned an invalid paper URL.")
        url = raw_url.strip() if raw_url else ""
        if not url:
            url = f"https://www.semanticscholar.org/paper/{quote(paper_id.strip(), safe='')}"
        if len(url) > MAX_URL_CHARS or not _http_url(url):
            raise ValueError("Semantic Scholar returned an invalid paper URL.")

        open_access = paper.get("openAccessPdf")
        if open_access is not None and not isinstance(open_access, dict):
            raise TypeError("Semantic Scholar returned malformed open-access PDF metadata.")
        pdf_url = open_access.get("url") if open_access else None
        if pdf_url is not None and not isinstance(pdf_url, str):
            raise TypeError("Semantic Scholar returned an invalid open-access PDF URL.")
        if pdf_url is not None and (len(pdf_url) > MAX_URL_CHARS or not _http_url(pdf_url)):
            raise ValueError("Semantic Scholar returned an invalid open-access PDF URL.")

        results.append(PaperSearchResult(
            paper_id=paper_id,
            title=title.strip()[:MAX_TITLE_CHARS],
            abstract=abstract,
            authors=authors,
            citation_count=citation_count,
            year=year,
            url=url,
            open_access_pdf=pdf_url,
        ))

    logger.info("Semantic Scholar search returned %d results", len(results))
    return results
