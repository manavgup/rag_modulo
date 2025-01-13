"""Tests for LLM parameters functionality."""

import pytest
from sqlalchemy.orm import Session
from uuid import UUID
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.schemas.llm_parameters_schema import (
    LLMParametersInput,
    LLMParametersUpdate,
    LLMParametersResponse
)
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.repository.llm_parameters_repository import LLMParametersRepository
from rag_solution.services.user_service import UserService
from rag_solution.schemas.user_schema import UserInput
from core.custom_exceptions import NotFoundException, ValidationError

@pytest.fixture
def test_user(db_session: Session):
    """Create test user."""
    user_service = UserService(db_session)
    user = user_service.create_user(UserInput(
        ibm_id="test_ibm_id",
        email="test@example.com",
        name="Test User"
    ))
    return user

@pytest.fixture
def llm_params_service(db_session: Session) -> LLMParametersService:
    """Fixture for LLM parameters service."""
    return LLMParametersService(db_session)

@pytest.fixture
def llm_params_repository(db_session: Session) -> LLMParametersRepository:
    """Fixture for LLM parameters repository."""
    return LLMParametersRepository(db_session)

@pytest.fixture
def sample_params(test_user) -> LLMParametersInput:
    """Fixture for sample LLM parameters."""
    return LLMParametersInput(
        name="test_params",
        user_id=test_user.id,
        description="Test parameters",
        max_new_tokens=500,
        temperature=0.8,
        top_k=40,
        top_p=0.9,
        is_default=False
    )

class TestLLMParametersSchema:
    """Test LLM parameters schema validation."""

    def test_valid_parameters(self, test_user):
        """Test valid parameter creation."""
        params = LLMParametersInput(
            name="test",
            user_id=test_user.id,
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0
        )
        assert params.name == "test"
        assert params.max_new_tokens == 100
        assert params.temperature == 0.7

    def test_invalid_max_tokens(self, test_user):
        """Test validation of max_new_tokens."""
        with pytest.raises(ValueError):
            LLMParametersInput(
                name="test",
                user_id=test_user.id,
                max_new_tokens=3000  # > 2048
            )

    def test_invalid_temperature(self, test_user):
        """Test validation of temperature."""
        with pytest.raises(ValueError):
            LLMParametersInput(
                name="test",
                user_id=test_user.id,
                temperature=2.5  # > 2.0
            )

    def test_invalid_top_p(self, test_user):
        """Test validation of top_p."""
        with pytest.raises(ValueError):
            LLMParametersInput(
                name="test",
                user_id=test_user.id,
                top_p=1.5  # > 1.0
            )

    def test_min_tokens_validation(self, test_user):
        """Test min_new_tokens validation against max_new_tokens."""
        with pytest.raises(ValueError):
            LLMParametersInput(
                name="test",
                user_id=test_user.id,
                max_new_tokens=100,
                min_new_tokens=200  # > max_new_tokens
            )

class TestLLMParametersRepository:
    """Test LLM parameters repository operations."""

    def test_create_parameters(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersInput):
        """Test creating parameters."""
        created = llm_params_repository.create(sample_params)
        assert created.name == sample_params.name
        assert created.user_id == sample_params.user_id
        assert created.max_new_tokens == sample_params.max_new_tokens
        assert created.temperature == sample_params.temperature

    def test_get_parameters(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersInput):
        """Test retrieving parameters."""
        created = llm_params_repository.create(sample_params)
        retrieved = llm_params_repository.get(created.id)
        assert retrieved is not None
        assert retrieved.name == sample_params.name
        assert retrieved.user_id == sample_params.user_id

    def test_get_by_user_id(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersInput):
        """Test retrieving parameters by user ID."""
        created = llm_params_repository.create(sample_params)
        retrieved = llm_params_repository.get_by_user_id(sample_params.user_id)
        assert retrieved is not None
        assert len(retrieved) > 0
        assert any(p.name == sample_params.name for p in retrieved)

    def test_list_parameters(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersInput):
        """Test listing parameters."""
        llm_params_repository.create(sample_params)
        params_list = llm_params_repository.list()
        assert len(params_list) > 0
        assert any(p.name == sample_params.name for p in params_list)

    def test_update_parameters(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersInput):
        """Test updating parameters."""
        created = llm_params_repository.create(sample_params)
        update = LLMParametersUpdate(temperature=0.9)
        updated = llm_params_repository.update(created.id, update)
        assert updated is not None
        assert updated.temperature == 0.9

    def test_delete_parameters(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersInput):
        """Test deleting parameters."""
        created = llm_params_repository.create(sample_params)
        assert llm_params_repository.delete(created.id) is True
        assert llm_params_repository.get(created.id) is None

