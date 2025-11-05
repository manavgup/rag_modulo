"""
Quick manual test script for Week 1-3 Pipeline Implementation.

This script tests the full 6-stage pipeline without requiring SearchService integration.
Run this to validate the pipeline works end-to-end before Week 4.

Usage:
    poetry run python test_pipeline_quick.py

Prerequisites:
    - Infrastructure running: make local-dev-infra
    - .env configured with WATSONX credentials
    - Test collection with documents
"""

import asyncio
import os
from uuid import UUID

from core.config import get_settings
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.generation.providers.factory import LLMService
from rag_solution.services.pipeline.pipeline_executor import PipelineExecutor
from rag_solution.services.pipeline.search_context import SearchContext
from rag_solution.services.pipeline.stages import (
    GenerationStage,
    PipelineResolutionStage,
    QueryEnhancementStage,
    ReasoningStage,
    RerankingStage,
    RetrievalStage,
)
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.search_service import SearchService
from vectordbs.vector_store import get_vector_store


async def test_full_pipeline():
    """Test the full 6-stage pipeline."""
    print("\n" + "=" * 80)
    print("Week 1-3 Pipeline Manual Test")
    print("=" * 80 + "\n")

    # Get settings
    settings = get_settings()

    # Initialize database session
    from rag_solution.file_management.database import get_db

    db = next(get_db())

    try:
        # ===== CONFIGURE THESE VALUES =====
        # Replace with your test collection and user IDs
        TEST_COLLECTION_ID = os.getenv(
            "TEST_COLLECTION_ID", "123e4567-e89b-12d3-a456-426614174000"
        )  # Replace!
        TEST_USER_ID = os.getenv("TEST_USER_ID", "123e4567-e89b-12d3-a456-426614174001")  # Replace!
        TEST_QUESTION = "What is machine learning and how does it work?"

        print(f"Configuration:")
        print(f"  Collection ID: {TEST_COLLECTION_ID}")
        print(f"  User ID: {TEST_USER_ID}")
        print(f"  Question: {TEST_QUESTION}")
        print()

        # Initialize services
        print("Initializing services...")
        vector_store = get_vector_store(settings)
        pipeline_service = PipelineService(db, settings)
        llm_service = LLMService(settings=settings, db=db)
        search_service = SearchService(db=db, vector_store=vector_store, settings=settings)
        cot_service = ChainOfThoughtService(
            settings=settings, llm_service=llm_service, search_service=search_service, db=db
        )
        print("✅ Services initialized\n")

        # Create search input
        search_input = SearchInput(
            question=TEST_QUESTION,
            collection_id=UUID(TEST_COLLECTION_ID),
            user_id=UUID(TEST_USER_ID),
            config_metadata={
                "cot_enabled": True,  # Force CoT for testing
                "show_cot_steps": True,
            },
        )

        # Create context
        context = SearchContext(
            search_input=search_input,
            user_id=UUID(TEST_USER_ID),
            collection_id=UUID(TEST_COLLECTION_ID),
        )

        # Create all 6 stages
        print("Creating pipeline stages...")
        stages = [
            PipelineResolutionStage(pipeline_service),
            QueryEnhancementStage(pipeline_service),
            RetrievalStage(pipeline_service),
            RerankingStage(pipeline_service),
            ReasoningStage(cot_service),
            GenerationStage(pipeline_service),
        ]
        print("✅ 6 stages created\n")

        # Execute pipeline
        print("=" * 80)
        print("Executing Pipeline...")
        print("=" * 80 + "\n")

        executor = PipelineExecutor()
        final_context = await executor.execute(stages, context)

        # Display results
        print("\n" + "=" * 80)
        print("Pipeline Execution Complete!")
        print("=" * 80 + "\n")

        print("Results Summary:")
        print(f"  Pipeline ID: {final_context.pipeline_id}")
        print(f"  Original Query: {final_context.search_input.question}")
        print(f"  Rewritten Query: {final_context.rewritten_query}")
        print(f"  Retrieved Documents: {len(final_context.query_results) if final_context.query_results else 0}")
        print()

        if hasattr(final_context, "cot_output") and final_context.cot_output:
            print("Chain of Thought Results:")
            print(f"  Reasoning Steps: {len(final_context.cot_output.reasoning_steps)}")
            print(f"  Confidence: {final_context.cot_output.total_confidence:.2f}")
            print(f"  Execution Time: {final_context.cot_output.total_execution_time:.2f}s")
            print()

            print("Reasoning Steps:")
            for step in final_context.cot_output.reasoning_steps:
                print(f"\n  Step {step.step_number}: {step.question}")
                print(f"    Answer: {step.intermediate_answer[:100]}...")
                print(f"    Confidence: {step.confidence_score:.2f}")

            print()

        print("Generated Answer:")
        print(f"  {final_context.generated_answer}")
        print()

        print("Metadata by Stage:")
        for stage_name, stage_metadata in final_context.metadata.items():
            print(f"  {stage_name}:")
            for key, value in stage_metadata.items():
                print(f"    {key}: {value}")
        print()

        # Validate
        print("=" * 80)
        print("Validation Checks:")
        print("=" * 80)
        checks = [
            ("Pipeline ID set", final_context.pipeline_id is not None),
            ("Query rewritten", final_context.rewritten_query is not None),
            ("Documents retrieved", final_context.query_results is not None),
            ("Answer generated", final_context.generated_answer is not None),
            ("Metadata present", len(final_context.metadata) > 0),
        ]

        if hasattr(final_context, "cot_output") and final_context.cot_output:
            checks.append(("CoT reasoning applied", True))
            checks.append(
                (
                    "CoT steps present",
                    len(final_context.cot_output.reasoning_steps) > 0,
                )
            )

        all_passed = True
        for check_name, passed in checks:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {check_name}")
            if not passed:
                all_passed = False

        print()
        if all_passed:
            print("🎉 All checks passed! Pipeline is working correctly.")
        else:
            print("⚠️  Some checks failed. Review output above.")

        print("\n" + "=" * 80)
        print("Test Complete")
        print("=" * 80 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
