"""Unit tests for the RAG technique system.

Tests cover:
- Technique registration and discovery
- Pipeline building and validation
- Technique execution
- Configuration validation
- Error handling
"""

from __future__ import annotations

import pytest
from pydantic import UUID4

from rag_solution.techniques.base import (
    BaseTechnique,
    TechniqueConfig,
    TechniqueContext,
    TechniqueResult,
    TechniqueStage,
)
from rag_solution.techniques.pipeline import TECHNIQUE_PRESETS, TechniquePipeline, TechniquePipelineBuilder
from rag_solution.techniques.registry import TechniqueRegistry, register_technique


# Test fixtures


@pytest.fixture
def registry():
    """Create a fresh technique registry for testing."""
    return TechniqueRegistry()


@pytest.fixture
def sample_context():
    """Create a sample technique context for testing."""
    return TechniqueContext(
        user_id=UUID4("12345678-1234-5678-1234-567812345678"),
        collection_id=UUID4("87654321-4321-8765-4321-876543218765"),
        original_query="What is machine learning?",
        current_query="What is machine learning?",
    )


# Mock technique implementations for testing


class MockQueryTransformTechnique(BaseTechnique[str, str]):
    """Mock technique that transforms queries."""

    technique_id = "mock_transform"
    name = "Mock Query Transform"
    description = "Test technique for query transformation"
    stage = TechniqueStage.QUERY_TRANSFORMATION
    requires_llm = True
    estimated_latency_ms = 100

    async def execute(self, context: TechniqueContext) -> TechniqueResult[str]:
        """Transform the query by appending suffix."""
        suffix = context.config.get("suffix", " [transformed]")
        transformed = context.current_query + suffix
        context.current_query = transformed

        return TechniqueResult(
            success=True,
            output=transformed,
            metadata={"original": context.original_query},
            technique_id=self.technique_id,
            execution_time_ms=0,
        )

    def validate_config(self, config: dict) -> bool:
        """Validate config."""
        return True


class MockRetrievalTechnique(BaseTechnique[str, list]):
    """Mock technique that retrieves documents."""

    technique_id = "mock_retrieval"
    name = "Mock Retrieval"
    description = "Test technique for document retrieval"
    stage = TechniqueStage.RETRIEVAL
    requires_vector_store = True
    estimated_latency_ms = 50

    async def execute(self, context: TechniqueContext) -> TechniqueResult[list]:
        """Return mock documents."""
        num_docs = context.config.get("num_docs", 5)
        docs = [{"id": i, "text": f"Document {i}"} for i in range(num_docs)]

        return TechniqueResult(
            success=True,
            output=docs,
            metadata={"num_docs": num_docs},
            technique_id=self.technique_id,
            execution_time_ms=0,
        )

    def validate_config(self, config: dict) -> bool:
        """Validate config."""
        num_docs = config.get("num_docs")
        if num_docs is not None and (not isinstance(num_docs, int) or num_docs <= 0):
            return False
        return True


class MockFailingTechnique(BaseTechnique[str, str]):
    """Mock technique that always fails."""

    technique_id = "mock_failing"
    name = "Mock Failing"
    description = "Test technique that fails"
    stage = TechniqueStage.QUERY_PREPROCESSING

    async def execute(self, context: TechniqueContext) -> TechniqueResult[str]:
        """Always return failure."""
        return TechniqueResult(
            success=False,
            output="",
            metadata={},
            technique_id=self.technique_id,
            execution_time_ms=0,
            error="Intentional test failure",
        )

    def validate_config(self, config: dict) -> bool:
        """Validate config."""
        return True


# Tests for TechniqueRegistry


