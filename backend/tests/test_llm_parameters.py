"""Tests for LLM parameters functionality."""

import pytest
from sqlalchemy.orm import Session
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.schemas.llm_parameters_schema import (
    LLMParametersCreate,
    LLMParametersUpdate,
    LLMParametersResponse
)
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.repository.llm_parameters_repository import LLMParametersRepository
from core.custom_exceptions import NotFoundException, ValidationError

@pytest.fixture
def llm_params_service(db_session: Session) -> LLMParametersService:
    """Fixture for LLM parameters service."""
    return LLMParametersService(db_session)

@pytest.fixture
def llm_params_repository(db_session: Session) -> LLMParametersRepository:
    """Fixture for LLM parameters repository."""
    return LLMParametersRepository(db_session)

@pytest.fixture
def sample_params() -> LLMParametersCreate:
    """Fixture for sample LLM parameters."""
    return LLMParametersCreate(
        name="test_params",
        description="Test parameters",
        max_new_tokens=500,
        temperature=0.8,
        top_k=40,
        top_p=0.9,
        is_default=False
    )

class TestLLMParametersSchema:
    """Test LLM parameters schema validation."""

    def test_valid_parameters(self):
        """Test valid parameter creation."""
        params = LLMParametersCreate(
            name="test",
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0
        )
        assert params.name == "test"
        assert params.max_new_tokens == 100
        assert params.temperature == 0.7

    def test_invalid_max_tokens(self):
        """Test validation of max_new_tokens."""
        with pytest.raises(ValueError):
            LLMParametersCreate(
                name="test",
                max_new_tokens=3000  # > 2048
            )

    def test_invalid_temperature(self):
        """Test validation of temperature."""
        with pytest.raises(ValueError):
            LLMParametersCreate(
                name="test",
                temperature=2.5  # > 2.0
            )

    def test_invalid_top_p(self):
        """Test validation of top_p."""
        with pytest.raises(ValueError):
            LLMParametersCreate(
                name="test",
                top_p=1.5  # > 1.0
            )

    def test_min_tokens_validation(self):
        """Test min_new_tokens validation against max_new_tokens."""
        with pytest.raises(ValueError):
            LLMParametersCreate(
                name="test",
                max_new_tokens=100,
                min_new_tokens=200  # > max_new_tokens
            )

class TestLLMParametersRepository:
    """Test LLM parameters repository operations."""

    def test_create_parameters(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersCreate):
        """Test creating parameters."""
        created = llm_params_repository.create(sample_params)
        assert created.name == sample_params.name
        assert created.max_new_tokens == sample_params.max_new_tokens
        assert created.temperature == sample_params.temperature

    def test_get_parameters(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersCreate):
        """Test retrieving parameters."""
        created = llm_params_repository.create(sample_params)
        retrieved = llm_params_repository.get(created.id)
        assert retrieved is not None
        assert retrieved.name == sample_params.name

    def test_get_by_name(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersCreate):
        """Test retrieving parameters by name."""
        created = llm_params_repository.create(sample_params)
        retrieved = llm_params_repository.get_by_name(sample_params.name)
        assert retrieved is not None
        assert retrieved.name == sample_params.name

    def test_list_parameters(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersCreate):
        """Test listing parameters."""
        llm_params_repository.create(sample_params)
        params_list = llm_params_repository.list()
        assert len(params_list) > 0
        assert any(p.name == sample_params.name for p in params_list)

    def test_update_parameters(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersCreate):
        """Test updating parameters."""
        created = llm_params_repository.create(sample_params)
        update = LLMParametersUpdate(temperature=0.9)
        updated = llm_params_repository.update(created.id, update)
        assert updated is not None
        assert updated.temperature == 0.9

    def test_delete_parameters(self, llm_params_repository: LLMParametersRepository, sample_params: LLMParametersCreate):
        """Test deleting parameters."""
        created = llm_params_repository.create(sample_params)
        assert llm_params_repository.delete(created.id) is True
        assert llm_params_repository.get(created.id) is None

class TestLLMParametersService:
    """Test LLM parameters service operations."""

    def test_create_parameters(self, llm_params_service: LLMParametersService, sample_params: LLMParametersCreate):
        """Test creating parameters through service."""
        created = llm_params_service.create_parameters(sample_params)
        assert created.name == sample_params.name
        assert created.max_new_tokens == sample_params.max_new_tokens

    def test_create_duplicate_name(self, llm_params_service: LLMParametersService, sample_params: LLMParametersCreate):
        """Test creating parameters with duplicate name."""
        llm_params_service.create_parameters(sample_params)
        with pytest.raises(ValidationError):
            llm_params_service.create_parameters(sample_params)

    def test_get_parameters(self, llm_params_service: LLMParametersService, sample_params: LLMParametersCreate):
        """Test retrieving parameters through service."""
        created = llm_params_service.create_parameters(sample_params)
        retrieved = llm_params_service.get_parameters(created.id)
        assert retrieved.name == sample_params.name

    def test_get_nonexistent_parameters(self, llm_params_service: LLMParametersService):
        """Test retrieving non-existent parameters."""
        with pytest.raises(NotFoundException):
            llm_params_service.get_parameters(999)

    def test_update_parameters(self, llm_params_service: LLMParametersService, sample_params: LLMParametersCreate):
        """Test updating parameters through service."""
        created = llm_params_service.create_parameters(sample_params)
        update = LLMParametersUpdate(temperature=0.9)
        updated = llm_params_service.update_parameters(created.id, update)
        assert updated.temperature == 0.9

    def test_delete_parameters(self, llm_params_service: LLMParametersService, sample_params: LLMParametersCreate):
        """Test deleting parameters through service."""
        created = llm_params_service.create_parameters(sample_params)
        assert llm_params_service.delete_parameters(created.id) is True
        with pytest.raises(NotFoundException):
            llm_params_service.get_parameters(created.id)

    def test_default_parameters_management(self, llm_params_service: LLMParametersService):
        """Test default parameters management."""
        # Create first default parameters
        params1 = LLMParametersCreate(
            name="default1",
            is_default=True
        )
        created1 = llm_params_service.create_parameters(params1)
        assert created1.is_default is True

        # Create second default parameters
        params2 = LLMParametersCreate(
            name="default2",
            is_default=True
        )
        created2 = llm_params_service.create_parameters(params2)

        # First parameters should no longer be default
        updated1 = llm_params_service.get_parameters(created1.id)
        assert updated1.is_default is False
        assert created2.is_default is True

    def test_delete_default_parameters(self, llm_params_service: LLMParametersService):
        """Test attempting to delete default parameters."""
        params = LLMParametersCreate(
            name="default",
            is_default=True
        )
        created = llm_params_service.create_parameters(params)
        with pytest.raises(ValidationError):
            llm_params_service.delete_parameters(created.id)

    def test_set_default_parameters(self, llm_params_service: LLMParametersService, sample_params: LLMParametersCreate):
        """Test setting parameters as default."""
        created = llm_params_service.create_parameters(sample_params)
        updated = llm_params_service.set_default_parameters(created.id)
        assert updated.is_default is True
        
        # Verify it's returned by get_default_parameters
        default = llm_params_service.get_default_parameters()
        assert default.id == created.id
