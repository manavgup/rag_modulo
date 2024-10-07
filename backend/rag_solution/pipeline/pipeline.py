from typing import List, Dict, Any
from rag_solution.query_rewriting.query_rewriter import QueryRewriter
from rag_solution.retrieval.retriever import Retriever
from vectordbs.factory import get_datastore

class Pipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.query_rewriter = QueryRewriter(config.get('query_rewriting', {}))
        
        vector_store = get_datastore(config.get('vector_store', 'milvus'))
        documents = self._load_documents()  # Implement this method to load your documents
        self.retriever = Retriever(config.get('retrieval', {}), vector_store, documents)
        
        # Lazy import to avoid circular dependency
        from rag_solution.generation.generator import Generator
        self.generator = Generator(config.get('generation', {}))

    def _load_documents(self) -> List[Dict[str, Any]]:
        # Implement this method to load your documents from your data source
        # For example, you might load them from a database or a file
        # Return a list of dictionaries, where each dictionary represents a document
        # with 'id' and 'content' keys
        return [
            {"id": 1, "content": "Sample document 1"},
            {"id": 2, "content": "Sample document 2"},
            # Add more documents...
        ]

    def process(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        # Query rewriting
        rewritten_query = self.query_rewriter.rewrite(query, context)
        
        # Retrieval
        retrieved_documents = self.retriever.retrieve(rewritten_query, k=self.config.get('top_k', 5))
        
        # Generation
        response = self.generator.generate(rewritten_query, retrieved_documents)
        
        return {
            'original_query': query,
            'rewritten_query': rewritten_query,
            'retrieved_documents': retrieved_documents,
            'response': response
        }

# Example usage
if __name__ == "__main__":
    config = {
        'query_rewriting': {
            'use_simple_rewriter': True,
            'use_t5_rewriter': True,
            't5_model_name': 't5-small',
            'use_hde': True
        },
        'retrieval': {
            'use_hybrid': True,
            'vector_weight': 0.7
        },
        'generation': {
            'type': 'huggingface',
            'model_name': 'gpt2'
        },
        'vector_store': 'milvus',
        'top_k': 5
    }

    pipeline = Pipeline(config)
    query = "What is the theory of relativity?"
    result = pipeline.process(query)
    
    print(f"Original Query: {result['original_query']}")
    print(f"Rewritten Query: {result['rewritten_query']}")
    print("Retrieved Documents:")
    for doc in result['retrieved_documents']:
        print(f"  - ID: {doc['id']}, Score: {doc['score']}, Content: {doc['content']}")
    print(f"Generated Response: {result['response']}")