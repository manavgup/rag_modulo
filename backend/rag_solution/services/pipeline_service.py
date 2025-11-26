"""Service layer for RAG pipeline execution and management."""

import os
import re
import time
import uuid
from datetime import datetime
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
from rag_solution.retrieval.reranker import BaseReranker
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
from vectordbs.data_types import DocumentMetadata, QueryResult, VectorQuery
from vectordbs.error_types import CollectionError
from vectordbs.factory import VectorStoreFactory

logger = get_logger("services.pipeline")


# pylint: disable=too-many-instance-attributes,too-many-public-methods
# Justification: Service class requires multiple dependencies and orchestrates many pipeline operations
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
            self._llm_parameters_service = LLMParametersService(self.db, self.settings)
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

    def get_reranker(self, user_id: UUID4) -> BaseReranker | None:
        """Get reranker instance for the given user.

        Creates a fresh reranker on-demand for each request. No caching is needed
        because reranker initialization is lightweight (just object creation).

        Args:
            user_id: User UUID for creating LLM-based reranker

        Returns:
            Reranker instance (CrossEncoderReranker, LLMReranker or SimpleReranker), or None if disabled
        """
        if not self.settings.enable_reranking:
            return None

        logger.debug("Creating reranker for user %s", user_id)

        # pylint: disable=import-outside-toplevel
        # Justification: Lazy import to avoid circular dependency
        from rag_solution.retrieval.reranker import CrossEncoderReranker, LLMReranker, SimpleReranker
        from rag_solution.schemas.prompt_template_schema import PromptTemplateType

        if self.settings.reranker_type == "cross-encoder":
            try:
                logger.debug("Creating cross-encoder reranker for user %s", user_id)
                reranker = CrossEncoderReranker(model_name=self.settings.cross_encoder_model)
                logger.debug("Cross-encoder reranker created successfully for user %s", user_id)
                return reranker
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Justification: Fallback to simple reranker for any initialization error
                logger.warning(
                    "Failed to create cross-encoder reranker for user %s: %s, using simple reranker", user_id, e
                )
                return SimpleReranker()
        elif self.settings.reranker_type == "llm":
            try:
                # Get LLM provider
                provider_config = self.llm_provider_service.get_default_provider()
                if not provider_config:
                    logger.warning("No LLM provider found, using simple reranker for user %s", user_id)
                    return SimpleReranker()

                # pylint: disable=import-outside-toplevel
                # Justification: Lazy import to avoid circular dependency
                from rag_solution.generation.providers.factory import LLMProviderFactory

                factory = LLMProviderFactory(self.db, self.settings)
                llm_provider = factory.get_provider(provider_config.name)

                # Get reranking prompt template (user-specific)
                try:
                    template = self.prompt_template_service.get_by_type(user_id, PromptTemplateType.RERANKING)
                    if template is None:
                        raise ValueError("Reranking template not found")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    # Justification: Fallback to simple reranker if template loading fails
                    logger.warning(
                        "Could not load reranking template for user %s: %s, using simple reranker", user_id, e
                    )
                    return SimpleReranker()

                reranker = LLMReranker(
                    llm_provider=llm_provider,
                    user_id=user_id,
                    prompt_template=template,
                    batch_size=self.settings.reranker_batch_size,
                    score_scale=self.settings.reranker_score_scale,
                )
                logger.debug("LLM reranker created successfully for user %s", user_id)
                return reranker
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Justification: Fallback to simple reranker for any initialization error
                logger.warning("Failed to create LLM reranker for user %s: %s, using simple reranker", user_id, e)
                return SimpleReranker()
        else:
            logger.debug("Creating simple reranker for user %s", user_id)
            return SimpleReranker()

    async def _apply_reranking(self, query: str, results: list[QueryResult], user_id: UUID4) -> list[QueryResult]:
        """Apply reranking to search results if enabled.

        Uses async concurrent batch processing for improved performance (50% faster).

        Args:
            query: The search query
            results: List of QueryResult objects from retrieval
            user_id: User UUID

        Returns:
            Reranked list of QueryResult objects (or original if reranking disabled/failed)
        """
        if not self.settings.enable_reranking or not results:
            return results

        try:
            reranker = self.get_reranker(user_id)
            if reranker is None:
                logger.debug("Reranking disabled, returning original results")
                return results

            original_count = len(results)
            # Use async reranking for 50% performance improvement via concurrent batch processing
            reranked_results = await reranker.rerank_async(
                query=query,
                results=results,
                top_k=self.settings.reranker_top_k,
            )
            logger.info(
                "Reranking reduced results from %d to %d documents (top_k=%d)",
                original_count,
                len(reranked_results),
                self.settings.reranker_top_k or len(results),
            )
            return reranked_results

        except (TimeoutError, ValueError, KeyError, AttributeError, TypeError) as e:
            # Catch specific exceptions from reranking: LLM errors, scoring failures, async timeouts
            # Reranking is an enhancement - if it fails, fall back to original retrieval results
            # This ensures the query still succeeds even if reranking fails
            logger.warning("Reranking failed: %s, returning original results", e)
            return results

    async def initialize(self, collection_name: str, collection_id: UUID4 | None = None) -> None:  # noqa: ARG002  # pylint: disable=unused-argument
        """Initialize pipeline components for a collection."""
        try:
            # Update document store collection
            self._document_store = DocumentStore(self.vector_store, collection_name)

            # Reinitialize retriever with new document store
            self._retriever = RetrieverFactory.create_retriever({}, self.document_store)

            # For search operations, we don't need to reload documents - they should already be processed
            # Only ensure the collection exists in vector store
            try:
                # Check if collection exists, create only if it doesn't
                if not hasattr(self.vector_store, "collection_exists") or not self.vector_store.collection_exists(
                    collection_name
                ):
                    self.vector_store.create_collection(collection_name)
                    logger.info("Created collection %s in vector store", collection_name)
                else:
                    logger.info("Collection %s already exists in vector store", collection_name)
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Justification: Need to catch all exceptions to handle collection already exists
                # If creation fails because it exists, that's fine
                if "already exists" in str(e).lower():
                    logger.info("Collection %s already exists in vector store", collection_name)
                else:
                    logger.warning("Could not verify/create collection %s: %s", collection_name, e)

            logger.info("Pipeline initialized for collection: %s", collection_name)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Need to catch all exceptions during initialization
            logger.error("Pipeline initialization failed: %s", e)
            raise ConfigurationError("pipeline", f"Pipeline initialization failed: {e!s}") from e

    async def _load_documents(self, collection_id: UUID4 | None = None) -> None:
        """Load and process documents from configured data sources."""
        try:
            # Get collection from database to find associated files
            if collection_id:
                collection = self.collection_service.get_collection(collection_id)
            else:
                # Fallback: try to find collection by vector_db_name
                logger.warning(
                    "No collection_id provided, cannot load documents for %s", self.document_store.collection_name
                )
                await self.document_store.load_documents([])
                return

            if not collection:
                logger.warning("Collection %s not found in database", self.document_store.collection_name)
                await self.document_store.load_documents([])
                return

            # Get files associated with this collection
            files = self.file_management_service.get_files_by_collection(collection.id)
            if not files:
                logger.info("No files found for collection %s", self.document_store.collection_name)
                await self.document_store.load_documents([])
                return

            # Create collection in vector store if it doesn't exist
            try:
                self.vector_store.create_collection(self.document_store.collection_name)
                logger.info("Created collection %s in vector store", self.document_store.collection_name)
            except CollectionError as e:
                if "already exists" in str(e):
                    logger.info("Collection %s already exists in vector store", self.document_store.collection_name)
                else:
                    raise

            # Get file paths and document IDs
            file_paths = [file.file_path for file in files if file.file_path]
            document_ids = [file.document_id for file in files if file.document_id]

            if not file_paths:
                logger.warning("No valid file paths found for collection %s", self.document_store.collection_name)
                await self.document_store.load_documents([])
                return

            # Process and ingest documents
            processed_documents = await self.collection_service.ingest_documents(
                file_paths, self.document_store.collection_name, document_ids
            )

            logger.info(
                "Loaded %d documents into collection: %s", len(processed_documents), self.document_store.collection_name
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error loading documents: %s", e)
            raise ConfigurationError("document_loading", f"Document loading failed: {e!s}") from e

    def get_user_pipelines(self, user_id: UUID4) -> list[PipelineConfigOutput]:
        """Get all pipelines for a user."""
        try:
            pipelines = self.pipeline_repository.get_by_user(user_id)

            # If no pipelines exist, create a default one for existing users
            if not pipelines:
                logger.info("No pipelines found for user %s, creating default pipeline", user_id)

                # Get user's provider or system default
                provider = self.llm_provider_service.get_user_provider(user_id)
                if not provider:
                    # Try to get system default provider
                    providers = self.llm_provider_service.get_all_providers()
                    if providers:
                        provider = providers[0]  # Use first available provider
                    else:
                        logger.error("No LLM providers available in the system")
                        raise ConfigurationError(
                            "llm_providers", "No LLM providers available. Please contact administrator."
                        )

                # Create default pipeline for existing user
                default_pipeline = self.initialize_user_pipeline(user_id, provider.id)
                return [default_pipeline]

            return pipelines  # Already PipelineConfigOutput objects from repository
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to get user pipelines: %s", e)
            raise ConfigurationError("pipeline_retrieval", f"Failed to retrieve pipeline configurations: {e!s}") from e

    def get_default_pipeline(self, user_id: UUID4) -> PipelineConfigOutput | None:
        """Get default pipeline for a user.

        Args:
            user_id: User UUID

        Returns:
            Optional[PipelineConfigOutput]: Default pipeline configuration if found
        """
        try:
            return self.pipeline_repository.get_user_default(user_id)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Return None as fallback for any failure when fetching default pipeline
            logger.error("Failed to get default pipeline: %s", e)
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
            logger.error("Failed to initialize default pipeline: %s", e)
            raise Exception(f"Failed to initialize default pipeline: {e!s}") from e  # pylint: disable=broad-exception-raised
            # Justification: Re-raising as generic Exception to maintain backward compatibility

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
            logger.info("**** Results: %s", results)
            return PipelineResult(
                success=True,
                error=None,
                rewritten_query=rewritten_query,
                query_results=results[:3],
                generated_answer=None,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Pipeline test failed: %s", e)
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
            # Filter out None chunks and extract text
            texts: list[str] = [result.chunk.text for result in query_results if result.chunk and result.chunk.text]
            return self.prompt_template_service.apply_context_strategy(template_id, texts)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error formatting context: %s", e)
            return "\n\n".join(texts)

    def _validate_configuration(
        self, pipeline_id: UUID4, user_id: UUID4
    ) -> tuple[PipelineConfigOutput, LLMParametersInput, LLMBase]:
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
        logger.info("**** Validating configuration for user_id: %s", user_id)
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

        provider = LLMProviderFactory(self.db, self.settings).get_provider(provider_output.name)
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

    def _apply_hierarchical_retrieval(
        self,
        results: list[QueryResult],
        collection_name: str,  # noqa: ARG002  # pylint: disable=unused-argument
    ) -> list[QueryResult]:
        """Apply hierarchical retrieval by replacing child chunks with parent chunks.

        Args:
            results: Query results containing child chunks
            collection_name: Name of the collection

        Returns:
            Query results with parent chunks (if hierarchical mode enabled)
        """
        # Check if hierarchical retrieval is enabled
        retrieval_mode = getattr(self.settings, "hierarchical_retrieval_mode", "child_only")

        if retrieval_mode == "child_only" or not results:
            return results

        # Get all chunks from the vector store to find parents
        try:
            modified_results = []

            for result in results:
                if not result.chunk:
                    modified_results.append(result)
                    continue

                chunk = result.chunk
                parent_id = chunk.parent_chunk_id

                if retrieval_mode == "child_with_parent" and parent_id:
                    # FIXME: Implement parent chunk retrieval  # pylint: disable=fixme
                    # Would need vector store method to fetch by chunk_id
                    # For now, we'll keep the child and note the limitation
                    logger.debug("Hierarchical retrieval: child %s has parent %s", chunk.chunk_id, parent_id)
                    modified_results.append(result)

                elif retrieval_mode == "parent_only" and parent_id:
                    # FIXME: Implement parent-only retrieval by fetching parent chunk  # pylint: disable=fixme
                    logger.debug("Parent-only mode: would replace child %s with parent %s", chunk.chunk_id, parent_id)
                    modified_results.append(result)
                else:
                    modified_results.append(result)

            return modified_results

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Hierarchical retrieval failed: %s, returning original results", e)
            return results

    def retrieve_documents_by_id(self, query: str, collection_id, top_k: int | None = None) -> list[QueryResult]:
        """Retrieve documents using collection_id (modern pipeline interface).

        This is the preferred method for new code. It handles the collection_id
        to collection_name lookup internally.

        Args:
            query: The query text
            collection_id: UUID of the collection
            top_k: Number of documents to retrieve

        Returns:
            List of query results

        Raises:
            ConfigurationError: If retrieval fails
            ValueError: If collection not found
        """
        from rag_solution.models.collection import Collection

        # Look up collection to get vector_db_name
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()

        if not collection:
            raise ValueError(f"Collection not found: {collection_id}")

        # Delegate to existing _retrieve_documents with the Milvus collection name
        return self._retrieve_documents(query, collection.vector_db_name, top_k)

    def _retrieve_documents(self, query: str, collection_name: str, top_k: int | None = None) -> list[QueryResult]:
        """Retrieve relevant documents for the query.

        Args:
            query: The query text
            collection_name: Name of the collection to search
            top_k: Number of documents to retrieve (overrides default if provided)

        Returns:
            List of query results

        Raises:
            ConfigurationError: If retrieval fails
        """
        try:
            num_results = top_k if top_k is not None else self.settings.number_of_results
            vector_query = VectorQuery(text=query, number_of_results=num_results)

            # Log retrieval details
            logger.debug(
                "Retrieving documents: query='%s...', collection=%s, top_k=%d",
                query[:50] if len(query) > 50 else query,
                collection_name,
                num_results,
            )

            results = self.retriever.retrieve(collection_name, vector_query)
            logger.info("Retrieved %d documents (requested: %d)", len(results), num_results)

            # DEBUG: Log first result details
            if results:
                first = results[0]
                logger.info("  First result: score=%.4f", first.score)
                logger.info(
                    "  First result text: %s...", first.chunk.text[:150] if first.chunk and first.chunk.text else "N/A"
                )

            # COMPREHENSIVE DEBUG LOGGING - Write detailed chunk info to file
            self._log_retrieved_chunks_to_file(query, collection_name, results, "retrieval")

            # Apply hierarchical retrieval if enabled
            if self.settings.chunking_strategy.lower() == "hierarchical":
                results = self._apply_hierarchical_retrieval(results, collection_name)

            return results
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error retrieving documents: %s", e)
            raise ConfigurationError("document_retrieval", f"Failed to retrieve documents: {e!s}") from e

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    # Justification: All parameters are required for LLM answer generation
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
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error in generation: %s", e)
            raise LLMProviderError(
                provider=provider._provider_name,  # pylint: disable=protected-access
                error_type="generation_failed",
                message=f"LLM provider error: {e!s}",
            ) from e

    async def _evaluate_response(
        self, query: str, answer: str, context: str, template: PromptTemplateOutput
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
            self.prompt_template_service.format_prompt(
                template.id, {"context": context, "question": query, "answer": answer}
            )
            return await self.evaluator.evaluate(context=context, answer=answer, question_text=query)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Evaluation failed: %s", e)
            return {"error": str(e)}

    # pylint: disable=too-many-branches,too-many-locals,too-many-statements
    # Justification: Pipeline execution orchestrates multiple steps with complex error handling
    async def execute_pipeline(
        self, search_input: SearchInput, collection_name: str, pipeline_id: UUID4
    ) -> PipelineResult:
        """
        Execute the RAG pipeline.

        Args:
            search_input: Search parameters and query.
            collection_name: Name of the collection to search.
            pipeline_id: ID of the pipeline configuration to use.

        Returns:
            PipelineResult containing generated answer and metadata.

        Raises:
            Domain exceptions (NotFoundError, ValidationError, ConfigurationError, LLMProviderError)
            for different error types.
        """
        start_time = time.time()
        logger.info("Starting RAG pipeline execution")

        try:
            # Validate input query
            if not search_input.question or not search_input.question.strip():
                raise ValidationError("Query cannot be empty")

            # Validate pipeline configuration
            _, llm_parameters_input, provider = self._validate_configuration(  # pylint: disable=unused-variable
                pipeline_id, search_input.user_id
            )

            # Get required templates
            rag_template, eval_template = self._get_templates(search_input.user_id)

            # Process query and retrieve documents
            clean_query = self._prepare_query(search_input.question)
            rewritten_query = self.query_rewriter.rewrite(clean_query)

            # DEBUG: Log query transformation
            logger.info("=" * 80)
            logger.info("Original query: %s", search_input.question)
            logger.info("Clean query: %s", clean_query)
            logger.info("Rewritten query: %s", rewritten_query)
            logger.info("Collection: %s", collection_name)

            # Extract top_k from config_metadata (defaults to settings value if not provided)
            top_k = self.settings.number_of_results
            if search_input.config_metadata and "top_k" in search_input.config_metadata:
                top_k = search_input.config_metadata["top_k"]
                logger.info("Using top_k=%d from config_metadata", top_k)

            query_results = self._retrieve_documents(rewritten_query, collection_name, top_k)

            # DEBUG: Log retrieval results
            if query_results:
                for i, result in enumerate(query_results[:5], 1):
                    logger.info(
                        "  Result %d: Score=%.4f, Text=%s...",
                        i,
                        result.score,
                        result.chunk.text[:100] if result.chunk and result.chunk.text else "N/A",
                    )
            logger.info("=" * 80)

            # Apply reranking BEFORE context formatting and LLM generation (P0-2 fix)
            # Uses async concurrent batch processing for 50% performance improvement (P0-3)
            if query_results:
                query_results = await self._apply_reranking(clean_query, query_results, search_input.user_id)
                logger.info("Reranking applied, proceeding with %d results", len(query_results))

            # Generate answer and evaluate response
            if not query_results:
                generated_answer = "I apologize, but I couldn't find any relevant documents."
                evaluation_result: dict[str, Any] | None = {"error": "No documents found"}
            else:
                context_text = self._format_context(rag_template.id, query_results)
                generated_answer = self._generate_answer(
                    search_input.user_id, clean_query, context_text, provider, llm_parameters_input, rag_template
                )
                evaluation_result = (
                    await self._evaluate_response(clean_query, generated_answer, context_text, eval_template)
                    if self.settings.runtime_eval and eval_template
                    else None
                )

            # Prepare and return the result
            execution_time = time.time() - start_time
            logger.info("Pipeline executed in %.2f seconds", execution_time)

            return PipelineResult(
                success=True,
                error=None,
                rewritten_query=rewritten_query,
                query_results=query_results,
                generated_answer=generated_answer,
                evaluation=evaluation_result,
            )

        except ValidationError as e:
            logger.error("Validation error: %s", e)
            raise
        except NotFoundError as e:
            logger.error("Resource not found: %s", e)
            raise
        except ConfigurationError as e:
            logger.error("Configuration error: %s", e)
            raise Exception(str(e)) from e  # pylint: disable=broad-exception-raised
        except LLMProviderError as e:
            logger.error("LLM provider error: %s", e)
            raise Exception(str(e)) from e  # pylint: disable=broad-exception-raised
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Unexpected error: %s", e)
            raise Exception(f"Pipeline execution failed: {e!s}") from e  # pylint: disable=broad-exception-raised

    def generate_document_metadata(
        self, query_results: list[QueryResult], collection_id: UUID4
    ) -> list[DocumentMetadata]:
        """
        Generate metadata from retrieved query results.

        Args:
            query_results: List of query results with document references
            collection_id: ID of the collection being searched

        Returns:
            List of document metadata

        Raises:
            ConfigurationError: If files not found or metadata incomplete
        """
        logger.debug("Generating document metadata for collection %s", collection_id)

        # Get unique document IDs from results
        doc_ids = {result.document_id for result in query_results if result.document_id is not None}

        if not doc_ids:
            logger.debug("No document IDs found in query results")
            return []

        # Get file metadata from file service
        files = self.file_management_service.get_files_by_collection(collection_id)
        if not files:
            logger.warning("No files found for collection %s", collection_id)
            return []

        # Create metadata map by document_id
        file_metadata_by_id: dict[str, DocumentMetadata] = {
            file.document_id: DocumentMetadata(
                document_name=file.filename,
                total_pages=file.metadata.total_pages if file.metadata else None,
                total_chunks=file.metadata.total_chunks if file.metadata else None,
                keywords=file.metadata.keywords if file.metadata else None,
            )
            for file in files
            if file.document_id
        }

        # Build document metadata list (unique documents only)
        doc_metadata = []
        for doc_id in doc_ids:
            if doc_id in file_metadata_by_id:
                doc_metadata.append(file_metadata_by_id[doc_id])
            else:
                logger.warning("Document %s not found in collection metadata", doc_id)

        logger.debug("Generated metadata for %d documents", len(doc_metadata))
        return doc_metadata

    def _log_retrieved_chunks_to_file(
        self, query: str, collection_name: str, results: list[QueryResult], stage: str
    ) -> None:
        """
        Log detailed chunk retrieval information to debug file.

        Creates comprehensive logs in /tmp/rag_debug/ with:
        - Query and collection info
        - All retrieved chunks with scores, metadata, and text
        - Timestamp for tracking

        Args:
            query: The search query
            collection_name: Milvus collection name
            results: List of retrieved QueryResult objects
            stage: Pipeline stage (e.g., 'retrieval', 'reranking')
        """
        try:
            # Create debug directory
            # Use system temp directory instead of hardcoded path (Bandit B108)
            import tempfile

            debug_dir = os.path.join(tempfile.gettempdir(), "rag_debug")
            os.makedirs(debug_dir, exist_ok=True)

            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"{debug_dir}/chunks_{stage}_{timestamp}.txt"

            with open(debug_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write(f"RAG CHUNK RETRIEVAL DEBUG - {stage.upper()} STAGE\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")

                f.write(f"Query: {query}\n")
                f.write(f"Collection: {collection_name}\n")
                f.write(f"Total chunks retrieved: {len(results)}\n")
                f.write("\n" + "=" * 80 + "\n")
                f.write("RETRIEVED CHUNKS:\n")
                f.write("=" * 80 + "\n\n")

                for i, result in enumerate(results, 1):
                    f.write(f"CHUNK #{i}\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"Score: {result.score:.6f}\n")

                    # Extract metadata from chunk
                    if result.chunk:
                        chunk_text = result.chunk.text or ""

                        # Get metadata from chunk.metadata if available
                        if result.chunk.metadata:
                            doc_name = (
                                getattr(result.chunk.metadata, "document_name", None)
                                or getattr(result.chunk.metadata, "source_id", None)
                                or "unknown"
                            )
                            page_num = getattr(result.chunk.metadata, "page_number", "?")
                            chunk_num = getattr(result.chunk.metadata, "chunk_number", "?")
                        else:
                            doc_name = "unknown"
                            page_num = "?"
                            chunk_num = "?"

                        f.write(f"Document: {doc_name}\n")
                        f.write(f"Page: {page_num}\n")
                        f.write(f"Chunk Number: {chunk_num}\n")
                        f.write(f"Document ID: {result.chunk.document_id or 'N/A'}\n")
                        f.write(f"Text Length: {len(chunk_text)} chars\n")
                        f.write("\nFull Text:\n")
                        f.write(chunk_text)
                        f.write("\n")
                    else:
                        f.write("WARNING: No chunk data available\n")

                    f.write("\n" + "-" * 80 + "\n\n")

                f.write("=" * 80 + "\n")
                f.write("END OF DEBUG LOG\n")
                f.write("=" * 80 + "\n")

            logger.info("📝 Chunk debug log written to: %s", debug_file)

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Don't fail the search if logging fails
            logger.warning("Failed to write chunk debug log: %s", e)
