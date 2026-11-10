"""Async Gemini embeddings with validated, normalized 768-dimensional vectors."""

import math
import re
from typing import List

import httpx

from app.config import settings

VECTOR_SIZE = 768
MAX_BATCH_SIZE = 100
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _model_name() -> str:
    model = settings.embedding_model.removeprefix("models/")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", model):
        raise ValueError("Configured Gemini embedding model name is invalid")
    return model


def _validated_embeddings(payload: object, expected_count: int) -> List[List[float]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("embeddings"), list):
        raise ValueError("Gemini returned a malformed embedding response")

    embeddings = payload["embeddings"]
    if len(embeddings) != expected_count:
        raise ValueError("Gemini returned a different number of embeddings than requested")

    normalized: List[List[float]] = []
    for item in embeddings:
        if not isinstance(item, dict) or not isinstance(item.get("values"), list):
            raise ValueError("Gemini returned a malformed embedding vector")
        values = item["values"]
        if len(values) != VECTOR_SIZE:
            raise ValueError(f"Gemini embedding must contain exactly {VECTOR_SIZE} values")

        vector: List[float] = []
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Gemini embedding contains a non-numeric value")
            try:
                number = float(value)
            except (OverflowError, ValueError) as exc:
                raise ValueError("Gemini embedding contains an invalid numeric value") from exc
            if not math.isfinite(number):
                raise ValueError("Gemini embedding contains a non-finite value")
            vector.append(number)

        magnitude = math.hypot(*vector)
        if not math.isfinite(magnitude) or not magnitude:
            raise ValueError("Gemini returned a zero or invalid embedding vector")
        normalized.append([value / magnitude for value in vector])
    return normalized


class EmbeddingService:
    """Generate document and query embeddings using Gemini's REST API."""

    async def _embed(self, texts: List[str], task_type: str) -> List[List[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Embedding texts must be non-empty strings")
        if not settings.google_api_key.strip():
            raise RuntimeError("GOOGLE_API_KEY is required to generate embeddings")

        model = _model_name()
        endpoint = f"{API_BASE}/{model}:batchEmbedContents"
        headers = {"x-goog-api-key": settings.google_api_key}
        vectors: List[List[float]] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for start in range(0, len(texts), MAX_BATCH_SIZE):
                batch = texts[start : start + MAX_BATCH_SIZE]
                response = await client.post(
                    endpoint,
                    headers=headers,
                    json={
                        "requests": [
                            {
                                "model": f"models/{model}",
                                "content": {"parts": [{"text": text}]},
                                "taskType": task_type,
                                "outputDimensionality": VECTOR_SIZE,
                            }
                            for text in batch
                        ]
                    },
                )
                response.raise_for_status()
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ValueError("Gemini returned invalid JSON for embeddings") from exc
                vectors.extend(_validated_embeddings(payload, len(batch)))
        return vectors

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Return one normalized 768-dimensional vector per document text."""
        return await self._embed(texts, "RETRIEVAL_DOCUMENT")

    async def embed_single(self, text: str) -> List[float]:
        """Return one normalized 768-dimensional vector for a search query."""
        return (await self._embed([text], "RETRIEVAL_QUERY"))[0]


# Singleton instance
embedding_service = EmbeddingService()
