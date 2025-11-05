from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from rag_solution.schemas.conversation_schema import SummarizationConfigInput
from rag_solution.services.conversation_summarization_service import ConversationSummarizationService


@pytest.fixture
def db_session():
    return MagicMock()

@pytest.fixture
def settings():
    return MagicMock()

@pytest.fixture
def conversation_repository():
    """Mock unified conversation repository."""
    return MagicMock()

@pytest.fixture
def llm_provider_service():
    """Mock LLM provider service."""
    return MagicMock()

@pytest.fixture
def token_tracking_service():
    """Mock token tracking service."""
    return MagicMock()

@pytest.fixture
def conversation_summarization_service(
    db_session, settings, conversation_repository, llm_provider_service, token_tracking_service
):
    """Create ConversationSummarizationService with injected dependencies."""
    service = ConversationSummarizationService(
        db_session, settings, conversation_repository, llm_provider_service, token_tracking_service
    )
    return service

@pytest.mark.asyncio
async def test_check_context_window_threshold_below_threshold(conversation_summarization_service):
    session_id = uuid4()
    config = SummarizationConfigInput(min_messages_for_summary=5, context_window_threshold=0.8)

    mock_session = MagicMock()
    mock_session.context_window_size = 1000
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    mock_messages = [MagicMock(token_count=100) for _ in range(5)]
    conversation_summarization_service.repository.get_messages_by_session.return_value = mock_messages

    result = await conversation_summarization_service.check_context_window_threshold(session_id, config)

    assert result is False

@pytest.mark.asyncio
async def test_check_context_window_threshold_above_threshold(conversation_summarization_service):
    session_id = uuid4()
    config = SummarizationConfigInput(min_messages_for_summary=5, context_window_threshold=0.8)

    mock_session = MagicMock()
    mock_session.context_window_size = 1000
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    mock_messages = [MagicMock(token_count=200) for _ in range(5)]
    conversation_summarization_service.repository.get_messages_by_session.return_value = mock_messages

    result = await conversation_summarization_service.check_context_window_threshold(session_id, config)

    assert result is True

@pytest.mark.asyncio
async def test_get_session_summaries(conversation_summarization_service):
    session_id = uuid4()
    user_id = uuid4()

    mock_session = MagicMock()
    mock_session.user_id = user_id
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    mock_summaries = [MagicMock(), MagicMock()]
    conversation_summarization_service.repository.get_summaries_by_session.return_value = mock_summaries

    result = await conversation_summarization_service.get_session_summaries(session_id, user_id)

    assert result == mock_summaries


# ============================================================================
# CONTEXT WINDOW CHECKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_check_context_window_threshold_exactly_at_threshold(conversation_summarization_service):
    """Test context window exactly at threshold"""
    session_id = uuid4()
    config = SummarizationConfigInput(min_messages_for_summary=5, context_window_threshold=0.8)

    mock_session = MagicMock()
    mock_session.context_window_size = 1000
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    # Exactly 800 tokens = 0.8 threshold
    mock_messages = [MagicMock(token_count=160) for _ in range(5)]
    conversation_summarization_service.repository.get_messages_by_session.return_value = mock_messages

    result = await conversation_summarization_service.check_context_window_threshold(session_id, config)

    assert result is True


@pytest.mark.asyncio
async def test_check_context_window_threshold_insufficient_messages(conversation_summarization_service):
    """Test context window check with fewer than minimum messages"""
    session_id = uuid4()
    config = SummarizationConfigInput(min_messages_for_summary=10, context_window_threshold=0.8)

    mock_session = MagicMock()
    mock_session.context_window_size = 1000
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    # Only 5 messages when min is 10
    mock_messages = [MagicMock(token_count=200) for _ in range(5)]
    conversation_summarization_service.repository.get_messages_by_session.return_value = mock_messages

    result = await conversation_summarization_service.check_context_window_threshold(session_id, config)

    assert result is False


