"""Tests for PromptTemplateService."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.custom_exceptions import NotFoundError, ValidationError
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateOutput, PromptTemplateType
from rag_solution.services.prompt_template_service import PromptTemplateService


@pytest.fixture
def db_session() -> Mock:
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def template_service(db_session: Mock) -> PromptTemplateService:
    """Create a PromptTemplateService instance."""
    # We use a MagicMock for the repository so we can mock its methods.
    repository_mock = MagicMock()
    service = PromptTemplateService(db_session)
    service.repository = repository_mock
    return service


@pytest.fixture
def sample_user_id() -> UUID4:
    """Create a sample user ID."""
    return uuid4()


@pytest.fixture
def sample_template_input(sample_user_id: UUID4) -> PromptTemplateInput:
    """Create a sample template input."""
    return PromptTemplateInput(
        user_id=sample_user_id,
        name="test-template",
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a helpful assistant.",
        template_format="{context}\n\n{question}",
        input_variables={"context": "Context for the question", "question": "User's question"},
        example_inputs={"context": "Sample context", "question": "Sample question"},
        is_default=True,
        max_context_length=1000,
        validation_schema={
            "model": "PromptVariables",
            "fields": {"context": {"type": "str", "min_length": 1}, "question": {"type": "str", "min_length": 1}},
            "required": ["context", "question"],
        },
    )


@pytest.fixture
def sample_template_model(sample_user_id: UUID4, sample_template_input: PromptTemplateInput) -> PromptTemplate:
    """Create a sample template model."""
    return PromptTemplate(
        id=uuid4(),
        user_id=sample_user_id,
        name=sample_template_input.name,
        template_type=sample_template_input.template_type,
        system_prompt=sample_template_input.system_prompt,
        template_format=sample_template_input.template_format,
        input_variables=sample_template_input.input_variables,
        example_inputs=sample_template_input.example_inputs,
        validation_schema=sample_template_input.validation_schema,
        is_default=sample_template_input.is_default,
        max_context_length=sample_template_input.max_context_length,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.mark.atomic
def test_create_template(template_service: PromptTemplateService, sample_user_id: UUID4) -> None:
    """Test creating a template."""
    # Mock repository response
    mock_template = Mock(spec=PromptTemplate, template_type=PromptTemplateType.RAG_QUERY)

    with patch.object(template_service.repository, "create_template", return_value=mock_template) as mock_create:
        template_input = PromptTemplateInput(
            user_id=sample_user_id,
            name="Test Template",
            template_format="Test {context}",
            template_type=PromptTemplateType.RAG_QUERY,
            input_variables={"context": "The context to use"},
            max_context_length=1000,
        )

        result = template_service.create_template(template_input)

        assert result is not None
        mock_create.assert_called_once()


def test_create_template_with_fixtures(
    template_service: PromptTemplateService,
    sample_user_id: UUID4,
    sample_template_input: PromptTemplateInput,
    sample_template_model: PromptTemplate,
) -> None:
    """Test template creation with fixtures."""
    with patch.object(template_service.repository, "create_template", return_value=sample_template_model) as mock_create:
        result = template_service.create_template(sample_template_input)

        assert isinstance(result, PromptTemplateOutput)
        assert result.name == sample_template_input.name
        assert result.template_type == sample_template_input.template_type
        mock_create.assert_called_once()


def test_get_by_type(template_service: PromptTemplateService, sample_template_model: PromptTemplate) -> None:
    """Test template retrieval by type."""
    with patch.object(template_service.repository, "get_by_user_id_and_type", return_value=[sample_template_model]) as mock_get:
        result = template_service.get_by_type(sample_template_model.user_id, sample_template_model.template_type)

        assert isinstance(result, PromptTemplateOutput)
        assert result.id == sample_template_model.id
        assert result.name == sample_template_model.name
        mock_get.assert_called_once()

    # Test nonexistent template
    with patch.object(template_service.repository, "get_by_user_id_and_type", return_value=[]):
        assert template_service.get_by_type(sample_template_model.user_id, PromptTemplateType.QUESTION_GENERATION) is None


def test_get_user_templates(template_service: PromptTemplateService, sample_user_id: UUID4, sample_template_model: PromptTemplate) -> None:
    """Test retrieving user's templates."""
    with patch.object(template_service.repository, "get_by_user_id", return_value=[sample_template_model]):
        results = template_service.get_user_templates(sample_user_id)

        assert len(results) == 1
        assert isinstance(results[0], PromptTemplateOutput)
        assert results[0].id == sample_template_model.id


