from pathlib import Path

from app.ingestion.cleaner import clean_text
from app.ingestion.chunker import chunk_pages
from app.ingestion.pdf_loader import load_pdf


def ingest_pdf(file_path: str):

    pages = load_pdf(file_path)

    # Clean extracted text
    for page in pages:
        page.text = clean_text(page.text)

    # Convert pages into retrieval chunks
    chunks = chunk_pages(pages)

    return {
        "document_id": pages[0].document_id if pages else None,
        "filename": Path(file_path).name,
        "pages": pages,
        "chunks": chunks,
    }