@pytest.mark.asyncio
async def test_check_context_window_threshold_exception_handling(conversation_summarization_service):
    """Test context window check handles exceptions gracefully"""
    session_id = uuid4()
    config = SummarizationConfigInput()

    conversation_summarization_service.repository.get_session_by_id.side_effect = Exception("Database error")

    result = await conversation_summarization_service.check_context_window_threshold(session_id, config)

    assert result is False


@pytest.mark.asyncio
async def test_check_context_window_threshold_with_none_tokens(conversation_summarization_service):
    """Test context window check with messages having None token counts"""
    session_id = uuid4()
    config = SummarizationConfigInput(min_messages_for_summary=5, context_window_threshold=0.8)

    mock_session = MagicMock()
    mock_session.context_window_size = 1000
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    mock_messages = [MagicMock(token_count=None) for _ in range(10)]
    conversation_summarization_service.repository.get_messages_by_session.return_value = mock_messages

    result = await conversation_summarization_service.check_context_window_threshold(session_id, config)

    # Should handle None tokens as 0, resulting in 0% usage
    assert result is False


# ============================================================================
# SUMMARY CREATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_summary_success(conversation_summarization_service):
    """Test successful summary creation"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import ConversationSummaryInput

    session_id = uuid4()
    user_id = uuid4()
    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=5,
    )

    # Mock session
    mock_session = MagicMock()
    mock_session.user_id = user_id
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    # Mock messages
    mock_messages = []
    for i in range(5):
        msg = MagicMock()
        msg.role.value = "user" if i % 2 == 0 else "assistant"
        msg.content = f"Message {i}"
        msg.created_at = datetime.utcnow()
        mock_messages.append(msg)
    conversation_summarization_service.repository.get_messages_by_session.return_value = mock_messages

    # Mock summary creation
    mock_summary = MagicMock()
    mock_summary.id = uuid4()
    conversation_summarization_service.repository.create_summary.return_value = mock_summary

    # Mock LLM provider
    mock_provider_config = MagicMock()
    mock_provider_config.name = "openai"
    conversation_summarization_service.llm_provider_service.get_default_provider = MagicMock(return_value=mock_provider_config)

    # Mock updated summary
    mock_updated_summary = MagicMock()
    conversation_summarization_service.repository.update_summary.return_value = mock_updated_summary

    # Mock _generate_summary_content
    conversation_summarization_service._generate_summary_content = AsyncMock(
        return_value=("Test summary text", {"key_topics": ["topic1"], "tokens_saved": 100})
    )

    result = await conversation_summarization_service.create_summary(summary_input, user_id)

    assert result == mock_updated_summary
    conversation_summarization_service.repository.create_summary.assert_called_once_with(summary_input)


@pytest.mark.asyncio
async def test_create_summary_user_access_denied(conversation_summarization_service):
    """Test summary creation with unauthorized user"""
    from rag_solution.core.exceptions import ValidationError
    from rag_solution.schemas.conversation_schema import ConversationSummaryInput

    session_id = uuid4()
    user_id = uuid4()
    other_user_id = uuid4()

    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=5,
    )

    mock_session = MagicMock()
    mock_session.user_id = other_user_id  # Different user
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    with pytest.raises(ValidationError, match="User does not have access"):
        await conversation_summarization_service.create_summary(summary_input, user_id)


@pytest.mark.asyncio
async def test_create_summary_no_messages(conversation_summarization_service):
    """Test summary creation with no messages"""
    from rag_solution.core.exceptions import ValidationError
    from rag_solution.schemas.conversation_schema import ConversationSummaryInput

    session_id = uuid4()
    user_id = uuid4()
    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=5,
    )

    mock_session = MagicMock()
    mock_session.user_id = user_id
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    conversation_summarization_service.repository.get_messages_by_session.return_value = []

    with pytest.raises(ValidationError, match="No messages found"):
        await conversation_summarization_service.create_summary(summary_input, user_id)


@pytest.mark.asyncio
async def test_create_summary_session_not_found(conversation_summarization_service):
    """Test summary creation with non-existent session"""
    from rag_solution.core.exceptions import NotFoundError
    from rag_solution.schemas.conversation_schema import ConversationSummaryInput

    session_id = uuid4()
    user_id = uuid4()
    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=5,
    )

    conversation_summarization_service.repository.get_session_by_id.side_effect = NotFoundError("Session not found")

    with pytest.raises(NotFoundError):
        await conversation_summarization_service.create_summary(summary_input, user_id)


# ============================================================================
# CONTEXT SUMMARIZATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_summarize_for_context_insufficient_messages(conversation_summarization_service):
    """Test context summarization with insufficient messages"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import (
        ContextSummarizationInput,
        ConversationMessageOutput,
        MessageRole,
        MessageType,
        SummarizationConfigInput,
    )

    session_id = uuid4()
    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="Test",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=10
        )
        for _ in range(3)
    ]

    config = SummarizationConfigInput(
        min_messages_for_summary=10,
        preserve_recent_messages=2
    )

    summarization_input = ContextSummarizationInput(
        session_id=session_id,
        messages=messages,
        config=config,
        current_context_size=30,
        target_context_size=500
    )

    result = await conversation_summarization_service.summarize_for_context_management(summarization_input)

    assert result.summary.summarized_message_count == 0
    assert result.compression_ratio == 0.0
    assert len(result.preserved_messages) == 3


