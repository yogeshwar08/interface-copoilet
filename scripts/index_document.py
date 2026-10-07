import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval.indexer import index_document


PDF_PATH = (
    "data/raw/01_Diabetes_Clinical_Guideline.pdf"
)


def main():

    result = index_document(PDF_PATH)

    print("\n=== INDEXING COMPLETE ===")

    print(
        f"Document ID    : "
        f"{result['document_id']}"
    )

    print(
        f"Filename       : "
        f"{result['filename']}"
    )

    print(
        f"Chunks indexed : "
        f"{result['chunks_indexed']}"
    )


if __name__ == "__main__":
    main()