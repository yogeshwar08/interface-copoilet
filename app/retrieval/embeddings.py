from typing import Optional
from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingModel:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.embedding_model_name
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]):
        return self.model.encode(
            texts,
            normalize_embeddings=True,
        )


embedding_model = EmbeddingModel()