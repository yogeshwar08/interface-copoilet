import uuid

from qdrant_client.models import PointStruct

from app.ingestion.pipeline import ingest_pdf
from app.retrieval.embeddings import embedding_model
from app.retrieval.vector_store import (
    COLLECTION_NAME,
    client,
    create_collection,
)


def index_document(pdf_path: str):

    create_collection()

    result = ingest_pdf(pdf_path)

    chunks = result["chunks"]

    texts = [
        chunk.text
        for chunk in chunks
    ]

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
    """
    from pathlib import Path
    create_collection()

    try:
        count = client.count(collection_name=COLLECTION_NAME).count
        if count > 0:
            return count
    except Exception:
        pass

    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        return 0

    total_chunks = 0
    for pdf_path in sorted(raw_dir.glob("*.pdf")):
        try:
            res = index_document(str(pdf_path))
            total_chunks += res.get("chunks_indexed", 0)
        except Exception as exc:
            pass

    return total_chunks