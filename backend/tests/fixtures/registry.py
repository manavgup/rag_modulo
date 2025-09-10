"""Central registry of all test fixtures."""

from enum import Enum
from typing import Any


class FixtureType(Enum):
    """Types of fixtures based on testing layer."""

    ATOMIC = "atomic"  # Pure data, no dependencies
    UNIT = "unit"  # Mocked dependencies
    INTEGRATION = "integration"  # Real services via testcontainers
    E2E = "e2e"  # Full stack fixtures


class FixtureScope(Enum):
    """Fixture scopes for pytest."""

    FUNCTION = "function"  # Per test function
    CLASS = "class"  # Per test class
    MODULE = "module"  # Per test module
    SESSION = "session"  # Per test session


class FixtureRegistry:
    """Registry of all available fixtures."""

    def __init__(self) -> None:
        self.fixtures: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        fixture_type: FixtureType,
        scope: FixtureScope,
        location: str,
        description: str,
        dependencies: list[str] | None = None,
    ) -> None:
        """Register a fixture."""
        self.fixtures[name] = {
            "type": fixture_type,
            "scope": scope,
            "location": location,
            "description": description,
            "dependencies": dependencies or [],
            "usage_count": 0,
        }

    def find_fixtures(self, pattern: str | None = None, fixture_type: FixtureType | None = None) -> list[str]:
        """Find fixtures by pattern or type."""
        results = []
        for name, info in self.fixtures.items():
            if pattern and pattern.lower() not in name.lower():
                continue
            if fixture_type and info["type"] != fixture_type:
                continue
            results.append(name)
        return results

    def get_fixture_info(self, name: str) -> dict[str, Any] | None:
        """Get information about a specific fixture."""
        return self.fixtures.get(name)

    def increment_usage(self, name: str) -> None:
        """Increment usage count for a fixture."""
        if name in self.fixtures:
            self.fixtures[name]["usage_count"] += 1

    def get_most_used_fixtures(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get most frequently used fixtures."""
        return sorted(
            [(name, info["usage_count"]) for name, info in self.fixtures.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:limit]


# Global fixture registry instance
fixture_registry = FixtureRegistry()

# Register atomic fixtures
fixture_registry.register(
    "mock_env_vars",
    FixtureType.ATOMIC,
    FixtureScope.FUNCTION,
    "fixtures.atomic",
    "Mocked environment variables for testing",
)

fixture_registry.register(
    "isolated_test_env",
    FixtureType.ATOMIC,
    FixtureScope.FUNCTION,
    "fixtures.atomic",
    "Isolated test environment with mocked variables",
    ["mock_env_vars"],
)

fixture_registry.register(
    "mock_settings",
    FixtureType.ATOMIC,
    FixtureScope.FUNCTION,
    "fixtures.atomic",
    "Mock settings object for testing",
)

fixture_registry.register(
    "user_input_data",
    FixtureType.ATOMIC,
    FixtureScope.FUNCTION,
    "fixtures.atomic",
    "User input data for testing",
)

fixture_registry.register(
    "collection_input_data",
    FixtureType.ATOMIC,
    FixtureScope.FUNCTION,
    "fixtures.atomic",
    "Collection input data for testing",
)

fixture_registry.register(
    "team_input_data",
    FixtureType.ATOMIC,
    FixtureScope.FUNCTION,
    "fixtures.atomic",
    "Team input data for testing",
)

# Register unit fixtures
fixture_registry.register(
    "mock_user_service",
    FixtureType.UNIT,
    FixtureScope.FUNCTION,
    "fixtures.unit",
    "Mocked user service for unit tests",
)

fixture_registry.register(
    "mock_collection_service",
    FixtureType.UNIT,
    FixtureScope.FUNCTION,
    "fixtures.unit",
    "Mocked collection service for unit tests",
)

fixture_registry.register(
    "mock_team_service",
    FixtureType.UNIT,
    FixtureScope.FUNCTION,
    "fixtures.unit",
    "Mocked team service for unit tests",
)

fixture_registry.register(
    "mock_llm_provider",
    FixtureType.UNIT,
    FixtureScope.FUNCTION,
    "fixtures.unit",
    "Mocked LLM provider for unit tests",
)

fixture_registry.register(
    "mock_vector_store",
    FixtureType.UNIT,
    FixtureScope.FUNCTION,
    "fixtures.unit",
    "Mocked vector store for unit tests",
)

fixture_registry.register(
    "mock_database_session",
    FixtureType.UNIT,
    FixtureScope.FUNCTION,
    "fixtures.unit",
    "Mocked database session for unit tests",
)

fixture_registry.register(
    "mock_http_client",
    FixtureType.UNIT,
    FixtureScope.FUNCTION,
    "fixtures.unit",
    "Mocked HTTP client for unit tests",
)


def get_fixture_registry() -> FixtureRegistry:
    """Get the global fixture registry."""
    return fixture_registry


def discover_fixtures() -> dict[str, int]:
    """Discover and count fixtures across the test suite."""
    # This would scan the test files and count fixture usage
    # For now, return a placeholder
    return {
        "atomic": 6,
        "unit": 7,
        "integration": 0,  # To be implemented
        "e2e": 0,  # To be implemented
    }
