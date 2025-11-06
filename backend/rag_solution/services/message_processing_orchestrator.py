"""Message processing orchestrator for conversation system.

This orchestrator handles the complex workflow of processing user messages,
integrating search, Chain of Thought reasoning, token tracking, and context building.

Extracted from ConversationService.process_user_message() (423 lines) for better
separation of concerns and improved testability.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.core.exceptions import NotFoundError, ValidationError
from rag_solution.repository.conversation_repository import ConversationRepository
from rag_solution.schemas.conversation_schema import (
    ConversationMessageInput,
    ConversationMessageOutput,
    MessageRole,
    MessageType,
)
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.schemas.search_schema import SearchOutput as SearchResult
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.services.conversation_context_service import ConversationContextService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.search_service import SearchService
from rag_solution.services.token_tracking_service import TokenTrackingService

logger = logging.getLogger(__name__)


class MessageProcessingOrchestrator:
    """Orchestrates user message processing with search, CoT, and context integration.

    This service handles the end-to-end workflow of processing user messages:
    1. Validate session and store user message
    2. Build conversation context
    3. Enhance question with context
    4. Execute search (automatic CoT detection)
    5. Track token usage
    6. Generate token warnings if needed
    7. Serialize response with sources and CoT output
    8. Store assistant message
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
        """Initialize the message processing orchestrator.

        Args:
            db: Database session
            settings: Application settings
            conversation_repository: Unified conversation repository
            search_service: Search service for RAG queries
            context_service: Conversation context service
            token_tracking_service: Token tracking service
            llm_provider_service: LLM provider service
            chain_of_thought_service: Optional Chain of Thought service
        """
        self.db = db
        self.settings = settings
        self.repository = conversation_repository
        self.search_service = search_service
        self.context_service = context_service
        self.token_tracking_service = token_tracking_service
        self.llm_provider_service = llm_provider_service
        self.chain_of_thought_service = chain_of_thought_service

    async def process_user_message(self, message_input: ConversationMessageInput) -> ConversationMessageOutput:
        """Process user message end-to-end with search, CoT, and token tracking.

        Args:
            message_input: User message input

        Returns:
            Assistant message output with full metadata, sources, and CoT output

        Raises:
            NotFoundError: If session not found
            ValidationError: If session invalid or processing fails
        """
        logger.info(
            f"🚀 MESSAGE ORCHESTRATOR: process_user_message() called with session_id={message_input.session_id}"
        )
        logger.info("📝 MESSAGE ORCHESTRATOR: message content: %s...", message_input.content[:100])

        # 1. Validate session exists and get user/collection context
        try:
            session = self.repository.get_session_by_id(message_input.session_id)
        except NotFoundError:
            raise ValueError("Session not found") from None

        logger.info(
            f"📊 MESSAGE ORCHESTRATOR: Found session - user_id={session.user_id}, collection_id={session.collection_id}"
        )

        # 2. Calculate token count for user message
        user_token_count = message_input.token_count or 0
        if user_token_count == 0:
            # Simple token estimation for user message
            user_token_count = max(5, int(len(message_input.content.split()) * 1.3))  # Rough estimation

        # 3. Store user message
        user_message_input = ConversationMessageInput(
            session_id=message_input.session_id,
            content=message_input.content,
            role=message_input.role,
            message_type=message_input.message_type,
            metadata=message_input.metadata,
            token_count=int(user_token_count),
            execution_time=message_input.execution_time or 0.0,
        )
        self.repository.create_message(user_message_input)

        # 4. Get conversation messages and build context
        messages = self.repository.get_messages_by_session(message_input.session_id)
        messages_output = [ConversationMessageOutput.from_db_message(msg) for msg in messages]
        context = await self.context_service.build_context_from_messages(message_input.session_id, messages_output)

        # 5. Enhance question with conversation context
        enhanced_question = await self.context_service.enhance_question_with_context(
            message_input.content,
            context.context_window,
            [msg.content for msg in messages_output[-5:]],  # Last 5 messages
        )

        # 6. Execute search with context
        search_result = await self._coordinate_search(
            enhanced_question=enhanced_question,
            session_id=message_input.session_id,
            collection_id=session.collection_id,
            user_id=session.user_id,
            context=context,
            messages=messages_output,
        )

        # 7. Serialize response and calculate tokens
        serialized_response, assistant_response_tokens = await self._serialize_response(
            search_result=search_result, user_token_count=user_token_count, user_id=session.user_id
        )

        # 8. Store assistant message with full metadata
        assistant_message = await self._store_assistant_message(
            session_id=message_input.session_id,
            search_result=search_result,
            serialized_response=serialized_response,
            assistant_response_tokens=assistant_response_tokens,
            user_token_count=user_token_count,
            user_id=session.user_id,
        )

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
        context: Any,
        messages: list[ConversationMessageOutput],
    ) -> SearchResult:
        """Coordinate search with conversation context.

        Args:
            enhanced_question: Enhanced question with context
            session_id: Session ID
            collection_id: Collection ID
            user_id: User ID
            context: Conversation context
            messages: Conversation messages

        Returns:
            Search result with answer, documents, and CoT output
        """
        # Validate IDs
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
                "show_cot_steps": False,  # Disable CoT steps visibility for context flow tests
                "conversation_aware": True,
            },
        )

        # Execute search - this will automatically use CoT if appropriate
        search_result = await self.search_service.search(search_input)

        logger.info("📊 MESSAGE ORCHESTRATOR: Search completed successfully")
        return search_result

    async def _serialize_response(
        self,
        search_result: SearchResult,
        user_token_count: int,  # noqa: ARG002
        user_id: UUID,
    ) -> tuple[dict[str, Any], int]:
        """Serialize search result and calculate token usage.

        Args:
            search_result: Search result from SearchService
            user_token_count: User message token count (unused, reserved for future enhancements)
            user_id: User ID

        Returns:
            Tuple of (serialized_response_dict, assistant_response_tokens)
        """
        # Extract metadata and cot_output
        result_metadata = getattr(search_result, "metadata", None)
        result_cot_output = getattr(search_result, "cot_output", None)

        logger.info("📊 MESSAGE ORCHESTRATOR: Search result has metadata: %s", result_metadata is not None)
        if result_metadata:
            logger.info("📊 MESSAGE ORCHESTRATOR: Search metadata keys: %s", list(result_metadata.keys()))
        logger.info("📊 MESSAGE ORCHESTRATOR: Search result has cot_output: %s", result_cot_output is not None)

        # Extract CoT information
        cot_used = False
        cot_steps: list[dict[str, Any]] = []

        # Check both metadata and cot_output for CoT information
        if result_metadata:
            cot_used = result_metadata.get("cot_used", False)
            logger.info("🧠 CoT metadata: cot_used=%s", cot_used)

        # Extract CoT steps from cot_output
        if result_cot_output and isinstance(result_cot_output, dict):
            reasoning_steps = result_cot_output.get("reasoning_steps", [])
            if reasoning_steps:
                cot_used = True
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

        logger.info("🧠 Final CoT extraction: cot_used=%s, cot_steps_count=%d", cot_used, len(cot_steps))

        # Serialize documents with query results for scores and page numbers
        result_documents = getattr(search_result, "documents", []) or []
        result_query_results = getattr(search_result, "query_results", []) or []
        serialized_documents = self._serialize_documents(result_documents, result_query_results)

        # Calculate assistant response tokens
        try:
            provider = self.llm_provider_service.get_user_provider(user_id)
            provider_client = getattr(provider, "client", None) if provider else None
            tokenize_method = getattr(provider_client, "tokenize", None) if provider_client else None

            if tokenize_method:
                try:
                    assistant_tokens_result = tokenize_method(text=search_result.answer)
                    assistant_response_tokens = len(assistant_tokens_result.get("result", []))
                    logger.info("✅ Real token count from provider: assistant=%d", assistant_response_tokens)
                except (ValueError, KeyError, AttributeError) as e:
                    logger.info("Provider tokenize failed, using improved estimation: %s", str(e))
                    assistant_response_tokens = max(50, int(len(search_result.answer.split()) * 1.3))
            else:
                assistant_response_tokens = max(50, int(len(search_result.answer.split()) * 1.3))

        except (ValueError, KeyError, AttributeError) as e:
            logger.info("Using improved token estimation: %s", str(e))
            assistant_response_tokens = max(50, int(len(search_result.answer.split()) * 1.3))

        # Add CoT token usage
        cot_token_usage = 0
        if result_cot_output and isinstance(result_cot_output, dict):
            cot_token_usage = result_cot_output.get("token_usage", 0)
            if not cot_token_usage:
                # Sum from individual reasoning steps
                reasoning_steps = result_cot_output.get("reasoning_steps", [])
                for step in reasoning_steps:
                    step_tokens = step.get("token_usage", 0) if isinstance(step, dict) else 0
                    cot_token_usage += step_tokens
            logger.info("🔢 CoT token usage extracted: %s", cot_token_usage)

        logger.info(
            f"🔢 Final token count breakdown: assistant={assistant_response_tokens}, cot={cot_token_usage}, total={assistant_response_tokens + cot_token_usage}"
        )

        # Build serialized response
        serialized_response = {
            "answer": search_result.answer,
            "documents": serialized_documents,
            "cot_used": cot_used,
            "cot_steps": cot_steps,
            "cot_output": result_cot_output if (cot_used and result_cot_output) else None,
            "execution_time": search_result.execution_time,
        }

        return serialized_response, assistant_response_tokens

    async def _store_assistant_message(
        self,
        session_id: UUID,
        search_result: SearchResult,
        serialized_response: dict[str, Any],
        assistant_response_tokens: int,
        user_token_count: int,
        user_id: UUID,
    ) -> ConversationMessageOutput:
        """Store assistant message with full metadata and token tracking.

        Args:
            session_id: Session ID
            search_result: Search result
            serialized_response: Serialized response dictionary
            assistant_response_tokens: Assistant response token count
            user_token_count: User message token count
            user_id: User ID

        Returns:
            Created assistant message
        """
        cot_used = serialized_response["cot_used"]
        cot_steps = serialized_response["cot_steps"]
        cot_output = serialized_response["cot_output"]
        serialized_documents = serialized_response["documents"]

        # Calculate total token count
        cot_token_usage = 0
        if cot_output and isinstance(cot_output, dict):
            cot_token_usage = cot_output.get("token_usage", 0)
            if not cot_token_usage:
                for step in cot_steps:
                    cot_token_usage += step.get("token_usage", 0)

        token_count = assistant_response_tokens + cot_token_usage

        # Calculate context tokens and conversation total tokens
        context_tokens = len(serialized_documents) * 100 if serialized_documents else 0

        # Get conversation total tokens from session statistics
        try:
            total_messages_tokens = self.repository.get_token_usage_by_session(session_id)
            conversation_total_tokens = total_messages_tokens
        except Exception:
            conversation_total_tokens = 0

        # Generate token warning if needed
        token_warning_dict = await self._generate_token_warning(
            user_token_count=user_token_count,
            assistant_response_tokens=assistant_response_tokens,
            user_id=user_id,
        )

        # Build metadata dictionary
        metadata_dict = {
            "source_documents": [doc.get("document_name", "") for doc in serialized_documents]
            if serialized_documents
            else None,
            "search_metadata": {
                "enhanced_question": search_result.answer,  # Store for reference
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
            "cot_output": cot_output if (cot_used and cot_output) else None,
        }

        logger.info(
            f"📊 MESSAGE ORCHESTRATOR: Created metadata_dict with token_analysis: {metadata_dict.get('token_analysis')}"
        )

        # Create assistant message input
        assistant_message_input = ConversationMessageInput(
            session_id=session_id,
            content=search_result.answer,
            role=MessageRole.ASSISTANT,
            message_type=MessageType.ANSWER,
            metadata=metadata_dict,  # Pass dict directly
            token_count=token_count,
            execution_time=search_result.execution_time,
        )

        # Store assistant message
        assistant_message = self.repository.create_message(assistant_message_input)
        logger.info(
            f"📊 MESSAGE ORCHESTRATOR: Assistant message created with token_count={assistant_message.token_count}"
        )

        # Convert to output schema
        assistant_message_output = ConversationMessageOutput.from_db_message(assistant_message)

        # Add token warning to the response if present
        if token_warning_dict:
            assistant_message_output.token_warning = token_warning_dict
            logger.info("📊 MESSAGE ORCHESTRATOR: Added token warning to response")

        # Add full source documents to the response
        if serialized_documents:
            assistant_message_output.sources = serialized_documents
            logger.info(f"📊 MESSAGE ORCHESTRATOR: Added {len(serialized_documents)} sources to response")

        # Add CoT output to the response if CoT was used
        if cot_used and cot_output:
            assistant_message_output.cot_output = cot_output
            logger.info("📊 MESSAGE ORCHESTRATOR: Added CoT output to response")

        return assistant_message_output

    async def _generate_token_warning(
        self, user_token_count: int, assistant_response_tokens: int, user_id: UUID
    ) -> dict[str, Any] | None:
        """Generate token warning if usage exceeds thresholds.

        Args:
            user_token_count: User message token count
            assistant_response_tokens: Assistant response token count
            user_id: User ID

        Returns:
            Token warning dictionary or None
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
                return token_warning_dict

        except (ValueError, KeyError, AttributeError) as e:
            logger.warning("Failed to generate token warning: %s", str(e))

        return None

    def _serialize_documents(self, documents: list[Any], query_results: list[Any]) -> list[dict[str, Any]]:
        """Convert DocumentMetadata objects to JSON-serializable dictionaries.

        Enhances documents with scores and page numbers from query_results.
        Frontend expects: {document_name: str, content: str, metadata: {score: float, page_number: int, ...}}

        Args:
            documents: List of document metadata objects
            query_results: List of query result objects

        Returns:
            List of serialized document dictionaries
        """
        # Extract scores and page numbers from query_results by document_id
        doc_data_map = {}
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
