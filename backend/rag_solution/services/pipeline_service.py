"""Service layer for RAG pipeline execution and management."""

import re
import time
import uuid
from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings
from core.custom_exceptions import LLMProviderError
from core.logging_utils import get_logger
from rag_solution.core.exceptions import ConfigurationError, NotFoundError, ValidationError
from rag_solution.data_ingestion.ingestion import DocumentStore
from rag_solution.evaluation.evaluator import RAGEvaluator
from rag_solution.generation.providers.base import LLMBase
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.query_rewriting.query_rewriter import QueryRewriter
from rag_solution.repository.pipeline_repository import PipelineConfigRepository
from rag_solution.retrieval.factories import RetrieverFactory
from rag_solution.retrieval.retriever import BaseRetriever
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.pipeline_schema import (
    ChunkingStrategy,
    ContextStrategy,
    PipelineConfigInput,
    PipelineConfigOutput,
    PipelineResult,
    RetrieverType,
)
from rag_solution.schemas.prompt_template_schema import PromptTemplateOutput, PromptTemplateType
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService
from vectordbs.data_types import QueryResult, VectorQuery
from vectordbs.error_types import CollectionError
from vectordbs.factory import VectorStoreFactory

logger = get_logger("services.pipeline")


class PipelineService:
    """Service for managing and executing RAG pipelines."""

    def __init__(self: Any, db: Session, settings: Settings) -> None:
        """Initialize service with database session and settings injection."""
        self.db = db
        if settings is None:
            raise ValueError("Settings must be provided to PipelineService")
        self.settings = settings
        self._pipeline_repository: PipelineConfigRepository | None = None
        self._llm_parameters_service: LLMParametersService | None = None
        self._prompt_template_service: PromptTemplateService | None = None
        self._llm_provider_service: LLMProviderService | None = None
        self._file_management_service: FileManagementService | None = None
        self._collection_service: CollectionService | None = None

        # Core RAG components
        self.query_rewriter = QueryRewriter({})
        # Use factory with proper dependency injection
        factory = VectorStoreFactory(self.settings)
        self.vector_store = factory.get_datastore(self.settings.vector_db)
        # Lazy initialize evaluator to avoid WatsonX client initialization at import time
        self._evaluator: RAGEvaluator | None = None

        # Lazy initialized components
        self._document_store: DocumentStore | None = None
        self._retriever: BaseRetriever | None = None

    # Property-based lazy initialization
    @property
    def pipeline_repository(self) -> PipelineConfigRepository:
        """Get or create pipeline repository instance."""
        if self._pipeline_repository is None:
            self._pipeline_repository = PipelineConfigRepository(self.db)
        return self._pipeline_repository

    @property
    def llm_parameters_service(self) -> LLMParametersService:
        """Get or create LLM parameters service instance."""
        if self._llm_parameters_service is None:
            self._llm_parameters_service = LLMParametersService(self.db)
        return self._llm_parameters_service

    @property
    def prompt_template_service(self) -> PromptTemplateService:
        """Get or create prompt template service instance."""
        if self._prompt_template_service is None:
            self._prompt_template_service = PromptTemplateService(self.db)
        return self._prompt_template_service

    @property
    def llm_provider_service(self) -> LLMProviderService:
        """Get or create LLM provider service instance."""
        if self._llm_provider_service is None:
            self._llm_provider_service = LLMProviderService(self.db)
        return self._llm_provider_service

    @property
    def file_management_service(self) -> FileManagementService:
        """Get or create file management service instance."""
        if self._file_management_service is None:
            self._file_management_service = FileManagementService(self.db, self.settings)
        return self._file_management_service

    @property
    def collection_service(self) -> CollectionService:
        """Lazy initialization of collection service."""
        if self._collection_service is None:
            self._collection_service = CollectionService(self.db, self.settings)
        return self._collection_service

    @property
    def evaluator(self) -> RAGEvaluator:
        """Get or create RAG evaluator instance."""
        if self._evaluator is None:
            self._evaluator = RAGEvaluator()
        return self._evaluator

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

    async def initialize(self, collection_name: str, collection_id: UUID4 | None = None) -> None:
        """Initialize pipeline components for a collection."""
        try:
            # Update document store collection
            self._document_store = DocumentStore(self.vector_store, collection_name)

            # Reinitialize retriever with new document store
            self._retriever = RetrieverFactory.create_retriever({}, self.document_store)

            # Load documents
            await self._load_documents(collection_id)

            logger.info(f"Pipeline initialized for collection: {collection_name}")
        except Exception as e:
            logger.error(f"Pipeline initialization failed: {e!s}")
            raise ConfigurationError("pipeline", f"Pipeline initialization failed: {e!s}") from e

    async def _load_documents(self, collection_id: UUID4 | None = None) -> None:
        """Load and process documents from configured data sources."""
        try:
            # Get collection from database to find associated files
            if collection_id:
                collection = self.collection_service.get_collection(collection_id)
            else:
                # Fallback: try to find collection by vector_db_name
                logger.warning(f"No collection_id provided, cannot load documents for {self.document_store.collection_name}")
                await self.document_store.load_documents([])
                return

            if not collection:
                logger.warning(f"Collection {self.document_store.collection_name} not found in database")
                await self.document_store.load_documents([])
                return

            # Get files associated with this collection
            files = self.file_management_service.get_files_by_collection(collection.id)
            if not files:
                logger.info(f"No files found for collection {self.document_store.collection_name}")
                await self.document_store.load_documents([])
                return

            # Create collection in vector store if it doesn't exist
            try:
                self.vector_store.create_collection(self.document_store.collection_name)
                logger.info(f"Created collection {self.document_store.collection_name} in vector store")
            except CollectionError as e:
                if "already exists" in str(e):
                    logger.info(f"Collection {self.document_store.collection_name} already exists in vector store")
                else:
                    raise

            # Get file paths and document IDs
            file_paths = [file.file_path for file in files if file.file_path]
            document_ids = [file.document_id for file in files if file.document_id]

            if not file_paths:
                logger.warning(f"No valid file paths found for collection {self.document_store.collection_name}")
                await self.document_store.load_documents([])
                return

            # Process and ingest documents
            processed_documents = await self.collection_service.ingest_documents(
                file_paths,
                self.document_store.collection_name,
                document_ids
            )

            logger.info(f"Loaded {len(processed_documents)} documents into collection: {self.document_store.collection_name}")
        except Exception as e:
            logger.error(f"Error loading documents: {e!s}")
            raise ConfigurationError("document_loading", f"Document loading failed: {e!s}") from e

    def get_user_pipelines(self, user_id: UUID4) -> list[PipelineConfigOutput]:
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
                        raise ConfigurationError("llm_providers", "No LLM providers available. Please contact administrator.")

                # Create default pipeline for existing user
                default_pipeline = self.initialize_user_pipeline(user_id, provider.id)
                return [default_pipeline]

            return pipelines  # Already PipelineConfigOutput objects from repository
        except Exception as e:
            logger.error(f"Failed to get user pipelines: {e!s}")
            raise ConfigurationError("pipeline_retrieval", f"Failed to retrieve pipeline configurations: {e!s}") from e

    def get_default_pipeline(self, user_id: UUID4, collection_id: UUID4 | None = None) -> PipelineConfigOutput | None:
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

    def initialize_user_pipeline(self, user_id: UUID4, provider_id: UUID4) -> PipelineConfigOutput:
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
                collection_id=None,  # Default pipeline doesn't belong to a specific collection
                provider_id=provider_id,
                chunking_strategy=ChunkingStrategy(self.settings.chunking_strategy),
                embedding_model=self.settings.embedding_model,
                retriever=RetrieverType(self.settings.retrieval_type),
                context_strategy=ContextStrategy.PRIORITY,
                enable_logging=True,
                max_context_length=self.settings.max_context_length,
                timeout=30.0,
                is_default=True,
            )
            return self.create_pipeline(pipeline_input)
        except Exception as e:
            logger.error(f"Failed to initialize default pipeline: {e!s}")
            raise Exception(f"Failed to initialize default pipeline: {e!s}") from e

    def get_pipeline_config(self, pipeline_id: UUID4) -> PipelineConfigOutput | None:
        """Retrieve pipeline configuration by ID."""
        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError(resource_type="PipelineConfig", resource_id=str(pipeline_id))
        return PipelineConfigOutput.model_validate(pipeline) if pipeline else None

    def create_pipeline(self, config_input: PipelineConfigInput) -> PipelineConfigOutput:
        """Create a new pipeline configuration."""
        # Validate provider exists
        if not self.llm_provider_service.get_provider_by_id(config_input.provider_id):
            raise ValidationError("Invalid provider ID")

        return self.pipeline_repository.create(config_input)

    def update_pipeline(self, pipeline_id: UUID4, config_input: PipelineConfigInput) -> PipelineConfigOutput:
        """Update an existing pipeline configuration."""
        # Validate provider exists
        if not self.llm_provider_service.get_provider_by_id(config_input.provider_id):
            raise ValidationError("Invalid provider ID")

        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError(resource_type="PipelineConfig", resource_id=str(pipeline_id))

        # Update the pipeline
        updated_pipeline = self.pipeline_repository.update(pipeline_id, config_input)
        return PipelineConfigOutput.model_validate(updated_pipeline)

    def delete_pipeline(self, pipeline_id: UUID4) -> bool:
        """Delete a pipeline configuration by ID."""
        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError(resource_id=str(pipeline_id), resource_type="PipelineConfig")

        return self.pipeline_repository.delete(pipeline_id)

    def validate_pipeline(self, pipeline_id: UUID4) -> PipelineResult:
        """Validate pipeline configuration."""
        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError(resource_type="PipelineConfig", resource_id=str(pipeline_id))

        errors = []
        warnings: list[str] = []

        # Validate provider
        if not self.llm_provider_service.get_provider_by_id(uuid.UUID(str(pipeline.provider_id))):
            errors.append("Invalid provider ID")

            # Basic validation using settings
            if pipeline.retriever not in ["vector", "keyword", "hybrid"]:
                errors.append("Invalid retriever type")

        return PipelineResult(
            success=len(errors) == 0,
            error=errors[0] if errors else None,
            warnings=warnings,
            rewritten_query=None,
            generated_answer=None,
        )

    def test_pipeline(self, pipeline_id: UUID4, query: str) -> PipelineResult:
        """Test pipeline with a sample query."""
        pipeline = self.pipeline_repository.get_by_id(pipeline_id)
        if not pipeline:
            raise NotFoundError(resource_type="PipelineConfig", resource_id=str(pipeline_id))

        try:
            # Initialize retriever with basic config
            retriever_config = {
                "type": pipeline.retriever,
                "vector_weight": self.settings.vector_weight if pipeline.retriever == "hybrid" else None,
            }
            self._retriever = RetrieverFactory.create_retriever(retriever_config, self.document_store)

            # Process query
            rewritten_query = self.query_rewriter.rewrite(query)
            vector_query = VectorQuery(text=query, number_of_results=self.settings.number_of_results)
            results = self.retriever.retrieve("test_collection", vector_query)
            logger.info(f"**** Results: {results}")
            return PipelineResult(
                success=True,
                error=None,
                rewritten_query=rewritten_query,
                query_results=results[:3],
                generated_answer=None,
            )

        except Exception as e:
            logger.error(f"Pipeline test failed: {e!s}")
            return PipelineResult(success=False, error=str(e), rewritten_query=None, generated_answer=None)

    def set_default_pipeline(self, pipeline_id: UUID4) -> PipelineConfigOutput:
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
            raise NotFoundError(resource_type="PipelineConfig", resource_id=str(pipeline_id))

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

    def _format_context(self, template_id: UUID4, query_results: list[QueryResult]) -> str:
        """Format retrieved contexts using template's context strategy."""
        try:
            texts = [result.chunk.text for result in query_results]
            return self.prompt_template_service.apply_context_strategy(template_id, texts)
        except Exception as e:
            logger.error(f"Error formatting context: {e!s}")
            return "\n\n".join(texts)

    def _validate_configuration(self, pipeline_id: UUID4, user_id: UUID4) -> tuple[PipelineConfigOutput, LLMParametersInput, LLMBase]:
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
            raise NotFoundError(resource_type="PipelineConfig", resource_id=str(pipeline_id))

        llm_parameters = self.llm_parameters_service.get_latest_or_default_parameters(user_id)
        if not llm_parameters:
            raise ConfigurationError("llm_parameters", "No default LLM parameters found")

        provider_output = self.llm_provider_service.get_provider_by_id(pipeline_config.provider_id)
        if not provider_output:
            raise NotFoundError(
                resource_type="LLMProvider",
                resource_id=str(pipeline_config.provider_id),
            )

        provider = LLMProviderFactory(self.db).get_provider(provider_output.name)
        if not provider:
            raise ConfigurationError("llm_provider", "Failed to initialize LLM provider")

        return (pipeline_config, llm_parameters.to_input(), provider)

    def _get_templates(self, user_id: UUID4) -> tuple[PromptTemplateOutput, PromptTemplateOutput | None]:
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
            )

        eval_template = (
            self.prompt_template_service.get_by_type(
                user_id,
                PromptTemplateType.RESPONSE_EVALUATION,
            )
            if self.settings.runtime_eval
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
            vector_query = VectorQuery(text=query, number_of_results=self.settings.number_of_results)
            results = self.retriever.retrieve(collection_name, vector_query)
            logger.info(f"Retrieved {len(results)} documents")
            return results
        except Exception as e:
            logger.error(f"Error retrieving documents: {e!s}")
            raise ConfigurationError("document_retrieval", f"Failed to retrieve documents: {e!s}") from e

    def _generate_answer(
        self,
        user_id: UUID4,
        query: str,
        context: str,
        provider: LLMBase,
        llm_params: LLMParametersInput,
        template: PromptTemplateOutput,
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
            ) from e

    async def _evaluate_response(self, query: str, answer: str, context: str, template: PromptTemplateOutput) -> dict[str, Any] | None:
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
            self.prompt_template_service.format_prompt(template.id, {"context": context, "question": query, "answer": answer})
            return await self.evaluator.evaluate(context=context, answer=answer, question=query)
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
            Domain exceptions (NotFoundError, ValidationError, ConfigurationError, LLMProviderError) for different error types.
        """
        start_time = time.time()
        logger.info("Starting RAG pipeline execution")

        try:
            # Validate input query
            if not search_input.question or not search_input.question.strip():
                raise ValidationError("Query cannot be empty")

            # Validate pipeline configuration
            pipeline_config, llm_parameters_input, provider = self._validate_configuration(search_input.pipeline_id, search_input.user_id)

            # Get required templates
            rag_template, eval_template = self._get_templates(search_input.user_id)

            # Process query and retrieve documents
            clean_query = self._prepare_query(search_input.question)
            rewritten_query = self.query_rewriter.rewrite(clean_query)
            query_results = self._retrieve_documents(rewritten_query, collection_name)

            # Generate answer and evaluate response
            if not query_results:
                generated_answer = "I apologize, but I couldn't find any relevant documents."
                evaluation_result: dict[str, Any] | None = {"error": "No documents found"}
            else:
                context_text = self._format_context(rag_template.id, query_results)
                generated_answer = self._generate_answer(search_input.user_id, clean_query, context_text, provider, llm_parameters_input, rag_template)
                evaluation_result = await self._evaluate_response(clean_query, generated_answer, context_text, eval_template) if self.settings.runtime_eval and eval_template else None

            # Prepare and return the result
            execution_time = time.time() - start_time
            logger.info(f"Pipeline executed in {execution_time:.2f} seconds")

            return PipelineResult(
                success=True,
                error=None,
                rewritten_query=rewritten_query,
                query_results=query_results,
                generated_answer=generated_answer,
                evaluation=evaluation_result,
            )

        except ValidationError as e:
            logger.error(f"Validation error: {e!s}")
            raise
        except NotFoundError as e:
            logger.error(f"Resource not found: {e!s}")
            raise
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e!s}")
            raise Exception(str(e)) from e
        except LLMProviderError as e:
            logger.error(f"LLM provider error: {e!s}")
            raise Exception(str(e)) from e
        except Exception as e:
            logger.error(f"Unexpected error: {e!s}")
            raise Exception(f"Pipeline execution failed: {e!s}") from e
