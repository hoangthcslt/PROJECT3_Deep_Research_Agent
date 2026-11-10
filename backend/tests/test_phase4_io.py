import asyncio
import ipaddress

import httpx
import pymupdf as fitz
import pytest
from aiolimiter import AsyncLimiter

import app.tools.read_url as read_url_module
import app.tools.search_papers as search_papers_module
from app.tools.parse_pdf import PDFParseError
from app.tools.search_papers import ScholarRateLimitError

ORIGINAL_ASYNC_CLIENT = httpx.AsyncClient


def _pdf_bytes():
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Remote PDF text")
    content = doc.tobytes()
    doc.close()
    return content


def _install_transport(monkeypatch, module, handler):
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: ORIGINAL_ASYNC_CLIENT(*args, transport=transport, **kwargs),
    )


def _fresh_scholar_limiter(monkeypatch):
    monkeypatch.setattr(search_papers_module, "_scholar_limiter", AsyncLimiter(max_rate=15, time_period=60))


def _patch_addresses(monkeypatch, addresses_by_host):
    resolved = []

    async def resolve(host, _port):
        resolved.append(host)
        return [ipaddress.ip_address(value) for value in addresses_by_host[host]]

    monkeypatch.setattr(read_url_module, "_resolve_host_addresses", resolve)
    return resolved


def test_read_pdf_url_reuses_pinned_host_and_parses_bounded_pdf(monkeypatch):
    _patch_addresses(monkeypatch, {"papers.test": ["93.184.216.34"]})
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=_pdf_bytes(),
            request=request,
        )

    _install_transport(monkeypatch, read_url_module, handler)
    result = asyncio.run(read_url_module.read_pdf_url("https://papers.test/article.pdf"))

    assert result["full_text"] == "Remote PDF text"
    assert result["page_count"] == 1
    assert result["truncated"] is False
    assert requests[0].url.host == "93.184.216.34"
    assert requests[0].headers["host"] == "papers.test"
    assert requests[0].extensions["sni_hostname"] == "papers.test"


def test_read_pdf_url_revalidates_redirects_and_requires_pdf_media_type(monkeypatch):
    resolved = _patch_addresses(monkeypatch, {"public.test": ["8.8.8.8"]})
    requests = []

    def redirect(request):
        requests.append(request)
        return httpx.Response(302, headers={"location": "http://localhost/private.pdf"}, request=request)

    _install_transport(monkeypatch, read_url_module, redirect)
    with pytest.raises(PDFParseError, match="safely fetched"):
        asyncio.run(read_url_module.read_pdf_url("http://public.test/start.pdf"))
    assert resolved == ["public.test"]
    assert len(requests) == 1

    _patch_addresses(monkeypatch, {"public.test": ["8.8.8.8"]})
    _install_transport(
        monkeypatch,
        read_url_module,
        lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="not a PDF", request=request),
    )
    with pytest.raises(PDFParseError, match="safely fetched"):
        asyncio.run(read_url_module.read_pdf_url("http://public.test/page"))


def test_read_pdf_url_enforces_pdf_response_byte_limit(monkeypatch):
    _patch_addresses(monkeypatch, {"public.test": ["8.8.8.8"]})
    monkeypatch.setattr(read_url_module, "MAX_PDF_RESPONSE_BYTES", 16)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"x" * 17, request=request)

    _install_transport(monkeypatch, read_url_module, handler)
    with pytest.raises(PDFParseError, match="safely fetched"):
        asyncio.run(read_url_module.read_pdf_url("https://public.test/large.pdf"))
    assert len(calls) == 1


def test_search_papers_preserves_none_abstract_and_open_access_url(monkeypatch):
    _fresh_scholar_limiter(monkeypatch)
    paper = {
        "paperId": "paper-1",
        "title": "A research paper",
        "abstract": None,
        "authors": [{"name": "Author One"}],
        "citationCount": 12,
        "year": 2025,
        "url": "https://papers.test/paper-1",
        "openAccessPdf": {"url": "https://papers.test/paper-1.pdf"},
    }
    _install_transport(
        monkeypatch,
        search_papers_module,
        lambda request: httpx.Response(200, json={"data": [paper]}, request=request),
    )

    results = asyncio.run(search_papers_module.search_papers("research"))

    assert len(results) == 1
    assert results[0].abstract is None
    assert results[0].open_access_pdf == "https://papers.test/paper-1.pdf"
    assert results[0].authors == ["Author One"]


def test_search_papers_does_not_retry_rate_limits_or_hide_http_errors(monkeypatch):
    _fresh_scholar_limiter(monkeypatch)
    calls = []
    responses = [429, 503]

    def handler(request):
        calls.append(request)
        return httpx.Response(responses.pop(0), request=request)

    _install_transport(monkeypatch, search_papers_module, handler)

    async def run():
        with pytest.raises(ScholarRateLimitError):
            await search_papers_module.search_papers("research")
        with pytest.raises(httpx.HTTPStatusError):
            await search_papers_module.search_papers("research")

    asyncio.run(run())
    assert len(calls) == 2


def test_search_papers_separates_no_results_and_rejects_malformed_entries(monkeypatch):
    _fresh_scholar_limiter(monkeypatch)
    payloads = [{"data": []}, {"data": [{"paperId": "paper-1"}]}]
    _install_transport(
        monkeypatch,
        search_papers_module,
        lambda request: httpx.Response(200, json=payloads.pop(0), request=request),
    )

    async def run():
        assert await search_papers_module.search_papers("research") == []
        with pytest.raises(ValueError, match="ID or title"):
            await search_papers_module.search_papers("research")

    asyncio.run(run())
