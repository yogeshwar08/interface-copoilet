import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.reranker_model_name
        self._model = None
        self._load_failed = False

    @property
    def model(self):
        if not getattr(settings, "reranker_enabled", True):
            return None
        if self._model is None and not self._load_failed:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except Exception as exc:
                self._load_failed = True
                logger.warning(f"Could not load CrossEncoder ({exc}). Operating with RRF rank.")
                return None
        return self._model

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ):
        if not documents:
            return []

        model = self.model
        if model is None:
            # Fall back directly to existing fused ranking
            return documents[:top_k]

        try:
            pairs = [
                (query, document["payload"]["text"])
                for document in documents
            ]
            scores = model.predict(pairs)
            ranked = sorted(
                zip(scores, documents),
                key=lambda x: x[0],
                reverse=True,
            )
            return [
                {
                    "score": float(score),
                    "payload": document["payload"],
                }
                for score, document in ranked[:top_k]
            ]
        except Exception as exc:
            logger.warning(f"Reranking encountered error ({exc}). Falling back to candidate ranking.")
            return documents[:top_k]


reranker = Reranker()