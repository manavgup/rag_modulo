import unittest
from fastapi.testclient import TestClient
from rag_solution.router.collection_router import create_collection


class TestCollectionRouter(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_collection)

    def test_create_collection(self):
        # Implement test logic here
        pass


if __name__ == "__main__":
    unittest.main()