class TestTechniqueRegistry:
    """Tests for technique registry."""

    def test_register_technique(self, registry):
        """Test registering a technique."""
        registry.register("test_technique", MockQueryTransformTechnique)

        assert registry.is_registered("test_technique")
        assert "test_technique" in [t.technique_id for t in registry.list_techniques()]

    def test_register_duplicate_technique_warns(self, registry, caplog):
        """Test registering duplicate technique shows warning."""
        registry.register("test_technique", MockQueryTransformTechnique)
        registry.register("test_technique", MockRetrievalTechnique)  # Duplicate

        assert "already registered" in caplog.text.lower()

    def test_get_technique(self, registry):
        """Test getting a technique instance."""
        registry.register("test_technique", MockQueryTransformTechnique)

        technique = registry.get_technique("test_technique")

        assert isinstance(technique, MockQueryTransformTechnique)
        assert technique.technique_id == "test_technique"

    def test_get_unknown_technique_raises(self, registry):
        """Test getting unknown technique raises ValueError."""
        with pytest.raises(ValueError, match="Unknown technique"):
            registry.get_technique("nonexistent")

    def test_list_techniques(self, registry):
        """Test listing all techniques."""
        registry.register("transform", MockQueryTransformTechnique)
        registry.register("retrieval", MockRetrievalTechnique)

        techniques = registry.list_techniques()

        assert len(techniques) == 2
        assert {t.technique_id for t in techniques} == {"transform", "retrieval"}

    def test_list_techniques_by_stage(self, registry):
        """Test filtering techniques by stage."""
        registry.register("transform", MockQueryTransformTechnique)
        registry.register("retrieval", MockRetrievalTechnique)

        retrieval_techniques = registry.list_techniques(stage=TechniqueStage.RETRIEVAL)

        assert len(retrieval_techniques) == 1
        assert retrieval_techniques[0].technique_id == "retrieval"

    def test_validate_pipeline_success(self, registry):
        """Test validating a valid pipeline."""
        registry.register("transform", MockQueryTransformTechnique)
        registry.register("retrieval", MockRetrievalTechnique)

        is_valid, error = registry.validate_pipeline(["transform", "retrieval"])

        assert is_valid
        assert error is None

    def test_validate_pipeline_unknown_technique(self, registry):
        """Test validating pipeline with unknown technique."""
        registry.register("transform", MockQueryTransformTechnique)

        is_valid, error = registry.validate_pipeline(["transform", "nonexistent"])

        assert not is_valid
        assert "Unknown technique" in error

    def test_validate_pipeline_invalid_stage_order(self, registry):
        """Test validating pipeline with invalid stage ordering."""
        registry.register("transform", MockQueryTransformTechnique)
        registry.register("retrieval", MockRetrievalTechnique)

        # Retrieval before transformation (wrong order)
        is_valid, error = registry.validate_pipeline(["retrieval", "transform"])

        assert not is_valid
        assert "stage ordering" in error.lower()

    def test_validate_empty_pipeline(self, registry):
        """Test validating empty pipeline."""
        is_valid, error = registry.validate_pipeline([])

        assert not is_valid
        assert "empty" in error.lower()

    def test_unregister_technique(self, registry):
        """Test unregistering a technique."""
        registry.register("test_technique", MockQueryTransformTechnique)
        assert registry.is_registered("test_technique")

        registry.unregister("test_technique")

        assert not registry.is_registered("test_technique")

    def test_clear_registry(self, registry):
        """Test clearing all techniques."""
        registry.register("t1", MockQueryTransformTechnique)
        registry.register("t2", MockRetrievalTechnique)

        registry.clear()

        assert len(registry.list_techniques()) == 0


class TestRegisterDecorator:
    """Tests for @register_technique decorator."""

    def test_register_decorator_with_id(self):
        """Test decorator with explicit technique ID."""
        test_registry = TechniqueRegistry()

        @register_technique("decorated_technique")
        class DecoratedTechnique(BaseTechnique[str, str]):
            technique_id = "should_be_overridden"
            name = "Decorated"
            description = "Test"
            stage = TechniqueStage.QUERY_PREPROCESSING

            async def execute(self, context):
                return TechniqueResult(
                    success=True, output="", metadata={}, technique_id=self.technique_id, execution_time_ms=0
                )

            def validate_config(self, config):
                return True

        # Manually register to our test registry
        test_registry.register("decorated_technique", DecoratedTechnique)

        assert test_registry.is_registered("decorated_technique")


