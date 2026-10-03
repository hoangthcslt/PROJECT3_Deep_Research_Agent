"""
Qdrant Vector Database Service
Handles document ingestion (chunk → embed → store) and semantic search.

Maps from brainstorm: tool_api_data_contracts.md (Qdrant Schema).
"""

import logging
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
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class QdrantService:
    """Manages Qdrant vector database operations for document storage and retrieval."""

    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None
        self.collection_name = settings.qdrant_collection
        self.vector_size = 768  # text-embedding-004 dimensions

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

    async def ingest_document(
        self,
        session_id: str,
        source_id: str,
        content: str,
        metadata: Dict[str, Any],
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
        # ── Simple chunking (upgrade to semantic chunking later) ──
        chunks = self._chunk_text(content, chunk_size, chunk_overlap)

        if not chunks:
            logger.warning(f"⚠️ No chunks generated for {source_id}")
            return

        # ── Generate embeddings ──
        embeddings = await embedding_service.embed_texts(chunks)

        # ── Store in Qdrant ──
        points = []
        import uuid

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "session_id": session_id,
                    "source_id": source_id,
                    "chunk_index": i,
                    "content": chunk,
                    **metadata,
                },
            ))

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        logger.info(f"📦 Ingested {len(points)} chunks for {source_id}")

    async def search(
        self,
        session_id: str,
        query_text: str,
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
        # Generate query embedding
        query_embedding = await embedding_service.embed_single(query_text)

        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id),
                    )
                ]
            ),
            limit=top_k,
        )

        return [
            {
                "content": hit.payload.get("content", ""),
                "source_id": hit.payload.get("source_id", ""),
                "score": hit.score,
                **{k: v for k, v in hit.payload.items() if k not in ("content",)},
            }
            for hit in results
        ]

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
