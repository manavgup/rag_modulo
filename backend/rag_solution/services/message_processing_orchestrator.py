"""Message Processing Orchestrator for conversation message handling.

This service orchestrates the complete user message processing workflow,
integrating search, Chain of Thought reasoning, token tracking, and context
enhancement. Extracted from ConversationService to follow the Facade pattern
and improve separation of concerns.

Architecture:
- Facade Pattern: Simplifies complex subsystem interactions
- Strategy Pattern: Configurable CoT detection and enhancement
- Template Method: Define workflow skeleton, allow customization
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.core.exceptions import SessionExpiredError, ValidationError
from rag_solution.models.conversation_session import ConversationSession
from rag_solution.repository.conversation_repository import ConversationRepository
from rag_solution.schemas.conversation_schema import (
    ConversationContext,
    ConversationMessageInput,
    ConversationMessageOutput,
    MessageRole,
    MessageType,
    SessionStatus,
)
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.services.conversation_context_service import ConversationContextService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.search_service import SearchService
from rag_solution.services.token_tracking_service import TokenTrackingService

logger = logging.getLogger(__name__)


class MessageProcessingOrchestrator:
    """Orchestrates user message processing with search, CoT, and context integration.

    This service extracts the complex message processing workflow from ConversationService,
    providing a clean facade for multi-service coordination.

    Workflow Steps:
    1. Validate session and store user message
    2. Build conversation context
    3. Enhance question with context
    4. Execute search (automatic CoT detection)
    5. Track token usage
    6. Generate token warnings
    7. Serialize response with sources and CoT output
    8. Store assistant message

    Example:
        ```python
        orchestrator = MessageProcessingOrchestrator(
            db=db_session,
            settings=settings,
            conversation_repository=repository,
            search_service=search_service,
            context_service=context_service,
            token_tracking_service=token_service,
            llm_provider_service=llm_service,
            chain_of_thought_service=cot_service,
        )

        message_input = ConversationMessageInput(
            session_id=session_id,
            content="What is machine learning?",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
        )

        response = await orchestrator.process_user_message(message_input)
        # Returns ConversationMessageOutput with full metadata
        ```
    """

    def __init__(
        self,
        db: Session,
        settings: Settings,
        conversation_repository: ConversationRepository,
        search_service: SearchService,
        context_service: ConversationContextService,
        token_tracking_service: TokenTrackingService,
        llm_provider_service: LLMProviderService,
        chain_of_thought_service: ChainOfThoughtService | None = None,
    ):
        """Initialize MessageProcessingOrchestrator with all required services.

        Args:
            db: Database session for transactions
            settings: Application settings
            conversation_repository: Unified repository for conversation data access
            search_service: Service for executing RAG search
            context_service: Service for building and enhancing conversation context
            token_tracking_service: Service for tracking LLM token usage
            llm_provider_service: Service for managing LLM providers
            chain_of_thought_service: Optional service for CoT reasoning
        """
        self.db = db
        self.settings = settings
        self.repository = conversation_repository
        self.search_service = search_service
        self.context_service = context_service
        self.token_tracking_service = token_tracking_service
        self.llm_provider_service = llm_provider_service
        self.cot_service = chain_of_thought_service

    async def process_user_message(
        self, message_input: ConversationMessageInput
    ) -> ConversationMessageOutput:  # pylint: disable=too-many-locals,too-many-statements
        """Process user message end-to-end with search, CoT, and context integration.

        This is the main orchestration method that coordinates all services to process
        a user message and generate an assistant response. It handles the complete
        workflow from message storage through search execution to response generation.

        Workflow:
        1. **Session Validation**: Validate session exists and is active
        2. **User Message Storage**: Store user message with token count
        3. **Context Building**: Build conversation context from message history
        4. **Question Enhancement**: Enhance question with conversation entities
        5. **Search Execution**: Execute RAG search with automatic CoT detection
        6. **Token Tracking**: Track token usage across user input and assistant response
        7. **Token Warnings**: Generate warnings if approaching token limits
        8. **Response Serialization**: Serialize search results with sources and CoT steps
        9. **Assistant Message Storage**: Store assistant response with full metadata

        Args:
            message_input: User message to process containing session_id, content, role

        Returns:
            ConversationMessageOutput: Assistant response with full metadata including:
                - answer: Generated response text
                - sources: List of source documents with scores and page numbers
                - cot_output: Chain of Thought reasoning steps (if used)
                - token_analysis: Token usage breakdown
                - token_warning: Warning if approaching limits

        Raises:
            ValueError: If session not found or invalid
            ValidationError: If session lacks required fields (collection_id, user_id)
            SessionExpiredError: If session is expired

        Example:
            ```python
            message_input = ConversationMessageInput(
                session_id=UUID("..."),
                content="What is IBM Watson?",
                role=MessageRole.USER,
                message_type=MessageType.QUESTION,
            )

            response = await orchestrator.process_user_message(message_input)

            print(f"Answer: {response.content}")
            print(f"Sources: {len(response.sources)}")
            print(f"CoT Used: {response.metadata.cot_used if response.metadata else False}")
            print(f"Total Tokens: {response.token_count}")
            ```

        Notes:
            - Automatically detects when to use Chain of Thought reasoning
            - Handles token counting for both user messages and assistant responses
            - Serializes complex DocumentMetadata objects for frontend consumption
            - Integrates conversation context for better question understanding
        """
        logger.info(
            f"🚀 MESSAGE ORCHESTRATOR: process_user_message() called with session_id={message_input.session_id}"
        )
        logger.info("📝 MESSAGE ORCHESTRATOR: message content: %s...", message_input.content[:100])

        # Step 1: Get the session to get user_id and validate access
        session = self.db.query(ConversationSession).filter(ConversationSession.id == message_input.session_id).first()
        if not session:
            raise ValueError("Session not found")

        if session.status == SessionStatus.EXPIRED:
            raise SessionExpiredError("Session has expired")

        logger.info(
            f"📊 MESSAGE ORCHESTRATOR: Found session - user_id={session.user_id}, collection_id={session.collection_id}"
        )

        # Step 2: Calculate token count for user message if not provided
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

        # Step 3: Add the user message to the session (using repository)
        self.repository.create_message(user_message_input)

        # Step 4: Get conversation context
        messages = self.repository.get_messages_by_session(message_input.session_id)
        context = await self.context_service.build_context_from_messages(message_input.session_id, messages)

        # Step 5: Enhance question with conversation context
        # Performance optimization: Reuse extracted entities from context to avoid duplicate extraction
        enhanced_question = await self.context_service.enhance_question_with_context(
            message_input.content,
            context.context_window,
            [msg.content for msg in messages[-5:]],  # Last 5 messages
            cached_entities=context.entities,  # Reuse entities (saves 50-100ms)
        )

        # Step 6: Execute search with conversation context
        search_result = await self._coordinate_search(
            enhanced_question=enhanced_question,
            session_id=message_input.session_id,
            collection_id=session.collection_id,
            user_id=session.user_id,
            context=context,
            messages=messages,
        )

        # Step 7: Serialize response and calculate token usage
        metadata_dict, total_token_count = await self._serialize_response(
            search_result=search_result,
            user_token_count=user_token_count,
            user_id=session.user_id,
            session_id=message_input.session_id,
            context=context,
        )

        # Step 8: Generate token warning if needed
        token_warning_dict = await self._generate_token_warning(
            user_token_count=user_token_count,
            assistant_token_count=total_token_count,
            user_id=session.user_id,
        )

        # Step 9: Create assistant response message
        assistant_message_input = ConversationMessageInput(
            session_id=message_input.session_id,
            content=search_result.answer,
            role=MessageRole.ASSISTANT,
            message_type=MessageType.ANSWER,
            metadata=metadata_dict,
            token_count=total_token_count,
            execution_time=search_result.execution_time,
        )

        # Step 10: Store assistant message (using repository)
        assistant_message = self.repository.create_message(assistant_message_input)

        logger.info(
            f"📊 MESSAGE ORCHESTRATOR: Assistant message created with token_count={assistant_message.token_count}"
        )

        # Step 11: Add token warning to the response if present
        if token_warning_dict:
            assistant_message.token_warning = token_warning_dict
            logger.info("📊 MESSAGE ORCHESTRATOR: Added token warning to response")

        # Step 12: Add full source documents to the response for frontend consumption
        # Extract serialized documents from metadata
        serialized_documents = metadata_dict.get("sources", [])
        if serialized_documents:
            assistant_message.sources = serialized_documents
            logger.info(f"📊 MESSAGE ORCHESTRATOR: Added {len(serialized_documents)} sources to response")

        # Step 13: Add CoT output to the response if CoT was used
        cot_used = metadata_dict.get("cot_used", False)
        cot_output = metadata_dict.get("cot_output")
        if cot_used and cot_output:
            assistant_message.cot_output = cot_output
            logger.info("📊 MESSAGE ORCHESTRATOR: Added CoT output to response")

        logger.info(
            "🎉 MESSAGE ORCHESTRATOR: Returning assistant message with full metadata (including token_analysis), sources, and CoT"
        )
        return assistant_message

    async def _coordinate_search(
        self,
        enhanced_question: str,
        session_id: UUID,
        collection_id: UUID,
        user_id: UUID,
        context: ConversationContext,
        messages: list[ConversationMessageOutput],
    ) -> SearchOutput:
        """Coordinate search with conversation context.

        This method integrates conversation context into the search request,
        enabling conversation-aware RAG search with automatic CoT detection.

        Args:
            enhanced_question: Question enhanced with conversation entities
            session_id: Conversation session ID
            collection_id: Collection to search in
            user_id: User ID for authentication
            context: Built conversation context
            messages: Recent conversation messages

        Returns:
            SearchOutput: Search results with answer, documents, and optional CoT output

        Example:
            ```python
            search_result = await self._coordinate_search(
                enhanced_question="Tell me about IBM Watson",
                session_id=session_id,
                collection_id=collection_id,
                user_id=user_id,
                context=context,
                messages=messages[-10:],
            )
            ```

        Notes:
            - Passes conversation context to SearchService
            - Enables automatic CoT detection for complex questions
            - Includes message history for better context understanding
        """
        # Validate that we have proper IDs for search
        if not collection_id or not user_id:
            raise ValidationError("Session must have valid collection_id and user_id for search")

        # Create search input with conversation context
        search_input = SearchInput(
            question=enhanced_question,
            collection_id=collection_id,
            user_id=user_id,
            config_metadata={
                "conversation_context": context.context_window,
                "session_id": str(session_id),
                "message_history": [msg.content for msg in messages[-10:]],
                "conversation_entities": context.context_metadata.get("extracted_entities", []),
                "cot_enabled": True,
                "show_cot_steps": False,  # Disable CoT steps visibility for context flow
                "conversation_aware": True,
            },
        )

        # Execute search - this will automatically use CoT if appropriate
        logger.info("🔍 MESSAGE ORCHESTRATOR: Executing search with conversation context")
        search_result = await self.search_service.search(search_input)
        logger.info("✅ MESSAGE ORCHESTRATOR: Search completed successfully")

        return search_result

    async def _serialize_response(
        self,
        search_result: SearchOutput,
        user_token_count: int,
        user_id: UUID,
        session_id: UUID,
        context: ConversationContext,
    ) -> tuple[dict[str, Any], int]:
        """Serialize search result and calculate token usage.

        This method converts complex search result objects (DocumentMetadata, QueryResult)
        into JSON-serializable dictionaries for database storage and frontend consumption.

        Args:
            search_result: Search result from SearchService
            user_token_count: Token count for user input
            user_id: User ID for provider lookup
            session_id: Session ID for statistics
            context: Conversation context

        Returns:
            Tuple of (metadata_dict, total_token_count) where:
                - metadata_dict: JSON-serializable metadata with sources, CoT, tokens
                - total_token_count: Total tokens (assistant + CoT)

        Example:
            ```python
            metadata_dict, token_count = await self._serialize_response(
                search_result=search_result,
                user_token_count=50,
                user_id=user_id,
                session_id=session_id,
                context=context,
            )

            print(f"Sources: {len(metadata_dict['sources'])}")
            print(f"Total tokens: {token_count}")
            ```

        Notes:
            - Extracts CoT information from both metadata and cot_output
            - Serializes DocumentMetadata with scores and page numbers
            - Calculates token usage using provider's tokenize method if available
            - Falls back to word-based estimation if provider unavailable
        """
        # Extract metadata and cot_output from search result
        result_metadata = getattr(search_result, "metadata", None)
        result_cot_output = getattr(search_result, "cot_output", None)

        logger.info("📊 MESSAGE ORCHESTRATOR: Search result has metadata: %s", result_metadata is not None)
        if result_metadata:
            logger.info("📊 MESSAGE ORCHESTRATOR: Search metadata keys: %s", list(result_metadata.keys()))
        logger.info("📊 MESSAGE ORCHESTRATOR: Search result has cot_output: %s", result_cot_output is not None)

        # Extract CoT information if it was used
        cot_used = False
        cot_steps: list[dict[str, Any]] = []

        # Check both metadata and cot_output for CoT information
        if result_metadata:
            cot_used = result_metadata.get("cot_used", False)
            logger.info("🧠 CoT metadata: cot_used=%s", cot_used)

        # Extract CoT steps from cot_output (this is where the actual reasoning steps are)
        if result_cot_output and isinstance(result_cot_output, dict):
            reasoning_steps = result_cot_output.get("reasoning_steps", [])
            if reasoning_steps:
                cot_used = True  # If we have reasoning steps, CoT was used
                # Convert reasoning steps to a format suitable for conversation metadata
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

        logger.info("🧠 Final CoT extraction: cot_used=%s, cot_steps_count=%d", cot_used, len(cot_steps))

        # Serialize documents with query results for scores and page numbers
        result_documents = getattr(search_result, "documents", []) or []
        result_query_results = getattr(search_result, "query_results", []) or []
        serialized_documents = self._serialize_documents(result_documents, result_query_results)

        # Calculate assistant response tokens
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
                for step in result_cot_output.get("reasoning_steps", []):
                    step_tokens = step.get("token_usage", 0) if isinstance(step, dict) else 0
                    cot_token_usage += step_tokens
            logger.info("🔢 CoT token usage extracted: %s", cot_token_usage)

        # Total token count for the assistant response (includes assistant response + CoT tokens)
        total_token_count = assistant_response_tokens + cot_token_usage

        # Calculate context tokens and conversation total tokens
        context_tokens = len(serialized_documents) * 100 if serialized_documents else 0

        # Get conversation total tokens from session messages
        # NOTE: This is a simple estimation - full implementation would use session statistics
        conversation_total_tokens = sum(msg.token_count or 0 for msg in self.repository.get_messages_by_session(session_id))

        # Create metadata dictionary with all information
        metadata_dict = {
            "source_documents": [doc.get("document_name", "") for doc in serialized_documents]
            if serialized_documents
            else None,
            "search_metadata": {
                "enhanced_question": "",  # Will be populated by caller if needed
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
            "token_count": total_token_count,
            "token_analysis": {
                "query_tokens": user_token_count,
                "context_tokens": context_tokens,
                "response_tokens": assistant_response_tokens,
                "system_tokens": cot_token_usage,
                "total_this_turn": total_token_count,
                "conversation_total": conversation_total_tokens,
            },
            # Store full source data for frontend consumption
            "sources": serialized_documents if serialized_documents else None,
            # Store CoT output for frontend consumption
            "cot_output": result_cot_output if (cot_used and result_cot_output) else None,
        }

        logger.info(
            f"📊 MESSAGE ORCHESTRATOR: Created metadata_dict with token_analysis: {metadata_dict.get('token_analysis')}"
        )
        logger.info(
            f"🔢 Token tracking breakdown: assistant={assistant_response_tokens}, cot={cot_token_usage}, total={total_token_count}"
        )

        return metadata_dict, total_token_count

    def _serialize_documents(
        self, documents: list[Any], query_results: list[Any]
    ) -> list[dict[str, Any]]:
        """Convert DocumentMetadata objects to JSON-serializable dictionaries.

        This method enhances documents with scores and page numbers from query_results,
        matching the frontend schema requirements.

        Args:
            documents: List of DocumentMetadata objects from search
            query_results: List of QueryResult objects with scores and page numbers

        Returns:
            List of dictionaries with structure:
                {
                    "document_name": str,
                    "content": str,
                    "metadata": {
                        "score": float,
                        "page_number": int,
                        ...other fields
                    }
                }

        Example:
            ```python
            serialized = self._serialize_documents(
                documents=search_result.documents,
                query_results=search_result.query_results,
            )

            for doc in serialized:
                print(f"Document: {doc['document_name']}")
                print(f"Score: {doc['metadata']['score']}")
                print(f"Page: {doc['metadata'].get('page_number')}")
            ```

        Notes:
            - Extracts best score across all chunks per document
            - Collects all page numbers mentioned
            - Limits content length to avoid huge payloads (2000 chars)
            - Defaults score to 1.0 when no query_results available
        """
        # Extract scores and page numbers from query_results by document_id
        doc_data_map: dict[Any, dict[str, Any]] = {}
        if query_results:
            for result in query_results:
                if not result.chunk:
                    continue

                doc_id = result.chunk.document_id
                if not doc_id:
                    continue

                # Get score (from QueryResult level first, then chunk level)
                score = (
                    result.score
                    if result.score is not None
                    else (result.chunk.score if hasattr(result.chunk, "score") else None)
                )

                # Get page number from chunk metadata
                page_number = None
                if result.chunk.metadata and hasattr(result.chunk.metadata, "page_number"):
                    page_number = result.chunk.metadata.page_number

                # Get content from chunk
                content = result.chunk.text if hasattr(result.chunk, "text") and result.chunk.text else ""

                # Keep track of best score and first page number for each document
                if doc_id not in doc_data_map:
                    doc_data_map[doc_id] = {
                        "score": score,
                        "page_numbers": {page_number} if page_number else set(),
                        "content": content,
                    }
                else:
                    # Update with better score if found
                    if score is not None and (
                        doc_data_map[doc_id]["score"] is None or score > doc_data_map[doc_id]["score"]
                    ):
                        doc_data_map[doc_id]["score"] = score
                    # Collect all page numbers
                    if page_number:
                        doc_data_map[doc_id]["page_numbers"].add(page_number)
                    # Append content (limit to avoid huge payloads)
                    if content and len(doc_data_map[doc_id]["content"]) < 2000:
                        doc_data_map[doc_id]["content"] += "\n\n" + content

        serialized = []
        for doc in documents:
            if hasattr(doc, "__dict__"):
                # Extract fields matching frontend schema
                doc_dict = {
                    "document_name": getattr(doc, "document_name", getattr(doc, "name", "Unknown Document")),
                    "content": getattr(doc, "content", getattr(doc, "text", "")),
                    "metadata": {},
                }

                # Collect all other attributes into metadata dict
                for key, value in doc.__dict__.items():
                    if key not in ["document_name", "name", "content", "text"]:
                        if isinstance(value, str | int | float | bool | type(None)):
                            doc_dict["metadata"][key] = value
                        else:
                            doc_dict["metadata"][key] = str(value)

                # Try to enhance with data from query_results
                if doc_data_map:
                    all_scores = [data["score"] for data in doc_data_map.values() if data["score"] is not None]
                    all_pages = []
                    for data in doc_data_map.values():
                        all_pages.extend(data["page_numbers"])

                    if all_scores:
                        # Use the best (highest) score from all retrieved chunks
                        doc_dict["metadata"]["score"] = max(all_scores)
                    else:
                        # Default score when query_results exist but have no scores
                        doc_dict["metadata"]["score"] = 1.0

                    if all_pages:
                        # Use the first page number mentioned
                        doc_dict["metadata"]["page_number"] = min(all_pages)

                    # If original content is empty, use content from query results
                    if not doc_dict["content"]:
                        # Get first non-empty content
                        for data in doc_data_map.values():
                            if data["content"]:
                                doc_dict["content"] = data["content"][:1000]  # Limit to 1000 chars
                                break
                else:
                    # Default score when no query_results available
                    doc_dict["metadata"]["score"] = 1.0

                serialized.append(doc_dict)
            else:
                # Fallback for unknown types
                serialized.append({"document_name": "Unknown", "content": str(doc), "metadata": {}})

        logger.info(f"📊 Serialized {len(serialized)} documents with scores and page numbers")
        if serialized and "metadata" in serialized[0]:
            logger.info(f"📊 First source metadata: {serialized[0]['metadata']}")

        return serialized

    async def _generate_token_warning(
        self, user_token_count: int, assistant_token_count: int, user_id: UUID
    ) -> dict[str, Any] | None:
        """Generate token warning if needed based on usage thresholds.

        Args:
            user_token_count: Token count for user input
            assistant_token_count: Token count for assistant response
            user_id: User ID for provider lookup

        Returns:
            Dictionary with token warning information or None if no warning needed

        Example:
            ```python
            warning = await self._generate_token_warning(
                user_token_count=50,
                assistant_token_count=200,
                user_id=user_id,
            )

            if warning:
                print(f"Warning: {warning['message']}")
                print(f"Usage: {warning['percentage_used']}%")
            ```
        """
        try:
            # Get model name from provider
            provider = self.llm_provider_service.get_user_provider(user_id)
            model_name = getattr(provider, "model_id", None) if provider else None
            if not model_name:
                model_name = getattr(provider, "model_name", "default-model") if provider else "default-model"

            # Create LLMUsage object for warning check
            current_usage = LLMUsage(
                prompt_tokens=user_token_count,
                completion_tokens=assistant_token_count,
                total_tokens=user_token_count + assistant_token_count,
                model_name=model_name,
                service_type=ServiceType.CONVERSATION,
                timestamp=datetime.now(),
                user_id=str(user_id),
            )

            # Check for token usage warnings
            token_warning = await self.token_tracking_service.check_usage_warning(
                current_usage=current_usage, context_tokens=user_token_count + assistant_token_count
            )

            if token_warning:
                return {
                    "type": token_warning.warning_type.value,
                    "severity": token_warning.severity,
                    "percentage_used": token_warning.percentage_used,
                    "current_tokens": token_warning.current_tokens,
                    "limit_tokens": token_warning.limit_tokens,
                    "message": token_warning.message,
                    "suggested_action": token_warning.suggested_action,
                }
        except (ValueError, KeyError, AttributeError) as e:
            logger.warning("Failed to generate token warning: %s", str(e))

        return None