class TestLLMParametersService:
    """Test LLM parameters service operations."""

    def test_create_parameters(self, llm_params_service: LLMParametersService, sample_params: LLMParametersInput):
        """Test creating parameters through service."""
        created = llm_params_service.create_or_update_parameters(sample_params.user_id, sample_params)
        assert created.name == sample_params.name
        assert created.user_id == sample_params.user_id
        assert created.max_new_tokens == sample_params.max_new_tokens

    def test_create_duplicate_name(self, llm_params_service: LLMParametersService, sample_params: LLMParametersInput):
        """Test creating parameters with duplicate name."""
        llm_params_service.create_or_update_parameters(sample_params.user_id, sample_params)
        # Should update instead of raising error
        updated = llm_params_service.create_or_update_parameters(sample_params.user_id, sample_params)
        assert updated.name == sample_params.name

    def test_get_parameters(self, llm_params_service: LLMParametersService, sample_params: LLMParametersInput):
        """Test retrieving parameters through service."""
        created = llm_params_service.create_or_update_parameters(sample_params.user_id, sample_params)
        retrieved = llm_params_service.get_parameters(created.id)
        assert retrieved.name == sample_params.name
        assert retrieved.user_id == sample_params.user_id

    def test_get_nonexistent_parameters(self, llm_params_service: LLMParametersService):
        """Test retrieving non-existent parameters."""
        with pytest.raises(NotFoundException):
            llm_params_service.get_parameters(999)

    def test_update_parameters(self, llm_params_service: LLMParametersService, sample_params: LLMParametersInput):
        """Test updating parameters through service."""
        created = llm_params_service.create_or_update_parameters(sample_params.user_id, sample_params)
        update = LLMParametersUpdate(temperature=0.9)
        updated = llm_params_service.update_parameters(created.id, update)
        assert updated.temperature == 0.9

    def test_delete_parameters(self, llm_params_service: LLMParametersService, sample_params: LLMParametersInput):
        """Test deleting parameters through service."""
        created = llm_params_service.create_or_update_parameters(sample_params.user_id, sample_params)
        assert llm_params_service.delete_parameters(created.id) is True
        with pytest.raises(NotFoundException):
            llm_params_service.get_parameters(created.id)

    def test_user_default_parameters_management(self, llm_params_service: LLMParametersService, test_user):
        """Test user's default parameters management."""
        # Create first default parameters
        params1 = LLMParametersInput(
            name="default1",
            user_id=test_user.id,
            is_default=True
        )
        created1 = llm_params_service.create_or_update_parameters(test_user.id, params1)
        assert created1.is_default is True

        # Create second default parameters
        params2 = LLMParametersInput(
            name="default2",
            user_id=test_user.id,
            is_default=True
        )
        created2 = llm_params_service.create_or_update_parameters(test_user.id, params2)

        # First parameters should no longer be default
        updated1 = llm_params_service.get_parameters(created1.id)
        assert updated1.is_default is False
        assert created2.is_default is True

        # Get user's default parameters
        default = llm_params_service.get_user_default(test_user.id)
        assert default.id == created2.id

    def test_multiple_users_default_parameters(
        self,
        llm_params_service: LLMParametersService,
        test_user,
        db_session: Session
    ):
        """Test default parameters for multiple users."""
        # Create second user
        user_service = UserService(db_session)
        user2 = user_service.create_user(UserInput(
            ibm_id="test_ibm_id_2",
            email="test2@example.com",
            name="Test User 2"
        ))

        # Create default parameters for first user
        params1 = LLMParametersInput(
            name="user1_default",
            user_id=test_user.id,
            temperature=0.7,
            is_default=True
        )
        created1 = llm_params_service.create_or_update_parameters(test_user.id, params1)

        # Create default parameters for second user
        params2 = LLMParametersInput(
            name="user2_default",
            user_id=user2.id,
            temperature=0.8,
            is_default=True
        )
        created2 = llm_params_service.create_or_update_parameters(user2.id, params2)

        # Each user should have their own default
        default1 = llm_params_service.get_user_default(test_user.id)
        default2 = llm_params_service.get_user_default(user2.id)

        assert default1.id == created1.id
        assert default2.id == created2.id
        assert default1.temperature == 0.7
        assert default2.temperature == 0.8

    def test_delete_user_default_parameters(self, llm_params_service: LLMParametersService, test_user):
        """Test attempting to delete user's default parameters."""
        params = LLMParametersInput(
            name="default",
            user_id=test_user.id,
            is_default=True
        )
        created = llm_params_service.create_or_update_parameters(test_user.id, params)
        with pytest.raises(ValidationError):
            llm_params_service.delete_parameters(created.id)

    def test_set_user_default_parameters(
        self,
        llm_params_service: LLMParametersService,
        sample_params: LLMParametersInput
    ):
        """Test setting parameters as user's default."""
        created = llm_params_service.create_or_update_parameters(sample_params.user_id, sample_params)
        updated = llm_params_service.set_default_parameters(created.id)
        assert updated.is_default is True
        
        # Verify it's returned by get_user_default
        default = llm_params_service.get_user_default(sample_params.user_id)
        assert default.id == created.id
