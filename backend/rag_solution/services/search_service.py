"""Service for handling search operations through the RAG pipeline."""
# pylint: disable=too-many-lines
# Justification: Search service orchestrates multiple complex search paths

import time
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

from fastapi import HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings
from core.custom_exceptions import ConfigurationError, LLMProviderError, NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput
from rag_solution.schemas.collection_schema import CollectionStatus
from rag_solution.schemas.llm_usage_schema import TokenWarning
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.pipeline.pipeline_executor import PipelineExecutor
from rag_solution.services.pipeline.search_context import SearchContext
from rag_solution.services.pipeline.stages import (
    GenerationStage,
    PipelineResolutionStage,
    QueryEnhancementStage,
    ReasoningStage,
    RerankingStage,
    RetrievalStage,
)
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.token_tracking_service import TokenTrackingService
from vectordbs.data_types import DocumentMetadata, QueryResult

# pylint: disable=wrong-import-position
# Justification: TYPE_CHECKING import must come after regular imports to prevent circular import
if TYPE_CHECKING:
    from rag_solution.services.chain_of_thought_service import ChainOfThoughtService

logger = get_logger("services.search")

T = TypeVar("T")
P = ParamSpec("P")


def handle_search_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle common search errors and convert them to HTTPExceptions."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except NotFoundError as e:
            logger.error("Resource not found: %s", e)
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValidationError as e:
            logger.error("Validation error: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e
        except LLMProviderError as e:
            logger.error("LLM provider error: %s", e)
            raise HTTPException(status_code=500, detail=str(e)) from e
        except ConfigurationError as e:
            logger.error("Configuration error: %s", e)
            raise HTTPException(status_code=500, detail=str(e)) from e
        except Exception as e:
            logger.error("Unexpected error during search: %s", e)
            raise HTTPException(status_code=500, detail=f"Error processing search: {e!s}") from e

    return wrapper


# pylint: disable=too-many-instance-attributes
# Justification: Service class requires multiple dependencies for search orchestration
class SearchService:
    """Service for handling search operations through the RAG pipeline."""

    def __init__(self, db: Session, settings: Settings) -> None:
        """Initialize SearchService with dependencies."""
        logger.info("🔍 SEARCH SERVICE: __init__ called!")
        logger.debug("Initializing SearchService")
        self.db: Session = db
        self.settings = settings
        self._file_service: FileManagementService | None = None
        self._collection_service: CollectionService | None = None
        self._pipeline_service: PipelineService | None = None
        self._llm_provider_service: LLMProviderService | None = None
        self._chain_of_thought_service: Any | None = None
        self._token_tracking_service: TokenTrackingService | None = None
        # Note: Reranking moved to PipelineService (P0-2 fix)

    @property
    def file_service(self) -> FileManagementService:
        """Lazy initialization of file management service."""
        if self._file_service is None:
            logger.debug("Lazy initializing file management service")
            self._file_service = FileManagementService(self.db, self.settings)
        return self._file_service

    @property
    def collection_service(self) -> CollectionService:
        """Lazy initialization of collection service."""
        if self._collection_service is None:
            logger.debug("Lazy initializing collection service")
            self._collection_service = CollectionService(self.db, self.settings)
        return self._collection_service

    @property
    def pipeline_service(self) -> PipelineService:
        """Lazy initialization of pipeline service."""
        if self._pipeline_service is None:
            logger.debug("Lazy initializing pipeline service")
            self._pipeline_service = PipelineService(self.db, self.settings)
        return self._pipeline_service

    @property
    def llm_provider_service(self) -> LLMProviderService:
        """Lazy initialization of LLM provider service."""
        if self._llm_provider_service is None:
            logger.debug("Lazy initializing LLM provider service")
            self._llm_provider_service = LLMProviderService(self.db)
        return self._llm_provider_service

    @property
    def chain_of_thought_service(self) -> "ChainOfThoughtService":
        """Lazy initialization of Chain of Thought service."""
        if self._chain_of_thought_service is None:
            logger.debug("Lazy initializing Chain of Thought service")
            # pylint: disable=import-outside-toplevel
            # Justification: Lazy import to avoid circular dependency with ChainOfThoughtService
            from rag_solution.services.chain_of_thought_service import ChainOfThoughtService

            # Get default LLM provider configuration for CoT
            try:
                provider_config = self.llm_provider_service.get_default_provider()
                logger.debug("Retrieved provider config: %s", provider_config)
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Justification: Fallback to None for any provider configuration error
                logger.exception("Failed to get default provider configuration: %s", e)
                provider_config = None

            # Create actual LLM provider instance if config is available
            llm_service = None
            if provider_config:
                try:
                    # pylint: disable=import-outside-toplevel
                    # Justification: Lazy import to avoid circular dependency with LLMProviderFactory
                    from rag_solution.generation.providers.factory import LLMProviderFactory

                    # Use the factory to create the provider instance properly
                    factory = LLMProviderFactory(self.db, self.settings)
                    llm_service = factory.get_provider(provider_config.name)
                    logger.debug("Using %s LLM provider for CoT service", provider_config.name)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    # Justification: Fallback to None for any provider creation error
                    logger.exception("Failed to create LLM provider instance: %s", e)
                    logger.warning("Chain of Thought service will be created without LLM provider")
            else:
                logger.warning("No default provider configuration found for CoT service")
                logger.info("Chain of Thought service will be created without LLM provider")

            try:
                self._chain_of_thought_service = ChainOfThoughtService(
                    settings=self.settings, llm_service=llm_service, search_service=self, db=self.db
                )
                logger.debug("Chain of Thought service initialized successfully")
            except Exception as e:
                logger.exception("Failed to initialize Chain of Thought service: %s", e)
                raise ConfigurationError(f"Failed to initialize Chain of Thought service: {e}") from e
        return self._chain_of_thought_service

    @property
    def token_tracking_service(self) -> TokenTrackingService:
        """Lazy initialization of token tracking service."""
        if self._token_tracking_service is None:
            logger.debug("Lazy initializing token tracking service")
            self._token_tracking_service = TokenTrackingService(self.db, self.settings)
        return self._token_tracking_service

    # Note: Reranking methods removed - now handled by PipelineService (P0-2 fix)
    # - get_reranker() moved to PipelineService
    # - _apply_reranking() moved to PipelineService

    def _should_use_chain_of_thought(self, search_input: SearchInput) -> bool:
        """Automatically determine if Chain of Thought should be used for this search.

        CoT is used for complex questions that benefit from reasoning:
        - Multi-part questions (how, why, explain, compare, analyze)
        - Questions with multiple clauses or conditions
        - Long questions requiring deep analysis
        - Questions explicitly asking for reasoning or explanations

        Users can override with 'show_cot_steps' for visibility or 'cot_disabled' to disable.
        """
        # Debug logging
        logger.debug("CoT decision check for question: %s", search_input.question)
        logger.debug("Config metadata: %s", search_input.config_metadata)

        # Allow explicit override to disable CoT
        if search_input.config_metadata and search_input.config_metadata.get("cot_disabled"):
            logger.debug("CoT disabled by config")
            return False

        # Allow explicit override to enable CoT - FORCE ENABLED
        if search_input.config_metadata and search_input.config_metadata.get("cot_enabled"):
            logger.info("🚨 FORCED COT ENABLED by config")
            return True

        # Automatic detection based on question complexity
        question = search_input.question.lower()
        question_length = len(search_input.question.split())

        # Complex question indicators
        complex_patterns = [
            "how does",
            "how do",
            "why does",
            "why do",
            "explain",
            "compare",
            "analyze",
            "what are the differences",
            "what is the relationship",
            "how can i",
            "what are the steps",
            "walk me through",
            "break down",
            "elaborate",
            "pros and cons",
            "advantages and disadvantages",
            "benefits and drawbacks",
        ]

        # Check for complex patterns
        has_complex_patterns = any(pattern in question for pattern in complex_patterns)

        # Check for multiple questions (indicated by multiple question marks or 'and')
        multiple_questions = question.count("?") > 1 or (" and " in question and "?" in question)

        # Long questions likely need more reasoning
        is_long_question = question_length > 15

        # Questions asking for reasoning
        asks_for_reasoning = any(
            word in question for word in ["because", "reason", "rationale", "justify", "evidence", "support"]
        )

        # Use CoT if any complexity indicators are present
        should_use_cot = has_complex_patterns or multiple_questions or is_long_question or asks_for_reasoning

        logger.debug(
            "CoT decision: %s (patterns=%s, multiple=%s, long=%s, reasoning=%s, length=%d)",
            should_use_cot,
            has_complex_patterns,
            multiple_questions,
            is_long_question,
            asks_for_reasoning,
            question_length,
        )

        return should_use_cot

    def _should_show_cot_steps(self, search_input: SearchInput) -> bool:
        """Determine if Chain of Thought steps should be shown to the user."""
        if not search_input.config_metadata:
            return False
        return search_input.config_metadata.get("show_cot_steps", False)

    def _convert_to_cot_input(self, search_input: SearchInput) -> ChainOfThoughtInput:
        """Convert SearchInput to ChainOfThoughtInput."""
        return ChainOfThoughtInput(
            question=search_input.question,
            collection_id=search_input.collection_id,
            user_id=search_input.user_id,
            cot_config=search_input.config_metadata,
            context_metadata=search_input.config_metadata,
        )

    @handle_search_errors
    async def _initialize_pipeline(self, collection_id: UUID4) -> str:
        """Initialize pipeline with collection."""
        try:
            # Get collection
            collection = self.collection_service.get_collection(collection_id)
            if not collection:
                raise NotFoundError(
                    resource_type="Collection",
                    resource_id=str(collection_id),
                    message=f"Collection with ID {collection_id} not found",
                )

            # Initialize pipeline
            await self.pipeline_service.initialize(collection.vector_db_name, collection_id)
            return collection.vector_db_name

        except (NotFoundError, ConfigurationError):
            raise
        except Exception as e:
            logger.error("Error initializing pipeline: %s", e)
            raise ConfigurationError(f"Pipeline initialization failed: {e!s}") from e

    def _generate_document_metadata(
        self, query_results: list[QueryResult], collection_id: UUID4
    ) -> list[DocumentMetadata]:
        """Generate metadata from retrieved query results."""
        logger.debug("Generating document metadata")

        # Get unique document IDs from results
        doc_ids = {result.document_id for result in query_results if result.document_id is not None}

        if not doc_ids:
            return []

        # Get file metadata
        files = self.file_service.get_files_by_collection(collection_id)
        if not files:
            # Only return empty list if there are no query results requiring metadata
            if not doc_ids:
                return []
            raise ConfigurationError(f"No files found for collection {collection_id} but documents were referenced")

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

        # Map metadata to results
        doc_metadata = []
        missing_docs = []
        for doc_id in doc_ids:
            if doc_id not in file_metadata_by_id:
                missing_docs.append(doc_id)

        if missing_docs:
            raise ConfigurationError(
                f"Metadata generation failed: Documents not found in collection metadata: {', '.join(missing_docs)}"
            )

        for doc_id in doc_ids:
            doc_metadata.append(file_metadata_by_id[doc_id])

        logger.debug("Generated metadata for %d documents", len(doc_metadata))
        return doc_metadata

    def _clean_generated_answer(self, answer: str) -> str:
        """
        Clean generated answer by removing artifacts and duplicates.

        Removes:
        - " AND " artifacts from query rewriting
        - Duplicate consecutive words
        - Leading/trailing whitespace
        """
        # pylint: disable=import-outside-toplevel
        # Justification: Lazy import to avoid loading re module unless needed
        import re

        cleaned = answer.strip()

        # Remove " AND " artifacts that come from query rewriting
        # Handle both middle "AND" and trailing "AND"
        cleaned = re.sub(r"\s+AND\s+", " ", cleaned)  # Middle ANDs
        cleaned = re.sub(r"\s+AND$", "", cleaned)  # Trailing AND

        # Remove duplicate consecutive words
        words = cleaned.split()
        deduplicated_words = []
        prev_word = None

        for word in words:
            if not prev_word or word.lower() != prev_word.lower():
                deduplicated_words.append(word)
            prev_word = word

        # Join back and clean up any multiple spaces
        result = " ".join(deduplicated_words)
        result = re.sub(r"\s+", " ", result).strip()

        return result

    def _validate_search_input(self, search_input: SearchInput) -> None:
        """Validate search input parameters."""
        if not search_input.question or not search_input.question.strip():
            raise ValidationError("Query cannot be empty")

    def _validate_collection_access(self, collection_id: UUID4, user_id: UUID4 | None) -> None:
        """Validate collection access."""
        try:
            collection = self.collection_service.get_collection(collection_id)
            if not collection:
                raise NotFoundError(
                    resource_type="Collection",
                    resource_id=str(collection_id),
                    message=f"Collection with ID {collection_id} not found",
                )

            # Check collection status - only allow search on completed collections
            if collection.status != CollectionStatus.COMPLETED:
                if collection.status == CollectionStatus.PROCESSING:
                    raise ValidationError(
                        f"Collection {collection_id} is still processing documents. Please wait for processing to complete."
                    )
                if collection.status == CollectionStatus.CREATED:
                    raise ValidationError(
                        f"Collection {collection_id} has no documents. Please upload documents before searching."
                    )
                if collection.status == CollectionStatus.ERROR:
                    raise ValidationError(
                        f"Collection {collection_id} encountered errors during processing. Please check collection status."
                    )
                raise ValidationError(
                    f"Collection {collection_id} is not ready for search (status: {collection.status})."
                )

            if user_id and collection.is_private:
                user_collections = self.collection_service.get_user_collections(user_id)
                if collection.id not in [c.id for c in user_collections]:
                    raise NotFoundError(
                        resource_type="Collection",
                        resource_id=str(collection_id),
                        message="Collection not found or access denied",
                    )
        except HTTPException as e:
            # Convert HTTPException to NotFoundError to ensure consistent error handling
            if e.status_code == 404:
                raise NotFoundError(
                    resource_type="Collection", resource_id=str(collection_id), message=str(e.detail)
                ) from e
            raise

    def _validate_pipeline(self, pipeline_id: UUID4) -> None:
        """Validate pipeline configuration."""
        pipeline_config = self.pipeline_service.get_pipeline_config(pipeline_id)
        if not pipeline_config:
            raise NotFoundError(
                resource_type="Pipeline",
                resource_id=str(pipeline_id),
                message=f"Pipeline configuration not found for ID {pipeline_id}",
            )

    def _resolve_user_default_pipeline(self, user_id: UUID4) -> UUID4:
        """Resolve user's default pipeline, creating one if none exists."""
        # Try to get user's existing default pipeline
        default_pipeline = self.pipeline_service.get_default_pipeline(user_id)

        if default_pipeline:
            return default_pipeline.id

        # No default pipeline exists, check if user exists before creating one
        logger.info("Creating default pipeline for user %s", user_id)

        # Check if user exists first to avoid foreign key constraint violations
        try:
            # Try to verify user exists by checking user service
            # pylint: disable=import-outside-toplevel
            # Justification: Lazy import to avoid circular dependency with UserService
            from rag_solution.services.user_service import UserService

            user_service = UserService(self.db, self.settings)
            user = user_service.get_user(user_id)
            if not user:
                raise ConfigurationError(f"User {user_id} does not exist. Cannot create pipeline.")
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Re-raise as ConfigurationError for any user verification failure
            logger.error("Failed to verify user %s exists: %s", user_id, e)
            raise ConfigurationError(
                f"User {user_id} does not exist or cannot be verified. Cannot create pipeline."
            ) from e

        # Get user's LLM provider (or system default)
        default_provider = self.llm_provider_service.get_user_provider(user_id)
        if not default_provider:
            raise ConfigurationError("No LLM provider available for pipeline creation")

        # Create default pipeline for user
        try:
            created_pipeline = self.pipeline_service.initialize_user_pipeline(user_id, default_provider.id)
            return created_pipeline.id
        except Exception as e:
            logger.error("Failed to create pipeline for user %s: %s", user_id, e)
            raise ConfigurationError(f"Failed to create default pipeline for user {user_id}: {e}") from e

    @handle_search_errors
    async def search(self, search_input: SearchInput) -> SearchOutput:
        """Process a search query using modern pipeline architecture."""
        logger.info("🔍 Processing search query: %s", search_input.question)

        # Validate search input before executing pipeline
        self._validate_search_input(search_input)
        self._validate_collection_access(search_input.collection_id, search_input.user_id)

        return await self._search_with_pipeline(search_input)

    async def _search_with_pipeline(self, search_input: SearchInput) -> SearchOutput:
        """New stage-based pipeline architecture (Week 4).

        This method uses the modern pipeline architecture with explicit stages:
        1. PipelineResolutionStage - Resolve user's default pipeline
        2. QueryEnhancementStage - Enhance/rewrite query
        3. RetrievalStage - Retrieve documents from vector DB
        4. RerankingStage - Rerank results for relevance
        5. ReasoningStage - Apply Chain of Thought if needed
        6. GenerationStage - Generate final answer

        Each stage is independent, testable, and modifiable without affecting
        others. This enables easier maintenance, testing, and feature addition.

        Args:
            search_input: The search request

        Returns:
            SearchOutput with answer, documents, and metadata
        """
        logger.info("✨ Starting NEW pipeline architecture execution")
        logger.info("Question: %s", search_input.question)

        # Create initial search context
        context = SearchContext(
            search_input=search_input, user_id=search_input.user_id, collection_id=search_input.collection_id
        )

        # Create pipeline executor (pass empty list, stages will be added below)
        executor = PipelineExecutor(stages=[])

        # Add stages in execution order (Week 4 implementation uses all stages)
        logger.debug("Configuring pipeline with all 6 stages")

        # Stage 1: Pipeline Resolution - Get user's default pipeline configuration
        executor.add_stage(PipelineResolutionStage(self.pipeline_service))

        # Stage 2: Query Enhancement - Rewrite/enhance query for better retrieval
        executor.add_stage(QueryEnhancementStage(self.pipeline_service))

        # Stage 3: Retrieval - Get documents from vector DB
        executor.add_stage(RetrievalStage(self.pipeline_service))

        # Stage 4: Reranking - Rerank results for better relevance
        executor.add_stage(RerankingStage(self.pipeline_service))

        # Stage 5: Reasoning - Apply Chain of Thought if needed
        executor.add_stage(ReasoningStage(self.chain_of_thought_service))

        # Stage 6: Generation - Generate final answer from context
        executor.add_stage(GenerationStage(self.pipeline_service))

        # Execute pipeline
        logger.info("Executing pipeline with %d stages", len(executor.get_stage_names()))
        result_context = await executor.execute(context)

        # Check for errors
        if result_context.errors:
            logger.warning("Pipeline completed with %d errors: %s", len(result_context.errors), result_context.errors)

        # Convert SearchContext to SearchOutput
        logger.debug("Converting SearchContext to SearchOutput")

        # Clean the generated answer
        cleaned_answer = self._clean_generated_answer(result_context.generated_answer or "")

        # Build SearchOutput from context
        # Convert cot_output from ChainOfThoughtOutput to dict if present
        cot_output_dict = result_context.cot_output.model_dump() if result_context.cot_output else None

        # Debug: Log document_metadata before creating SearchOutput
        logger.info("📊 SEARCH_SERVICE: result_context.document_metadata has %d items", len(result_context.document_metadata))
        if result_context.document_metadata:
            logger.info("📊 SEARCH_SERVICE: First doc_metadata = %s", result_context.document_metadata[0].document_name if hasattr(result_context.document_metadata[0], 'document_name') else 'NO DOCUMENT_NAME')

        search_output = SearchOutput(
            answer=cleaned_answer,
            documents=result_context.document_metadata,
            query_results=result_context.query_results,
            rewritten_query=result_context.rewritten_query,
            evaluation=result_context.evaluation,
            execution_time=result_context.execution_time,
            cot_output=cot_output_dict,
            token_warning=result_context.token_warning,
            structured_answer=result_context.structured_answer,
            metadata={
                "pipeline_architecture": "v2_stage_based",
                "stages_executed": executor.get_stage_names(),
                **result_context.metadata,
            },
        )

        logger.info("✨ Pipeline execution completed successfully in %.2f seconds", result_context.execution_time)
        logger.info("Generated answer length: %d chars", len(cleaned_answer))
        logger.info("Retrieved documents: %d", len(result_context.query_results))

        return search_output

    def _estimate_token_usage(self, question: str, answer: str) -> int:
        """Estimate token usage based on text length.

        Uses a rough approximation of 4 characters per token as a baseline.
        This provides a reasonable estimate when actual token counts aren't available.
        """
        # Combine question and answer text
        total_text = f"{question} {answer}"

        # Rough estimation: ~4 characters per token
        estimated_tokens = len(total_text) // 4

        # Add some baseline tokens for processing overhead
        estimated_tokens += 50

        return max(50, estimated_tokens)  # Minimum 50 tokens

    async def _track_token_usage(
        self, user_id: UUID4, tokens_used: int, session_id: str | None = None
    ) -> TokenWarning | None:
        """Track token usage using TokenWarningService and return warning if thresholds exceeded.

        This method properly integrates with the TokenWarningService to:
        1. Track cumulative token usage
        2. Check against user limits and model constraints
        3. Generate appropriate warnings when thresholds are exceeded
        """
        try:
            logger.debug("Starting token usage tracking for user %s, tokens: %d", user_id, tokens_used)

            # Create LLMUsage object for token tracking
            try:
                logger.debug("Importing required modules for token tracking")
                # pylint: disable=import-outside-toplevel
                # Justification: Lazy imports to avoid loading schemas unless needed
                from datetime import datetime

                from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType

                logger.debug("Modules imported successfully")
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Justification: Re-raise to propagate import failure
                logger.exception("Failed to import required modules: %s", e)
                raise

            # Create a mock LLMUsage object for token tracking
            try:
                logger.debug("Creating LLMUsage object for token tracking")
                llm_usage = LLMUsage(
                    prompt_tokens=max(1, tokens_used // 2),  # Estimate prompt tokens
                    completion_tokens=max(1, tokens_used - (tokens_used // 2)),  # Estimate completion tokens
                    total_tokens=tokens_used,
                    model_name="search_estimated",  # Placeholder model name
                    service_type=ServiceType.SEARCH,
                    timestamp=datetime.utcnow(),
                    user_id=str(user_id) if user_id else None,
                    session_id=session_id,
                )
                logger.debug("LLMUsage object created: %d total tokens", llm_usage.total_tokens)
            except Exception as e:
                logger.exception("Failed to create LLMUsage object: %s", e)
                raise

            # Use TokenTrackingService to check for warnings
            try:
                logger.debug("Checking usage warning with TokenTrackingService")
                token_warning = await self.token_tracking_service.check_usage_warning(current_usage=llm_usage)
                logger.debug("Token warning check completed, result: %s", token_warning is not None)
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Justification: Re-raise to propagate warning check failure
                logger.exception("Failed to check usage warning: %s", e)
                raise

            if token_warning:
                logger.info("Token warning generated for user %s: %s", user_id, token_warning.warning_type)
                logger.debug("Token warning details: %s", token_warning)
                return token_warning

            logger.debug("No token warning generated")
            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Return None to avoid failing search due to token tracking issues
            logger.exception("Error tracking token usage: %s", e)
            # Don't fail search operation due to token tracking issues
            return None

    async def search_for_podcast(
        self,
        collection_id: UUID4,
        user_id: UUID4,
        topic: str | None = None,
        duration_minutes: int = 5,
        top_k: int | None = None,
    ) -> SearchOutput:
        """
        Specialized search for podcast content generation.

        This method is optimized for retrieving comprehensive content suitable for
        podcast generation, using multiple retrieval strategies to gather diverse
        content from the collection.

        Args:
            collection_id: Collection to search
            user_id: User requesting the search
            topic: Optional topic focus (if provided, will be used in queries)
            duration_minutes: Podcast duration (affects retrieval strategy)
            top_k: Number of documents to retrieve (defaults based on duration)

        Returns:
            SearchOutput with comprehensive content for podcast generation

        Raises:
            ValidationError: If inputs are invalid
            NotFoundError: If collection not found
            ConfigurationError: If pipeline configuration fails
        """
        logger.info("🎙️ PODCAST SEARCH: Starting specialized podcast content retrieval")
        logger.info("Collection: %s, Topic: %s, Duration: %d min", collection_id, topic, duration_minutes)

        start_time = time.time()

        # Validate inputs
        if not collection_id:
            raise ValidationError("Collection ID is required for podcast search")
        if not user_id:
            raise ValidationError("User ID is required for podcast search")

        # Set default top_k based on duration if not provided
        if top_k is None:
            top_k_map = {
                5: self.settings.podcast_retrieval_top_k_short,  # 30
                15: self.settings.podcast_retrieval_top_k_medium,  # 50
                30: self.settings.podcast_retrieval_top_k_long,  # 75
                60: self.settings.podcast_retrieval_top_k_extended,  # 100
            }
            top_k = top_k_map.get(duration_minutes, 30)

        logger.info("Using top_k=%d for %d-minute podcast", top_k, duration_minutes)

        try:
            # Validate collection access
            self._validate_collection_access(collection_id, user_id)

            # Resolve user's default pipeline
            pipeline_id = self._resolve_user_default_pipeline(user_id)
            self._validate_pipeline(pipeline_id)

            # Initialize pipeline
            collection_name = await self._initialize_pipeline(collection_id)

            # Create multiple retrieval strategies for comprehensive content
            all_query_results = []

            # Strategy 1: Topic-focused retrieval (if topic provided)
            if topic:
                topic_query = f"Comprehensive information about {topic}. Key concepts, examples, details, and insights."
                logger.info("Strategy 1: Topic-focused retrieval for '%s'", topic)
                topic_results = await self._retrieve_for_podcast(topic_query, collection_name, pipeline_id, top_k // 2)
                all_query_results.extend(topic_results)
                logger.info("Retrieved %d documents for topic-focused search", len(topic_results))

            # Strategy 2: General comprehensive retrieval
            general_query = (
                "Provide comprehensive overview of all key topics, main insights, "
                "important concepts, and significant information from this collection. "
                "Include examples, details, and practical applications."
            )
            logger.info("Strategy 2: General comprehensive retrieval")
            general_results = await self._retrieve_for_podcast(
                general_query, collection_name, pipeline_id, top_k // 2 if topic else top_k
            )
            all_query_results.extend(general_results)
            logger.info("Retrieved %d documents for general search", len(general_results))

            # Strategy 3: Diversity retrieval (for longer podcasts)
            if duration_minutes >= 15:
                diversity_query = (
                    "Find diverse content covering different aspects, perspectives, "
                    "and topics from this collection. Include various examples and use cases."
                )
                logger.info("Strategy 3: Diversity retrieval for longer podcast")
                diversity_results = await self._retrieve_for_podcast(
                    diversity_query, collection_name, pipeline_id, top_k // 3
                )
                all_query_results.extend(diversity_results)
                logger.info("Retrieved %d documents for diversity search", len(diversity_results))

            # Remove duplicates based on chunk ID
            seen_chunks = set()
            unique_results = []
            for result in all_query_results:
                chunk_id = getattr(result.chunk, "id", None) if result.chunk else None
                if chunk_id and chunk_id not in seen_chunks:
                    seen_chunks.add(chunk_id)
                    unique_results.append(result)
                elif not chunk_id:  # Include results without chunk IDs
                    unique_results.append(result)

            logger.info("Total unique documents after deduplication: %d", len(unique_results))

            # Limit to requested top_k
            if len(unique_results) > top_k:
                unique_results = unique_results[:top_k]
                logger.info("Limited to top %d documents", top_k)

            # Generate document metadata
            document_metadata = self._generate_document_metadata(unique_results, collection_id)

            # Create comprehensive summary for podcast context
            execution_time = time.time() - start_time

            # For podcast search, we don't generate an answer - just return the documents
            search_output = SearchOutput(
                answer=f"Retrieved {len(unique_results)} documents for podcast generation",
                documents=document_metadata,
                query_results=unique_results,
                rewritten_query=f"Podcast content retrieval: {topic or 'comprehensive overview'}",
                evaluation=None,
                execution_time=execution_time,
                cot_output=None,
                token_warning=None,
                metadata={
                    "podcast_search": True,
                    "duration_minutes": duration_minutes,
                    "strategies_used": ["topic-focused", "general", "diversity"][: 3 if duration_minutes >= 15 else 2],
                    "total_documents_retrieved": len(unique_results),
                    "topic": topic,
                },
            )

            logger.info("🎙️ PODCAST SEARCH: Completed successfully in %.2f seconds", execution_time)
            return search_output

        except Exception as e:
            logger.exception("Podcast search failed: %s", e)
            raise

    async def _retrieve_for_podcast(
        self,
        query: str,
        collection_name: str,
        pipeline_id: UUID4,
        top_k: int,
    ) -> list[QueryResult]:
        """
        Helper method to retrieve documents for podcast search.

        Args:
            query: Search query
            collection_name: Collection to search
            pipeline_id: Pipeline configuration ID
            top_k: Number of documents to retrieve

        Returns:
            List of query results
        """
        try:
            # Create search input for this specific query
            search_input = SearchInput(
                user_id=UUID4("00000000-0000-0000-0000-000000000000"),  # Placeholder - not used in retrieval
                collection_id=UUID4("00000000-0000-0000-0000-000000000000"),  # Placeholder - not used in retrieval
                question=query,
                config_metadata={
                    "top_k": top_k,
                    "enable_reranking": False,  # Disable reranking for podcast content
                    "enable_hierarchical": True,
                    "cot_enabled": False,  # Skip CoT for document retrieval
                },
            )

            # Execute pipeline to get documents
            pipeline_result = await self.pipeline_service.execute_pipeline(
                search_input=search_input, collection_name=collection_name, pipeline_id=pipeline_id
            )

            if not pipeline_result.success:
                logger.warning("Pipeline failed for query '%s': %s", query[:50], pipeline_result.error)
                return []

            return pipeline_result.query_results or []

        except Exception as e:
            logger.warning("Retrieval failed for query '%s': %s", query[:50], e)
            return []
