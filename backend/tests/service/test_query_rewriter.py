import logging
import unittest
from io import StringIO
from typing import Any
from unittest.mock import patch

import pytest

from rag_solution.query_rewriting.query_rewriter import (
    ConfigurationError,
    HypotheticalDocumentEmbedding,
    InvalidQueryError,
    QueryRewriter,
    RewriterError,
    SimpleQueryRewriter,
)


@pytest.mark.atomic
class TestQueryRewriter(unittest.TestCase):
    def test_simple_query_rewriter(self) -> None:
        rewriter = SimpleQueryRewriter()
        query = "test query"
        rewritten_query = rewriter.rewrite(query)
        self.assertIn("test query", rewritten_query)
        self.assertIn("AND", rewritten_query)
        self.assertIn("relevant", rewritten_query)
        self.assertIn("important", rewritten_query)
        self.assertIn("key", rewritten_query)

    @patch("rag_solution.query_rewriting.query_rewriter.generate_text")
    def test_hde_rewriter(self, mock_generate_text: Any) -> None:
        mock_generate_text.return_value = "hypothetical document"
        rewriter = HypotheticalDocumentEmbedding(max_tokens=50, timeout=30, max_retries=3)
        query = "test query"
        rewritten_query = rewriter.rewrite(query)
        self.assertIn("test query", rewritten_query)
        self.assertIn("hypothetical document", rewritten_query)

        mock_generate_text.assert_called_once_with(
            "Generate a concise hypothetical document (maximum 50 tokens) that would perfectly answer the query: test query", params={"max_tokens": 50, "timeout": 30, "max_retries": 3}
        )

    @patch("rag_solution.query_rewriting.query_rewriter.generate_text")
    def test_hde_rewriter_with_context(self, mock_generate_text: Any) -> None:
        mock_generate_text.return_value = "hypothetical document with context"
        rewriter = HypotheticalDocumentEmbedding(max_tokens=50, timeout=30, max_retries=3)
        query = "test query"
        context = {"additional_info": "context information"}
        rewritten_query = rewriter.rewrite(query, context)
        self.assertIn("test query", rewritten_query)
        self.assertIn("hypothetical document with context", rewritten_query)

        mock_generate_text.assert_called_once_with(
            "Generate a concise hypothetical document (maximum 50 tokens) that would perfectly answer the query: test query\nAdditional context: {'additional_info': 'context information'}",
            params={"max_tokens": 50, "timeout": 30, "max_retries": 3},
        )

    @patch("rag_solution.query_rewriting.query_rewriter.generate_text")
    def test_hde_rewriter_error_handling(self, mock_generate_text: Any) -> None:
        mock_generate_text.side_effect = Exception("API Error")
        rewriter = HypotheticalDocumentEmbedding(max_tokens=50, timeout=30, max_retries=3)
        query = "test query"
        with self.assertRaises(RewriterError):
            rewriter.rewrite(query)

    @patch("rag_solution.query_rewriting.query_rewriter.generate_text")
    def test_hde_rewriter_empty_response(self, mock_generate_text: Any) -> None:
        mock_generate_text.return_value = ""
        rewriter = HypotheticalDocumentEmbedding(max_tokens=50, timeout=30, max_retries=3)
        query = "test query"
        rewritten_query = rewriter.rewrite(query)
        self.assertEqual(rewritten_query, query)  # Should return original query on empty response

    def test_query_rewriter_with_all_rewriters(self) -> None:
        config = {
            "use_simple_rewriter": True,
            "use_hde": True,
            "hde_max_tokens": 50,
            "hde_timeout": 30,
            "hde_max_retries": 3,
        }
        with patch("rag_solution.query_rewriting.query_rewriter.HypotheticalDocumentEmbedding") as mock_hde:
            mock_hde.return_value.rewrite.return_value = "test query AND (relevant OR important OR key) hde rewritten query"

            rewriter = QueryRewriter(config)
            query = "test query"
            rewritten_query = rewriter.rewrite(query)

            self.assertIn("AND", rewritten_query)  # From SimpleQueryRewriter
            self.assertIn("hde rewritten query", rewritten_query)

            mock_hde.assert_called_once_with(50, 30, 3)

    def test_query_rewriter_invalid_config(self) -> None:
        invalid_configs: list[Any] = [
            "not a dict",
            {"use_hde": True, "hde_max_tokens": -1},
            {"use_hde": True, "hde_timeout": -1},
            {"use_hde": True, "hde_max_retries": -1},
        ]
        for config in invalid_configs:
            with self.assertRaises(ConfigurationError):
                QueryRewriter(config)

    def test_query_rewriter_empty_query(self) -> None:
        config = {"use_simple_rewriter": True}
        rewriter = QueryRewriter(config)
        with self.assertRaises(InvalidQueryError):
            rewriter.rewrite("")

    def test_logging(self) -> None:
        # Create a StringIO object to capture log output
        log_capture_string = StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.INFO)

        # Get the logger used in the SimpleQueryRewriter
        logger = logging.getLogger("rag_solution.query_rewriting.query_rewriter")
        logger.addHandler(ch)

        rewriter = SimpleQueryRewriter()
        rewriter.rewrite("test query")

        # Get the log output and check if it contains the expected message
        log_contents = log_capture_string.getvalue()
        self.assertIn("Expanded query: test query AND (relevant OR important OR key)", log_contents)

        # Clean up
        logger.removeHandler(ch)


if __name__ == "__main__":
    unittest.main()
