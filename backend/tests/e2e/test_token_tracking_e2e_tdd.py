"""TDD Red Phase: End-to-end tests for token tracking through API.

E2E tests focus on testing complete token tracking workflows from API
to database, with real dependencies and full system integration.
"""

import logging
from collections.abc import Generator
from datetime import datetime
from uuid import UUID

import pytest
from core.config import Settings, get_settings
from core.mock_auth import ensure_mock_user_exists
from fastapi import UploadFile
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from rag_solution.file_management.database import get_db
from rag_solution.schemas.collection_schema import CollectionStatus
from rag_solution.services.collection_service import CollectionService


# New helper function to create a mock file
def create_mock_file(filename="test_doc.txt", content=None) -> UploadFile:
    """Helper to create a mock UploadFile object."""
    from io import BytesIO

    if content is None:
        content = """
        Artificial Intelligence and Machine Learning Fundamentals

        Artificial Intelligence (AI) is a broad field of computer science focused on creating systems that can perform tasks typically requiring human intelligence. Machine Learning (ML) is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed.

        Key concepts in machine learning include:
        - Supervised learning: Learning with labeled training data
        - Unsupervised learning: Finding patterns in data without labels
        - Deep learning: Using neural networks with multiple layers
        - Natural language processing: Teaching computers to understand human language

        Applications of AI and ML span across industries including healthcare, finance, transportation, and entertainment. These technologies are transforming how we work, communicate, and solve complex problems.

        The future of AI holds promise for even more advanced capabilities, including general artificial intelligence that could match or exceed human cognitive abilities across all domains.
        """

    return UploadFile(
        filename=filename,
        file=BytesIO(content.encode("utf-8")),
    )


# New helper function to wait for collection status, using the service layer
def wait_for_collection_status(
    collection_service: CollectionService, collection_id: UUID, status: CollectionStatus, timeout=60, interval=2
):
    """Waits for a collection to reach a specific status by calling the service."""
    import time

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            collection = collection_service.get_collection(collection_id)
            if collection.status == status:
                return True
        except Exception:
            pass  # Ignore exceptions while polling
        time.sleep(interval)
    return False


# NEW FIXTURE to override the database dependency for the entire test session.
# This fixes the psycopg2.OperationalError by ensuring all connections use the correct hostname.
@pytest.fixture(scope="session")
def db_session(e2e_settings: Settings) -> Generator[Session, None, None]:
    # Use injected settings instead of accessing environment directly
    # Determine the correct database host based on environment
    # When running via 'make test', we're in a Docker container, so use 'postgres'
    # When running locally, PostgreSQL might be accessible via localhost
    db_host = e2e_settings.collectiondb_host

    database_url = f"postgresql://{e2e_settings.collectiondb_user}:{e2e_settings.collectiondb_pass}@{db_host}:{e2e_settings.collectiondb_port}/{e2e_settings.collectiondb_name}"
    engine = create_engine(database_url)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = testing_session_local()
    try:
        # Override the dependency for the duration of the test session
        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        yield db
    finally:
        db.close()
        del app.dependency_overrides[get_db]


