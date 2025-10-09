#!/usr/bin/env python3
"""Test regular search without CoT for comparison."""

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


def test_regular_search(api_client: Any, collection_id: str, question: str, user_id: str) -> bool:
    """Test regular search without CoT."""
    print("\n🔍 Testing Regular Search (No CoT)")
    print("=" * 50)
    print(f"Question: {question}")
    print(f"Collection: {collection_id}")

    # Get proper user_id from /api/auth/me just like the working CLI does
    try:
        current_user = api_client.get("/api/auth/me")
        api_user_id = current_user.get("uuid") or current_user.get("id")
        print(f"   API User ID: {api_user_id} (type: {type(api_user_id)})")
    except Exception as e:
        print(f"   ❌ Failed to get user from /api/auth/me: {e}")
        api_user_id = user_id  # Fallback to provided user_id

    # Regular search payload (no CoT)
    search_payload = {
        "question": question,
        "collection_id": collection_id,
        "user_id": api_user_id,
        "config_metadata": {},
    }

    print("\n📝 Request payload:")
    print(json.dumps(search_payload, indent=2))

    try:
        response = api_client.post("/api/search", data=search_payload)

        if response and "answer" in response:
            print("\n✅ Regular search successful!")
            print(f"Answer: {response['answer'][:500]}...")
            print(f"Execution time: {response.get('execution_time', 'N/A')}s")

            # Check for document sources
            query_results = response.get("query_results", [])
            print(f"Query results: {len(query_results)} chunks")

            documents = response.get("documents", [])
            print(f"Documents: {len(documents)} document metadata entries")

            print("\n🔍 First few document chunks:")
            for i, result in enumerate(query_results[:3]):
                chunk_text = result.get("chunk", {}).get("text", "No text")
                print(f"   Chunk {i + 1}: {chunk_text[:150]}...")

            return True
        else:
            print(f"\n❌ Regular search failed: {response}")
            return False

    except Exception as e:
        print(f"\n❌ Regular search failed with error: {e}")
        return False


def main() -> None:
    """Main test function."""
    print("🔍 Regular Search Test (for comparison with CoT)")
    print("=" * 50)

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

        # Use the same collection and question as CoT test
        collection_id = "e641b71c-fb41-4e3b-9ff3-e2be6ea88b73"
        test_question = (
            "How does IBM's business strategy work and what are the key components that drive their success?"
        )

        success = test_regular_search(api_client, collection_id, test_question, user_id)

        if success:
            print("\n🎉 Regular search test completed!")
        else:
            print("\n❌ Regular search test failed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
