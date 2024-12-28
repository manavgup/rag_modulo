import unittest
from fastapi.testclient import TestClient
from rag_solution.router.file_router import upload_file


class TestFileRouter(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(upload_file)

    def test_upload_file(self):
        # Implement test logic here
        pass


if __name__ == "__main__":
    unittest.main()