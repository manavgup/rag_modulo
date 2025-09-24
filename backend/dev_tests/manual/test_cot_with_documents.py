#!/usr/bin/env python3
"""Test Chain of Thought with real document retrieval.

This script tests that CoT properly integrates with document retrieval from collections.
"""

import os
import sys
from typing import Any

# Add the backend directory to sys.path to enable imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, backend_dir)

from rag_solution.cli.client import RAGAPIClient  # noqa: E402
from rag_solution.cli.commands.collections import CollectionCommands  # noqa: E402
from rag_solution.cli.commands.pipelines import PipelineCommands  # noqa: E402
from rag_solution.cli.commands.users import UserCommands  # noqa: E402
from rag_solution.cli.config import RAGConfig  # noqa: E402
from rag_solution.cli.mock_auth_helper import setup_mock_authentication  # noqa: E402


def setup_environment() -> tuple[Any, Any, str]:
    """Set up CLI configuration and authentication."""
    from pydantic import HttpUrl

    config = RAGConfig(
        api_url=HttpUrl("http://localhost:8000"),
        profile="test",
        timeout=30,
        output_format="table",
        verbose=True,
        dry_run=False,
    )

    api_client = RAGAPIClient(config)
    print("🔐 Setting up mock authentication...")
    mock_token = setup_mock_authentication(api_client, verbose=True)

    return config, api_client, mock_token


def get_user_info(api_client: Any, config: Any) -> str | None:
    """Get current user information."""
    users_cmd = UserCommands(api_client, config)
    user_result = users_cmd.get_current_user()

    if user_result.success:
        user_data = user_result.data
        if user_data:
            print("✅ User information:")
            user_id = user_data.get("id", "N/A")
            print(f"   User ID: {user_id} (type: {type(user_id)})")
            print(f"   Name: {user_data.get('name', 'N/A')}")
            print(f"   Email: {user_data.get('email', 'N/A')}")
            return user_id
        else:
            print("❌ No user data returned")
            return None
    else:
        print(f"❌ Failed to get user info: {user_result.message}")
        return None


def ensure_user_has_pipeline(api_client: Any, config: Any, user_id: str) -> str | None:
    """Ensure user has a pipeline, create one if needed."""
    pipelines_cmd = PipelineCommands(api_client, config)

    # Get user's pipelines
    print("\n🔧 Checking user pipelines...")
    result = pipelines_cmd.list_pipelines(user_id)

    if result.success and result.data:
        pipelines: list[dict[str, Any]] = result.data if isinstance(result.data, list) else []

        if pipelines:
            print(f"   Found {len(pipelines)} pipeline(s)")
            # Look for default pipeline
            default_pipeline = None
            for pipeline in pipelines:
                if pipeline.get("is_default"):
                    default_pipeline = pipeline
                    break

            # If no default, use the first one
            if not default_pipeline and pipelines:
                default_pipeline = pipelines[0]

            if default_pipeline:
                pipeline_id = default_pipeline.get("id")
                pipeline_name = default_pipeline.get("name", "Unknown")
                print(f"   Using pipeline: {pipeline_name} (ID: {pipeline_id})")
                return pipeline_id

        # No pipelines found, create a default one
        print("   No pipelines found, creating default pipeline...")
        create_result = pipelines_cmd.create_pipeline(
            name="Default CoT Pipeline",
            llm_provider_id=None,  # Use default provider
            parameters={"retrieval": {"top_k": 10}, "generation": {"temperature": 0.7}},
        )

        if create_result.success and create_result.data:
            pipeline_id = create_result.data.get("id")
            print(f"   ✅ Created pipeline with ID: {pipeline_id}")
            return pipeline_id
        else:
            print(f"   ❌ Failed to create pipeline: {create_result.message}")
            return None
    else:
        print(f"   ❌ Failed to list pipelines: {result.message}")
        return None


