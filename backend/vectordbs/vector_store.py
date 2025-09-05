from abc import ABC, abstractmethod

from .data_types import Document, DocumentMetadataFilter, QueryResult, QueryWithEmbedding


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
        """Creates a collection in the vector store."""

    @abstractmethod
    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Adds documents to the vector store.

        Returns:
            List[str]: List of document IDs that were added
        """

    @abstractmethod
    def retrieve_documents(self, query: str, collection_name: str, number_of_results: int = 10) -> list[QueryResult]:
        """Retrieves documents based on a query or query embedding.

        Args:
            query: Either a text string or a QueryWithEmbedding object.
            collection_name: Name of the collection to search in.
            number_of_results: Number of top results to return. (Default: 10)

        Returns:
            A list of QueryResult objects containing the retrieved documents and their scores.
        """

    @abstractmethod
    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: DocumentMetadataFilter | None = None,
    ) -> list[QueryResult]:
        """Queries the vector store with filtering and query mode options.

        Args:
            collection_name: Name of the collection to search in.
            query: Either a text string or a QueryWithEmbedding object.
            number_of_results: Number of top results to return. (Default: 10)
            filter: Optional metadata filter to apply to the search.

        Returns:
            A list of QueryResult objects containing the retrieved documents and their scores.
        """

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """Deletes a collection from the vector store."""

    @abstractmethod
    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Deletes documents by their IDs from the vector store."""
