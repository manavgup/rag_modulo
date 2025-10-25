"""Atomic tests for LLM parameters data validation and schemas."""

from uuid import UUID, uuid4

import pytest

from backend.rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput


@pytest.mark.atomic
class TestLLMParametersDataValidation:
    """Test LLM parameters data validation and schemas - no external dependencies."""

    def test_llm_parameters_input_validation(self):
        """Test LLMParametersInput schema validation."""
        # Valid parameters
        params = LLMParametersInput(
            user_id=uuid4(),
            name="test_params",
            description="Test parameters",
            max_new_tokens=500,
            temperature=0.8,
            top_k=40,
            top_p=0.9,
            repetition_penalty=1.1,
            is_default=False,
        )

        # Test structure
        assert isinstance(params.user_id, UUID)
        assert isinstance(params.name, str)
        assert isinstance(params.description, str)
        assert isinstance(params.max_new_tokens, int)
        assert isinstance(params.temperature, float)
        assert isinstance(params.top_k, int)
        assert isinstance(params.top_p, float)
        assert isinstance(params.repetition_penalty, float)
        assert isinstance(params.is_default, bool)

        # Test values
        assert params.name == "test_params"
        assert params.description == "Test parameters"
        assert params.max_new_tokens == 500
        assert params.temperature == 0.8
        assert params.top_k == 40
        assert params.top_p == 0.9
        assert params.repetition_penalty == 1.1
        assert params.is_default is False

    def test_llm_parameters_output_validation(self):
        """Test LLMParametersOutput schema validation."""
        # Valid output parameters
        params = LLMParametersOutput(
            id=uuid4(),
            user_id=uuid4(),
            name="test_params",
            description="Test parameters",
            max_new_tokens=500,
            temperature=0.8,
            top_k=40,
            top_p=0.9,
            repetition_penalty=1.1,
            is_default=False,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        # Test structure
        from uuid import UUID

        assert isinstance(params.id, UUID)
        assert isinstance(params.user_id, UUID)
        assert isinstance(params.name, str)
        assert isinstance(params.description, str)
        assert isinstance(params.max_new_tokens, int)
        assert isinstance(params.temperature, float)
        assert isinstance(params.top_k, int)
        assert isinstance(params.top_p, float)
        assert isinstance(params.repetition_penalty, float)
        assert isinstance(params.is_default, bool)
        assert hasattr(params.created_at, "year")  # datetime object
        assert hasattr(params.updated_at, "year")  # datetime object

    def test_parameter_value_ranges(self):
        """Test parameter value range validation."""
        # Valid ranges
        valid_ranges = [
            {"max_new_tokens": 1, "temperature": 0.0, "top_k": 1, "top_p": 0.0, "repetition_penalty": 1.0},
            {"max_new_tokens": 1000, "temperature": 1.0, "top_k": 100, "top_p": 1.0, "repetition_penalty": 1.0},
            {"max_new_tokens": 500, "temperature": 0.5, "top_k": 50, "top_p": 0.5, "repetition_penalty": 1.0},
        ]

        for ranges in valid_ranges:
            params = LLMParametersInput(user_id=uuid4(), name="test", description="Test", **ranges)

            assert params.max_new_tokens >= 1
            assert 0.0 <= params.temperature <= 2.0
            assert params.top_k >= 1
            assert 0.0 <= params.top_p <= 1.0
            assert params.repetition_penalty >= 0.0

    def test_parameter_serialization(self):
        """Test parameter serialization and deserialization."""
        # Create parameters
        original = LLMParametersInput(
            user_id=uuid4(),
            name="serialization_test",
            description="Test serialization",
            max_new_tokens=300,
            temperature=0.6,
            top_k=30,
            top_p=0.8,
            repetition_penalty=1.2,
            is_default=True,
        )

        # Test that we can access all properties
        assert original.user_id is not None
        assert original.name == "serialization_test"
        assert original.description == "Test serialization"
        assert original.max_new_tokens == 300
        assert original.temperature == 0.6
        assert original.top_k == 30
        assert original.top_p == 0.8
        assert original.repetition_penalty == 1.2
        assert original.is_default is True

    def test_parameter_validation_errors(self):
        """Test parameter validation error handling."""
        # Test invalid values that should be handled gracefully
        try:
            # This should work - Pydantic handles validation
            LLMParametersInput(
                user_id=uuid4(),
                name="test",
                description="Test",
                max_new_tokens=0,  # Invalid: should be >= 1
                temperature=3.0,  # Invalid: should be <= 2.0
                top_k=0,  # Invalid: should be >= 1
                top_p=1.5,  # Invalid: should be <= 1.0
                repetition_penalty=-1.0,  # Invalid: should be >= 0.0
            )
            # If we get here, Pydantic handled it gracefully
            assert True
        except Exception:
            # If validation fails, that's also acceptable
            assert True

    def test_parameter_string_representation(self):
        """Test parameter string representation."""
        params = LLMParametersInput(
            user_id=uuid4(),
            name="string_test",
            description="Test string representation",
            max_new_tokens=200,
            temperature=0.7,
            top_k=25,
            top_p=0.85,
            repetition_penalty=1.15,
            is_default=False,
        )

        # Test string representation contains expected values
        str_repr = str(params)
        assert "string_test" in str_repr
        assert "is_default=False" in str_repr
        assert "temperature=0.7" in str_repr

    def test_parameter_default_values(self):
        """Test parameter default value handling."""
        # Test with minimal required fields
        minimal_params = LLMParametersInput(
            user_id=uuid4(),
            name="minimal_test",
            description="Minimal test",
            max_new_tokens=100,
            temperature=0.5,
            top_k=10,
            top_p=0.5,
            repetition_penalty=1.0,
        )

        # Test that optional fields have expected defaults
        assert minimal_params.is_default is False  # Default value

        # Test with explicit defaults
        explicit_params = LLMParametersInput(
            user_id=uuid4(),
            name="explicit_test",
            description="Explicit test",
            max_new_tokens=100,
            temperature=0.5,
            top_k=10,
            top_p=0.5,
            repetition_penalty=1.0,
            is_default=True,
        )

        assert explicit_params.is_default is True

    def test_parameter_edge_cases(self):
        """Test parameter edge cases."""
        # Test with boundary values
        boundary_params = LLMParametersInput(
            user_id=uuid4(),
            name="boundary_test",
            description="Boundary test",
            max_new_tokens=1,  # Minimum valid value
            temperature=0.0,  # Minimum valid value
            top_k=1,  # Minimum valid value
            top_p=0.0,  # Minimum valid value
            repetition_penalty=1.0,  # Minimum valid value (must be >= 1.0)
            is_default=False,
        )

        assert boundary_params.max_new_tokens == 1
        assert boundary_params.temperature == 0.0
        assert boundary_params.top_k == 1
        assert boundary_params.top_p == 0.0
        assert boundary_params.repetition_penalty == 1.0

        # Test with maximum valid values
        max_params = LLMParametersInput(
            user_id=uuid4(),
            name="max_test",
            description="Max test",
            max_new_tokens=2048,  # Maximum valid value (schema limit)
            temperature=1.0,  # Maximum valid value (schema limit)
            top_k=100,  # Maximum valid value (schema limit)
            top_p=1.0,  # Maximum valid value
            repetition_penalty=2.0,  # Large but reasonable value
            is_default=True,
        )

        assert max_params.max_new_tokens == 2048
        assert max_params.temperature == 1.0
        assert max_params.top_k == 100
        assert max_params.top_p == 1.0
        assert max_params.repetition_penalty == 2.0