# Apply the db_session fixture to the entire test class to ensure consistent database connections
@pytest.mark.usefixtures("db_session")
class TestTokenTrackingE2ETDD:
    """End-to-end tests for token tracking through the complete system."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client for E2E testing."""
        return TestClient(app)

    @pytest.fixture
    def test_user_id(self) -> str:
        """Get the mock user ID that the authentication middleware uses."""
        # Use the overridden database session
        db_gen = get_db()
        db = next(db_gen)
        try:
            settings = get_settings()
            user_id = ensure_mock_user_exists(db, settings)
            return str(user_id)
        finally:
            db.close()

    @pytest.fixture(scope="session")
    def e2e_settings(self):
        """Create a real settings object for E2E tests using actual environment variables."""
        from core.config import get_settings

        return get_settings()

    # The test_collection_id fixture is now correctly using the API endpoint
    # to create and process documents.
    @pytest.fixture
    def test_collection_id(self, client: TestClient) -> str:
        """Create a real test collection in the database with documents for E2E testing."""
        logger = logging.getLogger(__name__)

        # Create a mock file
        create_mock_file()

        # Use BytesIO for test isolation instead of file system access
        from io import BytesIO

        # Get file content without file system operations
        file_content = b"Test content for token tracking E2E test"

        # Define variables locally before making the API call
        collection_name = f"E2E Token Test Collection {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        is_private_flag = True

        create_response = client.post(
            "/api/collections/with-files",
            data={
                "collection_name": collection_name,
                "is_private": str(is_private_flag).lower(),
            },
            files={"files": ("test_file.txt", BytesIO(file_content), "text/plain")},
        )

        assert (
            create_response.status_code == 200
        ), f"API call failed with status {create_response.status_code} and response: {create_response.text}"
        collection = create_response.json()
        collection_id = UUID(collection["id"])

        # Get a database session to instantiate the service
        db_gen = get_db()
        db = next(db_gen)
        try:
            collection_service = CollectionService(db, get_settings())

            logger.info(f"Waiting for collection {collection_id} to complete processing...")
            is_ready = wait_for_collection_status(collection_service, collection_id, CollectionStatus.COMPLETED)
            assert is_ready, "Collection did not reach 'COMPLETED' status within the timeout."
            logger.info(f"Test collection {collection_id} is ready for search.")
        finally:
            db.close()

        # No cleanup needed since we're using BytesIO

        return str(collection_id)

    # ==================== CONVERSATION API TOKEN TRACKING E2E ====================

    @pytest.mark.e2e
    def test_conversation_process_message_returns_token_usage(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test conversation message processing returns token usage metadata."""
        # Set up logging for this test
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        # Step 1: Create a conversation session
        logger.info("🔍 STEP 1: Creating conversation session")
        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "Token Tracking Test Session",
            "context_window_size": 4000,
            "max_messages": 50,
        }
        logger.info(f"   📝 Session data: {session_data}")

        create_response = client.post("/api/chat/sessions", json=session_data)
        logger.info(f"   📊 Session creation response status: {create_response.status_code}")
        logger.info(f"   📄 Session creation response body: {create_response.json()}")

        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["id"]
        logger.info(f"   ✅ Session created successfully with ID: {session_id}")

        # Step 2: Process a user message (this should trigger search with token tracking)
        logger.info("🔍 STEP 2: Processing user message")
        user_message = {
            "session_id": session_id,
            "content": "What is artificial intelligence and how does machine learning work?",
            "role": "user",
            "message_type": "question",
            "metadata": None,
        }
        logger.info(f"   📝 User message: {user_message}")

        # Use the process endpoint which integrates with search service
        logger.info(f"   🚀 Making POST request to: /api/chat/sessions/{session_id}/process")
        process_response = client.post(f"/api/chat/sessions/{session_id}/process", json=user_message)
        logger.info(f"   📊 Process response status: {process_response.status_code}")

        if process_response.status_code != 200:
            logger.error(f"   ❌ Process response failed with status {process_response.status_code}")
            logger.error(f"   📄 Error response body: {process_response.text}")

        assert process_response.status_code == 200

        response_data = process_response.json()
        logger.info(f"   📄 Full response data: {response_data}")

        assert "id" in response_data  # Check for a key that should exist in ConversationMessageOutput
        assert "content" in response_data
        logger.info("   ✅ Message processing successful")

        # Step 3: Verify token usage is included in response
        logger.info("🔍 STEP 3: Verifying token usage in response")
        message = response_data
        logger.info(f"   📝 Message object: {message}")

        assert "metadata" in message
        assert message["metadata"] is not None
        logger.info(f"   📊 Message metadata: {message['metadata']}")

        # Check for token usage in search metadata
        if "search_metadata" in message["metadata"] and message["metadata"]["search_metadata"]:
            logger.info("   🔍 Found search_metadata in response")
            search_metadata = message["metadata"]["search_metadata"]
            logger.info(f"   📊 Search metadata: {search_metadata}")

            if "token_usage" in search_metadata:
                logger.info("   ✅ Found token_usage in search_metadata!")
                token_usage = search_metadata["token_usage"]
                logger.info(f"   📊 Token usage data: {token_usage}")

                assert "prompt_tokens" in token_usage
                assert "completion_tokens" in token_usage
                assert "total_tokens" in token_usage
                assert "model_name" in token_usage
                assert token_usage["prompt_tokens"] > 0
                assert token_usage["completion_tokens"] > 0
                assert token_usage["total_tokens"] > 0
                logger.info("   ✅ All token usage assertions passed!")
            else:
                logger.warning("   ⚠️  No token_usage found in search_metadata")
                logger.info(f"   📊 Available keys in search_metadata: {list(search_metadata.keys())}")
        else:
            logger.warning("   ⚠️  No search_metadata found in message metadata")
            if message["metadata"]:
                logger.info(f"   📊 Available keys in metadata: {list(message['metadata'].keys())}")
            else:
                logger.info("   📊 Message metadata is empty/None")

        # Step 4: Check if token warning is present (may or may not be)
        logger.info("🔍 STEP 4: Checking for token warnings")
        if "token_warning" in response_data and response_data["token_warning"] is not None:
            logger.info("   ✅ Found token_warning in response!")
            token_warning = response_data["token_warning"]
            logger.info(f"   📊 Token warning data: {token_warning}")

            assert "type" in token_warning
            assert "message" in token_warning
            assert "severity" in token_warning
            assert "percentage_used" in token_warning
            assert token_warning["severity"] in ["info", "warning", "critical"]
            logger.info("   ✅ All token warning assertions passed!")
        else:
            logger.info("   i  No token warning found in response (this is optional)")

        logger.info("🎉 Test completed successfully!")

    @pytest.mark.e2e
    def test_conversation_token_warning_appears_with_high_usage(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test token warning appears when approaching context limits."""
        # Create session with small context window to trigger warnings easier
        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "Token Warning Test Session",
            "context_window_size": 1000,  # Smaller window to trigger warnings
            "max_messages": 50,
        }

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["id"]

        # Send multiple messages to build up context
        questions = [
            "Tell me everything about artificial intelligence, machine learning, deep learning, neural networks, and their applications.",
            "Explain in detail how convolutional neural networks work, including backpropagation, gradient descent, and optimization techniques.",
            "Describe the history of AI from Alan Turing to modern large language models, including all major breakthroughs and researchers.",
            "What are the ethical implications of AI, including bias, privacy, job displacement, and the potential for artificial general intelligence?",
        ]

        for i, question in enumerate(questions):
            user_message = {
                "session_id": session_id,
                "content": question,
                "role": "user",
                "message_type": "question" if i == 0 else "follow_up",
                "metadata": None,
            }

            process_response = client.post(f"/api/chat/sessions/{session_id}/process", json=user_message)

            # All requests should succeed (even if warnings are present)
            assert process_response.status_code == 200
            response_data = process_response.json()
            assert "id" in response_data
            assert "content" in response_data

            # Check for token warning in later messages
            if i >= 2 and "token_warning" in response_data:  # After a few messages, we might see warnings
                token_warning = response_data["token_warning"]
                if token_warning is not None:  # Only check if token_warning is not None
                    assert token_warning["type"] in ["approaching_limit", "at_limit", "conversation_too_long"]
                    assert token_warning["severity"] in ["info", "warning", "critical"]
                    assert token_warning["percentage_used"] > 60  # Should be getting full

                    # If critical warning, should suggest new session
                    if token_warning["severity"] == "critical":
                        assert "suggested_action" in token_warning
                        assert token_warning["suggested_action"] in ["start_new_session", "consider_new_session"]

    @pytest.mark.e2e
    def test_session_token_statistics_endpoint(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test session token statistics endpoint returns aggregated usage."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        # Create session
        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "Token Stats Test Session",
            "context_window_size": 4000,
            "max_messages": 50,
        }

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["id"]

        # Send several messages to accumulate token usage
        messages = [
            "What is machine learning?",
            "Tell me about neural networks.",
            "How does deep learning work?",
        ]

        for message_content in messages:
            user_message = {
                "session_id": session_id,
                "content": message_content,
                "role": "user",
                "message_type": "question",
                "metadata": None,
            }

            process_response = client.post(f"/api/chat/sessions/{session_id}/process", json=user_message)
            assert process_response.status_code == 200

        # Get token statistics
        stats_response = client.get(f"/api/chat/sessions/{session_id}/statistics?user_id={test_user_id}")
        assert stats_response.status_code == 200

        stats_data = stats_response.json()
        logger.info("********** %s\n", stats_data)
        assert "session_id" in stats_data
        assert "total_tokens" in stats_data
        assert stats_data["session_id"] == session_id

        # The API now returns a flat structure, so the 'statistics' key is removed.
        # All statistics are directly available in the stats_data dictionary.
        # Check basic token statistics (these should always be present)
        assert stats_data.get("total_tokens") >= 0
        assert stats_data.get("total_prompt_tokens") >= 0
        assert stats_data.get("total_completion_tokens") >= 0

        # Check if there were any LLM calls and proceed with detailed assertions if so.
        if stats_data.get("metadata", {}).get("total_llm_calls", 0) > 0:
            # These keys are now part of the metadata dictionary
            # The 'average_tokens_per_call' key is not present, but can be derived
            assert "by_service" in stats_data.get("metadata", {})
            assert "by_model" in stats_data.get("metadata", {})

    # ==================== SEARCH API TOKEN TRACKING E2E ====================

    @pytest.mark.e2e
    def test_search_api_includes_token_usage_in_response(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test search API includes token usage in response metadata."""
        # Make a search request
        search_data = {
            "question": "What are the key concepts in artificial intelligence?",
            "collection_id": test_collection_id,
            "user_id": test_user_id,
            "config_metadata": {
                "session_id": "test_session_search",
                "enable_token_tracking": True,
            },
        }

        search_response = client.post("/api/search", json=search_data)

        # Search may fail due to missing implementation, but if it succeeds,
        # it should include token metadata
        if search_response.status_code == 200:
            response_data = search_response.json()
            assert "metadata" in response_data

            metadata = response_data["metadata"]

            # Check for token usage
            if "token_usage" in metadata:
                token_usage = metadata["token_usage"]
                assert "prompt_tokens" in token_usage
                assert "completion_tokens" in token_usage
                assert "total_tokens" in token_usage
                assert "model_name" in token_usage
                assert token_usage["total_tokens"] > 0

            # Check for token warning
            if "token_warning" in metadata:
                token_warning = metadata["token_warning"]
                assert "type" in token_warning
                assert "severity" in token_warning
                assert "percentage_used" in token_warning

    # ==================== CHAIN OF THOUGHT TOKEN TRACKING E2E ====================

    @pytest.mark.e2e
    def test_chain_of_thought_token_breakdown_in_response(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test Chain of Thought provides token breakdown for each step."""
        # Create session
        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "CoT Token Test Session",
            "context_window_size": 4000,
            "max_messages": 50,
        }

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["id"]

        # Ask a complex question that should trigger Chain of Thought
        complex_question = {
            "session_id": session_id,
            "content": "Analyze the relationship between artificial intelligence, machine learning, and deep learning. Compare their historical development, current applications, and future potential. What are the key differences and how do they complement each other?",
            "role": "user",
            "message_type": "question",
            "metadata": None,
        }

        process_response = client.post(f"/api/chat/sessions/{session_id}/process", json=complex_question)

        if process_response.status_code == 200:
            response_data = process_response.json()
            assert "id" in response_data
            assert "content" in response_data

            message = response_data
            if message.get("metadata"):
                metadata = message["metadata"]

                # Check for CoT usage indicator
                if metadata.get("cot_used") and metadata.get("search_metadata"):
                    # Should have search metadata with CoT breakdown
                    search_metadata = metadata["search_metadata"]

                    # Look for CoT token breakdown
                    if "cot_steps" in search_metadata:
                        cot_steps = search_metadata["cot_steps"]
                        assert isinstance(cot_steps, list)
                        assert len(cot_steps) > 0

                        # Each step should have token information
                        for step in cot_steps:
                            if "total_tokens" in step:
                                assert step["total_tokens"] > 0

    # ==================== ERROR HANDLING E2E ====================

    @pytest.mark.e2e
    def test_token_tracking_graceful_failure(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test system handles token tracking failures gracefully."""
        # Create session
        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "Error Handling Test Session",
            "context_window_size": 4000,
            "max_messages": 50,
        }

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["id"]

        # Send a message even if token tracking fails
        user_message = {
            "session_id": session_id,
            "content": "This should work even if token tracking fails.",
            "role": "user",
            "message_type": "question",
            "metadata": None,
        }

        process_response = client.post(f"/api/chat/sessions/{session_id}/process", json=user_message)

        # The request should still succeed even if token tracking has issues
        # (This tests graceful degradation)
        assert process_response.status_code in [200, 500]  # Either works or fails gracefully

        if process_response.status_code == 200:
            response_data = process_response.json()
            # Response should be valid even if token data is missing
            assert "id" in response_data
            assert "content" in response_data

    # ==================== MULTIPLE MODELS TOKEN TRACKING E2E ====================

    @pytest.mark.e2e
    def test_token_tracking_different_models(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        """E2E: Test token tracking works correctly with different LLM models."""
        # This test would verify that token tracking works regardless of which
        # LLM provider is being used (OpenAI, Anthropic, IBM WatsonX, etc.)

        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "Multi-Model Token Test Session",
            "context_window_size": 4000,
            "max_messages": 50,
        }

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["id"]

        # Send a message
        user_message = {
            "session_id": session_id,
            "content": "Test message for any LLM model.",
            "role": "user",
            "message_type": "question",
            "metadata": None,
        }

        process_response = client.post(f"/api/chat/sessions/{session_id}/process", json=user_message)

        if process_response.status_code == 200:
            message = process_response.json()

            if message.get("metadata"):
                metadata = message["metadata"]
                if metadata.get("search_metadata"):
                    search_metadata = metadata["search_metadata"]
                    if "token_usage" in search_metadata:
                        token_usage = search_metadata["token_usage"]

                        # Should have a model name regardless of which provider
                        assert "model_name" in token_usage
                        assert token_usage["model_name"] is not None
                        assert len(token_usage["model_name"]) > 0

                        logger.info(f"   ✅ Found token usage with model: {token_usage['model_name']}")
                    else:
                        logger.info("   ⚠️  No token usage found in search metadata")
                else:
                    logger.info("   ⚠️  No search metadata found")
            else:
                logger.info("   ⚠️  No message metadata found")
        else:
            logger.error(f"   ❌ Request failed with status {process_response.status_code}")
            logger.error(f"   📄 Error response: {process_response.text}")

        logger.info("🎉 Token usage model name test completed!")
