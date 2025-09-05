import requests
import uuid

BASE_URL = "http://localhost:8000"

def test_health_check():
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200, f"Health check failed with status code {response.status_code}"
    print("Health check passed")

def test_create_user():
    user_data = {
        "ibm_id": f"test_user_{uuid.uuid4()}",
        "email": f"test_{uuid.uuid4()}@example.com",
        "name": f"Test User {uuid.uuid4()}"
    }
    response = requests.post(f"{BASE_URL}/api/users/", json=user_data)
    assert response.status_code == 200, f"User creation failed with status code {response.status_code}"
    user = response.json()
    print(f"User created: {user['id']}")
    return user['id']

def test_create_collection(user_id):
    collection_data = {
        "name": f"Test Collection {uuid.uuid4()}",
        "is_private": True,
        "users": [user_id]
    }
    response = requests.post(f"{BASE_URL}/api/collections/create", json=collection_data)
    assert response.status_code == 200, f"Collection creation failed with status code {response.status_code}"
    collection = response.json()
    print(f"Collection created: {collection['id']}")
    return collection['id']

def test_upload_file(user_id, collection_id):
    # Create a dummy text file
    file_content = f"This is a test file content {uuid.uuid4()}"
    files = {'file': ('test_file.txt', file_content)}
    response = requests.post(f"{BASE_URL}/api/files/{user_id}/{collection_id}", files=files)
    assert response.status_code == 200, f"File upload failed with status code {response.status_code}"
    file_info = response.json()
    print(f"File uploaded: {file_info['id']}")
    return file_info['id']

def run_tests():
    test_health_check()
    user_id = test_create_user()
    collection_id = test_create_collection(user_id)
    test_upload_file(user_id, collection_id)
    print("All tests passed successfully")

if __name__ == "__main__":
    run_tests()
