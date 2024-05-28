# Final implementation with VectorStore as the base class
from abc import ABC, abstractmethod
from typing import Union, List, Optional
from vectordbs.data_types import Document, QueryResult, QueryWithEmbedding, DocumentMetadataFilter

class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_documents(self, collection_name: str, documents: List[Document]):
        """Adds documents to the vector store."""

    @abstractmethod
    def retrieve_documents(self, query: Union[str, QueryWithEmbedding], 
                          collection_name: Optional[str] = None, 
                          limit: int = 10) -> List[QueryResult]:
        """Retrieves documents based on a query or query embedding.
        
        Args:
            query: Either a text string or a QueryWithEmbedding object.
            collection_name: Optional name of the collection.
            top_k: Number of top results to return. (Default: 4)
        
        Returns:
            A QueryResult object containing the retrieved documents and their scores.
        """

    @abstractmethod
    def query(self, 
              collection_name: str, 
              query: QueryWithEmbedding,
              number_of_results: int = 10, 
              filter: Optional[DocumentMetadataFilter] = None) -> List[QueryResult]:
        """Queries the vector store with filtering and query mode options.

        Args:
            query: Either a text string or a QueryWithEmbedding object.
            collection_name: Optional name of the collection.
            number_of_results: Number of top results to return. (Default: 10)
            filter: Optional metadata filter to apply to the search.
        
        Returns:
            A QueryResult object containing the retrieved documents and their scores.
        """

    @abstractmethod
    def delete_collection(self, collection_name: str):
        """Deletes a collection from the vector store."""

    @abstractmethod
    def delete_documents(self, 
                         document_ids: List[str], 
                         collection_name: Optional[str] = None):
        """Deletes documents by their IDs from the vector store."""
    
 
 
