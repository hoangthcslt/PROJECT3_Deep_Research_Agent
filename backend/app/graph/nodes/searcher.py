"""
Node 2: Multi-Source Searcher
Executes search queries across Semantic Scholar and Tavily based on
the approved research plan or knowledge gaps from previous loops.

Maps from brainstorm: agent_flow_state_machine.md (Node 2).
"""

import logging
from typing import Any, Dict

from app.graph.state import DeepResearchState
from app.models.budget import BudgetExhaustedError, SessionBudget
from app.models.schemas import SourceMetadata
from app.graph.errors import UserVisibleResearchError
from app.tools.search_papers import search_papers
from app.tools.search_web import search_web
from app.tools.source_ids import source_id_for_url

logger = logging.getLogger(__name__)
# Covers 8 supplied URLs + 3 uploads + 5 Quick queries × 5 results.
MAX_SOURCE_CANDIDATES = 40


async def searcher_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Execute search queries from pending sub-questions or knowledge gaps.
    Search only the providers enabled by the session mode. User-provided
    sources are already present in ``sources_found`` and remain candidates.
    Deduplicates results against existing sources_found.
    """
    logger.info("🔍 Searcher: Starting multi-source search...")

    loop_count = state.get("loop_count", 0)
    existing_urls = {
        s.url for s in state.get("sources_found", []) if s.url
    }

    new_sources: list[SourceMetadata] = []
    errors: list[str] = []
    budget = SessionBudget.model_validate(state.get("budget") or {})
    search_mode = state.get("search_mode", "web")

    if search_mode == "provided":
        if not state.get("sources_found"):
            raise UserVisibleResearchError("No supplied URLs or PDFs are available for this research.")
        return {"sources_found": [], "budget": budget.model_dump()}

    # ── Determine what to search ──
    if loop_count == 0:
        # First iteration: use research plan sub-questions
        queries = [
            (sq.question, sq.target_source, sq.id)
            for sq in state.get("research_plan", [])
            if sq.status == "pending"
        ]
    else:
        # Subsequent iterations: use knowledge gaps from reflector
        queries = [
            (gap.suggested_query, gap.target_source, f"gap_{i}")
            for i, gap in enumerate(state.get("knowledge_gaps", []))
        ]

    planned = {"web": 0, "academic": 0}
    for _query, source_type, _query_id in queries:
        if source_type not in planned:
            raise ValueError("Unsupported search provider in the approved plan.")
        if search_mode == "web" and source_type != "web":
            raise ValueError("The web search mode cannot run academic queries.")
        if search_mode == "academic" and source_type != "academic":
            raise ValueError("The academic search mode cannot run web queries.")
        planned[source_type] += 1
    remaining = {
        "web": budget.max_tavily_calls - budget.current_tavily_calls,
        "academic": budget.max_scholar_calls - budget.current_scholar_calls,
    }
    if any(planned[source] > remaining[source] for source in planned):
        raise BudgetExhaustedError("The approved plan exceeds the remaining search budget.")

    # ── Execute searches ──
    existing_ids = {source.source_id for source in state.get("sources_found", [])}

    source_errors: list[str] = []
    for query_text, source_type, query_id in queries:
        try:
            if not query_text.strip():
                continue
            if len(state.get("sources_found", [])) + len(new_sources) >= MAX_SOURCE_CANDIDATES:
                source_errors.append("Source candidate limit reached; additional results were skipped.")
                break

            if source_type == "academic":
                budget.increment_search("scholar")
                results = await search_papers(query_text[:500], max_results=5)
            else:
                budget.increment_search("tavily")
                results = await search_web(query_text[:500], max_results=5)
            added = 0
            for result in results:
                url = str(result.url or "").strip()
                title = str(result.title or "").strip()
                if not url.startswith(("http://", "https://")) or not title or url in existing_urls:
                    continue
                source_id = source_id_for_url(url)
                if source_id in existing_ids or len(state.get("sources_found", [])) + len(new_sources) >= MAX_SOURCE_CANDIDATES:
                    continue
                if source_type == "academic":
                    abstract = result.abstract
                    if abstract == "No abstract available":
                        abstract = None
                    open_access_pdf = result.open_access_pdf
                    kind = "abstract" if abstract else ("pdf_excerpt" if open_access_pdf else "abstract")
                    source_type_name = "paper"
                    credibility_tier = 1
                else:
                    abstract = result.content_snippet
                    open_access_pdf = None
                    kind = "webpage"
                    source_type_name = "webpage"
                    credibility_tier = _classify_credibility(url)
                new_sources.append(SourceMetadata(
                    source_id=source_id,
                    url=url,
                    title=title[:500],
                    authors=list(getattr(result, "authors", []) or []),
                    year=getattr(result, "year", None),
                    source_type=source_type_name,
                    content_snippet=str(abstract or "")[:2_000] or None,
                    credibility_tier=credibility_tier,
                    citation_count=getattr(result, "citation_count", None),
                    open_access_pdf=open_access_pdf,
                    content_kind=kind,
                    truncated=bool(abstract and len(str(abstract)) > 2_000),
                ))
                existing_urls.add(url)
                existing_ids.add(source_id)
                added += 1

            logger.info("Searcher: query %s returned %s usable web sources", query_id, added)

        except Exception as e:
            if isinstance(e, BudgetExhaustedError):
                raise
            error_msg = f"Search failed for question {query_id}; no source was added."
            logger.error("%s", error_msg)
            errors.append(error_msg)
            source_errors.append(error_msg)

    if not new_sources and not state.get("sources_found"):
        raise UserVisibleResearchError("No usable sources were found for this search mode.")

    logger.info(f"🔍 Searcher: Total new sources found: {len(new_sources)}")

    return {
        "sources_found": new_sources,
        "errors": errors,
        "source_errors": source_errors,
        "budget": budget.model_dump(),
    }


def _classify_credibility(url: str) -> int:
    """
    Classify source credibility based on domain.
    Tier 1: Academic (.edu, .gov, arxiv, ieee, acm)
    Tier 2: Official docs (github.com, official company blogs)
    Tier 3: Personal blogs, forums
    """
    url_lower = url.lower()

    tier_1_domains = [
        ".edu", ".gov", "arxiv.org", "ieee.org", "acm.org",
        "semanticscholar.org", "nature.com", "springer.com",
        "sciencedirect.com",
    ]
    tier_2_domains = [
        "github.com", "docs.", "cloud.google.com", "aws.amazon.com",
        "huggingface.co", "openai.com", "anthropic.com",
        "langchain.com",
    ]

    for domain in tier_1_domains:
        if domain in url_lower:
            return 1
    for domain in tier_2_domains:
        if domain in url_lower:
            return 2
    return 3
