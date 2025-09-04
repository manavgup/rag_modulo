"""Tests for Prompt Templates router endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.services.prompt_template_service import PromptTemplateService

# Test data
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_TEMPLATE_ID = UUID("87654321-4321-8765-4321-876543210987")


@pytest.fixture
@pytest.mark.api
def test_template_data():
    return {
        "name": "Test Template",
        "provider": "test_provider",
        "provider_config_id": str(uuid4()),
        "description": "Test description",
        "system_prompt": "You are a helpful assistant",
        "context_prefix": "Context:\n",
        "query_prefix": "Question:\n",
        "answer_prefix": "Answer:\n",
        "is_default": False,
        "input_variables": ["topic", "aspect"],
        "template_format": "Explain {topic}, focusing on {aspect}",
    }


@pytest.fixture
def mock_prompt_template_service(mocker):
    service = mocker.Mock(spec=PromptTemplateService)

    # Mock get_templates
    service.get_templates.return_value = [
        PromptTemplate(
            id=TEST_TEMPLATE_ID,
            user_id=TEST_USER_ID,
            name="Test Template",
            provider="test_provider",
            provider_config_id=str(uuid4()),
            description="Test description",
            system_prompt="You are a helpful assistant",
            context_prefix="Context:\n",
            query_prefix="Question:\n",
            answer_prefix="Answer:\n",
            is_default=False,
            input_variables=["topic", "aspect"],
            template_format="Explain {topic}, focusing on {aspect}",
        )
    ]

    # Mock create_template
    service.create_template.return_value = PromptTemplate(
        id=TEST_TEMPLATE_ID,
        user_id=TEST_USER_ID,
        name="Test Template",
        provider="test_provider",
        provider_config_id=str(uuid4()),
        description="Test description",
        system_prompt="You are a helpful assistant",
        context_prefix="Context:\n",
        query_prefix="Question:\n",
        answer_prefix="Answer:\n",
        is_default=False,
        input_variables=["topic", "aspect"],
        template_format="Explain {topic}, focusing on {aspect}",
    )

    # Mock update_template
    service.update_template.return_value = PromptTemplate(
        id=TEST_TEMPLATE_ID,
        user_id=TEST_USER_ID,
        name="Updated Template",
        provider="test_provider",
        provider_config_id=str(uuid4()),
        description="Updated description",
        system_prompt="You are a very helpful assistant",
        context_prefix="Context:\n",
        query_prefix="Question:\n",
        answer_prefix="Answer:\n",
        is_default=False,
        input_variables=["topic", "aspect", "depth"],
        template_format="Explain {topic}, focusing on {aspect} with {depth} detail",
    )

    # Mock delete_template
    service.delete_template.return_value = True

    # Mock set_default_template
    service.set_default_template.return_value = PromptTemplate(
        id=TEST_TEMPLATE_ID,
        user_id=TEST_USER_ID,
        name="Default Template",
        provider="test_provider",
        provider_config_id=str(uuid4()),
        description="Default template",
        system_prompt="You are a helpful assistant",
        context_prefix="Context:\n",
        query_prefix="Question:\n",
        answer_prefix="Answer:\n",
        is_default=True,
        input_variables=["topic", "aspect"],
        template_format="Explain {topic}, focusing on {aspect}",
    )

    return service


@pytest.mark.asyncio
async def test_get_prompt_templates(client: AsyncClient, mock_prompt_template_service, mock_auth_user):
    """Test GET /api/users/{user_id}/prompt-templates endpoint."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Make request
    response = await client.get(f"/api/users/{TEST_USER_ID}/prompt-templates")

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["id"] == str(TEST_TEMPLATE_ID)
    assert data[0]["user_id"] == str(TEST_USER_ID)

    # Verify service called
    mock_prompt_template_service.get_templates.assert_called_once_with(TEST_USER_ID)


@pytest.mark.asyncio
async def test_create_prompt_template(
    client: AsyncClient, mock_prompt_template_service, mock_auth_user, test_template_data
):
    """Test POST /api/users/{user_id}/prompt-templates endpoint."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Make request
    response = await client.post(f"/api/users/{TEST_USER_ID}/prompt-templates", json=test_template_data)

    # Assert response
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(TEST_TEMPLATE_ID)
    assert data["user_id"] == str(TEST_USER_ID)

    # Verify service called
    mock_prompt_template_service.create_template.assert_called_once()


@pytest.mark.asyncio
async def test_update_prompt_template(
    client: AsyncClient, mock_prompt_template_service, mock_auth_user, test_template_data
):
    """Test PUT /api/users/{user_id}/prompt-templates/{template_id} endpoint."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Update data
    test_template_data["name"] = "Updated Template"
    test_template_data["description"] = "Updated description"
    test_template_data["input_variables"] = ["topic", "aspect", "depth"]
    test_template_data["template_format"] = "Explain {topic}, focusing on {aspect} with {depth} detail"

    # Make request
    response = await client.put(
        f"/api/users/{TEST_USER_ID}/prompt-templates/{TEST_TEMPLATE_ID}", json=test_template_data
    )

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(TEST_TEMPLATE_ID)
    assert data["name"] == "Updated Template"
    assert data["description"] == "Updated description"
    assert "depth" in data["input_variables"]

    # Verify service called
    mock_prompt_template_service.update_template.assert_called_once()


@pytest.mark.asyncio
async def test_delete_prompt_template(client: AsyncClient, mock_prompt_template_service, mock_auth_user):
    """Test DELETE /api/users/{user_id}/prompt-templates/{template_id} endpoint."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Make request
    response = await client.delete(f"/api/users/{TEST_USER_ID}/prompt-templates/{TEST_TEMPLATE_ID}")

    # Assert response
    assert response.status_code == 200
    assert response.json() is True

    # Verify service called
    mock_prompt_template_service.delete_template.assert_called_once_with(TEST_TEMPLATE_ID)


@pytest.mark.asyncio
async def test_set_default_prompt_template(client: AsyncClient, mock_prompt_template_service, mock_auth_user):
    """Test PUT /api/users/{user_id}/prompt-templates/{template_id}/default endpoint."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Make request
    response = await client.put(f"/api/users/{TEST_USER_ID}/prompt-templates/{TEST_TEMPLATE_ID}/default")

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(TEST_TEMPLATE_ID)
    assert data["is_default"] is True

    # Verify service called
    mock_prompt_template_service.set_default_template.assert_called_once_with(TEST_TEMPLATE_ID)


@pytest.mark.asyncio
async def test_get_prompt_templates_unauthorized(client: AsyncClient):
    """Test unauthorized access to GET endpoint."""
    response = await client.get(f"/api/users/{TEST_USER_ID}/prompt-templates")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_prompt_templates_wrong_user(client: AsyncClient, mock_auth_user):
    """Test accessing templates with wrong user ID."""
    # Mock auth user with different ID
    different_user_id = uuid4()
    mock_auth_user(different_user_id)

    response = await client.get(f"/api/users/{TEST_USER_ID}/prompt-templates")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_prompt_template_invalid_data(client: AsyncClient, mock_auth_user):
    """Test creating template with invalid data."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Invalid data (missing required fields)
    invalid_data = {"name": "Test Template"}

    response = await client.post(f"/api/users/{TEST_USER_ID}/prompt-templates", json=invalid_data)
    assert response.status_code == 422