@pytest.mark.asyncio
async def test_summarize_for_context_success(conversation_summarization_service):
    """Test successful context summarization"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import (
        ContextSummarizationInput,
        ConversationMessageOutput,
        MessageRole,
        MessageType,
        SummarizationConfigInput,
    )

    session_id = uuid4()
    user_id = uuid4()

    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content=f"Message {i}",
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=100
        )
        for i in range(15)
    ]

    config = SummarizationConfigInput(
        min_messages_for_summary=5,
        preserve_recent_messages=5
    )

    summarization_input = ContextSummarizationInput(
        session_id=session_id,
        messages=messages,
        config=config,
        current_context_size=1500,
        target_context_size=800
    )

    # Mock session
    mock_session = MagicMock()
    mock_session.user_id = user_id
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    # Mock _generate_summary_content
    conversation_summarization_service._generate_summary_content = AsyncMock(
        return_value=("Summary of 10 messages", {"key_topics": ["topic1"], "important_decisions": []})
    )

    result = await conversation_summarization_service.summarize_for_context_management(summarization_input)

    assert result.summary.summarized_message_count == 10
    assert len(result.preserved_messages) == 5
    assert result.tokens_saved >= 0


@pytest.mark.asyncio
async def test_summarize_for_context_preserve_all_messages(conversation_summarization_service):
    """Test context summarization when preserving all messages"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import (
        ContextSummarizationInput,
        ConversationMessageOutput,
        MessageRole,
        MessageType,
        SummarizationConfigInput,
    )

    session_id = uuid4()
    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content=f"Message {i}",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=50
        )
        for i in range(8)
    ]

    config = SummarizationConfigInput(
        min_messages_for_summary=5,
        preserve_recent_messages=10  # More than message count
    )

    summarization_input = ContextSummarizationInput(
        session_id=session_id,
        messages=messages,
        config=config,
        current_context_size=400,
        target_context_size=500
    )

    result = await conversation_summarization_service.summarize_for_context_management(summarization_input)

    assert result.summary.summarized_message_count == 0
    assert len(result.preserved_messages) == 8


