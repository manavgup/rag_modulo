"""Service layer for RAG pipeline execution and management."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from rag_solution.models.pipeline import PipelineConfig  # For type hints only

from datetime import datetime
import re
import time
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from core.config import settings
from core.custom_exceptions import ConfigurationError, ValidationError, NotFoundError
from core.logging_utils import get_logger

from rag_solution.data_ingestion.ingestion import DocumentStore
from rag_solution.evaluation.evaluator import RAGEvaluator
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.llm_provider import LLMProvider
from rag_solution.models.pipeline import PipelineConfig
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.query_rewriting.query_rewriter import QueryRewriter
from rag_solution.repository.pipeline_repository import PipelineConfigRepository
from rag_solution.retrieval.factories import RetrieverFactory
from rag_solution.retrieval.retriever import BaseRetriever
from rag_solution.schemas.llm_parameters_schema import LLMParametersOutput
from rag_solution.schemas.pipeline_schema import (
    PipelineConfigInput,
    PipelineConfigOutput,
    PipelineResult
)
from rag_solution.schemas.prompt_template_schema import PromptTemplateType
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.generation.providers.factory import LLMProviderFactory
from vectordbs.data_types import QueryResult, DocumentChunk, DocumentMetadata, VectorQuery
from vectordbs.factory import get_datastore
from vectordbs.vector_store import VectorStore


logger = get_logger("services.pipeline")


class PipelineService:
    """Service for managing and executing RAG pipelines."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self._pipeline_repository: Optional[PipelineConfigRepository] = None
        self._llm_parameters_service: Optional[LLMParametersService] = None
        self._prompt_template_service: Optional[PromptTemplateService] = None
        self._llm_provider_service: Optional[LLMProviderService] = None
        self._file_management_service: Optional[FileManagementService] = None
        
        # Core RAG components
        self.query_rewriter = QueryRewriter({})
        self.vector_store = get_datastore('milvus')
        self.evaluator = RAGEvaluator()
        
        # Lazy initialized components
        self._document_store: Optional[DocumentStore] = None
        self._retriever: Optional[BaseRetriever] = None

    # Property-based lazy initialization
    @property
    def pipeline_repository(self) -> PipelineConfigRepository:
        if self._pipeline_repository is None:
            self._pipeline_repository = PipelineConfigRepository(self.db)
        return self._pipeline_repository

    @property
    def llm_parameters_service(self) -> LLMParametersService:
        if self._llm_parameters_service is None:
            self._llm_parameters_service = LLMParametersService(self.db)
        return self._llm_parameters_service

    @property
    def prompt_template_service(self) -> PromptTemplateService:
        if self._prompt_template_service is None:
            self._prompt_template_service = PromptTemplateService(self.db)
        return self._prompt_template_service

    @property
    def llm_provider_service(self) -> LLMProviderService:
        if self._llm_provider_service is None:
            self._llm_provider_service = LLMProviderService(self.db)
        return self._llm_provider_service

    @property
    def file_management_service(self) -> FileManagementService:
        if self._file_management_service is None:
            self._file_management_service = FileManagementService(self.db)
        return self._file_management_service

    @property
    def document_store(self) -> DocumentStore:
        """Lazy initialization of document store."""
        if self._document_store is None:
            self._document_store = DocumentStore(self.vector_store, "default_collection")
        return self._document_store

    @property
    def retriever(self) -> BaseRetriever:
        """Lazy initialization of retriever."""
        if self._retriever is None:
            self._retriever = RetrieverFactory.create_retriever({}, self.document_store)
        return self._retriever

    async def initialize(self, collection_name: str) -> None:
        """Initialize pipeline components for a collection."""
        try:
            # Update document store collection
            self._document_store = DocumentStore(self.vector_store, collection_name)
            
            # Reinitialize retriever with new document store
            self._retriever = RetrieverFactory.create_retriever({}, self.document_store)
            
            # Load documents
            await self._load_documents()
            
            logger.info(f"Pipeline initialized for collection: {collection_name}")
        except Exception as e:
            logger.error(f"Pipeline initialization failed: {str(e)}")
            raise ConfigurationError(f"Pipeline initialization failed: {str(e)}")

    async def _load_documents(self) -> None:
        """Load and process documents from configured data sources."""
        try:
            await self.document_store.load_documents([])
            logger.info(f"Loaded documents into collection: {self.document_store.collection_name}")
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            raise ConfigurationError(f"Document loading failed: {str(e)}")

    def get_user_pipelines(self, user_id: UUID, include_system: bool = True) -> List[PipelineConfigOutput]:
        """Get all pipelines for a user."""
        pipelines = self.pipeline_repository.get_by_user(user_id, include_system)
        return [PipelineConfigOutput.model_validate(p) for p in pipelines]

    def get_pipeline_config(self, pipeline_id: UUID) -> Optional[PipelineConfigOutput]:
        """Retrieve pipeline configuration by ID."""
        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        return PipelineConfigOutput.model_validate(pipeline) if pipeline else None

    def create_pipeline(self, config_input: PipelineConfigInput) -> PipelineConfigOutput:
        """Create a new pipeline configuration."""
        # Validate provider exists
        if not self.llm_provider_service.get_provider_by_id(config_input.provider_id):
            raise ValidationError("Invalid provider ID")
            
        # Validate collection exists if specified
        if config_input.collection_id:
            collection = self.collection_service.get_collection(config_input.collection_id)
            if not collection:
                raise ValidationError("Invalid collection ID")
                
        return self.pipeline_repository.create(config_input.model_dump())

    def validate_pipeline(self, pipeline_id: UUID) -> PipelineResult:
        """Validate pipeline configuration."""
        pipeline: PipelineConfig = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError("Pipeline not found")

        errors = []
        warnings = []

        # Validate provider
        if not self.llm_provider_service.get_provider_by_id(pipeline.provider_id):
            errors.append("Invalid provider ID")

            # Basic validation using settings
            if pipeline.retriever not in ['vector', 'keyword', 'hybrid']:
                errors.append("Invalid retriever type")

        return PipelineResult(
            success=len(errors) == 0,
            error=errors[0] if errors else None,
            warnings=warnings
        )

    def test_pipeline(self, pipeline_id: UUID, query: str) -> PipelineResult:
        """Test pipeline with a sample query."""
        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError("Pipeline not found")

        try:
            # Initialize retriever with basic config
            retriever_config = {
                'type': pipeline.retriever,
                'vector_weight': settings.vector_weight if pipeline.retriever == 'hybrid' else None
            }
            self.retriever = RetrieverFactory.create_retriever(
                retriever_config,
                self.document_store
            )

            # Process query
            rewritten_query = self.query_rewriter.rewrite(query)
            vector_query = VectorQuery(
                text=rewritten_query,
                number_of_results=settings.number_of_results
            )
            results = self.retriever.retrieve("test_collection", vector_query)

            return PipelineResult(
                success=True,
                rewritten_query=rewritten_query,
                query_results=results[:3]
            )

        except Exception as e:
            logger.error(f"Pipeline test failed: {str(e)}")
            return PipelineResult(
                success=False,
                error=str(e)
            )

    def set_default_pipeline(self, pipeline_id: UUID) -> PipelineConfigOutput:
        """
        Set a pipeline as the default.
        
        Args:
            pipeline_id: ID of the pipeline to set as default
            
        Returns:
            Updated pipeline configuration
            
        Raises:
            NotFoundError: If pipeline not found
            ValidationError: If update fails
        """
        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError("Pipeline not found")

        # Use collection-specific clear
        if pipeline.collection_id:
            self.pipeline_repository.clear_collection_defaults(pipeline.collection_id)
        
        # Update using input schema
        return self.pipeline_repository.update(
            pipeline_id,
            PipelineConfigInput(**{**pipeline.model_dump(), "is_default": True})
        )

    def _prepare_query(self, query: str) -> str:
        """Sanitize and prepare query for execution."""
        clean_query = re.sub(r'\s+(AND|OR)\s+', ' ', query)
        clean_query = re.sub(r'[\(\)]', '', clean_query)
        return clean_query.strip()

    def _format_context(self, template_id: UUID, query_results: List[QueryResult]) -> str:
        """Format retrieved contexts using template's context strategy."""
        try:
            texts = [result.chunk.text for result in query_results]
            return self.prompt_template_service.apply_context_strategy(template_id, texts)
        except Exception as e:
            logger.error(f"Error formatting context: {str(e)}")
            return "\n\n".join(texts)

    def _validate_configuration(self, pipeline_id: UUID, user_id: UUID) -> Tuple[PipelineConfigOutput, LLMParametersOutput, LLMProvider]:
        """Validate pipeline configuration and return required components."""
        # Get pipeline configuration as schema
        pipeline_config = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline_config:
            raise ConfigurationError("Pipeline configuration not found")

        # Get and validate LLM parameters
        llm_parameters = self.llm_parameters_service.get_user_default(user_id)
        if not llm_parameters:
            raise ConfigurationError("No default LLM parameters found")

        # Get and validate provider - need to get actual provider instance, not just schema
        provider_output = self.llm_provider_service.get_provider_by_id(pipeline_config.provider_id)
        if not provider_output:
            raise ConfigurationError("LLM provider not found")

        # Get provider factory instance
        try:
            provider_factory = LLMProviderFactory(self.db)
            provider = provider_factory.get_provider(provider_output.name)
            if not provider:
                raise ConfigurationError("Failed to initialize LLM provider")
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize LLM provider: {str(e)}")

        return pipeline_config, llm_parameters, provider

    def _get_templates(self, user_id: UUID) -> Tuple[PromptTemplate, Optional[PromptTemplate]]:
        """
        Get required templates for the pipeline.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Tuple of (RAG template, optional evaluation template)
            
        Raises:
            NotFoundError: If required template not found
        """
        rag_template = self.prompt_template_service.get_by_type(
            PromptTemplateType.RAG_QUERY,
            user_id
        )
        if not rag_template:
            raise NotFoundError("User's RAG query template not found")

        eval_template = None
        if settings.runtime_eval:
            eval_template = self.prompt_template_service.get_by_type(
                PromptTemplateType.RESPONSE_EVALUATION,
                user_id
            )

        return rag_template, eval_template

    def _retrieve_documents(self, query: str, collection_name: str) -> List[QueryResult]:
        """
        Retrieve relevant documents for the query.
        
        Args:
            query: The query text
            collection_id: ID of the collection to search
            
        Returns:
            List of query results
        """
        vector_query = VectorQuery(
            text=query,
            number_of_results=settings.number_of_results
        )
        results = self.retriever.retrieve(collection_name, vector_query)
        logger.info(f"Retrieved {len(results)} documents")
        return results

    def _generate_answer(
        self,
        query: str,
        context: str,
        provider: LLMProvider,
        llm_params: LLMParameters,
        template: PromptTemplate
    ) -> str:
        """
        Generate answer using the LLM.
        
        Args:
            query: The query text
            context: The context text
            provider: The LLM provider
            llm_params: LLM parameters
            template: The prompt template
            
        Returns:
            Generated answer text
        """
        try:
            formatted_prompt = self.prompt_template_service.format_prompt(
                template.id,
                {
                    "context": context,
                    "question": query,
                    "max_length": llm_params.max_new_tokens
                }
            )

            answer = provider.generate_text(
                prompt=formatted_prompt,
                model_parameters=llm_params
            )
            return answer[0] if isinstance(answer, list) else answer
        except Exception as e:
            logger.error(f"Error in generation: {str(e)}")
            return "I apologize, but I encountered an error while generating the answer."

    async def _evaluate_response(
        self,
        query: str,
        answer: str,
        context: str,
        template: PromptTemplate
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate generated response if enabled.
        
        Args:
            query: The original query
            answer: The generated answer
            context: The context used
            template: The evaluation template
            
        Returns:
            Optional evaluation results
        """
        try:
            eval_prompt = self.prompt_template_service.format_prompt(
                template.id,
                {
                    "context": context,
                    "question": query,
                    "answer": answer
                }
            )
            return await self.evaluator.evaluate(
                question=query,
                answer=answer,
                context=context,
                eval_prompt=eval_prompt
            )
        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            return {"error": str(e)}

    async def execute_pipeline(self, search_input: SearchInput, user_id: UUID, collection_name: str) -> PipelineResult:
        """
        Execute the RAG pipeline.
        
        Args:
            search_input: Search parameters and query
            user_id: ID of the user
            
        Returns:
            PipelineResult containing generated answer and metadata
        """
        start_time = time.time()
        logger.info("Starting RAG pipeline execution")

        try:
            # Configuration validation
            pipeline_config, llm_parameters, provider = self._validate_configuration(search_input.pipeline_id, user_id)
            rag_template, eval_template = self._get_templates(user_id)

            # Query processing and retrieval
            clean_query = self._prepare_query(search_input.question)
            rewritten_query = self.query_rewriter.rewrite(clean_query)
            
            query_results = self._retrieve_documents(rewritten_query, collection_name)

            # Answer generation
            if not query_results:
                generated_answer = "I apologize, but I couldn't find any relevant documents."
            else:
                context_text = self._format_context(rag_template.id, query_results)
                generated_answer = self._generate_answer(
                    clean_query, context_text, provider, llm_parameters, rag_template
                )

            # Optional evaluation
            evaluation_result = None
            if settings.runtime_eval and eval_template and query_results:
                context_text = self._format_context(rag_template.id, query_results)
                evaluation_result = await self._evaluate_response(
                    clean_query, generated_answer, context_text, eval_template
                )

            # Prepare result
            execution_time = time.time() - start_time
            logger.info(f"Pipeline executed in {execution_time:.2f} seconds")

            return PipelineResult(
                success=True,
                rewritten_query=rewritten_query,
                query_results=query_results,
                generated_answer=generated_answer,
                evaluation=evaluation_result
            )

        except (ValidationError, NotFoundError, ConfigurationError) as e:
            logger.error(f"{type(e).__name__}: {str(e)}")
            return PipelineResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            return PipelineResult(success=False, error=f"Pipeline execution failed: {str(e)}")
