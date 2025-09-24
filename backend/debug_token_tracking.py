#!/usr/bin/env python3
"""Debug script to test token tracking in conversation processing."""

import asyncio
import json
import logging
import os
import sys

# Add the backend directory to sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, backend_dir)


from core.config import get_settings
from core.mock_auth import ensure_mock_user_exists
from rag_solution.file_management.database import get_db
from rag_solution.schemas.conversation_schema import ConversationMessageInput, MessageRole, MessageType
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.conversation_service import ConversationService

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def debug_token_tracking():
    """Debug token tracking in conversation processing."""
    logger.info("🔍 DEBUG: Starting token tracking debug...")

    # Get database and settings
    db_gen = get_db()
    db = next(db_gen)
    settings = get_settings()

    try:
        # Create a test user
        user_id = ensure_mock_user_exists(db, settings, user_key="debug_token_test")
        logger.info(f"✅ Created test user: {user_id}")

        # Use an existing collection with documents instead of creating a new one
        collection_service = CollectionService(db, settings)
        collections = collection_service.get_user_collections(user_id)

        # Find a collection with documents
        suitable_collection = None
        for collection in collections:
            if len(collection.files) > 0:
                suitable_collection = collection
                break

        if not suitable_collection:
            logger.error("❌ No collections with documents found. Please upload documents to a collection first.")
            return

        logger.info(
            f"✅ Using existing collection: {suitable_collection.name} (ID: {suitable_collection.id}) with {len(suitable_collection.files)} files"
        )
        collection = suitable_collection

        # Create conversation service
        conversation_service = ConversationService(db, settings)

        # Create a conversation session
        from rag_solution.schemas.conversation_schema import ConversationSessionInput

        session_input = ConversationSessionInput(
            user_id=user_id,
            collection_id=collection.id,
            session_name="Debug Token Tracking Session",
            context_window_size=4000,
            max_messages=50,
        )
        session = await conversation_service.create_session(session_input)
        logger.info(f"✅ Created conversation session: {session.id}")

        # Create a test message
        message_input = ConversationMessageInput(
            session_id=session.id,
            content="What is artificial intelligence and how does machine learning work?",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            metadata=None,
            token_count=None,  # Let the service calculate it
            execution_time=None,
        )

        logger.info("🚀 Processing user message...")
        logger.info(f"📝 Message content: {message_input.content}")
        logger.info(f"📊 Message input token_count: {message_input.token_count}")

        # Process the message
        response = await conversation_service.process_user_message(message_input)

        logger.info("✅ Message processing completed!")
        logger.info(f"📊 Response token_count: {response.token_count}")
        logger.info(f"📊 Response execution_time: {response.execution_time}")
        logger.info(f"📊 Response metadata type: {type(response.metadata)}")

        if response.metadata:
            logger.info(f"📊 Metadata keys: {list(response.metadata.model_dump().keys())}")

            # Check for search metadata
            if hasattr(response.metadata, "search_metadata") and response.metadata.search_metadata:
                search_meta = response.metadata.search_metadata
                logger.info(f"📊 Search metadata keys: {list(search_meta.keys())}")

                # Check for token usage in search metadata
                if "token_usage" in search_meta:
                    token_usage = search_meta["token_usage"]
                    logger.info(f"📊 Token usage in search metadata: {token_usage}")
                else:
                    logger.warning("⚠️  No token_usage found in search metadata")

                # Check for CoT steps
                if "cot_steps" in search_meta:
                    cot_steps = search_meta["cot_steps"]
                    logger.info(f"📊 CoT steps count: {len(cot_steps)}")
                    if cot_steps:
                        logger.info(f"📊 CoT steps: {cot_steps}")
                    else:
                        logger.warning("⚠️  CoT steps is empty")
                else:
                    logger.warning("⚠️  No cot_steps found in search metadata")

            # Check for cot_used flag
            if hasattr(response.metadata, "cot_used"):
                logger.info(f"📊 CoT used: {response.metadata.cot_used}")

            # Check for token_count in metadata
            if hasattr(response.metadata, "token_count"):
                logger.info(f"📊 Token count in metadata: {response.metadata.token_count}")

        # Print full response for inspection
        logger.info("📄 Full response structure:")
        response_dict = response.model_dump()
        logger.info(json.dumps(response_dict, indent=2, default=str))

        # Clean up
        await conversation_service.delete_session(session.id, user_id)
        logger.info("🗑️  Cleaned up test session")

    except Exception as e:
        logger.error(f"❌ Error during debug: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(debug_token_tracking())