def test_get_by_type_fallback(template_service: PromptTemplateService, sample_user_id: UUID4, sample_template_model: PromptTemplate) -> None:
    """Test template retrieval by type with fallback."""
    # Test user has a template of this type
    with patch.object(template_service.repository, "get_by_user_id_and_type", return_value=[sample_template_model]):
        result = template_service.get_by_type(sample_user_id, PromptTemplateType.RAG_QUERY)

        assert isinstance(result, PromptTemplateOutput)
        assert result.template_type == PromptTemplateType.RAG_QUERY

    # Test no template found
    with patch.object(template_service.repository, "get_by_user_id_and_type", return_value=[]):
        result = template_service.get_by_type(sample_user_id, PromptTemplateType.RAG_QUERY)
        assert result is None


def test_delete_template(template_service: PromptTemplateService, sample_user_id: UUID4) -> None:
    """Test template deletion."""
    with patch.object(template_service.repository, "delete_user_template", return_value=None):
        assert template_service.delete_template(sample_user_id, uuid4()) is True

    with patch.object(template_service.repository, "delete_user_template", side_effect=Exception("Delete failed")):
        assert template_service.delete_template(sample_user_id, uuid4()) is False


def test_format_prompt(template_service: PromptTemplateService, sample_template_model: PromptTemplate) -> None:
    """Test prompt formatting."""
    with patch.object(template_service.repository, "get_by_id", return_value=sample_template_model):
        variables = {"context": "Test context", "question": "Test question"}

        result = template_service.format_prompt_by_id(sample_template_model.id, variables)

        assert isinstance(result, str)
        assert variables["context"] in result
        assert variables["question"] in result
        if sample_template_model.system_prompt:
            assert sample_template_model.system_prompt in result

    # Test missing variables
    with patch.object(template_service.repository, "get_by_id", return_value=sample_template_model), pytest.raises(ValidationError):
        template_service.format_prompt_by_id(sample_template_model.id, {"context": "Test"})

    # Test nonexistent template
    with patch.object(template_service.repository, "get_by_id", return_value=None), pytest.raises(NotFoundError):
        template_service.format_prompt_by_id(uuid4(), variables)


def test_apply_context_strategy(template_service: PromptTemplateService, sample_template_model: PromptTemplate) -> None:
    """Test context strategy application."""
    contexts = ["First context chunk", "Second context chunk", "Third context chunk"]

    # Test default strategy
    sample_template_model.context_strategy = None
    with patch.object(template_service.repository, "get_by_id", return_value=sample_template_model):
        result = template_service.apply_context_strategy(sample_template_model.id, contexts)
        assert isinstance(result, str)
        assert all(context in result for context in contexts)

    # Test custom strategy
    sample_template_model.context_strategy = {
        "max_chunks": 2,
        "chunk_separator": " | ",
        "ordering": "relevance",
        "truncation": "end",
    }
    sample_template_model.max_context_length = 10
    with patch.object(template_service.repository, "get_by_id", return_value=sample_template_model):
        result = template_service.apply_context_strategy(sample_template_model.id, contexts)
        assert isinstance(result, str)
        assert len(result.split(" | ")) == 2  # Only 2 chunks due to max_chunks
        assert all(len(chunk) <= 10 for chunk in result.split(" | "))  # Truncated chunks

    # Test nonexistent template
    with patch.object(template_service.repository, "get_by_id", return_value=None), pytest.raises(NotFoundError):
        template_service.apply_context_strategy(uuid4(), contexts)


if __name__ == "__main__":
    pytest.main([__file__])
