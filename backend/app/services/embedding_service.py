"""
Embedding Service — Google Gemini text-embedding-004
Generates vector embeddings for document chunks and queries.
"""

import logging
from typing import List

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates embeddings using Google's text-embedding-004 model."""

    def __init__(self):
        self._initialized = False

    def _ensure_initialized(self):
        if not self._initialized:
            genai.configure(api_key=settings.google_api_key)
            self._initialized = True

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings to embed.
        
        Returns:
            List of embedding vectors (each is a list of 768 floats).
        """
        self._ensure_initialized()

        if not texts:
            return []

        try:
            result = genai.embed_content(
                model=settings.embedding_model,
                content=texts,
                task_type="retrieval_document",
            )
            return result["embedding"]

        except Exception as e:
            logger.error(f"❌ Embedding batch failed: {e}")
            # Return zero vectors as fallback
            return [[0.0] * 768 for _ in texts]

    async def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single query text.
        
        Args:
            text: Text string to embed.
        
        Returns:
            Embedding vector (list of 768 floats).
        """
        self._ensure_initialized()

        try:
            result = genai.embed_content(
                model=settings.embedding_model,
                content=text,
                task_type="retrieval_query",
            )
            return result["embedding"]

        except Exception as e:
            logger.error(f"❌ Embedding single failed: {e}")
            return [0.0] * 768


# Singleton instance
embedding_service = EmbeddingService()
