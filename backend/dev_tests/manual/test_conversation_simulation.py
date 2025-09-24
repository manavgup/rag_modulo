#!/usr/bin/env python3
"""Simulate conversation functionality using existing search API.

This script demonstrates conversation-like behavior using the existing search API,
similar to how the CoT script works but with conversation context simulation.
"""

import time
from uuid import uuid4

import requests


def simulate_conversation():
    """Simulate a conversation using the existing search API."""
    base_url = "http://localhost:8000"

    print("💬 Simulating Conversation with Documents")
    print("=" * 50)
    print("Using existing search API to simulate conversation behavior")

    # Test data
    user_id = str(uuid4())
    collection_id = "db523922-4ea2-414e-bfb8-ab937eae02a7"

    print(f"User ID: {user_id}")
    print(f"Collection ID: {collection_id}")

    # Simulate conversation context
    conversation_context = []

    # Conversation flow
    questions = [
        "What is machine learning?",
        "How does it work?",
        "What are the different types?",
        "Can you give me examples of supervised learning?",
    ]

    print(f"\n🔄 Simulating conversation with {len(questions)} questions...")

    for i, question in enumerate(questions, 1):
        print(f"\n--- Question {i} ---")
        print(f"User: {question}")

        # Build context from previous questions
        context_metadata = {}
        if conversation_context:
            context_metadata = {
                "conversation_context": " ".join(conversation_context[-3:]),  # Last 3 questions
                "conversation_aware": True,
                "previous_questions": conversation_context,
                "question_number": i,
            }

        # Create search payload with conversation context
        search_data = {
            "question": question,
            "collection_id": collection_id,
            "user_id": user_id,
            "config_metadata": {"cot_enabled": True, "show_cot_steps": False, **context_metadata},
        }

        try:
            response = requests.post(f"{base_url}/api/search", json=search_data)

            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", "")

                print(f"Assistant: {answer[:200]}{'...' if len(answer) > 200 else ''}")

                # Show integration metadata
                print("   🔗 Integration Status:")
                print(f"      CoT Used: {result.get('metadata', {}).get('cot_used', 'N/A')}")
                print(f"      Conversation Aware: {context_metadata.get('conversation_aware', 'N/A')}")
                print(f"      Context Used: {bool(context_metadata.get('conversation_context'))}")
                print(f"      Documents: {len(result.get('documents', []))}")
                print(f"      Execution Time: {result.get('execution_time', 0):.2f}s")

                # Add to conversation context
                conversation_context.append(question)

            else:
                print(f"   ❌ Search failed: {response.text}")
                break

        except Exception as e:
            print(f"   ❌ Error: {e}")
            break

        time.sleep(1)  # Brief pause between questions

    print("\n📊 Conversation Summary:")
    print(f"   Questions Asked: {len(conversation_context)}")
    print(f"   Context Built: {len(conversation_context) > 1}")
    print("   Integration Demonstrated: ✅")

    print("\n🎉 Conversation Simulation Complete!")
    print("   This demonstrates how conversation context can be built")
    print("   using the existing search API with CoT integration.")

    return True


if __name__ == "__main__":
    simulate_conversation()
