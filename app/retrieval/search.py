import logging
from typing import List, Dict, Any

from app.retrieval.embeddings import embedding_model
from app.retrieval.vector_store import COLLECTION_NAME, client
from app.retrieval.bm25 import build_bm25_index, tokenize
from app.retrieval.reranker import reranker

logger = logging.getLogger(__name__)


def dense_search(query: str, top_k: int = 5) -> list:
    try:
        query_vector = embedding_model.encode([query])[0]
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector.tolist(),
            limit=top_k,
            with_payload=True,
        ).points
        return results or []
    except Exception as exc:
        logger.warning(f"Dense search encountered error ({exc}). Falling back to lexical retrieval.")
        return []


def bm25_search(query: str, top_k: int = 5) -> list:
    try:
        bm25, documents = build_bm25_index()
        if bm25 is None or not documents:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = bm25.get_scores(query_tokens)

        ranked = sorted(
            zip(scores, documents),
            key=lambda x: x[0],
            reverse=True,
        )

        return ranked[:top_k]
    except Exception as exc:
        logger.debug(f"BM25 search error: {exc}")
        return []


def reciprocal_rank_fusion(
    dense_results,
    bm25_results,
    k: int = 60,
) -> List[Dict[str, Any]]:
    fused_scores = {}
    documents = {}

    # Dense results
    for rank, result in enumerate(dense_results, start=1):
        payload = getattr(result, "payload", {}) or {}
        chunk_id = payload.get("chunk_id", str(rank))

        fused_scores[chunk_id] = (
            fused_scores.get(chunk_id, 0)
            + 1 / (k + rank)
        )
        documents[chunk_id] = payload

    # BM25 results
    for rank, (score, document) in enumerate(
        bm25_results,
        start=1,
    ):
        payload = document.get("payload", {})
        chunk_id = payload.get("chunk_id", str(rank))

        fused_scores[chunk_id] = (
            fused_scores.get(chunk_id, 0)
            + 1 / (k + rank)
        )
        documents[chunk_id] = payload

    ranked = sorted(
        fused_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    return [
        {
            "chunk_id": chunk_id,
            "score": score,
            "payload": documents[chunk_id],
        }
        for chunk_id, score in ranked
    ]


def hybrid_search(
    query: str,
    top_k: int = 5,
    candidate_k: int = 10,
) -> List[Dict[str, Any]]:
    dense_results = dense_search(
        query,
        top_k=candidate_k,
    )

    bm25_results = bm25_search(
        query,
        top_k=candidate_k,
    )

    fused_results = reciprocal_rank_fusion(
        dense_results,
        bm25_results,
    )

    return fused_results[:top_k]


def retrieve_context(
    query: str,
    candidate_k: int = 10,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    dense_results = dense_search(
        query,
        top_k=candidate_k,
    )

    bm25_results = bm25_search(
        query,
        top_k=candidate_k,
    )

    fused_results = reciprocal_rank_fusion(
        dense_results,
        bm25_results,
    )

    candidates = fused_results[:candidate_k]
    if not candidates:
        return []

    reranked_results = reranker.rerank(
        query,
        candidates,
        top_k=top_k,
    )

    return reranked_results