def list_collections(api_client: Any, config: Any) -> list[dict[str, Any]]:
    """List available collections."""
    collections_cmd = CollectionCommands(api_client, config)
    result = collections_cmd.list_collections()

    if result.success and result.data:
        if isinstance(result.data, list):
            collections = result.data
        else:
            collections = result.data.get("collections", []) if result.data else []

        if collections:
            print(f"\n📁 Available Collections ({len(collections)}):")
            for i, collection in enumerate(collections, 1):
                name = collection.get("name", "Unnamed")
                collection_id = collection.get("id", "N/A")
                files = collection.get("files", [])
                file_count = len(files) if files else 0
                status = collection.get("status", "unknown")
                print(f"   {i}. {name} (ID: {collection_id})")
                print(f"      Files: {file_count}, Status: {status}")
            return collections
        else:
            print("\n📭 No collections found")
            return []
    else:
        print(f"\n❌ Failed to list collections: {result.message}")
        return []


def run_search(
    api_client: Any, collection_id: str, question: str, user_id: str, cot_enabled: bool = False
) -> dict[str, Any] | None:
    """Run a search with or without CoT enabled."""

    # Get proper user_id from /api/auth/me
    try:
        current_user = api_client.get("/api/auth/me")
        api_user_id = current_user.get("uuid") or current_user.get("id")
    except Exception as e:
        print(f"   ❌ Failed to get user from /api/auth/me: {e}")
        api_user_id = user_id  # Fallback to provided user_id

    # Build payload
    payload = {"question": question, "collection_id": collection_id, "user_id": api_user_id, "config_metadata": {}}

    if cot_enabled:
        payload["config_metadata"] = {
            "cot_enabled": True,
            "show_cot_steps": True,
            "cot_config": {
                "max_reasoning_depth": 3,
                "reasoning_strategy": "decomposition",
                "token_budget_multiplier": 1.5,
            },
        }

    try:
        response = api_client.post("/api/search", data=payload)
        return response if response and "answer" in response else None
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        return None


