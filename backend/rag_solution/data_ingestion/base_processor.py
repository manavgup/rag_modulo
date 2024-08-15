import logging
from abc import ABC, abstractmethod
from typing import Iterable

from backend.core.config import settings
from backend.rag_solution.data_ingestion.chunking import get_chunking_method
from backend.vectordbs.data_types import Document

logging.basicConfig(level=logging.INFO)


class BaseProcessor(ABC):
    """
    Abstract base class for document processors.

    Attributes:
        min_chunk_size (int): Minimum chunk size for chunking documents.
        max_chunk_size (int): Maximum chunk size for chunking documents.
        semantic_threshold (float): Semantic threshold for chunking documents.
        chunking_method: Method used for chunking documents.
    """

    def __init__(self) -> None:
        self.min_chunk_size: int = settings.min_chunk_size
        self.max_chunk_size: int = settings.max_chunk_size
        self.semantic_threshold: float = settings.semantic_threshold
        self.chunking_method = get_chunking_method()

    @abstractmethod
    def process(self, file_path: str) -> Iterable[Document]:
        """
        Abstract method to process a file and yield documents.

        Args:
            file_path (str): The path to the file to be processed.

        Yields:
            Document: An instance of Document containing the processed data.
        """
        pass
