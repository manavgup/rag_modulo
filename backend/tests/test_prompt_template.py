"""Tests for prompt template functionality."""

import pytest
from uuid import uuid4, UUID
from sqlalchemy.orm import Session

from core.custom_exceptions import (
    PromptTemplateNotFoundError,
    DuplicatePromptTemplateError,
    InvalidPromptTemplateError
)
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.repository.prompt_template_repository import PromptTemplateRepository
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateCreate,
    PromptTemplateUpdate
)

# Test Data
SAMPLE_TEMPLATE = {
    "name": "test_template",
    "provider": "watsonx",
    "description": "Test template",
    "system_prompt": "You are a test assistant",
    "context_prefix": "Context:",
    "query_prefix": "Question:",
    "answer_prefix": "Answer:",
    "is_default": False
}

@pytest.fixture
def template_create_data():
    """Fixture for template creation data."""
    return PromptTemplateCreate(**SAMPLE_TEMPLATE)

@pytest.fixture
def template_update_data():
    """Fixture for template update data."""
    return PromptTemplateUpdate(
        name="updated_template",
        description="Updated description",
        system_prompt="Updated system prompt"
    )

@pytest.fixture
def prompt_template_repository(db_session: Session):
    """Fixture for prompt template repository."""
    return PromptTemplateRepository(db_session)

@pytest.fixture
def prompt_template_service(db_session: Session):
    """Fixture for prompt template service."""
    return PromptTemplateService(db_session)

@pytest.fixture
def sample_template(prompt_template_repository: PromptTemplateRepository, template_create_data: PromptTemplateCreate):
    """Fixture for a sample template in the database."""
    return prompt_template_repository.create(template_create_data)

# Repository Tests
def test_create_template(
    prompt_template_repository: PromptTemplateRepository,
    template_create_data: PromptTemplateCreate
):
    """Test creating a new template."""
    template = prompt_template_repository.create(template_create_data)
    assert template.name == template_create_data.name
    assert template.provider == template_create_data.provider
    assert template.system_prompt == template_create_data.system_prompt

def test_create_duplicate_template(
    prompt_template_repository: PromptTemplateRepository,
    template_create_data: PromptTemplateCreate,
    sample_template: PromptTemplate
):
    """Test creating a duplicate template raises error."""
    with pytest.raises(DuplicatePromptTemplateError):
        prompt_template_repository.create(template_create_data)

def test_get_template(
    prompt_template_repository: PromptTemplateRepository,
    sample_template: PromptTemplate
):
    """Test getting a template by ID."""
    template = prompt_template_repository.get(UUID(sample_template.id))
    assert template.id == sample_template.id
    assert template.name == sample_template.name

def test_get_nonexistent_template(prompt_template_repository: PromptTemplateRepository):
    """Test getting a nonexistent template raises error."""
    with pytest.raises(PromptTemplateNotFoundError):
        prompt_template_repository.get(uuid4())

def test_get_by_provider(
    prompt_template_repository: PromptTemplateRepository,
    sample_template: PromptTemplate
):
    """Test getting templates by provider."""
    templates = prompt_template_repository.get_by_provider(sample_template.provider)
    assert len(templates) == 1
    assert templates[0].id == sample_template.id

def test_update_template(
    prompt_template_repository: PromptTemplateRepository,
    sample_template: PromptTemplate,
    template_update_data: PromptTemplateUpdate
):
    """Test updating a template."""
    updated = prompt_template_repository.update(
        UUID(sample_template.id),
        template_update_data
    )
    assert updated.name == template_update_data.name
    assert updated.description == template_update_data.description

def test_delete_template(
    prompt_template_repository: PromptTemplateRepository,
    sample_template: PromptTemplate
):
    """Test deleting a template."""
    prompt_template_repository.delete(UUID(sample_template.id))
    with pytest.raises(PromptTemplateNotFoundError):
        prompt_template_repository.get(UUID(sample_template.id))

def test_delete_default_template(
    prompt_template_repository: PromptTemplateRepository,
    template_create_data: PromptTemplateCreate
):
    """Test deleting a default template raises error."""
    template_create_data.is_default = True
    template = prompt_template_repository.create(template_create_data)
    
    with pytest.raises(InvalidPromptTemplateError):
        prompt_template_repository.delete(UUID(template.id))

# Service Tests
def test_service_create_template(
    prompt_template_service: PromptTemplateService,
    template_create_data: PromptTemplateCreate
):
    """Test creating a template through service."""
    response = prompt_template_service.create_template(template_create_data)
    assert response.name == template_create_data.name
    assert response.provider == template_create_data.provider

def test_service_get_template(
    prompt_template_service: PromptTemplateService,
    sample_template: PromptTemplate
):
    """Test getting a template through service."""
    response = prompt_template_service.get_template(UUID(sample_template.id))
    assert response.id == UUID(sample_template.id)
    assert response.name == sample_template.name

def test_service_create_example_template(prompt_template_service: PromptTemplateService):
    """Test creating an example template."""
    response = prompt_template_service.create_example_template("watsonx")
    print(f"******Response: {response}")
    assert response is not None
    assert response.provider == "watsonx"
    assert "IBM Watsonx" in response.description

def test_service_initialize_default_templates(prompt_template_service: PromptTemplateService):
    """Test initializing default templates from config."""
    prompt_template_service.initialize_default_templates()
    
    # Check watsonx default template
    watsonx_template = prompt_template_service.get_default_template("watsonx")
    assert watsonx_template is not None
    assert watsonx_template.is_default
    
    # Check openai default template
    openai_template = prompt_template_service.get_default_template("openai")
    assert openai_template is not None
    assert openai_template.is_default

def test_service_list_templates(
    prompt_template_service: PromptTemplateService,
    sample_template: PromptTemplate
):
    """Test listing all templates."""
    templates = prompt_template_service.list_templates()
    assert len(templates) >= 1
    assert any(t.id == UUID(sample_template.id) for t in templates)