@pytest.mark.asyncio
async def test_summarize_for_context_exception_handling(conversation_summarization_service):
    """Test context summarization exception handling"""
    from datetime import datetime

    from rag_solution.core.exceptions import ValidationError
    from rag_solution.schemas.conversation_schema import (
        ContextSummarizationInput,
        ConversationMessageOutput,
        MessageRole,
        MessageType,
        SummarizationConfigInput,
    )

    session_id = uuid4()
    user_id = uuid4()

    # Create enough messages to trigger summarization
    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content=f"Test {i}",
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=100
        )
        for i in range(15)
    ]

    config = SummarizationConfigInput(
        min_messages_for_summary=5,
        preserve_recent_messages=5
    )

    summarization_input = ContextSummarizationInput(
        session_id=session_id,
        messages=messages,
        config=config,
        current_context_size=1500,
        target_context_size=800
    )

    # Mock session first, then fail on generate_summary_content
    mock_session = MagicMock()
    mock_session.user_id = user_id
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    # Cause failure during _generate_summary_content
    conversation_summarization_service._generate_summary_content = AsyncMock(side_effect=Exception("LLM error"))

    with pytest.raises(ValidationError, match="Failed to summarize"):
        await conversation_summarization_service.summarize_for_context_management(summarization_input)


# ============================================================================
# GET SESSION SUMMARIES TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_session_summaries_with_limit(conversation_summarization_service):
    """Test getting session summaries with custom limit"""
    session_id = uuid4()
    user_id = uuid4()

    mock_session = MagicMock()
    mock_session.user_id = user_id
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    mock_summaries = [MagicMock() for _ in range(5)]
    conversation_summarization_service.repository.get_summaries_by_session.return_value = mock_summaries

    result = await conversation_summarization_service.get_session_summaries(session_id, user_id, limit=5)

    assert len(result) == 5
    conversation_summarization_service.repository.get_summaries_by_session.assert_called_once_with(session_id, limit=5)


@pytest.mark.asyncio
async def test_get_session_summaries_unauthorized(conversation_summarization_service):
    """Test getting session summaries for unauthorized user"""
    from rag_solution.core.exceptions import ValidationError

    session_id = uuid4()
    user_id = uuid4()
    other_user_id = uuid4()

    mock_session = MagicMock()
    mock_session.user_id = other_user_id
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    with pytest.raises(ValidationError, match="User does not have access"):
        await conversation_summarization_service.get_session_summaries(session_id, user_id)


@pytest.mark.asyncio
async def test_get_session_summaries_session_not_found(conversation_summarization_service):
    """Test getting summaries for non-existent session"""
    from rag_solution.core.exceptions import NotFoundError

    session_id = uuid4()
    user_id = uuid4()

    conversation_summarization_service.repository.get_session_by_id.side_effect = NotFoundError("Session not found")

    with pytest.raises(NotFoundError):
        await conversation_summarization_service.get_session_summaries(session_id, user_id)


@pytest.mark.asyncio
async def test_get_session_summaries_exception_handling(conversation_summarization_service):
    """Test get session summaries exception handling"""
    from rag_solution.core.exceptions import ValidationError

    session_id = uuid4()
    user_id = uuid4()

    mock_session = MagicMock()
    mock_session.user_id = user_id
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    conversation_summarization_service.repository.get_summaries_by_session.side_effect = Exception("Database error")

    with pytest.raises(ValidationError, match="Failed to get session summaries"):
        await conversation_summarization_service.get_session_summaries(session_id, user_id)


