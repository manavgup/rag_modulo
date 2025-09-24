#!/usr/bin/env python3
"""Direct API test for search endpoints (like CoT script).

This script tests the existing search API endpoints directly to understand how they work.
"""

from uuid import uuid4

import requests


def test_search_api():
    """Test the search API endpoints directly."""
    base_url = "http://localhost:8000"

    print("🧪 Testing Search API Endpoints (CoT Style)")
    print("=" * 50)

    # Test data (using same collection as CoT script)
    user_id = str(uuid4())  # Generate a proper UUID
    collection_id = "db523922-4ea2-414e-bfb8-ab937eae02a7"  # From the CLI test output

    print(f"User ID: {user_id}")
    print(f"Collection ID: {collection_id}")

    # Test 1: Regular search (like CoT script)
    print("\n1️⃣ Testing regular search...")
    search_data = {
        "question": "What is machine learning?",
        "collection_id": collection_id,
        "user_id": user_id,
        "config_metadata": {},
    }

    try:
        # Use json= parameter for JSON data
        response = requests.post(f"{base_url}/api/search", json=search_data)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("   ✅ Search successful")
            print(f"   Answer: {result.get('answer', '')[:100]}...")
            print(f"   Documents: {len(result.get('documents', []))}")
            print(f"   Execution Time: {result.get('execution_time', 0):.2f}s")
        else:
            print(f"   ❌ Search failed: {response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error in search: {e}")
        return False

    # Test 2: CoT search (like CoT script)
    print("\n2️⃣ Testing CoT search...")
    cot_search_data = {
        "question": "How does machine learning work and what are the key components?",
        "collection_id": collection_id,
        "user_id": user_id,
        "config_metadata": {
            "cot_enabled": True,
            "show_cot_steps": True,
            "cot_config": {
                "max_reasoning_depth": 3,
                "reasoning_strategy": "decomposition",
                "token_budget_multiplier": 1.5,
            },
        },
    }

    try:
        # Use json= parameter for JSON data
        response = requests.post(f"{base_url}/api/search", json=cot_search_data)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("   ✅ CoT Search successful")
            print(f"   Answer: {result.get('answer', '')[:100]}...")
            print(f"   Documents: {len(result.get('documents', []))}")
            print(f"   Execution Time: {result.get('execution_time', 0):.2f}s")

            # Check CoT metadata
            cot_output = result.get("cot_output", {})
            if cot_output:
                print(f"   CoT Steps: {len(cot_output.get('reasoning_steps', []))}")
                print(f"   Confidence: {cot_output.get('total_confidence', 'N/A')}")
        else:
            print(f"   ❌ CoT Search failed: {response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error in CoT search: {e}")
        return False

    # Test 3: Test conversation endpoints (our new ones)
    print("\n3️⃣ Testing conversation endpoints...")

    # Create session
    session_data = {
        "user_id": user_id,
        "collection_id": collection_id,
        "session_name": "Search API Test",
        "context_window_size": 4000,
        "max_messages": 50,
        "is_archived": False,
        "is_pinned": False,
    }

    try:
        response = requests.post(f"{base_url}/api/chat/sessions", json=session_data)
        print(f"   Session Creation Status: {response.status_code}")

        if response.status_code == 200:
            session = response.json()
            session_id = session["id"]
            print(f"   ✅ Session created: {session_id}")

            # Test message processing
            message_data = {
                "session_id": session_id,
                "content": "What is machine learning?",
                "role": "user",
                "message_type": "question",
            }

            response = requests.post(f"{base_url}/api/chat/sessions/{session_id}/process", json=message_data)
            print(f"   Message Processing Status: {response.status_code}")

            if response.status_code == 200:
                message = response.json()
                print("   ✅ Message processed successfully")
                print(f"   Response: {message.get('content', '')[:100]}...")
            else:
                print(f"   ❌ Message processing failed: {response.text}")
        else:
            print(f"   ❌ Session creation failed: {response.text}")

    except Exception as e:
        print(f"   ❌ Error in conversation test: {e}")

    print("\n🎉 Search API Test Complete!")
    return True


if __name__ == "__main__":
    test_search_api()
