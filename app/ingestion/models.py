from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DocumentPage:
    document_id: str
    filename: str
    page_number: int
    text: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    text: str
    metadata: Dict[str, str] = field(default_factory=dict)