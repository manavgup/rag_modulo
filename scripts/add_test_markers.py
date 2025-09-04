#!/usr/bin/env python3
"""
Add appropriate pytest markers to test files based on their location and content.
"""

import os
import re
from pathlib import Path

def categorize_test_file(filepath):
    """Categorize test file based on its path and content."""
    path_parts = filepath.parts
    
    if 'integration' in path_parts:
        return 'integration'
    elif 'unit' in path_parts:
        return 'atomic'  # Using atomic as the unit marker
    elif 'api' in path_parts:
        return 'api'
    elif 'service' in path_parts or 'services' in path_parts:
        return 'atomic'  # Service tests are typically unit tests
    elif 'data_ingestion' in path_parts:
        return 'atomic'  # Data ingestion tests are typically unit tests
    elif 'vectordb' in path_parts or 'vectordbs' in path_parts:
        return 'integration'  # Vector DB tests need external services
    elif 'router' in path_parts:
        return 'api'  # Router tests are API tests
    elif 'model' in path_parts:
        return 'atomic'  # Model tests are unit tests
    elif 'generation' in path_parts:
        return 'atomic'  # Generation tests are unit tests
    elif 'evaluation' in path_parts:
        return 'atomic'  # Evaluation tests are unit tests
    elif 'cli' in path_parts:
        return 'integration'  # CLI tests typically need integration
    elif 'retrieval' in path_parts:
        return 'atomic'  # Retrieval logic tests are unit tests
    else:
        # Analyze content for clues
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for external dependencies
            if any(term in content.lower() for term in ['milvus', 'elasticsearch', 'pinecone', 'weaviate', 'chroma']):
                return 'integration'
            elif any(term in content.lower() for term in ['fastapi', 'client', 'httpx', 'request']):
                return 'api'
            else:
                return 'atomic'
        except:
            return 'atomic'  # Default to unit test

def has_pytest_marker(content, marker_name):
    """Check if content already has a specific pytest marker."""
    pattern = rf'@pytest\.mark\.{marker_name}'
    return bool(re.search(pattern, content))

def add_marker_to_file(filepath, marker_name):
    """Add pytest marker to test file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if marker already exists
        if has_pytest_marker(content, marker_name):
            return f"✓ {marker_name} marker already exists"
        
        # Find the first test function or test class
        lines = content.split('\n')
        modified_lines = []
        marker_added = False
        
        for i, line in enumerate(lines):
            # Look for test functions or test classes
            if (not marker_added and 
                (line.strip().startswith('def test_') or 
                 line.strip().startswith('class Test') or
                 line.strip().startswith('async def test_'))):
                
                # Get the indentation level
                indent = len(line) - len(line.lstrip())
                marker_line = ' ' * indent + f'@pytest.mark.{marker_name}'
                
                modified_lines.append(marker_line)
                marker_added = True
            
            modified_lines.append(line)
        
        if marker_added:
            # Write back to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(modified_lines))
            return f"✅ Added @pytest.mark.{marker_name}"
        else:
            return f"⚠️ No test functions found"
            
    except Exception as e:
        return f"❌ Error: {e}"

def main():
    test_dir = Path('backend/tests')
    if not test_dir.exists():
        print("backend/tests directory not found")
        return
    
    print("=" * 80)
    print("Adding Pytest Markers to Test Files")
    print("=" * 80)
    
    files_processed = 0
    files_modified = 0
    
    # Find all Python test files
    for test_file in test_dir.rglob('test_*.py'):
        if test_file.name.startswith('test_'):
            expected_marker = categorize_test_file(test_file)
            
            rel_path = str(test_file).replace('/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/', '')
            result = add_marker_to_file(test_file, expected_marker)
            
            print(f"{rel_path}")
            print(f"  {result}")
            
            files_processed += 1
            if "Added" in result:
                files_modified += 1
    
    print()
    print(f"Files processed: {files_processed}")
    print(f"Files modified: {files_modified}")
    
    print()
    print("Next steps:")
    print("1. Run: python scripts/analyze_test_markers.py")
    print("2. Commit the changes")
    print("3. Test the CI pipeline")

if __name__ == "__main__":
    main()