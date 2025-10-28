"""Unit tests for LLMModelService."""

from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from core.custom_exceptions import LLMProviderError, ModelConfigError, ModelValidationError
from rag_solution.core.exceptions import NotFoundError
from rag_solution.schemas.llm_model_schema import LLMModelInput, LLMModelOutput, ModelType
from rag_solution.services.llm_model_service import LLMModelService


class TestLLMModelService:
    """Test cases for LLMModelService."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db: Mock) -> LLMModelService:
        """Create an LLMModelService instance with mocked dependencies."""
        service = LLMModelService(mock_db)
        # Mock the repositories
        service.repository = Mock()
        service.provider_repository = Mock()
        return service

    @pytest.fixture
    def sample_model_input(self) -> LLMModelInput:
        """Create a sample LLMModelInput."""
        return LLMModelInput(
            provider_id=uuid4(),
            model_id="test-model",
            default_model_id="test-model",
            model_type=ModelType.GENERATION,
            timeout=30,
            max_retries=3,
            is_default=False
        )

    @pytest.fixture
    def sample_model_output(self) -> LLMModelOutput:
        """Create a sample LLMModelOutput."""
        return LLMModelOutput(
            id=uuid4(),
            provider_id=uuid4(),
            model_id="test-model",
            default_model_id="test-model",
            model_type=ModelType.GENERATION,
            timeout=30,
            max_retries=3,
            batch_size=10,
            retry_delay=1.0,
            concurrency_limit=10,
            stream=False,
            rate_limit=10,
            is_default=False,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def test_init(self, mock_db: Mock) -> None:
        """Test LLMModelService initialization."""
        service = LLMModelService(mock_db)

        assert service.session == mock_db
        assert service.repository is not None
        assert service.provider_repository is not None

    def test_validate_model_input_success(self, service: LLMModelService, sample_model_input: LLMModelInput) -> None:
        """Test _validate_model_input with valid input."""
        # Mock provider exists
        service.provider_repository.get_provider_by_id.return_value = Mock()

        # Should not raise an exception
        service._validate_model_input(sample_model_input)

        service.provider_repository.get_provider_by_id.assert_called_once_with(sample_model_input.provider_id)

    def test_validate_model_input_invalid_timeout(self, service: LLMModelService) -> None:
        """Test _validate_model_input with invalid timeout."""
        model_input = LLMModelInput(
            model_id="test-model",
            default_model_id="test-model",
            provider_id=uuid4(),
            model_type=ModelType.GENERATION,
            timeout=0,  # Invalid timeout
            max_retries=3,
            is_default=False
        )

        with pytest.raises(ModelValidationError) as exc_info:
            service._validate_model_input(model_input)

        assert exc_info.value.details["field"] == "timeout"
        assert "Timeout must be greater than 0" in exc_info.value.message

    def test_validate_model_input_negative_retries(self, service: LLMModelService) -> None:
        """Test _validate_model_input with negative max_retries."""
        model_input = LLMModelInput(
            model_id="test-model",
            default_model_id="test-model",
            provider_id=uuid4(),
            model_type=ModelType.GENERATION,
            timeout=30,
            max_retries=-1,  # Invalid retries
            is_default=False
        )

        with pytest.raises(ModelValidationError) as exc_info:
            service._validate_model_input(model_input)

        assert exc_info.value.details["field"] == "max_retries"
        assert "Max retries cannot be negative" in exc_info.value.message

    def test_validate_model_input_provider_not_found(self, service: LLMModelService, sample_model_input: LLMModelInput) -> None:
        """Test _validate_model_input with non-existent provider."""
        service.provider_repository.get_provider_by_id.return_value = None

        with pytest.raises(ModelConfigError) as exc_info:
            service._validate_model_input(sample_model_input)

        assert exc_info.value.details["field"] == "provider_id"
        assert f"Provider {sample_model_input.provider_id} does not exist" in exc_info.value.message

    def test_create_model_success(self, service: LLMModelService, sample_model_input: LLMModelInput, sample_model_output: LLMModelOutput) -> None:
        """Test create_model with successful result."""
        # Mock validation passes
        service.provider_repository.get_provider_by_id.return_value = Mock()
        service.repository.create_model.return_value = sample_model_output

        result = service.create_model(sample_model_input)

        assert result == sample_model_output
        service.repository.create_model.assert_called_once_with(sample_model_input)

    def test_create_model_validation_error(self, service: LLMModelService) -> None:
        """Test create_model with validation error."""
        model_input = LLMModelInput(
            model_id="test-model",
            default_model_id="test-model",
            provider_id=uuid4(),
            model_type=ModelType.GENERATION,
            timeout=0,  # Invalid timeout
            max_retries=3,
            is_default=False
        )

        with pytest.raises(ModelValidationError):
            service.create_model(model_input)

    def test_create_model_provider_error(self, service: LLMModelService, sample_model_input: LLMModelInput) -> None:
        """Test create_model with provider error."""
        service.provider_repository.get_provider_by_id.return_value = Mock()
        service.repository.create_model.side_effect = Exception("Database error")

        with pytest.raises(LLMProviderError) as exc_info:
            service.create_model(sample_model_input)

        assert exc_info.value.details["provider"] == str(sample_model_input.provider_id)
        assert exc_info.value.details["error_type"] == "model_creation"

    def test_set_default_model_success(self, service: LLMModelService, sample_model_output: LLMModelOutput) -> None:
        """Test set_default_model with successful result."""
        model_id = uuid4()
        service.repository.get_model_by_id.return_value = sample_model_output
        service.repository.update_model.return_value = sample_model_output

        result = service.set_default_model(model_id)

        assert result == sample_model_output
        service.repository.get_model_by_id.assert_called_once_with(model_id)
        service.repository.clear_other_defaults.assert_called_once_with(sample_model_output.provider_id, sample_model_output.model_type)
        # Check that update_model was called (service passes LLMModelUpdate object)
        service.repository.update_model.assert_called_once()
        call_args = service.repository.update_model.call_args
        assert call_args[0][0] == model_id
        assert call_args[0][1].is_default is True

    def test_set_default_model_not_found(self, service: LLMModelService) -> None:
        """Test set_default_model with model not found."""
        model_id = uuid4()
        service.repository.get_model_by_id.return_value = None

        with pytest.raises(LLMProviderError) as exc_info:
            service.set_default_model(model_id)

        assert exc_info.value.details["error_type"] == "default_update"
        service.repository.get_model_by_id.assert_called_once_with(model_id)

    def test_set_default_model_error(self, service: LLMModelService, sample_model_output: LLMModelOutput) -> None:
        """Test set_default_model with error."""
        model_id = uuid4()
        service.repository.get_model_by_id.return_value = sample_model_output
        service.repository.clear_other_defaults.side_effect = Exception("Database error")

        with pytest.raises(LLMProviderError) as exc_info:
            service.set_default_model(model_id)

        assert exc_info.value.details["error_type"] == "default_update"

    def test_get_default_model_success(self, service: LLMModelService, sample_model_output: LLMModelOutput) -> None:
        """Test get_default_model with successful result."""
        provider_id = uuid4()
        model_type = ModelType.GENERATION
        service.repository.get_default_model.return_value = sample_model_output

        result = service.get_default_model(provider_id, model_type)

        assert result == sample_model_output
        service.repository.get_default_model.assert_called_once_with(provider_id, model_type)

    def test_get_default_model_error(self, service: LLMModelService) -> None:
        """Test get_default_model with error."""
        provider_id = uuid4()
        model_type = ModelType.GENERATION
        service.repository.get_default_model.side_effect = Exception("Database error")

        with pytest.raises(LLMProviderError) as exc_info:
            service.get_default_model(provider_id, model_type)

        assert exc_info.value.details["provider"] == str(provider_id)
        assert exc_info.value.details["error_type"] == "default_retrieval"

    def test_get_model_by_id_success(self, service: LLMModelService, sample_model_output: LLMModelOutput) -> None:
        """Test get_model_by_id with successful result."""
        model_id = uuid4()
        service.repository.get_model_by_id.return_value = sample_model_output

        result = service.get_model_by_id(model_id)

        assert result == sample_model_output
        service.repository.get_model_by_id.assert_called_once_with(model_id)

    def test_get_model_by_id_not_found(self, service: LLMModelService) -> None:
        """Test get_model_by_id with model not found."""
        model_id = uuid4()
        service.repository.get_model_by_id.return_value = None

        result = service.get_model_by_id(model_id)

        assert result is None
        service.repository.get_model_by_id.assert_called_once_with(model_id)

    def test_get_models_by_provider_success(self, service: LLMModelService, sample_model_output: LLMModelOutput) -> None:
        """Test get_models_by_provider with successful result."""
        provider_id = uuid4()
        service.repository.get_models_by_provider.return_value = [sample_model_output]

        result = service.get_models_by_provider(provider_id)

        assert result == [sample_model_output]
        service.repository.get_models_by_provider.assert_called_once_with(provider_id)

    def test_get_models_by_provider_error(self, service: LLMModelService) -> None:
        """Test get_models_by_provider with error."""
        provider_id = uuid4()
        service.repository.get_models_by_provider.side_effect = Exception("Database error")

        with pytest.raises(LLMProviderError) as exc_info:
            service.get_models_by_provider(provider_id)

        assert exc_info.value.details["provider"] == str(provider_id)
        assert exc_info.value.details["error_type"] == "model_retrieval"

    def test_get_models_by_type_success(self, service: LLMModelService, sample_model_output: LLMModelOutput) -> None:
        """Test get_models_by_type with successful result."""
        model_type = ModelType.GENERATION
        service.repository.get_models_by_type.return_value = [sample_model_output]

        result = service.get_models_by_type(model_type)

        assert result == [sample_model_output]
        service.repository.get_models_by_type.assert_called_once_with(model_type)

    def test_get_models_by_type_error(self, service: LLMModelService) -> None:
        """Test get_models_by_type with error."""
        model_type = ModelType.GENERATION
        service.repository.get_models_by_type.side_effect = Exception("Database error")

        with pytest.raises(LLMProviderError) as exc_info:
            service.get_models_by_type(model_type)

        assert exc_info.value.details["error_type"] == "model_retrieval"

    def test_update_model_success(self, service: LLMModelService, sample_model_output: LLMModelOutput) -> None:
        """Test update_model with successful result."""
        model_id = uuid4()
        updates = {"name": "updated-model"}
        service.repository.update_model.return_value = sample_model_output

        result = service.update_model(model_id, updates)

        assert result == sample_model_output
        service.repository.update_model.assert_called_once_with(model_id, updates)

    def test_update_model_error(self, service: LLMModelService) -> None:
        """Test update_model with error."""
        model_id = uuid4()
        updates = {"name": "updated-model"}
        service.repository.update_model.side_effect = Exception("Database error")

        with pytest.raises(LLMProviderError) as exc_info:
            service.update_model(model_id, updates)

        assert exc_info.value.details["provider"] == str(model_id)
        assert exc_info.value.details["error_type"] == "model_update"

    def test_delete_model_success(self, service: LLMModelService) -> None:
        """Test delete_model with successful result."""
        model_id = uuid4()
        service.repository.delete_model.return_value = None

        result = service.delete_model(model_id)

        assert result is True
        service.repository.delete_model.assert_called_once_with(model_id)

    def test_delete_model_error(self, service: LLMModelService) -> None:
        """Test delete_model with error."""
        model_id = uuid4()
        service.repository.delete_model.side_effect = Exception("Database error")

        result = service.delete_model(model_id)

        assert result is False
        service.repository.delete_model.assert_called_once_with(model_id)
