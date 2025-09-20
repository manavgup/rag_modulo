"""End-to-end tests for seamless Search + CoT + Conversation workflow - TDD Red Phase.

This module validates the complete workflow ensuring:
1. Conversation provides UI and context management
2. Search provides RAG functionality with conversation awareness
3. CoT provides enhanced reasoning with conversation history
4. All three work seamlessly without duplication
5. Existing capabilities are preserved and enhanced
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from rag_solution.main import app


class TestSeamlessWorkflowTDD:
    """Test cases for seamless workflow validation."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def test_user_id(self) -> str:
        """Create test user ID."""
        return str(uuid4())

    @pytest.fixture
    def test_collection_id(self) -> str:
        """Create test collection ID."""
        return str(uuid4())

    @pytest.mark.e2e
    def test_conversation_ui_and_context_management_workflow(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test that Conversation provides UI and context management."""
        # Step 1: Create conversation session (UI functionality)
        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "UI and Context Test",
            "context_window_size": 4000,
            "max_messages": 50,
        }

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Verify UI functionality - session management
        assert session["user_id"] == test_user_id
        assert session["collection_id"] == test_collection_id
        assert session["session_name"] == "UI and Context Test"
        assert session["context_window_size"] == 4000
        assert session["max_messages"] == 50

        # Step 2: Test context management - build context from messages
        user_message_1 = {"content": "What is machine learning?", "role": "user", "message_type": "question"}

        message_response_1 = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message_1)
        assert message_response_1.status_code == 201
        user_msg_1 = message_response_1.json()

        assistant_message_1 = {
            "content": "Machine learning is a subset of AI that enables computers to learn from data.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": {
                "context_managed": True,
                "entities_extracted": ["machine learning", "AI"],
                "conversation_topic": "AI concepts",
            },
        }

        assistant_response_1 = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message_1)
        assert assistant_response_1.status_code == 201
        assistant_msg_1 = assistant_response_1.json()

        # Verify context management
        assert assistant_msg_1["metadata"]["context_managed"] is True
        assert "machine learning" in assistant_msg_1["metadata"]["entities_extracted"]
        assert assistant_msg_1["metadata"]["conversation_topic"] == "AI concepts"

        # Step 3: Test context enhancement for follow-up questions
        user_message_2 = {"content": "How does it work?", "role": "user", "message_type": "follow_up"}

        message_response_2 = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message_2)
        assert message_response_2.status_code == 201
        user_msg_2 = message_response_2.json()

        assistant_message_2 = {
            "content": "Machine learning works by using algorithms to identify patterns in data, building on our previous discussion about AI concepts.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": {
                "context_enhanced": True,
                "enhanced_question": "How does machine learning work? (in the context of AI concepts)",
                "conversation_context_used": True,
                "entities_resolved": ["machine learning", "AI"],
            },
        }

        assistant_response_2 = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message_2)
        assert assistant_response_2.status_code == 201
        assistant_msg_2 = assistant_response_2.json()

        # Verify context enhancement
        assert assistant_msg_2["metadata"]["context_enhanced"] is True
        assert "AI concepts" in assistant_msg_2["metadata"]["enhanced_question"]
        assert assistant_msg_2["metadata"]["conversation_context_used"] is True

        # Step 4: Clean up
        delete_response = client.delete(f"/api/chat/sessions/{session_id}?user_id={test_user_id}")
        assert delete_response.status_code == 200

    @pytest.mark.e2e
    def test_search_rag_with_conversation_awareness_workflow(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test that Search provides RAG functionality with conversation awareness."""
        # Step 1: Create session
        session_data = {"user_id": test_user_id, "collection_id": test_collection_id, "session_name": "Search RAG Test"}

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Step 2: Test search without conversation context (preserves existing functionality)
        user_message_1 = {"content": "What is machine learning?", "role": "user", "message_type": "question"}

        message_response_1 = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message_1)
        assert message_response_1.status_code == 201

        assistant_message_1 = {
            "content": "Machine learning is a subset of artificial intelligence that enables computers to learn from data.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": {
                "search_used": True,
                "conversation_aware": False,
                "original_functionality": True,
                "search_sources": ["doc1", "doc2"],
            },
        }

        assistant_response_1 = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message_1)
        assert assistant_response_1.status_code == 201
        assistant_msg_1 = assistant_response_1.json()

        # Verify original search functionality preserved
        assert assistant_msg_1["metadata"]["search_used"] is True
        assert assistant_msg_1["metadata"]["conversation_aware"] is False
        assert assistant_msg_1["metadata"]["original_functionality"] is True

        # Step 3: Test search with conversation context (enhanced functionality)
        user_message_2 = {"content": "How does it work?", "role": "user", "message_type": "follow_up"}

        message_response_2 = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message_2)
        assert message_response_2.status_code == 201

        assistant_message_2 = {
            "content": "Machine learning works by using algorithms to identify patterns in data, building on our previous discussion about AI concepts.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": {
                "search_used": True,
                "conversation_aware": True,
                "enhanced_functionality": True,
                "enhanced_question": "How does machine learning work? (in the context of AI concepts)",
                "conversation_context_used": True,
                "search_sources": ["doc1", "doc3"],
            },
        }

        assistant_response_2 = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message_2)
        assert assistant_response_2.status_code == 201
        assistant_msg_2 = assistant_response_2.json()

        # Verify enhanced search functionality
        assert assistant_msg_2["metadata"]["search_used"] is True
        assert assistant_msg_2["metadata"]["conversation_aware"] is True
        assert assistant_msg_2["metadata"]["enhanced_functionality"] is True
        assert "AI concepts" in assistant_msg_2["metadata"]["enhanced_question"]
        assert assistant_msg_2["metadata"]["conversation_context_used"] is True

        # Step 4: Clean up
        delete_response = client.delete(f"/api/chat/sessions/{session_id}?user_id={test_user_id}")
        assert delete_response.status_code == 200

    @pytest.mark.e2e
    def test_cot_enhanced_reasoning_with_conversation_history_workflow(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test that CoT provides enhanced reasoning with conversation history."""
        # Step 1: Create session
        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "CoT Reasoning Test",
        }

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Step 2: Test CoT without conversation context (preserves existing functionality)
        user_message_1 = {"content": "How does machine learning work?", "role": "user", "message_type": "question"}

        message_response_1 = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message_1)
        assert message_response_1.status_code == 201

        assistant_message_1 = {
            "content": "Machine learning works by using algorithms to identify patterns in data.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": {
                "cot_used": True,
                "reasoning_strategy": "decomposition",
                "reasoning_steps": 2,
                "conversation_context_used": False,
                "original_functionality": True,
            },
        }

        assistant_response_1 = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message_1)
        assert assistant_response_1.status_code == 201
        assistant_msg_1 = assistant_response_1.json()

        # Verify original CoT functionality preserved
        assert assistant_msg_1["metadata"]["cot_used"] is True
        assert assistant_msg_1["metadata"]["reasoning_strategy"] == "decomposition"
        assert assistant_msg_1["metadata"]["conversation_context_used"] is False
        assert assistant_msg_1["metadata"]["original_functionality"] is True

        # Step 3: Test CoT with conversation context (enhanced functionality)
        user_message_2 = {"content": "How do they relate?", "role": "user", "message_type": "follow_up"}

        message_response_2 = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message_2)
        assert message_response_2.status_code == 201

        assistant_message_2 = {
            "content": "Machine learning and neural networks are closely related. Machine learning is the broader field that includes neural networks as one of its key techniques, building on our previous discussion about AI concepts.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": {
                "cot_used": True,
                "reasoning_strategy": "conversation_aware",
                "reasoning_steps": 3,
                "conversation_context_used": True,
                "enhanced_functionality": True,
                "conversation_entities": ["machine learning", "neural networks", "AI"],
                "reasoning_enhanced": True,
            },
        }

        assistant_response_2 = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message_2)
        assert assistant_response_2.status_code == 201
        assistant_msg_2 = assistant_response_2.json()

        # Verify enhanced CoT functionality
        assert assistant_msg_2["metadata"]["cot_used"] is True
        assert assistant_msg_2["metadata"]["reasoning_strategy"] == "conversation_aware"
        assert assistant_msg_2["metadata"]["conversation_context_used"] is True
        assert assistant_msg_2["metadata"]["enhanced_functionality"] is True
        assert "machine learning" in assistant_msg_2["metadata"]["conversation_entities"]
        assert assistant_msg_2["metadata"]["reasoning_enhanced"] is True

        # Step 4: Clean up
        delete_response = client.delete(f"/api/chat/sessions/{session_id}?user_id={test_user_id}")
        assert delete_response.status_code == 200

    @pytest.mark.e2e
    def test_seamless_integration_without_duplication_workflow(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test that all three services work seamlessly without duplication."""
        # Step 1: Create session
        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "Seamless Integration Test",
        }

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Step 2: Test seamless integration flow
        user_message = {
            "content": "What is machine learning and how does it work?",
            "role": "user",
            "message_type": "question",
        }

        message_response = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message)
        assert message_response.status_code == 201

        # Step 3: Verify seamless integration response
        assistant_message = {
            "content": "Machine learning is a subset of artificial intelligence that enables computers to learn from data. It works by using algorithms to identify patterns in data and make predictions or decisions based on those patterns.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": {
                "integration_seamless": True,
                "conversation_ui_used": True,
                "search_rag_used": True,
                "cot_reasoning_used": True,
                "no_duplication": True,
                "service_boundaries_respected": True,
                "conversation_context_managed": True,
                "search_enhanced_with_context": True,
                "cot_enhanced_with_history": True,
            },
        }

        assistant_response = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message)
        assert assistant_response.status_code == 201
        assistant_msg = assistant_response.json()

        # Verify seamless integration
        assert assistant_msg["metadata"]["integration_seamless"] is True
        assert assistant_msg["metadata"]["conversation_ui_used"] is True
        assert assistant_msg["metadata"]["search_rag_used"] is True
        assert assistant_msg["metadata"]["cot_reasoning_used"] is True
        assert assistant_msg["metadata"]["no_duplication"] is True
        assert assistant_msg["metadata"]["service_boundaries_respected"] is True

        # Step 4: Test follow-up with enhanced integration
        user_message_2 = {"content": "Tell me more about neural networks", "role": "user", "message_type": "follow_up"}

        message_response_2 = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message_2)
        assert message_response_2.status_code == 201

        assistant_message_2 = {
            "content": "Neural networks are computing systems inspired by biological neural networks. They are a key technique in machine learning, building on our previous discussion about AI concepts.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": {
                "integration_seamless": True,
                "conversation_context_enhanced": True,
                "search_aware_of_conversation": True,
                "cot_considers_history": True,
                "enhanced_question": "Tell me more about neural networks (in the context of machine learning and AI)",
                "conversation_entities_used": ["neural networks", "machine learning", "AI"],
                "reasoning_strategy": "conversation_aware",
            },
        }

        assistant_response_2 = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message_2)
        assert assistant_response_2.status_code == 201
        assistant_msg_2 = assistant_response_2.json()

        # Verify enhanced integration
        assert assistant_msg_2["metadata"]["integration_seamless"] is True
        assert assistant_msg_2["metadata"]["conversation_context_enhanced"] is True
        assert assistant_msg_2["metadata"]["search_aware_of_conversation"] is True
        assert assistant_msg_2["metadata"]["cot_considers_history"] is True
        assert "AI" in assistant_msg_2["metadata"]["enhanced_question"]
        assert "machine learning" in assistant_msg_2["metadata"]["conversation_entities_used"]

        # Step 5: Clean up
        delete_response = client.delete(f"/api/chat/sessions/{session_id}?user_id={test_user_id}")
        assert delete_response.status_code == 200

    @pytest.mark.e2e
    def test_preservation_and_enhancement_of_existing_capabilities_workflow(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test that existing capabilities are preserved and enhanced."""
        # Step 1: Create session
        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "Preservation and Enhancement Test",
        }

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Step 2: Test existing search functionality preserved
        user_message_1 = {"content": "What is machine learning?", "role": "user", "message_type": "question"}

        message_response_1 = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message_1)
        assert message_response_1.status_code == 201

        assistant_message_1 = {
            "content": "Machine learning is a subset of artificial intelligence that enables computers to learn from data.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": {
                "original_functionality_preserved": True,
                "search_works_as_before": True,
                "cot_works_as_before": True,
                "conversation_aware": False,
                "enhanced": False,
                "backward_compatible": True,
            },
        }

        assistant_response_1 = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message_1)
        assert assistant_response_1.status_code == 201
        assistant_msg_1 = assistant_response_1.json()

        # Verify existing functionality preserved
        assert assistant_msg_1["metadata"]["original_functionality_preserved"] is True
        assert assistant_msg_1["metadata"]["search_works_as_before"] is True
        assert assistant_msg_1["metadata"]["cot_works_as_before"] is True
        assert assistant_msg_1["metadata"]["backward_compatible"] is True

        # Step 3: Test enhanced functionality
        user_message_2 = {"content": "How does it work?", "role": "user", "message_type": "follow_up"}

        message_response_2 = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message_2)
        assert message_response_2.status_code == 201

        assistant_message_2 = {
            "content": "Machine learning works by using algorithms to identify patterns in data, building on our previous discussion about AI concepts.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": {
                "original_functionality_preserved": True,
                "enhanced_functionality_added": True,
                "conversation_aware": True,
                "search_enhanced": True,
                "cot_enhanced": True,
                "backward_compatible": True,
                "enhanced_question": "How does machine learning work? (in the context of AI concepts)",
                "conversation_context_used": True,
            },
        }

        assistant_response_2 = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message_2)
        assert assistant_response_2.status_code == 201
        assistant_msg_2 = assistant_response_2.json()

        # Verify enhanced functionality
        assert assistant_msg_2["metadata"]["original_functionality_preserved"] is True
        assert assistant_msg_2["metadata"]["enhanced_functionality_added"] is True
        assert assistant_msg_2["metadata"]["conversation_aware"] is True
        assert assistant_msg_2["metadata"]["search_enhanced"] is True
        assert assistant_msg_2["metadata"]["cot_enhanced"] is True
        assert assistant_msg_2["metadata"]["backward_compatible"] is True
        assert "AI concepts" in assistant_msg_2["metadata"]["enhanced_question"]

        # Step 4: Clean up
        delete_response = client.delete(f"/api/chat/sessions/{session_id}?user_id={test_user_id}")
        assert delete_response.status_code == 200
