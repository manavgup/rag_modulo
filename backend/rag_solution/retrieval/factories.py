from typing import Dict, Any
from rag_solution.data_ingestion.ingestion import DocumentStore
from .retriever import BaseRetriever, VectorRetriever, KeywordRetriever, HybridRetriever

class RetrieverFactory:
    @staticmethod
    def create_retriever(config: Dict[str, Any], document_store: DocumentStore) -> BaseRetriever:
        """
        Create and return a retriever based on the given configuration.

        Args:
            config (Dict[str, Any]): Configuration for the retriever.
            document_store (DocumentStore): The document store to use for retrieval.

        Returns:
            BaseRetriever: An instance of a retriever.

        Raises:
            ValueError: If an invalid retriever type is specified in the configuration.
        """
        retriever_type = config.get('type', 'hybrid')
        
        if retriever_type == 'hybrid':
            return HybridRetriever(
                document_store, 
                config.get('vector_weight', 0.7)
            )
        elif retriever_type == 'vector':
            return VectorRetriever(document_store)
        elif retriever_type == 'keyword':
            return KeywordRetriever(document_store)
        else:
            raise ValueError(f"Invalid retriever type: {retriever_type}")