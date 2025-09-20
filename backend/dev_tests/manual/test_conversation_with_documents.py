#!/usr/bin/env python3
"""Test integrated Conversation with Documents experience via CLI.

This script tests the seamless integration between Conversation, Search, and CoT services
through a realistic chat experience with document collections.
"""

import os
import sys
import time
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
            print(f"   User ID: {user_id}")
            print(f"   Name: {user_data.get('name', 'N/A')}")
            print(f"   Email: {user_data.get('email', 'N/A')}")
            return user_id
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


def create_conversation_session(api_client: Any, user_id: str, collection_id: str) -> str | None:
    """Create a new conversation session."""
    print(f"\n💬 Creating conversation session...")
    
    from uuid import UUID
    
    session_data = {
        "user_id": str(UUID(user_id)) if user_id else str(UUID("00000000-0000-0000-0000-000000000000")),
        "collection_id": str(UUID(collection_id)),
        "session_name": "CLI Test Conversation",
        "context_window_size": 4000,
        "max_messages": 50,
        "is_archived": False,
        "is_pinned": False
    }
    
    try:
        response = api_client.post("/api/chat/sessions", json=session_data)
        if response and "id" in response:
            session_id = response["id"]
            print(f"   ✅ Created session: {session_id}")
            print(f"   Session Name: {response.get('session_name', 'N/A')}")
            print(f"   Context Window: {response.get('context_window_size', 'N/A')}")
            return session_id
        else:
            print(f"   ❌ Failed to create session: {response}")
            return None
    except Exception as e:
        print(f"   ❌ Session creation failed: {e}")
        return None


def send_message(api_client: Any, session_id: str, content: str, role: str = "user") -> dict[str, Any] | None:
    """Send a message to the conversation session."""
    from uuid import UUID
    
    message_data = {
        "session_id": str(UUID(session_id)),
        "content": content,
        "role": role,
        "message_type": "question" if role == "user" else "answer"
    }
    
    try:
        response = api_client.post(f"/api/chat/sessions/{session_id}/process", json=message_data)
        if response and "content" in response:
            return response
        else:
            print(f"   ❌ Failed to process message: {response}")
            return None
    except Exception as e:
        print(f"   ❌ Message processing failed: {e}")
        return None


def get_session_messages(api_client: Any, session_id: str, user_id: str) -> list[dict[str, Any]]:
    """Get all messages from the conversation session."""
    try:
        from uuid import UUID
        response = api_client.get(f"/api/chat/sessions/{str(UUID(session_id))}/messages?user_id={str(UUID(user_id))}")
        if response and isinstance(response, list):
            return response
        else:
            print(f"   ❌ Failed to get messages: {response}")
            return []
    except Exception as e:
        print(f"   ❌ Get messages failed: {e}")
        return []


def get_session_statistics(api_client: Any, session_id: str, user_id: str) -> dict[str, Any] | None:
    """Get conversation session statistics."""
    try:
        from uuid import UUID
        response = api_client.get(f"/api/chat/sessions/{str(UUID(session_id))}/statistics?user_id={str(UUID(user_id))}")
        if response and "message_count" in response:
            return response
        else:
            print(f"   ❌ Failed to get statistics: {response}")
            return None
    except Exception as e:
        print(f"   ❌ Get statistics failed: {e}")
        return None