# Tests for TechniquePipelineBuilder


class TestTechniquePipelineBuilder:
    """Tests for pipeline builder."""

    def test_add_technique(self, registry):
        """Test adding techniques to builder."""
        registry.register("t1", MockQueryTransformTechnique)

        builder = TechniquePipelineBuilder(registry)
        builder.add_technique("t1", {"suffix": " [custom]"})

        assert len(builder.techniques) == 1
        assert builder.techniques[0][0] == "t1"
        assert builder.techniques[0][1]["suffix"] == " [custom]"

    def test_build_pipeline(self, registry):
        """Test building a pipeline."""
        registry.register("transform", MockQueryTransformTechnique)
        registry.register("retrieval", MockRetrievalTechnique)

        builder = TechniquePipelineBuilder(registry)
        pipeline = builder.add_technique("transform").add_technique("retrieval").build()

        assert isinstance(pipeline, TechniquePipeline)
        assert len(pipeline.techniques) == 2

    def test_build_invalid_pipeline_raises(self, registry):
        """Test building invalid pipeline raises ValueError."""
        builder = TechniquePipelineBuilder(registry)

        with pytest.raises(ValueError, match="Invalid pipeline"):
            builder.add_technique("nonexistent").build()

    def test_validate_pipeline(self, registry):
        """Test validating pipeline configuration."""
        registry.register("transform", MockQueryTransformTechnique)

        builder = TechniquePipelineBuilder(registry)
        builder.add_technique("transform")

        is_valid, error = builder.validate()

        assert is_valid
        assert error is None

    def test_validate_config_invalid(self, registry):
        """Test validation catches invalid config."""
        registry.register("retrieval", MockRetrievalTechnique)

        builder = TechniquePipelineBuilder(registry)
        builder.add_technique("retrieval", {"num_docs": -5})  # Invalid

        is_valid, error = builder.validate()

        assert not is_valid
        assert "Invalid config" in error

    def test_clear_builder(self, registry):
        """Test clearing builder."""
        registry.register("t1", MockQueryTransformTechnique)

        builder = TechniquePipelineBuilder(registry)
        builder.add_technique("t1")
        assert len(builder.techniques) == 1

        builder.clear()

        assert len(builder.techniques) == 0


# Tests for TechniquePipeline


class TestTechniquePipeline:
    """Tests for pipeline execution."""

    @pytest.mark.asyncio
    async def test_execute_pipeline(self, registry, sample_context):
        """Test executing a pipeline."""
        registry.register("transform", MockQueryTransformTechnique)
        registry.register("retrieval", MockRetrievalTechnique)

        builder = TechniquePipelineBuilder(registry)
        pipeline = builder.add_technique("transform", {"suffix": " [test]"}).add_technique("retrieval").build()

        result_context = await pipeline.execute(sample_context)

        # Query should be transformed
        assert result_context.current_query == "What is machine learning? [test]"

        # Should have execution trace
        assert "Executing: mock_transform" in result_context.execution_trace
        assert "Executing: mock_retrieval" in result_context.execution_trace

        # Should have metrics
        assert "pipeline_metrics" in result_context.metrics
        assert "mock_transform" in result_context.metrics["pipeline_metrics"]
        assert "mock_retrieval" in result_context.metrics["pipeline_metrics"]

    @pytest.mark.asyncio
    async def test_pipeline_continues_on_failure(self, registry, sample_context):
        """Test pipeline continues even if a technique fails."""
        registry.register("failing", MockFailingTechnique)
        registry.register("transform", MockQueryTransformTechnique)

        builder = TechniquePipelineBuilder(registry)
        pipeline = builder.add_technique("failing").add_technique("transform").build()

        result_context = await pipeline.execute(sample_context)

        # Pipeline should complete
        assert "pipeline_metrics" in result_context.metrics

        # Failing technique should be recorded
        assert result_context.metrics["pipeline_metrics"]["mock_failing"]["success"] is False

        # Subsequent technique should still execute
        assert result_context.metrics["pipeline_metrics"]["mock_transform"]["success"] is True

    @pytest.mark.asyncio
    async def test_get_estimated_cost(self, registry):
        """Test estimating pipeline cost."""
        registry.register("transform", MockQueryTransformTechnique)
        registry.register("retrieval", MockRetrievalTechnique)

        builder = TechniquePipelineBuilder(registry)
        pipeline = builder.add_technique("transform").add_technique("retrieval").build()

        cost = pipeline.get_estimated_cost()

        assert cost["technique_count"] == 2
        assert cost["estimated_latency_ms"] == 150  # 100 + 50
        assert cost["llm_techniques"] == 1  # Only transform requires LLM

    def test_get_technique_ids(self, registry):
        """Test getting technique IDs from pipeline."""
        registry.register("t1", MockQueryTransformTechnique)
        registry.register("t2", MockRetrievalTechnique)

        builder = TechniquePipelineBuilder(registry)
        pipeline = builder.add_technique("t1").add_technique("t2").build()

        ids = pipeline.get_technique_ids()

        assert ids == ["t1", "t2"]


