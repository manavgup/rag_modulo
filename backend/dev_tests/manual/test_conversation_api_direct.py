#!/usr/bin/env python3
"""Direct API test for conversation endpoints.

This script tests the conversation API endpoints directly without CLI dependencies.
"""

from uuid import uuid4

import requests


def test_conversation_api():
    """Test the conversation API endpoints directly."""
    base_url = "http://localhost:8000"

    print("🧪 Testing Conversation API Endpoints")
    print("=" * 50)

    # Test data
    user_id = str(uuid4())
    collection_id = "db523922-4ea2-414e-bfb8-ab937eae02a7"  # From the CLI test output

    print(f"User ID: {user_id}")
    print(f"Collection ID: {collection_id}")

    # Test 1: Create session
    print("\n1️⃣ Testing session creation...")
    session_data = {
        "user_id": user_id,
        "collection_id": collection_id,
        "session_name": "API Test Conversation",
        "context_window_size": 4000,
        "max_messages": 50,
        "is_archived": False,
        "is_pinned": False,
    }

    try:
        response = requests.post(f"{base_url}/api/chat/sessions", json=session_data)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            session = response.json()
            session_id = session["id"]
            print(f"   ✅ Session created: {session_id}")
            print(f"   Session Name: {session.get('session_name')}")
        else:
            print(f"   ❌ Failed to create session: {response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error creating session: {e}")
        return False

    # Test 2: Send a message
    print("\n2️⃣ Testing message processing...")
    message_data = {
        "session_id": session_id,
        "content": "What is machine learning?",
        "role": "user",
        "message_type": "question",
    }

    try:
        response = requests.post(f"{base_url}/api/chat/sessions/{session_id}/process", json=message_data)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            message = response.json()
            print("   ✅ Message processed")
            print(f"   Response: {message.get('content', '')[:100]}...")

            # Check integration metadata
            metadata = message.get("metadata", {})
            print("   🔗 Integration Status:")
            print(f"      Conversation UI Used: {metadata.get('conversation_ui_used', 'N/A')}")
            print(f"      Search RAG Used: {metadata.get('search_rag_used', 'N/A')}")
            print(f"      CoT Reasoning Used: {metadata.get('cot_reasoning_used', 'N/A')}")
            print(f"      Context Enhanced: {metadata.get('conversation_context_used', 'N/A')}")
            print(f"      Seamless Integration: {metadata.get('integration_seamless', 'N/A')}")
        else:
            print(f"   ❌ Failed to process message: {response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error processing message: {e}")
        return False

    # Test 3: Get session statistics
    print("\n3️⃣ Testing session statistics...")
    try:
        response = requests.get(f"{base_url}/api/chat/sessions/{session_id}/statistics?user_id={user_id}")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            stats = response.json()
            print("   ✅ Statistics retrieved")
            print(f"   Messages: {stats.get('message_count', 0)}")
            print(f"   User Messages: {stats.get('user_messages', 0)}")
            print(f"   Assistant Messages: {stats.get('assistant_messages', 0)}")
        else:
            print(f"   ❌ Failed to get statistics: {response.text}")

    except Exception as e:
        print(f"   ❌ Error getting statistics: {e}")

    # Test 4: Get messages
    print("\n4️⃣ Testing message retrieval...")
    try:
        response = requests.get(f"{base_url}/api/chat/sessions/{session_id}/messages?user_id={user_id}")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            messages = response.json()
            print(f"   ✅ Retrieved {len(messages)} messages")
        else:
            print(f"   ❌ Failed to get messages: {response.text}")

    except Exception as e:
        print(f"   ❌ Error getting messages: {e}")

    # Test 5: Test question suggestions
    print("\n5️⃣ Testing question suggestions...")
    try:
        response = requests.get(
            f"{base_url}/api/chat/sessions/{session_id}/suggestions?"
            f"user_id={user_id}&current_message=What else can you tell me?&max_suggestions=3"
        )
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            suggestions = response.json()
            print(f"   ✅ Generated {len(suggestions.get('suggestions', []))} suggestions")
            for i, suggestion in enumerate(suggestions.get("suggestions", []), 1):
                print(f"      {i}. {suggestion}")
        else:
            print(f"   ❌ Failed to get suggestions: {response.text}")

    except Exception as e:
        print(f"   ❌ Error getting suggestions: {e}")

    # Test 6: Export session
    print("\n6️⃣ Testing session export...")
    try:
        response = requests.get(f"{base_url}/api/chat/sessions/{session_id}/export?user_id={user_id}&format=json")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            export_data = response.json()
            print("   ✅ Export successful")
            print(f"   Session: {export_data.get('session_data', {}).get('session_name', 'N/A')}")
            print(f"   Messages: {len(export_data.get('messages', []))}")
        else:
            print(f"   ❌ Failed to export: {response.text}")

    except Exception as e:
        print(f"   ❌ Error exporting: {e}")

    # Test 7: Delete session
    print("\n7️⃣ Testing session deletion...")
    try:
        response = requests.delete(f"{base_url}/api/chat/sessions/{session_id}?user_id={user_id}")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Session deleted: {result.get('message')}")
        else:
            print(f"   ❌ Failed to delete session: {response.text}")

    except Exception as e:
        print(f"   ❌ Error deleting session: {e}")

    print("\n🎉 API Test Complete!")
    return True


if __name__ == "__main__":
    test_conversation_api()
