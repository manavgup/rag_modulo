import pytest
import uuid
from typing import Dict, Any
from fastapi.testclient import TestClient

@pytest.fixture
def user_id(test_client: TestClient, auth_headers: Dict[str, str], base_user) -> str:
    return str(base_user.id)

@pytest.fixture
def collection_id(test_client: TestClient, auth_headers: Dict[str, str], base_collection) -> str:
    return str(base_collection.id)

def test_health_check(test_client: TestClient, auth_headers: Dict[str, str]):
    response = test_client.get("/api/health", headers=auth_headers)
    assert response.status_code == 200, f"Health check failed with status code {response.status_code}"
    data = response.json()
    assert "status" in data, "Health check response should have a status field"
    assert "components" in data, "Health check response should have a components field"

def test_create_user(test_client: TestClient, auth_headers: Dict[str, str]):
    user_data = {
        "ibm_id": f"test_user_{uuid.uuid4()}",
        "email": f"test_{uuid.uuid4()}@example.com",
        "name": f"Test User {uuid.uuid4()}"
    }
    response = test_client.post("/api/users/", json=user_data, headers=auth_headers)
    assert response.status_code == 200, f"User creation failed with status code {response.status_code}"
    user = response.json()
    assert 'id' in user, "User response should contain an 'id' field"
    assert user['ibm_id'] == user_data['ibm_id'], "Created user should have the same IBM ID"
    assert user['email'] == user_data['email'], "Created user should have the same email"
    assert user['name'] == user_data['name'], "Created user should have the same name"
    test_client.delete(f"/api/users/{user['id']}", headers=auth_headers)

def test_create_collection(test_client: TestClient, user_id: str, auth_headers: Dict[str, str]):
    collection_data = {
        "name": f"Test Collection {uuid.uuid4()}",
        "is_private": True,
        "users": [user_id]
    }
    response = test_client.post("/api/users/collections/create", json=collection_data, headers=auth_headers)
    assert response.status_code == 200, f"Collection creation failed with status code {response.status_code}"
    collection = response.json()
    assert 'id' in collection, "Collection response should contain an 'id' field"
    assert collection['name'] == collection_data['name'], "Created collection should have the same name"
    assert collection['is_private'] == collection_data['is_private'], "Created collection should have the same privacy setting"
    assert user_id in collection['user_ids'], "Created collection should include the user who created it"
    test_client.delete(f"/api/collections/{collection['id']}", headers=auth_headers)

def test_upload_file(test_client: TestClient, user_id: str, collection_id: str, auth_headers: Dict[str, str]):
    file_content = f"This is a test file content {uuid.uuid4()}"
    files = {'file': ('test_file.txt', file_content)}
    response = test_client.post(f"/api/users/files/{user_id}/{collection_id}", files=files, headers=auth_headers)
    assert response.status_code == 200, f"File upload failed with status code {response.status_code}"
    file_info = response.json()
    assert 'id' in file_info, "File upload response should contain an 'id' field"
    assert 'filename' in file_info, "File upload response should contain a 'filename' field"
    assert file_info['filename'] == 'test_file.txt', "Uploaded file should have the correct filename"
    test_client.delete(f"/api/files/{file_info['id']}", headers=auth_headers)

def test_get_user_collections(test_client: TestClient, user_id: str, auth_headers: Dict[str, str]):
    response = test_client.get(f"/api/users/collections/{user_id}", headers=auth_headers)
    assert response.status_code == 200, f"Get user collections failed with status code {response.status_code}"
    user_collections = response.json()
    assert 'user_id' in user_collections, "User collections response should contain a 'user_id' field"
    assert 'collections' in user_collections, "User collections response should contain a 'collections' field"
    assert isinstance(user_collections['collections'], list), "Collections should be a list"

def test_unauthorized_access(test_client: TestClient):
    response = test_client.get("/api/users/")
    assert response.status_code == 401, f"Unauthorized access should return 401, got {response.status_code}"

def test_not_found(test_client: TestClient):
    non_existent_id = str(uuid.uuid4())
    response = test_client.get(f"/api/users/{non_existent_id}")
    assert response.status_code == 404, f"Non-existent resource should return 404, got {response.status_code}"

def test_get_user(test_client: TestClient, user_id: str, auth_headers: Dict[str, str]):
    response = test_client.get(f"/api/users/{user_id}", headers=auth_headers)
    assert response.status_code == 200, f"Get user failed with status code {response.status_code}"
    user = response.json()
    assert user['id'] == user_id, "Retrieved user should have the correct ID"

def test_update_user(test_client: TestClient, user_id: str, auth_headers: Dict[str, str]):
    update_data = {"name": "Updated Test User"}
    response = test_client.put(f"/api/users/{user_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200, f"Update user failed with status code {response.status_code}"
    updated_user = response.json()
    assert updated_user['name'] == update_data['name'], "User name should be updated"

def test_delete_user(test_client: TestClient, auth_headers: Dict[str, str]):
    user_data = {
        "ibm_id": f"test_user_to_delete_{uuid.uuid4()}",
        "email": f"test_delete_{uuid.uuid4()}@example.com",
        "name": f"Test User to Delete {uuid.uuid4()}"
    }
    create_response = test_client.post("/api/users/", json=user_data, headers=auth_headers)
    assert create_response.status_code == 200, f"User creation for deletion test failed with status code {create_response.status_code}"
    user_to_delete = create_response.json()
    
    delete_response = test_client.delete(f"/api/users/{user_to_delete['id']}", headers=auth_headers)
    assert delete_response.status_code == 200, f"Delete user failed with status code {delete_response.status_code}"
    
    get_response = test_client.get(f"/api/users/{user_to_delete['id']}", headers=auth_headers)
    assert get_response.status_code == 404, f"Deleted user should not be found, got status code {get_response.status_code}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
