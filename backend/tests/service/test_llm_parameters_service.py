"""Integration tests for LLMParametersService."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from core.custom_exceptions import NotFoundException
from rag_solution.models.user import User
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput
from rag_solution.schemas.user_schema import UserInput
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.user_service import UserService

# -------------------------------------------
# 🔧 FIXTURES
# -------------------------------------------


@pytest.fixture
def test_llm_parameters(base_user: User) -> LLMParametersInput:
    """Create sample LLM parameters input."""
    return LLMParametersInput(
        name="test_params",
        description="Test parameters",
        user_id=base_user.id,
        max_new_tokens=500,
        temperature=0.8,
        top_k=40,
        top_p=0.9,
        repetition_penalty=1.1,
        is_default=False,
    )


@pytest.fixture
def test_parameters_service(db_session: Session) -> LLMParametersService:
    """Create LLMParametersService instance."""
    return LLMParametersService(db_session)


# -------------------------------------------
# 🧪 SCHEMA VALIDATION TESTS
# -------------------------------------------


class TestLLMParametersSchema:
    """Test LLM parameters schema validation."""

    def test_valid_parameters(self, base_user: User) -> None:
        """Test valid parameter creation."""
        params = LLMParametersInput(
            name="test",
            description="Test parameters",
            user_id=base_user.id,
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.1,
        )
        assert params.name == "test"
        assert params.max_new_tokens == 100
        assert params.temperature == 0.7
        assert params.repetition_penalty == 1.1

    def test_invalid_max_new_tokens_high(self, base_user: User) -> None:
        """Test validation of max_new_tokens."""
        with pytest.raises(ValueError):
            LLMParametersInput(
                name="test",
                description="Test parameters",
                user_id=base_user.id,
                max_new_tokens=3000,  # > 2048
            )

    def test_invalid_temperature_high(self, base_user: User) -> None:
        """Test validation of temperature."""
        with pytest.raises(ValueError):
            LLMParametersInput(
                name="test",
                description="Test parameters",
                user_id=base_user.id,
                temperature=2.5,  # > 2.0
            )

    def test_invalid_top_p(self, base_user: User) -> None:
        """Test validation of top_p."""
        with pytest.raises(ValueError):
            LLMParametersInput(
                name="test",
                description="Test parameters",
                user_id=base_user.id,
                top_p=1.5,  # > 1.0
            )

    def test_invalid_repetition_penalty(self, base_user: User) -> None:
        """Test validation of repetition_penalty."""
        with pytest.raises(ValueError):
            LLMParametersInput(
                name="test",
                description="Test parameters",
                user_id=base_user.id,
                repetition_penalty=0.5,  # < 1.0
            )


# -------------------------------------------
# 🧪 SERVICE OPERATION TESTS
# -------------------------------------------


def test_create_parameters(base_user: User, test_parameters_service: LLMParametersService, test_llm_parameters: LLMParametersInput) -> None:
    """Test creating parameters through service."""
    created = test_parameters_service.create_parameters(test_llm_parameters)

    assert isinstance(created, LLMParametersOutput)
    assert created.name == test_llm_parameters.name
    assert created.max_new_tokens == test_llm_parameters.max_new_tokens
    assert created.repetition_penalty == test_llm_parameters.repetition_penalty


def test_create_duplicate_name(base_user: User, test_parameters_service: LLMParametersService, test_llm_parameters: LLMParametersInput) -> None:
    """Test creating parameters with duplicate name."""
    test_parameters_service.create_parameters(test_llm_parameters)

    # Should update instead of raising error
    updated = test_parameters_service.create_parameters(test_llm_parameters)
    assert updated.name == test_llm_parameters.name


def test_get_parameters(base_user: User, test_parameters_service: LLMParametersService, test_llm_parameters: LLMParametersInput) -> None:
    """Test retrieving parameters through service."""
    test_parameters_service.create_parameters(test_llm_parameters)

    retrieved = test_parameters_service.get_user_parameters(test_llm_parameters.user_id)
    assert len(retrieved) > 0
    assert any(param.name == test_llm_parameters.name for param in retrieved)


def test_get_nonexistent_user_parameters(test_parameters_service: LLMParametersService) -> None:
    """Test retrieving parameters for non-existent user."""
    retrieved = test_parameters_service.get_user_parameters(uuid4())
    assert len(retrieved) == 0


def test_update_parameters(base_user: User, test_parameters_service: LLMParametersService, test_llm_parameters: LLMParametersInput) -> None:
    """Test updating parameters through service."""
    created = test_parameters_service.create_parameters(test_llm_parameters)

    update = LLMParametersInput(
        name="updated_params",
        description="Updated parameters",
        user_id=base_user.id,
        temperature=0.9,
        max_new_tokens=500,
        top_k=40,
        top_p=0.9,
        repetition_penalty=1.2,
    )
    updated = test_parameters_service.update_parameters(created.id, update)
    assert updated.temperature == 0.9
    assert updated.name == "updated_params"
    assert updated.repetition_penalty == 1.2


def test_delete_parameters(base_user: User, test_parameters_service: LLMParametersService, test_llm_parameters: LLMParametersInput) -> None:
    """Test deleting parameters through service."""
    created = test_parameters_service.create_parameters(test_llm_parameters)

    test_parameters_service.delete_parameters(created.id)
    with pytest.raises(NotFoundException):
        test_parameters_service.update_parameters(created.id, test_llm_parameters)


# -------------------------------------------
# 🧪 DEFAULT PARAMETERS TESTS
# -------------------------------------------


def test_user_default_parameters_management(test_parameters_service: LLMParametersService, base_user: User) -> None:
    """Test user's default parameters management."""
    # Create first default parameters
    params1 = LLMParametersInput(
        name="default1",
        description="Default parameters 1",
        user_id=base_user.id,
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        is_default=True,
    )
    created1 = test_parameters_service.create_parameters(params1)
    assert created1.is_default is True

    # Create second default parameters
    params2 = LLMParametersInput(
        name="default2",
        description="Default parameters 2",
        user_id=base_user.id,
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        is_default=True,
    )
    created2 = test_parameters_service.create_parameters(params2)

    # First parameters should no longer be default
    params_list = test_parameters_service.get_user_parameters(base_user.id)
    param1 = next(p for p in params_list if p.id == created1.id)
    assert param1.is_default is False
    assert created2.is_default is True