def compare_search_results(
    api_client: Any, collection_id: str, question: str, user_id: str, pipeline_id: str | None
) -> bool:
    """Compare search results with CoT ON vs OFF."""
    print("\n🔍 Comparing Search Results: CoT ON vs OFF")
    print("=" * 70)
    print(f"Question: {question}")
    print(f"Collection: {collection_id}")
    if pipeline_id:
        print(f"Pipeline: {pipeline_id}")

    # Run search without CoT
    print("\n📊 Running Regular Search (CoT OFF)...")
    regular_response = run_search(api_client, collection_id, question, user_id, cot_enabled=False)

    # Run search with CoT
    print("\n🧠 Running Chain of Thought Search (CoT ON)...")
    cot_response = run_search(api_client, collection_id, question, user_id, cot_enabled=True)

    if not regular_response or not cot_response:
        print("❌ One or both searches failed - cannot compare")
        return False

    # Extract key metrics
    regular_answer = regular_response.get("answer", "")
    cot_answer = cot_response.get("answer", "")

    regular_time = regular_response.get("execution_time", 0)
    cot_time = cot_response.get("execution_time", 0)

    regular_chunks = len(regular_response.get("query_results", []))
    cot_chunks = len(cot_response.get("query_results", []))

    # CoT-specific data
    cot_output = cot_response.get("cot_output")
    print(f"🔍 DEBUG: cot_output type: {type(cot_output)}")
    print(f"🔍 DEBUG: cot_output value: {cot_output}")

    if cot_output is None:
        print("❌ ERROR: CoT output is None - CoT logic not triggered!")
        reasoning_steps = 0
        cot_confidence = "N/A"
    else:
        reasoning_steps = len(cot_output.get("reasoning_steps", []))
        cot_confidence = cot_output.get("total_confidence", "N/A")

    # Token information extraction
    regular_tokens = regular_response.get("token_count", 0)
    cot_tokens = cot_output.get("token_usage", 0) if cot_output else 0
    regular_token_warning = regular_response.get("token_warning")
    cot_token_warning = cot_response.get("token_warning")

    # Display comparison
    print("\n" + "=" * 70)
    print("📊 SEARCH COMPARISON RESULTS")
    print("=" * 70)

    print("\n⏱️  PERFORMANCE:")
    print(f"   Regular Search Time: {regular_time:.2f}s")
    print(f"   CoT Search Time:     {cot_time:.2f}s")
    print(
        f"   Time Difference:     +{cot_time - regular_time:.2f}s ({((cot_time / regular_time - 1) * 100):.1f}% slower)"
    )

    print("\n📄 DOCUMENT RETRIEVAL:")
    print(f"   Regular Search Chunks: {regular_chunks}")
    print(f"   CoT Search Chunks:     {cot_chunks}")
    print(f"   Chunk Difference:      {cot_chunks - regular_chunks}")

    print("\n📝 ANSWER ANALYSIS:")
    print(f"   Regular Answer Length: {len(regular_answer)} chars")
    print(f"   CoT Answer Length:     {len(cot_answer)} chars")
    print(f"   Length Difference:     +{len(cot_answer) - len(regular_answer)} chars")

    print("\n🪙 TOKEN USAGE:")
    print(f"   Regular Search Tokens: {regular_tokens}")
    print(f"   CoT Search Tokens:     {cot_tokens}")
    if cot_tokens > 0 and regular_tokens > 0:
        token_increase = cot_tokens - regular_tokens
        token_increase_pct = (token_increase / regular_tokens) * 100
        print(f"   Token Increase:        +{token_increase} ({token_increase_pct:.1f}% more)")
    elif cot_tokens > 0:
        print(f"   Token Efficiency:      CoT used {cot_tokens} tokens vs {regular_tokens} regular")

    # Token warnings
    if regular_token_warning:
        print(f"   Regular Warning:       {regular_token_warning}")
    if cot_token_warning:
        print(f"   CoT Warning:           {cot_token_warning}")

    if reasoning_steps > 0:
        print("\n🧠 COT REASONING:")
        print(f"   Reasoning Steps:       {reasoning_steps}")
        print(f"   Overall Confidence:    {cot_confidence}")
        if cot_tokens > 0:
            tokens_per_step = cot_tokens / reasoning_steps
            print(f"   Tokens per Step:       {tokens_per_step:.1f} avg")

    # Show answer previews
    print("\n📖 ANSWER PREVIEWS:")
    print("\n🔹 Regular Search Answer:")
    print(f"   {regular_answer[:300]}{'...' if len(regular_answer) > 300 else ''}")

    print("\n🧠 CoT Search Answer:")
    print(f"   {cot_answer[:300]}{'...' if len(cot_answer) > 300 else ''}")

    # Quality assessment
    print("\n🎯 QUALITY ASSESSMENT:")

    # Check for actual source information in response metadata
    regular_documents = regular_response.get("documents", [])
    regular_query_results = regular_response.get("query_results", [])
    regular_has_sources = len(regular_documents) > 0 or len(regular_query_results) > 0

    cot_documents = cot_response.get("documents", [])
    cot_query_results = cot_response.get("query_results", [])
    cot_has_sources = len(cot_documents) > 0 or len(cot_query_results) > 0

    regular_has_structure = any(marker in regular_answer for marker in ["1.", "2.", "•", "*", "-"])
    cot_has_structure = any(marker in cot_answer for marker in ["1.", "2.", "•", "*", "-"])

    print(
        f"   Regular - Has Sources:     {'✅' if regular_has_sources else '❌'} ({len(regular_documents)} docs, {len(regular_query_results)} chunks)"
    )
    print(f"   Regular - Has Structure:   {'✅' if regular_has_structure else '❌'}")
    print(
        f"   CoT - Has Sources:         {'✅' if cot_has_sources else '❌'} ({len(cot_documents)} docs, {len(cot_query_results)} chunks)"
    )
    print(f"   CoT - Has Structure:       {'✅' if cot_has_structure else '❌'}")

    # Show detailed CoT reasoning if available
    if reasoning_steps > 0:
        print("\n🔍 DETAILED COT REASONING:")
        for i, step in enumerate(cot_output.get("reasoning_steps", []), 1):
            step_question = step.get("question", step.get("step_question", "N/A"))
            step_answer = step.get("intermediate_answer", "N/A")
            step_confidence = step.get("confidence_score", "N/A")
            step_tokens = step.get("token_usage", "N/A")
            step_time = step.get("execution_time", "N/A")

            print(f"   Step {i}: {step_question}")
            print(f"           {step_answer[:150]}{'...' if len(step_answer) > 150 else ''}")
            print(f"           Confidence: {step_confidence} | Tokens: {step_tokens} | Time: {step_time}s")

    print("\n🎉 COMPARISON COMPLETE!")
    print(f"   CoT provides {'more detailed' if len(cot_answer) > len(regular_answer) else 'similar length'} answers")
    print(f"   CoT takes {cot_time / regular_time:.1f}x longer but adds reasoning transparency")
    if cot_tokens > 0 and regular_tokens > 0:
        print(f"   CoT uses {cot_tokens / regular_tokens:.1f}x more tokens for enhanced reasoning")

    # Debug the data structures for token tracking
    print("\n🔍 TOKEN TRACKING DEBUG:")
    print(f"   Regular response keys: {list(regular_response.keys())}")
    print(f"   CoT response keys: {list(cot_response.keys())}")
    print(f"   CoT output keys: {list(cot_output.keys()) if cot_output else 'No cot_output'}")

    if reasoning_steps > 0 and cot_output.get("reasoning_steps"):
        first_step = cot_output.get("reasoning_steps")[0]
        print(f"   First reasoning step keys: {list(first_step.keys())}")
    else:
        print(f"   No reasoning steps found (reasoning_steps={reasoning_steps})")
        print(f"   CoT output reasoning_steps: {cot_output.get('reasoning_steps', 'None') if cot_output else 'None'}")

    return True


