"""Basic test to verify the new test structure works."""

import pytest
from pathlib import Path


def test_test_structure():
    """Test that the test structure is properly set up."""
    # Verify we're in the right location
    test_dir = Path(__file__).parent
    assert test_dir.name == "tests"
    
    # Verify we can access the backend directory
    backend_dir = Path(__file__).parent.parent / "backend"
    assert backend_dir.exists()
    assert backend_dir.is_dir()


def test_environment_variables():
    """Test that test environment variables are set correctly."""
    import os
    assert os.getenv("TESTING") == "true"
    assert os.getenv("CONTAINER_ENV") == "false"


def test_conftest_basic(test_data_dir, test_files_dir):
    """Test that basic conftest.py functionality works."""
    # Test that we can import basic fixtures
    assert test_data_dir is not None
    assert test_files_dir is not None
    
    # Test that these are Path objects
    assert isinstance(test_data_dir, Path)
    assert isinstance(test_files_dir, Path)


def test_import_paths():
    """Test that import paths work correctly."""
    # Test that we can import from the project root
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        # This should work now - use the correct config path
        from backend.core.config import settings
        assert settings is not None
    except ImportError as e:
        pytest.fail(f"Failed to import from backend: {e}")


def test_simple_math():
    """Simple test to ensure pytest is working."""
    assert 2 + 2 == 4
    assert 3 * 3 == 9