# ============================================================================
# SUMMARY GENERATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_generate_summary_content_success(conversation_summarization_service):
    """Test successful summary content generation"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import (
        ConversationMessageOutput,
        ConversationSummaryInput,
        MessageRole,
        MessageType,
    )

    session_id = uuid4()
    user_id = uuid4()

    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content=f"Message {i}",
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=50
        )
        for i in range(5)
    ]

    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=5,
    )

    # Mock LLM provider
    mock_provider_config = MagicMock()
    mock_provider_config.name = "openai"
    conversation_summarization_service.llm_provider_service.get_default_provider = MagicMock(return_value=mock_provider_config)

    # Mock factory and provider
    mock_provider = AsyncMock()
    mock_provider.generate_text_with_usage = AsyncMock(
        return_value=("This is a test summary", {"tokens": 10})
    )

    with patch("rag_solution.generation.providers.factory.LLMProviderFactory") as mock_factory:
        mock_factory.return_value.get_provider.return_value = mock_provider

        summary_text, metadata = await conversation_summarization_service._generate_summary_content(
            messages, summary_input, user_id
        )

        assert summary_text == "This is a test summary"
        assert "generation_method" in metadata


@pytest.mark.asyncio
async def test_generate_summary_content_empty_llm_response(conversation_summarization_service):
    """Test summary generation with empty LLM response"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import (
        ConversationMessageOutput,
        ConversationSummaryInput,
        MessageRole,
        MessageType,
    )

    session_id = uuid4()
    user_id = uuid4()

    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="Test message",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=10
        )
    ]

    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=1,
    )

    # Mock LLM provider returning empty response
    mock_provider_config = MagicMock()
    mock_provider_config.name = "openai"
    conversation_summarization_service.llm_provider_service.get_default_provider = MagicMock(return_value=mock_provider_config)

    mock_provider = AsyncMock()
    mock_provider.generate_text_with_usage = AsyncMock(return_value=("", {}))

    with patch("rag_solution.generation.providers.factory.LLMProviderFactory") as mock_factory:
        mock_factory.return_value.get_provider.return_value = mock_provider

        summary_text, metadata = await conversation_summarization_service._generate_summary_content(
            messages, summary_input, user_id
        )

        # Should fall back to fallback summary
        assert len(summary_text) > 0
        assert metadata.get("fallback") is True


@pytest.mark.asyncio
async def test_generate_summary_content_no_provider(conversation_summarization_service):
    """Test summary generation with no LLM provider"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import (
        ConversationMessageOutput,
        ConversationSummaryInput,
        MessageRole,
        MessageType,
    )

    session_id = uuid4()
    user_id = uuid4()

    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="Test",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=10
        )
    ]

    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=1,
    )

    conversation_summarization_service.llm_provider_service.get_default_provider = MagicMock(return_value=None)

    summary_text, metadata = await conversation_summarization_service._generate_summary_content(
        messages, summary_input, user_id
    )

    # Should use fallback
    assert len(summary_text) > 0
    assert metadata.get("fallback") is True


@pytest.mark.asyncio
async def test_generate_summary_content_llm_exception(conversation_summarization_service):
    """Test summary generation with LLM exception"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import (
        ConversationMessageOutput,
        ConversationSummaryInput,
        MessageRole,
        MessageType,
    )

    session_id = uuid4()
    user_id = uuid4()

    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="Test",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=10
        )
    ]

    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=1,
    )

    mock_provider_config = MagicMock()
    mock_provider_config.name = "openai"
    conversation_summarization_service.llm_provider_service.get_default_provider = MagicMock(return_value=mock_provider_config)

    mock_provider = AsyncMock()
    mock_provider.generate_text_with_usage = AsyncMock(side_effect=Exception("LLM error"))

    with patch("rag_solution.generation.providers.factory.LLMProviderFactory") as mock_factory:
        mock_factory.return_value.get_provider.return_value = mock_provider

        summary_text, metadata = await conversation_summarization_service._generate_summary_content(
            messages, summary_input, user_id
        )

        assert len(summary_text) > 0
        assert metadata.get("fallback") is True
        assert "error" in metadata


# ============================================================================
# HELPER METHOD TESTS
# ============================================================================

