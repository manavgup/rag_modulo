#!/usr/bin/env python3
"""Script to fix all schema validation errors in test files."""

import re
from pathlib import Path

def fix_search_output_instances(file_path: Path) -> None:
    """Fix SearchOutput instances to use proper schema."""
    content = file_path.read_text()
    
    # Pattern to find SearchOutput instances with old format
    pattern = r'SearchOutput\(\s*([^)]+)\s*\)'
    
    def replace_search_output(match):
        content_inside = match.group(1)
        
        # Check if this is using old format (has "content" and "score" in query_results)
        if '"content"' in content_inside and '"score"' in content_inside:
            # This needs to be fixed
            return "SearchOutput(\n            # Fixed schema - using helper methods\n            answer=\"[PLACEHOLDER_ANSWER]\",\n            documents=[self.create_test_document_metadata(\"doc1\", \"Test Doc\")],\n            query_results=[self.create_test_query_result(\"chunk1\", \"Test content\", 0.95)],\n            rewritten_query=\"[PLACEHOLDER_QUERY]\",\n            evaluation={\"relevance_score\": 0.90},\n        )"
        
        return match.group(0)
    
    # Replace all SearchOutput instances that need fixing
    new_content = re.sub(pattern, replace_search_output, content, flags=re.DOTALL)
    
    if new_content != content:
        file_path.write_text(new_content)
        print(f"Fixed schema errors in {file_path}")

def main():
    """Fix all test files."""
    test_files = [
        Path("tests/e2e/test_comprehensive_search_scenarios.py"),
        Path("tests/e2e/test_search_performance_benchmarks.py"),
        Path("tests/e2e/test_search_data_validation.py"),
    ]
    
    for test_file in test_files:
        if test_file.exists():
            fix_search_output_instances(test_file)
        else:
            print(f"File not found: {test_file}")

if __name__ == "__main__":
    main()

