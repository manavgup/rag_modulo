#!/usr/bin/env python3
"""
Analyze pytest markers across all test files to ensure CI compatibility.
"""

import os
import re
from pathlib import Path

def analyze_test_file(filepath):
    """Analyze a test file for pytest markers and test functions."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all test functions
    test_functions = re.findall(r'def (test_\w+)', content)

    # Find all pytest markers
    markers = re.findall(r'@pytest\.mark\.(\w+)', content)

    # Check for class-level markers
    class_markers = re.findall(r'class.*:\s*\n(?:\s*@pytest\.mark\.(\w+)\s*\n)*', content)

    return {
        'file': str(filepath),
        'test_functions': test_functions,
        'markers': markers,
        'has_atomic': 'atomic' in markers,
        'has_integration': 'integration' in markers,
        'has_unit': 'unit' in markers,
        'has_performance': 'performance' in markers,
        'has_api': 'api' in markers,
        'test_count': len(test_functions)
    }

def categorize_test_file(filepath):
    """Categorize test file based on its path and content."""
    path_parts = filepath.parts

    if 'integration' in path_parts:
        return 'integration'
    elif 'unit' in path_parts:
        return 'unit'
    elif 'api' in path_parts:
        return 'api'
    elif 'service' in path_parts or 'services' in path_parts:
        return 'unit'  # Service tests are typically unit tests
    elif 'data_ingestion' in path_parts:
        return 'unit'  # Data ingestion tests are typically unit tests
    elif 'vectordb' in path_parts or 'vectordbs' in path_parts:
        return 'integration'  # Vector DB tests need external services
    elif 'router' in path_parts:
        return 'api'  # Router tests are API tests
    elif 'model' in path_parts:
        return 'unit'  # Model tests are unit tests
    else:
        # Analyze content for clues
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Look for external dependencies
        if any(term in content.lower() for term in ['milvus', 'elasticsearch', 'pinecone', 'weaviate', 'chroma']):
            return 'integration'
        elif any(term in content.lower() for term in ['fastapi', 'client', 'httpx', 'request']):
            return 'api'
        else:
            return 'unit'

def main():
    test_dir = Path('backend/tests')
    if not test_dir.exists():
        print("backend/tests directory not found")
        return

    results = []

    # Find all Python test files
    for test_file in test_dir.rglob('test_*.py'):
        if test_file.name.startswith('test_'):
            analysis = analyze_test_file(test_file)
            analysis['expected_category'] = categorize_test_file(test_file)
            results.append(analysis)

    # Print analysis
    print("=" * 80)
    print("Test Marker Analysis")
    print("=" * 80)

    total_files = len(results)
    files_with_atomic = sum(1 for r in results if r['has_atomic'])
    files_with_integration = sum(1 for r in results if r['has_integration'])
    files_with_unit = sum(1 for r in results if r['has_unit'])
    files_with_api = sum(1 for r in results if r['has_api'])

    print(f"Total test files: {total_files}")
    print(f"Files with @pytest.mark.atomic: {files_with_atomic}")
    print(f"Files with @pytest.mark.integration: {files_with_integration}")
    print(f"Files with @pytest.mark.unit: {files_with_unit}")
    print(f"Files with @pytest.mark.api: {files_with_api}")
    print()

    # Files missing expected markers
    missing_markers = []

    for result in results:
        expected = result['expected_category']
        file_path = result['file']

        needs_marker = False
        missing_marker = None

        if expected == 'integration' and not result['has_integration']:
            needs_marker = True
            missing_marker = 'integration'
        elif expected == 'unit' and not (result['has_atomic'] or result['has_unit']):
            needs_marker = True
            missing_marker = 'atomic'  # Using atomic as the unit marker
        elif expected == 'api' and not result['has_api']:
            needs_marker = True
            missing_marker = 'api'

        if needs_marker:
            missing_markers.append({
                'file': file_path,
                'expected': expected,
                'missing': missing_marker,
                'test_count': result['test_count']
            })

    if missing_markers:
        print(f"Files missing expected markers: {len(missing_markers)}")
        print("-" * 40)

        for item in missing_markers:
            rel_path = item['file'].replace('/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/', '')
            print(f"📁 {rel_path}")
            print(f"   Expected: @pytest.mark.{item['missing']}")
            print(f"   Tests: {item['test_count']}")
            print()

    else:
        print("✅ All test files have appropriate markers!")

    # CI Marker Usage
    print("=" * 80)
    print("CI Workflow Marker Requirements")
    print("=" * 80)
    print("The CI workflow expects:")
    print("- Unit tests: @pytest.mark.atomic")
    print("- Integration tests: @pytest.mark.integration (and not performance)")
    print()

    atomic_files = [r for r in results if r['has_atomic']]
    integration_files = [r for r in results if r['has_integration']]

    print(f"Files that will run in unit test phase: {len(atomic_files)}")
    print(f"Files that will run in integration test phase: {len(integration_files)}")

    return missing_markers

if __name__ == "__main__":
    missing = main()
