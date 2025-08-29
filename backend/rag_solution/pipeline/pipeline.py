"""
DEPRECATED: This module is deprecated in favor of pipeline_service.py.
It is kept temporarily for reference during the service migration.
New code should use rag_solution.services.pipeline_service.PipelineService instead.
"""

import logging
import warnings

warnings.warn(
    "The pipeline.py module is deprecated and will be removed in a future version. " "Use pipeline_service.py instead.",
    DeprecationWarning,
    stacklevel=2,
)

from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from core.config import settings
from rag_solution.data_ingestion.ingestion import DocumentStore
from rag_solution.evaluation.evaluator import RAGEvaluator
from rag_solution.generation.providers.base import LLMBase
from rag_solution.query_rewriting.query_rewriter import QueryRewriter
from rag_solution.retrieval.factories import RetrieverFactory
from rag_solution.retrieval.retriever import BaseRetriever
from rag_solution.schemas.llm_parameters_schema import LLMParametersBase
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from vectordbs.data_types import QueryResult, VectorQuery
from vectordbs.factory import get_datastore
from vectordbs.vector_store import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    """Result from pipeline processing.

    Attributes:
        rewritten_query: Query after rewriting
        query_results: List of vector similarity matches
        generated_answer: Generated answer text
        evaluation: Optional evaluation results
    """

    rewritten_query: str
    query_results: list[QueryResult]
    generated_answer: str
    evaluation: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

    def get_sorted_results(self) -> list[QueryResult]:
        """Get results sorted by similarity score."""
        return sorted(self.query_results, key=lambda x: x.score, reverse=True)

    def get_top_k_results(self, k: int) -> list[QueryResult]:
        """Get top k results by similarity score."""
        return self.get_sorted_results()[:k]

    def get_all_texts(self) -> list[str]:
        """Get all chunk texts from results."""
        return [result.chunk.text for result in self.query_results]

    def get_unique_document_ids(self) -> set[str]:
        """Get set of unique document IDs from results."""
        return {
            result.document_id  # Using the convenience property
            for result in self.query_results
            if result.document_id is not None
        }

    def get_results_for_document(self, document_id: str) -> list[QueryResult]:
        """Get all results from a specific document."""
        return [result for result in self.query_results if result.document_id == document_id]


class Pipeline:
    """Main RAG pipeline implementation.

    This class orchestrates the entire RAG process:
    1. Query rewriting
    2. Document retrieval
    3. Answer generation
    4. Optional evaluation
    """

    def __init__(
        self,
        db: Session,
        provider: LLMBase,  # Pre-configured provider instance
        model_parameters: LLMParametersBase,  # LLM generation parameters
        prompt_template: PromptTemplateBase,  # Prompt template for generation
        collection_name: str = "default_collection",
    ):
        """Initialize the RAG Pipeline.

        Args:
            db: SQLAlchemy database session
            provider: Pre-configured LLM provider instance
            model_parameters: LLM generation parameters
            prompt_template: Prompt template for generation
            collection_name: Name of the collection to use
        """
        self.db: Session = db
        self.provider: LLMBase = provider
        self.model_parameters: LLMParametersBase = model_parameters
        self.prompt_template: PromptTemplateBase = prompt_template

        # Initialize core RAG components with strong typing
        self.query_rewriter: QueryRewriter = QueryRewriter({})
        self.vector_store: VectorStore = get_datastore("milvus")
        self.collection_name: str = collection_name
        self.document_store: DocumentStore = DocumentStore(self.vector_store, self.collection_name)
        self.retriever: BaseRetriever = RetrieverFactory.create_retriever({}, self.document_store)
        self.evaluator: RAGEvaluator = RAGEvaluator()

    async def initialize(self) -> None:
        """Initialize the pipeline and load documents."""
        await self._load_documents()

    async def _load_documents(self) -> None:
        """Load and process documents from configured data sources."""
        try:
            await self.document_store.load_documents([])  # Empty list since we're not loading documents in tests
            logger.info(f"Loaded documents into collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error loading documents: {e!s}")
            raise

    async def process(self, query: str, collection_name: str, context: dict[str, Any] | None = None) -> PipelineResult:
        """Process a query through the RAG pipeline.

        Args:
            query: The user's query string
            collection_name: Name of the collection to search in
            context: Optional context information for query processing

        Returns:
            PipelineResult: Contains the generated answer and supporting information
        """
        # Validate query first, before try block
        if not query.strip():
            raise ValueError("Query cannot be empty")

        try:
            # 1: Check provider first
            if self.provider.client is None:
                logger.error("Provider client is not initialized")
                raise Exception("Provider client is not initialized")

            # 2: Query Rewriting
            rewritten_query = self.query_rewriter.rewrite(query, context)
            logger.info(f"Rewritten query: {rewritten_query}")
            logger.info(f"Going with original query: {query}")

            # 3: Vector Retrieval
            vector_query = VectorQuery(text=query, number_of_results=settings.number_of_results)
            query_results: list[QueryResult] = self.retriever.retrieve(collection_name, vector_query)
            logger.info(f"Retrieved {len(query_results)} documents")

            # Get all texts from retrieved documents
            retrieved_texts = [result.chunk.text for result in query_results]
            context_text = "\n\n".join(retrieved_texts)

            # 4: Format prompt and generate answer
            try:
                if not retrieved_texts:
                    logger.warning("No documents found for query")
                    generated_answer = (
                        "I apologize, but I couldn't find any relevant documents to answer your question."
                    )
                else:
                    try:
                        # Use the template's format_prompt method to create the complete prompt
                        formatted_prompt = self.prompt_template.format_prompt(context=context_text, question=query)
                        logger.info(f"Generated prompt with context length: {len(formatted_prompt)}")

                        # Generate answer using provider with pre-formatted prompt
                        # Since we've already formatted the prompt, don't pass template to avoid double formatting
                        generated_answer = self.provider.generate_text(
                            prompt=formatted_prompt, model_parameters=self.model_parameters
                        )
                    except ValueError as e:
                        # Handle specific template formatting errors
                        logger.error(f"Error formatting prompt: {e!s}")
                        # Fall back to using query directly if template formatting fails
                        formatted_prompt = f"{self.prompt_template.system_prompt}\n{self.prompt_template.context_prefix}{context_text}\n{self.prompt_template.query_prefix}{query}\n{self.prompt_template.answer_prefix}"
                        generated_answer = self.provider.generate_text(
                            prompt=formatted_prompt, model_parameters=self.model_parameters
                        )

                    if isinstance(generated_answer, list):
                        generated_answer = generated_answer[0]  # Take first response if list returned
            except Exception as e:
                logger.error(f"Error generating answer: {e!s}")
                generated_answer = ""

            logger.info(f"Generated answer: {generated_answer}")

            # 4: Evaluation
            logger.info("Now going to evaluate the results")
            try:
                if settings.runtime_eval:
                    evaluation_result = await self.evaluator.evaluate(
                        question=query, answer=generated_answer, context=context_text
                    )
                else:
                    evaluation_result = None
            except Exception as e:
                logger.error(f"Evaluation failed: {e}")
                evaluation_result = {"error": f"Evaluation failed: {e!s}"}

            return PipelineResult(
                rewritten_query=rewritten_query,
                query_results=query_results,
                generated_answer=generated_answer,
                evaluation=evaluation_result,
            )
        except Exception as e:
            logger.error(f"Error in pipeline: {e!s}")
            return PipelineResult(
                rewritten_query=rewritten_query if "rewritten_query" in locals() else "",
                query_results=[],
                generated_answer="",
                evaluation={"error": str(e)},
            )