def test_multiple_users_default_parameters(test_parameters_service: LLMParametersService, base_user: User, db_session: Session) -> None:
    """Test default parameters for multiple users."""
    user_service = UserService(db_session)

    # Create second user
    user2 = user_service.create_user(UserInput(ibm_id="test_ibm_id_2", email="test2@example.com", name="Test User 2"))

    # Create default parameters for first user
    params1 = LLMParametersInput(
        name="user1_default",
        description="User 1 default parameters",
        user_id=base_user.id,
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        is_default=True,
    )
    created1 = test_parameters_service.create_parameters(params1)

    # Create default parameters for second user
    params2 = LLMParametersInput(
        name="user2_default",
        description="User 2 default parameters",
        user_id=user2.id,
        max_new_tokens=100,
        temperature=0.8,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.2,
        is_default=True,
    )
    created2 = test_parameters_service.create_parameters(params2)

    # Each user should have their own default
    params_list1 = test_parameters_service.get_user_parameters(base_user.id)
    params_list2 = test_parameters_service.get_user_parameters(user2.id)

    default1 = next(p for p in params_list1 if p.is_default)
    default2 = next(p for p in params_list2 if p.is_default)

    assert default1.id == created1.id
    assert default2.id == created2.id
    assert default1.temperature == 0.7
    assert default2.temperature == 0.8
    assert default1.repetition_penalty == 1.1
    assert default2.repetition_penalty == 1.2


def test_set_default_parameters(base_user: User, test_parameters_service: LLMParametersService, test_llm_parameters: LLMParametersInput) -> None:
    """Test setting parameters as default."""
    created = test_parameters_service.create_parameters(test_llm_parameters)
    updated = test_parameters_service.set_default_parameters(created.id)

    assert updated.is_default is True
    # Verify it's returned as default in parameters list
    params_list = test_parameters_service.get_user_parameters(base_user.id)
    default_param = next(p for p in params_list if p.is_default)
    assert default_param.id == created.id


if __name__ == "__main__":
    pytest.main([__file__])
