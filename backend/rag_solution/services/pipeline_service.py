"""Service layer for RAG pipeline execution and management."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag_solution.models.pipeline import PipelineConfig  # For type hints only

import re
import time
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from core.custom_exceptions import ConfigurationError, LLMProviderError, NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.data_ingestion.ingestion import DocumentStore
from rag_solution.evaluation.evaluator import RAGEvaluator
from rag_solution.generation.providers.base import LLMBase
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.models.llm_provider import LLMProvider
from rag_solution.models.pipeline import PipelineConfig
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.query_rewriting.query_rewriter import QueryRewriter
from rag_solution.repository.pipeline_repository import PipelineConfigRepository
from rag_solution.retrieval.factories import RetrieverFactory
from rag_solution.retrieval.retriever import BaseRetriever
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.pipeline_schema import PipelineConfigInput, PipelineConfigOutput, PipelineResult
from rag_solution.schemas.prompt_template_schema import PromptTemplateType
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService
from vectordbs.data_types import QueryResult, VectorQuery
from vectordbs.factory import get_datastore

logger = get_logger("services.pipeline")


class PipelineService:
    """Service for managing and executing RAG pipelines."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self._pipeline_repository: PipelineConfigRepository | None = None
        self._llm_parameters_service: LLMParametersService | None = None
        self._prompt_template_service: PromptTemplateService | None = None
        self._llm_provider_service: LLMProviderService | None = None
        self._file_management_service: FileManagementService | None = None

        # Core RAG components
        self.query_rewriter = QueryRewriter({})
        self.vector_store = get_datastore("milvus")
        self.evaluator = RAGEvaluator()

        # Lazy initialized components
        self._document_store: DocumentStore | None = None
        self._retriever: BaseRetriever | None = None

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
            logger.error(f"Pipeline initialization failed: {e!s}")
            raise ConfigurationError(f"Pipeline initialization failed: {e!s}")

    async def _load_documents(self) -> None:
        """Load and process documents from configured data sources."""
        try:
            await self.document_store.load_documents([])
            logger.info(f"Loaded documents into collection: {self.document_store.collection_name}")
        except Exception as e:
            logger.error(f"Error loading documents: {e!s}")
            raise ConfigurationError(f"Document loading failed: {e!s}")

    def get_user_pipelines(self, user_id: UUID) -> list[PipelineConfigOutput]:
        """Get all pipelines for a user."""
        try:
            pipelines = self.pipeline_repository.get_by_user(user_id)

            # If no pipelines exist, create a default one for existing users
            if not pipelines:
                logger.info(f"No pipelines found for user {user_id}, creating default pipeline")

                # Get user's provider or system default
                provider = self.llm_provider_service.get_user_provider(user_id)
                if not provider:
                    # Try to get system default provider
                    providers = self.llm_provider_service.get_all_providers()
                    if providers:
                        provider = providers[0]  # Use first available provider
                    else:
                        logger.error("No LLM providers available in the system")
                        raise HTTPException(
                            status_code=500, detail="No LLM providers available. Please contact administrator."
                        )

                # Create default pipeline for existing user
                try:
                    default_pipeline = self.initialize_user_pipeline(user_id, provider.id)
                    return [default_pipeline]
                except Exception as init_error:
                    logger.error(f"Failed to create default pipeline: {init_error!s}")
                    raise HTTPException(status_code=500, detail=f"Failed to create default pipeline: {init_error!s}")

            return pipelines  # Already PipelineConfigOutput objects from repository
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logger.error(f"Failed to get user pipelines: {e!s}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve pipeline configurations: {e!s}")

    def get_default_pipeline(self, user_id: UUID, collection_id: UUID | None = None) -> PipelineConfigOutput | None:
        """Get default pipeline for a user or collection.

        Args:
            user_id: User UUID
            collection_id: Optional collection UUID to get collection-specific default

        Returns:
            Optional[PipelineConfigOutput]: Default pipeline configuration if found
        """
        try:
            if collection_id:
                pipeline = self.pipeline_repository.get_collection_default(collection_id)
                if pipeline:
                    return pipeline

            # Fall back to user default if no collection default exists
            return self.pipeline_repository.get_user_default(user_id)
        except Exception as e:
            logger.error(f"Failed to get default pipeline: {e!s}")
            return None

    def initialize_user_pipeline(self, user_id: UUID, provider_id: UUID) -> PipelineConfigOutput:
        """Initialize default pipeline for a new user.

        Args:
            user_id: User UUID
            provider_id: Provider UUID to use for pipeline

        Returns:
            PipelineConfigOutput: Created default pipeline
        """
        try:
            pipeline_input = PipelineConfigInput(
                name="Default Pipeline",
                description="Default RAG pipeline configuration",
                user_id=user_id,
                provider_id=provider_id,
                chunking_strategy=settings.chunking_strategy,
                embedding_model=settings.embedding_model,
                retriever=settings.retrieval_type,
                context_strategy="priority",
                enable_logging=True,
                max_context_length=settings.max_context_length,
                timeout=30.0,
                is_default=True,
            )
            return self.create_pipeline(pipeline_input)
        except Exception as e:
            logger.error(f"Failed to initialize default pipeline: {e!s}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize default pipeline: {e!s}")

    def get_pipeline_config(self, pipeline_id: UUID) -> PipelineConfigOutput | None:
        """Retrieve pipeline configuration by ID."""
        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError(
                resource_type="PipelineConfig", resource_id=str(pipeline_id), message="Pipeline configuration not found"
            )
        return PipelineConfigOutput.model_validate(pipeline) if pipeline else None

    def create_pipeline(self, config_input: PipelineConfigInput) -> PipelineConfigOutput:
        """Create a new pipeline configuration."""
        # Validate provider exists
        if not self.llm_provider_service.get_provider_by_id(config_input.provider_id):
            raise ValidationError("Invalid provider ID")

        return self.pipeline_repository.create(config_input)

    def delete_pipeline(self, pipeline_id: UUID) -> bool:
        """Delete a pipeline configuration by ID."""
        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError(
                resource_id=str(pipeline_id), resource_type="PipelineConfig", message="Pipeline configuration not found"
            )

        return self.pipeline_repository.delete(pipeline_id)

    def validate_pipeline(self, pipeline_id: UUID) -> PipelineResult:
        """Validate pipeline configuration."""
        pipeline: PipelineConfig = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError(
                resource_type="PipelineConfig", resource_id=str(pipeline_id), message="Pipeline not found"
            )

        errors = []
        warnings = []

        # Validate provider
        if not self.llm_provider_service.get_provider_by_id(pipeline.provider_id):
            errors.append("Invalid provider ID")

            # Basic validation using settings
            if pipeline.retriever not in ["vector", "keyword", "hybrid"]:
                errors.append("Invalid retriever type")

        return PipelineResult(success=len(errors) == 0, error=errors[0] if errors else None, warnings=warnings)

    def test_pipeline(self, pipeline_id: UUID, query: str) -> PipelineResult:
        """Test pipeline with a sample query."""
        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError(
                resource_type="PipelineConfig", resource_id=str(pipeline_id), message="Pipeline not found"
            )

        try:
            # Initialize retriever with basic config
            retriever_config = {
                "type": pipeline.retriever,
                "vector_weight": settings.vector_weight if pipeline.retriever == "hybrid" else None,
            }
            self.retriever = RetrieverFactory.create_retriever(retriever_config, self.document_store)

            # Process query
            rewritten_query = self.query_rewriter.rewrite(query)
            vector_query = VectorQuery(text=query, number_of_results=settings.number_of_results)
            results = self.retriever.retrieve("test_collection", vector_query)
            logger.info(f"**** Results: {results}")
            return PipelineResult(success=True, rewritten_query=rewritten_query, query_results=results[:3])

        except Exception as e:
            logger.error(f"Pipeline test failed: {e!s}")
            return PipelineResult(success=False, error=str(e))

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
            raise NotFoundError(
                resource_type="PipelineConfig", resource_id=str(pipeline_id), message="Pipeline not found"
            )

        # Use collection-specific clear
        if pipeline.collection_id:
            self.pipeline_repository.clear_collection_defaults(pipeline.collection_id)

        # Get fields from current pipeline
        update_data = pipeline.model_dump(include=set(PipelineConfigInput.model_fields.keys()))
        update_data["is_default"] = True  # Override the is_default field

        # Update using input schema
        return self.pipeline_repository.update(pipeline_id, PipelineConfigInput(**update_data))

    def _prepare_query(self, query: str) -> str:
        """Sanitize and prepare query for execution."""
        clean_query = re.sub(r"\s+(AND|OR)\s+", " ", query)
        clean_query = re.sub(r"[\(\)]", "", clean_query)
        return clean_query.strip()

    def _format_context(self, template_id: UUID, query_results: list[QueryResult]) -> str:
        """Format retrieved contexts using template's context strategy."""
        try:
            texts = [result.chunk.text for result in query_results]
            return self.prompt_template_service.apply_context_strategy(template_id, texts)
        except Exception as e:
            logger.error(f"Error formatting context: {e!s}")
            return "\n\n".join(texts)

    def _validate_configuration(
        self, pipeline_id: UUID, user_id: UUID
    ) -> tuple[PipelineConfigOutput, LLMParametersInput, LLMProvider]:
        """
        Validate pipeline configuration and return required components.

        Args:
            pipeline_id: Pipeline UUID to validate
            user_id: User UUID

        Returns:
            Tuple of (pipeline config, LLM parameters, provider)

        Raises:
            NotFoundError: If pipeline or provider not found
            ConfigurationError: If validation fails
        """
        logger.info(f"**** Validating configuration for user_id: {user_id}")
        # Get pipeline configuration
        pipeline_config = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline_config:
            raise NotFoundError(
                resource_type="PipelineConfig", resource_id=str(pipeline_id), message="Pipeline configuration not found"
            )

        llm_parameters = self.llm_parameters_service.get_latest_or_default_parameters(user_id)
        if not llm_parameters:
            raise ConfigurationError("No default LLM parameters found")

        provider_output = self.llm_provider_service.get_provider_by_id(pipeline_config.provider_id)
        if not provider_output:
            raise NotFoundError(
                resource_type="LLMProvider",
                resource_id=str(pipeline_config.provider_id),
                message="LLM provider not found",
            )

        provider = LLMProviderFactory(self.db).get_provider(provider_output.name)
        if not provider:
            raise ConfigurationError("Failed to initialize LLM provider")

        return (pipeline_config, llm_parameters.to_input(), provider)

    def _get_templates(self, user_id: UUID) -> tuple[PromptTemplate, PromptTemplate | None]:
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
            user_id,
            PromptTemplateType.RAG_QUERY,
        )
        if not rag_template:
            raise NotFoundError(
                resource_type="PromptTemplateType",
                resource_id=str(user_id),
                message="User's RAG query template not found",
            )

        eval_template = (
            self.prompt_template_service.get_by_type(
                user_id,
                PromptTemplateType.RESPONSE_EVALUATION,
            )
            if settings.runtime_eval
            else None
        )

        return rag_template, eval_template

    def _retrieve_documents(self, query: str, collection_name: str) -> list[QueryResult]:
        """
        Retrieve relevant documents for the query.

        Args:
            query: The query text
            collection_name: Name of the collection to search

        Returns:
            List of query results

        Raises:
            ConfigurationError: If retrieval fails
        """
        try:
            vector_query = VectorQuery(text=query, number_of_results=settings.number_of_results)
            results = self.retriever.retrieve(collection_name, vector_query)
            logger.info(f"Retrieved {len(results)} documents")
            return results
        except Exception as e:
            logger.error(f"Error retrieving documents: {e!s}")
            raise ConfigurationError(f"Failed to retrieve documents: {e!s}")

    def _generate_answer(
        self,
        user_id: UUID,
        query: str,
        context: str,
        provider: LLMBase,
        llm_params: LLMParametersInput,
        template: PromptTemplate,
    ) -> str:
        """
        Generate answer using the LLM.

        Args:
            user_id: User's UUID
            query: The query text
            context: The context text
            provider: The LLM provider
            llm_params: LLM parameters
            template: The prompt template

        Returns:
            Generated answer text

        Raises:
            LLMProviderError: If generation fails
        """
        try:
            # Let provider handle prompt formatting and generation
            answer = provider.generate_text(
                user_id=user_id,
                prompt=query,
                model_parameters=llm_params,
                template=template,
                variables={"context": context, "question": query},
            )
            return answer[0] if isinstance(answer, list) else str(answer)

        except LLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Error in generation: {e!s}")
            raise LLMProviderError(
                provider=provider._provider_name,
                error_type="generation_failed",
                message=f"LLM provider error: {e!s}",
            )

    async def _evaluate_response(
        self, query: str, answer: str, context: str, template: PromptTemplate
    ) -> dict[str, Any] | None:
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
                template.id, {"context": context, "question": query, "answer": answer}
            )
            return await self.evaluator.evaluate(
                question=query, answer=answer, context=context, eval_prompt=eval_prompt
            )
        except Exception as e:
            logger.error(f"Evaluation failed: {e!s}")
            return {"error": str(e)}

    async def execute_pipeline(self, search_input: SearchInput, collection_name: str) -> PipelineResult:
        """
        Execute the RAG pipeline.

        Args:
            search_input: Search parameters and query.
            user_id: ID of the user.
            collection_name: Name of the collection to search.

        Returns:
            PipelineResult containing generated answer and metadata.

        Raises:
            HTTPException: With appropriate status codes for different error types.
        """
        start_time = time.time()
        logger.info("Starting RAG pipeline execution")

        try:
            # Validate input query
            if not search_input.question or not search_input.question.strip():
                raise ValidationError("Query cannot be empty")

            # Validate pipeline configuration
            pipeline_config, llm_parameters_input, provider = self._validate_configuration(
                search_input.pipeline_id, search_input.user_id
            )

            # Get required templates
            rag_template, eval_template = self._get_templates(search_input.user_id)

            # Process query and retrieve documents
            clean_query = self._prepare_query(search_input.question)
            rewritten_query = self.query_rewriter.rewrite(clean_query)
            query_results = self._retrieve_documents(rewritten_query, collection_name)

            # Generate answer and evaluate response
            if not query_results:
                generated_answer = "I apologize, but I couldn't find any relevant documents."
                evaluation_result = {"error": "No documents found"}
            else:
                context_text = self._format_context(rag_template.id, query_results)
                generated_answer = self._generate_answer(
                    search_input.user_id, clean_query, context_text, provider, llm_parameters_input, rag_template
                )
                evaluation_result = (
                    await self._evaluate_response(clean_query, generated_answer, context_text, eval_template)
                    if settings.runtime_eval and eval_template
                    else None
                )

            # Prepare and return the result
            execution_time = time.time() - start_time
            logger.info(f"Pipeline executed in {execution_time:.2f} seconds")

            return PipelineResult(
                success=True,
                rewritten_query=rewritten_query,
                query_results=query_results,
                generated_answer=generated_answer,
                evaluation=evaluation_result,
                metadata={
                    "execution_time": execution_time,
                    "num_chunks": len(query_results),
                    "unique_docs": len(set(r.document_id for r in query_results if r.document_id)),
                },
            )

        except ValidationError as e:
            logger.error(f"Validation error: {e!s}")
            raise HTTPException(status_code=400, detail=str(e))
        except NotFoundError as e:
            logger.error(f"Resource not found: {e!s}")
            raise HTTPException(status_code=404, detail=str(e))
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e!s}")
            raise HTTPException(status_code=500, detail=str(e))
        except LLMProviderError as e:
            logger.error(f"LLM provider error: {e!s}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {e!s}")
            raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {e!s}")
