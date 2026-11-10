import asyncio
import ipaddress
import json
import math

import httpx
import pytest

import app.services.embedding_service as embedding_module
import app.tools.read_url as read_url_module


def _install_transport(monkeypatch, module, handler):
    client_type = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: client_type(*args, transport=transport, **kwargs),
    )


def _patch_addresses(monkeypatch, addresses_by_host):
    resolved = []

    async def resolve(host, _port):
        resolved.append(host)
        return [ipaddress.ip_address(value) for value in addresses_by_host[host]]

    monkeypatch.setattr(read_url_module, "_resolve_host_addresses", resolve)
    return resolved


def test_read_url_rejects_unsafe_urls_before_http_request(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="Should not be read", request=request)

    _install_transport(monkeypatch, read_url_module, handler)

    for url in (
        "file:///etc/passwd",
        "ftp://example.com/page",
        "https://user:secret@example.com/",
        "http://localhost/admin",
        "http://127.0.0.1/admin",
        "http://[::1]/admin",
        "http://[::ffff:10.0.0.1]/admin",
        "http://[64:ff9b::a00:1]/admin",
        "http://[2002:a00:1::]/admin",
        "http://[2001:0:a00:1::]/admin",
        "http://224.0.0.1/",
    ):
        result = asyncio.run(read_url_module.read_url(url))
        assert result.full_text == ""
        assert result.title.startswith("Error:")
    assert calls == []


def test_read_url_rejects_mixed_public_and_private_dns_answers(monkeypatch):
    resolved = _patch_addresses(monkeypatch, {"mixed.test": ["8.8.8.8", "10.0.0.2"]})
    calls = []
    _install_transport(monkeypatch, read_url_module, lambda request: calls.append(request))

    result = asyncio.run(read_url_module.read_url("https://mixed.test/article"))

    assert result.full_text == ""
    assert resolved == ["mixed.test"]
    assert calls == []


def test_read_url_pins_dns_ip_and_keeps_host_and_tls_sni(monkeypatch):
    _patch_addresses(monkeypatch, {"example.test": ["93.184.216.34"]})
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<title>Article</title><nav>Skip</nav><p>Readable text</p><script>bad()</script>",
            request=request,
        )

    _install_transport(monkeypatch, read_url_module, handler)
    result = asyncio.run(read_url_module.read_url("https://example.test/story"))

    assert result.title == "Article"
    assert result.full_text == "Article\nReadable text"
    assert len(seen) == 1
    assert seen[0].url.host == "93.184.216.34"
    assert seen[0].headers["host"] == "example.test"
    assert seen[0].extensions["sni_hostname"] == "example.test"


def test_read_url_revalidates_redirect_before_connecting(monkeypatch):
    resolved = _patch_addresses(monkeypatch, {"public.test": ["8.8.8.8"]})
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            302,
            headers={"location": "http://localhost/private"},
            request=request,
        )

    _install_transport(monkeypatch, read_url_module, handler)
    result = asyncio.run(read_url_module.read_url("http://public.test/start"))

    assert result.full_text == ""
    assert resolved == ["public.test"]
    assert len(calls) == 1


def test_read_url_rejects_private_redirect_dns_answer(monkeypatch):
    resolved = _patch_addresses(
        monkeypatch,
        {"public.test": ["8.8.8.8"], "private.test": ["10.0.0.7"]},
    )
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            302,
            headers={"location": "http://private.test/admin"},
            request=request,
        )

    _install_transport(monkeypatch, read_url_module, handler)
    result = asyncio.run(read_url_module.read_url("http://public.test/start"))

    assert result.full_text == ""
    assert resolved == ["public.test", "private.test"]
    assert len(calls) == 1


def test_read_url_bounds_response_bytes_and_rejects_binary_content(monkeypatch):
    _patch_addresses(monkeypatch, {"example.test": ["8.8.8.8"]})

    def handler(request):
        if request.url.path.endswith(".pdf"):
            return httpx.Response(
                200, headers={"content-type": "application/pdf"}, content=b"%PDF", request=request
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"x" * (read_url_module.MAX_RESPONSE_BYTES + 1),
            request=request,
        )

    _install_transport(monkeypatch, read_url_module, handler)
    oversized = asyncio.run(read_url_module.read_url("http://example.test/large"))
    binary = asyncio.run(read_url_module.read_url("http://example.test/file.pdf"))

    assert oversized.full_text == ""
    assert binary.full_text == ""
    assert oversized.title.startswith("Error:")
    assert binary.title.startswith("Error:")


def test_read_url_bounds_redirect_count(monkeypatch):
    _patch_addresses(monkeypatch, {"example.test": ["8.8.8.8"]})
    calls = []

    def handler(request):
        calls.append(request)
        hop = int(request.url.path.rsplit("/", 1)[-1])
        return httpx.Response(
            302,
            headers={"location": f"/hop/{hop + 1}"},
            request=request,
        )

    _install_transport(monkeypatch, read_url_module, handler)
    result = asyncio.run(read_url_module.read_url("http://example.test/hop/0"))

    assert result.full_text == ""
    assert len(calls) == read_url_module.MAX_REDIRECTS + 1


def test_read_url_bounds_fetch_time(monkeypatch):
    monkeypatch.setattr(read_url_module, "MAX_FETCH_SECONDS", 0.001)

    async def slow_fetch(_url):
        await asyncio.sleep(1)

    monkeypatch.setattr(read_url_module, "_fetch_page", slow_fetch)
    result = asyncio.run(read_url_module.read_url("https://example.test/slow"))

    assert result.full_text == ""
    assert result.title.startswith("Error:")


