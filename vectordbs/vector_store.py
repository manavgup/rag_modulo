# Final implementation with VectorStore as the base class
from genai import Client
from typing import Union, List, Optional
from chromadb import Collection as ChromaCollection
from pymilvus import Collection as PyMilvusCollection
from data_types import Document, DocumentQuery, QueryResult

class VectorStore:
    def create_collection(self, name: str, embedding_model_id: str, client: Client, 
                          create_new: bool = False) -> Union[ChromaCollection, PyMilvusCollection]:
        """
        Create a new collection with the specified name.
        
        :param name: The name of the collection to be created.
        """
        raise NotImplementedError("create_collection method must be implemented by subclass")

    def delete_collection(self, name: str):
        """
        Delete a collection with the specified name.
        
        :param name: The name of the collection to be deleted.
        """
        raise NotImplementedError("delete_collection method must be implemented by subclass")

    def add_documents(self, documents: List[Document], collection_name: Optional[str] = None):
        """Adds documents to the vector store."""
        """
        Add documents to a collection.

        :param collection_name: The name of the collection to add documents to.
        :param documents: A list of documents to be added.
        """
        raise NotImplementedError("add_documents method must be implemented by subclass")

    def retrieve_documents(self, query: DocumentQuery, 
                          collection_name: Optional[str] = None, top_k: int = 4) -> QueryResult:
        """Retrieves documents based on a query or query embedding.
        
        Args:
            query: Either a text string or a QueryWithEmbedding object.
            collection_name: Optional name of the collection.
            top_k: Number of top results to return. (Default: 4)
        
        Returns:
            A QueryResult object containing the retrieved documents and their scores.
        """
    @abstractmethod
    def query(self, query: DocumentQuery,
              collection_name: Optional[str] = None, 
              top_k: int = 4) -> QueryResult:
        """Queries the vector store with filtering and query mode options.

        Args:
            query: Either a text string or a QueryWithEmbedding object.
            collection_name: Optional name of the collection.
            top_k: Number of top results to return. (Default: 4)
            filter: Optional metadata filter to apply to the search.
            mode: Optional query mode (sparse, hybrid, etc.).
        
        Returns:
            A QueryResult object containing the retrieved documents and their scores.
        """
        
    def delete_data(self, collection_name: str, criteria: str):
        """
        Delete data from a collection based on certain criteria.

        :param collection_name: The name of the collection to delete data from.
        :param criteria: The criteria to delete data.
        """
        raise NotImplementedError("delete_data method must be implemented by subclass")
    
    def _print_info(self, msg: str):
        # TODO: logger
        print(msg)

    def _print_err(self, msg: str):
        # TODO: logger
        print(msg)
