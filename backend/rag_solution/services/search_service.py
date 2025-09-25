"""Service for handling search operations through the RAG pipeline."""

import time
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

if TYPE_CHECKING:
    from rag_solution.services.chain_of_thought_service import ChainOfThoughtService

from core.config import Settings
from core.custom_exceptions import ConfigurationError, LLMProviderError, NotFoundError, ValidationError
from core.logging_utils import get_logger
from fastapi import HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session
from vectordbs.data_types import DocumentMetadata, QueryResult

from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput
from rag_solution.schemas.collection_schema import CollectionStatus
from rag_solution.schemas.llm_usage_schema import TokenWarning
from rag_solution.schemas.search_schema import SearchInput, SearchOutput

# ChainOfThoughtService imported above in TYPE_CHECKING block to avoid circular import
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.token_tracking_service import TokenTrackingService

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
            logger.error(f"Resource not found: {e!s}")
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValidationError as e:
            logger.error(f"Validation error: {e!s}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except LLMProviderError as e:
            logger.error(f"LLM provider error: {e!s}")
            raise HTTPException(status_code=500, detail=str(e)) from e
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e!s}")
            raise HTTPException(status_code=500, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Unexpected error during search: {e!s}")
            raise HTTPException(status_code=500, detail=f"Error processing search: {e!s}") from e

    return wrapper


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
            from rag_solution.services.chain_of_thought_service import ChainOfThoughtService

            # Get default LLM provider configuration for CoT
            try:
                provider_config = self.llm_provider_service.get_default_provider()
                logger.debug(f"Retrieved provider config: {provider_config}")
            except Exception as e:
                logger.exception(f"Failed to get default provider configuration: {e}")
                provider_config = None

            # Create actual LLM provider instance if config is available
            llm_service = None
            if provider_config:
                try:
                    from rag_solution.generation.providers.factory import LLMProviderFactory

                    # Use the factory to create the provider instance properly
                    factory = LLMProviderFactory(self.db)
                    llm_service = factory.get_provider(provider_config.name)
                    logger.debug(f"Using {provider_config.name} LLM provider for CoT service")
                except Exception as e:
                    logger.exception(f"Failed to create LLM provider instance: {e}")
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
                logger.exception(f"Failed to initialize Chain of Thought service: {e}")
                raise ConfigurationError(f"Failed to initialize Chain of Thought service: {e}") from e
        return self._chain_of_thought_service

    @property
    def token_tracking_service(self) -> TokenTrackingService:
        """Lazy initialization of token tracking service."""
        if self._token_tracking_service is None:
            logger.debug("Lazy initializing token tracking service")
            self._token_tracking_service = TokenTrackingService(self.db, self.settings)
        return self._token_tracking_service

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
        logger.info(f"🔍 CoT decision check for question: {search_input.question}")
        logger.info(f"🔍 Config metadata: {search_input.config_metadata}")
        logger.debug(f"CoT decision check for question: {search_input.question}")
        logger.debug(f"Config metadata: {search_input.config_metadata}")

        # Allow explicit override to disable CoT
        if search_input.config_metadata and search_input.config_metadata.get("cot_disabled"):
            logger.info("🔍 CoT disabled by config")
            logger.debug("CoT disabled by config")
            return False

        # Allow explicit override to enable CoT - FORCE ENABLED
        if search_input.config_metadata and search_input.config_metadata.get("cot_enabled"):
            logger.info("🔍 CoT FORCE ENABLED by config")
            logger.debug("CoT FORCE ENABLED by config")
            logger.info("🚨 FORCED COT ENABLED 🚨")
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
            f"CoT decision: {should_use_cot} (patterns={has_complex_patterns}, "
            f"multiple={multiple_questions}, long={is_long_question}, "
            f"reasoning={asks_for_reasoning}, length={question_length})"
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
            logger.error(f"Error initializing pipeline: {e!s}")
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

        logger.debug(f"Generated metadata for {len(doc_metadata)} documents")
        return doc_metadata

    def _clean_generated_answer(self, answer: str) -> str:
        """
        Clean generated answer by removing artifacts and duplicates.

        Removes:
        - " AND " artifacts from query rewriting
        - Duplicate consecutive words
        - Leading/trailing whitespace
        """
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
                elif collection.status == CollectionStatus.CREATED:
                    raise ValidationError(
                        f"Collection {collection_id} has no documents. Please upload documents before searching."
                    )
                elif collection.status == CollectionStatus.ERROR:
                    raise ValidationError(
                        f"Collection {collection_id} encountered errors during processing. Please check collection status."
                    )
                else:
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
        logger.info(f"Creating default pipeline for user {user_id}")

        # Check if user exists first to avoid foreign key constraint violations
        try:
            # Try to verify user exists by checking user service
            from rag_solution.services.user_service import UserService

            user_service = UserService(self.db, self.settings)
            user = user_service.get_user(user_id)
            if not user:
                raise ConfigurationError(f"User {user_id} does not exist. Cannot create pipeline.")
        except Exception as e:
            logger.error(f"Failed to verify user {user_id} exists: {e}")
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
            logger.error(f"Failed to create pipeline for user {user_id}: {e}")
            raise ConfigurationError(f"Failed to create default pipeline for user {user_id}: {e}") from e

    @handle_search_errors
    async def search(self, search_input: SearchInput) -> SearchOutput:
        """Process a search query through the RAG pipeline."""
        logger.info("🔍 SEARCH SERVICE: METHOD ENTRY - search() called!")
        start_time = time.time()
        logger.info("Starting search operation")
        logger.info(f"🔍 SEARCH SERVICE: search() called with question: {search_input.question}")
        logger.info(f"🔍 SEARCH SERVICE: config_metadata: {search_input.config_metadata}")
        logger.info("🔍 SEARCH SERVICE: search() method STARTED")

        # Validate inputs
        try:
            logger.debug("Validating search input")
            self._validate_search_input(search_input)
            logger.debug("Search input validation successful")
        except Exception as e:
            logger.exception(f"Search input validation failed: {e}")
            raise

        try:
            logger.debug("Validating collection access")
            self._validate_collection_access(search_input.collection_id, search_input.user_id)
            logger.debug("Collection access validation successful")
        except Exception as e:
            logger.exception(f"Collection access validation failed: {e}")
            raise

        # Check if Chain of Thought should be used
        logger.info("🔍 SEARCH SERVICE: About to check _should_use_chain_of_thought")

        # TEMPORARY FIX: Force CoT when explicitly enabled
        force_cot = search_input.config_metadata and search_input.config_metadata.get("cot_enabled")
        logger.info(f"🔍 SEARCH SERVICE: force_cot = {force_cot}")
        logger.info(f"🔍 SEARCH SERVICE: config_metadata = {search_input.config_metadata}")

        # FORCE CoT when explicitly enabled - bypass detection logic
        cot_should_be_used = force_cot
        if not cot_should_be_used:
            try:
                logger.debug("Running CoT decision logic")
                cot_should_be_used = self._should_use_chain_of_thought(search_input)
                logger.debug(f"CoT decision logic returned: {cot_should_be_used}")
            except Exception as e:
                logger.exception(f"CoT decision logic failed: {e}")
                cot_should_be_used = False
        logger.info(f"🔍 SEARCH SERVICE: _should_use_chain_of_thought returned: {cot_should_be_used}")

        if cot_should_be_used:
            logger.info("🔍 SEARCH SERVICE: CoT will be used!")
            logger.info("Using Chain of Thought for enhanced reasoning")
            try:
                logger.debug("Starting Chain of Thought processing")
                # IMPORTANT: CoT must use the same pipeline as regular search to access documents
                # First, perform regular search to get document context
                try:
                    logger.debug("Resolving user default pipeline")
                    pipeline_id = self._resolve_user_default_pipeline(search_input.user_id)
                    logger.debug(f"Resolved pipeline ID: {pipeline_id}")
                except Exception as e:
                    logger.exception(f"Failed to resolve user default pipeline: {e}")
                    raise

                try:
                    logger.debug("Validating pipeline")
                    self._validate_pipeline(pipeline_id)
                    logger.debug("Pipeline validation successful")
                except Exception as e:
                    logger.exception(f"Pipeline validation failed: {e}")
                    raise

                try:
                    logger.debug("Initializing pipeline")
                    collection_name = await self._initialize_pipeline(search_input.collection_id)
                    logger.debug(f"Pipeline initialized with collection: {collection_name}")
                except Exception as e:
                    logger.exception(f"Pipeline initialization failed: {e}")
                    raise

                # Execute pipeline to get document context for CoT
                logger.info("🔍 SEARCH SERVICE: About to execute pipeline for CoT")
                try:
                    logger.debug("Executing pipeline for CoT context")
                    pipeline_result = await self.pipeline_service.execute_pipeline(
                        search_input=search_input, collection_name=collection_name, pipeline_id=pipeline_id
                    )
                    logger.debug("Pipeline execution completed")
                except Exception as e:
                    logger.exception(f"Pipeline execution failed: {e}")
                    raise

                logger.info(f"🔍 SEARCH SERVICE: Pipeline result - success: {pipeline_result.success}")
                logger.info(
                    f"🔍 SEARCH SERVICE: Pipeline result - query_results count: {len(pipeline_result.query_results) if pipeline_result.query_results else 0}"
                )

                if not pipeline_result.success:
                    logger.info("🔍 SEARCH SERVICE: Pipeline FAILED for CoT, falling back to regular search")
                    logger.warning("Pipeline failed for CoT, falling back to regular search")
                    # Fall through to regular search
                else:
                    logger.info("🔍 SEARCH SERVICE: Pipeline SUCCESS, proceeding with CoT")
                    # Convert to CoT input with document context
                    try:
                        logger.debug("Converting to CoT input")
                        cot_input = self._convert_to_cot_input(search_input)
                        logger.debug("CoT input conversion successful")
                    except Exception as e:
                        logger.exception(f"Failed to convert to CoT input: {e}")
                        raise

                    # Extract document context from pipeline results
                    try:
                        logger.debug("Extracting document context from pipeline results")
                        context_documents = []
                        if pipeline_result.query_results:
                            for result in pipeline_result.query_results:
                                # Handle different result structures
                                text_content = None
                                if hasattr(result, "content") and result.content:
                                    text_content = result.content
                                elif hasattr(result, "text") and result.text:
                                    text_content = result.text
                                elif hasattr(result, "chunk") and result.chunk and hasattr(result.chunk, "text"):
                                    text_content = result.chunk.text
                                elif isinstance(result, dict):
                                    if result.get("content"):
                                        text_content = result["content"]
                                    elif result.get("text"):
                                        text_content = result["text"]
                                    elif "chunk" in result and result["chunk"] and "text" in result["chunk"]:
                                        text_content = result["chunk"]["text"]

                                if text_content:
                                    context_documents.append(text_content)
                        logger.debug(f"Extracted {len(context_documents)} context documents")
                    except Exception as e:
                        logger.exception(f"Failed to extract document context: {e}")
                        raise

                    # Debug logging
                    logger.info(f"CoT context extraction: Found {len(context_documents)} context documents")
                    for i, doc in enumerate(context_documents[:2]):  # Log first 2 docs
                        logger.info(f"Context doc {i + 1}: {doc[:100]}...")

                    # Execute CoT with document context
                    logger.info(f"🔍 SEARCH SERVICE: About to execute CoT with {len(context_documents)} context docs")
                    logger.info(f"Executing CoT with question: {search_input.question}")
                    try:
                        logger.debug("Starting CoT execution")
                        cot_result = await self.chain_of_thought_service.execute_chain_of_thought(
                            cot_input, context_documents, user_id=str(search_input.user_id)
                        )
                        logger.debug("CoT execution completed successfully")
                        logger.info(f"🔍 SEARCH SERVICE: CoT execution SUCCESS - result type: {type(cot_result)}")
                        logger.info(
                            f"🔍 SEARCH SERVICE: CoT result has token_usage: {hasattr(cot_result, 'token_usage')}"
                        )
                        if hasattr(cot_result, "token_usage"):
                            logger.info(f"🔍 SEARCH SERVICE: CoT token_usage: {cot_result.token_usage}")
                        logger.info(
                            f"🔍 SEARCH SERVICE: CoT reasoning_steps count: {len(cot_result.reasoning_steps) if hasattr(cot_result, 'reasoning_steps') and cot_result.reasoning_steps else 0}"
                        )
                        if hasattr(cot_result, "reasoning_steps") and cot_result.reasoning_steps:
                            for i, step in enumerate(cot_result.reasoning_steps):
                                logger.info(
                                    f"🔍 SEARCH SERVICE: Step {i + 1}: {step.step_number} - {step.question[:50]}..."
                                )
                    except Exception as e:
                        logger.info(f"🔍 SEARCH SERVICE: CoT execution FAILED: {e}")
                        logger.exception(f"CoT execution failed: {e}")
                        raise

                    # Generate document metadata from pipeline results
                    try:
                        logger.debug("Generating document metadata from pipeline results")
                        document_metadata = self._generate_document_metadata(
                            pipeline_result.query_results or [], search_input.collection_id
                        )
                        logger.debug(f"Generated metadata for {len(document_metadata)} documents")
                    except Exception as e:
                        logger.exception(f"Failed to generate document metadata: {e}")
                        raise

                    # Convert CoT output to SearchOutput
                    try:
                        logger.debug("Converting CoT output to SearchOutput")
                        execution_time = time.time() - start_time

                        # Track token usage if available
                        token_warning = None
                        if hasattr(cot_result, "token_usage") and cot_result.token_usage > 0:
                            try:
                                logger.debug("Tracking token usage for CoT")
                                # Use TokenWarningService to track and generate warnings
                                session_id = (
                                    search_input.config_metadata.get("session_id")
                                    if search_input.config_metadata
                                    else None
                                )
                                token_warning = await self._track_token_usage(
                                    user_id=search_input.user_id,
                                    tokens_used=cot_result.token_usage,
                                    session_id=session_id,
                                )
                                logger.debug("Token usage tracking completed")
                            except Exception as e:
                                logger.exception(f"Failed to track token usage: {e}")
                                # Don't fail the search due to token tracking issues
                        logger.debug("CoT output conversion completed")
                    except Exception as e:
                        logger.exception(f"Failed to convert CoT output to SearchOutput: {e}")
                        raise

                    # Include CoT reasoning steps if user requested them
                    try:
                        logger.debug("Preparing CoT output for response")
                        cot_output = None
                        logger.info(
                            f"🔍 SEARCH SERVICE: _should_show_cot_steps result: {self._should_show_cot_steps(search_input)}"
                        )
                        logger.info(f"🔍 SEARCH SERVICE: config_metadata: {search_input.config_metadata}")
                        if self._should_show_cot_steps(search_input):
                            cot_output = {
                                "original_question": cot_result.original_question,
                                "reasoning_steps": [
                                    {
                                        "step_number": step.step_number,
                                        "step_question": step.question,
                                        "intermediate_answer": step.intermediate_answer,
                                        "confidence_score": step.confidence_score,
                                        "reasoning_trace": step.reasoning_trace,
                                        "execution_time": step.execution_time,
                                        "context_used": step.context_used,
                                    }
                                    for step in cot_result.reasoning_steps
                                ],
                                "final_answer": cot_result.final_answer,
                                "total_confidence": cot_result.total_confidence,
                                "total_execution_time": cot_result.total_execution_time,
                                "reasoning_strategy": cot_result.reasoning_strategy,
                            }
                        logger.debug("CoT output preparation completed")
                    except Exception as e:
                        logger.exception(f"Failed to prepare CoT output: {e}")
                        # Don't fail the search due to CoT output preparation issues
                        cot_output = None

                    try:
                        logger.debug("Creating SearchOutput for CoT result")
                        search_output: SearchOutput = SearchOutput(
                            answer=cot_result.final_answer,
                            documents=document_metadata,  # Use real document metadata
                            query_results=pipeline_result.query_results or [],  # Use real query results
                            rewritten_query=pipeline_result.rewritten_query,
                            evaluation=pipeline_result.evaluation,
                            execution_time=execution_time,
                            cot_output=cot_output,
                            token_warning=token_warning,
                            metadata={
                                "cot_used": True,
                                "conversation_aware": True,
                                "reasoning_strategy": cot_result.reasoning_strategy,
                                "conversation_context_used": bool(
                                    search_input.config_metadata
                                    and search_input.config_metadata.get("conversation_context")
                                ),
                            },
                        )
                        logger.debug("SearchOutput created successfully for CoT")
                        return search_output
                    except Exception as e:
                        logger.exception(f"Failed to create SearchOutput for CoT result: {e}")
                        raise
            except Exception as e:
                logger.error(f"Chain of Thought failed, falling back to regular search: {e!s}")
                logger.exception(f"CoT exception details: {type(e).__name__}: {e}")
                import traceback

                logger.error(f"CoT traceback: {traceback.format_exc()}")
                # Fall through to regular search

        # Regular search pipeline
        try:
            logger.debug("Starting regular search pipeline")
            # Resolve user's default pipeline
            try:
                logger.debug("Resolving user default pipeline for regular search")
                pipeline_id = self._resolve_user_default_pipeline(search_input.user_id)
                logger.debug(f"Resolved pipeline ID: {pipeline_id}")
            except Exception as e:
                logger.exception(f"Failed to resolve user default pipeline for regular search: {e}")
                raise

            try:
                logger.debug("Validating pipeline for regular search")
                self._validate_pipeline(pipeline_id)
                logger.debug("Pipeline validation successful")
            except Exception as e:
                logger.exception(f"Pipeline validation failed for regular search: {e}")
                raise

            try:
                logger.debug("Initializing pipeline for regular search")
                collection_name = await self._initialize_pipeline(search_input.collection_id)
                logger.debug(f"Pipeline initialized with collection: {collection_name}")
            except Exception as e:
                logger.exception(f"Pipeline initialization failed for regular search: {e}")
                raise

            try:
                logger.debug("Executing pipeline for regular search")
                pipeline_result = await self.pipeline_service.execute_pipeline(
                    search_input=search_input, collection_name=collection_name, pipeline_id=pipeline_id
                )
                logger.debug("Pipeline execution completed for regular search")
            except Exception as e:
                logger.exception(f"Pipeline execution failed for regular search: {e}")
                raise
        except Exception as e:
            logger.exception(f"Regular search pipeline failed: {e}")
            raise

        if not pipeline_result.success:
            logger.error(f"Pipeline execution failed: {pipeline_result.error}")
            raise ConfigurationError(pipeline_result.error or "Pipeline execution failed")

        # Generate metadata
        try:
            logger.debug("Generating document metadata for regular search")
            if pipeline_result.query_results is None:
                pipeline_result.query_results = []
            document_metadata = self._generate_document_metadata(
                pipeline_result.query_results, search_input.collection_id
            )
            logger.debug(f"Generated metadata for {len(document_metadata)} documents")
        except Exception as e:
            logger.exception(f"Failed to generate document metadata for regular search: {e}")
            raise

        # Clean answer
        try:
            logger.debug("Cleaning generated answer")
            if pipeline_result.generated_answer is None:
                pipeline_result.generated_answer = ""
            cleaned_answer = self._clean_generated_answer(pipeline_result.generated_answer)
            logger.debug("Answer cleaning completed")
        except Exception as e:
            logger.exception(f"Failed to clean generated answer: {e}")
            raise

        # Calculate execution time
        execution_time = time.time() - start_time
        logger.debug(f"Total execution time: {execution_time:.2f} seconds")

        # Track token usage for regular search (estimate based on content length)
        try:
            logger.debug("Estimating and tracking token usage")
            estimated_tokens = self._estimate_token_usage(search_input.question, cleaned_answer)
            session_id = search_input.config_metadata.get("session_id") if search_input.config_metadata else None
            token_warning = await self._track_token_usage(
                user_id=search_input.user_id, tokens_used=estimated_tokens, session_id=session_id
            )
            logger.debug("Token usage tracking completed")
        except Exception as e:
            logger.exception(f"Failed to track token usage for regular search: {e}")
            # Don't fail the search due to token tracking issues
            token_warning = None

        # Build response
        try:
            logger.debug("Creating SearchOutput for regular search")
            regular_search_output: SearchOutput = SearchOutput(
                answer=cleaned_answer,
                documents=document_metadata,
                query_results=pipeline_result.query_results or [],
                rewritten_query=pipeline_result.rewritten_query,
                evaluation=pipeline_result.evaluation,
                execution_time=execution_time,
                cot_output=None,  # No CoT output for regular search
                token_warning=token_warning,
                metadata={
                    "cot_used": False,
                    "conversation_aware": bool(
                        search_input.config_metadata and search_input.config_metadata.get("conversation_context")
                    ),
                    "conversation_context_used": bool(
                        search_input.config_metadata and search_input.config_metadata.get("conversation_context")
                    ),
                },
            )
            logger.debug("SearchOutput created successfully for regular search")
            logger.info("Search operation completed successfully")
            return regular_search_output
        except Exception as e:
            logger.exception(f"Failed to create SearchOutput for regular search: {e}")
            raise

    def _estimate_token_usage(self, question: str, answer: str) -> int:
        """Estimate token usage based on text length.

        Uses a rough approximation of 4 characters per token as a baseline.
        This provides a reasonable estimate when actual token counts aren't available.
        """
        # Get model name from provider
        try:
            provider = self.llm_provider_service.get_default_provider()
            if provider and hasattr(provider, "_default_model_id"):
                model_name = provider._default_model_id
            else:
                model_name = "gpt-3.5-turbo"  # Fallback
        except Exception:
            model_name = "gpt-3.5-turbo"  # Fallback

        # Use token_tracking_service for accurate counting
        if self.token_tracking_service:
            # Count tokens for question and answer separately for better accuracy
            question_tokens = self.token_tracking_service.count_tokens(question, model_name)
            answer_tokens = self.token_tracking_service.count_tokens(answer, model_name)
            total_tokens = question_tokens + answer_tokens

            # Add some baseline tokens for system prompts and processing overhead
            total_tokens += 50

            return max(50, total_tokens)
        else:
            # Fallback to estimation
            total_text = f"{question} {answer}"
            estimated_tokens = len(total_text) // 4
            estimated_tokens += 50
            return max(50, estimated_tokens)

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
            logger.debug(f"Starting token usage tracking for user {user_id}, tokens: {tokens_used}")

            # Create LLMUsage object for token tracking
            try:
                logger.debug("Importing required modules for token tracking")
                from datetime import datetime

                from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType

                logger.debug("Modules imported successfully")
            except Exception as e:
                logger.exception(f"Failed to import required modules: {e}")
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
                logger.debug(f"LLMUsage object created: {llm_usage.total_tokens} total tokens")
            except Exception as e:
                logger.exception(f"Failed to create LLMUsage object: {e}")
                raise

            # Use TokenTrackingService to check for warnings
            try:
                logger.debug("Checking usage warning with TokenTrackingService")
                token_warning = await self.token_tracking_service.check_usage_warning(current_usage=llm_usage)
                logger.debug(f"Token warning check completed, result: {token_warning is not None}")
            except Exception as e:
                logger.exception(f"Failed to check usage warning: {e}")
                raise

            if token_warning:
                logger.info(f"Token warning generated for user {user_id}: {token_warning.warning_type}")
                logger.debug(f"Token warning details: {token_warning}")
                return token_warning

            logger.debug("No token warning generated")
            return None

        except Exception as e:
            logger.exception(f"Error tracking token usage: {e}")
            # Don't fail search operation due to token tracking issues
            return None
