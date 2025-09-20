"""Service for handling search operations through the RAG pipeline."""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from core.config import Settings
from core.custom_exceptions import ConfigurationError, LLMProviderError, NotFoundError, ValidationError
from core.logging_utils import get_logger
from fastapi import HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session
from vectordbs.data_types import DocumentMetadata, QueryResult

from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput
from rag_solution.schemas.collection_schema import CollectionStatus
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.pipeline_service import PipelineService

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
        logger.debug("Initializing SearchService")
        self.db: Session = db
        self.settings = settings
        self._file_service: FileManagementService | None = None
        self._collection_service: CollectionService | None = None
        self._pipeline_service: PipelineService | None = None
        self._llm_provider_service: LLMProviderService | None = None
        self._chain_of_thought_service: Any | None = None

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
    def chain_of_thought_service(self) -> Any:
        """Lazy initialization of Chain of Thought service."""
        if self._chain_of_thought_service is None:
            logger.debug("Lazy initializing Chain of Thought service")
            from rag_solution.services.chain_of_thought_service import ChainOfThoughtService

            # Get default LLM provider configuration for CoT
            provider_config = self.llm_provider_service.get_default_provider()

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
                    logger.warning(f"Failed to create LLM provider instance: {e}")
            else:
                logger.warning("No default provider configuration found for CoT service")

            self._chain_of_thought_service = ChainOfThoughtService(
                settings=self.settings, llm_service=llm_service, search_service=self, db=self.db
            )
        return self._chain_of_thought_service

    def _should_use_chain_of_thought(self, search_input: SearchInput) -> bool:
        """Automatically determine if Chain of Thought should be used for this search.

        CoT is used for complex questions that benefit from reasoning:
        - Multi-part questions (how, why, explain, compare, analyze)
        - Questions with multiple clauses or conditions
        - Long questions requiring deep analysis
        - Questions explicitly asking for reasoning or explanations

        Users can override with 'show_cot_steps' for visibility or 'cot_disabled' to disable.
        """
        # Debug logging with print (temporary)
        print(f"🔍 CoT decision check for question: {search_input.question}")
        print(f"🔍 Config metadata: {search_input.config_metadata}")
        logger.error(f"CoT decision check for question: {search_input.question}")
        logger.error(f"Config metadata: {search_input.config_metadata}")

        # Allow explicit override to disable CoT
        if search_input.config_metadata and search_input.config_metadata.get("cot_disabled"):
            logger.info("CoT disabled by config")
            return False

        # Allow explicit override to enable CoT
        if search_input.config_metadata and search_input.config_metadata.get("cot_enabled"):
            print("🔍 CoT enabled by config")
            logger.error("CoT enabled by config")
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

        # No default pipeline exists, create one
        logger.info(f"Creating default pipeline for user {user_id}")

        # Get user's LLM provider (or system default)
        default_provider = self.llm_provider_service.get_user_provider(user_id)
        if not default_provider:
            raise ConfigurationError("No LLM provider available for pipeline creation")

        # Create default pipeline for user
        created_pipeline = self.pipeline_service.initialize_user_pipeline(user_id, default_provider.id)
        return created_pipeline.id

    @handle_search_errors
    async def search(self, search_input: SearchInput) -> SearchOutput:
        """Process a search query through the RAG pipeline."""
        start_time = time.time()
        logger.info("Starting search operation")

        # Validate inputs
        self._validate_search_input(search_input)
        self._validate_collection_access(search_input.collection_id, search_input.user_id)

        # Check if Chain of Thought should be used
        if self._should_use_chain_of_thought(search_input):
            logger.info("Using Chain of Thought for enhanced reasoning")
            try:
                # IMPORTANT: CoT must use the same pipeline as regular search to access documents
                # First, perform regular search to get document context
                pipeline_id = self._resolve_user_default_pipeline(search_input.user_id)
                self._validate_pipeline(pipeline_id)
                collection_name = await self._initialize_pipeline(search_input.collection_id)

                # Execute pipeline to get document context for CoT
                pipeline_result = await self.pipeline_service.execute_pipeline(
                    search_input=search_input, collection_name=collection_name, pipeline_id=pipeline_id
                )

                if not pipeline_result.success:
                    logger.warning("Pipeline failed for CoT, falling back to regular search")
                    # Fall through to regular search
                else:
                    # Convert to CoT input with document context
                    cot_input = self._convert_to_cot_input(search_input)

                    # Extract document context from pipeline results
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
                                if "content" in result and result["content"]:
                                    text_content = result["content"]
                                elif "text" in result and result["text"]:
                                    text_content = result["text"]
                                elif "chunk" in result and result["chunk"] and "text" in result["chunk"]:
                                    text_content = result["chunk"]["text"]

                            if text_content:
                                context_documents.append(text_content)

                    # Debug logging
                    logger.info(f"CoT context extraction: Found {len(context_documents)} context documents")
                    for i, doc in enumerate(context_documents[:2]):  # Log first 2 docs
                        logger.info(f"Context doc {i+1}: {doc[:100]}...")

                    # Execute CoT with document context
                    logger.info(f"Executing CoT with question: {search_input.question}")
                    cot_result = await self.chain_of_thought_service.execute_chain_of_thought(
                        cot_input, context_documents, user_id=str(search_input.user_id)
                    )

                    # Generate document metadata from pipeline results
                    document_metadata = self._generate_document_metadata(
                        pipeline_result.query_results or [], search_input.collection_id
                    )

                    # Convert CoT output to SearchOutput
                    execution_time = time.time() - start_time

                    # Include CoT reasoning steps if user requested them
                    cot_output = None
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

                    return SearchOutput(
                        answer=cot_result.final_answer,
                        documents=document_metadata,  # Use real document metadata
                        query_results=pipeline_result.query_results or [],  # Use real query results
                        rewritten_query=pipeline_result.rewritten_query,
                        evaluation=pipeline_result.evaluation,
                        execution_time=execution_time,
                        cot_output=cot_output,
                        metadata={
                            "cot_used": True,
                            "conversation_aware": True,
                            "reasoning_strategy": cot_result.reasoning_strategy,
                            "conversation_context_used": bool(search_input.config_metadata and search_input.config_metadata.get("conversation_context"))
                        }
                    )
            except Exception as e:
                logger.error(f"Chain of Thought failed, falling back to regular search: {e!s}")
                logger.error(f"CoT exception details: {type(e).__name__}: {e}")
                import traceback

                logger.error(f"CoT traceback: {traceback.format_exc()}")
                # Fall through to regular search

        # Regular search pipeline
        # Resolve user's default pipeline
        pipeline_id = self._resolve_user_default_pipeline(search_input.user_id)
        self._validate_pipeline(pipeline_id)

        # Initialize pipeline
        collection_name = await self._initialize_pipeline(search_input.collection_id)

        # Execute pipeline
        pipeline_result = await self.pipeline_service.execute_pipeline(
            search_input=search_input, collection_name=collection_name, pipeline_id=pipeline_id
        )

        if not pipeline_result.success:
            raise ConfigurationError(pipeline_result.error or "Pipeline execution failed")

        # Generate metadata
        if pipeline_result.query_results is None:
            pipeline_result.query_results = []
        document_metadata = self._generate_document_metadata(pipeline_result.query_results, search_input.collection_id)

        # Clean answer
        if pipeline_result.generated_answer is None:
            pipeline_result.generated_answer = ""
        cleaned_answer = self._clean_generated_answer(pipeline_result.generated_answer)

        # Calculate execution time
        execution_time = time.time() - start_time

        # Build response
        return SearchOutput(
            answer=cleaned_answer,
            documents=document_metadata,
            query_results=pipeline_result.query_results,
            rewritten_query=pipeline_result.rewritten_query,
            evaluation=pipeline_result.evaluation,
            execution_time=execution_time,
            cot_output=None,  # No CoT output for regular search
            metadata={
                "cot_used": False,
                "conversation_aware": bool(search_input.config_metadata and search_input.config_metadata.get("conversation_context")),
                "conversation_context_used": bool(search_input.config_metadata and search_input.config_metadata.get("conversation_context"))
            }
        )
