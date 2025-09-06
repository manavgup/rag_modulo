#!/usr/bin/env python3
"""
Focused test script to validate Settings fix for CI/CD.

This script specifically tests ONLY the Settings configuration fix,
avoiding other unrelated test suite issues (database, imports, etc.).
"""

import sys
import os


def test_settings_import_without_env_vars():
    """Test that Settings can be imported without environment variables."""
    print("Testing Settings import without env vars...")

    # Remove all potentially required env vars
    for var in ["JWT_SECRET_KEY", "RAG_LLM", "WATSONX_INSTANCE_ID", "WATSONX_APIKEY", "WATSONX_URL"]:
        os.environ.pop(var, None)

    try:
        from core.config import settings, get_settings

        # Validate defaults work
        assert settings.jwt_secret_key.startswith("dev-secret-key"), f"Expected dev-secret-key, got {settings.jwt_secret_key[:20]}"
        assert settings.rag_llm == "openai", f"Expected openai, got {settings.rag_llm}"
        assert settings.wx_project_id == "", f"Expected empty string, got {settings.wx_project_id}"
        assert settings.wx_api_key == "", f"Expected empty string, got {settings.wx_api_key}"
        assert "us-south.ml.cloud.ibm.com" in settings.wx_url, f"Expected default URL, got {settings.wx_url}"

        # Test lazy initialization
        assert get_settings() is not None, "get_settings() should return Settings instance"
        assert get_settings() is get_settings(), "Should return same instance (singleton)"

        print("✅ SUCCESS: Settings import works without env vars")
        return True

    except Exception as e:
        print(f"❌ FAILED: Settings import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_settings_with_env_vars():
    """Test that Settings respect environment variables when provided."""
    print("Testing Settings with environment variables...")

    # Set test env vars
    os.environ["JWT_SECRET_KEY"] = "test-secret-key"
    os.environ["RAG_LLM"] = "anthropic"
    os.environ["WATSONX_INSTANCE_ID"] = "test-instance"
    os.environ["WATSONX_APIKEY"] = "test-api-key"
    os.environ["WATSONX_URL"] = "https://test.watsonx.com"

    try:
        # Need to reload the module to pick up new env vars
        import importlib
        import core.config

        importlib.reload(core.config)
        from core.config import settings

        # Validate env vars override defaults
        assert settings.jwt_secret_key == "test-secret-key"
        assert settings.rag_llm == "anthropic"
        assert settings.wx_project_id == "test-instance"
        assert settings.wx_api_key == "test-api-key"
        assert settings.wx_url == "https://test.watsonx.com"

        print("✅ SUCCESS: Settings respect environment variables")
        return True

    except Exception as e:
        print(f"❌ FAILED: Settings env var override failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # Clean up env vars
        for var in ["JWT_SECRET_KEY", "RAG_LLM", "WATSONX_INSTANCE_ID", "WATSONX_APIKEY", "WATSONX_URL"]:
            os.environ.pop(var, None)


def main():
    """Run all Settings tests."""
    print("=" * 60)
    print("SETTINGS CONFIGURATION TEST (Issue #177)")
    print("=" * 60)

    tests = [
        test_settings_import_without_env_vars,
        test_settings_with_env_vars,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAILED: {test_func.__name__} crashed: {e}")
            failed += 1
        print("-" * 40)

    print(f"\n📊 RESULTS: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 ALL SETTINGS TESTS PASSED!")
        print("✅ Issue #177 Settings fix is working correctly")
        return 0
    else:
        print("❌ Some Settings tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
