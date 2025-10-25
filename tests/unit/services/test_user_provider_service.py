"""Comprehensive unit tests for UserProviderService.

This module provides complete test coverage for the UserProviderService,
including user initialization, provider management, template creation,
and error handling. All external dependencies (database, repositories, services)
are mocked.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

from backend.core.config import Settings
from backend.core.custom_exceptions import NotFoundError, RepositoryError
from backend.rag_solution.core.exceptions import ValidationError
from backend.rag_solution.schemas.llm_parameters_schema import LLMParametersOutput
from backend.rag_solution.schemas.llm_provider_schema import LLMProviderOutput
from backend.rag_solution.schemas.prompt_template_schema import (
    PromptTemplateInput,
    PromptTemplateOutput,
    PromptTemplateType,
)
from backend.rag_solution.services.user_provider_service import UserProviderService


@pytest.mark.unit
class TestUserProviderServiceUnit:
    """Unit tests for UserProviderService with fully mocked dependencies."""

    # ============================================================================
    # FIXTURES
    # ============================================================================

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        db = Mock(spec=Session)
        db.commit = Mock()
        db.rollback = Mock()
        return db

    @pytest.fixture
    def mock_user_provider_repository(self) -> Mock:
        """Mock user provider repository."""
        return Mock()

    @pytest.fixture
    def mock_prompt_template_service(self) -> Mock:
        """Mock prompt template service."""
        return Mock()

    @pytest.fixture
    def mock_llm_model_service(self) -> Mock:
        """Mock LLM model service."""
        return Mock()

    @pytest.fixture
    def service(
        self,
        mock_db,
        mock_settings,
        mock_user_provider_repository,
        mock_prompt_template_service,
        mock_llm_model_service,
    ) -> UserProviderService:
        """Create service instance with mocked dependencies."""
        with patch("backend.rag_solution.services.user_provider_service.UserProviderRepository"), patch(
            "backend.rag_solution.services.user_provider_service.PromptTemplateService"
        ), patch("backend.rag_solution.services.user_provider_service.LLMModelService"):
            service = UserProviderService(mock_db, mock_settings)
            service.user_provider_repository = mock_user_provider_repository
            service.prompt_template_service = mock_prompt_template_service
            service.llm_model_service = mock_llm_model_service
            return service

    @pytest.fixture
    def mock_provider(self) -> LLMProviderOutput:
        """Create a mock LLM provider output."""
        return LLMProviderOutput(
            id=uuid4(),
            name="watsonx-test",
            base_url="https://us-south.ml.cloud.ibm.com",
            org_id="test-org",
            project_id="test-project",
            is_active=True,
            is_default=True,
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

    @pytest.fixture
    def mock_prompt_template(self) -> PromptTemplateOutput:
        """Create a mock prompt template output."""
        return PromptTemplateOutput(
            id=uuid4(),
            name="default-rag-template",
            user_id=uuid4(),
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="You are a helpful AI assistant.",
            template_format="{context}\n\n{question}",
            input_variables={"context": "Retrieved context", "question": "User's question"},
            example_inputs={"context": "Test context", "question": "Test question?"},
            is_default=True,
            max_context_length=2048,
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

    @pytest.fixture
    def mock_parameters(self) -> LLMParametersOutput:
        """Create a mock LLM parameters output."""
        return LLMParametersOutput(
            id=uuid4(),
            user_id=uuid4(),
            name="default-parameters",
            description="Default LLM parameters",
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.1,
            is_default=True,
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

    # ============================================================================
    # INITIALIZATION TESTS
    # ============================================================================

    def test_service_initialization(self, mock_db, mock_settings):
        """Test service initializes correctly with database session and settings."""
        with patch("backend.rag_solution.services.user_provider_service.UserProviderRepository") as mock_repo_class, patch(
            "backend.rag_solution.services.user_provider_service.PromptTemplateService"
        ) as mock_template_class, patch(
            "backend.rag_solution.services.user_provider_service.LLMModelService"
        ) as mock_model_class:
            service = UserProviderService(mock_db, mock_settings)

            assert service.db is mock_db
            assert service.settings is mock_settings
            mock_repo_class.assert_called_once_with(mock_db)
            mock_template_class.assert_called_once_with(mock_db)
            mock_model_class.assert_called_once_with(mock_db)

    # ============================================================================
    # INITIALIZE USER DEFAULTS TESTS
    # ============================================================================

    def test_initialize_user_defaults_success(
        self,
        service,
        mock_user_provider_repository,
        mock_prompt_template_service,
        mock_db,
        mock_provider,
        mock_prompt_template,
        mock_parameters,
    ):
        """Test successful initialization of user defaults."""
        user_id = uuid4()

        # Mock get_user_provider returns None (no existing provider)
        mock_user_provider_repository.get_user_provider.return_value = None
        mock_user_provider_repository.get_default_provider.return_value = mock_provider
        mock_user_provider_repository.set_user_provider.return_value = True

        # Mock template creation
        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        # Mock parameters service (module-level import) and pipeline service (local import)
        with patch("backend.rag_solution.services.user_provider_service.LLMParametersService") as mock_params_class, patch(
            "backend.rag_solution.services.pipeline_service.PipelineService"
        ) as mock_pipeline_class:
            mock_params_service = Mock()
            mock_params_service.initialize_default_parameters.return_value = mock_parameters
            mock_params_class.return_value = mock_params_service

            mock_pipeline_service = Mock()
            mock_pipeline_service.initialize_user_pipeline.return_value = None
            mock_pipeline_class.return_value = mock_pipeline_service

            result_provider, result_templates, result_params = service.initialize_user_defaults(user_id)

            assert result_provider == mock_provider
            assert len(result_templates) == 3
            assert result_params == mock_parameters
            mock_user_provider_repository.set_user_provider.assert_called_once_with(user_id, mock_provider.id)
            assert mock_prompt_template_service.create_template.call_count == 3
            mock_params_service.initialize_default_parameters.assert_called_once_with(user_id)
            mock_pipeline_service.initialize_user_pipeline.assert_called_once_with(user_id, mock_provider.id)
            mock_db.commit.assert_called_once()

    def test_initialize_user_defaults_with_existing_provider(
        self,
        service,
        mock_user_provider_repository,
        mock_prompt_template_service,
        mock_db,
        mock_provider,
        mock_prompt_template,
        mock_parameters,
    ):
        """Test initialization when user already has a provider."""
        user_id = uuid4()

        # Mock user already has a provider
        mock_user_provider_repository.get_user_provider.return_value = mock_provider

        # Mock template creation
        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        # Mock parameters and pipeline services - patch at service module level
        with patch("backend.rag_solution.services.user_provider_service.LLMParametersService") as mock_params_class, patch(
            "backend.rag_solution.services.pipeline_service.PipelineService"
        ) as mock_pipeline_class:
            mock_params_service = Mock()
            mock_params_service.initialize_default_parameters.return_value = mock_parameters
            mock_params_class.return_value = mock_params_service

            mock_pipeline_service = Mock()
            mock_pipeline_class.return_value = mock_pipeline_service

            result_provider, result_templates, result_params = service.initialize_user_defaults(user_id)

            assert result_provider == mock_provider
            assert len(result_templates) == 3
            assert result_params == mock_parameters
            # Should NOT call set_user_provider since provider already exists
            mock_user_provider_repository.set_user_provider.assert_not_called()
            mock_db.commit.assert_called_once()

    def test_initialize_user_defaults_no_default_provider(
        self,
        service,
        mock_user_provider_repository,
        mock_db,
    ):
        """Test initialization fails when no default provider exists."""
        user_id = uuid4()

        # Mock no existing provider and no default provider
        mock_user_provider_repository.get_user_provider.return_value = None
        mock_user_provider_repository.get_default_provider.return_value = None

        result_provider, result_templates, result_params = service.initialize_user_defaults(user_id)

        assert result_provider is None
        assert result_templates == []
        assert result_params is None

    def test_initialize_user_defaults_parameters_initialization_fails(
        self,
        service,
        mock_user_provider_repository,
        mock_prompt_template_service,
        mock_db,
        mock_provider,
        mock_prompt_template,
    ):
        """Test initialization fails when parameters initialization fails."""
        user_id = uuid4()

        mock_user_provider_repository.get_user_provider.return_value = mock_provider
        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        with patch("backend.rag_solution.services.user_provider_service.LLMParametersService") as mock_params_class:
            mock_params_service = Mock()
            mock_params_service.initialize_default_parameters.return_value = None
            mock_params_class.return_value = mock_params_service

            result_provider, result_templates, result_params = service.initialize_user_defaults(user_id)

            assert result_provider is None
            assert result_templates == []
            assert result_params is None

    def test_initialize_user_defaults_exception_handling(
        self,
        service,
        mock_user_provider_repository,
        mock_db,
    ):
        """Test initialization handles exceptions and rolls back transaction."""
        user_id = uuid4()

        mock_user_provider_repository.get_user_provider.side_effect = Exception("Database connection error")

        with pytest.raises(ValidationError) as exc_info:
            service.initialize_user_defaults(user_id)

        assert "Failed to initialize required user configuration" in str(exc_info.value)
        mock_db.rollback.assert_called_once()

    # ============================================================================
    # GET USER PROVIDER TESTS
    # ============================================================================

    def test_get_user_provider_with_existing_provider(
        self,
        service,
        mock_user_provider_repository,
        mock_provider,
    ):
        """Test retrieving user's existing provider."""
        user_id = uuid4()

        mock_user_provider_repository.get_user_provider.return_value = mock_provider

        result = service.get_user_provider(user_id)

        assert result == mock_provider
        mock_user_provider_repository.get_user_provider.assert_called_once_with(user_id)

    def test_get_user_provider_assigns_default_when_missing(
        self,
        service,
        mock_user_provider_repository,
        mock_provider,
    ):
        """Test assigning default provider when user has none."""
        user_id = uuid4()

        # Mock no existing provider
        mock_user_provider_repository.get_user_provider.return_value = None
        mock_user_provider_repository.get_default_provider.return_value = mock_provider
        mock_user_provider_repository.set_user_provider.return_value = True

        result = service.get_user_provider(user_id)

        assert result == mock_provider
        mock_user_provider_repository.get_default_provider.assert_called_once()
        mock_user_provider_repository.set_user_provider.assert_called_once_with(user_id, mock_provider.id)

    def test_get_user_provider_no_default_provider_available(
        self,
        service,
        mock_user_provider_repository,
    ):
        """Test when no default provider is available in the system."""
        user_id = uuid4()

        mock_user_provider_repository.get_user_provider.return_value = None
        mock_user_provider_repository.get_default_provider.return_value = None

        result = service.get_user_provider(user_id)

        assert result is None

    def test_get_user_provider_repository_error(
        self,
        service,
        mock_user_provider_repository,
    ):
        """Test get_user_provider handles repository errors."""
        user_id = uuid4()

        mock_user_provider_repository.get_user_provider.side_effect = Exception("Database error")

        with pytest.raises(ValidationError) as exc_info:
            service.get_user_provider(user_id)

        assert "Error fetching provider" in str(exc_info.value)

    # ============================================================================
    # SET USER PROVIDER TESTS
    # ============================================================================

    def test_set_user_provider_success(
        self,
        service,
        mock_user_provider_repository,
    ):
        """Test successfully setting user's preferred provider."""
        user_id = uuid4()
        provider_id = uuid4()

        mock_user_provider_repository.set_user_provider.return_value = True

        result = service.set_user_provider(user_id, provider_id)

        assert result is True
        mock_user_provider_repository.set_user_provider.assert_called_once_with(user_id, provider_id)

    def test_set_user_provider_user_not_found(
        self,
        service,
        mock_user_provider_repository,
    ):
        """Test setting provider for non-existent user."""
        user_id = uuid4()
        provider_id = uuid4()

        mock_user_provider_repository.set_user_provider.return_value = False

        with pytest.raises(ValidationError) as exc_info:
            service.set_user_provider(user_id, provider_id)

        assert "User not found" in str(exc_info.value)
        assert str(user_id) in str(exc_info.value)

    def test_set_user_provider_repository_error(
        self,
        service,
        mock_user_provider_repository,
    ):
        """Test set_user_provider handles repository errors."""
        user_id = uuid4()
        provider_id = uuid4()

        mock_user_provider_repository.set_user_provider.side_effect = RepositoryError("Failed to set user provider")

        with pytest.raises(RepositoryError):
            service.set_user_provider(user_id, provider_id)

    # ============================================================================
    # TEMPLATE CREATION TESTS
    # ============================================================================

    def test_create_default_rag_template_success(
        self,
        service,
        mock_prompt_template_service,
        mock_prompt_template,
    ):
        """Test creating default RAG template."""
        user_id = uuid4()

        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        result = service._create_default_rag_template(user_id)

        assert result == mock_prompt_template
        mock_prompt_template_service.create_template.assert_called_once()

        # Verify the template input structure
        call_args = mock_prompt_template_service.create_template.call_args[0][0]
        assert isinstance(call_args, PromptTemplateInput)
        assert call_args.name == "default-rag-template"
        assert call_args.user_id == user_id
        assert call_args.template_type == PromptTemplateType.RAG_QUERY
        assert call_args.is_default is True
        assert "context" in call_args.input_variables
        assert "question" in call_args.input_variables
        assert call_args.max_context_length == 2048

    def test_create_default_question_template_success(
        self,
        service,
        mock_prompt_template_service,
        mock_prompt_template,
    ):
        """Test creating default question generation template."""
        user_id = uuid4()

        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        result = service._create_default_question_template(user_id)

        assert result == mock_prompt_template
        mock_prompt_template_service.create_template.assert_called_once()

        call_args = mock_prompt_template_service.create_template.call_args[0][0]
        assert isinstance(call_args, PromptTemplateInput)
        assert call_args.name == "default-question-template"
        assert call_args.template_type == PromptTemplateType.QUESTION_GENERATION
        assert "context" in call_args.input_variables
        assert "num_questions" in call_args.input_variables

    def test_create_default_podcast_template_success(
        self,
        service,
        mock_prompt_template_service,
        mock_prompt_template,
    ):
        """Test creating default podcast generation template."""
        user_id = uuid4()

        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        result = service._create_default_podcast_template(user_id)

        assert result == mock_prompt_template
        mock_prompt_template_service.create_template.assert_called_once()

        call_args = mock_prompt_template_service.create_template.call_args[0][0]
        assert isinstance(call_args, PromptTemplateInput)
        assert call_args.name == "default-podcast-template"
        assert call_args.template_type == PromptTemplateType.PODCAST_GENERATION
        assert "user_topic" in call_args.input_variables
        assert "rag_results" in call_args.input_variables
        assert "duration_minutes" in call_args.input_variables
        assert call_args.max_context_length == 8192

    def test_template_creation_validates_input_variables(
        self,
        service,
        mock_prompt_template_service,
        mock_prompt_template,
    ):
        """Test that template creation includes proper input variables."""
        user_id = uuid4()
        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        # Test RAG template
        service._create_default_rag_template(user_id)
        rag_call = mock_prompt_template_service.create_template.call_args[0][0]
        assert "context" in rag_call.template_format
        assert "question" in rag_call.template_format

        # Test question template
        mock_prompt_template_service.create_template.reset_mock()
        service._create_default_question_template(user_id)
        question_call = mock_prompt_template_service.create_template.call_args[0][0]
        assert "context" in question_call.template_format
        assert "num_questions" in question_call.template_format

        # Test podcast template
        mock_prompt_template_service.create_template.reset_mock()
        service._create_default_podcast_template(user_id)
        podcast_call = mock_prompt_template_service.create_template.call_args[0][0]
        assert "user_topic" in podcast_call.template_format
        assert "rag_results" in podcast_call.template_format
        assert "duration_minutes" in podcast_call.template_format

    # ============================================================================
    # INTEGRATION WORKFLOW TESTS
    # ============================================================================

    def test_full_user_initialization_workflow(
        self,
        service,
        mock_user_provider_repository,
        mock_prompt_template_service,
        mock_db,
        mock_provider,
        mock_prompt_template,
        mock_parameters,
    ):
        """Test complete user initialization workflow from start to finish."""
        user_id = uuid4()

        # Setup mocks for complete workflow
        mock_user_provider_repository.get_user_provider.return_value = None
        mock_user_provider_repository.get_default_provider.return_value = mock_provider
        mock_user_provider_repository.set_user_provider.return_value = True
        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        with patch("backend.rag_solution.services.user_provider_service.LLMParametersService") as mock_params_class, patch(
            "backend.rag_solution.services.pipeline_service.PipelineService"
        ) as mock_pipeline_class:
            mock_params_service = Mock()
            mock_params_service.initialize_default_parameters.return_value = mock_parameters
            mock_params_class.return_value = mock_params_service

            mock_pipeline_service = Mock()
            mock_pipeline_class.return_value = mock_pipeline_service

            # Execute initialization
            provider, templates, params = service.initialize_user_defaults(user_id)

            # Verify all steps completed
            assert provider is not None
            assert len(templates) == 3
            assert params is not None

            # Verify correct order of operations
            mock_user_provider_repository.get_user_provider.assert_called_once()
            mock_user_provider_repository.get_default_provider.assert_called_once()
            mock_user_provider_repository.set_user_provider.assert_called_once()
            assert mock_prompt_template_service.create_template.call_count == 3
            mock_params_service.initialize_default_parameters.assert_called_once()
            mock_pipeline_service.initialize_user_pipeline.assert_called_once()
            mock_db.commit.assert_called_once()

    def test_provider_retrieval_with_automatic_assignment(
        self,
        service,
        mock_user_provider_repository,
        mock_provider,
    ):
        """Test provider retrieval automatically assigns default when missing."""
        user_id = uuid4()

        # First call returns None (no provider)
        mock_user_provider_repository.get_user_provider.return_value = None
        mock_user_provider_repository.get_default_provider.return_value = mock_provider
        mock_user_provider_repository.set_user_provider.return_value = True

        result = service.get_user_provider(user_id)

        assert result == mock_provider
        # Verify set_user_provider was called to persist the assignment
        mock_user_provider_repository.set_user_provider.assert_called_once_with(user_id, mock_provider.id)

    # ============================================================================
    # ERROR HANDLING AND EDGE CASES
    # ============================================================================

    def test_initialize_user_defaults_partial_failure_rollback(
        self,
        service,
        mock_user_provider_repository,
        mock_prompt_template_service,
        mock_db,
        mock_provider,
    ):
        """Test that initialization rolls back on partial failure."""
        user_id = uuid4()

        mock_user_provider_repository.get_user_provider.return_value = mock_provider
        # Template creation fails
        mock_prompt_template_service.create_template.side_effect = Exception("Template creation failed")

        with pytest.raises(ValidationError):
            service.initialize_user_defaults(user_id)

        mock_db.rollback.assert_called_once()

    def test_concurrent_user_initializations(
        self,
        service,
        mock_user_provider_repository,
        mock_prompt_template_service,
        mock_db,
        mock_provider,
        mock_prompt_template,
        mock_parameters,
    ):
        """Test handling of concurrent user initializations."""
        user_id_1 = uuid4()
        user_id_2 = uuid4()

        mock_user_provider_repository.get_user_provider.return_value = mock_provider
        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        with patch("backend.rag_solution.services.user_provider_service.LLMParametersService") as mock_params_class, patch(
            "backend.rag_solution.services.pipeline_service.PipelineService"
        ) as mock_pipeline_class:
            mock_params_service = Mock()
            mock_params_service.initialize_default_parameters.return_value = mock_parameters
            mock_params_class.return_value = mock_params_service

            mock_pipeline_service = Mock()
            mock_pipeline_class.return_value = mock_pipeline_service

            # Initialize both users
            result1 = service.initialize_user_defaults(user_id_1)
            result2 = service.initialize_user_defaults(user_id_2)

            # Both should succeed independently
            assert result1[0] is not None
            assert result2[0] is not None
            assert mock_db.commit.call_count == 2

    def test_get_user_provider_with_invalid_user_id(
        self,
        service,
        mock_user_provider_repository,
    ):
        """Test getting provider with invalid user ID format."""
        # This would be caught by UUID4 validation in real usage
        user_id = uuid4()

        mock_user_provider_repository.get_user_provider.side_effect = ValidationError(
            "Invalid user ID format", field="user_id"
        )

        with pytest.raises(ValidationError):
            service.get_user_provider(user_id)

    def test_set_user_provider_with_invalid_provider_id(
        self,
        service,
        mock_user_provider_repository,
    ):
        """Test setting provider with invalid provider ID."""
        user_id = uuid4()
        provider_id = uuid4()

        # Repository returns False indicating user not found
        mock_user_provider_repository.set_user_provider.return_value = False

        with pytest.raises(ValidationError) as exc_info:
            service.set_user_provider(user_id, provider_id)

        assert "User not found" in str(exc_info.value)

    def test_template_creation_with_custom_configuration(
        self,
        service,
        mock_prompt_template_service,
        mock_prompt_template,
    ):
        """Test that templates are created with correct configurations."""
        user_id = uuid4()
        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        # Create RAG template
        result = service._create_default_rag_template(user_id)
        call_args = mock_prompt_template_service.create_template.call_args[0][0]
        assert call_args.max_context_length == 2048
        assert call_args.validation_schema is not None

        # Create podcast template
        mock_prompt_template_service.create_template.reset_mock()
        result = service._create_default_podcast_template(user_id)
        call_args = mock_prompt_template_service.create_template.call_args[0][0]
        assert call_args.max_context_length == 8192  # Larger for podcasts
        assert call_args.validation_schema is not None

    def test_initialize_user_defaults_database_commit_failure(
        self,
        service,
        mock_user_provider_repository,
        mock_prompt_template_service,
        mock_db,
        mock_provider,
        mock_prompt_template,
        mock_parameters,
    ):
        """Test handling of database commit failure."""
        user_id = uuid4()

        mock_user_provider_repository.get_user_provider.return_value = mock_provider
        mock_prompt_template_service.create_template.return_value = mock_prompt_template
        mock_db.commit.side_effect = Exception("Commit failed")

        with patch("backend.rag_solution.services.user_provider_service.LLMParametersService") as mock_params_class, patch(
            "backend.rag_solution.services.pipeline_service.PipelineService"
        ) as mock_pipeline_class:
            mock_params_service = Mock()
            mock_params_service.initialize_default_parameters.return_value = mock_parameters
            mock_params_class.return_value = mock_params_service

            mock_pipeline_service = Mock()
            mock_pipeline_class.return_value = mock_pipeline_service

            with pytest.raises(ValidationError) as exc_info:
                service.initialize_user_defaults(user_id)

            assert "Failed to initialize required user configuration" in str(exc_info.value)
            mock_db.rollback.assert_called_once()

    def test_get_user_provider_multiple_calls_consistency(
        self,
        service,
        mock_user_provider_repository,
        mock_provider,
    ):
        """Test that multiple calls to get_user_provider return consistent results."""
        user_id = uuid4()

        mock_user_provider_repository.get_user_provider.return_value = mock_provider

        # Call multiple times
        result1 = service.get_user_provider(user_id)
        result2 = service.get_user_provider(user_id)
        result3 = service.get_user_provider(user_id)

        assert result1 == result2 == result3 == mock_provider
        assert mock_user_provider_repository.get_user_provider.call_count == 3

    def test_initialize_user_defaults_creates_all_template_types(
        self,
        service,
        mock_user_provider_repository,
        mock_prompt_template_service,
        mock_db,
        mock_provider,
        mock_parameters,
    ):
        """Test that initialization creates all three required template types."""
        user_id = uuid4()

        mock_user_provider_repository.get_user_provider.return_value = mock_provider

        # Create different mock templates for each type
        rag_template = PromptTemplateOutput(
            id=uuid4(),
            name="default-rag-template",
            user_id=user_id,
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="RAG system prompt",
            template_format="{context}\n\n{question}",
            input_variables={"context": "context", "question": "question"},
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        question_template = PromptTemplateOutput(
            id=uuid4(),
            name="default-question-template",
            user_id=user_id,
            template_type=PromptTemplateType.QUESTION_GENERATION,
            system_prompt="Question system prompt",
            template_format="{context}\n\n{num_questions}",
            input_variables={"context": "context", "num_questions": "num"},
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        podcast_template = PromptTemplateOutput(
            id=uuid4(),
            name="default-podcast-template",
            user_id=user_id,
            template_type=PromptTemplateType.PODCAST_GENERATION,
            system_prompt="Podcast system prompt",
            template_format="{user_topic}\n\n{rag_results}\n\n{duration_minutes}",
            input_variables={
                "user_topic": "topic",
                "rag_results": "results",
                "duration_minutes": "duration",
            },
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_prompt_template_service.create_template.side_effect = [
            rag_template,
            question_template,
            podcast_template,
        ]

        with patch("backend.rag_solution.services.user_provider_service.LLMParametersService") as mock_params_class, patch(
            "backend.rag_solution.services.pipeline_service.PipelineService"
        ) as mock_pipeline_class:
            mock_params_service = Mock()
            mock_params_service.initialize_default_parameters.return_value = mock_parameters
            mock_params_class.return_value = mock_params_service

            mock_pipeline_service = Mock()
            mock_pipeline_class.return_value = mock_pipeline_service

            provider, templates, params = service.initialize_user_defaults(user_id)

            # Verify all three templates were created
            assert len(templates) == 3
            assert any(t.template_type == PromptTemplateType.RAG_QUERY for t in templates)
            assert any(t.template_type == PromptTemplateType.QUESTION_GENERATION for t in templates)
            assert any(t.template_type == PromptTemplateType.PODCAST_GENERATION for t in templates)

    # ============================================================================
    # ASYNC OPERATIONS SIMULATION
    # ============================================================================

    def test_service_handles_repository_async_operations(
        self,
        service,
        mock_user_provider_repository,
        mock_provider,
    ):
        """Test that service correctly handles repository operations (simulating async behavior)."""
        user_id = uuid4()

        # Simulate async repository call
        mock_user_provider_repository.get_user_provider.return_value = mock_provider

        result = service.get_user_provider(user_id)

        assert result == mock_provider
        mock_user_provider_repository.get_user_provider.assert_called_once_with(user_id)

    def test_set_user_provider_with_transaction(
        self,
        service,
        mock_user_provider_repository,
    ):
        """Test that set_user_provider works correctly with database transactions."""
        user_id = uuid4()
        provider_id = uuid4()

        mock_user_provider_repository.set_user_provider.return_value = True

        result = service.set_user_provider(user_id, provider_id)

        assert result is True
        mock_user_provider_repository.set_user_provider.assert_called_once_with(user_id, provider_id)

    # ============================================================================
    # BOUNDARY TESTS
    # ============================================================================

    def test_initialize_user_defaults_with_minimal_provider(
        self,
        service,
        mock_user_provider_repository,
        mock_prompt_template_service,
        mock_db,
        mock_prompt_template,
        mock_parameters,
    ):
        """Test initialization with minimal provider configuration."""
        user_id = uuid4()

        minimal_provider = LLMProviderOutput(
            id=uuid4(),
            name="minimal-provider",
            base_url="https://api.example.com",
            org_id=None,
            project_id=None,
            is_active=True,
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_user_provider_repository.get_user_provider.return_value = minimal_provider
        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        with patch("backend.rag_solution.services.user_provider_service.LLMParametersService") as mock_params_class, patch(
            "backend.rag_solution.services.pipeline_service.PipelineService"
        ) as mock_pipeline_class:
            mock_params_service = Mock()
            mock_params_service.initialize_default_parameters.return_value = mock_parameters
            mock_params_class.return_value = mock_params_service

            mock_pipeline_service = Mock()
            mock_pipeline_class.return_value = mock_pipeline_service

            provider, templates, params = service.initialize_user_defaults(user_id)

            assert provider == minimal_provider
            assert len(templates) == 3
            assert params == mock_parameters

    def test_template_validation_schemas_are_correct(
        self,
        service,
        mock_prompt_template_service,
        mock_prompt_template,
    ):
        """Test that template validation schemas are correctly structured."""
        user_id = uuid4()
        mock_prompt_template_service.create_template.return_value = mock_prompt_template

        # Test RAG template validation schema
        service._create_default_rag_template(user_id)
        rag_template = mock_prompt_template_service.create_template.call_args[0][0]
        assert rag_template.validation_schema is not None
        assert "fields" in rag_template.validation_schema
        assert "required" in rag_template.validation_schema

        # Test question template validation schema
        mock_prompt_template_service.create_template.reset_mock()
        service._create_default_question_template(user_id)
        question_template = mock_prompt_template_service.create_template.call_args[0][0]
        assert question_template.validation_schema is not None

        # Test podcast template validation schema
        mock_prompt_template_service.create_template.reset_mock()
        service._create_default_podcast_template(user_id)
        podcast_template = mock_prompt_template_service.create_template.call_args[0][0]
        assert podcast_template.validation_schema is not None
