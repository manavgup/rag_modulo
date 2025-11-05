"""
Simple pipeline test for Week 1-3.

Tests the first 3 stages (PipelineResolution → QueryEnhancement → Retrieval)
without requiring ChainOfThoughtService or LLMService.

Usage:
    TEST_COLLECTION_ID=<uuid> TEST_USER_ID=<uuid> PYTHONPATH=backend poetry run python test_pipeline_simple.py
"""

import asyncio
import os
from uuid import UUID

from core.config import get_settings
from rag_solution.file_management.database import get_db
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline.pipeline_executor import PipelineExecutor
from rag_solution.services.pipeline.search_context import SearchContext
from rag_solution.services.pipeline.stages import (
    PipelineResolutionStage,
    QueryEnhancementStage,
    RerankingStage,
    RetrievalStage,
)
from rag_solution.services.pipeline_service import PipelineService


async def test_retrieval_pipeline():
    """Test the first 4 stages of the pipeline (no CoT/Generation)."""
    print("\n" + "=" * 80)
    print("Week 1-3 Pipeline Simple Test (4 Stages)")
    print("=" * 80 + "\n")

    # Get settings
    settings = get_settings()

    # Initialize database session
    db = next(get_db())

    try:
        # Get test IDs from environment
        TEST_COLLECTION_ID = os.getenv("TEST_COLLECTION_ID")
        TEST_USER_ID = os.getenv("TEST_USER_ID")
        TEST_QUESTION = os.getenv("TEST_QUESTION", "What is IBM Watson?")

        if not TEST_COLLECTION_ID or not TEST_USER_ID:
            print("❌ ERROR: Please set TEST_COLLECTION_ID and TEST_USER_ID environment variables")
            return

        print(f"Configuration:")
        print(f"  Collection ID: {TEST_COLLECTION_ID}")
        print(f"  User ID: {TEST_USER_ID}")
        print(f"  Question: {TEST_QUESTION}")
        print()

        # Initialize service
        print("Initializing PipelineService...")
        pipeline_service = PipelineService(db, settings)
        print("✅ PipelineService initialized\n")

        # Create search input
        search_input = SearchInput(
            question=TEST_QUESTION,
            collection_id=UUID(TEST_COLLECTION_ID),
            user_id=UUID(TEST_USER_ID),
        )

        # Create context
        context = SearchContext(
            search_input=search_input,
            user_id=UUID(TEST_USER_ID),
            collection_id=UUID(TEST_COLLECTION_ID),
        )

        # Create first 4 stages
        print("Creating pipeline stages...")
        stages = [
            PipelineResolutionStage(pipeline_service),
            QueryEnhancementStage(pipeline_service),
            RetrievalStage(pipeline_service),
            RerankingStage(pipeline_service),
        ]
        print("✅ 4 stages created (Resolution → Enhancement → Retrieval → Reranking)\n")

        # Execute pipeline
        print("=" * 80)
        print("Executing Pipeline...")
        print("=" * 80 + "\n")

        executor = PipelineExecutor(stages)
        final_context = await executor.execute(context)

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

        if final_context.query_results:
            print("Top 3 Retrieved Documents:")
            for i, result in enumerate(final_context.query_results[:3]):
                print(f"\n  Document {i+1}:")
                if hasattr(result, 'score'):
                    print(f"    Score: {result.score:.4f}")
                if hasattr(result, 'chunk') and result.chunk and hasattr(result.chunk, 'text'):
                    text_preview = result.chunk.text[:100].replace('\n', ' ')
                    print(f"    Text: {text_preview}...")
        print()

        print("Metadata by Stage:")
        for stage_name, stage_metadata in final_context.metadata.items():
            print(f"  {stage_name}:")
            for key, value in stage_metadata.items():
                if key == 'execution_time':
                    print(f"    {key}: {value:.3f}s")
                else:
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
            ("Documents not empty", final_context.query_results and len(final_context.query_results) > 0),
            ("Metadata present", len(final_context.metadata) > 0),
            ("Has resolution metadata", 'pipeline_resolution' in final_context.metadata),
            ("Has enhancement metadata", 'query_enhancement' in final_context.metadata),
            ("Has retrieval metadata", 'retrieval' in final_context.metadata),
            ("Has reranking metadata", 'reranking' in final_context.metadata),
        ]

        all_passed = True
        for check_name, passed in checks:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {check_name}")
            if not passed:
                all_passed = False

        print()
        if all_passed:
            print("🎉 All checks passed! Pipeline stages 1-4 working correctly.")
            print("\nNext Steps:")
            print("  - Week 3 stages (Reranking, Reasoning, Generation) are implemented")
            print("  - Full 6-stage pipeline requires ChainOfThoughtService initialization")
            print("  - Week 4 will integrate this into SearchService")
        else:
            print("⚠️  Some checks failed. Review output above.")

        print("\n" + "=" * 80)
        print("Test Complete")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_retrieval_pipeline())
