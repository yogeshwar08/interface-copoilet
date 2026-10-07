from typing import Optional
from sentence_transformers import CrossEncoder

from app.config import settings


class Reranker:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.reranker_model_name
        self._model: Optional[CrossEncoder] = None

    @property
    def model(self) -> CrossEncoder:
        if self._model is None:
            self._model = CrossEncoder(self.model_name)
        return self._model


    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ):
        pairs = [
            (query, document["payload"]["text"])
            for document in documents
        ]

        scores = self.model.predict(pairs)

        ranked = sorted(
            zip(scores, documents),
            key=lambda x: x[0],
            reverse=True,
        )

        results = []

        for score, document in ranked[:top_k]:
            results.append(
                {
                    "score": float(score),
                    "payload": document["payload"],
                }
            )

        return results


reranker = Reranker()