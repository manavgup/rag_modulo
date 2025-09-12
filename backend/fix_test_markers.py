#!/usr/bin/env python3
"""
Script to fix test markers in the test suite.
This script will correct the misaligned pytest markers across all test files.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Define what markers should be in each directory
DIRECTORY_MARKERS = {
    "tests/atomic": "atomic",
    "tests/unit": "unit", 
    "tests/integration": "integration",
    "tests/e2e": "e2e",
}

# Files that should be moved to different directories
FILES_TO_RECLASSIFY = {
    "tests/unit/test_milvus_connection.py": "tests/integration/",
    "tests/unit/test_postgresql_connection.py": "tests/integration/",
    "tests/unit/test_search_database.py": "tests/integration/",
    "tests/unit/test_team_database.py": "tests/integration/",
    "tests/unit/test_user_database.py": "tests/integration/",
    "tests/unit/test_collection_database.py": "tests/integration/",
    "tests/unit/test_vectordbs.py": "tests/integration/",
}


def find_test_files(directory: Path) -> List[Path]:
    """Find all test files in a directory."""
    return list(directory.glob("**/test_*.py"))


def get_current_markers(file_path: Path) -> List[str]:
    """Extract current pytest markers from a file."""
    markers = []
    with open(file_path, 'r') as f:
        content = f.read()
        # Find all pytest markers
        pattern = r'@pytest\.mark\.(\w+)'
        matches = re.findall(pattern, content)
        markers = [m for m in matches if m != 'asyncio']  # Exclude asyncio marker
    return markers


def fix_markers_in_file(file_path: Path, old_marker: str, new_marker: str) -> bool:
    """Replace incorrect markers with correct ones."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Replace class-level markers
    pattern = f'@pytest.mark.{old_marker}'
    replacement = f'@pytest.mark.{new_marker}'
    content = re.sub(pattern, replacement, content)
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False


def validate_file_location(file_path: Path) -> Tuple[bool, str]:
    """Check if a test file is in the correct directory based on its content."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for integration test indicators
    integration_indicators = [
        'real_db', 'real_database', 'TestContainer', 'docker',
        'PostgresContainer', 'MilvusContainer', 'connect(', 
        'connections.connect', 'create_engine'
    ]
    
    # Check for unit test indicators
    unit_indicators = [
        'Mock(', 'mock_', '@patch', 'MagicMock'
    ]
    
    integration_score = sum(1 for indicator in integration_indicators if indicator in content)
    unit_score = sum(1 for indicator in unit_indicators if indicator in content)
    
    file_name = file_path.name
    
    # Files with these names should be in integration
    if any(keyword in file_name for keyword in ['database', 'connection', 'milvus', 'postgresql', 'vectordb']):
        return False, "Should be in integration/ based on filename"
    
    # High integration score suggests integration test
    if integration_score >= 3:
        return False, f"Should be in integration/ (score: {integration_score})"
    
    return True, "Location seems correct"


def main():
    """Main function to fix test markers."""
    print("🔍 Analyzing and fixing test markers...\n")
    
    total_fixed = 0
    issues_found = []
    
    # Process each test directory
    for directory, expected_marker in DIRECTORY_MARKERS.items():
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"⚠️  Directory {directory} does not exist")
            continue
            
        print(f"\n📂 Processing {directory} (expected marker: @pytest.mark.{expected_marker})")
        print("-" * 60)
        
        test_files = find_test_files(dir_path)
        
        for file_path in test_files:
            current_markers = get_current_markers(file_path)
            
            # Skip if file has no markers or only has asyncio
            if not current_markers:
                continue
                
            # Check if markers are correct
            incorrect_markers = [m for m in current_markers if m != expected_marker]
            
            if incorrect_markers:
                print(f"\n  📄 {file_path.name}")
                print(f"     Current markers: {current_markers}")
                print(f"     Expected marker: {expected_marker}")
                
                # Fix each incorrect marker
                for wrong_marker in incorrect_markers:
                    if fix_markers_in_file(file_path, wrong_marker, expected_marker):
                        print(f"     ✅ Fixed: @pytest.mark.{wrong_marker} -> @pytest.mark.{expected_marker}")
                        total_fixed += 1
                    else:
                        print(f"     ⚠️  Could not fix marker: {wrong_marker}")
                
                # Validate file location
                if directory == "tests/unit":
                    is_correct, reason = validate_file_location(file_path)
                    if not is_correct:
                        issues_found.append(f"{file_path}: {reason}")
                        print(f"     ⚠️  Location issue: {reason}")
    
    # Report files that should be moved
    print("\n\n📋 Files that should be reclassified:")
    print("-" * 60)
    for old_path, new_dir in FILES_TO_RECLASSIFY.items():
        if Path(old_path).exists():
            print(f"  • {old_path} -> {new_dir}")
    
    # Summary
    print(f"\n\n✨ Summary:")
    print(f"  • Fixed {total_fixed} incorrect markers")
    print(f"  • Found {len(issues_found)} files that may be in wrong directories")
    
    if issues_found:
        print("\n⚠️  Files with location issues:")
        for issue in issues_found:
            print(f"  • {issue}")
    
    print("\n💡 Next steps:")
    print("  1. Review the changes with: git diff tests/")
    print("  2. Run tests to verify: make test-fast")
    print("  3. Move mislocated files to correct directories")
    print("  4. Update E2E tests to use real services instead of mocks")


if __name__ == "__main__":
    main()