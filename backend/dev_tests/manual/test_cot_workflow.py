#!/usr/bin/env python3
"""Chain of Thought test script based on existing test_workflow.py.

This script extends the existing workflow to test Chain of Thought integration:
1. Uses existing collections or creates new ones
2. Performs searches with CoT enabled via config_metadata
3. Shows evidence of CoT working vs regular search
4. Compares results between CoT and regular search
"""

import json
import os
import sys
from typing import Any

# Add the backend directory to sys.path to enable imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, backend_dir)

from rag_solution.cli.client import RAGAPIClient  # noqa: E402
from rag_solution.cli.commands.collections import CollectionCommands  # noqa: E402

# from rag_solution.cli.commands.search import SearchCommands  # Not used - direct API calls instead
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
            print(f"   User ID: {user_data.get('id', 'N/A')}")
            print(f"   Name: {user_data.get('name', 'N/A')}")
            print(f"   Email: {user_data.get('email', 'N/A')}")
            return user_data.get("id")
        else:
            print("❌ No user data returned")
            return None
    else:
        print(f"❌ Failed to get user info: {user_result.message}")
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


def select_collection(collections: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Let user select a collection."""
    if not collections:
        print("❌ No collections available for testing")
        return None

    while True:
        try:
            choice = int(input(f"\nSelect collection (1-{len(collections)}): "))
            if 1 <= choice <= len(collections):
                return collections[choice - 1]
            print(f"Please enter a number between 1 and {len(collections)}")
        except ValueError:
            print("Please enter a valid number")


def test_search_comparison(api_client: Any, config: Any, collection_id: str, question: str) -> None:
    """Test both regular search and CoT search for comparison."""
    # search_cmd = SearchCommands(api_client, config)  # Unused, direct API calls used instead

    print(f"\n🔍 Testing Search: '{question}'")
    print("=" * 60)

    # Test 1: Regular Search (no CoT)
    print("\n1️⃣ REGULAR SEARCH (No Chain of Thought)")
    print("-" * 40)

    # Use direct API call to have full control over config_metadata
    regular_payload = {
        "question": question,
        "collection_id": collection_id,
        "config_metadata": {}  # No CoT enabled
    }

    print("Request payload:")
    print(json.dumps(regular_payload, indent=2))

    regular_response = api_client.post("/api/search", data=regular_payload)

    if regular_response and "answer" in regular_response:
        print("✅ Regular search successful!")
        print(f"Answer: {regular_response['answer'][:200]}...")
        print(f"Execution time: {regular_response.get('execution_time', 'N/A')}s")
        print(f"Sources: {len(regular_response.get('query_results', []))} chunks")
        regular_execution_time = regular_response.get("execution_time", 0)
    else:
        print("❌ Regular search failed")
        print(f"Response: {regular_response}")
        regular_execution_time = 0

    # Test 2: Chain of Thought Search
    print("\n2️⃣ CHAIN OF THOUGHT SEARCH")
    print("-" * 40)

    cot_payload = {
        "question": question,
        "collection_id": collection_id,
        "config_metadata": {
            "cot_enabled": True,
            "cot_config": {
                "max_reasoning_depth": 3,
                "reasoning_strategy": "decomposition",
                "token_budget_multiplier": 1.5
            }
        }
    }

    print("Request payload:")
    print(json.dumps(cot_payload, indent=2))

    cot_response = api_client.post("/api/search", data=cot_payload)

    if cot_response and "answer" in cot_response:
        print("✅ Chain of Thought search successful!")
        print(f"Answer: {cot_response['answer'][:200]}...")
        print(f"Execution time: {cot_response.get('execution_time', 'N/A')}s")
        print(f"Sources: {len(cot_response.get('query_results', []))} chunks")
        cot_execution_time = cot_response.get("execution_time", 0)

        # Check for CoT-specific fields
        if "cot_output" in cot_response:
            cot_output = cot_response["cot_output"]
            print("🧠 Chain of Thought Evidence:")
            print(f"   Reasoning steps: {len(cot_output.get('reasoning_steps', []))}")
            print(f"   Original question: {cot_output.get('original_question', 'N/A')}")
            print(f"   Final answer: {cot_output.get('final_answer', 'N/A')[:100]}...")
            if cot_output.get("reasoning_steps"):
                print("   Step details:")
                for i, step in enumerate(cot_output["reasoning_steps"], 1):
                    print(f"     Step {i}: {step.get('step_question', 'N/A')}")
        else:
            print("⚠️  No CoT output detected (may have fallen back to regular search)")
    else:
        print("❌ Chain of Thought search failed")
        print(f"Response: {cot_response}")
        cot_execution_time = 0

    # Test 3: Comparison
    print("\n3️⃣ COMPARISON & EVIDENCE")
    print("-" * 40)

    print("🔍 Evidence of Chain of Thought Integration:")
    print(f"   ✅ Regular search completed: {'Yes' if regular_response else 'No'}")
    print(f"   ✅ CoT search completed: {'Yes' if cot_response else 'No'}")
    print(f"   ✅ Different execution times: Regular={regular_execution_time:.3f}s, CoT={cot_execution_time:.3f}s")

    if cot_response and "cot_output" in cot_response:
        print("   ✅ CoT-specific output fields present")
        print("   ✅ Chain of Thought reasoning steps detected")
        print("   🎉 CHAIN OF THOUGHT IS WORKING!")
    else:
        print("   ⚠️  CoT output not detected - may have fallen back to regular search")
        print("   💡 This could be due to:")
        print("      - ChainOfThoughtService not fully implemented")
        print("      - CoT service falling back to regular search")
        print("      - Error in CoT execution (check logs)")


def main() -> None:
    """Main test function."""
    print("🧠 Chain of Thought Integration Test")
    print("=" * 50)
    print("This test compares regular search vs CoT search to verify integration.")
    print()

    try:
        # Setup
        config, api_client, mock_token = setup_environment()

        # Get user info
        user_id = get_user_info(api_client, config)
        if not user_id:
            print("❌ Cannot proceed without user info")
            return

        # List collections
        collections = list_collections(api_client, config)
        if not collections:
            print("❌ No collections available for testing")
            print("💡 Please run the main test_workflow.py first to create collections")
            return

        # Select collection
        selected_collection = select_collection(collections)
        if not selected_collection:
            return

        collection_id = selected_collection.get("id")
        collection_name = selected_collection.get("name", "Unknown")

        print(f"\n📋 Selected Collection: {collection_name}")
        print(f"   Collection ID: {collection_id}")

        # Test questions (complex ones more likely to trigger CoT)
        test_questions = [
            "What is machine learning and how does it work?",
            "How do neural networks learn from data and what are the key components?",
            "What are the differences between supervised and unsupervised learning algorithms?",
            "How does deep learning differ from traditional machine learning approaches?"
        ]

        print("\n🤔 Available test questions:")
        for i, q in enumerate(test_questions, 1):
            print(f"   {i}. {q}")

        while True:
            try:
                choice = int(input(f"\nSelect question (1-{len(test_questions)}) or 0 for custom: "))
                if choice == 0:
                    question = input("Enter your question: ").strip()
                    if question:
                        break
                elif 1 <= choice <= len(test_questions):
                    question = test_questions[choice - 1]
                    break
                print(f"Please enter 0-{len(test_questions)}")
            except ValueError:
                print("Please enter a valid number")

        # Run the comparison test
        test_search_comparison(api_client, config, collection_id, question)

        print("\n🎉 Chain of Thought Integration Test Complete!")
        print("\n💡 What to look for:")
        print("   • Different execution times between regular and CoT search")
        print("   • 'cot_output' field in CoT search response")
        print("   • 'reasoning_steps' array in CoT output")
        print("   • Logs showing 'Using Chain of Thought for enhanced reasoning'")
        print("   • If CoT fails, automatic fallback to regular search")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

