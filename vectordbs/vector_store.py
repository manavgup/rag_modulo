from abc import ABC, abstractmethod
from typing import List, Optional, Union
import asyncio

from vectordbs.data_types import Document, DocumentMetadataFilter, QueryResult, QueryWithEmbedding


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    async def create_collection_async(self, collection_name: str, metadata: Optional[dict] = None):
        """Creates a collection in the vector store asynchronously."""
        pass

    @abstractmethod
    async def add_documents_async(self, collection_name: str, documents: List[Document]):
        """Adds documents to the vector store asynchronously."""
        pass

    @abstractmethod
    async def retrieve_documents_async(
        self,
        query: str,
        collection_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[QueryResult]:
        """Retrieves documents asynchronously based on a query or query embedding.

        Args:
            query: Either a text string or a QueryWithEmbedding object.
            collection_name: Optional name of the collection.
            limit: Number of top results to return. (Default: 10)

        Returns:
            A list of QueryResult objects containing the retrieved documents and their scores.
        """
        pass

    @abstractmethod
    async def query_async(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: Optional[DocumentMetadataFilter] = None,
    ) -> List[QueryResult]:
        """Queries the vector store asynchronously with filtering and query mode options.

        Args:
            query: Either a text string or a QueryWithEmbedding object.
            collection_name: Optional name of the collection.
            number_of_results: Number of top results to return. (Default: 10)
            filter: Optional metadata filter to apply to the search.

        Returns:
            A list of QueryResult objects containing the retrieved documents and their scores.
        """
        pass

    @abstractmethod
    async def delete_collection_async(self, collection_name: str):
        """Deletes a collection from the vector store asynchronously."""
        pass

    @abstractmethod
    async def delete_documents_async(
        self, document_ids: List[str], collection_name: Optional[str] = None
    ):
        """Deletes documents by their IDs from the vector store asynchronously."""
        pass

