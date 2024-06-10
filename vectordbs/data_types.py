from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, List, Optional, Sequence, Union


Embedding = Union[Sequence[float], Sequence[int]]
Embeddings = List[Embedding]


@dataclass
class Document:
    name: str
    document_id: str
    chunks: List[DocumentChunk]
    path: Optional[str] = ""


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    vectors: Optional[List[float]] = None
    metadata: Optional[DocumentChunkMetadata] = None
    document_id: Optional[str] = None

    def dict(self) -> dict[str, Any]:
        return {"text": self.text}


@dataclass
class DocumentChunkMetadata:
    source: Source
    source_id: Optional[str] = ""
    url: Optional[str] = ""
    created_at: Optional[str] = ""
    author: Optional[str] = ""


@dataclass
class DocumentQuery:
    text: str
    metadata: Optional[DocumentMetadataFilter] = None


class Source(str, Enum):
    WEBSITE = "website"
    PDF = "pdf"
    WORD_DOCUMENT = "word"
    POWERPOINT = "ppt"
    OTHER = "other"


@dataclass
class DocumentMetadataFilter:
    field_name: str
    operator: str = ""
    value: Any = None


@dataclass
class DocumentChunkWithScore(DocumentChunk):
    score: Optional[float] = None


@dataclass
class QueryResult:
    data: Optional[List[DocumentChunkWithScore]] = None
    similarities: Optional[List[float]] = None
    ids: Optional[List[str]] = None


@dataclass
class VectorStoreQuery:
    query_embedding: Optional[List[float]] = None
    similarity_top_k: int = 1
    ids: Optional[List[str]] = None
    query_str: Optional[str] = None


@dataclass
class QueryWithEmbedding:
    text: str
    vectors: List[float]


@dataclass
class VectorStoreData:
    id: str
    data: dict
    embedding: List[float]


@dataclass
class VectorStoreQueryMode(Enum):
    DEFAULT = auto()
    SPARSE = auto()
    HYBRID = auto()

    @classmethod
    def get_current_mode(cls) -> VectorStoreQueryMode:
        return cls.DEFAULT