def test_build_conversation_text(conversation_summarization_service):
    """Test building conversation text from messages"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import ConversationMessageOutput, MessageRole, MessageType

    session_id = uuid4()
    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="Hello",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            token_count=5
        ),
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="Hi there",
            role=MessageRole.ASSISTANT,
            message_type=MessageType.ANSWER,
            created_at=datetime(2024, 1, 1, 10, 0, 5),
            token_count=5
        )
    ]

    result = conversation_summarization_service._build_conversation_text(messages)

    assert "USER: Hello" in result
    assert "ASSISTANT: Hi there" in result
    assert "2024-01-01 10:00:00" in result


def test_build_conversation_text_empty(conversation_summarization_service):
    """Test building conversation text with empty messages"""
    result = conversation_summarization_service._build_conversation_text([])
    assert result == ""


def test_create_summarization_prompt_recent_plus_summary(conversation_summarization_service):
    """Test creating summarization prompt with RECENT_PLUS_SUMMARY strategy"""
    from rag_solution.schemas.conversation_schema import ConversationSummaryInput, SummarizationStrategy

    session_id = uuid4()
    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=5,
        strategy=SummarizationStrategy.RECENT_PLUS_SUMMARY,
        include_decisions=True,
        include_questions=True
    )

    conversation_text = "USER: Hello\nASSISTANT: Hi"
    result = conversation_summarization_service._create_summarization_prompt(conversation_text, summary_input)

    assert "recent interactions" in result.lower()
    assert conversation_text in result
    assert "Important decisions" in result


def test_create_summarization_prompt_full_conversation(conversation_summarization_service):
    """Test creating summarization prompt with FULL_CONVERSATION strategy"""
    from rag_solution.schemas.conversation_schema import ConversationSummaryInput, SummarizationStrategy

    session_id = uuid4()
    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=5,
        strategy=SummarizationStrategy.FULL_CONVERSATION,
        include_decisions=False,
        include_questions=False
    )

    result = conversation_summarization_service._create_summarization_prompt("test", summary_input)

    assert "comprehensive summary" in result.lower()


def test_create_summarization_prompt_key_points(conversation_summarization_service):
    """Test creating summarization prompt with KEY_POINTS_ONLY strategy"""
    from rag_solution.schemas.conversation_schema import ConversationSummaryInput, SummarizationStrategy

    session_id = uuid4()
    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=5,
        strategy=SummarizationStrategy.KEY_POINTS_ONLY
    )

    result = conversation_summarization_service._create_summarization_prompt("test", summary_input)

    assert "key points" in result.lower()


def test_create_summarization_prompt_topic_based(conversation_summarization_service):
    """Test creating summarization prompt with TOPIC_BASED strategy"""
    from rag_solution.schemas.conversation_schema import ConversationSummaryInput, SummarizationStrategy

    session_id = uuid4()
    summary_input = ConversationSummaryInput(
        session_id=session_id,
        message_count_to_summarize=5,
        strategy=SummarizationStrategy.TOPIC_BASED
    )

    result = conversation_summarization_service._create_summarization_prompt("test", summary_input)

    assert "topics" in result.lower()


def test_parse_summary_response_with_structured_data(conversation_summarization_service):
    """Test parsing LLM response with structured sections"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import ConversationMessageOutput, MessageRole, MessageType

    response = """Summary of the conversation.

Key Topics:
- Machine learning
- Data processing
- Model training

Important Decisions:
- Use Python for implementation
- Deploy on AWS

Unresolved Questions:
- What is the budget?
- When is the deadline?"""

    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=uuid4(),
            content="Test",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=10
        )
    ]

    summary_text, metadata = conversation_summarization_service._parse_summary_response(response, messages)

    assert len(summary_text) > 0
    assert "Machine learning" in metadata["key_topics"]
    assert "Use Python for implementation" in metadata["important_decisions"]
    assert "What is the budget?" in metadata["unresolved_questions"]


