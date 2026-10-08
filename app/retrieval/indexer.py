import gc
import logging
import uuid
from pathlib import Path

from qdrant_client.models import PointStruct

from app.ingestion.pipeline import ingest_pdf
from app.retrieval.embeddings import embedding_model
from app.retrieval.vector_store import (
    COLLECTION_NAME,
    client,
    create_collection,
)

logger = logging.getLogger(__name__)

# Absolute path to data/raw/ resolved relative to THIS file — works correctly
# inside Docker containers regardless of the process working directory.
# Path: app/retrieval/indexer.py -> parent.parent.parent = project root
_RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"


def index_document(pdf_path: str):

    create_collection()

    result = ingest_pdf(pdf_path)

    chunks = result["chunks"]

    texts = [chunk.text for chunk in chunks]

    vectors = embedding_model.encode(texts)

    points = []

    for chunk, vector in zip(chunks, vectors):

        point_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                chunk.chunk_id,
            )
        )

        points.append(
            PointStruct(
                id=point_id,
                vector=vector.tolist(),
                payload={
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "filename": chunk.filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                },
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    return {
        "document_id": result["document_id"],
        "filename": result["filename"],
        "chunks_indexed": len(points),
    }


def ensure_documents_indexed() -> int:
    """
    Ensures that documents in data/raw are indexed into Qdrant.
    If the collection is empty, automatically indexes all available PDF documents.
    Uses an absolute path so this works correctly inside Docker containers
    regardless of the process working directory.
    """
    create_collection()

    try:
        count = client.count(collection_name=COLLECTION_NAME).count
        if count > 0:
            logger.info(f"Qdrant already has {count} vectors — skipping re-index.")
            return count
    except Exception as exc:
        logger.warning(f"Could not read Qdrant collection count: {exc}")

    if not _RAW_DIR.exists():
        logger.warning(
            f"data/raw directory not found at '{_RAW_DIR}' — no documents to index."
        )
        return 0

    pdf_files = sorted(_RAW_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {_RAW_DIR}")
        return 0

    logger.info(f"Indexing {len(pdf_files)} PDF(s) from {_RAW_DIR} ...")
    total_chunks = 0
    for pdf_path in pdf_files:
        try:
            res = index_document(str(pdf_path))
            chunks = res.get("chunks_indexed", 0)
            total_chunks += chunks
            logger.info(f"  Indexed '{pdf_path.name}' -> {chunks} chunks")
        except Exception as exc:
            logger.error(
                f"  Failed to index '{pdf_path.name}': {exc}",
                exc_info=True,
            )
        finally:
            # Release PyMuPDF page objects + PyTorch tensors before next PDF
            gc.collect()

    return total_chunks