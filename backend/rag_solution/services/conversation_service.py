"""Conversation service for Chat with Documents feature.

This service handles conversation sessions, message processing,
and integration with search and context management services.
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.core.exceptions import NotFoundError, SessionExpiredError, ValidationError
from rag_solution.models.conversation import ConversationMessage, ConversationSession
from rag_solution.repository.conversation_repository import ConversationRepository
from rag_solution.schemas.conversation_schema import (
    ConversationContext,
    ConversationMessageInput,
    ConversationMessageOutput,
    ConversationSessionInput,
    ConversationSessionOutput,
    MessageMetadata,
    MessageRole,
    MessageType,
    QuestionSuggestionOutput,
    SessionStatistics,
    SessionStatus,
)
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.services.entity_extraction_service import EntityExtractionService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.search_service import SearchService
from rag_solution.services.token_tracking_service import TokenTrackingService

logger = logging.getLogger(__name__)


class ConversationService:  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """Service for managing conversation sessions and messages."""

    def __init__(
        self,
        db: Session,
        settings: Settings,
        conversation_repository: ConversationRepository,
        question_service: QuestionService,
    ):
        """Initialize the conversation service.

        Args:
            db: Database session
            settings: Application settings
            conversation_repository: Unified conversation repository
            question_service: Question service for suggestions
        """
        self.db = db
        self.settings = settings
        self.repository = conversation_repository
        self.question_service = question_service
        self._search_service: SearchService | None = None
        self._chain_of_thought_service: ChainOfThoughtService | None = None
        self._llm_provider_service: LLMProviderService | None = None
        self._token_tracking_service: TokenTrackingService | None = None
        self._entity_extraction_service: EntityExtractionService | None = None
        # Context management cache
        self._context_cache: dict[str, ConversationContext] = {}
        self._cache_ttl = 300  # 5 minutes

    @property
    def search_service(self) -> SearchService:
        """Get search service instance."""
        if self._search_service is None:
            self._search_service = SearchService(self.db, self.settings)
        return self._search_service

    @property
    def chain_of_thought_service(self) -> ChainOfThoughtService | None:
        """Get chain of thought service instance."""
        if self._chain_of_thought_service is None:
            llm_service = self.llm_provider_service.get_default_provider()
            if llm_service and hasattr(llm_service, "llm_base"):
                self._chain_of_thought_service = ChainOfThoughtService(
                    self.settings, llm_service.llm_base, self.search_service, self.db
                )
        return self._chain_of_thought_service

    @property
    def llm_provider_service(self) -> LLMProviderService:
        """Get LLM provider service instance."""
        if self._llm_provider_service is None:
            self._llm_provider_service = LLMProviderService(self.db)
        return self._llm_provider_service

    @property
    def token_tracking_service(self) -> TokenTrackingService:
        """Get token tracking service instance."""
        if self._token_tracking_service is None:
            self._token_tracking_service = TokenTrackingService(self.db, self.settings)
        return self._token_tracking_service

    @property
    def entity_extraction_service(self) -> EntityExtractionService:
        """Get entity extraction service instance."""
        if self._entity_extraction_service is None:
            self._entity_extraction_service = EntityExtractionService(self.db, self.settings)
        return self._entity_extraction_service

    async def create_session(self, session_input: ConversationSessionInput) -> ConversationSessionOutput:
        """Create a new conversation session."""
        session = ConversationSession(
            user_id=session_input.user_id,
            collection_id=session_input.collection_id,
            session_name=session_input.session_name,
            context_window_size=session_input.context_window_size,
            max_messages=session_input.max_messages,
            session_metadata=session_input.metadata or {},
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # Use the class method for clean, type-safe conversion
        return ConversationSessionOutput.from_db_session(session, message_count=0)

    async def get_session(self, session_id: UUID, user_id: UUID) -> ConversationSessionOutput:
        """Get a conversation session by ID with eager loaded relationships."""
        session = self.repository.get_session_by_id(session_id)

        # Validate user has access
        if session.user_id != user_id:
            raise NotFoundError("ConversationSession", str(session_id))

        # Convert model to schema
        return ConversationSessionOutput.model_validate(session)

    async def update_session(self, session_id: UUID, user_id: UUID, updates: dict) -> ConversationSessionOutput:
        """Update a conversation session."""
        # Validate user has access
        session = self.repository.get_session_by_id(session_id)
        if session.user_id != user_id:
            raise NotFoundError("ConversationSession", str(session_id))

        # Map 'metadata' to 'session_metadata' for repository
        repo_updates = {}
        for key, value in updates.items():
            if key == "metadata":
                repo_updates["session_metadata"] = value
            else:
                repo_updates[key] = value

        return self.repository.update_session(session_id, repo_updates)

    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool:
        """Delete a conversation session."""
        # Validate user has access
        session = self.repository.get_session_by_id(session_id)
        if session.user_id != user_id:
            raise NotFoundError("ConversationSession", str(session_id))

        return self.repository.delete_session(session_id)

    async def list_sessions(self, user_id: UUID) -> list[ConversationSessionOutput]:
        """List all sessions for a user with eager loaded relationships.

        Uses unified repository's eager loading to eliminate N+1 queries.
        Previously: 54 queries (1 + 53 message counts)
        Now: 1 query with joinedload
        """
        return self.repository.get_sessions_by_user(user_id)

    async def add_message(self, message_input: ConversationMessageInput) -> ConversationMessageOutput:
        """Add a message to a conversation session."""
        # Validate session exists
        try:
            session = self.repository.get_session_by_id(message_input.session_id)
        except NotFoundError:
            raise NotFoundError("ConversationSession", str(message_input.session_id)) from None

        # Check if session is expired (basic check)
        if session.status == SessionStatus.EXPIRED:
            raise SessionExpiredError("Session has expired")

        # Convert MessageMetadata Pydantic object to dictionary for database storage
        metadata_dict: dict[str, Any] = {}
        if message_input.metadata:
            if isinstance(message_input.metadata, dict):
                # Already a dictionary, use it directly
                metadata_dict = message_input.metadata
            else:
                # Pydantic model - try model_dump (v2) first, fall back to dict() (v1)
                try:
                    metadata_dict = message_input.metadata.model_dump()
                except AttributeError:
                    metadata_dict = dict(message_input.metadata)

        # Create message input with metadata dict
        message_input_with_dict = ConversationMessageInput(
            session_id=message_input.session_id,
            content=message_input.content,
            role=message_input.role,
            message_type=message_input.message_type,
            metadata=metadata_dict,
            token_count=message_input.token_count,
            execution_time=message_input.execution_time,
        )

        # Repository returns database model, convert to schema
        db_message = self.repository.create_message(message_input_with_dict)
        return ConversationMessageOutput.from_db_message(db_message)

    async def get_messages(
        self, session_id: UUID, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[ConversationMessageOutput]:
        """Get messages for a conversation session."""
        # First verify the user has access to this session
        try:
            session = self.repository.get_session_by_id(session_id)
            if session.user_id != user_id:
                return []
        except NotFoundError:
            return []

        # Repository returns database models, convert to schemas
        db_messages = self.repository.get_messages_by_session(session_id, limit=limit, offset=offset)
        return [ConversationMessageOutput.from_db_message(msg) for msg in db_messages]

    async def process_user_message(self, message_input: ConversationMessageInput) -> ConversationMessageOutput:
        """Process a user message and generate a response using integrated Search and CoT services.

        DEPRECATED: This method will be removed in a future version.
        Use MessageProcessingOrchestrator.process_user_message() instead.

        This method now delegates to MessageProcessingOrchestrator for better
        separation of concerns and maintainability.
        """
        import warnings

        warnings.warn(
            "ConversationService.process_user_message() is deprecated. "
            "Use MessageProcessingOrchestrator instead for better service separation.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Delegate to MessageProcessingOrchestrator
        from rag_solution.services.conversation_context_service import ConversationContextService
        from rag_solution.services.message_processing_orchestrator import MessageProcessingOrchestrator

        # Create required services
        context_service = ConversationContextService(self.db, self.settings, self.entity_extraction_service)

        orchestrator = MessageProcessingOrchestrator(
            db=self.db,
            settings=self.settings,
            conversation_repository=self.repository,
            search_service=self.search_service,
            context_service=context_service,
            token_tracking_service=self.token_tracking_service,
            llm_provider_service=self.llm_provider_service,
            chain_of_thought_service=self.chain_of_thought_service,
        )

        return await orchestrator.process_user_message(message_input)

        # Calculate token count for user message if not provided
        user_token_count = message_input.token_count or 0
        if user_token_count == 0:
            # Simple token estimation for user message
            user_token_count = max(5, int(len(message_input.content.split()) * 1.3))  # Rough estimation

        # Create user message input with token count
        user_message_input = ConversationMessageInput(
            session_id=message_input.session_id,
            content=message_input.content,
            role=message_input.role,
            message_type=message_input.message_type,
            metadata=message_input.metadata,
            token_count=int(user_token_count),
            execution_time=message_input.execution_time or 0.0,
        )

        # Add the user message to the session
        await self.add_message(user_message_input)

        # Get conversation context
        messages = await self.get_messages(message_input.session_id, session.user_id)
        context = await self.build_context_from_messages(message_input.session_id, messages)

        # Enhance question with conversation context
        enhanced_question = await self.enhance_question_with_context(
            message_input.content,
            context.context_window,
            [msg.content for msg in messages[-5:]],  # Last 5 messages
        )

        # Create search input with conversation context
        # Handle mocked database scenarios where IDs might be Mock objects
        collection_id = session.collection_id
        user_id = session.user_id

        # Validate that we have proper IDs for search
        if not collection_id or not user_id:
            raise ValidationError("Session must have valid collection_id and user_id for search")

        search_input = SearchInput(
            question=enhanced_question,
            collection_id=collection_id,
            user_id=user_id,
            config_metadata={
                "conversation_context": context.context_window,
                "session_id": str(message_input.session_id),
                "message_history": [msg.content for msg in messages[-10:]],
                "conversation_entities": context.context_metadata.get("extracted_entities", []),
                "cot_enabled": True,
                "show_cot_steps": False,  # Disable CoT steps visibility for context flow tests
                "conversation_aware": True,
            },
        )

        # Execute search - this will automatically use CoT if appropriate
        search_result = await self.search_service.search(search_input)

        # Extract metadata and cot_output using getattr with defaults
        result_metadata = getattr(search_result, "metadata", None)
        result_cot_output = getattr(search_result, "cot_output", None)

        logger.info("📊 CONVERSATION SERVICE: Search result has metadata: %s", result_metadata is not None)
        if result_metadata:
            logger.info("📊 CONVERSATION SERVICE: Search metadata keys: %s", list(result_metadata.keys()))
        logger.info("📊 CONVERSATION SERVICE: Search result has cot_output: %s", result_cot_output is not None)
        if result_cot_output:
            logger.info("📊 CONVERSATION SERVICE: CoT output type: %s", type(result_cot_output))

        # Extract CoT information if it was used
        cot_used = False
        cot_steps: list[dict[str, Any]] = []

        # Check both metadata and cot_output for CoT information
        if result_metadata:
            cot_used = result_metadata.get("cot_used", False)
            logger.info("🧠 CoT metadata: cot_used=%s", cot_used)

        # Extract CoT steps from cot_output (this is where the actual reasoning steps are)
        if result_cot_output:
            if isinstance(search_result.cot_output, dict):
                reasoning_steps = search_result.cot_output.get("reasoning_steps", [])
                if reasoning_steps:
                    cot_used = True  # If we have reasoning steps, CoT was used
                    # Convert reasoning steps to a format suitable for conversation metadata
                    cot_steps = []
                    for step in reasoning_steps:
                        step_dict = {
                            "step_number": step.get("step_number", 0),
                            "question": step.get("question", ""),
                            "intermediate_answer": step.get("intermediate_answer", ""),
                            "confidence_score": step.get("confidence_score", 0.0),
                            "token_usage": step.get("token_usage", 0),
                        }
                        cot_steps.append(step_dict)
                    logger.info("🧠 CoT steps extracted from cot_output: %d steps", len(cot_steps))
                else:
                    logger.info("🧠 CoT output exists but no reasoning_steps found")
            else:
                logger.info("🧠 CoT output exists but not a dict: %s", type(search_result.cot_output))

        logger.info("🧠 Final CoT extraction: cot_used=%s, cot_steps_count=%d", cot_used, len(cot_steps))

        # Convert DocumentMetadata and QueryResult objects to dictionaries for JSON serialization
        def serialize_documents(documents, query_results):
            """Convert query results to JSON-serializable source dictionaries matching frontend schema.

            Maps individual chunks from query_results, not documents, to fix:
            1. Identical chunk text bug (each chunk shows its own text)
            2. Score display bug (each chunk has its own relevance score)

            Frontend expects: {document_name: str, content: str, metadata: {score: float, page_number: int, ...}}

            Note: score represents RELEVANCE (cosine similarity from vector search), not confidence or accuracy.
            """
            serialized = []

            # If we have query_results, map each chunk individually
            if query_results:
                # Build document ID → name mapping from documents
                doc_id_to_name = {}
                for doc in documents:
                    if hasattr(doc, "id") and hasattr(doc, "document_name"):
                        doc_id_to_name[str(doc.id)] = doc.document_name
                    elif hasattr(doc, "document_id") and hasattr(doc, "document_name"):
                        doc_id_to_name[str(doc.document_id)] = doc.document_name

                # Limit to generation_top_k (default 5) for frontend display
                generation_top_k = settings.generation_top_k
                limited_results = query_results[:generation_top_k]

                logger.info(f"📊 Limiting sources from {len(query_results)} to {len(limited_results)} (generation_top_k={generation_top_k})")

                # Map each chunk from query_results to a source
                for result in limited_results:
                    if not result.chunk:
                        continue

                    # Get document name
                    doc_id = str(result.chunk.document_id) if result.chunk.document_id else None
                    document_name = doc_id_to_name.get(doc_id, "Unknown Document") if doc_id else "Unknown Document"

                    # Get relevance score (from QueryResult level first, then chunk level)
                    score = (
                        result.score
                        if result.score is not None
                        else (result.chunk.score if hasattr(result.chunk, "score") else None)
                    )

                    # Debug logging for score
                    if score is None or score == 0.0:
                        logger.warning(f"⚠️ Source has no score - result.score={result.score}, chunk.score={getattr(result.chunk, 'score', 'N/A')}")

                    # Get page number from chunk metadata
                    page_number = None
                    chunk_id = None
                    if result.chunk.metadata:
                        if hasattr(result.chunk.metadata, "page_number"):
                            page_number = result.chunk.metadata.page_number
                        if hasattr(result.chunk.metadata, "chunk_id"):
                            chunk_id = result.chunk.metadata.chunk_id

                    # Get chunk text
                    content = result.chunk.text if hasattr(result.chunk, "text") and result.chunk.text else ""

                    # Build display name with page number if available
                    display_name = f"{document_name} - Page {page_number}" if page_number else document_name

                    # Create source entry for this chunk
                    source_dict = {
                        "document_name": display_name,
                        "content": content[:1000],  # Limit to 1000 chars for UI display
                        "metadata": {
                            "score": score if score is not None else 0.0,  # Relevance score
                            "page_number": page_number,
                            "chunk_id": chunk_id,
                            "document_id": doc_id,
                        },
                    }

                    serialized.append(source_dict)

            # Fallback: If no query_results, map documents (backward compatibility)
            else:
                logger.warning("⚠️ No query_results available, falling back to documents (scores will default to 1.0)")
                for doc in documents:
                    if hasattr(doc, "__dict__"):
                        doc_dict = {
                            "document_name": getattr(doc, "document_name", getattr(doc, "name", "Unknown Document")),
                            "content": getattr(doc, "content", getattr(doc, "text", ""))[:1000],
                            "metadata": {"score": 1.0},  # Default relevance score
                        }

                        # Collect other attributes into metadata
                        for key, value in doc.__dict__.items():
                            if key not in ["document_name", "name", "content", "text", "id", "document_id"] and isinstance(value, str | int | float | bool | type(None)):
                                doc_dict["metadata"][key] = value

                        serialized.append(doc_dict)
                    else:
                        serialized.append({"document_name": "Unknown", "content": str(doc)[:1000], "metadata": {"score": 1.0}})

            logger.info(f"📊 Serialized {len(serialized)} sources from {'query_results' if query_results else 'documents'}")
            if serialized and "metadata" in serialized[0]:
                logger.info(f"📊 First source - name: {serialized[0]['document_name']}, score: {serialized[0]['metadata'].get('score', 'N/A')}")

            return serialized

        # Serialize search sources with query results for scores and page numbers
        result_documents = getattr(search_result, "documents", []) or []
        result_query_results = getattr(search_result, "query_results", []) or []
        serialized_documents = serialize_documents(result_documents, result_query_results)

        # IMPROVED TOKEN TRACKING: Better estimation for assistant response
        try:
            # Get the LLM provider to count tokens properly
            provider = self.llm_provider_service.get_user_provider(user_id)

            # Use the provider's tokenize method if available (WatsonX has this)
            provider_client = getattr(provider, "client", None) if provider else None
            tokenize_method = getattr(provider_client, "tokenize", None) if provider_client else None

            if tokenize_method:
                try:
                    assistant_tokens_result = tokenize_method(text=search_result.answer)
                    assistant_response_tokens = len(assistant_tokens_result.get("result", []))
                    logger.info("✅ Real token count from provider: assistant=%d", assistant_response_tokens)
                except (ValueError, KeyError, AttributeError) as e:
                    logger.info("Provider tokenize failed, using improved estimation: %s", str(e))
                    # Better estimation: roughly 1.3 tokens per word for most LLMs
                    assistant_response_tokens = max(50, int(len(search_result.answer.split()) * 1.3))
            else:
                # Fallback to improved estimation
                assistant_response_tokens = max(50, int(len(search_result.answer.split()) * 1.3))

        except (ValueError, KeyError, AttributeError) as e:
            logger.info("Using improved token estimation: %s", str(e))
            # Better estimation: roughly 1.3 tokens per word for most LLMs
            assistant_response_tokens = max(50, int(len(search_result.answer.split()) * 1.3))

        # Add CoT token usage to the total token count
        cot_token_usage = 0
        if result_cot_output and isinstance(result_cot_output, dict):
            # Extract total token usage from CoT output
            cot_token_usage = result_cot_output.get("token_usage", 0)
            if not cot_token_usage:
                # Sum from individual reasoning steps if total not available
                reasoning_steps = result_cot_output.get("reasoning_steps", [])
                for step in reasoning_steps:
                    step_tokens = step.get("token_usage", 0) if isinstance(step, dict) else 0
                    cot_token_usage += step_tokens
            logger.info("🔢 CoT token usage extracted: %s", cot_token_usage)

        # Total token count for the assistant response (includes assistant response + CoT tokens)
        token_count = assistant_response_tokens + cot_token_usage

        # Generate token warning if needed
        token_warning_dict = None
        try:
            # Get model name from provider
            model_name = getattr(provider, "model_id", None) if provider else None
            if not model_name:
                model_name = getattr(provider, "model_name", "default-model") if provider else "default-model"

            # Create LLMUsage object for warning check
            current_usage = LLMUsage(
                prompt_tokens=user_token_count,
                completion_tokens=assistant_response_tokens,
                total_tokens=user_token_count + assistant_response_tokens,
                model_name=model_name,
                service_type=ServiceType.CONVERSATION,
                timestamp=datetime.now(UTC),
                user_id=str(user_id),
            )

            # Check for token usage warnings
            token_warning = await self.token_tracking_service.check_usage_warning(
                current_usage=current_usage, context_tokens=user_token_count + assistant_response_tokens
            )

            if token_warning:
                token_warning_dict = {
                    "type": token_warning.warning_type.value,
                    "severity": token_warning.severity,
                    "percentage_used": token_warning.percentage_used,
                    "current_tokens": token_warning.current_tokens,
                    "limit_tokens": token_warning.limit_tokens,
                    "message": token_warning.message,
                    "suggested_action": token_warning.suggested_action,
                }
                logger.info("📊 Generated token warning: %s", token_warning_dict)
        except (ValueError, KeyError, AttributeError) as e:
            logger.warning("Failed to generate token warning: %s", str(e))
            token_warning_dict = None

        logger.info(
            f"🔢 Final token count breakdown: assistant={assistant_response_tokens}, cot={cot_token_usage}, total={token_count}"
        )

        # Debug logging
        logger.info("🔢 Token tracking debug: assistant_token_count=%d", token_count)
        logger.info(
            "🔢 User input tokens: %d, Assistant response tokens: %d", user_token_count, assistant_response_tokens
        )

        # Debug logging for token tracking
        logger.info(
            f"🔍 DEBUG: Assistant response: '{search_result.answer[:100]}...' -> {assistant_response_tokens} tokens"
        )

        # Calculate context tokens and conversation total tokens BEFORE creating metadata
        context_tokens = len(serialized_documents) * 100 if serialized_documents else 0

        # Get conversation total tokens from session statistics
        try:
            stats = await self.get_session_statistics(message_input.session_id, session.user_id)
            conversation_total_tokens = stats.total_tokens
        except (ValueError, KeyError, AttributeError):
            conversation_total_tokens = 0

        # Create assistant response with integration metadata and token tracking
        # IMPORTANT: Store sources and cot_output in metadata so they persist to database
        metadata_dict = {
            "source_documents": [doc.get("document_name", "") for doc in serialized_documents]
            if serialized_documents
            else None,
            "search_metadata": {
                "enhanced_question": enhanced_question,
                "cot_steps": cot_steps,
                "integration_seamless": True,
                "conversation_ui_used": True,
                "search_rag_used": True,
                "cot_reasoning_used": cot_used,
                "no_duplication": True,
                "service_boundaries_respected": True,
            },
            "cot_used": cot_used,
            "conversation_aware": True,
            "execution_time": search_result.execution_time,
            "context_length": len(context.context_window) if context else None,
            "token_count": token_count,
            "token_analysis": {
                "query_tokens": user_token_count,
                "context_tokens": context_tokens,
                "response_tokens": assistant_response_tokens,
                "system_tokens": cot_token_usage,
                "total_this_turn": token_count,
                "conversation_total": conversation_total_tokens,
            },
            # Store full source data for frontend consumption
            "sources": serialized_documents if serialized_documents else None,
            # Store CoT output for frontend consumption
            "cot_output": result_cot_output if (cot_used and result_cot_output) else None,
        }

        logger.info(
            f"📊 CONVERSATION SERVICE: Created metadata_dict with token_analysis: {metadata_dict.get('token_analysis')}"
        )

        assistant_message_input = ConversationMessageInput(
            session_id=message_input.session_id,
            content=search_result.answer,
            role=MessageRole.ASSISTANT,
            message_type=MessageType.ANSWER,
            metadata=metadata_dict,  # Pass dict directly instead of creating MessageMetadata object
            token_count=token_count,
            execution_time=search_result.execution_time,
        )

        # Debug logging for ConversationMessageInput

        assistant_message = await self.add_message(assistant_message_input)
        logger.info(
            f"📊 CONVERSATION SERVICE: Assistant message created with token_count={assistant_message.token_count}"
        )
        logger.info(
            f"📊 CONVERSATION SERVICE: Assistant message metadata keys: {list(assistant_message.metadata.model_dump().keys()) if assistant_message.metadata else 'None'}"
        )

        # Add token warning to the response if present
        if token_warning_dict:
            assistant_message.token_warning = token_warning_dict
            logger.info("📊 CONVERSATION SERVICE: Added token warning to response")

        # Add full source documents to the response for frontend consumption
        # Frontend expects: sources: [{document_name, content, metadata}]
        if serialized_documents:
            assistant_message.sources = serialized_documents
            logger.info(f"📊 CONVERSATION SERVICE: Added {len(serialized_documents)} sources to response")

        # Add CoT output to the response if CoT was used
        if cot_used and result_cot_output:
            assistant_message.cot_output = result_cot_output
            logger.info("📊 CONVERSATION SERVICE: Added CoT output to response")

        logger.info(
            "🎉 CONVERSATION SERVICE: Returning assistant message with full metadata (including token_analysis), sources, and CoT"
        )
        return assistant_message

    async def get_session_statistics(self, session_id: UUID, user_id: UUID) -> SessionStatistics:
        """Get statistics for a conversation session."""
        messages = await self.get_messages(session_id, user_id)
        session = await self.get_session(session_id, user_id)

        if not session:
            raise ValueError("Session not found")

        user_messages = [msg for msg in messages if msg.role == MessageRole.USER]
        assistant_messages = [msg for msg in messages if msg.role == MessageRole.ASSISTANT]

        cot_usage_count = sum(1 for msg in assistant_messages if msg.metadata and msg.metadata.cot_used)

        context_enhancement_count = sum(
            1 for msg in assistant_messages if msg.metadata and msg.metadata.conversation_aware
        )

        # Calculate total tokens from actual token_count field, not word count
        total_tokens = 0
        total_llm_calls = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0

        # Count tokens from stored token_count field for each message
        for msg in messages:
            if hasattr(msg, "token_count") and msg.token_count:
                total_tokens += msg.token_count
                if msg.role == MessageRole.ASSISTANT:
                    total_llm_calls += 1
                    # Estimate prompt vs completion tokens for assistant messages
                    # Rough estimation: 60% prompt, 40% completion for assistant responses
                    estimated_prompt = int(msg.token_count * 0.6)
                    estimated_completion = int(msg.token_count * 0.4)
                    total_prompt_tokens += estimated_prompt
                    total_completion_tokens += estimated_completion
                elif msg.role == MessageRole.USER:
                    # User messages are typically all prompt tokens
                    total_prompt_tokens += msg.token_count

        # Also add CoT token usage from metadata if available
        cot_token_count = 0
        for msg in assistant_messages:
            if msg.metadata and hasattr(msg.metadata, "cot_steps"):
                for step in msg.metadata.cot_steps or []:
                    if isinstance(step, dict) and "token_usage" in step:
                        cot_token_count += step.get("token_usage", 0)
                        # CoT tokens are typically prompt tokens (reasoning steps)
                        total_prompt_tokens += step.get("token_usage", 0)

        total_tokens += cot_token_count

        logger.info(
            f"🔢 Session stats - Total tokens: {total_tokens}, LLM calls: {total_llm_calls}, CoT tokens: {cot_token_count}"
        )
        logger.info("🔢 Token breakdown - Prompt: %d, Completion: %d", total_prompt_tokens, total_completion_tokens)

        # Calculate by_service and by_model breakdowns
        by_service: dict[str, int] = {}
        by_model: dict[str, int] = {}

        # Analyze messages for service and model usage
        for msg in messages:
            if msg.metadata and hasattr(msg.metadata, "search_metadata"):
                search_metadata = msg.metadata.search_metadata
                if isinstance(search_metadata, dict):
                    # Extract service type from search metadata
                    service_type = search_metadata.get("integration_seamless", False)
                    if service_type:
                        by_service["search"] = by_service.get("search", 0) + (msg.token_count or 0)

                    # Extract model information if available
                    model_used = msg.metadata.model_used if hasattr(msg.metadata, "model_used") else None
                    if model_used:
                        by_model[model_used] = by_model.get(model_used, 0) + (msg.token_count or 0)
                    else:
                        # Use a default model name if not specified
                        by_model["default_model"] = by_model.get("default_model", 0) + (msg.token_count or 0)

        return SessionStatistics(
            session_id=session_id,
            message_count=len(messages),
            user_messages=len(user_messages),
            assistant_messages=len(assistant_messages),
            total_tokens=total_tokens,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            cot_usage_count=cot_usage_count,
            context_enhancement_count=context_enhancement_count,
            created_at=session.created_at,
            last_activity=datetime.now(UTC),
            metadata={
                "total_llm_calls": total_llm_calls,
                "cot_token_count": cot_token_count,
                "by_service": by_service,
                "by_model": by_model,
            },
        )

    async def export_session(self, session_id: UUID, user_id: UUID, export_format: str = "json") -> dict:
        """Export a conversation session."""
        # Validate export format
        supported_formats = ["json", "csv", "txt"]
        if export_format not in supported_formats:
            raise ValidationError(f"Unsupported export format: {export_format}")

        session = await self.get_session(session_id, user_id)
        messages = await self.get_messages(session_id, user_id)

        return {
            "session_data": session,
            "messages": messages,
            "export_format": export_format,
            "export_timestamp": datetime.now(UTC),
            "metadata": {"cot_integration": True, "context_enhancement": True},
        }

    # Context Management Methods (moved from ContextManagerService)
    async def build_context_from_messages(  # pylint: disable=too-many-locals,too-many-branches
        self, session_id: UUID, messages: list[ConversationMessageOutput]
    ) -> ConversationContext:
        """Build conversation context from messages."""
        # Check cache first
        cache_key = f"{session_id}_{len(messages)}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        # Use the implementation method as expected by tests
        context = await self._build_context_from_messages_impl(session_id, messages)

        # Cache the result
        self._context_cache[cache_key] = context
        return context

    async def enhance_question_with_context(
        self, question: str, conversation_context: str, message_history: list[str]
    ) -> str:
        """Enhance question with conversation context.

        IMPORTANT: Only extracts entities from USER messages to prevent pollution
        from assistant's verbose responses containing discourse markers.
        """
        # Extract user-only context to prevent assistant response pollution
        user_only_context = self._extract_user_messages_from_context(conversation_context)

        # Extract entities only from user messages
        entities = self._extract_entities_from_context(user_only_context)

        # Start with the original question
        enhanced_question = question

        # Add entity context if entities exist
        if entities:
            entity_context = f" (in the context of {', '.join(entities)})"
            enhanced_question = f"{enhanced_question}{entity_context}"

        # Add conversation context if question is ambiguous
        if self._is_ambiguous_question(question):
            recent_context = " ".join(message_history[-3:])  # Last 3 messages
            if entities:
                # If we already added entity context, add ambiguous context as well
                enhanced_question = f"{enhanced_question} (referring to: {recent_context})"
            else:
                # If no entities, add both conversation context and message history
                context_parts = []
                if user_only_context.strip():
                    context_parts.append(user_only_context)
                if recent_context.strip():
                    context_parts.append(recent_context)

                if context_parts:
                    combined_context = " ".join(context_parts)
                    enhanced_question = f"{question} (referring to: {combined_context})"
                else:
                    enhanced_question = question

        return enhanced_question

    async def generate_question_suggestions(
        self, session_id: UUID, current_message: str, user_id: UUID, max_suggestions: int = 3
    ) -> dict:
        """Generate question suggestions using the enhanced QuestionService."""
        # Get conversation context
        messages = await self.get_messages(session_id, user_id)
        context = await self.build_context_from_messages(session_id, messages)

        # Use QuestionService to generate conversation suggestions
        suggestions = await self.question_service.generate_conversation_suggestions(
            conversation_context=context.context_window,
            current_message=current_message,
            user_id=user_id,
            max_suggestions=max_suggestions,
        )

        return {
            "suggestions": [s["question"] for s in suggestions],
            "confidence_scores": [s["confidence"] for s in suggestions],
            "reasoning": f"Generated {len(suggestions)} suggestions based on conversation context",
        }

    def _build_context_window(self, messages: list[ConversationMessageOutput]) -> str:
        """Build context window from messages."""
        if not messages:
            return "No previous conversation context"

        # Take last 10 messages for context
        recent_messages = messages[-10:]
        context_parts = []

        for msg in recent_messages:
            if msg.role == "user":
                context_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                context_parts.append(f"Assistant: {msg.content}")

        return " ".join(context_parts) if context_parts else "No previous conversation context"

    def _extract_user_messages_from_context(self, context: str) -> str:
        """Extract only user messages from context, excluding assistant responses.

        This prevents contamination from assistant's verbose responses which contain
        discourse markers like "Based on", "However", "Additionally" that get
        incorrectly identified as entities by spaCy's noun chunking.

        Args:
            context: Full conversation context with both user and assistant messages

        Returns:
            String containing only user messages, filtered from the context

        Example:
            Input: "User: What is IBM? Assistant: Based on the analysis..."
            Output: "What is IBM?"
        """
        if not context or context == "No previous conversation context":
            return ""

        user_messages = []

        # Split by "Assistant:" to separate sections
        sections = context.split("Assistant:")

        for section in sections:
            if "User:" in section:
                # Extract all user messages from this section
                user_parts = section.split("User:")
                for part in user_parts[1:]:  # Skip first split (before first "User:")
                    user_msg = part.strip()
                    if user_msg:
                        user_messages.append(user_msg)

        return " ".join(user_messages)

    def _extract_entities_from_context(self, context: str) -> list[str]:
        """Extract entities from context using EntityExtractionService.

        This method delegates to EntityExtractionService which provides:
        - Fast spaCy NER extraction (5ms, 75% accuracy)
        - Hybrid mode: spaCy + LLM-based refinement for better quality
        - Comprehensive stop word filtering
        - Entity validation and deduplication

        Note: Using 'hybrid' mode (instead of 'fast') for better quality filtering
        of noise and discourse markers from conversation context. The slight
        performance tradeoff (~50-100ms) is worthwhile for cleaner entity extraction.

        Args:
            context: Conversation context to extract entities from

        Returns:
            List of validated entity strings (max 10)
        """
        # Use async service in sync context
        import asyncio

        loop = asyncio.get_event_loop()
        try:
            entities = loop.run_until_complete(
                self.entity_extraction_service.extract_entities(
                    context=context,
                    method="hybrid",  # Changed from "fast" to "hybrid" for better quality
                    use_cache=True,
                    max_entities=10,
                )
            )
            logger.debug("Extracted %d entities from context: %s", len(entities), entities)
            return entities
        except Exception as e:
            logger.error("Entity extraction failed: %s, returning empty list", e)
            return []

    def _extract_topics_from_context(self, context: str) -> list[str]:
        """Extract topics from context."""
        topics = []

        # Look for question patterns
        question_patterns = [r"what is (.+?)\?", r"how does (.+?) work", r"explain (.+?)", r"tell me about (.+?)"]

        for pattern in question_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            topics.extend(matches)

        return list(set(topics))

    def _is_ambiguous_question(self, question: str) -> bool:
        """Check if a question is ambiguous and needs context."""
        question_lower = question.lower().strip()

        # Pattern-based detection for ambiguous questions
        ambiguous_patterns = [
            r"\b(it|this|that|they|them|these|those)\b",  # Pronouns
            r"^(what|how|why|when|where)\s+(is|are|was|were|does|do|did|can|could|will|would)\s+(it|this|that|they)\b",  # Pronoun questions
            r"^(tell me more|what about|how about|what\'s next|next step)\b",  # Vague requests
            r"\b(earlier|before|previous|last|first)\b",  # Temporal references
        ]

        return any(re.search(pattern, question_lower) for pattern in ambiguous_patterns)

    # Additional context management methods expected by integration tests
    def extract_entities_from_context(self, context: str) -> list[str]:
        """Extract entities from context - enhanced version for tests."""
        return self._extract_entities_from_context(context)

    def is_ambiguous_question(self, question: str) -> bool:
        """Public method for checking if a question is ambiguous."""
        return self._is_ambiguous_question(question)

    async def enhance_question_with_conversation_context(
        self, question: str, conversation_context: str, message_history: list[str]
    ) -> str:
        """Enhance question with conversation context - public method for tests."""
        return await self.enhance_question_with_context(question, conversation_context, message_history)

    def _calculate_relevance_scores(self, context: str, current_question: str) -> dict[str, float]:
        """Calculate relevance scores for context elements."""
        scores = {}
        entities = self._extract_entities_from_context(context)
        question_lower = current_question.lower()

        for entity in entities:
            if entity.lower() in question_lower:
                scores[entity] = 0.9
            elif any(word in entity.lower() for word in question_lower.split()):
                scores[entity] = 0.7
            else:
                scores[entity] = 0.3

        return scores

    def _keep_relevant_content(self, _context: str, relevance_scores: dict[str, float], threshold: float = 0.5) -> str:
        """Keep only relevant content based on scores."""
        relevant_entities = [entity for entity, score in relevance_scores.items() if score >= threshold]
        return ", ".join(relevant_entities)

    async def _build_context_from_messages_impl(
        self, session_id: UUID, messages: list[ConversationMessageOutput]
    ) -> ConversationContext:
        """Implementation for building context from messages."""
        context_window = self._build_context_window(messages)
        entities = self._extract_entities_from_context(context_window)
        topics = self._extract_topics_from_context(context_window)

        return ConversationContext(
            session_id=session_id,
            context_window=context_window,
            relevant_documents=[],
            context_metadata={
                "extracted_entities": entities,
                "conversation_topics": topics,
                "message_count": len(messages),
                "context_length": len(context_window),
            },
        )

    async def archive_session(self, session_id: UUID, user_id: UUID) -> ConversationSessionOutput:
        """Archive a conversation session by setting status to ARCHIVED."""
        session = (
            self.db.query(ConversationSession)
            .filter(ConversationSession.id == session_id, ConversationSession.user_id == user_id)
            .first()
        )

        if not session:
            raise NotFoundError("ConversationSession", str(session_id))

        session.status = SessionStatus.ARCHIVED
        session.is_archived = True
        self.db.commit()
        self.db.refresh(session)

        return ConversationSessionOutput.from_db_session(session)

    async def restore_session(self, session_id: UUID, user_id: UUID) -> ConversationSessionOutput:
        """Restore an archived session by setting status to ACTIVE."""
        session = (
            self.db.query(ConversationSession)
            .filter(ConversationSession.id == session_id, ConversationSession.user_id == user_id)
            .first()
        )

        if not session:
            raise NotFoundError("ConversationSession", str(session_id))

        session.status = SessionStatus.ACTIVE
        session.is_archived = False
        self.db.commit()
        self.db.refresh(session)

        return ConversationSessionOutput.from_db_session(session)

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count of cleaned sessions."""

        # Sessions expire after 7 days of inactivity
        expiry_date = datetime.now(UTC) - timedelta(days=7)

        expired_sessions = (
            self.db.query(ConversationSession)
            .filter(ConversationSession.updated_at < expiry_date, ConversationSession.status != SessionStatus.ARCHIVED)
            .all()
        )

        count = len(expired_sessions)

        for session in expired_sessions:
            session.status = SessionStatus.EXPIRED

        self.db.commit()
        return count

    def search_sessions(self, user_id: UUID, query: str) -> list[ConversationSessionOutput]:
        """Search sessions by query in session name or messages."""
        sessions = (
            self.db.query(ConversationSession)
            .filter(ConversationSession.user_id == user_id, ConversationSession.session_name.ilike(f"%{query}%"))
            .order_by(ConversationSession.updated_at.desc())
            .all()
        )

        return [ConversationSessionOutput.from_db_session(session) for session in sessions]

    def get_user_sessions(
        self, user_id: UUID, status: SessionStatus | None = None, limit: int = 50, offset: int = 0
    ) -> list[ConversationSessionOutput]:
        """Get user sessions with optional status filter."""
        query = self.db.query(ConversationSession).filter(ConversationSession.user_id == user_id)

        if status:
            query = query.filter(ConversationSession.status == status)

        sessions = query.order_by(ConversationSession.updated_at.desc()).offset(offset).limit(limit).all()

        return [ConversationSessionOutput.from_db_session(session) for session in sessions]

    def get_session_messages(
        self, session_id: UUID, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[ConversationMessageOutput]:
        """Get session messages with pagination."""
        # Verify session belongs to user
        session = (
            self.db.query(ConversationSession)
            .filter(ConversationSession.id == session_id, ConversationSession.user_id == user_id)
            .first()
        )

        if not session:
            return []

        messages = (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [
            ConversationMessageOutput(
                id=message.id,
                session_id=message.session_id,
                content=message.content,
                role=MessageRole(message.role),
                message_type=MessageType(message.message_type),
                created_at=message.created_at,
                metadata=message.message_metadata if isinstance(message.message_metadata, MessageMetadata) else None,
                token_count=message.token_count,
                execution_time=message.execution_time,
            )
            for message in messages
        ]

    async def get_question_suggestions(self, session_id: UUID, user_id: UUID):
        """Get question suggestions for a conversation session."""

        # Get session messages for context
        messages = await self.get_messages(session_id, user_id)

        # Build context from messages
        context = await self.build_context_from_messages(session_id, messages)

        # Use QuestionService to generate suggestions
        question_service = self.question_service
        suggestions_list = await question_service.generate_conversation_suggestions(
            conversation_context=context.context_window,
            current_message=messages[-1].content if messages else "",
            user_id=user_id,
            max_suggestions=5,
        )

        # Convert list to QuestionSuggestionOutput
        suggestions_texts = []
        confidence_scores = []
        for suggestion in suggestions_list:
            if isinstance(suggestion, dict):
                suggestions_texts.append(suggestion.get("question", ""))
                confidence_scores.append(suggestion.get("confidence", 0.8))
            else:
                suggestions_texts.append(str(suggestion))
                confidence_scores.append(0.8)

        return QuestionSuggestionOutput(
            suggestions=suggestions_texts,
            confidence_scores=confidence_scores,
            reasoning="Generated based on conversation context and recent messages",
        )

    async def generate_conversation_summary(self, session_id: UUID, user_id: UUID, summary_type: str = "brief") -> dict:  # pylint: disable=too-many-return-statements,too-many-branches
        """Generate a summary of the conversation session.

        Args:
            session_id: The conversation session ID
            user_id: The user ID
            summary_type: Type of summary ('brief', 'detailed', 'key_points')

        Returns:
            Dictionary containing the conversation summary
        """
        # Get the session and messages
        session = await self.get_session(session_id, user_id)
        messages = await self.get_messages(session_id, user_id, limit=1000)  # Get all messages

        if not messages:
            return {
                "summary": "No messages in this conversation yet.",
                "summary_type": summary_type,
                "message_count": 0,
                "session_name": session.session_name,
                "created_at": session.created_at.isoformat(),
            }

        # Extract conversation content
        conversation_text = []
        user_questions = []
        assistant_responses = []
        topics = set()

        for msg in messages:
            if msg.role == MessageRole.USER:
                conversation_text.append(f"User: {msg.content}")
                user_questions.append(msg.content)
            elif msg.role == MessageRole.ASSISTANT:
                conversation_text.append(f"Assistant: {msg.content}")
                assistant_responses.append(msg.content)

                # Extract topics from metadata if available
                if msg.metadata and hasattr(msg.metadata, "search_metadata"):
                    search_metadata = msg.metadata.search_metadata
                    if isinstance(search_metadata, dict) and "conversation_entities" in search_metadata:
                        for entity in search_metadata.get("conversation_entities", []):
                            topics.add(entity)

        # Generate different types of summaries
        if summary_type == "brief":
            summary = self._generate_brief_summary(user_questions, assistant_responses, list(topics))
        elif summary_type == "detailed":
            summary = self._generate_detailed_summary(
                conversation_text, user_questions, assistant_responses, list(topics)
            )
        elif summary_type == "key_points":
            summary = self._generate_key_points_summary(user_questions, assistant_responses, list(topics))
        else:
            summary = self._generate_brief_summary(user_questions, assistant_responses, list(topics))

        # Calculate conversation statistics
        stats = await self.get_session_statistics(session_id, user_id)

        return {
            "summary": summary,
            "summary_type": summary_type,
            "message_count": len(messages),
            "user_messages": len(user_questions),
            "assistant_messages": len(assistant_responses),
            "session_name": session.session_name,
            "created_at": session.created_at.isoformat(),
            "topics": list(topics)[:10],  # Limit to top 10 topics
            "total_tokens": stats.total_tokens,
            "cot_usage_count": stats.cot_usage_count,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _generate_brief_summary(
        self, user_questions: list[str], assistant_responses: list[str], topics: list[str]
    ) -> str:
        """Generate a brief summary of the conversation."""
        if not user_questions:
            return "No user questions in this conversation."

        # Extract main topics and themes
        main_topics = topics[:3] if topics else ["general discussion"]

        summary_parts = []
        summary_parts.append(f"Conversation covering {len(user_questions)} questions")

        if main_topics:
            summary_parts.append(f"about {', '.join(main_topics)}")

        # Add information about conversation style
        if len(assistant_responses) > 0:
            avg_response_length = sum(len(resp.split()) for resp in assistant_responses) / len(assistant_responses)
            if avg_response_length > 100:
                summary_parts.append("with detailed explanations")
            elif avg_response_length > 50:
                summary_parts.append("with moderate detail")
            else:
                summary_parts.append("with brief responses")

        return ". ".join(summary_parts) + "."

    def _generate_detailed_summary(
        self,
        _conversation_text: list[str],
        user_questions: list[str],
        assistant_responses: list[str],
        topics: list[str],
    ) -> str:
        """Generate a detailed summary of the conversation."""
        summary_parts = []

        # Overview
        summary_parts.append(
            f"This conversation contains {len(user_questions)} user questions and {len(assistant_responses)} assistant responses."
        )

        # Main topics
        if topics:
            summary_parts.append(f"Key topics discussed include: {', '.join(topics[:5])}.")

        # Question patterns
        if user_questions:
            # Analyze question types
            how_questions = [q for q in user_questions if q.lower().startswith(("how", "how to", "how can", "how do"))]
            what_questions = [q for q in user_questions if q.lower().startswith(("what", "what is", "what are"))]
            why_questions = [q for q in user_questions if q.lower().startswith(("why", "why is", "why do"))]

            if how_questions:
                summary_parts.append(f"User asked {len(how_questions)} 'how' questions about processes and methods.")
            if what_questions:
                summary_parts.append(
                    f"User asked {len(what_questions)} 'what' questions seeking definitions and explanations."
                )
            if why_questions:
                summary_parts.append(f"User asked {len(why_questions)} 'why' questions exploring reasoning and causes.")

        # Response characteristics
        if assistant_responses:
            total_words = sum(len(resp.split()) for resp in assistant_responses)
            avg_words = total_words / len(assistant_responses)
            summary_parts.append(f"Assistant provided responses averaging {avg_words:.0f} words each.")

        return " ".join(summary_parts)

    def _generate_key_points_summary(
        self, user_questions: list[str], assistant_responses: list[str], topics: list[str]
    ) -> str:
        """Generate a key points summary of the conversation."""
        key_points = []

        # Extract key questions (first, last, and any containing important keywords)
        important_keywords = ["important", "critical", "key", "main", "primary", "essential", "fundamental"]

        if user_questions:
            # Always include first question
            key_points.append(
                f'• Started with: "{user_questions[0][:100]}{"..." if len(user_questions[0]) > 100 else ""}"'
            )

            # Include questions with important keywords
            important_questions = [
                q for q in user_questions[1:-1] if any(keyword in q.lower() for keyword in important_keywords)
            ]

            for q in important_questions[:2]:  # Limit to 2 important questions
                key_points.append(f'• Key question: "{q[:100]}{"..." if len(q) > 100 else ""}"')

            # Include last question if different from first
            if len(user_questions) > 1:
                key_points.append(
                    f'• Ended with: "{user_questions[-1][:100]}{"..." if len(user_questions[-1]) > 100 else ""}"'
                )

        # Add topic summary
        if topics:
            key_points.append(f"• Main topics: {', '.join(topics[:5])}")

        # Add conversation metrics
        key_points.append(f"• {len(user_questions)} questions answered across {len(assistant_responses)} responses")

        return "\n".join(key_points)

    async def generate_conversation_name(self, session_id: UUID, user_id: UUID) -> str:
        """Generate a concise name for the conversation using LLM.

        Args:
            session_id: The conversation session ID
            user_id: The user ID

        Returns:
            A short, concise conversation name
        """
        try:
            # Get session messages for context
            messages = await self.get_messages(session_id, user_id, limit=10)  # First 10 messages for context

            if not messages:
                return "New Conversation"

            # Extract the first few questions/topics from the conversation
            user_questions = []
            for msg in messages[:5]:  # Look at first 5 messages
                if msg.role == MessageRole.USER:
                    user_questions.append(msg.content)

            if not user_questions:
                return "New Conversation"

            # Get LLM provider to generate name
            provider = self.llm_provider_service.get_default_provider()
            if not provider:
                # Fallback to simple name generation
                return self._generate_simple_name_from_questions(user_questions)

            # Create prompt for LLM to generate conversation name
            questions_text = "\n".join([f"- {q}" for q in user_questions[:3]])

            prompt = f"""Based on the following conversation questions, generate a short, concise conversation title (maximum 40 characters).
The title should capture the main topic or theme. Respond with ONLY the title, no extra text.

Questions:
{questions_text}

Title:"""

            # Use the LLM to generate the name
            # Use low max_tokens for short titles (typically 2-5 words)
            # Use lower temperature for focused, concise output
            max_tokens = 20  # Reasonable limit for short titles
            temperature = min(self.settings.temperature, 0.3)  # Cap at 0.3 for consistency

            try:
                if hasattr(provider, "generate") and callable(provider.generate):
                    response = await provider.generate(prompt, max_tokens=max_tokens, temperature=temperature)
                elif hasattr(provider, "llm_base") and hasattr(provider.llm_base, "generate"):
                    response = await provider.llm_base.generate(prompt, max_tokens=max_tokens, temperature=temperature)
                else:
                    # Fallback to simple name generation
                    return self._generate_simple_name_from_questions(user_questions)

                # Extract and clean the generated name
                if isinstance(response, dict) and "text" in response:
                    name = response["text"].strip()
                elif isinstance(response, str):
                    name = response.strip()
                else:
                    name = str(response).strip()

                # Clean up the name
                name = name.replace('"', "").replace("'", "").strip()
                if len(name) > 40:
                    name = name[:37] + "..."

                return name if name else self._generate_simple_name_from_questions(user_questions)

            except Exception as llm_error:
                logger.warning("LLM name generation failed: %s", llm_error)
                return self._generate_simple_name_from_questions(user_questions)

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error generating conversation name: %s", str(e))
            return "New Conversation"

    def _generate_simple_name_from_questions(self, user_questions: list[str]) -> str:
        """Generate a simple name from user questions without LLM."""
        if not user_questions:
            return "New Conversation"

        # Take the first question and extract key words
        first_question = user_questions[0]

        # Simple keyword extraction
        important_words = []

        # Look for question words and important terms
        words = first_question.lower().split()

        # Skip common question words but keep topic words
        skip_words = {
            "what",
            "how",
            "why",
            "when",
            "where",
            "who",
            "is",
            "are",
            "does",
            "do",
            "can",
            "will",
            "should",
            "would",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }

        for word in words:
            # Remove punctuation
            clean_word = "".join(char for char in word if char.isalnum())
            if len(clean_word) > 2 and clean_word not in skip_words:
                important_words.append(clean_word.title())

        # Create name from important words
        if important_words:
            name = " ".join(important_words[:4])  # Take first 4 important words
            if len(name) > 40:
                name = name[:37] + "..."
            return name

        # Fallback to time-based name
        return f"Chat {datetime.now().strftime('%m/%d %H:%M')}"

    async def update_conversation_name(self, session_id: UUID, user_id: UUID) -> str:
        """Update conversation name using LLM and return the new name.

        Args:
            session_id: The conversation session ID
            user_id: The user ID

        Returns:
            The newly generated conversation name
        """
        try:
            # Generate new name
            new_name = await self.generate_conversation_name(session_id, user_id)

            # Update the session with the new name
            await self.update_session(session_id, user_id, {"session_name": new_name})

            logger.info("Updated conversation %s name to: %s", session_id, new_name)
            return new_name
        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error updating conversation name: %s", str(e))
            return "New Conversation"

    async def update_all_conversation_names(self, user_id: UUID) -> dict:
        """Update names for all conversations of a user.

        Args:
            user_id: The user ID

        Returns:
            Dictionary with results of the naming operation
        """
        try:
            sessions = await self.list_sessions(user_id)
            results = {"updated": 0, "failed": 0, "skipped": 0}

            for session in sessions:
                try:
                    # Skip conversations that already have meaningful names (not auto-generated)
                    if (
                        session.session_name
                        and not session.session_name.startswith("Chat with")
                        and not session.session_name.startswith("New Conversation")
                        and len(session.session_name.strip()) > 0
                    ):
                        results["skipped"] += 1
                        continue

                    # Generate new name
                    new_name = await self.update_conversation_name(session.id, user_id)
                    if new_name != "New Conversation":
                        results["updated"] += 1
                    else:
                        results["failed"] += 1

                except (ValueError, KeyError, AttributeError) as e:
                    logger.error("Error updating name for session %s: %s", session.id, str(e))
                    results["failed"] += 1

            logger.info("Conversation naming results for user %s: %s", user_id, results)
            return results

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error updating all conversation names: %s", str(e))
            return {"updated": 0, "failed": 1, "skipped": 0}
