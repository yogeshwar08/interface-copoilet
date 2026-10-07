import logging
import re
from typing import Optional, Tuple, List, Dict, Any

from rank_bm25 import BM25Okapi

from app.retrieval.vector_store import COLLECTION_NAME, client

logger = logging.getLogger(__name__)


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def load_documents() -> list[dict]:
    try:
        scroll_result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=2000,
            with_payload=True,
        )
        records = scroll_result[0] if scroll_result else []
    except Exception as exc:
        logger.debug(f"BM25 document loader noticed collection missing or empty: {exc}")
        return []

    documents = []
    for record in records:
        payload = record.payload or {}
        text = payload.get("text", "")
        if text:
            documents.append(
                {
                    "text": text,
                    "payload": payload,
                }
            )

    return documents


def build_bm25_index() -> Tuple[Optional[BM25Okapi], List[Dict[str, Any]]]:
    documents = load_documents()
    if not documents:
        return None, []

    tokenized_documents = [
        tokenize(document["text"])
        for document in documents
    ]

    # Filter out empty token lists if any
    valid_tokenized = [toks if toks else ["<empty>"] for toks in tokenized_documents]

    bm25 = BM25Okapi(valid_tokenized)
    return bm25, documents