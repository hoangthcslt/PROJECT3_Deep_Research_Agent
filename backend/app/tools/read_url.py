"""
Tool: read_url — Jina Reader API with BeautifulSoup fallback
Scrapes full web page content into clean Markdown for LLM consumption.

Maps from brainstorm: tool_api_data_contracts.md (Tool 3).
"""

import logging
from datetime import datetime, timezone

import httpx

from app.models.schemas import WebScrapeResult

logger = logging.getLogger(__name__)

JINA_READER_BASE = "https://r.jina.ai/"


async def read_url(url: str) -> WebScrapeResult:
    """
    Read a web page and convert it to clean Markdown using Jina Reader API.
    Falls back to basic extraction if Jina fails.
    
    Args:
        url: The URL to read.
    
    Returns:
        WebScrapeResult with title and clean markdown text.
    """
    now = datetime.now(timezone.utc).isoformat()

    # ── Primary: Jina Reader API ──
    try:
        jina_url = f"{JINA_READER_BASE}{url}"
        headers = {
            "Accept": "application/json",
            "X-Return-Format": "markdown",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(jina_url, headers=headers)

            if response.status_code == 200:
                data = response.json().get("data", {})
                content = data.get("content", "")

                if content:
                    logger.info(f"📄 read_url('{url}') → {len(content)} chars via Jina")
                    return WebScrapeResult(
                        url=url,
                        title=data.get("title", "Untitled"),
                        full_text=content,
                        extracted_date=now,
                    )
    except Exception as e:
        logger.warning(f"⚠️ Jina Reader failed for {url}: {e}")

    # ── Fallback: Basic httpx + text extraction ──
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Deep Research Agent)"},
        ) as client:
            response = await client.get(url)

            if response.status_code == 200:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove script, style, nav elements
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()

                title = soup.title.string if soup.title else "Untitled"
                text = soup.get_text(separator="\n", strip=True)

                # Limit text length to avoid token overflow
                text = text[:50_000]

                logger.info(f"📄 read_url('{url}') → {len(text)} chars via fallback")
                return WebScrapeResult(
                    url=url,
                    title=title,
                    full_text=text,
                    extracted_date=now,
                )
    except Exception as e:
        logger.error(f"❌ Fallback scraping also failed for {url}: {e}")

    # ── Both failed ──
    return WebScrapeResult(
        url=url,
        title="Error: Could not read page",
        full_text="",
        extracted_date=now,
    )
