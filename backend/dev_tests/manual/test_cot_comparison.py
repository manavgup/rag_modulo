#!/usr/bin/env python3
"""Compare Chain of Thought vs Regular Search side-by-side."""

import json
import os
import sys
from typing import Any

# Add the backend directory to sys.path to enable imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, backend_dir)

from rag_solution.cli.client import RAGAPIClient  # noqa: E402
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


def run_search(api_client: Any, question: str, collection_id: str, user_id: str, enable_cot: bool = False) -> dict:
    """Run a search with or without CoT."""

    # Get proper user_id from /api/auth/me
    try:
        current_user = api_client.get("/api/auth/me")
        api_user_id = current_user.get("uuid") or current_user.get("id")
    except Exception as e:
        print(f"   ❌ Failed to get user from /api/auth/me: {e}")
        api_user_id = user_id  # Fallback

    if enable_cot:
        # Enable CoT explicitly
        config_metadata = {
            "cot_enabled": True,
            "show_cot_steps": True,
            "cot_config": {
                "max_reasoning_depth": 3,
                "reasoning_strategy": "decomposition",
                "token_budget_multiplier": 1.5,
            },
        }
        mode_name = "WITH CoT"
    else:
        # Disable CoT explicitly
        config_metadata = {"cot_disabled": True}
        mode_name = "WITHOUT CoT (Regular Search)"

    search_payload = {
        "question": question,
        "collection_id": collection_id,
        "user_id": api_user_id,
        "config_metadata": config_metadata,
    }

    print(f"\n🔍 Testing Search {mode_name}")
    print("=" * 60)
    print("Request payload:")
    print(json.dumps(search_payload, indent=2))

    try:
        response = api_client.post("/api/search", data=search_payload)

        if response and "answer" in response:
            print(f"\n✅ Search {mode_name} successful!")
            print(f"Answer: {response['answer']}")
            print(f"Execution time: {response.get('execution_time', 'N/A')}s")

            # Check for document sources
            query_results = response.get("query_results", [])
            print(f"Query results: {len(query_results)} chunks")

            documents = response.get("documents", [])
            print(f"Documents: {len(documents)} document metadata entries")

            # Check for CoT output
            if enable_cot and "cot_output" in response:
                cot_output = response["cot_output"]
                print("\n🧠 Chain of Thought Details:")
                print(f"   Reasoning steps: {len(cot_output.get('reasoning_steps', []))}")
                print(f"   Strategy: {cot_output.get('reasoning_strategy', 'N/A')}")
                print(f"   Total confidence: {cot_output.get('total_confidence', 'N/A')}")

                if cot_output.get("reasoning_steps"):
                    print("   Step details:")
                    for i, step in enumerate(cot_output["reasoning_steps"], 1):
                        print(f"     Step {i}: {step.get('step_question', 'N/A')}")
                        print(f"       Answer: {step.get('intermediate_answer', 'N/A')[:100]}...")
                        print(f"       Confidence: {step.get('confidence_score', 'N/A')}")

            return response
        else:
            print(f"\n❌ Search {mode_name} failed: {response}")
            return {}

    except Exception as e:
        print(f"\n❌ Search {mode_name} failed with error: {e}")
        return {}


def compare_answers(regular_response: dict, cot_response: dict):
    """Compare the two responses side by side."""
    print("\n" + "=" * 80)
    print("📊 SIDE-BY-SIDE COMPARISON")
    print("=" * 80)

    print("\n🔵 REGULAR SEARCH (No CoT):")
    print("-" * 40)
    regular_answer = regular_response.get("answer", "No answer")
    print(f"Answer: {regular_answer}")
    print(f"Length: {len(regular_answer)} characters")
    print(f"Execution time: {regular_response.get('execution_time', 'N/A')}s")

    print("\n🧠 CHAIN OF THOUGHT SEARCH:")
    print("-" * 40)
    cot_answer = cot_response.get("answer", "No answer")
    print(f"Answer: {cot_answer}")
    print(f"Length: {len(cot_answer)} characters")
    print(f"Execution time: {cot_response.get('execution_time', 'N/A')}s")

    # Compare document retrieval
    regular_chunks = len(regular_response.get("query_results", []))
    cot_chunks = len(cot_response.get("query_results", []))

    print("\n📚 DOCUMENT RETRIEVAL:")
    print(f"Regular search: {regular_chunks} chunks")
    print(f"CoT search: {cot_chunks} chunks")

    # Quality assessment
    print("\n🎯 QUALITY ASSESSMENT:")
    print(
        f"Regular answer quality: {'Good' if len(regular_answer) > 100 and 'Based on the analysis' not in regular_answer else 'Poor'}"
    )
    print(
        f"CoT answer quality: {'Good' if len(cot_answer) > 100 and 'Based on the analysis' not in cot_answer else 'Poor'}"
    )

    if "Based on the analysis" in cot_answer and "Based on the analysis" not in regular_answer:
        print("⚠️  CoT is adding redundant wrapper text that makes the answer worse!")
    elif len(cot_answer) > len(regular_answer) * 1.5:
        print("⚠️  CoT answer is significantly longer - check if it's adding value or just verbosity")


def main() -> None:
    """Main comparison test."""
    print("📊 Chain of Thought vs Regular Search Comparison")
    print("=" * 60)
    print("This test compares the same search with and without CoT enabled.")
    print()

    try:
        # Setup
        config, api_client, _mock_token = setup_environment()

        # Get user info
        users_cmd = UserCommands(api_client, config)
        user_result = users_cmd.get_current_user()

        if user_result.success:
            user_data = user_result.data
            if user_data:
                user_id = user_data.get("id", "N/A")
                print(f"✅ User ID: {user_id}")
            else:
                print("❌ No user data")
                return
        else:
            print(f"❌ Failed to get user info: {user_result.message}")
            return

        # Use the same collection and question as previous tests
        collection_id = "e641b71c-fb41-4e3b-9ff3-e2be6ea88b73"
        test_question = (
            "How does IBM's business strategy work and what are the key components that drive their success?"
        )

        print("\n📋 Test Parameters:")
        print(f"   Collection ID: {collection_id}")
        print(f"   Question: {test_question}")

        # Run both searches
        print("\n🚀 Running comparison tests...")

        # Test 1: Regular search (CoT disabled)
        regular_response = run_search(api_client, test_question, collection_id, user_id, enable_cot=False)

        # Test 2: CoT search (CoT enabled)
        cot_response = run_search(api_client, test_question, collection_id, user_id, enable_cot=True)

        # Compare results
        if regular_response and cot_response:
            compare_answers(regular_response, cot_response)
        else:
            print("❌ Could not complete comparison - one or both searches failed")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
