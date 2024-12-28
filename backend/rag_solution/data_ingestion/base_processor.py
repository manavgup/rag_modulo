import logging
from abc import ABC, abstractmethod
from typing import Iterable, Dict, Any, AsyncIterable
import os
from datetime import datetime
from core.config import settings
from rag_solution.data_ingestion.chunking import get_chunking_method
from vectordbs.data_types import Document, DocumentMetadata

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
    
    def extract_metadata(self, file_path: str) -> DocumentMetadata:
        """
        Extract basic metadata from the file.

        Args:
            file_path (str): The path to the file.

        Returns:
            DocumentMetadata: Metadata object containing file information.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If the file cannot be accessed.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        file_stat = os.stat(file_path)
        filename = os.path.basename(file_path)
        
        return DocumentMetadata(
            document_name=filename,
            title=filename,  # Default to filename if no specific title
            author=None,
            subject=None,
            keywords={},
            creator=None,
            producer=None,
            creation_date=datetime.fromtimestamp(file_stat.st_ctime),
            mod_date=datetime.fromtimestamp(file_stat.st_mtime),
            total_pages=None,  # To be set by specific processors
            total_chunks=None,  # To be set after chunking
        )

    @abstractmethod
    async def process(self, file_path: str, document_id: str) -> AsyncIterable[Document]:
        """
        Process a document file and generate Document objects.
        
        This abstract method must be implemented by specific processors to handle
        their respective document types. It should handle the complete document
        processing pipeline including parsing, chunking, and metadata extraction.
        
        Args:
            file_path: Path to the document file.
            
        Yields:
            Document: Processed document objects containing chunks and metadata.
            
        Raises:
            DocumentProcessingError: If there is an error processing the document.
            NotImplementedError: If the processor doesn't implement this method.
        """
        pass
