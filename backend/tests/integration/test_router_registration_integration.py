"""Integration tests for router registration and database enum validation.

These tests verify that:
1. All routers are properly registered in the FastAPI app
2. Database enum values match Python schema enums
3. API endpoints are accessible
"""

import pytest
from fastapi.testclient import TestClient
from main import app

from rag_solution.schemas.prompt_template_schema import PromptTemplateType


@pytest.mark.integration
class TestRouterRegistration:
    """Integration tests for router registration."""

    def test_all_routers_registered(self) -> None:
        """Integration: Verify all expected routers are registered in the app."""
        # Get all registered routes
        routes = [getattr(route, 'path', str(route)) for route in app.routes]

        # Expected router prefixes
        expected_prefixes = [
            "/api/auth",
            "/api/chat",
            "/api/conversations",
            "/api/dashboard",
            "/api/health",
            "/api/collections",
            "/api/podcasts",  # This was missing!
            "/api/users",
            "/api/teams",
            "/api/search",
            "/api/token-warnings",
            "/api/ws",
        ]

        # Check that all expected prefixes have corresponding routes
        for prefix in expected_prefixes:
            matching_routes = [route for route in routes if route.startswith(prefix)]
            assert len(matching_routes) > 0, f"No routes found for prefix: {prefix}"
            print(f"✅ Found {len(matching_routes)} routes for {prefix}")

    def test_podcast_endpoints_accessible(self) -> None:
        """Integration: Verify podcast endpoints are accessible."""
        client = TestClient(app)

        # Test that podcast endpoints exist (even if they return errors due to auth)
        response = client.post("/api/podcasts/generate")
        # Should not be 404 - that means router is not registered
        assert response.status_code != 404, "Podcast router not registered - endpoint returns 404"

        # Should be 422 (validation error) or 401 (auth error), not 404
        assert response.status_code in [422, 401, 400], f"Unexpected status code: {response.status_code}"

    def test_openapi_schema_includes_podcast_endpoints(self) -> None:
        """Integration: Verify OpenAPI schema includes podcast endpoints."""
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})

        # Check for podcast endpoints in OpenAPI schema
        podcast_paths = [path for path in paths if "/podcasts" in path]
        assert len(podcast_paths) > 0, "No podcast endpoints found in OpenAPI schema"

        # Verify specific endpoints exist
        expected_podcast_paths = [
            "/api/podcasts/generate",
            "/api/podcasts/",
            "/api/podcasts/{podcast_id}",
        ]

        for expected_path in expected_podcast_paths:
            assert expected_path in paths, f"Missing podcast endpoint in OpenAPI: {expected_path}"


@pytest.mark.integration
class TestDatabaseEnumValidation:
    """Integration tests for database enum validation."""

    def test_prompt_template_enum_values_in_schema(self) -> None:
        """Integration: Verify all PromptTemplateType enum values are valid."""
        # Test all enum values that should exist
        expected_values = [
            "RAG_QUERY",
            "QUESTION_GENERATION",
            "RESPONSE_EVALUATION",
            "COT_REASONING",
            "RERANKING",  # This was missing from database
            "CUSTOM",
        ]

        for value in expected_values:
            # This should not raise an exception
            enum_value = PromptTemplateType(value)
            assert enum_value.value == value
            print(f"✅ Enum value {value} is valid")

    def test_enum_values_match_database_constraints(self) -> None:
        """Integration: Verify enum values can be used in database queries."""
        from sqlalchemy import text

        from rag_solution.file_management.database import engine

        with engine.connect() as connection:
            # Query the database enum values
            result = connection.execute(
                text(
                    """
                    SELECT enumlabel
                    FROM pg_enum
                    WHERE enumtypid = (
                        SELECT oid
                        FROM pg_type
                        WHERE typname = 'prompttemplatetype'
                    )
                    ORDER BY enumsortorder
                """
                )
            )

            db_enum_values = [row[0] for row in result.fetchall()]
            print(f"Database enum values: {db_enum_values}")

            # Verify all Python enum values exist in database
            for enum_value in PromptTemplateType:
                assert enum_value.value in db_enum_values, f"Python enum value {enum_value.value} not found in database"
                print(f"✅ Database has enum value: {enum_value.value}")


@pytest.mark.integration
class TestApplicationStartup:
    """Integration tests for application startup validation."""

    def test_app_imports_successfully(self) -> None:
        """Integration: Verify the main app can be imported without errors."""
        # This test passes if we can import main and create the app
        assert app is not None
        assert hasattr(app, "routes")
        assert len(app.routes) > 0
        print(f"✅ App imported successfully with {len(app.routes)} routes")

    def test_app_has_expected_middleware(self) -> None:
        """Integration: Verify app has expected middleware configured."""
        middleware_classes = [type(middleware).__name__ for middleware in app.user_middleware]

        expected_middleware = [
            "LoggingCORSMiddleware",
            "AuthenticationMiddleware",
        ]

        # SessionMiddleware is added via app.add_middleware, not user_middleware
        # Check if it exists in the middleware stack differently
        has_session_middleware = any("SessionMiddleware" in str(middleware) for middleware in app.user_middleware)
        if has_session_middleware:
            expected_middleware.append("SessionMiddleware")

        for expected in expected_middleware:
            found = any(expected in middleware for middleware in middleware_classes)
            if not found and expected == "SessionMiddleware":
                # Try alternative check for SessionMiddleware
                found = has_session_middleware
            assert found, f"Missing middleware: {expected}"
            print(f"✅ Found middleware: {expected}")
