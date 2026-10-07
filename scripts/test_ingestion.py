from pathlib import Path

from app.ingestion.pipeline import ingest_pdf


PDF_PATH = Path(
    "data/raw/01_Diabetes_Clinical_Guideline.pdf"
)


def main():

    if not PDF_PATH.exists():
        print(f"PDF not found: {PDF_PATH}")
        return

    result = ingest_pdf(str(PDF_PATH))

    print("\n=== INGESTION RESULT ===")

    print(f"Document ID : {result['document_id']}")
    print(f"Filename    : {result['filename']}")
    print(f"Pages       : {len(result['pages'])}")
    print(f"Chunks      : {len(result['chunks'])}")

    print("\n=== FIRST CHUNK ===")

    if result["chunks"]:

        chunk = result["chunks"][0]

        print(f"Chunk ID    : {chunk.chunk_id}")
        print(f"Page        : {chunk.page_number}")
        print(f"Chunk index : {chunk.chunk_index}")
        print(f"Metadata    : {chunk.metadata}")

        print("\nText:")
        print(chunk.text)


if __name__ == "__main__":
    main()