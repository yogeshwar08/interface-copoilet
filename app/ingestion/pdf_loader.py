from pathlib import Path
import hashlib

import pymupdf


from app.ingestion.models import DocumentPage


def create_document_id(file_path: Path) -> str:
    """
    Create a stable document ID from the filename and file size.
    """

    raw = f"{file_path.name}:{file_path.stat().st_size}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]


def load_pdf(file_path: str) -> list[DocumentPage]:

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"PDF not found: {path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected a PDF file, got: {path.suffix}"
        )

    document_id = create_document_id(path)

    pdf = pymupdf.open(path)

    pages = []

    for page_number, page in enumerate(pdf, start=1):

        text = page.get_text("text")

        pages.append(
            DocumentPage(
                document_id=document_id,
                filename=path.name,
                page_number=page_number,
                text=text,
                metadata={
                    "document_id": document_id,
                    "filename": path.name,
                    "page_number": str(page_number),
                    "document_type": "pdf",
                },
            )
        )

    pdf.close()

    return pages