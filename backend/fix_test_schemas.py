#!/usr/bin/env python3
"""
Script to fix test data schemas to match actual Pydantic models.
This script converts test data from the old format to the new format.
"""

import re
import os
from pathlib import Path

def fix_search_output_instances(content: str) -> str:
    """Fix SearchOutput instances to use proper Pydantic models."""
    
    # Pattern to match SearchOutput with documents and query_results
    pattern = r'SearchOutput\(\s*([^)]+)\s*\)'
    
    def replace_search_output(match):
        full_match = match.group(0)
        
        # Extract the content inside SearchOutput
        inner_content = match.group(1)
        
        # Fix documents list
        documents_pattern = r'documents=\[\s*([^\]]+)\s*\]'
        documents_match = re.search(documents_pattern, inner_content, re.DOTALL)
        if documents_match:
            documents_content = documents_match.group(1)
            # Replace dict format with DocumentMetadata format
            documents_content = re.sub(
                r'\{"id":\s*"([^"]+)",\s*"title":\s*"([^"]+)",\s*"source":\s*"([^"]+)"\}',
                r'DocumentMetadata(document_name="\3", title="\2")',
                documents_content
            )
            inner_content = inner_content.replace(documents_match.group(0), f'documents=[{documents_content}]')
        
        # Fix query_results list
        query_results_pattern = r'query_results=\[\s*([^\]]+)\s*\]'
        query_results_match = re.search(query_results_pattern, inner_content, re.DOTALL)
        if query_results_match:
            query_results_content = query_results_match.group(1)
            # Replace dict format with QueryResult format
            query_results_content = re.sub(
                r'\{"content":\s*"([^"]+)",\s*"score":\s*([0-9.]+)\}',
                r'QueryResult(\n                    chunk=DocumentChunk(chunk_id="chunk\1", text="\1"),\n                    score=\2,\n                    embeddings=[0.1, 0.2, 0.3]\n                )',
                query_results_content
            )
            inner_content = inner_content.replace(query_results_match.group(0), f'query_results=[{query_results_content}]')
        
        return f'SearchOutput({inner_content})'
    
    return re.sub(pattern, replace_search_output, content, flags=re.DOTALL)

def fix_test_file(file_path: Path) -> None:
    """Fix a single test file."""
    print(f"Fixing {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add imports if not present
    if 'from vectordbs.data_types import' not in content:
        # Find the import section and add our imports
        import_pattern = r'(from rag_solution\.router\.search_router import router)'
        if re.search(import_pattern, content):
            content = re.sub(
                import_pattern,
                r'\1\nfrom vectordbs.data_types import DocumentMetadata, QueryResult, DocumentChunk',
                content
            )
    
    # Fix SearchOutput instances
    content = fix_search_output_instances(content)
    
    with open(file_path, 'w') as f:
        f.write(content)

def main():
    """Main function to fix all test files."""
    test_files = [
        Path("tests/e2e/test_comprehensive_search_scenarios.py"),
        Path("tests/e2e/test_search_performance_benchmarks.py"),
        Path("tests/e2e/test_search_data_validation.py"),
    ]
    
    for test_file in test_files:
        if test_file.exists():
            fix_test_file(test_file)
        else:
            print(f"File not found: {test_file}")

if __name__ == "__main__":
    main()
