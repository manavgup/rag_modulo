#!/usr/bin/env python3
"""
Fix Unit Test Fixtures
"""

from pathlib import Path


def fix_unit_tests():
    """Fix unit test fixture issues."""
    print("🔧 Fixing unit tests...")

    # Update unit conftest.py to include integration_settings
    unit_conftest = Path("tests/unit/conftest.py")
    if unit_conftest.exists():
        content = unit_conftest.read_text()
        if "integration_settings" not in content:
            # Add integration_settings fixture
            integration_fixture = '''
@pytest.fixture
def integration_settings():
    """Mock integration settings for unit tests."""
    from unittest.mock import Mock
    settings = Mock()
    settings.jwt_secret_key = "test-secret-key"
    settings.rag_llm = "watsonx"
    settings.vector_db = "milvus"
    settings.postgres_url = "postgresql://test:test@localhost:5432/test_db"
    return settings
'''
            content += integration_fixture
            unit_conftest.write_text(content)
            print("✅ Added integration_settings fixture to unit tests")


def fix_e2e_tests():
    """Fix E2E test fixture issues."""
    print("🔧 Fixing E2E tests...")

    # Update E2E conftest.py to include integration_settings
    e2e_conftest = Path("tests/e2e/conftest.py")
    if e2e_conftest.exists():
        content = e2e_conftest.read_text()
        if "integration_settings" not in content:
            # Add integration_settings fixture
            integration_fixture = '''
@pytest.fixture
def integration_settings():
    """Mock integration settings for E2E tests."""
    from unittest.mock import Mock
    settings = Mock()
    settings.jwt_secret_key = "test-secret-key"
    settings.rag_llm = "watsonx"
    settings.vector_db = "milvus"
    settings.postgres_url = "postgresql://test:test@localhost:5432/test_db"
    return settings
'''
            content += integration_fixture
            e2e_conftest.write_text(content)
            print("✅ Added integration_settings fixture to E2E tests")


def main():
    """Main fix function."""
    print("🚀 Starting unit test fixes...")

    fix_unit_tests()
    fix_e2e_tests()

    print("✅ Unit test fixes completed!")


if __name__ == "__main__":
    main()
