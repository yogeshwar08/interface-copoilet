try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover
    class RecursiveCharacterTextSplitter:  # type: ignore
        def __init__(
            self,
            chunk_size: int = 1000,
            chunk_overlap: int = 150,
            separators: list[str] | None = None,
        ):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
            self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

        def split_text(self, text: str) -> list[str]:
            if not text:
                return []
            chunks = []
            start = 0
            text_len = len(text)
            step = max(1, self.chunk_size - self.chunk_overlap)
            while start < text_len:
                end = min(start + self.chunk_size, text_len)
                chunks.append(text[start:end])
                if end == text_len:
                    break
                start += step
            return chunks

from app.ingestion.models import DocumentChunk, DocumentPage


def chunk_pages(
    pages: list[DocumentPage],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[DocumentChunk]:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],
    )

    chunks = []

    global_chunk_index = 0

    for page in pages:

        if not page.text.strip():
            continue

        page_chunks = splitter.split_text(page.text)

        for chunk_index, chunk_text in enumerate(page_chunks):

            chunk_id = (
                f"{page.document_id}"
                f"-p{page.page_number}"
                f"-c{chunk_index}"
            )

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    filename=page.filename,
                    page_number=page.page_number,
                    chunk_index=global_chunk_index,
                    text=chunk_text,
                    metadata={
                        **page.metadata,
                        "chunk_id": chunk_id,
                        "chunk_index": str(global_chunk_index),
                    },
                )
            )

            global_chunk_index += 1

    return chunks