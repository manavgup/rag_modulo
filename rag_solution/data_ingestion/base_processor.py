# base_processor.py
from abc import ABC, abstractmethod
from typing import AsyncIterable

from config import settings
from vectordbs.data_types import Document

from .chunking import get_chunking_method


class BaseProcessor(ABC):
    def __init__(self) -> None:
        self.min_chunk_size: int = settings.min_chunk_size
        self.max_chunk_size: int = settings.max_chunk_size
        self.semantic_threshold: float = settings.semantic_threshold
        self.chunking_method = get_chunking_method()

    @abstractmethod
    def process(self, file_path: str) -> AsyncIterable[Document]:
        pass
