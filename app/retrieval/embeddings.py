"""
Embedding model — dual backend support.

- Local backend  (default):  sentence-transformers/all-MiniLM-L6-v2 via PyTorch
                              Vector dim = 384.  Good for local dev / high-RAM hosts.

- Gemini backend (production): google-genai text-embedding-004 via REST API.
                              Vector dim = 768.  Zero PyTorch required — saves ~250MB
                              RAM on Render 512MB starter instances.

Select via env var:
    USE_GEMINI_EMBEDDINGS=true   → Gemini API  (set in render.yaml)
    USE_GEMINI_EMBEDDINGS=false  → local HF model (default)
"""

import logging
import re
import time
from typing import Optional

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gemini API backend — no PyTorch, no local model weights
# ---------------------------------------------------------------------------

class GeminiEmbeddingModel:
    """Embeds text via Google Gemini text-embedding-004 (768-dim, REST API).
    Batches up to 100 texts per request; retries on transient errors.
    """

    GEMINI_MODEL = "gemini-embedding-001"
    VECTOR_SIZE = 768
    _BATCH_SIZE = 50        # Gemini embed batch limit is 100; use 50 to be safe
    _MAX_RETRIES = 5

    def __init__(self):
        from google import genai
        self._client = genai.Client(api_key=settings.gemini_api_key)
        logger.info(f"EmbeddingModel: using Gemini API backend ({self.GEMINI_MODEL}, {self.VECTOR_SIZE}-dim)")

    def encode(self, texts: list[str], batch_size: int = _BATCH_SIZE) -> np.ndarray:
        """Encode texts in batches. Returns normalized float32 numpy array (N, 768)."""
        if not texts:
            return np.empty((0, self.VECTOR_SIZE), dtype=np.float32)

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self._BATCH_SIZE):
            batch = texts[i : i + self._BATCH_SIZE]
            for attempt in range(1, self._MAX_RETRIES + 1):
                try:
                    result = self._client.models.embed_content(
                        model=self.GEMINI_MODEL,
                        contents=batch,
                        config={"output_dimensionality": self.VECTOR_SIZE},
                    )
                    all_embeddings.extend(
                        e.values for e in result.embeddings
                    )
                    # Polite throttle between batches to avoid RPM burst spikes
                    time.sleep(0.3)
                    break
                except Exception as exc:
                    if attempt == self._MAX_RETRIES:
                        raise RuntimeError(
                            f"Gemini embedding failed after {self._MAX_RETRIES} attempts: {exc}"
                        ) from exc
                    # On 429 or quota exhaustion, back off with sufficient time for window reset.
                    # Parse the exact retry delay requested by Gemini API if present.
                    err_str = str(exc)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        delay_match = re.search(r"retry\s+in\s+([0-9.]+)\s*s", err_str, re.IGNORECASE)
                        if delay_match:
                            wait = float(delay_match.group(1)) + 1.5
                        else:
                            wait = 5.0 * attempt
                    else:
                        wait = 2.0 * attempt

                    # For user queries (small batches), do NOT freeze the HTTP request with long waits.
                    # Fast-fail so dense search immediately hands off to instantaneous BM25 retrieval.
                    if len(texts) <= 2 and wait > 3.0:
                        logger.warning(
                            f"Query embedding rate-limited (wait={wait:.1f}s). Fast failing to lexical BM25 fallback."
                        )
                        raise RuntimeError(f"Query embedding rate-limited: {exc}") from exc

                    logger.warning(
                        f"Gemini embed attempt {attempt} failed ({exc}), retrying in {wait:.1f}s..."
                    )
                    time.sleep(wait)

        v = np.array(all_embeddings, dtype=np.float32)
        if len(v) > 0:
            norms = np.linalg.norm(v, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            v = v / norms
        return v


# ---------------------------------------------------------------------------
# Local HuggingFace / sentence-transformers backend
# ---------------------------------------------------------------------------

class LocalEmbeddingModel:
    """Embeds text using a local sentence-transformers model via PyTorch.
    Lazy-loads the model on first use. batch_size=8 limits peak RAM usage.
    """

    VECTOR_SIZE = 384

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.embedding_model_name
        self._model = None
        logger.info(f"EmbeddingModel: using local backend ({self.model_name}, 384-dim)")

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str], batch_size: int = 8) -> np.ndarray:
        return self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )


# ---------------------------------------------------------------------------
# Auto-select backend
# ---------------------------------------------------------------------------

def _build_embedding_model():
    if settings.use_gemini_embeddings:
        if not settings.gemini_api_key:
            logger.warning(
                "USE_GEMINI_EMBEDDINGS=true but GEMINI_API_KEY is not set — "
                "falling back to local sentence-transformers model."
            )
            return LocalEmbeddingModel()
        return GeminiEmbeddingModel()
    return LocalEmbeddingModel()


embedding_model = _build_embedding_model()

# Expose the vector size so vector_store.py can read it without importing torch
EMBEDDING_VECTOR_SIZE: int = (
    GeminiEmbeddingModel.VECTOR_SIZE
    if settings.use_gemini_embeddings and settings.gemini_api_key
    else LocalEmbeddingModel.VECTOR_SIZE
)