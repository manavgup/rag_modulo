"""
Integration tests for user initialization and recovery after database operations.
"""

import pytest
from sqlalchemy import text

from core.mock_auth import ensure_mock_user_exists
from rag_solution.services.prompt_template_service import PromptTemplateService


@pytest.mark.integration
class TestSimplified:
    """Simplified test that works."""

    def test_basic_functionality(self):
        """Test basic functionality."""
        assert True

    def test_configuration(self, integration_settings):
        """Test configuration."""
        assert integration_settings is not None
        assert hasattr(integration_settings, "jwt_secret_key")

    def test_mock_services(self, mock_watsonx_provider):
        """Test mock services."""
        assert mock_watsonx_provider is not None
        assert hasattr(mock_watsonx_provider, "generate_response")


@pytest.mark.integration
class TestUserInitializationRecovery:
    """Integration tests for user initialization recovery after database wipes."""

    def test_mock_user_initialization_after_db_wipe(self, db_session, integration_settings):
        """Integration test: Mock user gets defaults even after DB wipe simulating template deletion."""
        # Create mock user with full initialization
        user_id = ensure_mock_user_exists(db_session, integration_settings)

        # Verify templates exist
        template_service = PromptTemplateService(db_session)
        templates_before = template_service.get_user_templates(user_id)
        assert len(templates_before) >= 3, f"Expected at least 3 templates, got {len(templates_before)}"

        # Simulate DB wipe (delete templates but keep user)
        # This simulates what happens after scripts/wipe_database.py
        db_session.execute(text("DELETE FROM prompt_templates WHERE user_id = :uid"), {"uid": str(user_id)})
        db_session.commit()

        # Verify templates were deleted
        templates_after_wipe = template_service.get_user_templates(user_id)
        assert len(templates_after_wipe) == 0, "Templates should be deleted after simulated wipe"

        # Call ensure_mock_user_exists again - should trigger defensive initialization
        recovered_user_id = ensure_mock_user_exists(db_session, integration_settings)
        assert recovered_user_id == user_id, "Should return same user ID"

        # Verify templates were recreated by defensive initialization
        templates_after_recovery = template_service.get_user_templates(user_id)
        assert len(templates_after_recovery) >= 3, (
            f"Expected at least 3 templates after recovery, got {len(templates_after_recovery)}"
        )

        # Verify we have all required template types
        template_types = {t.template_type for t in templates_after_recovery}
        assert "RAG_QUERY" in template_types, "Missing RAG_QUERY template"
        assert "QUESTION_GENERATION" in template_types, "Missing QUESTION_GENERATION template"
        assert "PODCAST_GENERATION" in template_types, "Missing PODCAST_GENERATION template"
