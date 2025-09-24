#!/usr/bin/env python3
"""Quick test to trigger the conversation process endpoint error using mock user."""

import requests
import json
from uuid import uuid4
import time

BASE_URL = "http://localhost:8000"

# Use the mock user ID from auth middleware
MOCK_USER_ID = "1aa5093c-084e-4f20-905b-cf5e18301b1c"

def main():
    """Test the conversation process endpoint directly."""
    print("🔄 Testing conversation process endpoint...")

    # First, create a collection using the mock user
    collection_data = {
        "name": "Test Collection",
        "description": "Test collection for conversation process",
        "is_private": True,
        "user_id": MOCK_USER_ID
    }

    print("Creating collection...")
    response = requests.post(f"{BASE_URL}/api/collections", json=collection_data, timeout=30)

    if response.status_code != 200:
        print(f"❌ Collection creation failed: {response.status_code} - {response.text}")
        return

    collection_id = response.json()['id']
    print(f"✅ Collection created: {collection_id}")

    # Create a session using the created collection
    session_data = {
        "user_id": MOCK_USER_ID,
        "collection_id": collection_id,
        "session_name": "Test Process Session",
        "context_window_size": 4000,
        "max_messages": 50,
    }

    print("Creating session...")
    response = requests.post(f"{BASE_URL}/api/chat/sessions", json=session_data, timeout=30)

    if response.status_code != 200:
        print(f"❌ Session creation failed: {response.status_code} - {response.text}")
        return

    session_id = response.json()['id']
    print(f"✅ Session created: {session_id}")

    # Now test the process endpoint
    message_data = {
        "session_id": session_id,
        "content": "What is machine learning?",
        "role": "user",
        "message_type": "question"
    }

    print("Testing process endpoint...")
    response = requests.post(
        f"{BASE_URL}/api/chat/sessions/{session_id}/process",
        json=message_data,
        timeout=30
    )

    print(f"Process endpoint response: {response.status_code}")
    if response.status_code != 200:
        print(f"❌ Process failed: {response.text}")
        try:
            error_json = response.json()
            print(f"Error details: {json.dumps(error_json, indent=2)}")
        except:
            print("Could not parse error response as JSON")
    else:
        print("✅ Process succeeded")

if __name__ == "__main__":
    main()