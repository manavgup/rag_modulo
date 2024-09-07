import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from backend.vectordbs.utils.watsonx import generate_text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseQueryRewriter(ABC):
    @abstractmethod
    def rewrite(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        pass

class SimpleQueryRewriter(BaseQueryRewriter):
    def rewrite(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        logger.info(f"Applying simple query expansion to: {query}")
        expanded_query = f"{query} AND (relevant OR important OR key)"
        logger.info(f"Expanded query: {expanded_query}")
        return expanded_query

class HypotheticalDocumentEmbedding(BaseQueryRewriter):
    def __init__(self, max_tokens: int = 100):
        self.max_tokens = max_tokens

    def rewrite(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        logger.info(f"Applying Hypothetical Document Embedding to: {query}")
        prompt = f"Generate a concise hypothetical document (maximum {self.max_tokens} tokens) that would perfectly answer the query: {query}"
        if context:
            prompt += f"\nAdditional context: {context}"
        
        try:
            hde = generate_text(prompt, max_tokens=self.max_tokens)
            rewritten_query = f"{query} {hde}"
            logger.info(f"HDE rewritten query: {rewritten_query}")
            return rewritten_query
        except Exception as e:
            logger.error(f"Error in HDE query rewriting: {str(e)}")
            return query  # Fallback to original query in case of error

class QueryRewriter:
    def __init__(self, config: Dict[str, Any]):
        self.rewriters: List[BaseQueryRewriter] = []
        if config.get('use_simple_rewriter', True):
            self.rewriters.append(SimpleQueryRewriter())
        if config.get('use_hde', False):
            self.rewriters.append(HypotheticalDocumentEmbedding(config.get('hde_max_tokens', 100)))
        
        logger.info(f"Initialized QueryRewriter with {len(self.rewriters)} rewriters")

    def rewrite(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        logger.info(f"Starting query rewriting process for: {query}")
        for rewriter in self.rewriters:
            query = rewriter.rewrite(query, context)
        logger.info(f"Final rewritten query: {query}")
        return query

# Example usage
if __name__ == "__main__":
    config = {
        'use_simple_rewriter': True,
        'use_t5_rewriter': True,
        't5_model_name': 't5-small',
        'use_hde': True,
        'hde_max_tokens': 50
    }
    rewriter = QueryRewriter(config)
    original_query = "How long to fry pork chop?"
    rewritten_query = rewriter.rewrite(original_query)
    print(f"Original Query: {original_query}")
    print(f"Rewritten Query: {rewritten_query}")
