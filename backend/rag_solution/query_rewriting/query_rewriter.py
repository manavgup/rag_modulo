import logging
from abc import ABC, abstractmethod
from typing import Any

# Note: Keeping legacy import for generate_text as this utility doesn't have user context
# required by LLMProviderFactory pattern. This usage is acceptable for utility functions.
from vectordbs.utils.watsonx import generate_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryRewriterError(Exception):
    """Base exception class for QueryRewriter errors"""


class InvalidQueryError(QueryRewriterError):
    """Exception raised for invalid queries"""


class ConfigurationError(QueryRewriterError):
    """Exception raised for invalid configuration"""


class RewriterError(QueryRewriterError):
    """Exception raised when a specific rewriter fails"""


class BaseQueryRewriter(ABC):
    @abstractmethod
    def rewrite(self, query: str, context: dict[str, Any] | None = None) -> str:
        pass


class SimpleQueryRewriter(BaseQueryRewriter):
    def rewrite(self, query: str, context: dict[str, Any] | None = None) -> str:  # noqa: ARG002
        """Simple query rewriter that returns query unchanged.

        Generic boolean expansion like 'AND (relevant OR important OR key)' adds no value
        for semantic/vector search, as vector embeddings already capture semantic relevance.

        Args:
            query: The original search query
            context: Optional context (unused in simple rewriter)

        Returns:
            The original query unchanged
        """
        logger.info(f"Simple query rewriter: returning query unchanged: {query}")
        return query


class HypotheticalDocumentEmbedding(BaseQueryRewriter):
    def __init__(self: Any, max_tokens: int = 100, timeout: int = 30, max_retries: int = 3) -> None:
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries

    def rewrite(self, query: str, context: dict[str, Any] | None = None) -> str:
        logger.info(f"Applying Hypothetical Document Embedding to: {query}")
        prompt = f"Generate a concise hypothetical document (maximum {self.max_tokens} tokens) that would perfectly answer the query: {query}"
        if context:
            prompt += f"\nAdditional context: {context}"

        try:
            # Pass parameters through the params dict
            params = {"max_tokens": self.max_tokens, "timeout": self.timeout, "max_retries": self.max_retries}
            hde = generate_text(prompt, params=params)
            if not hde:
                logger.warning("Failed to generate HDE, returning original query")
                return query
            rewritten_query = f"{query} {hde}"
            logger.info(f"HDE rewritten query: {rewritten_query}")
            return rewritten_query
        except Exception as e:
            logger.error(f"Error in HDE query rewriting: {e!s}")
            raise RewriterError(f"HypotheticalDocumentEmbedding failed: {e!s}") from e


class QueryRewriter:
    def __init__(self, config: dict[str, Any]) -> None:
        self.rewriters: list[BaseQueryRewriter] = []
        try:
            if not isinstance(config, dict):
                raise ConfigurationError("Config must be a dictionary")

            if config.get("use_simple_rewriter", True):
                self.rewriters.append(SimpleQueryRewriter())
            if config.get("use_hde", False):
                hde_max_tokens = config.get("hde_max_tokens", 100)
                hde_timeout = config.get("hde_timeout", 30)
                hde_max_retries = config.get("hde_max_retries", 3)
                if not isinstance(hde_max_tokens, int) or hde_max_tokens <= 0:
                    raise ConfigurationError("hde_max_tokens must be a positive integer")
                if not isinstance(hde_timeout, int) or hde_timeout <= 0:
                    raise ConfigurationError("hde_timeout must be a positive integer")
                if not isinstance(hde_max_retries, int) or hde_max_retries < 0:
                    raise ConfigurationError("hde_max_retries must be a non-negative integer")
                self.rewriters.append(HypotheticalDocumentEmbedding(hde_max_tokens, hde_timeout, hde_max_retries))

            logger.info(f"Initialized QueryRewriter with {len(self.rewriters)} rewriters")
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during QueryRewriter initialization: {e!s}")
            raise ConfigurationError(f"Failed to initialize QueryRewriter: {e!s}") from e

    def rewrite(self, query: str, context: dict[str, Any] | None = None) -> str:
        if not query or not query.strip():
            logger.error("Empty query provided")
            raise InvalidQueryError("Query cannot be empty")

        logger.info(f"Starting query rewriting process for: {query}")
        original_query = query
        for rewriter in self.rewriters:
            try:
                query = rewriter.rewrite(query, context)
            except RewriterError as e:
                logger.warning(f"Rewriter failed: {e!s}. Continuing with next rewriter.")
            except Exception as e:
                logger.error(f"Unexpected error in rewriter: {e!s}")
                # Fall back to the previous query state
                logger.info(f"Falling back to previous query state: {query}")

        if query == original_query:
            logger.warning("Query remained unchanged after rewriting process")
        else:
            logger.info(f"Final rewritten query: {query}")
        return query


# Example usage
if __name__ == "__main__":
    config = {
        "use_simple_rewriter": True,
        "use_hde": True,
        "hde_max_tokens": 50,
        "hde_timeout": 30,
        "hde_max_retries": 3,
    }
    try:
        rewriter = QueryRewriter(config)
        original_query = "How long to fry pork chop?"
        rewritten_query = rewriter.rewrite(original_query)
        print(f"Original Query: {original_query}")
        print(f"Rewritten Query: {rewritten_query}")
    except QueryRewriterError as e:
        print(f"Error occurred: {e!s}")
    except Exception as e:
        print(f"Unexpected error: {e!s}")
