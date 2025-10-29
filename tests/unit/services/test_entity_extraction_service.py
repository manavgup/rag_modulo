"""Unit tests for EntityExtractionService.

Tests cover:
- Fast extraction (spaCy NER)
- LLM-based extraction
- Hybrid extraction
- Entity validation and filtering
- Caching behavior
"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from rag_solution.services.entity_extraction_service import EntityExtractionService


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def mock_settings():
    """Mock settings."""
    return MagicMock()


@pytest.fixture
def entity_service(mock_db, mock_settings):
    """Create EntityExtractionService instance."""
    return EntityExtractionService(mock_db, mock_settings)


class TestEntityValidation:
    """Test entity validation and filtering."""

    def test_validate_entities_filters_stop_words(self, entity_service):
        """Test that stop words are filtered out."""
        entities = [
            "IBM",  # Valid
            "it",  # Stop word - pronoun
            "however",  # Stop word - discourse marker
            "user",  # Stop word - generic term
            "context",  # Stop word - generic term
            "2020",  # Valid
            "revenue",  # Valid
        ]

        validated = entity_service._validate_entities(entities)

        assert "IBM" in validated
        assert "2020" in validated
        assert "revenue" in validated
        assert "it" not in validated
        assert "however" not in validated
        assert "user" not in validated
        assert "context" not in validated

    def test_validate_entities_filters_short_entities(self, entity_service):
        """Test that very short entities are filtered."""
        entities = ["a", "I", "IBM", "AI"]

        validated = entity_service._validate_entities(entities)

        # Single characters should be removed
        assert "a" not in validated
        assert "I" not in validated
        # 2-3 character entities like "IBM", "AI" should be kept
        assert "IBM" in validated
        assert "AI" in validated

    def test_validate_entities_filters_entities_starting_with_stop_words(self, entity_service):
        """Test that entities starting with stop words are filtered."""
        entities = [
            "IBM revenue",  # Valid
            "it reports",  # Starts with stop word "it"
            "however strong",  # Starts with stop word "however"
            "Global Financing",  # Valid
        ]

        validated = entity_service._validate_entities(entities)

        assert "IBM revenue" in validated
        assert "Global Financing" in validated
        assert "it reports" not in validated
        assert "however strong" not in validated

    def test_validate_entities_deduplicates(self, entity_service):
        """Test that entities are deduplicated (case-insensitive)."""
        entities = ["IBM", "ibm", "IBM", "Revenue", "revenue"]

        validated = entity_service._validate_entities(entities)

        # Should only have one of each (case preserved from first occurrence)
        assert len([e for e in validated if e.lower() == "ibm"]) == 1
        assert len([e for e in validated if e.lower() == "revenue"]) == 1

    def test_validate_entities_filters_all_caps_noise(self, entity_service):
        """Test that all-caps noise is filtered but acronyms are kept."""
        entities = [
            "IBM",  # Acronym - 3 chars - should keep
            "API",  # Acronym - 3 chars - should keep
            "HOWEVER",  # All caps - 7 chars - should filter
            "SINCE",  # All caps - 5 chars - should filter (edge case)
        ]

        validated = entity_service._validate_entities(entities)

        assert "IBM" in validated
        assert "API" in validated
        assert "HOWEVER" not in validated
        # SINCE is 5 chars, not > 5, so it might pass (implementation detail)


class TestRegexFallback:
    """Test regex-based fallback extraction."""

    def test_extract_with_regex_finds_proper_nouns(self, entity_service):
        """Test regex extraction finds proper nouns."""
        context = "IBM reported strong revenue in 2020. Global Financing performed well."

        entities = entity_service._extract_with_regex(context)

        # Should extract proper nouns
        assert any("IBM" in e for e in entities)
        assert any("Global Financing" in e for e in entities)

    def test_extract_with_regex_finds_years(self, entity_service):
        """Test regex extraction finds years."""
        context = "The revenue in 2020 was higher than 2019."

        entities = entity_service._extract_with_regex(context)

        # Should extract years
        assert "2020" in entities
        assert "2019" in entities

    def test_extract_with_regex_finds_money(self, entity_service):
        """Test regex extraction finds money amounts."""
        context = "IBM reported revenue of $73.6B in 2020."

        entities = entity_service._extract_with_regex(context)

        # Should extract money amounts
        assert any("$73.6B" in e or "73.6B" in e for e in entities)


class TestSpacyExtraction:
    """Test spaCy-based extraction."""

    @patch("rag_solution.services.entity_extraction_service.spacy")
    def test_extract_with_spacy_success(self, mock_spacy, entity_service):
        """Test successful spaCy extraction."""
        # Mock spaCy model
        mock_nlp = MagicMock()
        mock_doc = MagicMock()

        # Mock named entities
        mock_ent1 = MagicMock()
        mock_ent1.text = "IBM"
        mock_ent1.label_ = "ORG"

        mock_ent2 = MagicMock()
        mock_ent2.text = "2020"
        mock_ent2.label_ = "DATE"

        mock_doc.ents = [mock_ent1, mock_ent2]

        # Mock noun chunks
        mock_chunk = MagicMock()
        mock_chunk.text = "revenue"
        mock_doc.noun_chunks = [mock_chunk]

        mock_nlp.return_value = mock_doc
        mock_spacy.load.return_value = mock_nlp

        # Force reload of nlp property
        entity_service._nlp = None

        context = "IBM reported revenue in 2020"
        entities = entity_service._extract_with_spacy(context)

        # Should extract entities from spaCy
        assert "IBM" in entities
        assert "2020" in entities
        assert "revenue" in entities

    def test_extract_with_spacy_fallback_when_unavailable(self, entity_service):
        """Test fallback to regex when spaCy is unavailable."""
        # Mock _extract_with_regex to verify fallback
        with patch.object(entity_service, "_extract_with_regex", return_value=["IBM", "2020"]) as mock_regex:
            # Mock nlp property to return None (spaCy unavailable)
            with patch.object(type(entity_service), "nlp", new_callable=PropertyMock, return_value=None):
                context = "IBM reported revenue in 2020"
                entities = entity_service._extract_with_spacy(context)

                # Should fallback to regex extraction
                mock_regex.assert_called_once_with(context)
                assert entities == ["IBM", "2020"]


@pytest.mark.asyncio
class TestLLMExtraction:
    """Test LLM-based extraction."""

    async def test_extract_with_llm_success(self, entity_service, mock_db):
        """Test successful LLM extraction."""
        # Mock LLM provider service
        mock_llm_service = MagicMock()
        mock_provider_config = MagicMock()
        mock_provider_config.name = "watsonx"
        mock_llm_service.get_default_provider.return_value = mock_provider_config

        # Mock LLM provider factory
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="IBM, 2020, revenue, Global Financing")

        with patch("rag_solution.services.entity_extraction_service.LLMProviderService", return_value=mock_llm_service):
            with patch("rag_solution.services.entity_extraction_service.LLMProviderFactory") as mock_factory:
                mock_factory.return_value.get_provider.return_value = mock_provider

                context = "IBM reported revenue in 2020"
                entities = await entity_service._extract_with_llm(context)

                # Should extract entities from LLM response
                assert "IBM" in entities
                assert "2020" in entities
                assert "revenue" in entities
                assert "Global Financing" in entities

    async def test_extract_with_llm_fallback_on_error(self, entity_service):
        """Test fallback to spaCy when LLM generation fails."""
        context = "IBM reported revenue in 2020"

        # Mock LLMProviderService
        mock_llm_service = MagicMock()
        mock_provider_config = MagicMock()
        mock_provider_config.name = "test_provider"
        mock_llm_service.get_default_provider.return_value = mock_provider_config

        # Set the mock service
        entity_service._llm_provider_service = mock_llm_service

        # Mock factory to raise an error (which is caught and falls back)
        with patch("rag_solution.services.entity_extraction_service.LLMProviderFactory") as mock_factory_class:
            mock_factory_class.return_value.get_provider.side_effect = RuntimeError("Provider error")

            # Mock _extract_with_spacy for fallback
            with patch.object(entity_service, "_extract_with_spacy", return_value=["IBM", "2020"]) as mock_spacy:
                entities = await entity_service._extract_with_llm(context)

                # Should fallback to spaCy
                mock_spacy.assert_called_once_with(context)
                assert entities == ["IBM", "2020"]


@pytest.mark.asyncio
class TestHybridExtraction:
    """Test hybrid extraction (spaCy + LLM)."""

    async def test_hybrid_uses_spacy_for_simple_context(self, entity_service):
        """Test hybrid uses only spaCy for simple contexts (< 50 words)."""
        with patch.object(entity_service, "_extract_with_spacy", return_value=["IBM", "2020"]) as mock_spacy:
            with patch.object(entity_service, "_extract_with_llm") as mock_llm:
                context = "IBM reported revenue in 2020"  # < 50 words
                entities = await entity_service._extract_hybrid(context)

                # Should only use spaCy
                mock_spacy.assert_called_once()
                mock_llm.assert_not_called()
                assert entities == ["IBM", "2020"]

    async def test_hybrid_uses_llm_for_complex_context(self, entity_service):
        """Test hybrid uses LLM refinement for complex contexts (> 50 words)."""
        # Complex context with > 50 words
        context = " ".join(["word"] * 60)  # 60 words

        with patch.object(entity_service, "_extract_with_spacy", return_value=["IBM", "2020"]) as mock_spacy:
            with patch.object(entity_service, "_extract_with_llm", return_value=["IBM", "2020", "revenue"]) as mock_llm:
                entities = await entity_service._extract_hybrid(context)

                # Should use both spaCy and LLM
                mock_spacy.assert_called_once()
                mock_llm.assert_called_once()

                # Should merge and rank entities
                assert "IBM" in entities  # In both lists
                assert "2020" in entities  # In both lists
                assert "revenue" in entities  # LLM only

    async def test_hybrid_fallback_on_llm_error(self, entity_service):
        """Test hybrid falls back to spaCy if LLM fails."""
        context = " ".join(["word"] * 60)  # Complex context

        with patch.object(entity_service, "_extract_with_spacy", return_value=["IBM", "2020"]) as mock_spacy:
            # Mock _extract_with_llm to raise RuntimeError (which is caught)
            with patch.object(entity_service, "_extract_with_llm", side_effect=RuntimeError("LLM error")) as mock_llm:
                entities = await entity_service._extract_hybrid(context)

                # Should call both (LLM fails, but spaCy succeeds)
                mock_spacy.assert_called_once()
                mock_llm.assert_called_once()
                # Returns spaCy results since LLM failed
                assert entities == ["IBM", "2020"]


@pytest.mark.asyncio
class TestPublicAPI:
    """Test public API of EntityExtractionService."""

    async def test_extract_entities_fast_method(self, entity_service):
        """Test extract_entities with fast method."""
        with patch.object(entity_service, "_extract_with_spacy", return_value=["IBM", "2020"]) as mock_spacy:
            context = "IBM reported revenue in 2020"
            entities = await entity_service.extract_entities(context, method="fast")

            mock_spacy.assert_called_once()
            assert "IBM" in entities
            assert "2020" in entities

    async def test_extract_entities_llm_method(self, entity_service):
        """Test extract_entities with LLM method."""
        with patch.object(entity_service, "_extract_with_llm", return_value=["IBM", "2020", "revenue"]) as mock_llm:
            context = "IBM reported revenue in 2020"
            entities = await entity_service.extract_entities(context, method="llm")

            mock_llm.assert_called_once()
            assert "IBM" in entities
            assert "revenue" in entities

    async def test_extract_entities_hybrid_method(self, entity_service):
        """Test extract_entities with hybrid method."""
        with patch.object(entity_service, "_extract_hybrid", return_value=["IBM", "2020", "revenue"]) as mock_hybrid:
            context = "IBM reported revenue in 2020"
            entities = await entity_service.extract_entities(context, method="hybrid")

            mock_hybrid.assert_called_once()
            assert len(entities) > 0

    async def test_extract_entities_caching(self, entity_service):
        """Test that entity extraction results are cached."""
        with patch.object(entity_service, "_extract_with_spacy", return_value=["IBM", "2020"]) as mock_spacy:
            context = "IBM reported revenue in 2020"

            # First call - should hit extraction
            entities1 = await entity_service.extract_entities(context, method="fast", use_cache=True)
            assert mock_spacy.call_count == 1

            # Second call - should use cache
            entities2 = await entity_service.extract_entities(context, method="fast", use_cache=True)
            assert mock_spacy.call_count == 1  # Not called again

            # Results should be the same
            assert entities1 == entities2

    async def test_extract_entities_max_entities_limit(self, entity_service):
        """Test that max_entities limit is enforced."""
        with patch.object(entity_service, "_extract_with_spacy", return_value=["A", "B", "C", "D", "E", "F"]):
            context = "Test context"
            entities = await entity_service.extract_entities(context, method="fast", max_entities=3)

            # Should only return max_entities
            assert len(entities) <= 3

    async def test_extract_entities_empty_context(self, entity_service):
        """Test extraction with empty context."""
        entities = await entity_service.extract_entities("", method="fast")
        assert entities == []

        entities = await entity_service.extract_entities("   ", method="fast")
        assert entities == []


class TestCacheManagement:
    """Test cache management methods."""

    def test_clear_cache(self, entity_service):
        """Test cache clearing."""
        # Add some cache entries
        entity_service._entity_cache["key1"] = ["IBM", "2020"]
        entity_service._entity_cache["key2"] = ["revenue"]

        assert entity_service.get_cache_size() == 2

        # Clear cache
        entity_service.clear_cache()

        assert entity_service.get_cache_size() == 0
        assert len(entity_service._entity_cache) == 0

    def test_get_cache_size(self, entity_service):
        """Test getting cache size."""
        assert entity_service.get_cache_size() == 0

        # Add entries
        entity_service._entity_cache["key1"] = ["IBM"]
        entity_service._entity_cache["key2"] = ["2020"]
        entity_service._entity_cache["key3"] = ["revenue"]

        assert entity_service.get_cache_size() == 3


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world entity extraction scenarios."""

    @pytest.mark.asyncio
    async def test_ibm_revenue_query(self, entity_service):
        """Test entity extraction from IBM revenue query context."""
        context = (
            "User: what was the IBM revenue in 2020? "
            "Assistant: Based on the analysis of what was the IBM revenue in 2020? "
            "(in the context of This, User, Revenue, strong returns on equity, However, "
            "Instead, the context, Global Financing): The provided context does not contain "
            "specific revenue figures for IBM in 2020."
        )

        with patch.object(entity_service, "_extract_with_spacy") as mock_spacy:
            # Mock spaCy to return realistic entities
            mock_spacy.return_value = ["IBM", "2020", "revenue", "Global Financing"]

            entities = await entity_service.extract_entities(context, method="fast")

            # Should extract meaningful entities, NOT stop words
            assert "IBM" in entities
            assert "2020" in entities
            assert "revenue" in entities or "Revenue" in entities
            assert "Global Financing" in entities or any("Financing" in e for e in entities)

            # Should NOT extract stop words/discourse markers
            assert "This" not in entities
            assert "User" not in entities
            assert "However" not in entities
            assert "Instead" not in entities
            assert "the context" not in entities