def test_parse_summary_response_empty(conversation_summarization_service):
    """Test parsing empty LLM response"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import ConversationMessageOutput, MessageRole, MessageType

    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=uuid4(),
            content="Test",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=10
        )
    ]

    summary_text, metadata = conversation_summarization_service._parse_summary_response("", messages)

    # Should fall back to fallback summary
    assert len(summary_text) > 0
    assert "Conversation Summary (Fallback)" in summary_text


def test_create_fallback_summary(conversation_summarization_service):
    """Test creating fallback summary"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import ConversationMessageOutput, MessageRole, MessageType

    session_id = uuid4()
    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="First message" * 20,
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            token_count=50
        ),
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="Last message",
            role=MessageRole.ASSISTANT,
            message_type=MessageType.ANSWER,
            created_at=datetime(2024, 1, 1, 11, 0, 0),
            token_count=30
        )
    ]

    result = conversation_summarization_service._create_fallback_summary(messages)

    assert "1 user, 1 assistant" in result
    assert "Total messages: 2" in result


def test_create_fallback_summary_empty(conversation_summarization_service):
    """Test creating fallback summary with empty messages"""
    result = conversation_summarization_service._create_fallback_summary([])
    assert result == "No messages to summarize."


def test_create_fallback_summary_long_content(conversation_summarization_service):
    """Test fallback summary truncates long messages"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import ConversationMessageOutput, MessageRole, MessageType

    long_content = "A" * 200
    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=uuid4(),
            content=long_content,
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=100
        )
    ]

    result = conversation_summarization_service._create_fallback_summary(messages)

    assert "..." in result  # Should be truncated


@pytest.mark.asyncio
async def test_estimate_tokens(conversation_summarization_service):
    """Test token estimation"""
    text = "This is a test message with approximately twenty characters"
    result = await conversation_summarization_service._estimate_tokens(text)

    # Should estimate ~4 characters per token
    expected = len(text) // 4
    assert result == expected


@pytest.mark.asyncio
async def test_estimate_tokens_empty(conversation_summarization_service):
    """Test token estimation with empty text"""
    result = await conversation_summarization_service._estimate_tokens("")
    assert result == 0


# ============================================================================
# PROPERTY TESTS
# ============================================================================

def test_llm_provider_service_dependency_injection():
    """Test LLM provider service is properly injected via dependency injection"""
    from rag_solution.services.conversation_summarization_service import ConversationSummarizationService

    mock_db = MagicMock()
    mock_settings = MagicMock()
    mock_repository = MagicMock()
    mock_llm_service = MagicMock()
    mock_token_service = MagicMock()

    service = ConversationSummarizationService(
        mock_db, mock_settings, mock_repository, mock_llm_service, mock_token_service
    )

    assert service.llm_provider_service == mock_llm_service


def test_token_tracking_service_dependency_injection():
    """Test token tracking service is properly injected via dependency injection"""
    from rag_solution.services.conversation_summarization_service import ConversationSummarizationService

    mock_db = MagicMock()
    mock_settings = MagicMock()
    mock_repository = MagicMock()
    mock_llm_service = MagicMock()
    mock_token_service = MagicMock()

    service = ConversationSummarizationService(
        mock_db, mock_settings, mock_repository, mock_llm_service, mock_token_service
    )

    assert service.token_tracking_service == mock_token_service


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_large_conversation_within_limits(conversation_summarization_service):
    """Test handling large conversations within validation limits (100 messages max)"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import (
        ContextSummarizationInput,
        ConversationMessageOutput,
        MessageRole,
        MessageType,
        SummarizationConfigInput,
    )

    session_id = uuid4()
    user_id = uuid4()

    # Create 100 messages (maximum allowed)
    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content=f"Message {i}",
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=50
        )
        for i in range(100)
    ]

    config = SummarizationConfigInput(
        min_messages_for_summary=5,
        preserve_recent_messages=10
    )

    summarization_input = ContextSummarizationInput(
        session_id=session_id,
        messages=messages,
        config=config,
        current_context_size=5000,
        target_context_size=2000
    )

    mock_session = MagicMock()
    mock_session.user_id = user_id
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    conversation_summarization_service._generate_summary_content = AsyncMock(
        return_value=("Summary of 90 messages", {"key_topics": []})
    )

    result = await conversation_summarization_service.summarize_for_context_management(summarization_input)

    assert result.summary.summarized_message_count == 90
    assert len(result.preserved_messages) == 10