def _embedding_payload(count, value=(3.0, 4.0)):
    return {
        "embeddings": [
            {"values": [*value, *([0.0] * (embedding_module.VECTOR_SIZE - len(value)))]}
            for _ in range(count)
        ]
    }


def test_embedding_rest_request_uses_document_and_query_tasks_and_normalizes(monkeypatch):
    monkeypatch.setattr(embedding_module.settings, "google_api_key", "test-secret")
    monkeypatch.setattr(embedding_module.settings, "embedding_model", "models/gemini-embedding-001")
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            json=_embedding_payload(len(json.loads(request.content)["requests"])),
            request=request,
        )

    _install_transport(monkeypatch, embedding_module, handler)
    service = embedding_module.EmbeddingService()
    documents = asyncio.run(service.embed_texts(["doc one", "doc two"]))
    query = asyncio.run(service.embed_single("query"))

    assert len(documents) == 2
    assert len(query) == embedding_module.VECTOR_SIZE
    assert math.isclose(math.sqrt(sum(value * value for value in documents[0])), 1.0)
    assert documents[0][:2] == pytest.approx([0.6, 0.8])
    assert query[:2] == pytest.approx([0.6, 0.8])
    assert [json.loads(request.content)["requests"][0]["taskType"] for request in seen] == [
        "RETRIEVAL_DOCUMENT",
        "RETRIEVAL_QUERY",
    ]
    body = json.loads(seen[0].content)
    assert body["requests"][0]["model"] == "models/gemini-embedding-001"
    assert body["requests"][0]["outputDimensionality"] == 768
    assert seen[0].headers["x-goog-api-key"] == "test-secret"
    assert "test-secret" not in str(seen[0].url)


def test_embedding_splits_batches_at_provider_limit(monkeypatch):
    monkeypatch.setattr(embedding_module.settings, "google_api_key", "test-secret")
    monkeypatch.setattr(embedding_module.settings, "embedding_model", "gemini-embedding-001")
    batch_sizes = []

    def handler(request):
        count = len(json.loads(request.content)["requests"])
        batch_sizes.append(count)
        return httpx.Response(200, json=_embedding_payload(count, (1.0,)), request=request)

    _install_transport(monkeypatch, embedding_module, handler)
    result = asyncio.run(embedding_module.EmbeddingService().embed_texts([f"doc {i}" for i in range(101)]))

    assert batch_sizes == [100, 1]
    assert len(result) == 101


def test_embedding_rejects_unsafe_configured_model_path(monkeypatch):
    monkeypatch.setattr(embedding_module.settings, "google_api_key", "test-secret")
    monkeypatch.setattr(
        embedding_module.settings, "embedding_model", "gemini-embedding-001/../../other"
    )
    calls = []
    _install_transport(monkeypatch, embedding_module, lambda request: calls.append(request))

    with pytest.raises(ValueError, match="model name is invalid"):
        asyncio.run(embedding_module.EmbeddingService().embed_single("query"))
    assert calls == []


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "malformed"),
        ({"embeddings": []}, "different number"),
        ({"embeddings": [{"values": [1.0] * 767}]}, "exactly 768"),
        ({"embeddings": [{"values": [0.0] * 768}]}, "zero or invalid"),
        ({"embeddings": [{"values": [1e308] * 768}]}, "zero or invalid"),
    ],
)
def test_embedding_rejects_malformed_or_invalid_vectors(monkeypatch, payload, message):
    monkeypatch.setattr(embedding_module.settings, "google_api_key", "test-secret")
    monkeypatch.setattr(embedding_module.settings, "embedding_model", "gemini-embedding-001")
    _install_transport(
        monkeypatch,
        embedding_module,
        lambda request: httpx.Response(200, json=payload, request=request),
    )

    with pytest.raises(ValueError, match=message):
        asyncio.run(embedding_module.EmbeddingService().embed_single("query"))


def test_embedding_rejects_non_finite_values():
    with pytest.raises(ValueError, match="non-finite"):
        embedding_module._validated_embeddings(
            {"embeddings": [{"values": [float("nan")] + [0.0] * 767}]}, 1
        )


def test_embedding_provider_failure_propagates_without_zero_fallback(monkeypatch):
    monkeypatch.setattr(embedding_module.settings, "google_api_key", "test-secret")
    monkeypatch.setattr(embedding_module.settings, "embedding_model", "gemini-embedding-001")
    _install_transport(
        monkeypatch,
        embedding_module,
        lambda request: httpx.Response(503, text="unavailable", request=request),
    )

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(embedding_module.EmbeddingService().embed_single("query"))


def test_embedding_rejects_blank_and_non_string_text_without_network(monkeypatch):
    monkeypatch.setattr(embedding_module.settings, "google_api_key", "test-secret")
    calls = []
    _install_transport(monkeypatch, embedding_module, lambda request: calls.append(request))
    service = embedding_module.EmbeddingService()

    for texts in (["  "], ["valid", None]):
        with pytest.raises(ValueError, match="non-empty strings"):
            asyncio.run(service.embed_texts(texts))
    assert calls == []


def test_embedding_requires_api_key_and_empty_batches_skip_provider(monkeypatch):
    monkeypatch.setattr(embedding_module.settings, "google_api_key", " ")
    calls = []
    _install_transport(monkeypatch, embedding_module, lambda request: calls.append(request))
    service = embedding_module.EmbeddingService()

    assert asyncio.run(service.embed_texts([])) == []
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY is required"):
        asyncio.run(service.embed_texts(["document"]))
    assert calls == []
