"""Unit tests for LLMParametersService.

This module provides comprehensive unit tests for the LLM Parameters Service,
covering CRUD operations, parameter validation, default handling, and error scenarios.
"""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from backend.core.custom_exceptions import NotFoundException
from backend.rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput
from backend.rag_solution.services.llm_parameters_service import LLMParametersService
from pydantic import UUID4, ValidationError


class TestLLMParametersService:
    """Test cases for LLMParametersService."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db: Mock) -> LLMParametersService:
        """Create an LLMParametersService instance with mocked dependencies."""
        service = LLMParametersService(mock_db)
        # Mock the repository
        service.repository = Mock()
        return service

    @pytest.fixture
    def sample_user_id(self) -> UUID4:
        """Create a sample user ID."""
        return uuid4()

    @pytest.fixture
    def sample_parameter_id(self) -> UUID4:
        """Create a sample parameter ID."""
        return uuid4()

    @pytest.fixture
    def sample_parameters_input(self, sample_user_id: UUID4) -> LLMParametersInput:
        """Create a sample LLMParametersInput."""
        return LLMParametersInput(
            user_id=sample_user_id,
            name="Test Parameters",
            description="Test LLM parameters configuration",
            max_new_tokens=512,
            temperature=0.7,
            top_k=50,
            top_p=0.9,
            repetition_penalty=1.1,
            is_default=False,
        )

    @pytest.fixture
    def sample_parameters_output(
        self, sample_parameter_id: UUID4, sample_user_id: UUID4
    ) -> LLMParametersOutput:
        """Create a sample LLMParametersOutput."""
        return LLMParametersOutput(
            id=sample_parameter_id,
            user_id=sample_user_id,
            name="Test Parameters",
            description="Test LLM parameters configuration",
            max_new_tokens=512,
            temperature=0.7,
            top_k=50,
            top_p=0.9,
            repetition_penalty=1.1,
            is_default=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    # ============================================================================
    # INITIALIZATION TESTS
    # ============================================================================

    def test_init(self, mock_db: Mock) -> None:
        """Test LLMParametersService initialization."""
        service = LLMParametersService(mock_db)

        assert service.repository is not None
        assert hasattr(service.repository, "db")

    # ============================================================================
    # CREATE OPERATIONS
    # ============================================================================

    def test_create_parameters_success(
        self,
        service: LLMParametersService,
        sample_parameters_input: LLMParametersInput,
        sample_parameters_output: LLMParametersOutput,
    ) -> None:
        """Test successful parameter creation."""
        service.repository.create.return_value = sample_parameters_output

        result = service.create_parameters(sample_parameters_input)

        assert result == sample_parameters_output
        assert result.name == "Test Parameters"
        assert result.max_new_tokens == 512
        assert result.temperature == 0.7
        service.repository.create.assert_called_once_with(sample_parameters_input)

    def test_create_parameters_with_defaults(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test parameter creation with default values."""
        minimal_input = LLMParametersInput(
            user_id=sample_user_id,
            name="Minimal Config",
            description="Minimal configuration",
        )

        mock_output = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Minimal Config",
            description="Minimal configuration",
            max_new_tokens=100,  # Default
            temperature=0.7,  # Default
            top_k=50,  # Default
            top_p=1.0,  # Default
            repetition_penalty=1.1,  # Default
            is_default=False,  # Default
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.create.return_value = mock_output

        result = service.create_parameters(minimal_input)

        assert result.max_new_tokens == 100
        assert result.temperature == 0.7
        assert result.is_default is False
        service.repository.create.assert_called_once_with(minimal_input)

    def test_create_parameters_as_default(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test creating parameters marked as default."""
        default_input = LLMParametersInput(
            user_id=sample_user_id,
            name="Default Config",
            description="Default configuration",
            is_default=True,
        )

        mock_output = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Default Config",
            description="Default configuration",
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.1,
            is_default=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.create.return_value = mock_output

        result = service.create_parameters(default_input)

        assert result.is_default is True
        service.repository.create.assert_called_once_with(default_input)

    # ============================================================================
    # READ OPERATIONS
    # ============================================================================

    def test_get_parameters_success(
        self,
        service: LLMParametersService,
        sample_parameter_id: UUID4,
        sample_parameters_output: LLMParametersOutput,
    ) -> None:
        """Test successful parameter retrieval."""
        service.repository.get_parameters.return_value = sample_parameters_output

        result = service.get_parameters(sample_parameter_id)

        assert result == sample_parameters_output
        assert result.id == sample_parameter_id
        service.repository.get_parameters.assert_called_once_with(sample_parameter_id)

    def test_get_parameters_not_found(
        self, service: LLMParametersService, sample_parameter_id: UUID4
    ) -> None:
        """Test get_parameters with non-existent parameter."""
        service.repository.get_parameters.return_value = None

        result = service.get_parameters(sample_parameter_id)

        assert result is None
        service.repository.get_parameters.assert_called_once_with(sample_parameter_id)

    def test_get_user_parameters_success(
        self,
        service: LLMParametersService,
        sample_user_id: UUID4,
        sample_parameters_output: LLMParametersOutput,
    ) -> None:
        """Test successful retrieval of user parameters."""
        service.repository.get_parameters_by_user_id.return_value = [sample_parameters_output]

        result = service.get_user_parameters(sample_user_id)

        assert len(result) == 1
        assert result[0] == sample_parameters_output
        service.repository.get_parameters_by_user_id.assert_called_once_with(sample_user_id)

    def test_get_user_parameters_empty_creates_default(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test get_user_parameters creates default when user has no parameters."""
        # First call returns empty, then return the created default
        service.repository.get_parameters_by_user_id.return_value = []

        default_params = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Default Configuration",
            description="Default LLM parameters configuration",
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.1,
            is_default=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.get_default_parameters.return_value = None
        service.repository.create.return_value = default_params

        result = service.get_user_parameters(sample_user_id)

        assert len(result) == 1
        assert result[0].is_default is True
        assert result[0].name == "Default Configuration"
        service.repository.get_parameters_by_user_id.assert_called_once_with(sample_user_id)

    def test_get_user_parameters_create_default_fails(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test get_user_parameters when default creation fails."""
        service.repository.get_parameters_by_user_id.return_value = []
        service.repository.get_default_parameters.return_value = None
        service.repository.create.side_effect = Exception("Database error")

        result = service.get_user_parameters(sample_user_id)

        assert result == []
        service.repository.get_parameters_by_user_id.assert_called_once_with(sample_user_id)

    def test_get_user_parameters_multiple(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test retrieval of multiple user parameters."""
        params1 = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Config 1",
            description="First config",
            max_new_tokens=100,
            temperature=0.5,
            top_k=30,
            top_p=0.8,
            repetition_penalty=1.0,
            is_default=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        params2 = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Config 2",
            description="Second config",
            max_new_tokens=200,
            temperature=0.9,
            top_k=70,
            top_p=0.95,
            repetition_penalty=1.2,
            is_default=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        service.repository.get_parameters_by_user_id.return_value = [params1, params2]

        result = service.get_user_parameters(sample_user_id)

        assert len(result) == 2
        assert result[0].name == "Config 1"
        assert result[1].name == "Config 2"
        service.repository.get_parameters_by_user_id.assert_called_once_with(sample_user_id)

    # ============================================================================
    # UPDATE OPERATIONS
    # ============================================================================

    def test_update_parameters_success(
        self,
        service: LLMParametersService,
        sample_parameter_id: UUID4,
        sample_parameters_input: LLMParametersInput,
        sample_parameters_output: LLMParametersOutput,
    ) -> None:
        """Test successful parameter update."""
        service.repository.update.return_value = sample_parameters_output

        result = service.update_parameters(sample_parameter_id, sample_parameters_input)

        assert result == sample_parameters_output
        service.repository.update.assert_called_once_with(sample_parameter_id, sample_parameters_input)

    def test_update_parameters_partial(
        self,
        service: LLMParametersService,
        sample_parameter_id: UUID4,
        sample_user_id: UUID4,
    ) -> None:
        """Test partial parameter update."""
        partial_update = LLMParametersInput(
            user_id=sample_user_id,
            name="Updated Name",
            description="Updated description",
            temperature=0.9,  # Only update temperature
        )

        updated_output = LLMParametersOutput(
            id=sample_parameter_id,
            user_id=sample_user_id,
            name="Updated Name",
            description="Updated description",
            max_new_tokens=512,  # Original value
            temperature=0.9,  # Updated value
            top_k=50,  # Original value
            top_p=0.9,  # Original value
            repetition_penalty=1.1,  # Original value
            is_default=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.update.return_value = updated_output

        result = service.update_parameters(sample_parameter_id, partial_update)

        assert result.temperature == 0.9
        assert result.name == "Updated Name"
        service.repository.update.assert_called_once_with(sample_parameter_id, partial_update)

    def test_update_parameters_not_found(
        self,
        service: LLMParametersService,
        sample_parameter_id: UUID4,
        sample_parameters_input: LLMParametersInput,
    ) -> None:
        """Test update_parameters with non-existent parameter."""
        service.repository.update.side_effect = NotFoundException(
            resource_type="LLM Parameters",
            resource_id=str(sample_parameter_id),
            message=f"LLM Parameters with ID {sample_parameter_id} not found.",
        )

        with pytest.raises(NotFoundException) as exc_info:
            service.update_parameters(sample_parameter_id, sample_parameters_input)

        assert exc_info.value.details["resource_type"] == "LLM Parameters"
        assert exc_info.value.details["resource_id"] == str(sample_parameter_id)
        service.repository.update.assert_called_once_with(sample_parameter_id, sample_parameters_input)

    # ============================================================================
    # DELETE OPERATIONS
    # ============================================================================

    def test_delete_parameters_success(
        self, service: LLMParametersService, sample_parameter_id: UUID4
    ) -> None:
        """Test successful parameter deletion."""
        service.repository.delete.return_value = None

        # Should not raise an exception
        service.delete_parameters(sample_parameter_id)

        service.repository.delete.assert_called_once_with(sample_parameter_id)

    def test_delete_parameters_not_found(
        self, service: LLMParametersService, sample_parameter_id: UUID4
    ) -> None:
        """Test delete_parameters with non-existent parameter."""
        service.repository.delete.side_effect = NotFoundException(
            resource_type="LLM Parameters",
            resource_id=str(sample_parameter_id),
            message=f"LLM Parameters with ID {sample_parameter_id} not found.",
        )

        with pytest.raises(NotFoundException) as exc_info:
            service.delete_parameters(sample_parameter_id)

        assert exc_info.value.details["resource_type"] == "LLM Parameters"
        service.repository.delete.assert_called_once_with(sample_parameter_id)

    # ============================================================================
    # DEFAULT PARAMETER OPERATIONS
    # ============================================================================

    def test_set_default_parameters_success(
        self,
        service: LLMParametersService,
        sample_parameter_id: UUID4,
        sample_parameters_output: LLMParametersOutput,
    ) -> None:
        """Test successful setting of default parameters."""
        # Mock existing parameters retrieval
        service.repository.get_parameters.return_value = sample_parameters_output

        # Mock the reset and update operations
        service.repository.reset_default_parameters.return_value = 1

        updated_output = LLMParametersOutput(
            id=sample_parameter_id,
            user_id=sample_parameters_output.user_id,
            name=sample_parameters_output.name,
            description=sample_parameters_output.description,
            max_new_tokens=sample_parameters_output.max_new_tokens,
            temperature=sample_parameters_output.temperature,
            top_k=sample_parameters_output.top_k,
            top_p=sample_parameters_output.top_p,
            repetition_penalty=sample_parameters_output.repetition_penalty,
            is_default=True,  # Changed to default
            created_at=sample_parameters_output.created_at,
            updated_at=datetime.now(UTC),
        )
        service.repository.update.return_value = updated_output

        result = service.set_default_parameters(sample_parameter_id)

        assert result.is_default is True
        assert result.id == sample_parameter_id
        service.repository.get_parameters.assert_called_once_with(sample_parameter_id)
        service.repository.reset_default_parameters.assert_called_once_with(
            sample_parameters_output.user_id
        )

    def test_set_default_parameters_not_found(
        self, service: LLMParametersService, sample_parameter_id: UUID4
    ) -> None:
        """Test set_default_parameters with non-existent parameter."""
        service.repository.get_parameters.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            service.set_default_parameters(sample_parameter_id)

        assert exc_info.value.details["resource_type"] == "LLM Parameters"
        assert exc_info.value.details["resource_id"] == str(sample_parameter_id)
        service.repository.get_parameters.assert_called_once_with(sample_parameter_id)

    def test_set_default_parameters_resets_existing_defaults(
        self,
        service: LLMParametersService,
        sample_parameter_id: UUID4,
        sample_parameters_output: LLMParametersOutput,
    ) -> None:
        """Test that setting default resets other defaults for the user."""
        service.repository.get_parameters.return_value = sample_parameters_output
        service.repository.reset_default_parameters.return_value = 2  # 2 previous defaults reset

        updated_output = LLMParametersOutput(
            id=sample_parameter_id,
            user_id=sample_parameters_output.user_id,
            name=sample_parameters_output.name,
            description=sample_parameters_output.description,
            max_new_tokens=sample_parameters_output.max_new_tokens,
            temperature=sample_parameters_output.temperature,
            top_k=sample_parameters_output.top_k,
            top_p=sample_parameters_output.top_p,
            repetition_penalty=sample_parameters_output.repetition_penalty,
            is_default=True,
            created_at=sample_parameters_output.created_at,
            updated_at=datetime.now(UTC),
        )
        service.repository.update.return_value = updated_output

        result = service.set_default_parameters(sample_parameter_id)

        assert result.is_default is True
        service.repository.reset_default_parameters.assert_called_once_with(
            sample_parameters_output.user_id
        )

    def test_initialize_default_parameters_creates_new(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test initialize_default_parameters creates new default when none exist."""
        service.repository.get_default_parameters.return_value = None

        default_params = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Default Configuration",
            description="Default LLM parameters configuration",
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.1,
            is_default=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.create.return_value = default_params

        result = service.initialize_default_parameters(sample_user_id)

        assert result.is_default is True
        assert result.name == "Default Configuration"
        assert result.max_new_tokens == 100
        assert result.temperature == 0.7
        service.repository.get_default_parameters.assert_called_once_with(sample_user_id)
        service.repository.create.assert_called_once()

    def test_initialize_default_parameters_returns_existing(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test initialize_default_parameters returns existing default."""
        existing_default = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Existing Default",
            description="Existing default configuration",
            max_new_tokens=200,
            temperature=0.8,
            top_k=60,
            top_p=0.95,
            repetition_penalty=1.2,
            is_default=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.get_default_parameters.return_value = existing_default

        result = service.initialize_default_parameters(sample_user_id)

        assert result == existing_default
        assert result.name == "Existing Default"
        service.repository.get_default_parameters.assert_called_once_with(sample_user_id)
        service.repository.create.assert_not_called()

    def test_get_latest_or_default_parameters_returns_default(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test get_latest_or_default_parameters returns default when available."""
        default_params = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Default Config",
            description="Default configuration",
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.1,
            is_default=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.get_default_parameters.return_value = default_params

        result = service.get_latest_or_default_parameters(sample_user_id)

        assert result == default_params
        assert result.is_default is True
        service.repository.get_default_parameters.assert_called_once_with(sample_user_id)

    def test_get_latest_or_default_parameters_returns_latest(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test get_latest_or_default_parameters returns latest when no default."""
        service.repository.get_default_parameters.return_value = None

        old_params = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Old Config",
            description="Old configuration",
            max_new_tokens=100,
            temperature=0.5,
            top_k=30,
            top_p=0.8,
            repetition_penalty=1.0,
            is_default=False,
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        )

        latest_params = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Latest Config",
            description="Latest configuration",
            max_new_tokens=200,
            temperature=0.9,
            top_k=70,
            top_p=0.95,
            repetition_penalty=1.2,
            is_default=False,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        service.repository.get_parameters_by_user_id.return_value = [old_params, latest_params]

        result = service.get_latest_or_default_parameters(sample_user_id)

        assert result == latest_params
        assert result.name == "Latest Config"
        service.repository.get_default_parameters.assert_called_once_with(sample_user_id)
        service.repository.get_parameters_by_user_id.assert_called_once_with(sample_user_id)

    def test_get_latest_or_default_parameters_creates_when_empty(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test get_latest_or_default_parameters creates default when user has none."""
        service.repository.get_default_parameters.return_value = None
        service.repository.get_parameters_by_user_id.return_value = []

        default_params = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Default Configuration",
            description="Default LLM parameters configuration",
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.1,
            is_default=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.create.return_value = default_params

        result = service.get_latest_or_default_parameters(sample_user_id)

        assert result == default_params
        assert result.is_default is True
        service.repository.get_parameters_by_user_id.assert_called_once_with(sample_user_id)

    def test_get_latest_or_default_parameters_handles_creation_error(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test get_latest_or_default_parameters handles default creation failure."""
        service.repository.get_default_parameters.return_value = None
        service.repository.get_parameters_by_user_id.return_value = []
        service.repository.create.side_effect = Exception("Database error")

        result = service.get_latest_or_default_parameters(sample_user_id)

        assert result is None
        service.repository.get_parameters_by_user_id.assert_called_once_with(sample_user_id)

    # ============================================================================
    # PARAMETER VALIDATION TESTS
    # ============================================================================

    def test_create_parameters_validates_temperature_range(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test that temperature validation is enforced."""
        # Temperature > 1.0 should fail validation at schema level
        with pytest.raises(ValidationError):
            LLMParametersInput(
                user_id=sample_user_id,
                name="Invalid Temp",
                description="Invalid temperature",
                temperature=1.5,  # Invalid: > 1.0
            )

    def test_create_parameters_validates_temperature_negative(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test that negative temperature is rejected."""
        with pytest.raises(ValidationError):
            LLMParametersInput(
                user_id=sample_user_id,
                name="Invalid Temp",
                description="Invalid temperature",
                temperature=-0.1,  # Invalid: < 0.0
            )

    def test_create_parameters_validates_top_p_range(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test that top_p validation is enforced."""
        with pytest.raises(ValidationError):
            LLMParametersInput(
                user_id=sample_user_id,
                name="Invalid Top P",
                description="Invalid top_p",
                top_p=1.5,  # Invalid: > 1.0
            )

    def test_create_parameters_validates_top_k_range(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test that top_k validation is enforced."""
        with pytest.raises(ValidationError):
            LLMParametersInput(
                user_id=sample_user_id,
                name="Invalid Top K",
                description="Invalid top_k",
                top_k=0,  # Invalid: < 1
            )

    def test_create_parameters_validates_max_tokens_positive(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test that max_new_tokens must be positive."""
        with pytest.raises(ValidationError):
            LLMParametersInput(
                user_id=sample_user_id,
                name="Invalid Tokens",
                description="Invalid max_new_tokens",
                max_new_tokens=0,  # Invalid: < 1
            )

    def test_create_parameters_validates_repetition_penalty_range(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test that repetition_penalty validation is enforced."""
        with pytest.raises(ValidationError):
            LLMParametersInput(
                user_id=sample_user_id,
                name="Invalid Penalty",
                description="Invalid repetition_penalty",
                repetition_penalty=0.5,  # Invalid: < 1.0
            )

    def test_create_parameters_boundary_values(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test parameter creation with boundary values."""
        boundary_input = LLMParametersInput(
            user_id=sample_user_id,
            name="Boundary Test",
            description="Testing boundary values",
            max_new_tokens=1,  # Minimum
            temperature=0.0,  # Minimum
            top_k=1,  # Minimum
            top_p=0.0,  # Minimum
            repetition_penalty=1.0,  # Minimum
            is_default=False,
        )

        boundary_output = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Boundary Test",
            description="Testing boundary values",
            max_new_tokens=1,
            temperature=0.0,
            top_k=1,
            top_p=0.0,
            repetition_penalty=1.0,
            is_default=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.create.return_value = boundary_output

        result = service.create_parameters(boundary_input)

        assert result.max_new_tokens == 1
        assert result.temperature == 0.0
        assert result.top_k == 1
        assert result.top_p == 0.0
        assert result.repetition_penalty == 1.0

    def test_create_parameters_maximum_values(
        self, service: LLMParametersService, sample_user_id: UUID4
    ) -> None:
        """Test parameter creation with maximum valid values."""
        max_input = LLMParametersInput(
            user_id=sample_user_id,
            name="Maximum Test",
            description="Testing maximum values",
            max_new_tokens=10000,
            temperature=1.0,  # Maximum for validation
            top_k=100,  # Maximum
            top_p=1.0,  # Maximum
            repetition_penalty=2.0,  # Maximum
            is_default=False,
        )

        max_output = LLMParametersOutput(
            id=uuid4(),
            user_id=sample_user_id,
            name="Maximum Test",
            description="Testing maximum values",
            max_new_tokens=10000,
            temperature=1.0,
            top_k=100,
            top_p=1.0,
            repetition_penalty=2.0,
            is_default=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.create.return_value = max_output

        result = service.create_parameters(max_input)

        assert result.max_new_tokens == 10000
        assert result.temperature == 1.0
        assert result.top_k == 100
        assert result.top_p == 1.0
        assert result.repetition_penalty == 2.0
