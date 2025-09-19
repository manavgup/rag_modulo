#!/usr/bin/env python3
"""Quick test to verify CoT LLM integration is working properly."""

import asyncio
import logging
import os
from uuid import uuid4

from core.config import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rag_solution.services.search_service import SearchService

# Configure logging to see debug messages
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def setup_test_environment():
    """Set up minimal environment variables for testing."""
    os.environ.update(
        {
            "JWT_SECRET_KEY": "test",
            "RAG_LLM": "openai",
            "WATSONX_INSTANCE_ID": "test",
            "WATSONX_APIKEY": "test",
            "WATSONX_URL": "https://test.com",
        }
    )


async def test_cot_llm_integration():
    """Test that CoT service uses LLM provider instead of fallback templates."""
    setup_test_environment()

    # Create a minimal database session (in-memory SQLite for testing)
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Initialize SearchService which will create CoT service with LLM
        settings = get_settings()
        search_service = SearchService(db=db, settings=settings)

        # Access the chain_of_thought_service property to trigger initialization
        cot_service = search_service.chain_of_thought_service

        # Test question classification
        logger.info("Testing question classification...")
        classification = await cot_service.classify_question(
            "How does machine learning compare to traditional programming?"
        )
        logger.info(f"Classification result: {classification}")

        # Test reasoning step execution with debug logging
        logger.info("Testing reasoning step execution...")
        reasoning_step = await cot_service.execute_reasoning_step(
            step_number=1,
            question="What is machine learning?",
            context=["Machine learning is a subset of artificial intelligence."],
            previous_answers=[],
            user_id=str(uuid4()),
        )

        logger.info(f"Reasoning step result: {reasoning_step}")
        logger.info(f"Intermediate answer: {reasoning_step.intermediate_answer}")

        # Check if the answer looks like an LLM-generated response vs template fallback
        if "Based on the available context:" in reasoning_step.intermediate_answer:
            logger.warning("⚠️  Still using template fallback responses!")
            logger.warning("   This suggests LLM service is not properly initialized")
        else:
            logger.info("✅ Answer appears to be LLM-generated (not template fallback)")

        return reasoning_step

    finally:
        db.close()


if __name__ == "__main__":
    result = asyncio.run(test_cot_llm_integration())
    print(f"\nFinal result: {result.intermediate_answer}")
