#!/usr/bin/env python3
"""Test conversation functionality using direct API calls like the CLI does.

This script calls the same API endpoints that the CLI uses, without the CLI infrastructure.
"""

import requests


def test_direct_api_calls():
    """Test conversation functionality using direct API calls."""
    base_url = "http://localhost:8000"

    print("💬 Direct API Test for Conversation")
    print("=" * 50)
    print("Using the same API endpoints that the CLI uses")

    # Test 1: Check if server is running
    print("\n1️⃣ Checking server health...")
    try:
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            print("   ✅ Server is running")
        else:
            print(f"   ❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Server not accessible: {e}")
        return False

    # Test 2: Get current user (like CLI does)
    print("\n2️⃣ Getting current user...")
    try:
        # Use mock token like the CLI does
        headers = {"Authorization": "Bearer dev-0000-0000-0000"}
        response = requests.get(f"{base_url}/api/auth/me", headers=headers)

        if response.status_code == 200:
            user_data = response.json()
            print(f"   ✅ User authenticated: {user_data.get('name')} ({user_data.get('email')})")
            user_id = user_data.get("uuid") or user_data.get("id")
            print(f"   User ID: {user_id}")
        else:
            print(f"   ❌ Authentication failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error getting user: {e}")
        return False

    # Test 3: List collections (like CLI does)
    print("\n3️⃣ Listing collections...")
    try:
        response = requests.get(f"{base_url}/api/collections", headers=headers)

        if response.status_code == 200:
            collections_data = response.json()
            collections = (
                collections_data if isinstance(collections_data, list) else collections_data.get("collections", [])
            )
            print(f"   ✅ Found {len(collections)} collections")

            # Find a collection with files
            selected_collection = None
            for collection in collections:
                if collection.get("file_count", 0) > 0 and collection.get("status") == "completed":
                    selected_collection = collection
                    break

            if not selected_collection:
                # Use the same collection as CoT script
                for collection in collections:
                    if collection.get("id") == "e641b71c-fb41-4e3b-9ff3-e2be6ea88b73":
                        selected_collection = collection
                        break

            if selected_collection:
                collection_id = selected_collection["id"]
                print(f"   📋 Using collection: {selected_collection.get('name')} (ID: {collection_id})")
                print(f"   Files: {selected_collection.get('file_count', 0)}")
            else:
                print("   ❌ No suitable collection found")
                return False
        else:
            print(f"   ❌ Failed to list collections: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error listing collections: {e}")
        return False

    # Test 4: Test search API (like CoT script does)
    print("\n4️⃣ Testing search API...")
    try:
        search_data = {
            "question": "What is machine learning?",
            "collection_id": collection_id,
            "user_id": user_id,
            "config_metadata": {},
        }

        response = requests.post(f"{base_url}/api/search", json=search_data, headers=headers)

        if response.status_code == 200:
            result = response.json()
            print("   ✅ Search successful")
            print(f"   Answer: {result.get('answer', '')[:100]}...")
            print(f"   Documents: {len(result.get('documents', []))}")
            print(f"   Execution Time: {result.get('execution_time', 0):.2f}s")
        else:
            print(f"   ❌ Search failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error in search: {e}")
        return False

    # Test 5: Test conversation API endpoints
    print("\n5️⃣ Testing conversation API...")
    try:
        # Create conversation session
        session_data = {
            "user_id": user_id,
            "collection_id": collection_id,
            "session_name": "Direct API Test",
            "context_window_size": 4000,
            "max_messages": 50,
            "is_archived": False,
            "is_pinned": False,
        }

        response = requests.post(f"{base_url}/api/chat/sessions", json=session_data, headers=headers)

        if response.status_code == 200:
            session = response.json()
            session_id = session["id"]
            print(f"   ✅ Session created: {session_id}")

            # Process a message
            message_data = {
                "session_id": session_id,
                "content": "What is machine learning?",
                "role": "user",
                "message_type": "question",
            }

            response = requests.post(
                f"{base_url}/api/chat/sessions/{session_id}/process", json=message_data, headers=headers
            )

            if response.status_code == 200:
                message = response.json()
                print("   ✅ Message processed successfully")
                print(f"   Response: {message.get('content', '')[:100]}...")

                # Show integration metadata
                metadata = message.get("metadata", {})
                print("   🔗 Integration Status:")
                print(f"      CoT Used: {metadata.get('cot_used', 'N/A')}")
                print(f"      Conversation Aware: {metadata.get('conversation_aware', 'N/A')}")
                print(f"      Context Used: {metadata.get('conversation_context_used', 'N/A')}")

                return True
            else:
                print(f"   ❌ Message processing failed: {response.status_code} - {response.text}")
                return False
        else:
            print(f"   ❌ Session creation failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error in conversation test: {e}")
        return False


def main():
    """Main test function."""
    print("🧪 Direct API Test for Conversation Feature")
    print("=" * 60)
    print("This test calls the same API endpoints that the CLI uses")
    print("to verify that the conversation feature works end-to-end.")

    success = test_direct_api_calls()

    if success:
        print("\n🎉 Direct API Test Successful!")
        print("   ✅ Server is running and accessible")
        print("   ✅ Authentication is working")
        print("   ✅ Collections API is working")
        print("   ✅ Search API is working")
        print("   ✅ Conversation API is working")
        print("   ✅ Integration between services is working")
    else:
        print("\n❌ Direct API Test Failed!")
        print("   One or more API endpoints are not working properly")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
