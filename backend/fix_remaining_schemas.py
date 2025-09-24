#!/usr/bin/env python3
"""Script to fix remaining schema validation errors."""

import re
from pathlib import Path


def fix_file(file_path: Path) -> None:
    """Fix all remaining schema issues in a file."""
    content = file_path.read_text()

    # Fix documents with old format
    old_docs_pattern = r'documents=\[\s*\{[^}]*"id"[^}]*"title"[^}]*"source"[^}]*\}[^\]]*\]'

    def replace_docs(match):
        # Count how many documents
        doc_count = len(re.findall(r'\{[^}]*"id"[^}]*\}', match.group(0)))
        docs = []
        for i in range(doc_count):
            docs.append(f'self.create_test_document_metadata("doc{i + 1}.pdf", "Test Doc {i + 1}")')
        return f"documents=[\n                {',\n                '.join(docs)},\n            ]"

    content = re.sub(old_docs_pattern, replace_docs, content, flags=re.DOTALL)

    # Fix query_results with old format
    old_query_pattern = r'query_results=\[\s*\{[^}]*"content"[^}]*"score"[^}]*\}[^\]]*\]'

    def replace_query_results(match):
        # Count how many query results
        result_count = len(re.findall(r'\{[^}]*"content"[^}]*\}', match.group(0)))
        results = []
        for i in range(result_count):
            results.append(f'self.create_test_query_result("chunk{i + 1}", "Test content {i + 1}", 0.95)')
        return f"query_results=[\n                {',\n                '.join(results)},\n            ]"

    content = re.sub(old_query_pattern, replace_query_results, content, flags=re.DOTALL)

    # Fix single line instances
    content = re.sub(
        r'documents=\[\{"id": "[^"]*", "title": "[^"]*", "source": "[^"]*"\}\]',
        'documents=[self.create_test_document_metadata("test.pdf", "Test Doc")]',
        content,
    )

    content = re.sub(
        r'query_results=\[\{"content": "[^"]*", "score": [^}]*\}\]',
        'query_results=[self.create_test_query_result("chunk1", "Test content", 0.95)]',
        content,
    )

    file_path.write_text(content)
    print(f"Fixed schemas in {file_path}")


def main():
    """Fix all test files."""
    test_files = [
        Path("tests/e2e/test_comprehensive_search_scenarios.py"),
        Path("tests/e2e/test_search_performance_benchmarks.py"),
        Path("tests/e2e/test_search_data_validation.py"),
    ]

    for test_file in test_files:
        if test_file.exists():
            fix_file(test_file)
        else:
            print(f"File not found: {test_file}")


if __name__ == "__main__":
    main()
