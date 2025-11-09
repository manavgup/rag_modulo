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

    def test_mock_constants_exist(self):
        """Test that all mock constants are defined and are valid UUIDs."""
        # Test DEFAULT_MOCK_USER_ID
        self.assertIsInstance(IdentityService.DEFAULT_MOCK_USER_ID, UUID)
        self.assertEqual(str(IdentityService.DEFAULT_MOCK_USER_ID), "9bae4a21-718b-4c8b-bdd2-22857779a85b")

        # Test MOCK_LLM_PROVIDER_ID
        self.assertIsInstance(IdentityService.MOCK_LLM_PROVIDER_ID, UUID)
        self.assertEqual(str(IdentityService.MOCK_LLM_PROVIDER_ID), "11111111-1111-1111-1111-111111111111")

        # Test MOCK_LLM_MODEL_ID
        self.assertIsInstance(IdentityService.MOCK_LLM_MODEL_ID, UUID)
        self.assertEqual(str(IdentityService.MOCK_LLM_MODEL_ID), "22222222-2222-2222-2222-222222222222")

    def test_mock_constants_are_unique(self):
        """Test that all mock constants have different values."""
        constants = [
            IdentityService.DEFAULT_MOCK_USER_ID,
            IdentityService.MOCK_LLM_PROVIDER_ID,
            IdentityService.MOCK_LLM_MODEL_ID,
        ]

        # Check that all constants are unique
        self.assertEqual(len(constants), len(set(constants)), "Mock constants should have unique values")

    def test_extract_user_id_from_jwt_with_string_uuid(self):
        """Test extract_user_id_from_jwt with string UUID (happy path)."""
        test_uuid_str = "d1f93297-3e3c-42b0-8da7-09efde032c25"
        current_user = {"uuid": test_uuid_str}

        result = IdentityService.extract_user_id_from_jwt(current_user)

        self.assertIsInstance(result, UUID)
        self.assertEqual(str(result), test_uuid_str)

    def test_extract_user_id_from_jwt_with_uuid_object(self):
        """Test extract_user_id_from_jwt with UUID object (already converted)."""
        test_uuid = UUID("d1f93297-3e3c-42b0-8da7-09efde032c25")
        current_user = {"uuid": test_uuid}

        result = IdentityService.extract_user_id_from_jwt(current_user)

        self.assertIsInstance(result, UUID)
        self.assertEqual(result, test_uuid)

    def test_extract_user_id_from_jwt_missing_field(self):
        """Test extract_user_id_from_jwt with missing field (should raise ValueError)."""
        current_user = {"other_field": "value"}

        with self.assertRaises(ValueError) as context:
            IdentityService.extract_user_id_from_jwt(current_user)

        self.assertIn("User ID not found in JWT token", str(context.exception))

    def test_extract_user_id_from_jwt_invalid_uuid_format(self):
        """Test extract_user_id_from_jwt with invalid UUID format (should raise ValueError)."""
        current_user = {"uuid": "not-a-valid-uuid"}

        with self.assertRaises(ValueError) as context:
            IdentityService.extract_user_id_from_jwt(current_user)

        self.assertIn("Invalid user ID format in JWT token", str(context.exception))

    def test_extract_user_id_from_jwt_custom_field_name(self):
        """Test extract_user_id_from_jwt with custom field name."""
        test_uuid_str = "d1f93297-3e3c-42b0-8da7-09efde032c25"
        current_user = {"user_id": test_uuid_str}

        result = IdentityService.extract_user_id_from_jwt(current_user, field_name="user_id")

        self.assertIsInstance(result, UUID)
        self.assertEqual(str(result), test_uuid_str)

    def test_extract_user_id_from_jwt_unexpected_type(self):
        """Test extract_user_id_from_jwt with unexpected type (should raise ValueError)."""
        current_user = {"uuid": 12345}  # Integer instead of UUID or string

        with self.assertRaises(ValueError) as context:
            IdentityService.extract_user_id_from_jwt(current_user)

        self.assertIn("Unexpected user ID type in JWT token", str(context.exception))


if __name__ == "__main__":
    unittest.main()
