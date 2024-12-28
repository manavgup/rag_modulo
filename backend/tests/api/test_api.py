import os
import pytest
import requests
import uuid
from typing import Dict, Any

BASE_URL = os.getenv("REACT_APP_API_URL", "http://localhost:8000")

@pytest.fixture(scope="module")
def auth_token():
    login_data = {
        "username": "test_user@example.com",
        "password": "test_password"
    }
    response = requests.post(f"{BASE_URL}/api/auth/token", json=login_data)
    assert response.status_code == 200, f"Authentication failed with status code {response.status_code}"
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture(scope="module")
def user_id(auth_headers):
    user_data = {
        "ibm_id": f"test_user_{uuid.uuid4()}",
        "email": f"test_{uuid.uuid4()}@example.com",
        "name": f"Test User {uuid.uuid4()}"
    }
    response = requests.post(f"{BASE_URL}/api/users/", json=user_data, headers=auth_headers)
    assert response.status_code == 200, f"User creation failed with status code {response.status_code}"
    user = response.json()
    yield user['id']
    requests.delete(f"{BASE_URL}/api/users/{user['id']}", headers=auth_headers)

@pytest.fixture(scope="module")
def collection_id(user_id, auth_headers):
    collection_data = {
        "name": f"Test Collection {uuid.uuid4()}",
        "is_private": True,
        "users": [user_id]
    }
    response = requests.post(f"{BASE_URL}/api/collections/create", json=collection_data, headers=auth_headers)
    assert response.status_code == 200, f"Collection creation failed with status code {response.status_code}"
    collection = response.json()
    yield collection['id']
    requests.delete(f"{BASE_URL}/api/collections/{collection['id']}", headers=auth_headers)

@pytest.mark.api
def test_health_check():
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200, f"Health check failed with status code {response.status_code}"
    assert response.json() == {}, "Health check response should be an empty object"

@pytest.mark.api
def test_create_user(auth_headers):
    user_data = {
        "ibm_id": f"test_user_{uuid.uuid4()}",
        "email": f"test_{uuid.uuid4()}@example.com",
        "name": f"Test User {uuid.uuid4()}"
    }
    response = requests.post(f"{BASE_URL}/api/users/", json=user_data, headers=auth_headers)
    assert response.status_code == 200, f"User creation failed with status code {response.status_code}"
    user = response.json()
    assert 'id' in user, "User response should contain an 'id' field"
    assert user['ibm_id'] == user_data['ibm_id'], "Created user should have the same IBM ID"
    assert user['email'] == user_data['email'], "Created user should have the same email"
    assert user['name'] == user_data['name'], "Created user should have the same name"
    requests.delete(f"{BASE_URL}/api/users/{user['id']}", headers=auth_headers)

@pytest.mark.api
def test_create_collection(user_id, auth_headers):
    collection_data = {
        "name": f"Test Collection {uuid.uuid4()}",
        "is_private": True,
        "users": [user_id]
    }
    response = requests.post(f"{BASE_URL}/api/collections/create", json=collection_data, headers=auth_headers)
    assert response.status_code == 200, f"Collection creation failed with status code {response.status_code}"
    collection = response.json()
    assert 'id' in collection, "Collection response should contain an 'id' field"
    assert collection['name'] == collection_data['name'], "Created collection should have the same name"
    assert collection['is_private'] == collection_data['is_private'], "Created collection should have the same privacy setting"
    assert user_id in collection['user_ids'], "Created collection should include the user who created it"
    requests.delete(f"{BASE_URL}/api/collections/{collection['id']}", headers=auth_headers)

@pytest.mark.api
def test_upload_file(user_id, collection_id, auth_headers):
    file_content = f"This is a test file content {uuid.uuid4()}"
    files = {'file': ('test_file.txt', file_content)}
    response = requests.post(f"{BASE_URL}/api/files/{user_id}/{collection_id}", files=files, headers=auth_headers)
    assert response.status_code == 200, f"File upload failed with status code {response.status_code}"
    file_info = response.json()
    assert 'id' in file_info, "File upload response should contain an 'id' field"
    assert 'filename' in file_info, "File upload response should contain a 'filename' field"
    assert file_info['filename'] == 'test_file.txt', "Uploaded file should have the correct filename"
    requests.delete(f"{BASE_URL}/api/files/{file_info['id']}", headers=auth_headers)

@pytest.mark.api
def test_get_user_collections(user_id, auth_headers):
    response = requests.get(f"{BASE_URL}/api/user-collections/{user_id}", headers=auth_headers)
    assert response.status_code == 200, f"Get user collections failed with status code {response.status_code}"
    user_collections = response.json()
    assert 'user_id' in user_collections, "User collections response should contain a 'user_id' field"
    assert 'collections' in user_collections, "User collections response should contain a 'collections' field"
    assert isinstance(user_collections['collections'], list), "Collections should be a list"

@pytest.mark.api
def test_unauthorized_access():
    response = requests.get(f"{BASE_URL}/api/users/")
    assert response.status_code == 401, f"Unauthorized access should return 401, got {response.status_code}"

@pytest.mark.api
def test_not_found():
    non_existent_id = str(uuid.uuid4())
    response = requests.get(f"{BASE_URL}/api/users/{non_existent_id}")
    assert response.status_code == 404, f"Non-existent resource should return 404, got {response.status_code}"

@pytest.mark.api
def test_get_user(user_id, auth_headers):
    response = requests.get(f"{BASE_URL}/api/users/{user_id}", headers=auth_headers)
    assert response.status_code == 200, f"Get user failed with status code {response.status_code}"
    user = response.json()
    assert user['id'] == user_id, "Retrieved user should have the correct ID"

@pytest.mark.api
def test_update_user(user_id, auth_headers):
    update_data = {"name": "Updated Test User"}
    response = requests.put(f"{BASE_URL}/api/users/{user_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200, f"Update user failed with status code {response.status_code}"
    updated_user = response.json()
    assert updated_user['name'] == update_data['name'], "User name should be updated"

@pytest.mark.api
def test_delete_user(auth_headers):
    user_data = {
        "ibm_id": f"test_user_to_delete_{uuid.uuid4()}",
        "email": f"test_delete_{uuid.uuid4()}@example.com",
        "name": f"Test User to Delete {uuid.uuid4()}"
    }
    create_response = requests.post(f"{BASE_URL}/api/users/", json=user_data, headers=auth_headers)
    assert create_response.status_code == 200, f"User creation for deletion test failed with status code {create_response.status_code}"
    user_to_delete = create_response.json()
    
    delete_response = requests.delete(f"{BASE_URL}/api/users/{user_to_delete['id']}", headers=auth_headers)
    assert delete_response.status_code == 200, f"Delete user failed with status code {delete_response.status_code}"
    
    get_response = requests.get(f"{BASE_URL}/api/users/{user_to_delete['id']}", headers=auth_headers)
    assert get_response.status_code == 404, f"Deleted user should not be found, got status code {get_response.status_code}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])