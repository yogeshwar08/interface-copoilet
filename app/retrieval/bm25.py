import logging
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from rank_bm25 import BM25Okapi

from app.retrieval.vector_store import COLLECTION_NAME, client

logger = logging.getLogger(__name__)

_cached_bm25: Optional[BM25Okapi] = None
_cached_documents: List[Dict[str, Any]] = []


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def load_documents() -> list[dict]:
    # 1. Try Qdrant vector store
    try:
        scroll_result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=2000,
            with_payload=True,
        )
        records = scroll_result[0] if scroll_result else []
        if records:
            documents = []
            for record in records:
                payload = record.payload or {}
                text = payload.get("text", "")
                if text:
                    documents.append({
                        "text": text,
                        "payload": payload,
                    })
            if documents:
                return documents
    except Exception as exc:
        logger.debug(f"BM25 document loader could not read from Qdrant: {exc}")

    # 2. Resilient fallback: parse raw PDFs directly from data/raw/
    try:
        from app.ingestion.pipeline import ingest_pdf
        raw_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
        if raw_dir.exists():
            documents = []
            for pdf_path in sorted(raw_dir.glob("*.pdf")):
                res = ingest_pdf(str(pdf_path))
                for chunk in res.get("chunks", []):
                    documents.append({
                        "text": chunk.text,
                        "payload": {
                            "document_id": chunk.document_id,
                            "chunk_id": chunk.chunk_id,
                            "filename": chunk.filename,
                            "page_number": chunk.page_number,
                            "chunk_index": chunk.chunk_index,
                            "text": chunk.text,
                            "metadata": chunk.metadata,
                        },
                    })
            if documents:
                logger.info(f"BM25 indexed {len(documents)} chunks directly from {raw_dir}")
                return documents
    except Exception as exc:
        logger.warning(f"BM25 raw PDF fallback encountered error: {exc}")

    return []


def build_bm25_index(force_refresh: bool = False) -> Tuple[Optional[BM25Okapi], List[Dict[str, Any]]]:
    global _cached_bm25, _cached_documents

    if not force_refresh and _cached_bm25 is not None and _cached_documents:
        return _cached_bm25, _cached_documents

    documents = load_documents()
    if not documents:
        return None, []

    tokenized_documents = [
        tokenize(document["text"])
        for document in documents
    ]

    valid_tokenized = [toks if toks else ["<empty>"] for toks in tokenized_documents]

    bm25 = BM25Okapi(valid_tokenized)
    _cached_bm25 = bm25
    _cached_documents = documents
    return bm25, documents