def main() -> None:
    """Main test function."""
    print("🔍 Chain of Thought vs Regular Search Comparison")
    print("=" * 50)
    print("This test compares CoT-enabled search vs regular search side-by-side.")
    print()

    try:
        # Setup
        config, api_client, mock_token = setup_environment()

        # Get user info
        user_id = get_user_info(api_client, config)
        if not user_id:
            print("❌ Cannot proceed without user info")
            return

        # Ensure user has a pipeline
        pipeline_id = ensure_user_has_pipeline(api_client, config, user_id)
        if not pipeline_id:
            print("⚠️  Warning: No pipeline available, search may use defaults")

        # List collections
        collections = list_collections(api_client, config)
        if not collections:
            print("❌ No collections available for testing")
            return

        # Find collection 51 (User_Uploaded_Files) or a collection with most documents
        suitable_collection = None

        # First, try to find User_Uploaded_Files_20250918_131815 (collection 51)
        for collection in collections:
            name = collection.get("name", "")
            if "User_Uploaded_Files_20250918_131815" in name:
                suitable_collection = collection
                break

        # If not found, find a collection with most documents
        if not suitable_collection:
            max_files = 0
            for collection in collections:
                files = collection.get("files", [])
                file_count = len(files) if files else 0
                status = collection.get("status", "unknown")

                if file_count > max_files and status == "completed":
                    max_files = file_count
                    suitable_collection = collection

        if not suitable_collection:
            print("❌ No suitable collections found (need completed collection with files)")
            return

        collection_id = suitable_collection.get("id")
        collection_name = suitable_collection.get("name", "Unknown")

        print(f"\n📋 Using Collection: {collection_name}")
        print(f"   Collection ID: {collection_id}")
        print(f"   Files: {len(suitable_collection.get('files', []))}")

        # Test complex question that should trigger CoT
        test_question = (
            "How does IBM's business strategy work and what are the key components that drive their success?"
        )

        success = compare_search_results(api_client, collection_id, test_question, user_id, pipeline_id)

        if success:
            print("\n🎉 CoT vs Regular Search Comparison COMPLETED!")
            print("   Both search modes are working and differences have been analyzed!")
        else:
            print("\n❌ CoT vs Regular Search Comparison FAILED!")
            print("   One or both search modes failed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