@pytest.mark.asyncio
async def test_mixed_role_messages(conversation_summarization_service):
    """Test summarization with mixed message roles"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import ConversationMessageOutput, MessageRole, MessageType

    session_id = uuid4()
    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="User message",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=10
        ),
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="Assistant message",
            role=MessageRole.ASSISTANT,
            message_type=MessageType.ANSWER,
            created_at=datetime.utcnow(),
            token_count=10
        ),
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="System message",
            role=MessageRole.SYSTEM,
            message_type=MessageType.SYSTEM,
            created_at=datetime.utcnow(),
            token_count=10
        )
    ]

    result = conversation_summarization_service._create_fallback_summary(messages)

    assert "Total messages: 3" in result


@pytest.mark.asyncio
async def test_zero_token_messages(conversation_summarization_service):
    """Test handling messages with zero tokens"""
    from datetime import datetime

    from rag_solution.schemas.conversation_schema import (
        ContextSummarizationInput,
        ConversationMessageOutput,
        MessageRole,
        MessageType,
        SummarizationConfigInput,
    )

    session_id = uuid4()
    user_id = uuid4()

    messages = [
        ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            created_at=datetime.utcnow(),
            token_count=0
        )
        for _ in range(10)
    ]

    config = SummarizationConfigInput(
        min_messages_for_summary=5,
        preserve_recent_messages=3
    )

    summarization_input = ContextSummarizationInput(
        session_id=session_id,
        messages=messages,
        config=config,
        current_context_size=0,
        target_context_size=500
    )

    mock_session = MagicMock()
    mock_session.user_id = user_id
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    conversation_summarization_service._generate_summary_content = AsyncMock(
        return_value=("Empty summary", {"key_topics": []})
    )

    result = await conversation_summarization_service.summarize_for_context_management(summarization_input)

    assert result.tokens_saved == 0  # No tokens to save


@pytest.mark.asyncio
async def test_context_window_at_exact_minimum(conversation_summarization_service):
    """Test context window check at exact minimum message count"""
    session_id = uuid4()
    config = SummarizationConfigInput(min_messages_for_summary=5, context_window_threshold=0.8)

    mock_session = MagicMock()
    mock_session.context_window_size = 1000
    conversation_summarization_service.repository.get_session_by_id.return_value = mock_session

    # Exactly 5 messages (minimum)
    mock_messages = [MagicMock(token_count=200) for _ in range(5)]
    conversation_summarization_service.repository.get_messages_by_session.return_value = mock_messages

    result = await conversation_summarization_service.check_context_window_threshold(session_id, config)

    # 5 messages * 200 tokens = 1000 tokens = 100% usage > 80% threshold
    assert result is True


@pytest.mark.asyncio
async def test_summarization_with_all_strategies(conversation_summarization_service):
    """Test summarization with all strategy types"""
    from rag_solution.schemas.conversation_schema import ConversationSummaryInput, SummarizationStrategy

    session_id = uuid4()
    strategies = [
        SummarizationStrategy.RECENT_PLUS_SUMMARY,
        SummarizationStrategy.FULL_CONVERSATION,
        SummarizationStrategy.KEY_POINTS_ONLY,
        SummarizationStrategy.TOPIC_BASED
    ]

    for strategy in strategies:
        summary_input = ConversationSummaryInput(
            session_id=session_id,
            message_count_to_summarize=5,
            strategy=strategy
        )

        prompt = conversation_summarization_service._create_summarization_prompt("test", summary_input)
        assert len(prompt) > 0
