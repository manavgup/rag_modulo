#!/usr/bin/env python3
"""Quick test of conversation summarization APIs."""

import time
from uuid import uuid4

import requests

BASE_URL = "http://localhost:8000"
USER_ID = str(uuid4())
COLLECTION_ID = str(uuid4())


def test_session_creation():
    """Test creating a conversation session."""
    print("🔄 Testing session creation...")

    data = {
        "user_id": USER_ID,
        "collection_id": COLLECTION_ID,
        "session_name": "Test Summarization Session",
        "context_window_size": 4000,
        "max_messages": 50,
    }

    response = requests.post(f"{BASE_URL}/api/chat/sessions", json=data, timeout=30)
    print(f"Session creation status: {response.status_code}")

    if response.status_code == 200:
        session_data = response.json()
        print(f"✅ Session created: {session_data['id']}")
        return session_data["id"]
    else:
        print(f"❌ Session creation failed: {response.text}")
        return None


def test_message_creation(session_id):
    """Test adding messages to the session."""
    print("🔄 Testing message creation...")

    messages = [
        {"session_id": session_id, "content": "What is machine learning?", "role": "user", "message_type": "question"},
        {
            "session_id": session_id,
            "content": "Machine learning is a subset of artificial intelligence that focuses on creating algorithms...",
            "role": "assistant",
            "message_type": "answer",
        },
    ]

    for i, msg in enumerate(messages):
        response = requests.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json=msg, timeout=30)
        print(f"Message {i + 1} status: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ Message {i + 1} failed: {response.text}")
            return False

    print("✅ Messages created successfully")
    return True


def test_summary_creation(session_id):
    """Test creating a conversation summary."""
    print("🔄 Testing summary creation...")

    data = {
        "session_id": session_id,
        "message_count_to_summarize": 2,
        "strategy": "key_points_only",
        "preserve_context": True,
        "include_decisions": False,
        "include_questions": True,
    }

    response = requests.post(
        f"{BASE_URL}/api/chat/sessions/{session_id}/summaries", json=data, params={"user_id": USER_ID}, timeout=60
    )

    print(f"Summary creation status: {response.status_code}")

    if response.status_code == 200:
        summary_data = response.json()
        print(f"✅ Summary created: {summary_data['id']}")
        print(f"Summary text: {summary_data['summary_text'][:100]}...")
        return summary_data["id"]
    else:
        print(f"❌ Summary creation failed: {response.text}")
        return None


def test_summary_listing(session_id):
    """Test listing conversation summaries."""
    print("🔄 Testing summary listing...")

    response = requests.get(
        f"{BASE_URL}/api/chat/sessions/{session_id}/summaries", params={"user_id": USER_ID, "limit": 5}, timeout=30
    )

    print(f"Summary listing status: {response.status_code}")

    if response.status_code == 200:
        summaries = response.json()
        print(f"✅ Found {len(summaries)} summaries")
        return True
    else:
        print(f"❌ Summary listing failed: {response.text}")
        return False


def main():
    """Main test function."""
    print("🧪 Starting conversation summarization test...")

    # Wait for backend to be ready
    time.sleep(3)

    try:
        # Test session creation
        session_id = test_session_creation()
        if not session_id:
            print("❌ Test failed at session creation")
            return

        # Test message creation
        if not test_message_creation(session_id):
            print("❌ Test failed at message creation")
            return

        # Test summary creation
        summary_id = test_summary_creation(session_id)
        if not summary_id:
            print("❌ Test failed at summary creation")
            return

        # Test summary listing
        if not test_summary_listing(session_id):
            print("❌ Test failed at summary listing")
            return

        print("🎉 All conversation summarization tests passed!")

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")


if __name__ == "__main__":
    main()
