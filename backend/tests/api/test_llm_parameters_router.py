"""Tests for LLM Parameters router endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.services.llm_parameters_service import LLMParametersService

# Test data
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_PARAMETER_ID = UUID("87654321-4321-8765-4321-876543210987")


@pytest.fixture
def test_parameter_data():
    return {
        "name": "Test Parameters",
        "provider_id": str(uuid4()),
        "temperature": 0.7,
        "max_tokens": 1000,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "is_default": False,
        "stop_sequences": [],
        "additional_params": {},
    }


@pytest.fixture
def mock_llm_parameters_service(mocker):
    service = mocker.Mock(spec=LLMParametersService)

    # Mock get_parameters
    service.get_parameters.return_value = [
        LLMParameters(
            id=TEST_PARAMETER_ID,
            user_id=TEST_USER_ID,
            name="Test Parameters",
            provider_id=str(uuid4()),
            temperature=0.7,
            max_tokens=1000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            is_default=False,
        )
    ]

    # Mock create_parameters
    service.create_parameters.return_value = LLMParameters(
        id=TEST_PARAMETER_ID,
        user_id=TEST_USER_ID,
        name="Test Parameters",
        provider_id=str(uuid4()),
        temperature=0.7,
        max_tokens=1000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        is_default=False,
    )

    # Mock update_parameters
    service.update_parameters.return_value = LLMParameters(
        id=TEST_PARAMETER_ID,
        user_id=TEST_USER_ID,
        name="Updated Parameters",
        provider_id=str(uuid4()),
        temperature=0.8,
        max_tokens=2000,
        top_p=0.9,
        frequency_penalty=0.1,
        presence_penalty=0.1,
        is_default=False,
    )

    # Mock delete_parameters
    service.delete_parameters.return_value = True

    # Mock set_default_parameters
    service.set_default_parameters.return_value = LLMParameters(
        id=TEST_PARAMETER_ID,
        user_id=TEST_USER_ID,
        name="Default Parameters",
        provider_id=str(uuid4()),
        temperature=0.7,
        max_tokens=1000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        is_default=True,
    )

    return service


@pytest.mark.asyncio
async def test_get_llm_parameters(client: AsyncClient, mock_llm_parameters_service, mock_auth_user):
    """Test GET /api/users/{user_id}/llm-parameters endpoint."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Make request
    response = await client.get(f"/api/users/{TEST_USER_ID}/llm-parameters")

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["id"] == str(TEST_PARAMETER_ID)
    assert data[0]["user_id"] == str(TEST_USER_ID)

    # Verify service called
    mock_llm_parameters_service.get_parameters.assert_called_once_with(TEST_USER_ID)


@pytest.mark.asyncio
async def test_create_llm_parameters(
    client: AsyncClient, mock_llm_parameters_service, mock_auth_user, test_parameter_data
):
    """Test POST /api/users/{user_id}/llm-parameters endpoint."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Make request
    response = await client.post(f"/api/users/{TEST_USER_ID}/llm-parameters", json=test_parameter_data)

    # Assert response
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(TEST_PARAMETER_ID)
    assert data["user_id"] == str(TEST_USER_ID)

    # Verify service called
    mock_llm_parameters_service.create_parameters.assert_called_once()


@pytest.mark.asyncio
async def test_update_llm_parameters(
    client: AsyncClient, mock_llm_parameters_service, mock_auth_user, test_parameter_data
):
    """Test PUT /api/users/{user_id}/llm-parameters/{parameter_id} endpoint."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Update data
    test_parameter_data["name"] = "Updated Parameters"
    test_parameter_data["temperature"] = 0.8

    # Make request
    response = await client.put(
        f"/api/users/{TEST_USER_ID}/llm-parameters/{TEST_PARAMETER_ID}", json=test_parameter_data
    )

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(TEST_PARAMETER_ID)
    assert data["name"] == "Updated Parameters"
    assert data["temperature"] == 0.8

    # Verify service called
    mock_llm_parameters_service.update_parameters.assert_called_once()


@pytest.mark.asyncio
async def test_delete_llm_parameters(client: AsyncClient, mock_llm_parameters_service, mock_auth_user):
    """Test DELETE /api/users/{user_id}/llm-parameters/{parameter_id} endpoint."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Make request
    response = await client.delete(f"/api/users/{TEST_USER_ID}/llm-parameters/{TEST_PARAMETER_ID}")

    # Assert response
    assert response.status_code == 200
    assert response.json() is True

    # Verify service called
    mock_llm_parameters_service.delete_parameters.assert_called_once_with(TEST_PARAMETER_ID)


@pytest.mark.asyncio
async def test_set_default_llm_parameters(
    client: AsyncClient, mock_llm_parameters_service, mock_auth_user
):
    """Test PUT /api/users/{user_id}/llm-parameters/{parameter_id}/default endpoint."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Make request
    response = await client.put(f"/api/users/{TEST_USER_ID}/llm-parameters/{TEST_PARAMETER_ID}/default")

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(TEST_PARAMETER_ID)
    assert data["is_default"] is True

    # Verify service called
    mock_llm_parameters_service.set_default_parameters.assert_called_once_with(TEST_PARAMETER_ID)


@pytest.mark.asyncio
async def test_get_llm_parameters_unauthorized(client: AsyncClient):
    """Test unauthorized access to GET endpoint."""
    response = await client.get(f"/api/users/{TEST_USER_ID}/llm-parameters")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_llm_parameters_wrong_user(
    client: AsyncClient, mock_auth_user
):
    """Test accessing parameters with wrong user ID."""
    # Mock auth user with different ID
    different_user_id = uuid4()
    mock_auth_user(different_user_id)

    response = await client.get(f"/api/users/{TEST_USER_ID}/llm-parameters")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_llm_parameters_invalid_data(
    client: AsyncClient, mock_auth_user
):
    """Test creating parameters with invalid data."""
    # Mock auth user
    mock_auth_user(TEST_USER_ID)

    # Invalid data (missing required fields)
    invalid_data = {"name": "Test Parameters"}

    response = await client.post(f"/api/users/{TEST_USER_ID}/llm-parameters", json=invalid_data)
    assert response.status_code == 422
