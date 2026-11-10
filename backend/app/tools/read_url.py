"""Fetch a bounded HTML page without allowing requests to internal addresses."""

import asyncio
import ipaddress
import logging
import socket
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from app.models.schemas import WebScrapeResult
from app.tools.parse_pdf import MAX_PDF_BYTES, PDFParseError, parse_pdf

logger = logging.getLogger(__name__)

MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 2_000_000
MAX_PDF_RESPONSE_BYTES = MAX_PDF_BYTES
MAX_FETCH_SECONDS = 30.0
MAX_CONTENT_CHARS = 50_000
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
NAT64_PREFIX = ipaddress.ip_network("64:ff9b::/96")


async def _resolve_host_addresses(host: str, port: int) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        records = await asyncio.get_running_loop().getaddrinfo(
            host, port, type=socket.SOCK_STREAM
        )
        return list(dict.fromkeys(ipaddress.ip_address(record[4][0]) for record in records))


def _is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if not address.is_global or address.is_multicast:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        embedded = [address.ipv4_mapped, address.sixtofour]
        if address.teredo:
            embedded.extend(address.teredo)
        if address in NAT64_PREFIX:
            embedded.append(ipaddress.IPv4Address(int(address) & 0xFFFFFFFF))
        if any(ip and (not ip.is_global or ip.is_multicast) for ip in embedded):
            return False
    return True


async def _validated_target(url: str) -> tuple[str, str, str]:
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise ValueError("Only HTTP(S) URLs with a hostname can be read")
    if parts.username is not None or parts.password is not None:
        raise ValueError("URLs containing credentials are not allowed")

    host = parts.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Localhost URLs are not allowed")
    host = host.encode("idna").decode("ascii")
    port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    addresses = await _resolve_host_addresses(host, port)
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise ValueError("URL must resolve only to public IP addresses")

    # The URL connects to the checked address; Host and TLS SNI retain the validated domain.
    # shortcut: try only the first public DNS answer, retry others if fetch failover becomes necessary.
    address = addresses[0].compressed
    authority = f"[{address}]" if ":" in address else address
    if parts.port is not None:
        authority += f":{parts.port}"
    pinned_url = urlunsplit((parts.scheme.lower(), authority, parts.path or "/", parts.query, ""))

    host_header = f"[{host}]" if ":" in host else host
    if parts.port is not None:
        host_header += f":{parts.port}"
    return pinned_url, host_header, host


async def _read_limited(response: httpx.Response, max_bytes: int = MAX_RESPONSE_BYTES) -> bytes:
    content_length = response.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError:
            declared_length = None
        if declared_length is not None and declared_length > max_bytes:
            raise ValueError("Page response exceeded the size limit")

    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > max_bytes:
            raise ValueError("Page response exceeded the size limit")
        chunks.append(chunk)
    return b"".join(chunks)


async def _fetch_page(
    url: str,
    *,
    allowed_content_types: set[str] | None = None,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> tuple[bytes, str]:
    accepted_types = allowed_content_types or {"text/html", "application/xhtml+xml", "text/plain"}
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        limits=httpx.Limits(max_keepalive_connections=0),
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "Deep Research Agent/1.0"},
    ) as client:
        current_url = url
        visited: set[str] = set()
        for redirects in range(MAX_REDIRECTS + 1):
            if current_url in visited:
                raise ValueError("Page redirect loop detected")
            visited.add(current_url)

            pinned_url, host_header, sni_hostname = await _validated_target(current_url)
            request = client.build_request(
                "GET",
                pinned_url,
                headers={"Host": host_header},
                extensions={"sni_hostname": sni_hostname},
            )
            response = await client.send(request, stream=True)
            try:
                if response.status_code in REDIRECT_STATUSES:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Page redirect is missing its destination")
                    if redirects == MAX_REDIRECTS:
                        raise ValueError("Page exceeded the redirect limit")
                    current_url = urljoin(current_url, location)
                    continue

                response.raise_for_status()
                media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if media_type not in accepted_types:
                    raise ValueError("Page has an unsupported content type")
                return await _read_limited(response, max_bytes), response.encoding or "utf-8"
            finally:
                await response.aclose()

    raise ValueError("Page exceeded the redirect limit")


async def read_url(url: str) -> WebScrapeResult:
    """Fetch and extract up to 50,000 characters from a public HTTP(S) page."""
    extracted_date = datetime.now(timezone.utc).isoformat()  # noqa: UP017 -- keep Python 3.10 support
    try:
        body, encoding = await asyncio.wait_for(_fetch_page(url), timeout=MAX_FETCH_SECONDS)
        soup = BeautifulSoup(body.decode(encoding, errors="replace"), "html.parser")
        for tag in soup(("script", "style", "nav", "footer", "header")):
            tag.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else "Untitled"
        text = soup.get_text(separator="\n", strip=True)[:MAX_CONTENT_CHARS]
        logger.info("Read public page (%d characters)", len(text))
        return WebScrapeResult(url=url, title=title or "Untitled", full_text=text, extracted_date=extracted_date)
    except (httpx.HTTPError, OSError, ValueError, UnicodeError, TimeoutError) as exc:
        logger.warning("Page read failed (%s)", type(exc).__name__)
        return WebScrapeResult(
            url=url,
            title="Error: Could not read page",
            full_text="",
            extracted_date=extracted_date,
        )


async def read_pdf_url(url: str) -> dict[str, object]:
    """Fetch a public PDF through the same pinned-address guard as HTML reads."""
    try:
        deadline = asyncio.get_running_loop().time() + MAX_FETCH_SECONDS
        body, _encoding = await asyncio.wait_for(
            _fetch_page(
                url,
                allowed_content_types={"application/pdf"},
                max_bytes=MAX_PDF_RESPONSE_BYTES,
            ),
            timeout=MAX_FETCH_SECONDS,
        )
        parsed = await asyncio.wait_for(
            asyncio.to_thread(parse_pdf, body),
            timeout=max(0, deadline - asyncio.get_running_loop().time()),
        )
        return {
            "full_text": parsed.full_text,
            "page_count": parsed.page_count,
            "metadata": parsed.metadata,
            "truncated": bool(parsed.metadata.get("truncated")),
        }
    except PDFParseError:
        raise
    except (httpx.HTTPError, OSError, ValueError, UnicodeError, TimeoutError) as exc:
        logger.warning("PDF read failed (%s)", type(exc).__name__)
        raise PDFParseError("PDF could not be safely fetched or parsed.") from exc
