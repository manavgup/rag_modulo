"""Conversation summarization service for managing conversation context windows.

This service handles automatic conversation summarization to manage context windows,
extract key insights, and preserve important conversation elements.
"""

import logging
from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.core.exceptions import NotFoundError, ValidationError
from rag_solution.repository.conversation_message_repository import ConversationMessageRepository
from rag_solution.repository.conversation_session_repository import ConversationSessionRepository
from rag_solution.repository.conversation_summary_repository import ConversationSummaryRepository
from rag_solution.schemas.conversation_schema import (
    ContextSummarizationInput,
    ContextSummarizationOutput,
    ConversationMessageOutput,
    ConversationSummaryInput,
    ConversationSummaryOutput,
    SummarizationConfigInput,
    SummarizationStrategy,
)
from rag_solution.schemas.llm_usage_schema import ServiceType
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.token_tracking_service import TokenTrackingService

logger = logging.getLogger(__name__)


class ConversationSummarizationService:
    """Service for handling conversation summarization and context management."""

    def __init__(self, db: Session, settings: Settings):
        """Initialize the conversation summarization service.

        Args:
            db: Database session
            settings: Application settings
        """
        self.db = db
        self.settings = settings
        self._llm_provider_service: LLMProviderService | None = None
        self._token_tracking_service: TokenTrackingService | None = None

        # Initialize repositories
        self.summary_repository = ConversationSummaryRepository(db)
        self.session_repository = ConversationSessionRepository(db)
        self.message_repository = ConversationMessageRepository(db)

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

    async def create_summary(
        self, summary_input: ConversationSummaryInput, user_id: UUID4
    ) -> ConversationSummaryOutput:
        """Create a conversation summary.

        Args:
            summary_input: Summary creation input
            user_id: ID of user requesting the summary

        Returns:
            Created conversation summary

        Raises:
            NotFoundError: If session not found
            ValidationError: If input validation fails
        """
        try:
            # Validate session exists and user has access
            session = self.session_repository.get_by_id(summary_input.session_id)
            if session.user_id != user_id:
                raise ValidationError("User does not have access to this session")

            # Get messages to summarize
            messages = self.message_repository.get_messages_by_session(
                summary_input.session_id, limit=summary_input.message_count_to_summarize
            )

            if not messages:
                raise ValidationError("No messages found to summarize")

            # Create initial summary record
            summary = self.summary_repository.create(summary_input)

            # Generate summary text using LLM
            summary_text, metadata = await self._generate_summary_content(messages, summary_input, user_id)

            # Update summary with generated content
            updates = {
                "summary_text": summary_text,
                "tokens_saved": metadata.get("tokens_saved", 0),
                "key_topics": metadata.get("key_topics", []),
                "important_decisions": metadata.get("important_decisions", []),
                "unresolved_questions": metadata.get("unresolved_questions", []),
                "summary_metadata": metadata,
            }

            updated_summary = self.summary_repository.update(summary.id, updates)

            logger.info(f"Created conversation summary: {updated_summary.id}")
            return updated_summary

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error creating conversation summary: {e}")
            raise ValidationError(f"Failed to create summary: {e}") from e

    async def summarize_for_context_management(
        self, summarization_input: ContextSummarizationInput
    ) -> ContextSummarizationOutput:
        """Summarize conversation for context window management.

        Args:
            summarization_input: Context summarization input

        Returns:
            Context summarization output with preserved messages and summary

        Raises:
            ValidationError: If input validation fails
        """
        try:
            messages = summarization_input.messages
            config = summarization_input.config

            # Determine which messages to summarize vs preserve
            total_messages = len(messages)
            preserve_count = min(config.preserve_recent_messages, total_messages)
            summarize_count = max(0, total_messages - preserve_count)

            if summarize_count < config.min_messages_for_summary:
                # Not enough messages to summarize, return as-is
                return ContextSummarizationOutput(
                    summary=ConversationSummaryOutput(
                        session_id=summarization_input.session_id,
                        summary_text="No summarization needed - insufficient messages",
                        summarized_message_count=0,
                        tokens_saved=0,
                        key_topics=[],
                        important_decisions=[],
                        unresolved_questions=[],
                        summary_strategy=SummarizationStrategy.RECENT_PLUS_SUMMARY,
                        metadata={"reason": "insufficient_messages"},
                    ),
                    preserved_messages=messages,
                    tokens_saved=0,
                    new_context_size=summarization_input.current_context_size,
                    compression_ratio=0.0,
                )

            # Split messages into summarize and preserve groups
            messages_to_summarize = messages[:-preserve_count] if preserve_count > 0 else messages
            preserved_messages = messages[-preserve_count:] if preserve_count > 0 else []

            # Create summary input
            summary_input = ConversationSummaryInput(
                session_id=summarization_input.session_id,
                message_count_to_summarize=len(messages_to_summarize),
                strategy=SummarizationStrategy.RECENT_PLUS_SUMMARY,
                preserve_context=True,
                include_decisions=config.decision_tracking_enabled,
                include_questions=True,
            )

            # Get user_id from session
            session = self.session_repository.get_by_id(summarization_input.session_id)
            user_id = session.user_id

            # Generate summary
            summary_text, metadata = await self._generate_summary_content(messages_to_summarize, summary_input, user_id)

            # Calculate token savings
            original_tokens = sum(msg.token_count or 0 for msg in messages_to_summarize)
            summary_tokens = await self._estimate_tokens(summary_text)
            tokens_saved = max(0, original_tokens - summary_tokens)

            # Create summary output
            summary = ConversationSummaryOutput(
                session_id=summarization_input.session_id,
                summary_text=summary_text,
                summarized_message_count=len(messages_to_summarize),
                tokens_saved=tokens_saved,
                key_topics=metadata.get("key_topics", []),
                important_decisions=metadata.get("important_decisions", []),
                unresolved_questions=metadata.get("unresolved_questions", []),
                summary_strategy=SummarizationStrategy.RECENT_PLUS_SUMMARY,
                metadata=metadata,
            )

            # Calculate new context size and compression ratio
            preserved_tokens = sum(msg.token_count or 0 for msg in preserved_messages)
            new_context_size = summary_tokens + preserved_tokens
            compression_ratio = tokens_saved / original_tokens if original_tokens > 0 else 0.0

            return ContextSummarizationOutput(
                summary=summary,
                preserved_messages=preserved_messages,
                tokens_saved=tokens_saved,
                new_context_size=new_context_size,
                compression_ratio=compression_ratio,
            )

        except Exception as e:
            logger.error(f"Error in context summarization: {e}")
            raise ValidationError(f"Failed to summarize for context management: {e}") from e

    async def get_session_summaries(
        self, session_id: UUID4, user_id: UUID4, limit: int = 10
    ) -> list[ConversationSummaryOutput]:
        """Get summaries for a conversation session.

        Args:
            session_id: Session ID
            user_id: User ID for access validation
            limit: Maximum number of summaries to return

        Returns:
            List of conversation summaries

        Raises:
            NotFoundError: If session not found
            ValidationError: If user doesn't have access
        """
        try:
            # Validate session exists and user has access
            session = self.session_repository.get_by_id(session_id)
            if session.user_id != user_id:
                raise ValidationError("User does not have access to this session")

            return self.summary_repository.get_by_session_id(session_id, limit=limit)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting session summaries: {e}")
            raise ValidationError(f"Failed to get session summaries: {e}") from e

    async def check_context_window_threshold(self, session_id: UUID4, config: SummarizationConfigInput) -> bool:
        """Check if context window has reached summarization threshold.

        Args:
            session_id: Session ID to check
            config: Summarization configuration

        Returns:
            True if summarization is recommended
        """
        try:
            session = self.session_repository.get_by_id(session_id)
            messages = self.message_repository.get_messages_by_session(session_id, limit=100)

            if len(messages) < config.min_messages_for_summary:
                return False

            # Calculate current context usage
            total_tokens = sum(msg.token_count or 0 for msg in messages)
            context_usage_ratio = total_tokens / session.context_window_size

            return context_usage_ratio >= config.context_window_threshold

        except Exception as e:
            logger.error(f"Error checking context window threshold: {e}")
            return False

    async def _generate_summary_content(
        self, messages: list[ConversationMessageOutput], summary_input: ConversationSummaryInput, user_id: UUID4
    ) -> tuple[str, dict[str, Any]]:
        """Generate summary content using LLM.

        Args:
            messages: Messages to summarize
            summary_input: Summary configuration

        Returns:
            Tuple of (summary_text, metadata)
        """
        try:
            # Build conversation text from messages
            conversation_text = self._build_conversation_text(messages)

            # Create summarization prompt based on strategy
            prompt = self._create_summarization_prompt(conversation_text, summary_input)

            # Get LLM provider configuration
            provider_config = self.llm_provider_service.get_default_provider()
            if not provider_config:
                raise ValidationError("No LLM provider available for summarization")

            # Create LLM provider instance using factory
            from rag_solution.generation.providers.factory import LLMProviderFactory

            factory = LLMProviderFactory(self.db)
            llm_provider = factory.get_provider(provider_config.name)

            # Generate summary
            response, _usage = await llm_provider.generate_text_with_usage(
                user_id=user_id,
                prompt=prompt,
                service_type=ServiceType.CONVERSATION,  # type: ignore
            )

            # Ensure response is not empty
            if not response or not response.strip():
                logger.warning("LLM returned empty response, using fallback")
                raise ValueError("Empty LLM response")

            # Parse response and extract metadata
            summary_text, metadata = self._parse_summary_response(response, messages)

            # Double-check we have valid summary text
            if not summary_text or not summary_text.strip():
                logger.warning("Parsed summary text is empty, using fallback")
                raise ValueError("Empty parsed summary")

            return summary_text, metadata

        except Exception as e:
            logger.error(f"Error generating summary content: {e}")
            # Fallback to simple concatenation - ensure it returns non-empty string
            fallback_text = self._create_fallback_summary(messages)
            if not fallback_text:
                # Ensure we always return something valid
                fallback_text = (
                    f"Summary of {len(messages)} messages in conversation (auto-generated due to LLM unavailability)"
                )

            metadata = {
                "fallback": True,
                "error": str(e),
                "message_count": len(messages),
                "key_topics": [],
                "important_decisions": [],
                "unresolved_questions": [],
            }
            return fallback_text, metadata

    def _build_conversation_text(self, messages: list[ConversationMessageOutput]) -> str:
        """Build conversation text from messages."""
        conversation_lines = []
        for msg in messages:
            role = msg.role.value.upper()
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            conversation_lines.append(f"[{timestamp}] {role}: {msg.content}")

        return "\n".join(conversation_lines)

    def _create_summarization_prompt(self, conversation_text: str, summary_input: ConversationSummaryInput) -> str:
        """Create LLM prompt for summarization."""
        strategy_instructions = {
            SummarizationStrategy.RECENT_PLUS_SUMMARY: "Focus on recent interactions while preserving important context",
            SummarizationStrategy.FULL_CONVERSATION: "Provide a comprehensive summary of the entire conversation",
            SummarizationStrategy.KEY_POINTS_ONLY: "Extract only the most important key points and decisions",
            SummarizationStrategy.TOPIC_BASED: "Organize the summary by main topics discussed",
        }

        instruction = strategy_instructions.get(
            summary_input.strategy, "Provide a balanced summary of the conversation"
        )

        return f"""Please summarize the following conversation using this strategy: {instruction}

Conversation:
{conversation_text}

Please provide:
1. A concise summary (2-3 paragraphs)
{f"2. Key topics discussed (if enabled: {summary_input.include_decisions})" if summary_input.include_decisions else ""}
{"3. Important decisions made (if any)" if summary_input.include_decisions else ""}
{"4. Unresolved questions or open items" if summary_input.include_questions else ""}

Format your response as structured text that can be easily parsed."""

    def _parse_summary_response(
        self, response: str, messages: list[ConversationMessageOutput]
    ) -> tuple[str, dict[str, Any]]:
        """Parse LLM response and extract metadata."""
        # Simple parsing - in production, this would be more sophisticated
        lines = response.strip().split("\n")
        summary_text = response.strip()  # Default to full response, but strip whitespace

        # If summary_text is empty after stripping, create a fallback
        if not summary_text:
            summary_text = self._create_fallback_summary(messages)

        metadata: dict[str, Any] = {
            "key_topics": [],
            "important_decisions": [],
            "unresolved_questions": [],
            "message_count": len(messages),
            "generation_method": "llm",
        }

        # Try to extract structured information if present
        # This is a simplified parser - in production, you'd use more robust parsing
        current_section = None
        for line in lines:
            line = line.strip()
            if "key topics" in line.lower():
                current_section = "topics"
            elif "decisions" in line.lower():
                current_section = "decisions"
            elif "questions" in line.lower() or "unresolved" in line.lower():
                current_section = "questions"
            elif line.startswith(("- ", "• ")):
                item = line[2:].strip()
                if current_section == "topics":
                    metadata["key_topics"].append(item)
                elif current_section == "decisions":
                    metadata["important_decisions"].append(item)
                elif current_section == "questions":
                    metadata["unresolved_questions"].append(item)

        # Final validation: ensure summary_text is not empty
        if not summary_text or not summary_text.strip():
            summary_text = self._create_fallback_summary(messages)

        return summary_text, metadata

    def _create_fallback_summary(self, messages: list[ConversationMessageOutput]) -> str:
        """Create a fallback summary when LLM is unavailable."""
        if not messages:
            return "No messages to summarize."

        user_count = len([m for m in messages if m.role.value == "user"])
        assistant_count = len([m for m in messages if m.role.value == "assistant"])

        first_msg = messages[0].content[:100] + "..." if len(messages[0].content) > 100 else messages[0].content
        last_msg = messages[-1].content[:100] + "..." if len(messages[-1].content) > 100 else messages[-1].content

        return f"""Conversation Summary (Fallback):
- Total messages: {len(messages)} ({user_count} user, {assistant_count} assistant)
- Started with: {first_msg}
- Ended with: {last_msg}
- Time span: {messages[0].created_at} to {messages[-1].created_at}"""

    async def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Simple estimation: ~4 characters per token for English text
        return len(text) // 4