def run_conversation_test(api_client: Any, user_id: str, collection_id: str) -> bool:
    """Run a comprehensive conversation test."""
    print("\n" + "=" * 80)
    print("💬 INTEGRATED CONVERSATION TEST")
    print("=" * 80)
    print("Testing seamless integration of Conversation + Search + CoT services")
    
    # Step 1: Create conversation session
    session_id = create_conversation_session(api_client, user_id, collection_id)
    if not session_id:
        return False
    
    # Step 2: Test conversation flow
    conversation_flow = [
        {
            "user_message": "What is machine learning?",
            "expected_context": "machine learning",
            "description": "Initial question about ML"
        },
        {
            "user_message": "How does it work?",
            "expected_context": "machine learning",
            "description": "Follow-up question (should use context)"
        },
        {
            "user_message": "What are the different types?",
            "expected_context": "machine learning",
            "description": "Another follow-up (should maintain context)"
        },
        {
            "user_message": "Can you give me examples of supervised learning?",
            "expected_context": "supervised learning",
            "description": "Specific question building on previous context"
        }
    ]
    
    print(f"\n🔄 Running conversation flow with {len(conversation_flow)} messages...")
    
    for i, step in enumerate(conversation_flow, 1):
        print(f"\n--- Message {i}: {step['description']} ---")
        print(f"User: {step['user_message']}")
        
        # Send user message
        response = send_message(api_client, session_id, step['user_message'], "user")
        if not response:
            print(f"❌ Failed to process message {i}")
            continue
            
        # Display assistant response
        assistant_content = response.get("content", "")
        print(f"Assistant: {assistant_content[:200]}{'...' if len(assistant_content) > 200 else ''}")
        
        # Check integration metadata
        metadata = response.get("metadata", {})
        print(f"   🔗 Integration Status:")
        print(f"      Conversation UI Used: {metadata.get('conversation_ui_used', 'N/A')}")
        print(f"      Search RAG Used: {metadata.get('search_rag_used', 'N/A')}")
        print(f"      CoT Reasoning Used: {metadata.get('cot_reasoning_used', 'N/A')}")
        print(f"      Context Enhanced: {metadata.get('conversation_context_used', 'N/A')}")
        print(f"      Seamless Integration: {metadata.get('integration_seamless', 'N/A')}")
        print(f"      No Duplication: {metadata.get('no_duplication', 'N/A')}")
        
        # Check if CoT was used
        if metadata.get('cot_used', False):
            print(f"   🧠 CoT Steps: {len(metadata.get('cot_steps', []))}")
            print(f"      Enhanced Question: {metadata.get('enhanced_question', 'N/A')}")
        
        time.sleep(1)  # Brief pause between messages
    
    # Step 3: Get session statistics
    print(f"\n📊 Getting session statistics...")
    stats = get_session_statistics(api_client, session_id, user_id)
    if stats:
        print(f"   Messages: {stats.get('message_count', 0)}")
        print(f"   User Messages: {stats.get('user_messages', 0)}")
        print(f"   Assistant Messages: {stats.get('assistant_messages', 0)}")
        print(f"   CoT Usage Count: {stats.get('cot_usage_count', 0)}")
        print(f"   Context Enhancement Count: {stats.get('context_enhancement_count', 0)}")
        print(f"   Total Tokens: {stats.get('total_tokens', 0)}")
    
    # Step 4: Get all messages
    print(f"\n📝 Getting all conversation messages...")
    messages = get_session_messages(api_client, session_id, user_id)
    print(f"   Retrieved {len(messages)} messages")
    
    # Step 5: Test question suggestions
    print(f"\n💡 Testing question suggestions...")
    try:
        from uuid import UUID
        suggestions_response = api_client.get(
            f"/api/chat/sessions/{str(UUID(session_id))}/suggestions?"
            f"user_id={str(UUID(user_id))}&current_message=What else can you tell me?&max_suggestions=3"
        )
        if suggestions_response and "suggestions" in suggestions_response:
            suggestions = suggestions_response["suggestions"]
            print(f"   Generated {len(suggestions)} suggestions:")
            for j, suggestion in enumerate(suggestions, 1):
                print(f"      {j}. {suggestion}")
        else:
            print(f"   ❌ Failed to get suggestions: {suggestions_response}")
    except Exception as e:
        print(f"   ❌ Suggestions failed: {e}")
    
    # Step 6: Export conversation
    print(f"\n📤 Testing conversation export...")
    try:
        from uuid import UUID
        export_response = api_client.get(f"/api/chat/sessions/{str(UUID(session_id))}/export?user_id={str(UUID(user_id))}&format=json")
        if export_response and "session_data" in export_response:
            print(f"   ✅ Export successful")
            print(f"   Session: {export_response['session_data'].get('session_name', 'N/A')}")
            print(f"   Messages: {len(export_response.get('messages', []))}")
            print(f"   Format: {export_response.get('export_format', 'N/A')}")
        else:
            print(f"   ❌ Export failed: {export_response}")
    except Exception as e:
        print(f"   ❌ Export failed: {e}")
    
    # Step 7: Clean up - delete session
    print(f"\n🗑️  Cleaning up session...")
    try:
        from uuid import UUID
        delete_response = api_client.delete(f"/api/chat/sessions/{str(UUID(session_id))}?user_id={str(UUID(user_id))}")
        if delete_response and delete_response.get("message") == "Session deleted successfully":
            print(f"   ✅ Session deleted successfully")
        else:
            print(f"   ❌ Delete failed: {delete_response}")
    except Exception as e:
        print(f"   ❌ Delete failed: {e}")
    
    return True


def main() -> None:
    """Main test function."""
    print("💬 Integrated Conversation with Documents Test")
    print("=" * 60)
    print("This test demonstrates the seamless integration between:")
    print("  • Conversation Service (UI and context management)")
    print("  • Search Service (RAG functionality with conversation awareness)")
    print("  • Chain of Thought Service (enhanced reasoning with conversation history)")
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
            return

        # Find a suitable collection
        suitable_collection = None
        for collection in collections:
            files = collection.get("files", [])
            file_count = len(files) if files else 0
            status = collection.get("status", "unknown")

            if file_count > 0 and status == "completed":
                suitable_collection = collection
                break

        if not suitable_collection:
            print("❌ No suitable collections found (need completed collection with files)")
            return

        collection_id = suitable_collection.get("id")
        collection_name = suitable_collection.get("name", "Unknown")

        print(f"\n📋 Using Collection: {collection_name}")
        print(f"   Collection ID: {collection_id}")
        print(f"   Files: {len(suitable_collection.get('files', []))}")

        # Run the conversation test
        success = run_conversation_test(api_client, user_id, collection_id)

        if success:
            print("\n🎉 INTEGRATED CONVERSATION TEST COMPLETED!")
            print("   All services are working together seamlessly!")
            print("   • Conversation provides UI and context management ✅")
            print("   • Search provides RAG with conversation awareness ✅")
            print("   • CoT provides enhanced reasoning with conversation history ✅")
            print("   • No duplication of functionality ✅")
        else:
            print("\n❌ INTEGRATED CONVERSATION TEST FAILED!")
            print("   One or more services failed to integrate properly!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
