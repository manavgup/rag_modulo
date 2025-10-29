"""Unit tests for SimpleQueryRewriter.

Tests verifying that SimpleQueryRewriter returns queries unchanged,
without adding generic boolean expansion.
"""

import pytest

from rag_solution.query_rewriting.query_rewriter import SimpleQueryRewriter


class TestSimpleQueryRewriter:
    """Test suite for SimpleQueryRewriter."""

    @pytest.fixture
    def rewriter(self):
        """Create a SimpleQueryRewriter instance."""
        return SimpleQueryRewriter()

    def test_returns_query_unchanged(self, rewriter):
        """Test that simple queries are returned unchanged."""
        query = "what is machine learning?"
        result = rewriter.rewrite(query)
        assert result == query

    def test_no_boolean_expansion_added(self, rewriter):
        """Test that no generic boolean expansion is added."""
        query = "IBM revenue 2020"
        result = rewriter.rewrite(query)

        # Should not contain boolean expansion
        assert "AND (relevant OR important OR key)" not in result
        assert result == query

    def test_handles_complex_queries(self, rewriter):
        """Test that complex queries are returned unchanged."""
        query = "what was the IBM revenue in 2020 and how did it compare to 2019?"
        result = rewriter.rewrite(query)
        assert result == query

    def test_handles_queries_with_context(self, rewriter):
        """Test that queries with entity context are returned unchanged."""
        query = "what was the IBM revenue in 2020? (in the context of IBM, 2020, revenue)"
        result = rewriter.rewrite(query)
        assert result == query

    def test_context_parameter_ignored(self, rewriter):
        """Test that optional context parameter is ignored."""
        query = "test query"
        context = {"some": "context"}
        result = rewriter.rewrite(query, context=context)
        assert result == query

    def test_empty_query(self, rewriter):
        """Test handling of empty query."""
        query = ""
        result = rewriter.rewrite(query)
        assert result == ""

    def test_whitespace_only_query(self, rewriter):
        """Test handling of whitespace-only query."""
        query = "   "
        result = rewriter.rewrite(query)
        assert result == query
