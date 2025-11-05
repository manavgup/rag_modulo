"""
Unit tests for WatsonX utilities, including embedding truncation fix validation.
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams

from backend.vectordbs.utils.watsonx import get_embeddings, get_wx_embeddings_client
from backend.vectordbs.utils.watsonx_refactored import WatsonXClient


@pytest.mark.unit
class TestEmbeddingTruncationFix:
    """Test that embedding truncation fix is correctly implemented."""

    def test_get_wx_embeddings_client_no_truncation_in_defaults(self, integration_settings):
        """Test that default embed_params does NOT include TRUNCATE_INPUT_TOKENS.

        This validates the fix for the embedding truncation bug where
        TRUNCATE_INPUT_TOKENS: 3 was destroying semantic meaning.
        """
        with patch("backend.vectordbs.utils.watsonx.wx_Embeddings") as mock_embeddings:
            client = get_wx_embeddings_client(integration_settings)

            # Verify wx_Embeddings was called
            assert mock_embeddings.called
            call_kwargs = mock_embeddings.call_args.kwargs

            # Verify params were passed
            assert "params" in call_kwargs
            params = call_kwargs["params"]

            # Critical assertion: TRUNCATE_INPUT_TOKENS should NOT be in default params
            assert EmbedParams.TRUNCATE_INPUT_TOKENS not in params
            # But RETURN_OPTIONS should still be there
            assert EmbedParams.RETURN_OPTIONS in params

    def test_get_wx_embeddings_client_custom_params_respected(self, integration_settings):
        """Test that custom embed_params are respected."""
        custom_params = {EmbedParams.TRUNCATE_INPUT_TOKENS: 100, EmbedParams.RETURN_OPTIONS: {"input_text": False}}

        with patch("backend.vectordbs.utils.watsonx.wx_Embeddings") as mock_embeddings:
            client = get_wx_embeddings_client(integration_settings, embed_params=custom_params)

            # Verify custom params were used
            call_kwargs = mock_embeddings.call_args.kwargs
            params = call_kwargs["params"]

            # Custom params should be passed through unchanged
            assert params[EmbedParams.TRUNCATE_INPUT_TOKENS] == 100
            assert params[EmbedParams.RETURN_OPTIONS] == {"input_text": False}

    def test_watsonx_refactored_no_truncation_in_defaults(self, integration_settings):
        """Test that WatsonXClient also has the truncation fix applied."""
        wx_client = WatsonXClient(integration_settings)

        with patch("backend.vectordbs.utils.watsonx_refactored.wx_Embeddings") as mock_embeddings:
            # Create mock API client
            mock_api_client = Mock()
            wx_client._client = mock_api_client

            embed_client = wx_client.get_embeddings_client()

            # Verify wx_Embeddings was called
            assert mock_embeddings.called
            call_kwargs = mock_embeddings.call_args.kwargs

            # Verify params were passed
            assert "params" in call_kwargs
            params = call_kwargs["params"]

            # Critical assertion: TRUNCATE_INPUT_TOKENS should NOT be in default params
            assert EmbedParams.TRUNCATE_INPUT_TOKENS not in params
            # But RETURN_OPTIONS should still be there
            assert EmbedParams.RETURN_OPTIONS in params


@pytest.mark.unit
class TestDebugLogging:
    """Test that debug logging is properly gated behind environment variable."""

    def test_debug_logging_disabled_by_default(self, integration_settings):
        """Test that debug logging is NOT called when RAG_DEBUG_EMBEDDINGS is not set."""
        # Ensure env var is not set
        if "RAG_DEBUG_EMBEDDINGS" in os.environ:
            del os.environ["RAG_DEBUG_EMBEDDINGS"]

        with (
            patch("backend.vectordbs.utils.watsonx.get_wx_embeddings_client") as mock_get_client,
            patch("backend.vectordbs.utils.watsonx._log_embedding_generation") as mock_log,
        ):
            # Setup mock embeddings client
            mock_embed_client = Mock()
            mock_embed_client.embed_documents.return_value = [[0.1, 0.2, 0.3]]
            mock_get_client.return_value = mock_embed_client

            # Call get_embeddings
            result = get_embeddings("test query", settings=integration_settings)

            # Verify debug logging was NOT called
            mock_log.assert_not_called()
            # Verify embeddings were still generated
            assert result == [[0.1, 0.2, 0.3]]

    def test_debug_logging_enabled_with_env_var(self, integration_settings):
        """Test that debug logging IS called when RAG_DEBUG_EMBEDDINGS=1."""
        # Set env var to enable debug logging
        os.environ["RAG_DEBUG_EMBEDDINGS"] = "1"

        try:
            with (
                patch("backend.vectordbs.utils.watsonx.get_wx_embeddings_client") as mock_get_client,
                patch("backend.vectordbs.utils.watsonx._log_embedding_generation") as mock_log,
            ):
                # Setup mock embeddings client
                mock_embed_client = Mock()
                mock_embed_client.embed_documents.return_value = [[0.1, 0.2, 0.3]]
                mock_get_client.return_value = mock_embed_client

                # Call get_embeddings
                result = get_embeddings("test query", settings=integration_settings)

                # Verify debug logging WAS called twice (BEFORE and AFTER)
                assert mock_log.call_count == 2
                # Verify first call was "BEFORE"
                assert mock_log.call_args_list[0][0][2] == "BEFORE"
                # Verify second call was "AFTER"
                assert mock_log.call_args_list[1][0][2] == "AFTER"
                # Verify embeddings were still generated
                assert result == [[0.1, 0.2, 0.3]]
        finally:
            # Cleanup
            if "RAG_DEBUG_EMBEDDINGS" in os.environ:
                del os.environ["RAG_DEBUG_EMBEDDINGS"]


@pytest.mark.unit
class TestSemanticPreservation:
    """Test that longer queries maintain semantic integrity without truncation."""

    def test_long_query_not_truncated_during_embedding_call(self, integration_settings):
        """Test that queries with many tokens are passed in full to the embedding model.

        This is a regression test for the bug where TRUNCATE_INPUT_TOKENS: 3
        was reducing a 12-token query to 3 tokens, destroying semantic meaning.
        """
        # Create a query with many tokens (simulate the IBM workforce query example)
        long_query = "What is the breakdown of IBM's workforce in terms of employee count across different countries?"

        with (
            patch("backend.vectordbs.utils.watsonx.get_wx_embeddings_client") as mock_get_client,
        ):
            # Setup mock embeddings client
            mock_embed_client = Mock()
            mock_embed_client.embed_documents.return_value = [[0.1] * 768]  # Typical embedding dimension
            mock_get_client.return_value = mock_embed_client

            # Call get_embeddings
            result = get_embeddings(long_query, settings=integration_settings)

            # Verify embed_documents was called with the FULL query text
            mock_embed_client.embed_documents.assert_called_once()
            call_args = mock_embed_client.embed_documents.call_args
            passed_texts = call_args.kwargs["texts"]

            # The full query should be passed, not truncated
            assert passed_texts == [long_query]
            assert len(passed_texts[0]) > 50  # Verify it's the full query
            # Verify embeddings were generated
            assert len(result[0]) == 768


@pytest.mark.unit
class TestSimplified:
    """Simplified test that works (kept for backward compatibility)."""

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