# Tests for technique presets


class TestTechniquePresets:
    """Tests for predefined technique presets."""

    def test_presets_defined(self):
        """Test that all expected presets are defined."""
        expected_presets = ["default", "fast", "accurate", "cost_optimized", "comprehensive"]

        for preset in expected_presets:
            assert preset in TECHNIQUE_PRESETS

    def test_preset_structure(self):
        """Test preset configurations have correct structure."""
        for preset_name, preset_config in TECHNIQUE_PRESETS.items():
            assert isinstance(preset_config, list)
            for technique_config in preset_config:
                assert isinstance(technique_config, TechniqueConfig)
                assert technique_config.technique_id
                assert isinstance(technique_config.enabled, bool)
                assert isinstance(technique_config.config, dict)


# Tests for TechniqueConfig


class TestTechniqueConfig:
    """Tests for TechniqueConfig schema."""

    def test_create_technique_config(self):
        """Test creating a technique config."""
        config = TechniqueConfig(technique_id="test", enabled=True, config={"key": "value"})

        assert config.technique_id == "test"
        assert config.enabled is True
        assert config.config == {"key": "value"}

    def test_technique_config_defaults(self):
        """Test default values for TechniqueConfig."""
        config = TechniqueConfig(technique_id="test")

        assert config.enabled is True
        assert config.config == {}
        assert config.fallback_enabled is True

    def test_technique_config_forbid_extra(self):
        """Test that extra fields are rejected."""
        with pytest.raises(Exception):  # Pydantic validation error
            TechniqueConfig(technique_id="test", unknown_field="value")


# Integration tests


class TestTechniqueSystemIntegration:
    """Integration tests for the entire technique system."""

    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self, registry, sample_context):
        """Test complete pipeline from building to execution."""
        # Register techniques
        registry.register("transform", MockQueryTransformTechnique)
        registry.register("retrieval", MockRetrievalTechnique)

        # Build pipeline
        builder = TechniquePipelineBuilder(registry)
        pipeline = (
            builder.add_technique("transform", {"suffix": " [enhanced]"})
            .add_technique("retrieval", {"num_docs": 3})
            .build()
        )

        # Execute pipeline
        result_context = await pipeline.execute(sample_context)

        # Verify results
        assert result_context.current_query == "What is machine learning? [enhanced]"
        assert "mock_transform" in result_context.intermediate_results
        assert "mock_retrieval" in result_context.intermediate_results
        assert len(result_context.intermediate_results["mock_retrieval"]) == 3

        # Verify metrics
        pipeline_metrics = result_context.metrics["pipeline_metrics"]
        assert pipeline_metrics["techniques_executed"] == 2
        assert pipeline_metrics["techniques_succeeded"] == 2
        assert pipeline_metrics["techniques_failed"] == 0
