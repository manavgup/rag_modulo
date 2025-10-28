"""Unit tests for the IdentityService."""

import unittest
from unittest.mock import patch
from uuid import UUID

from core.identity_service import IdentityService


class TestIdentityService(unittest.TestCase):
    """Test suite for the IdentityService."""

    def test_generate_id(self):
        """Test that generate_id returns a valid UUID."""
        generated_id = IdentityService.generate_id()
        self.assertIsInstance(generated_id, UUID)

    def test_generate_collection_name(self):
        """Test that generate_collection_name returns a valid format."""
        collection_name = IdentityService.generate_collection_name()
        self.assertIsInstance(collection_name, str)
        self.assertTrue(collection_name.startswith("collection_"))

    def test_uniqueness_of_generated_ids(self):
        """Test that generated IDs are unique."""
        # Test generate_id
        id1 = IdentityService.generate_id()
        id2 = IdentityService.generate_id()
        self.assertNotEqual(id1, id2)

        # Test generate_collection_name
        name1 = IdentityService.generate_collection_name()
        name2 = IdentityService.generate_collection_name()
        self.assertNotEqual(name1, name2)

        # Test generate_document_id
        doc_id1 = IdentityService.generate_document_id()
        doc_id2 = IdentityService.generate_document_id()
        self.assertNotEqual(doc_id1, doc_id2)

    def test_generate_document_id(self):
        """Test that generate_document_id returns a valid UUID string."""
        document_id = IdentityService.generate_document_id()
        self.assertIsInstance(document_id, str)
        try:
            UUID(document_id)
        except ValueError:
            self.fail("generate_document_id did not return a valid UUID string.")

    @patch.dict("os.environ", {}, clear=True)
    def test_get_mock_user_id_default(self):
        """Test get_mock_user_id returns the default UUID when env var is not set."""
        mock_user_id = IdentityService.get_mock_user_id()
        self.assertIsInstance(mock_user_id, UUID)

    @patch.dict("os.environ", {"MOCK_USER_ID": "123e4567-e89b-12d3-a456-426614174000"})
    def test_get_mock_user_id_from_env(self):
        """Test get_mock_user_id returns the UUID from the environment variable."""
        test_uuid = "123e4567-e89b-12d3-a456-426614174000"
        mock_user_id = IdentityService.get_mock_user_id()
        self.assertIsInstance(mock_user_id, UUID)
        self.assertEqual(str(mock_user_id), test_uuid)
        self.assertEqual(str(mock_user_id), test_uuid)

    @patch.dict("os.environ", {"MOCK_USER_ID": "not-a-uuid"})
    def test_get_mock_user_id_invalid_env(self):
        """Test get_mock_user_id falls back to default with an invalid env var."""
        mock_user_id = IdentityService.get_mock_user_id()
        # Should fall back to default UUID, not raise ValueError
        self.assertIsInstance(mock_user_id, UUID)
        self.assertEqual(mock_user_id, IdentityService.DEFAULT_MOCK_USER_ID)


if __name__ == "__main__":
    unittest.main()
