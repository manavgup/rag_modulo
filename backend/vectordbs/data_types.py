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
    metadata: Optional[DocumentChunkMetadata] = None  # New field

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        return cls(
            name=data["name"],
            document_id=data["document_id"],
            chunks=[DocumentChunk.from_dict(chunk) for chunk in data["chunks"]],
            path=data.get("path", ""),
            metadata=DocumentChunkMetadata.from_dict(data["metadata"]) if data.get("metadata") else None
        )


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    vectors: Optional[List[float]] = None
    metadata: Optional[DocumentChunkMetadata] = None
    document_id: Optional[str] = None

    def dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "vectors": self.vectors,
            "metadata": self.metadata.__dict__ if self.metadata else None,
            "document_id": self.document_id
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentChunk:
        return cls(
            chunk_id=data["chunk_id"],
            text=data["text"],
            vectors=data.get("vectors"),
            metadata=DocumentChunkMetadata.from_dict(data["metadata"]) if data.get("metadata") else None,
            document_id=data.get("document_id")
        )


@dataclass
class DocumentChunkMetadata:
    source: Source
    source_id: Optional[str] = ""
    url: Optional[str] = ""
    created_at: Optional[str] = ""
    author: Optional[str] = ""
    title: Optional[str] = ""
    subject: Optional[str] = ""
    keywords: Optional[str] = ""
    creator: Optional[str] = ""
    producer: Optional[str] = ""
    creationDate: Optional[str] = ""
    modDate: Optional[str] = ""
    total_pages: Optional[int] = None
    page_number: Optional[int] = None
    content_type: Optional[str] = None
    table_index: Optional[int] = None
    image_index: Optional[int] = None
    document_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentChunkMetadata:
        return cls(
            source=Source(data["source"]),
            source_id=data.get("source_id"),
            url=data.get("url"),
            created_at=data.get("created_at"),
            author=data.get("author"),
            title=data.get("title"),
            subject=data.get("subject"),
            keywords=data.get("keywords"),
            creator=data.get("creator"),
            producer=data.get("producer"),
            creationDate=data.get("creationDate"),
            modDate=data.get("modDate"),
            total_pages=data.get("total_pages"),
            page_number=data.get("page_number"),
            content_type=data.get("content_type"),
            table_index=data.get("table_index"),
            image_index=data.get("image_index")
        )


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
