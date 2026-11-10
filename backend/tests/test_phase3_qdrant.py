import asyncio
import uuid

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

import app.services.qdrant_service as qdrant_module
from app.models.budget import BudgetExhaustedError, SessionBudget


VECTOR_SIZE = 768


async def _service_with_memory_qdrant():
    client = AsyncQdrantClient(location=":memory:")
    service = qdrant_module.QdrantService()
    service.collection_name = "phase3-test"
    service.client = client
    await client.create_collection(
        collection_name=service.collection_name,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    return service, client


def _vector(index=0):
    vector = [0.0] * VECTOR_SIZE
    vector[index] = 1.0
    return vector


def test_real_qdrant_ingest_is_deterministic_session_scoped_and_metadata_safe(monkeypatch):
    async def embed_texts(texts):
        return [_vector() for _ in texts]

    async def embed_single(_text):
        return _vector()

    monkeypatch.setattr(qdrant_module.embedding_service, "embed_texts", embed_texts)
    monkeypatch.setattr(qdrant_module.embedding_service, "embed_single", embed_single)

    async def run():
        service, client = await _service_with_memory_qdrant()
        try:
            reserved_overrides = {
                "session_id": "spoofed-session",
                "source_id": "spoofed-source",
                "chunk_index": 99,
                "content": "spoofed content",
                "title": "Kept title",
            }
            assert await service.ingest_document(
                "session-a", "REF_1", "first document", reserved_overrides, SessionBudget()
            ) == 1
            first_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "session-a:REF_1:0"))
            assert await service.ingest_document(
                "session-a", "REF_1", "first document", reserved_overrides, SessionBudget()
            ) == 1
            assert await service.ingest_document(
                "session-b", "REF_1", "second document", {}, SessionBudget()
            ) == 1
            second_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "session-b:REF_1:0"))
            assert first_id != second_id

            points, _next = await client.scroll(
                collection_name=service.collection_name,
                limit=10,
                with_payload=True,
                with_vectors=False,
            )
            assert len(points) == 2
            first_point = next(point for point in points if point.id == first_id)
            assert first_point.payload == {
                "title": "Kept title",
                "session_id": "session-a",
                "source_id": "REF_1",
                "chunk_index": 0,
                "content": "first document",
            }

            in_session_a = await service.search("session-a", "query", SessionBudget())
            in_session_b = await service.search("session-b", "query", SessionBudget())
            assert [(item["source_id"], item["session_id"]) for item in in_session_a] == [
                ("REF_1", "session-a")
            ]
            assert [(item["source_id"], item["session_id"]) for item in in_session_b] == [
                ("REF_1", "session-b")
            ]
        finally:
            await service.close()

    asyncio.run(run())


def test_qdrant_rejects_invalid_embeddings_before_upsert(monkeypatch):
    async def bad_embeddings(_texts):
        return [[float("nan")] + [0.0] * (VECTOR_SIZE - 1)]

    monkeypatch.setattr(qdrant_module.embedding_service, "embed_texts", bad_embeddings)

    async def run():
        service, client = await _service_with_memory_qdrant()
        try:
            with pytest.raises(ValueError, match="invalid value"):
                await service.ingest_document(
                    "session-a", "REF_1", "document", {}, SessionBudget()
                )
            points, _next = await client.scroll(
                collection_name=service.collection_name,
                limit=10,
                with_payload=True,
                with_vectors=False,
            )
            assert points == []
        finally:
            await service.close()

    asyncio.run(run())


def test_qdrant_reserves_budget_before_calling_embedder(monkeypatch):
    calls = []

    async def embed_texts(_texts):
        calls.append(True)
        return [_vector()]

    monkeypatch.setattr(qdrant_module.embedding_service, "embed_texts", embed_texts)

    async def run():
        service, client = await _service_with_memory_qdrant()
        try:
            with pytest.raises(BudgetExhaustedError):
                await service.ingest_document(
                    "session-a",
                    "REF_1",
                    "document",
                    {},
                    SessionBudget(max_total_input_tokens=0),
                )
            assert calls == []
            points, _next = await client.scroll(
                collection_name=service.collection_name,
                limit=10,
                with_payload=True,
                with_vectors=False,
            )
            assert points == []
        finally:
            await service.close()

    asyncio.run(run())
