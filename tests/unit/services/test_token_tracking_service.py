"""Unit tests for TokenTrackingService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from rag_solution.schemas.llm_usage_schema import (
    LLMUsage,
    ServiceType,
    TokenUsageStats,
    TokenWarning,
    TokenWarningType,
)
from rag_solution.services.token_tracking_service import TokenTrackingService


class TestTokenTrackingService:
    """Test cases for TokenTrackingService."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings."""
        settings = Mock()
        settings.llm_provider = "openai"
        return settings

    @pytest.fixture
    def service(self, mock_db: Mock, mock_settings: Mock) -> TokenTrackingService:
        """Create a TokenTrackingService instance with mocked dependencies."""
        service = TokenTrackingService(mock_db, mock_settings)
        # Mock the repository
        service.token_warning_repository = Mock()
        return service

    @pytest.fixture
    def sample_llm_usage(self) -> LLMUsage:
        """Create sample LLM usage."""
        return LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name="test-model",
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200,
            timestamp=datetime.now(UTC)
        )

    @pytest.fixture
    def sample_model(self) -> Mock:
        """Create sample model."""
        model = Mock()
        model.context_window = 4096
        return model

    def test_init(self, mock_db: Mock, mock_settings: Mock) -> None:
        """Test TokenTrackingService initialization."""
        service = TokenTrackingService(mock_db, mock_settings)
        assert service.db == mock_db
        assert service.settings == mock_settings
        assert service.token_warning_repository is not None

    def test_llm_model_service_lazy_initialization(self, service: TokenTrackingService) -> None:
        """Test lazy initialization of LLM model service."""
        # First access should create the service
        model_service = service.llm_model_service
        assert model_service is not None

        # Second access should return the same instance
        assert service.llm_model_service is model_service

    @pytest.mark.asyncio
    async def test_check_usage_warning_no_warning(self, service: TokenTrackingService, sample_llm_usage: LLMUsage) -> None:
        """Test check_usage_warning when no warning is needed."""
        # Mock the model service
        service._llm_model_service = Mock()
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=None)

        result = await service.check_usage_warning(sample_llm_usage)

        assert result is None

    @pytest.mark.asyncio
    async def test_check_usage_warning_uuid_model(self, service: TokenTrackingService, sample_model: Mock) -> None:
        """Test check_usage_warning with UUID model name."""
        # Mock the model service
        service._llm_model_service = Mock()
        sample_model.context_window = 4096
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=sample_model)

        # Create usage with UUID model name
        usage = LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name=str(uuid4()),
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200,
            timestamp=datetime.now(UTC)
        )

        result = await service.check_usage_warning(usage)

        assert result is None  # 1000/4096 = 24.4% - no warning

    @pytest.mark.asyncio
    async def test_check_usage_warning_string_model(self, service: TokenTrackingService) -> None:
        """Test check_usage_warning with string model name."""
        # Mock the model service
        service._llm_model_service = Mock()
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=None)

        # Create usage with string model name
        usage = LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name="ibm/granite-3-3-8b-instruct",
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200,
            timestamp=datetime.now(UTC)
        )

        result = await service.check_usage_warning(usage)

        assert result is None  # 1000/4096 = 24.4% - no warning

    @pytest.mark.asyncio
    async def test_check_usage_warning_70_percent(self, service: TokenTrackingService, sample_model: Mock) -> None:
        """Test check_usage_warning at 70% threshold."""
        # Mock the model service
        service._llm_model_service = Mock()
        sample_model.context_window = 4096
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=sample_model)

        # Create usage at 70% threshold (2867 tokens out of 4096)
        usage = LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name=str(uuid4()),
            prompt_tokens=2868,
            completion_tokens=200,
            total_tokens=3068,
            timestamp=datetime.now(UTC)
        )

        result = await service.check_usage_warning(usage)

        assert result is not None
        assert result.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert result.severity == "info"
        assert result.suggested_action is None

    @pytest.mark.asyncio
    async def test_check_usage_warning_85_percent(self, service: TokenTrackingService, sample_model: Mock) -> None:
        """Test check_usage_warning at 85% threshold."""
        # Mock the model service
        service._llm_model_service = Mock()
        sample_model.context_window = 4096
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=sample_model)

        # Create usage at 85% threshold (3482 tokens out of 4096)
        usage = LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name=str(uuid4()),
            prompt_tokens=3482,
            completion_tokens=200,
            total_tokens=3682,
            timestamp=datetime.now(UTC)
        )

        result = await service.check_usage_warning(usage)

        assert result is not None
        assert result.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert result.severity == "warning"
        assert result.suggested_action == "consider_new_session"

    @pytest.mark.asyncio
    async def test_check_usage_warning_95_percent(self, service: TokenTrackingService, sample_model: Mock) -> None:
        """Test check_usage_warning at 95% threshold."""
        # Mock the model service
        service._llm_model_service = Mock()
        sample_model.context_window = 4096
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=sample_model)

        # Create usage at 95% threshold (3891 tokens out of 4096)
        usage = LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name=str(uuid4()),
            prompt_tokens=3892,
            completion_tokens=200,
            total_tokens=4092,
            timestamp=datetime.now(UTC)
        )

        result = await service.check_usage_warning(usage)

        assert result is not None
        assert result.warning_type == TokenWarningType.AT_LIMIT
        assert result.severity == "critical"
        assert result.suggested_action == "start_new_session"

    @pytest.mark.asyncio
    async def test_check_usage_warning_over_100_percent(self, service: TokenTrackingService, sample_model: Mock) -> None:
        """Test check_usage_warning over 100% threshold."""
        # Mock the model service
        service._llm_model_service = Mock()
        sample_model.context_window = 4096
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=sample_model)

        # Create usage over 100% threshold
        usage = LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name=str(uuid4()),
            prompt_tokens=5000,
            completion_tokens=200,
            total_tokens=5200,
            timestamp=datetime.now(UTC)
        )

        result = await service.check_usage_warning(usage)

        assert result is not None
        assert result.warning_type == TokenWarningType.AT_LIMIT
        assert result.severity == "critical"
        assert result.percentage_used == 100.0  # Should be capped at 100%

    @pytest.mark.asyncio
    async def test_check_usage_warning_with_context_tokens(self, service: TokenTrackingService, sample_model: Mock) -> None:
        """Test check_usage_warning with context_tokens override."""
        # Mock the model service
        service._llm_model_service = Mock()
        sample_model.context_window = 4096
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=sample_model)

        usage = LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name=str(uuid4()),
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200,
            timestamp=datetime.now(UTC)
        )

        # Use context_tokens override
        result = await service.check_usage_warning(usage, context_tokens=3482)

        assert result is not None
        assert result.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert result.severity == "warning"

    @pytest.mark.asyncio
    async def test_check_conversation_warning_empty_history(self, service: TokenTrackingService) -> None:
        """Test check_conversation_warning with empty history."""
        result = await service.check_conversation_warning([], "test-model")
        assert result is None

    @pytest.mark.asyncio
    async def test_check_conversation_warning_no_model(self, service: TokenTrackingService) -> None:
        """Test check_conversation_warning when model is not found."""
        # Mock the model service
        service._llm_model_service = Mock()
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=None)

        usage_history = [LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name="test-model",
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200,
            timestamp=datetime.now(UTC)
        )]

        result = await service.check_conversation_warning(usage_history, str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_check_conversation_warning_under_threshold(self, service: TokenTrackingService, sample_model: Mock) -> None:
        """Test check_conversation_warning under threshold."""
        # Mock the model service
        service._llm_model_service = Mock()
        sample_model.context_window = 4096
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=sample_model)

        # Create usage history under 80% threshold
        usage_history = [LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name="test-model",
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200,
            timestamp=datetime.now(UTC)
        )] * 3  # 3000 total tokens

        result = await service.check_conversation_warning(usage_history, str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_check_conversation_warning_over_threshold(self, service: TokenTrackingService, sample_model: Mock) -> None:
        """Test check_conversation_warning over threshold."""
        # Mock the model service
        service._llm_model_service = Mock()
        sample_model.context_window = 4096
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=sample_model)

        # Create usage history over 80% threshold (3277 tokens out of 4096)
        usage_history = [LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name="test-model",
            prompt_tokens=1100,
            completion_tokens=200,
            total_tokens=1300,
            timestamp=datetime.now(UTC)
        )] * 3  # 3300 total tokens

        result = await service.check_conversation_warning(usage_history, str(uuid4()))

        assert result is not None
        assert result.warning_type == TokenWarningType.CONVERSATION_TOO_LONG
        assert result.severity == "warning"

    @pytest.mark.asyncio
    async def test_check_conversation_warning_critical_severity(self, service: TokenTrackingService, sample_model: Mock) -> None:
        """Test check_conversation_warning with critical severity."""
        # Mock the model service
        service._llm_model_service = Mock()
        sample_model.context_window = 4096
        service._llm_model_service.get_model_by_id = AsyncMock(return_value=sample_model)

        # Create usage history over 95% threshold
        usage_history = [LLMUsage(
            service_type=ServiceType.SEARCH,
            model_name="test-model",
            prompt_tokens=1500,
            completion_tokens=200,
            total_tokens=1700,
            timestamp=datetime.now(UTC)
        )] * 3  # 4500 total tokens

        result = await service.check_conversation_warning(usage_history, str(uuid4()))

        assert result is not None
        assert result.warning_type == TokenWarningType.CONVERSATION_TOO_LONG
        assert result.severity == "critical"

    @pytest.mark.asyncio
    async def test_store_warning(self, service: TokenTrackingService) -> None:
        """Test store_warning method."""
        warning = TokenWarning(
            warning_type=TokenWarningType.APPROACHING_LIMIT,
            current_tokens=1000,
            limit_tokens=4096,
            percentage_used=24.4,
            message="Test warning",
            severity="info"
        )

        user_id = uuid4()
        await service.store_warning(warning, user_id, "session-123")

        service.token_warning_repository.create.assert_called_once_with(warning, user_id, "session-123")

    @pytest.mark.asyncio
    async def test_get_user_warnings(self, service: TokenTrackingService) -> None:
        """Test get_user_warnings method."""
        # Mock repository response
        mock_warning = Mock()
        mock_warning.id = uuid4()
        mock_warning.warning_type = TokenWarningType.APPROACHING_LIMIT
        mock_warning.current_tokens = 1000
        mock_warning.limit_tokens = 4096
        mock_warning.percentage_used = 24.4
        mock_warning.message = "Test warning"
        mock_warning.severity = "info"
        mock_warning.suggested_action = None
        mock_warning.model_name = "test-model"
        mock_warning.service_type = "llm"
        mock_warning.created_at = datetime.now(UTC)
        mock_warning.acknowledged_at = None

        service.token_warning_repository.get_warnings_by_user.return_value = [mock_warning]

        result = await service.get_user_warnings(uuid4(), acknowledged=False, limit=10, offset=0)

        assert len(result) == 1
        assert result[0]["warning_type"] == TokenWarningType.APPROACHING_LIMIT
        service.token_warning_repository.get_warnings_by_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_warnings(self, service: TokenTrackingService) -> None:
        """Test get_session_warnings method."""
        # Mock repository response
        mock_warning = Mock()
        mock_warning.id = uuid4()
        mock_warning.warning_type = TokenWarningType.APPROACHING_LIMIT
        mock_warning.current_tokens = 1000
        mock_warning.limit_tokens = 4096
        mock_warning.percentage_used = 24.4
        mock_warning.message = "Test warning"
        mock_warning.severity = "info"
        mock_warning.suggested_action = None
        mock_warning.model_name = "test-model"
        mock_warning.service_type = "llm"
        mock_warning.created_at = datetime.now(UTC)
        mock_warning.acknowledged_at = None

        service.token_warning_repository.get_warnings_by_session.return_value = [mock_warning]

        result = await service.get_session_warnings("session-123", limit=10, offset=0)

        assert len(result) == 1
        assert result[0]["warning_type"] == TokenWarningType.APPROACHING_LIMIT
        service.token_warning_repository.get_warnings_by_session.assert_called_once_with("session-123", 10, 0)

    @pytest.mark.asyncio
    async def test_get_recent_warnings(self, service: TokenTrackingService) -> None:
        """Test get_recent_warnings method."""
        # Mock repository response
        mock_warning = Mock()
        mock_warning.id = uuid4()
        mock_warning.user_id = uuid4()
        mock_warning.session_id = "session-123"
        mock_warning.warning_type = TokenWarningType.APPROACHING_LIMIT
        mock_warning.current_tokens = 1000
        mock_warning.limit_tokens = 4096
        mock_warning.percentage_used = 24.4
        mock_warning.message = "Test warning"
        mock_warning.severity = "info"
        mock_warning.suggested_action = None
        mock_warning.model_name = "test-model"
        mock_warning.service_type = "llm"
        mock_warning.created_at = datetime.now(UTC)
        mock_warning.acknowledged_at = None

        service.token_warning_repository.get_recent_warnings.return_value = [mock_warning]

        result = await service.get_recent_warnings(limit=50, severity="info")

        assert len(result) == 1
        assert result[0]["warning_type"] == TokenWarningType.APPROACHING_LIMIT
        service.token_warning_repository.get_recent_warnings.assert_called_once_with(50, "info")

    @pytest.mark.asyncio
    async def test_acknowledge_warning(self, service: TokenTrackingService) -> None:
        """Test acknowledge_warning method."""
        warning_id = uuid4()
        mock_warning = Mock()
        service.token_warning_repository.acknowledge_warning.return_value = mock_warning

        result = await service.acknowledge_warning(warning_id)

        assert result == mock_warning
        service.token_warning_repository.acknowledge_warning.assert_called_once_with(warning_id)

    @pytest.mark.asyncio
    async def test_delete_warning(self, service: TokenTrackingService) -> None:
        """Test delete_warning method."""
        warning_id = uuid4()
        service.token_warning_repository.delete.return_value = True

        result = await service.delete_warning(warning_id)

        assert result is True
        service.token_warning_repository.delete.assert_called_once_with(warning_id)

    @pytest.mark.asyncio
    async def test_delete_user_warnings(self, service: TokenTrackingService) -> None:
        """Test delete_user_warnings method."""
        user_id = uuid4()
        service.token_warning_repository.delete_warnings_by_user.return_value = 5

        result = await service.delete_user_warnings(user_id)

        assert result == 5
        service.token_warning_repository.delete_warnings_by_user.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_user_token_stats(self, service: TokenTrackingService) -> None:
        """Test get_user_token_stats method."""
        user_id = uuid4()
        mock_stats = {
            "total_warnings": 10,
            "critical_warnings": 2,
            "warning_warnings": 5,
            "info_warnings": 3
        }
        service.token_warning_repository.get_warning_stats_by_user.return_value = mock_stats

        result = await service.get_user_token_stats(user_id)

        assert isinstance(result, TokenUsageStats)
        assert result.total_tokens == 0  # Default value
        assert result.total_calls == 0  # Default value
        assert result.by_service == {}  # Default value
        assert result.by_model == {}  # Default value
        service.token_warning_repository.get_warning_stats_by_user.assert_called_once_with(user_id)
