"""
Qdrant Vector Database Service
Handles document ingestion (chunk → embed → store) and semantic search.

Maps from brainstorm: tool_api_data_contracts.md (Qdrant Schema).
"""

import logging
import math
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.config import settings
from app.models.budget import SessionBudget
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class QdrantService:
    """Manages Qdrant vector database operations for document storage and retrieval."""

    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None
        self.collection_name = settings.qdrant_collection
        self.vector_size = 768  # gemini-embedding-001 output dimensions

    async def initialize(self):
        """Initialize Qdrant client and ensure collection exists."""
        self.client = AsyncQdrantClient(url=settings.qdrant_url)

        # Create collection if not exists
        collections = await self.client.get_collections()
        existing_names = [c.name for c in collections.collections]

        if self.collection_name not in existing_names:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            # Create payload indexes for fast filtering
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="session_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="source_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info(f"✅ Created Qdrant collection: {self.collection_name}")
        else:
            logger.info(f"✅ Qdrant collection exists: {self.collection_name}")

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()
            self.client = None

    async def ingest_document(
        self,
        session_id: str,
        source_id: str,
        content: str,
        metadata: Dict[str, Any],
        budget: SessionBudget,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Chunk a document, generate embeddings, and store in Qdrant.
        
        Args:
            session_id: Research session identifier.
            source_id: Source reference ID (e.g., "REF_1").
            content: Full document text.
            metadata: Additional metadata to store with each chunk.
            chunk_size: Target chunk size in characters.
            chunk_overlap: Overlap between consecutive chunks.
        """
        if not content.strip():
            raise ValueError("Cannot ingest an empty document.")
        if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("Document chunk size/overlap configuration is invalid.")
        if self.client is None:
            raise RuntimeError("Qdrant client is not initialized.")

        # ── Simple chunking (upgrade to semantic chunking later) ──
        chunks = self._chunk_text(content, chunk_size, chunk_overlap)

        if not chunks:
            raise ValueError("Document did not contain any usable text.")

        # ── Generate embeddings ──
        budget.reserve_input("\n".join(chunks))
        embeddings = await embedding_service.embed_texts(chunks)
        if len(embeddings) != len(chunks):
            raise ValueError("Embedding count does not match document chunks.")

        # ── Store in Qdrant ──
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            self._validate_vector(embedding)
            point_id = str(uuid.uuid5(
                uuid.NAMESPACE_URL, f"{session_id}:{source_id}:{i}"
            ))
            safe_metadata = {
                key: value for key, value in metadata.items()
                if key not in {"session_id", "source_id", "chunk_index", "content"}
            }
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    **safe_metadata,
                    "session_id": session_id,
                    "source_id": source_id,
                    "chunk_index": i,
                    "content": chunk,
                },
            ))

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        logger.info(f"📦 Ingested {len(points)} chunks for {source_id}")
        return len(points)

    async def search(
        self,
        session_id: str,
        query_text: str,
        budget: SessionBudget,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search within a session's documents.
        
        Args:
            session_id: Filter to this session only.
            query_text: Query to search for.
            top_k: Number of results to return.
        
        Returns:
            List of matching chunks with metadata.
        """
        if self.client is None:
            raise RuntimeError("Qdrant client is not initialized.")
        if top_k < 1:
            raise ValueError("top_k must be positive.")

        # Generate query embedding
        budget.reserve_input(query_text)
        query_embedding = await embedding_service.embed_single(query_text)
        self._validate_vector(query_embedding)

        results = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id),
                    )
                ]
            ),
            limit=top_k,
            with_payload=True,
        )

        return [
            {
                "content": (hit.payload or {}).get("content", ""),
                "source_id": (hit.payload or {}).get("source_id", ""),
                "score": hit.score,
                **{
                    key: value for key, value in (hit.payload or {}).items()
                    if key not in {"content", "source_id"}
                },
            }
            for hit in results.points
        ]

    def _validate_vector(self, vector: List[float]) -> None:
        if len(vector) != self.vector_size:
            raise ValueError(f"Embedding vector must have {self.vector_size} dimensions.")
        try:
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in vector
            ):
                raise ValueError("Embedding vector contains an invalid value.")
            if math.hypot(*(float(value) for value in vector)) == 0:
                raise ValueError("Embedding vector cannot be zero.")
        except (OverflowError, TypeError, ValueError) as exc:
            if isinstance(exc, ValueError) and str(exc) in {
                "Embedding vector contains an invalid value.",
                "Embedding vector cannot be zero.",
            }:
                raise
            raise ValueError("Embedding vector contains an invalid value.") from exc

    def _chunk_text(
        self, text: str, chunk_size: int, overlap: int
    ) -> List[str]:
        """Simple character-based chunking with overlap."""
        if not text:
            return []

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start += chunk_size - overlap

        return chunks


# Singleton instance
qdrant_service = QdrantService()
