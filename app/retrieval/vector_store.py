import logging
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = settings.qdrant_collection
# Import the resolved vector size from the embeddings module.
# 384 for local sentence-transformers, 768 for Gemini text-embedding-004.
from app.retrieval.embeddings import EMBEDDING_VECTOR_SIZE
VECTOR_SIZE = EMBEDDING_VECTOR_SIZE

_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client

    if settings.qdrant_prefer_memory:
        logger.info("Using Qdrant in-memory mode per configuration.")
        _client = QdrantClient(":memory:")
        return _client

    try:
        if settings.qdrant_url:
            candidate_client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=3.0,
            )
        else:
            candidate_client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                timeout=3.0,
            )
        # Probe connection
        candidate_client.get_collections()
        _client = candidate_client
        logger.info(f"Connected to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")
    except Exception as exc:
        logger.warning(
            f"Failed to connect to Qdrant cluster ({exc}). Falling back to in-memory Qdrant instance."
        )
        _client = QdrantClient(":memory:")

    return _client


class _ClientProxy:
    """Proxy object so existing imports of `client` continue to work transparently."""
    def __getattr__(self, name):
        return getattr(get_qdrant_client(), name)


client = _ClientProxy()


def create_collection():
    q_client = get_qdrant_client()
    try:
        existing_collections = [
            collection.name
            for collection in q_client.get_collections().collections
        ]

        if COLLECTION_NAME not in existing_collections:
            q_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {COLLECTION_NAME}")
        else:
            logger.debug(f"Collection already exists: {COLLECTION_NAME}")
    except Exception as exc:
        logger.error(f"Error checking/creating collection: {exc}")