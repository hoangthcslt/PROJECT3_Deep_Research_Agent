"""
Node 2: Multi-Source Searcher
Executes search queries across Semantic Scholar and Tavily based on
the approved research plan or knowledge gaps from previous loops.

Maps from brainstorm: agent_flow_state_machine.md (Node 2).
"""

import logging
from typing import Any, Dict

from app.graph.state import DeepResearchState
from app.models.schemas import SourceMetadata
from app.tools.search_papers import search_papers
from app.tools.search_web import search_web

logger = logging.getLogger(__name__)


async def searcher_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Execute search queries from pending sub-questions or knowledge gaps.
    Routes to appropriate search provider based on target_source.
    Deduplicates results against existing sources_found.
    """
    logger.info("🔍 Searcher: Starting multi-source search...")

    loop_count = state.get("loop_count", 0)
    existing_urls = {
        s.url for s in state.get("sources_found", []) if s.url
    }

    new_sources: list[SourceMetadata] = []
    errors: list[str] = []

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

    # ── Execute searches ──
    ref_counter = len(state.get("sources_found", []))

    for query_text, source_type, query_id in queries:
        try:
            if source_type == "academic":
                results = await search_papers(query_text, max_results=5)
                for r in results:
                    if r.url not in existing_urls:
                        ref_counter += 1
                        new_sources.append(SourceMetadata(
                            source_id=f"REF_{ref_counter}",
                            url=r.url,
                            title=r.title,
                            authors=r.authors,
                            year=r.year,
                            source_type="paper",
                            content_snippet=r.abstract,
                            credibility_tier=1,
                            citation_count=r.citation_count,
                        ))
                        existing_urls.add(r.url)

            elif source_type == "web":
                results = await search_web(query_text, max_results=5)
                for r in results:
                    if r.url not in existing_urls:
                        ref_counter += 1
                        new_sources.append(SourceMetadata(
                            source_id=f"REF_{ref_counter}",
                            url=r.url,
                            title=r.title,
                            authors=[],
                            year=None,
                            source_type="webpage",
                            content_snippet=r.content_snippet,
                            credibility_tier=_classify_credibility(r.url),
                        ))
                        existing_urls.add(r.url)

            logger.info(f"🔍 Searcher: '{query_text}' ({source_type}) → {len(results)} results")

        except Exception as e:
            error_msg = f"Search failed for '{query_text}': {str(e)}"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)

    logger.info(f"🔍 Searcher: Total new sources found: {len(new_sources)}")

    return {
        "sources_found": new_sources,
        "errors": errors,
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
