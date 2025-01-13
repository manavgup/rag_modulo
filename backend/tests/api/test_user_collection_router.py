import unittest
from fastapi.testclient import TestClient
from uuid import uuid4
from rag_solution.router.user_collection_router import router
from unittest.mock import patch


class TestUserCollectionRouter(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(router)

    @patch('rag_solution.services.user_collection_service.UserCollectionService.add_user_to_collection')
    def test_add_user_to_collection(self, mock_add_user):
        mock_add_user.return_value = True
        user_id = uuid4()
        collection_id = uuid4()
        response = self.client.post(f"/api/user-collections/{user_id}/{collection_id}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json())

    @patch('rag_solution.services.user_collection_service.UserCollectionService.remove_user_from_collection')
    def test_remove_user_from_collection(self, mock_remove_user):
        mock_remove_user.return_value = True
        user_id = uuid4()
        collection_id = uuid4()
        response = self.client.delete(f"/api/user-collections/{user_id}/{collection_id}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json())

    @patch('rag_solution.services.user_collection_interaction_service.UserCollectionInteractionService.get_user_collections_with_files')
    def test_get_user_collections(self, mock_get_collections):
        user_id = uuid4()
        # Adjusting mock response to match expected response structure
        mock_get_collections.return_value = {'collections': [], 'user_id': str(user_id)}
        response = self.client.get(f"/api/user-collections/{user_id}")
        self.assertEqual(response.status_code, 200)
        # Adjusted expected JSON structure
        self.assertEqual(response.json(), {'collections': [], 'user_id': str(user_id)})

    @patch('rag_solution.services.user_collection_service.UserCollectionService.get_collection_users')
    def test_get_collection_users(self, mock_get_users):
        mock_get_users.return_value = []
        collection_id = uuid4()
        response = self.client.get(f"/api/user-collections/collection/{collection_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch('rag_solution.services.user_collection_service.UserCollectionService.remove_all_users_from_collection')
    def test_remove_all_users_from_collection(self, mock_remove_all_users):
        mock_remove_all_users.return_value = True
        collection_id = uuid4()
        response = self.client.delete(f"/api/user-collections/collection/{collection_id}/users")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json())


if __name__ == "__main__":
    unittest.main()
