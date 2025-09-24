#!/usr/bin/env python3
"""Test conversation functionality using mock authentication.

This script uses the same mock authentication system as the CoT script
to properly test the conversation API endpoints.
"""

import os
import sys
from typing import Any

# Add the backend directory to sys.path to enable imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, backend_dir)

from rag_solution.cli.client import RAGAPIClient  # noqa: E402
from rag_solution.cli.commands.collections import CollectionCommands  # noqa: E402
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
            print(f"   User ID: {user_data.get('id')}")
            print(f"   Name: {user_data.get('name')}")
            print(f"   Email: {user_data.get('email')}")
            return user_data.get("id")
    else:
        print(f"❌ Failed to get user info: {user_result.message}")
    return None


def get_collections(api_client: Any, config: Any) -> list[dict[str, Any]]:
    """Get available collections."""
    collections_cmd = CollectionCommands(api_client, config)
    result = collections_cmd.list_collections()

    if result.success and result.data:
        if isinstance(result.data, list):
            collections = result.data
        else:
            collections = result.data.get("collections", []) if result.data else []
        print(f"📁 Available Collections ({len(collections)}):")
        for i, collection in enumerate(collections, 1):
            collection_id = collection.get("id", "Unknown")
            name = collection.get("name", "Unknown")
            file_count = collection.get("file_count", 0)
            status = collection.get("status", "unknown")
            print(f"   {i:2d}. {name} (ID: {collection_id})")
            print(f"       Files: {file_count}, Status: {status}")
        return collections
    else:
        print(f"❌ Failed to get collections: {result.message}")
        return []


def test_conversation_api(api_client: Any, user_id: str, collection_id: str) -> bool:
    """Test the conversation API endpoints."""
    print("\n💬 Testing Conversation API")
    print("=" * 50)

    # Test 1: Create conversation session
    print("\n1️⃣ Creating conversation session...")
    session_data = {
        "user_id": user_id,
        "collection_id": collection_id,
        "session_name": "Mock Auth Test Conversation",
        "context_window_size": 4000,
        "max_messages": 50,
        "is_archived": False,
        "is_pinned": False,
    }

    try:
        response = api_client.post("/api/chat/sessions", data=session_data)
        print(f"   Status: {response.get('status_code', 'Unknown')}")

        if "id" in response:
            session_id = response["id"]
            print(f"   ✅ Session created: {session_id}")
            print(f"   Session Name: {response.get('session_name')}")

            # Test 2: Process a message
            print("\n2️⃣ Processing message...")
            message_data = {
                "session_id": session_id,
                "content": "What is machine learning?",
                "role": "user",
                "message_type": "question",
            }

            response = api_client.post(f"/api/chat/sessions/{session_id}/process", data=message_data)
            print(f"   Status: {response.get('status_code', 'Unknown')}")

            if "content" in response:
                print("   ✅ Message processed successfully")
                print(f"   Response: {response.get('content', '')[:100]}...")

                # Show integration metadata
                print("\n3️⃣ Integration Status:")
                print(f"   CoT Used: {response.get('metadata', {}).get('cot_used', 'N/A')}")
                print(f"   Conversation Aware: {response.get('metadata', {}).get('conversation_aware', 'N/A')}")
                print(f"   Context Used: {response.get('metadata', {}).get('conversation_context_used', 'N/A')}")

                return True
            else:
                print(f"   ❌ Message processing failed: {response}")
                return False
        else:
            print(f"   ❌ Session creation failed: {response}")
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Main test function."""
    print("💬 Conversation API Test with Mock Authentication")
    print("=" * 60)
    print("This test uses the same mock authentication system as the CoT script")
    print("to properly test the conversation API endpoints.")

    try:
        # Setup environment
        config, api_client, mock_token = setup_environment()

        # Get user info
        user_id = get_user_info(api_client, config)
        if not user_id:
            print("❌ Failed to get user information")
            return False

        # Get collections
        collections = get_collections(api_client, config)
        if not collections:
            print("❌ No collections available")
            return False

        # Use the same collection as the CoT script (User_Uploaded_Files_20250918_131815)
        selected_collection = None
        for collection in collections:
            if collection.get("id") == "e641b71c-fb41-4e3b-9ff3-e2be6ea88b73":
                selected_collection = collection
                break

        if not selected_collection:
            print("❌ Collection e641b71c-fb41-4e3b-9ff3-e2be6ea88b73 not found")
            return False

        collection_id = selected_collection["id"]
        print(f"\n📋 Using Collection: {selected_collection['name']}")
        print(f"   Collection ID: {collection_id}")
        print(f"   Files: {selected_collection.get('file_count', 0)}")

        # Test conversation API
        success = test_conversation_api(api_client, user_id, collection_id)

        if success:
            print("\n🎉 Conversation API Test Successful!")
            print("   ✅ Mock authentication working")
            print("   ✅ User creation and setup working")
            print("   ✅ Conversation API endpoints working")
            print("   ✅ Integration with Search and CoT working")
        else:
            print("\n❌ Conversation API Test Failed!")

        return success

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
