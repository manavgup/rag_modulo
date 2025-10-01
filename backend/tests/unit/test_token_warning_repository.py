"""Unit tests for TokenWarningRepository."""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError
from rag_solution.models.token_warning import TokenWarning
from rag_solution.repository.token_warning_repository import TokenWarningRepository
from rag_solution.schemas.llm_usage_schema import TokenWarning as TokenWarningSchema
from rag_solution.schemas.llm_usage_schema import TokenWarningType


@pytest.mark.unit
class TestTokenWarningRepository:
    """Unit tests for TokenWarningRepository."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def repository(self, mock_db):
        """Create repository instance with mocked database."""
        return TokenWarningRepository(mock_db)

    @pytest.fixture
    def sample_warning_schema(self):
        """Sample token warning schema."""
        return TokenWarningSchema(
            warning_type=TokenWarningType.APPROACHING_LIMIT,
            current_tokens=800,
            limit_tokens=1000,
            percentage_used=80.0,
            message="Approaching token limit",
            severity="warning",
            suggested_action="consider_new_session",
        )

    @pytest.fixture
    def sample_warning_model(self):
        """Sample token warning model."""
        warning = TokenWarning(
            id=uuid4(),
            user_id=uuid4(),
            session_id="test-session",
            warning_type="approaching_limit",
            current_tokens=800,
            limit_tokens=1000,
            percentage_used=80.0,
            message="Approaching token limit",
            severity="warning",
            suggested_action="consider_new_session",
            created_at=datetime.utcnow(),
        )
        return warning

    def test_create_warning_success(self, repository, mock_db, sample_warning_schema):
        """Test successful warning creation."""
        user_id = uuid4()
        session_id = "test-session"

        # Mock successful database operations
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Act
        result = repository.create(sample_warning_schema, user_id, session_id)

        # Assert
        assert isinstance(result, TokenWarning)
        assert result.user_id == user_id
        assert result.session_id == session_id
        assert result.warning_type == sample_warning_schema.warning_type.value
        assert result.current_tokens == sample_warning_schema.current_tokens
        assert result.limit_tokens == sample_warning_schema.limit_tokens
        assert result.percentage_used == sample_warning_schema.percentage_used
        assert result.message == sample_warning_schema.message
        assert result.severity == sample_warning_schema.severity
        assert result.suggested_action == sample_warning_schema.suggested_action

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_warning_integrity_error(self, repository, mock_db, sample_warning_schema):
        """Test warning creation with integrity error."""
        user_id = uuid4()
        session_id = "test-session"

        # Mock integrity error
        mock_db.add.side_effect = IntegrityError("statement", "params", "orig")
        mock_db.rollback.return_value = None

        # Act & Assert
        with pytest.raises(AlreadyExistsError):
            repository.create(sample_warning_schema, user_id, session_id)

        mock_db.rollback.assert_called_once()

    def test_create_warning_general_error(self, repository, mock_db, sample_warning_schema):
        """Test warning creation with general error."""
        user_id = uuid4()
        session_id = "test-session"

        # Mock general error
        mock_db.add.side_effect = Exception("Database error")
        mock_db.rollback.return_value = None

        # Act & Assert
        with pytest.raises(Exception, match="Failed to create token warning"):
            repository.create(sample_warning_schema, user_id, session_id)

        mock_db.rollback.assert_called_once()

    def test_get_by_id_success(self, repository, mock_db, sample_warning_model):
        """Test successful warning retrieval by ID."""
        warning_id = sample_warning_model.id

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_warning_model
        mock_db.query.return_value = mock_query

        # Act
        result = repository.get_by_id(warning_id)

        # Assert
        assert result == sample_warning_model
        mock_db.query.assert_called_once_with(TokenWarning)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.first.assert_called_once()

    def test_get_by_id_not_found(self, repository, mock_db):
        """Test warning retrieval when not found."""
        warning_id = uuid4()

        # Mock database query returning None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.get_by_id(warning_id)

    def test_get_warnings_by_user(self, repository, mock_db, sample_warning_model):
        """Test retrieving warnings by user ID."""
        user_id = uuid4()
        warnings = [sample_warning_model]

        # Mock database query - set up the chain correctly
        mock_query = Mock()
        mock_filter1 = Mock()  # First filter for user_id
        mock_filter2 = Mock()  # Second filter for acknowledged
        mock_order_by = Mock()
        mock_limit = Mock()
        mock_offset = Mock()

        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.offset.return_value = mock_offset
        mock_offset.all.return_value = warnings

        # Act
        result = repository.get_warnings_by_user(user_id, limit=50, offset=0, acknowledged=False)

        # Assert
        assert result == warnings
        mock_db.query.assert_called_once_with(TokenWarning)

    def test_get_warnings_by_session(self, repository, mock_db, sample_warning_model):
        """Test retrieving warnings by session ID."""
        session_id = "test-session"
        warnings = [sample_warning_model]

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            warnings
        )
        mock_db.query.return_value = mock_query

        # Act
        result = repository.get_warnings_by_session(session_id, limit=20, offset=0)

        # Assert
        assert result == warnings
        mock_db.query.assert_called_once_with(TokenWarning)

    def test_get_recent_warnings(self, repository, mock_db, sample_warning_model):
        """Test retrieving recent warnings."""
        warnings = [sample_warning_model]

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = warnings
        mock_db.query.return_value = mock_query

        # Act
        result = repository.get_recent_warnings(limit=100, severity="warning")

        # Assert
        assert result == warnings
        mock_db.query.assert_called_once_with(TokenWarning)

    def test_acknowledge_warning_success(self, repository, mock_db, sample_warning_model):
        """Test successful warning acknowledgment."""
        warning_id = sample_warning_model.id

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_warning_model
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Act
        result = repository.acknowledge_warning(warning_id)

        # Assert
        assert result == sample_warning_model
        assert sample_warning_model.acknowledged_at is not None
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_acknowledge_warning_not_found(self, repository, mock_db):
        """Test acknowledging non-existent warning."""
        warning_id = uuid4()

        # Mock database query returning None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.acknowledge_warning(warning_id)

    def test_delete_warning_success(self, repository, mock_db, sample_warning_model):
        """Test successful warning deletion."""
        warning_id = sample_warning_model.id

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_warning_model
        mock_db.query.return_value = mock_query
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        # Act
        result = repository.delete(warning_id)

        # Assert
        assert result is True
        mock_db.delete.assert_called_once_with(sample_warning_model)
        mock_db.commit.assert_called_once()

    def test_delete_warning_not_found(self, repository, mock_db):
        """Test deleting non-existent warning."""
        warning_id = uuid4()

        # Mock database query returning None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.delete(warning_id)

    def test_delete_warnings_by_user(self, repository, mock_db):
        """Test deleting all warnings for a user."""
        user_id = uuid4()
        deleted_count = 5

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = deleted_count
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None

        # Act
        result = repository.delete_warnings_by_user(user_id)

        # Assert
        assert result == deleted_count
        mock_db.query.assert_called_once_with(TokenWarning)
        mock_db.commit.assert_called_once()

    @patch("sqlalchemy.func")
    def test_get_warning_stats_by_user(self, _mock_func, repository, mock_db):
        """Test retrieving warning statistics for a user."""
        user_id = uuid4()

        # Mock statistics result
        mock_stats = Mock()
        mock_stats.total_warnings = 10
        mock_stats.acknowledged_warnings = 7
        mock_stats.critical_warnings = 2
        mock_stats.warning_warnings = 5
        mock_stats.info_warnings = 3

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_stats
        mock_db.query.return_value = mock_query

        # Act
        result = repository.get_warning_stats_by_user(user_id)

        # Assert
        assert result["total_warnings"] == 10
        assert result["acknowledged_warnings"] == 7
        assert result["unacknowledged_warnings"] == 3
        assert result["critical_warnings"] == 2
        assert result["warning_warnings"] == 5
        assert result["info_warnings"] == 3
        mock_db.query.assert_called_once()
